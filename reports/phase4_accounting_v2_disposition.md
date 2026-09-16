# V2 accounting disposition — provider evidence incomplete

Attempt: `p4-v2-20260915T104415Z`; notebook
`daichongwei06/arc3-phase4-fixture-prescreen-v2`; submitted version 1.
This is an append-only follow-up to `phase4_prescreen_v2_result.json`; it does not
replace that result or claim that billing has been reconciled.

## Evidence collected

Authenticated read-only SDK queries were made on September 15, 2026. The two
exports retain provider response fields, not authentication headers or notebook
source. Their `observed_at_utc` fields are local collection times in UTC, not
provider start/end times.

| Export | SHA-256 |
| --- | --- |
| `reports/phase4_accounting_v2_provider_export.json` | `5d0c158b62b1a361ce0ce3f5d7c1f0997d9d8acd490235803f13991405ce90b4` |
| `reports/phase4_accounting_v2_latest_export.json` | `d8d357ecb7955bec64dd6f49d42b1a1efec7ca97fdd38eebc9ffd1996962778c` |

Explicit `version_label=1` metadata and status requests returned HTTP 404. The
unversioned direct metadata response reports `currentVersionNumber=1`, notebook
ID `134478860`, private visibility, internet disabled, and accelerator
`NvidiaRtxPro6000`; the unversioned status response reports `COMPLETE`.
The notebook ID is **not** a session/run ID.

| Requested accounting field | Confirmed evidence / limitation |
| --- | --- |
| Provider session/run ID | Unavailable in these responses; local attempt ID is not a provider session ID. |
| Accelerator | Provider metadata: `NvidiaRtxPro6000`. Retained run telemetry: NVIDIA RTX PRO 6000 Blackwell Server Edition, UUID `GPU-335dc396-171a-bdba-3c3c-6a06aed3b9f9`. |
| Provider duration / charged GPU time | Unavailable per attempt. No value inferred. |
| Provider start/end with timezone | Unavailable. `lastRunTime=2026-09-12T13:26:14.566Z` is retained verbatim (UTC), but is not labeled start or end. It differs from prior observations and the collection date; it is not used for duration arithmetic. |
| Notebook internal elapsed | 1,074.1611904619997 seconds from the first cell; not provider billing or provisioning duration. |
| Interactive sessions / failed starts | Unknown. Available SDK read methods do not enumerate complete session history. No authenticated browser session-history view or owner attestation was available during collection. |
| Submitted attempts | Local launch record documents exactly one push, acknowledged as provider version 1; latest direct metadata still reports version 1. This does not prove absence of interactive sessions or failed starts. |

The account quota export is not per-attempt accounting. Its raw GPU `timeUsed`
is `26171.27.0s`, and `totalTimeAllowed` is `21600s`; neither is normalized into
a run duration. Earlier account counters decreased. These inconsistencies are
retained rather than repaired by inference. Provider log elapsed time is also
not a charged-duration measurement.

## Disposition

- Retain the full 28,800-second prescreen reservation; release zero seconds.
- Exact billed usage and complete session inventory remain unknown.
- The attempt remains consumed. No retry, restart, extra upload or scored run.
- No unused balance is transferred to full-game certification.
- A provider session-history export/screenshot or explicit owner-confirmed
  evidence can be added in a later disposition; never alter the original result.

Owner confirmation requested (not yet received):

> Version 1 was the only submitted run: [confirm / correct]. Additional
> interactive sessions or failed attempts: [none / list / unknown]. Kaggle
> displays duration: [value and units / unavailable]. Exact charged GPU time:
> [value and units / unavailable]. Start/end and timezone: [values / unavailable].
> Session/run ID: [value / unavailable].

An owner confirmation with unavailable exact usage may clarify inventory but
does not by itself release any of the retained reservation.
