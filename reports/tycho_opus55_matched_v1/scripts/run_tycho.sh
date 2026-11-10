#!/bin/zsh
# Launch the patched Tycho clone in a clean environment (no inherited *_BASE_URL, OPERATION_MODE,
# plugin, or OpenAI variables). Secrets are read from files and never echoed.
#   run_tycho.sh smoke            -> one paid transport call (~$0.01)
#   run_tycho.sh run <run-name>   -> lf52 + bp35, 100 actions/game, $70/game ceiling
# Optional overrides (defaults reproduce the Opus 5.5 matched run):
#   MODEL=claude-opus-5 CONFIG=<abs path to yaml> GAMES=bp35-0a0ad940 TAG=<replay tag>
#   EXTRA_ENV="TYCHO_MAX_INFERENCE_COST_PER_GAME=300 TYCHO_MAX_GAME_ACTIONS=100"
# Environment variables take precedence over the config file, so MODEL must match the config.
set -euo pipefail
REPO=/private/tmp/claude-501/-Users-dcw06-Desktop-AGI/36deb578-9c3d-406a-a800-7a40909bb0ae/scratchpad/untrusted/tycho
BASE=/Users/dcw06/Desktop/AGI/.cache/tycho          # under $HOME so Colima can bind-mount workspaces
KEY_FILE=${TYCHO_KEY_FILE:-$HOME/.config/tycho/anthropic.env}
ARC_ENV=/Users/dcw06/Desktop/AGI/.env

