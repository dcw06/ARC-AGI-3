"""Fail-closed offline artifact/context audit and target GPU telemetry.

Tokenizer contract: https://huggingface.co/docs/transformers/v4.57.0/chat_templating
No model generation, downloads, or environment access is needed for the audit.
"""
import csv
import hashlib
import importlib.metadata
import json
import subprocess
import threading

from evaluation.m0_profile import inventory_artifact_tree
from evaluation.phase4 import ROOT, sha
from evaluation.phase4_workload import canonical, validate_workload


def verify_artifact(primary):
    path = primary.model_path
    if path.is_symlink():
        raise ValueError("model root must not be a symlink")
    inventory = inventory_artifact_tree(path)
    if inventory.tree_sha256 != primary.model_tree_sha256:
        raise ValueError("model artifact SHA-256 mismatch")
    if (any(not (path / name).is_file() for name in primary.required_files)
            or len(list(path.glob(primary.shard_glob))) != primary.shard_count):
        raise ValueError("model artifact layout mismatch")
    return {"tree_sha256": inventory.tree_sha256, "bytes": inventory.total_bytes,
            "file_count": inventory.file_count}


def audit_context(fixtures, tokenizer, context_limit):
    if type(context_limit) is not int or context_limit < 1:
        raise ValueError("invalid context limit")
    counts = {}
    for fixture in fixtures:
        request = fixture["request"]
        digest = hashlib.sha256(canonical(request)).hexdigest()
        if digest != fixture["request_sha256"]:
            raise ValueError("fixture request hash mismatch")
        if any(not isinstance(m["content"], str) for m in request["messages"]):
            raise ValueError("E1S-R requires text-grid messages")
        # Do not truncate oversized input to manufacture a pass. Include the
        # generation prompt and the exact frozen chat-template keyword arguments.
        tokens = tokenizer.apply_chat_template(request["messages"], tokenize=True,
            add_generation_prompt=True, truncation=False,
            **request.get("chat_template_kwargs", {}))
        if not isinstance(tokens, list) or not tokens or any(type(t) is not int for t in tokens):
            raise ValueError("tokenizer returned invalid token sequence")
        completion = request["max_tokens"]
        if type(completion) is not int or completion <= 0 or len(tokens) + completion > context_limit:
            raise ValueError("prompt plus completion exceeds frozen context limit")
        if digest in counts:
            raise ValueError("duplicate request fixture")
        counts[digest] = len(tokens)
    if not counts:
        raise ValueError("empty context audit")
    return counts


def preflight(primary, workload, root=ROOT):
    validate_workload(workload, root)
    lock = json.loads((root / "config/phase4_preflight_lock.json").read_text())
    if sha(primary.launch_spec_path) != lock["launch_spec_sha256"]:
        raise ValueError("target launch spec drift")
    argv = json.loads(primary.launch_spec_path.read_text())["argv"]
    if (argv.count("--max-model-len") != 1
            or lock["context_limit"] != int(argv[argv.index("--max-model-len") + 1])):
        raise ValueError("context limit differs from frozen server launch")
    artifact = verify_artifact(primary)
    if importlib.metadata.version("transformers").split("+")[0] != "4.57.6":
        raise ValueError("tokenizer package version drift")
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(primary.model_path),
        local_files_only=True, trust_remote_code=False)
    counts = audit_context(workload["fixtures"], tokenizer, lock["context_limit"])
    return {"artifact": artifact, "prompt_tokens_by_request_sha256": counts,
            "context_limit": lock["context_limit"], "workload_sha256": workload["workload_sha256"],
            "model_inference": False, "target_gpu_certified": False,
            "server_token_count_parity": "pending_live_comparison"}


def sample_gpu(expected_uuid, max_used_bytes):
    if not expected_uuid or type(max_used_bytes) is not int or max_used_bytes <= 0:
        raise ValueError("GPU UUID and explicit VRAM ceiling are required")
    result = subprocess.run(["nvidia-smi", "--query-gpu=uuid,name,memory.total,memory.used",
        "--format=csv,noheader,nounits"], capture_output=True, text=True, check=True, timeout=2)
    rows = list(csv.reader(result.stdout.strip().splitlines()))
    if len(rows) != 1 or len(rows[0]) != 4:
        raise ValueError("expected exactly one unambiguous target GPU")
    uuid, name, total, used = [v.strip() for v in rows[0]]
    if uuid != expected_uuid or "RTX PRO 6000" not in name:
        raise ValueError("target GPU identity mismatch")
    total, used = int(total) * 1024**2, int(used) * 1024**2
    if not 0 <= used <= total or not 0 < max_used_bytes <= total:
        raise ValueError("invalid GPU memory telemetry or ceiling")
    if used > max_used_bytes:
        raise MemoryError("target VRAM ceiling exceeded")
    return {"uuid": uuid, "name": name, "total_bytes": total, "used_bytes": used}


class GPUMonitor:
    """Device-wide polling bound, not an allocator cap or per-process estimate."""
    def __init__(self, uuid, max_used_bytes, interval_seconds=.25):
        if interval_seconds <= 0:
            raise ValueError("monitor interval must be positive")
        self.uuid, self.max_used_bytes = uuid, max_used_bytes
        self.interval = interval_seconds
        self.peak_bytes = 0
        self.error = None
        self.stop = threading.Event()
        self.thread = None

    def check(self):
        if self.error is not None:
            raise RuntimeError("GPU monitor failed") from self.error
        try:
            row = sample_gpu(self.uuid, self.max_used_bytes)
            self.peak_bytes = max(self.peak_bytes, row["used_bytes"])
            return row
        except Exception as exc:
            self.error = exc
            raise

    def start(self):
        if self.thread is not None:
            raise RuntimeError("GPU monitor already started")
        self.check()
        def poll():
            while not self.stop.wait(self.interval):
                try:
                    self.check()
                except Exception:
                    return
        self.thread = threading.Thread(target=poll, daemon=True, name="p4-gpu-monitor")
        self.thread.start()

    def close(self):
        self.stop.set()
        if self.thread is not None:
            self.thread.join(timeout=3)
            if self.thread.is_alive():
                raise RuntimeError("GPU monitor did not stop")
