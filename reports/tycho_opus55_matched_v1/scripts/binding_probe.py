"""Probe Opus 5.5 preserved-thinking enforcement through Tycho's own (patched) transport.

Call 1 gets a reply with a thinking block. Call 2 replays it after EDITING the first user turn,
which is what Tycho's image cap does. Enforced account -> first attempt 400s, the patch flips to
drop_block and retries; non-enforced -> succeeds directly. Prints only non-secret diagnostics.
"""
import os
import time

from tycho.serving import llm_client
from tycho.serving import public_backends as backends

os.environ.setdefault("ANTHROPIC_THINKING", "adaptive")
os.environ.setdefault("ANTHROPIC_THINKING_DISPLAY", "summarized")
os.environ["TYCHO_PROMPT_CACHING"] = "0"
cfg = llm_client.LLMConfig.from_env()
assert cfg.backend == "anthropic" and cfg.base_url == "https://api.anthropic.com/v1", (cfg.backend, cfg.base_url)

def retry(fn):
    return fn()

q1 = ("A 5x5 grid has cells numbered 1..25 row by row. A token starts on cell 13 and alternately moves "
      "two right (wrapping) then one up (wrapping), 7 moves total. Which cell does it end on? Reply with the number only.")
r1 = None
for effort in ("medium", "high"):
    r1 = backends.anthropic_tools([{"role": "user", "content": q1}], [], cfg, "Be precise.", 4000, 300, effort, retry)
    if r1.get("raw_reasoning"):
        break
print("call1 text:", repr(r1["text"][:40]), "thinking_blocks:", len(r1.get("raw_reasoning") or []), "usage:", r1["usage"])
if not r1.get("raw_reasoning"):
    raise SystemExit("no thinking block returned; probe inconclusive")

history = [
    {"role": "user", "content": q1 + " (edited)"},  # earlier turn changed -> block bound to a different prefix
    {"role": "assistant", "content": r1["text"], "raw_reasoning": r1["raw_reasoning"]},
    {"role": "user", "content": "Now add 1 to your answer. Number only."},
]
t = time.time()
r2 = backends.anthropic_tools(history, [], cfg, "Be precise.", 4000, 300, "medium", retry)
print("call2 text:", repr(r2["text"][:40]), "usage:", r2["usage"], "secs:", round(time.time() - t, 1))
print("binding mode after call2:", repr(backends._binding_mode()), "stats:", backends.BINDING_STATS)
print("input_transformations:", r2.get("input_transformations"))
print("ENFORCED" if backends.BINDING_STATS["auto_enabled"] else "NOT ENFORCED (mismatched block reached the model)")
