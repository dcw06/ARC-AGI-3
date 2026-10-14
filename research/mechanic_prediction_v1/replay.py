"""Strict local replay of generated fixtures, independent keys, and request schedule."""
from research.mechanic_prediction_v1.build import make_bundle, sha256


def verify_scenario(scenario):
    history = scenario["history"]
    if not history or history[0]["pre_observation"] != scenario["initial_observation"]:
        raise ValueError("trajectory does not start at its initial observation")
    for index, record in enumerate(history):
        status = record["dispatch_status"]
        if status not in {"acknowledged", "dispatch_failed", "outcome_unknown"}:
            raise ValueError("unknown dispatch status")
        if record["pre_observation_source"] == "initial_observation":
            if index != 0:
                raise ValueError("initial observation source appears after step one")
        elif index:
            previous = history[index - 1]
            prior_status = previous["dispatch_status"]
            if record["pre_observation_source"] == "returned_observation":
                expected = {"frames": [previous["returned_frames"][-1]],
                            "signals": previous["returned_signals"]}
                if prior_status != "acknowledged" or record["pre_observation"] != expected:
                    raise ValueError("returned observation is not trajectory-continuous")
            elif record["pre_observation_source"] == "unchanged_after_dispatch_failure":
                if prior_status != "dispatch_failed" or record["pre_observation"] != previous["pre_observation"]:
                    raise ValueError("failed dispatch changed the known observation")
            elif record["pre_observation_source"] == "fresh_observation_after_unknown":
                if prior_status != "outcome_unknown":
                    raise ValueError("fresh observation does not follow an unknown outcome")
            else:
                raise ValueError("unknown observation source")
        if record["action"]["action_id"] not in record["available_actions"] and status != "dispatch_failed":
            raise ValueError("unavailable action was treated as acknowledged")
        if status == "acknowledged":
            if not record["returned_frames"] or type(record["returned_signals"]) is not dict:
                raise ValueError("acknowledged action lacks returned observations")
        elif record["returned_frames"] or record["returned_signals"] is not None or "observed_outcome" in record:
            raise ValueError("failed or unknown dispatch was converted to a no-op")
    proposed = scenario["proposed_action"]
    if any(record["action"] == proposed for record in history):
        raise ValueError("proposed action-coordinate pair is not novel")
    return True


def verify_bundle(bundle):
    expected = make_bundle()
    required = {"fixtures", "keys", "schedule", "manifest", "shortcuts", "token_audit"}
    if type(bundle) is not dict or set(bundle) != required:
        raise ValueError("bundle artifact set mismatch")
    for name in ("fixtures", "keys", "schedule"):
        if bundle["manifest"]["sha256"].get(name) != sha256(bundle[name]):
            raise ValueError(f"{name} manifest digest mismatch")
    if bundle["manifest"] != expected["manifest"]:
        raise ValueError("manifest differs from the frozen generated bundle")
    for name in required - {"manifest"}:
        if bundle[name] != expected[name]:
            raise ValueError(f"{name} differs from regenerated evidence")
    return {
        "status": "verified",
        "scenario_count": len(bundle["fixtures"]["cases"]),
        "request_count": bundle["schedule"]["request_count"],
        "evidence_scope": "declared_mechanism_space_only",
    }