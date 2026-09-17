# V8 pilot failure during monitored model startup

Version 1 reached `ERROR`. Manifest-only staging of the frozen games and split offline installation both passed. The monitor released the worker, which entered the model environment. Model readiness and workload completion were not established.

The fatal monitor error was `ValueError: monitor resource or sampling-gap limit`. Its combined predicate covers RAM outside 0–128 GiB, scratch outside 0–4 GiB, or a sampling gap above one second. The rejected sample is checked before it is appended or retained, and the failure receipt saves only the generic error. Consequently the exact triggering value cannot be recovered from these outputs.

All 24 retained samples were within limits. Their maximum gap was 0.899 seconds, maximum group RSS 1,095,053,312 bytes, maximum scratch 59,159 bytes, and maximum VRAM 714,080,256 bytes. The last retained sample was at 138.585 seconds; the outer supervisor reported monitor failure at 141.158 seconds. A sampling delay is plausible given these values, but is not proven. The retained VRAM use indicates GPU activity, not a loaded or ready model.

The next repair should first make this failure diagnosable: retain the rejected measurements, previous and current timestamps, separate probe durations, and the exact violated constraint in a bounded failure receipt. Review the serial GPU/RSS/scratch probes and persistence overhead while preserving the one-second limit. A monitor failure must still cancel the worker and invalidate the run. Cleanup should include a separately retained post-termination GPU-process check even when the continuous monitor has failed; that check cannot restore lost monitoring evidence or make the attempt pass. Exercise delayed-probe, resource-limit, retention-failure and monitor-death cleanup cases locally before another GPU request.

Source, dependency-tree, scratch and process cleanup receipts passed. GPU cleanup is **unverified**: the monitor failed before producing its final cleanup receipt. The final notebook verdict is failed, at 147.545 seconds. No capacity or successful model-pilot result is claimed.

Account usage changed from 26,818.521 to 26,976.712 seconds: 158.191 aggregate GPU seconds, not exact per-attempt billing. The attempt is consumed; the full 28,800-second local reservation remains retained. No retry was submitted. Output hashes and archive reference are in `reports/phase4_v8_pilot_evaluation.json`.