read_var() {  # read_var FILE NAME -> value (quotes stripped), never printed
  local line
  line=$(grep -E "^$2=" "$1" | tail -n 1) || { echo "missing $2 in $1" >&2; exit 2; }
  line=${line#*=}; line=${line%\"}; line=${line#\"}; line=${line%\'}; line=${line#\'}
  print -rn -- "$line"
}

[[ -f $KEY_FILE ]] || { echo "key file not found: $KEY_FILE" >&2; exit 2; }
ANTHROPIC_KEY=$(read_var "$KEY_FILE" ANTHROPIC_API_KEY)
ARC_KEY=$(read_var "$ARC_ENV" ARC_API_KEY)
[[ $ANTHROPIC_KEY == sk-ant-* ]] || { echo "unexpected key format in $KEY_FILE" >&2; exit 2; }
mkdir -p "$BASE/tmp" "$BASE/runs" "$BASE/diagnostics"

CLEAN=(
  HOME="$HOME" PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin" LANG=en_US.UTF-8
  TMPDIR="$BASE/tmp" MPLCONFIGDIR="$BASE/tmp"
  ANTHROPIC_API_KEY="$ANTHROPIC_KEY" ARC_API_KEY="$ARC_KEY"
  LLM_BACKEND=anthropic LLM_MODEL=${MODEL:-claude-opus-5-5}
  TYCHO_SANDBOX_RUNTIME=docker TYCHO_SKIP_WM_BAKE=1
  ANTHROPIC_THINKING_DISPLAY=summarized
)
cd "$REPO"
case ${1:-} in
  smoke)
    exec env -i "${CLEAN[@]}" .venv/bin/python scripts/smoke_provider.py --confirm-paid-call --effort low ;;
  replay)
    # Export the recorded action traces and replay them through the ARC API in competition mode
    # (no model calls; ARC key only). Writes replay_manifest.json with the scorecard id/url.
    NAME=${2:?run name}
    RUN="$BASE/runs/$NAME"; REP="$BASE/replays/$NAME"
    [[ -d $RUN ]] || { echo "no run dir: $RUN" >&2; exit 2; }
    [[ ! -e $REP ]] || { echo "replay dir exists: $REP" >&2; exit 2; }
    mkdir -p "$REP"
    RENV=(HOME="$HOME" PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin" LANG=en_US.UTF-8
          TMPDIR="$BASE/tmp" MPLCONFIGDIR="$BASE/tmp" ARC_API_KEY="$ARC_KEY")
    env -i "${RENV[@]}" .venv/bin/python -m tycho.harness.submission_replay export \
      --run-dir "$RUN" --out "$REP/trace.json"
    exec env -i "${RENV[@]}" .venv/bin/python -m tycho.harness.submission_replay replay \
      --trace "$REP/trace.json" --out-dir "$REP" --mode competition --competition \
      --tag tycho --tag "${TAG:-opus55-matched-100}" ;;
  continue)
    # Continue an existing run in place from its exact per-game checkpoints (journal replay, then
    # actor/workspace restore). Records are moved aside so --resume re-schedules the games.
    NAME=${2:?run name}; OUT="$BASE/runs/$NAME"
    [[ -f $OUT/run_spec.json ]] || { echo "no run_spec in $OUT" >&2; exit 2; }
    mkdir -p "$OUT/superseded"
    for f in "$OUT"/game_*.json(N); do mv "$f" "$OUT/superseded/"; done
    exec env -i "${CLEAN[@]}" TYCHO_DIAGNOSTICS_DIR="$BASE/diagnostics/$NAME" ${=EXTRA_ENV:-} \
      .venv/bin/python -m tycho.harness.run_parallel --approach tycho \
      --games "${GAMES:-lf52-271a04aa,bp35-0a0ad940}" --out-dir "$OUT" \
      --config "${CONFIG:-configs/local/opus55_orchestrator_matched.yaml}" \
      --operation-mode normal --max-workers 2 --resume ${=EXTRA_ARGS:-} ;;
  extend-spec)
    # extend-spec <source-run> <new-run> '<games-json>'  (budget env vars via EXTRA_ENV)
    SRC="$BASE/runs/${2:?source run}"; NEW="$BASE/runs/${3:?new run}"
    exec env -i "${CLEAN[@]}" ${=EXTRA_ENV:-} .venv/bin/python "${0:A:h}/build_extend_spec.py" \
      "$SRC/run_spec.json" "$NEW" "${CONFIG:-configs/local/opus55_orchestrator_matched.yaml}" "${4:?games json}" ;;
  probe)
    exec env -i "${CLEAN[@]}" .venv/bin/python "${0:A:h}/binding_probe.py" ;;
  run)
    NAME=${2:?run name}
    OUT="$BASE/runs/$NAME"
    [[ ! -e $OUT ]] || { echo "out-dir exists: $OUT (use a fresh name)" >&2; exit 2; }
    exec env -i "${CLEAN[@]}" TYCHO_DIAGNOSTICS_DIR="$BASE/diagnostics/$NAME" ${=EXTRA_ENV:-} \
      .venv/bin/python -m tycho.harness.run_parallel --approach tycho \
      --games "${GAMES:-lf52-271a04aa,bp35-0a0ad940}" --out-dir "$OUT" \
      --config "${CONFIG:-configs/local/opus55_orchestrator_matched.yaml}" \
      --operation-mode normal --max-workers 2 ;;
  show-config)
    # No model call, no network: print the settings a run would resolve to.
    exec env -i "${CLEAN[@]}" ANTHROPIC_API_KEY=redacted ARC_API_KEY=redacted ${=EXTRA_ENV:-} \
      .venv/bin/python -c 'import sys, json
from tycho.config import run_config as rc
p = sys.argv[1]; rc.apply_config_file(p)
import os
for k in ("LLM_BACKEND", "LLM_MODEL", "LLM_EFFORT", "TYCHO_EFFORT", "ANTHROPIC_THINKING", "TYCHO_MODE",
          "TYCHO_MAX_INFERENCE_COST_PER_GAME", "TYCHO_MAX_GAME_ACTIONS", "TYCHO_MAX_LLM_CALLS", "TYCHO_MAX_TOKENS"):
    print(f"{k:36} {os.environ.get(k)}")' "${CONFIG:-configs/local/opus55_orchestrator_matched.yaml}" ;;
  *) echo "usage: $0 smoke | run <name> | show-config | continue <name> | replay <name>" >&2; exit 2 ;;
esac
