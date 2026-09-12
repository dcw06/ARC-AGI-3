"""Read-only validation of the generated notebook and output contract."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    notebook = json.loads((ROOT / "notebooks" / "submission.ipynb").read_text())
    metadata = json.loads((ROOT / "notebooks" / "kernel-metadata.json").read_text())
    assert notebook["metadata"]["kaggle"]["isInternetEnabled"] is False
    assert metadata["enable_internet"] is False
    assert notebook["metadata"]["kaggle"]["accelerator"] == "nvidiaRtxPro6000"
    assert metadata["machine_shape"] == "NvidiaRtxPro6000"
    assert "driessmit1/arc3-vllm-h100-wheelhouse-v3" in metadata["dataset_sources"]
    assert "qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1" in metadata["model_sources"]
    source = "\n".join(str(cell.get("source", "")) for cell in notebook["cells"])
    assert "/kaggle/working/ARC-AGI-3-Agents" not in source
    assert "RECORDINGS_DIR=/kaggle/working" not in source
    assert "agent.production_main" in source
    assert "agent/runtime_audit.py" in source
    assert "agent/production_policy.py" in source
    assert "config/operational_primary.yaml" in source
    assert "sys.path.insert(0, '/tmp/arc3-agent/source')" in source
    assert "arc-agi==0.9.8" in source
    assert "requests==2.33.1" in source
    assert "numpy==2.4.4" in source
    assert "pydantic==2.13.2" in source
    assert "vllm==0.19.0" in source
    assert "torch==2.10.0" in source
    assert "transformers==4.57.6" in source
    # The adapter is base64 bundled, so inspect its authoritative source too.
    adapter_source = (ROOT / "agent" / "framework_adapter.py").read_text()
    assert "allow_redirects=False" in adapter_source
    print("submission notebook: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
