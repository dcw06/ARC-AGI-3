"""Append-only local family ledger; unresolved attempts retain their reservation."""
import fcntl
import json
import math
import hashlib
import os
from pathlib import Path

FAMILY_SECONDS = 8 * 3600


def verify_event_evidence(event, prior):
    if event["kind"] not in {"reconcile", "inventory_confirmed"}:
        return
    source = Path(event["evidence_path"])
    if hashlib.sha256(source.read_bytes()).hexdigest() != event["evidence_sha256"]:
        raise ValueError("ledger evidence missing or changed")
    evidence = json.loads(source.read_text())
    if event["kind"] == "reconcile":
        if (evidence.get("attempt_id") != event["attempt_id"]
                or evidence.get("charged_accelerator_seconds") != event["seconds"]
                or evidence.get("scope") != "all_accelerator_time_including_setup_and_failures"):
            raise ValueError("cost evidence does not substantiate the reconciliation")
    elif set(evidence.get("attempt_ids", [])) != set(prior["attempts"]):
        raise ValueError("incomplete provider attempt inventory")


def summarize(events):
    attempts = {}
    inventory_confirmed = False
    for event in events:
        kind = event["kind"]
        if kind in {"reserve", "discover"}:
            name = event["attempt_id"]
            seconds = event["seconds"]
            if name in attempts or type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds <= 0:
                raise ValueError("duplicate attempt or invalid reservation")
            attempts[name] = {"charged_seconds": seconds, "reconciled": False}
            if kind == "discover":
                inventory_confirmed = False
        elif kind == "reconcile":
            attempt = attempts[event["attempt_id"]]
            seconds = event["seconds"]
            if (attempt["reconciled"] or type(seconds) not in (int, float) or not math.isfinite(seconds)
                    or seconds <= 0 or not event.get("evidence_sha256") or not event.get("evidence_path")):
                raise ValueError("invalid reconciliation")
            attempt.update(charged_seconds=seconds, reconciled=True)
        elif kind == "inventory_confirmed":
            if not event.get("evidence_path") or not event.get("evidence_sha256"):
                raise ValueError("provider inventory evidence required")
            inventory_confirmed = True
        else:
            raise ValueError("unknown ledger event")
    total = sum(a["charged_seconds"] for a in attempts.values())
    return {"attempts": attempts, "charged_or_reserved_seconds": total,
            "remaining_seconds": max(0, FAMILY_SECONDS-total), "over_budget": total > FAMILY_SECONDS,
            "inventory_confirmed": inventory_confirmed,
            "new_execution_allowed": inventory_confirmed and total < FAMILY_SECONDS
                and all(a["reconciled"] for a in attempts.values())}


def read_ledger(path):
    value = json.loads(Path(path).read_text())
    if value["schema_version"] != 1:
        raise ValueError("unknown ledger schema")
    for i, event in enumerate(value["events"]):
        verify_event_evidence(event, summarize(value["events"][:i]))
    return summarize(value["events"])


def append_event(path, event):
    """Serialize appenders, preserve prior events, atomically replace the JSON file."""
    path = Path(path)
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        value = json.loads(path.read_text())
        read_ledger(path)
        prior = summarize(value["events"])
        verify_event_evidence(event, prior)
        if event["kind"] == "reserve" and (not prior["new_execution_allowed"] or event["seconds"] > prior["remaining_seconds"]):
            raise ValueError("unreconciled inventory/attempts or insufficient remaining family budget")
        events = value["events"] + [event]
        result = summarize(events)
        temporary = path.with_suffix(".tmp")
        with temporary.open("w") as stream:
            json.dump({"schema_version":1,"events":events}, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        return result
