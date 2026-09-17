#!/usr/bin/env bash
# Rebuild local development dependencies without changing frozen project assets.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PATH="$HOME/.local/bin:$PATH"
export UV_LINK_MODE=copy
command -v uv >/dev/null || { echo 'Install uv before running this script.' >&2; exit 1; }
command -v python3.12 >/dev/null || { echo 'Python 3.12 is required.' >&2; exit 1; }
mkdir -p .cache/matplotlib .kaggle
python3.12 - <<'PY'
import json
from pathlib import Path
manifest = json.loads(Path('config/dependency_manifest.lock').read_text())
Path('.cache/development-requirements.txt').write_text(''.join(
    f'{name}=={version}\n' for name, version in manifest['dependencies'].items()))
PY
if [ ! -x .venv/bin/python ]; then
    uv venv --python python3.12 .venv
fi
uv pip install --python .venv/bin/python -r .cache/development-requirements.txt
uv pip check --python .venv/bin/python
if [ ! -f vendor/ARC-AGI-3-Agents/agents/agent.py ]; then
    echo 'The transferred vendor framework is missing; restore it before running legacy tools.' >&2
    exit 1
fi
if [ ! -f .env ]; then cp .env.example .env; fi
echo 'Development environment ready. Run: source .venv/bin/activate'
