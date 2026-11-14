#!/bin/zsh
# Level-4 replicates of bp35 for Tycho + Opus 5.5, each starting from the exact action-100 checkpoint of
# the matched run (levels 1-3 done, 2 actions into level 4) and stopping when level 4 is completed.
#   l4exp.sh prep <name> <effort> [dc]  copy checkpoint + write run spec (no model call)
#   l4exp.sh go   <name> <effort> [dc]  continue live (paid) until level 4 completes or a cap is hit
#   l4exp.sh dry  <name> <effort> [dc]  replay to action 100 and stop (no model call) - validates the setup
# Optional 4th argument: "dc" = decision check (TYCHO_DECISION_CHECK=1), "rc" = restart challenge
# (TYCHO_RESTART_CHALLENGE=1), "dcrc" = both. GUARD="<level>:<actions>" sets TYCHO_LEVEL_PREFIX_GUARD
# (used once, to save the level-6 position the runs abandon).
# Caps (overridable): COST_CAP = total per-game USD including the $9.28 already in the checkpoint;
# ACTION_CAP = whole-game actions (98 were used before level 4).
set -euo pipefail
REPO=/private/tmp/claude-501/-Users-dcw06-Desktop-AGI/8aeb0acd-a0bc-47b6-8f45-2d65f611ed0f/scratchpad/tycho_l4
PY=/private/tmp/claude-501/-Users-dcw06-Desktop-AGI/36deb578-9c3d-406a-a800-7a40909bb0ae/scratchpad/untrusted/tycho/.venv/bin/python
BASE=/Users/dcw06/Desktop/AGI/.cache/tycho
SRC=$BASE/runs/${SRC_RUN:-opus55-matched-20261109}   # run whose latest checkpoint every replicate starts from
KEY_FILE=$HOME/.config/tycho/anthropic.env
CONFIG=configs/local/opus55_orchestrator_matched.yaml
GAME=bp35-0a0ad940
GAMES_JSON='{"bp35-0a0ad940": [21, 48, 44, 38, 33, 87, 86, 131, 163]}'
COST_CAP=${COST_CAP:-13.3}        # 9.28 restored + about 4.00 for the level-4 replicate
ACTION_CAP=${ACTION_CAP:-158}     # 98 + 60 actions on level 4
STOP_LEVELS=${STOP_LEVELS:-4}     # stop once this many levels are completed
DRY_AT=${DRY_AT:-100}             # number of actions in the source checkpoint (dry run stops there)

read_var() { local line; line=$(grep -E "^$2=" "$1" | tail -n 1) || { echo "missing $2 in $1" >&2; exit 2; }
  line=${line#*=}; line=${line%\"}; line=${line#\"}; line=${line%\'}; line=${line#\'}; print -rn -- "$line"; }

CMD=${1:?prep|go|dry}; NAME=${2:?run name}; EFFORT=${3:?effort}; ARM=${4:-}
OUT=$BASE/runs/$NAME
POLICY=(LLM_BACKEND=anthropic LLM_MODEL=claude-opus-5-5 LLM_EFFORT=$EFFORT TYCHO_EFFORT=$EFFORT
        TYCHO_SANDBOX_RUNTIME=docker TYCHO_SKIP_WM_BAKE=1 ANTHROPIC_THINKING_DISPLAY=summarized
        TYCHO_STOP_AFTER_LEVELS=$STOP_LEVELS TYCHO_MAX_GAME_ACTIONS=$ACTION_CAP TYCHO_MAX_INFERENCE_COST_PER_GAME=$COST_CAP)
[[ -z $ARM || $ARM == dc || $ARM == rc || $ARM == dcrc ]] || { echo "4th argument must be dc, rc, dcrc or absent" >&2; exit 2; }
[[ $ARM == dc || $ARM == dcrc ]] && POLICY+=(TYCHO_DECISION_CHECK=1)
[[ $ARM == rc || $ARM == dcrc ]] && POLICY+=(TYCHO_RESTART_CHALLENGE=1)
[[ -n ${GUARD:-} ]] && POLICY+=(TYCHO_LEVEL_PREFIX_GUARD=$GUARD)
ALLOW="LLM_EFFORT,TYCHO_EFFORT,TYCHO_STOP_AFTER_LEVELS,TYCHO_MAX_GAME_ACTIONS,TYCHO_MAX_INFERENCE_COST_PER_GAME,TYCHO_DECISION_CHECK,TYCHO_RESTART_CHALLENGE,TYCHO_LEVEL_PREFIX_GUARD,sources_sha256"
BASE_ENV=(HOME="$HOME" PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin" LANG=en_US.UTF-8
          TMPDIR="$BASE/tmp" MPLCONFIGDIR="$BASE/tmp" PYTHONPATH="$REPO")   # PYTHONPATH: import the patched copy
cd "$REPO"
case $CMD in
  prep)
    [[ ! -e $OUT ]] || { echo "exists: $OUT" >&2; exit 2; }
    mkdir -p "$OUT/resume" "$OUT/ws" "$OUT/status"
    cp -R "$SRC/resume/bp35" "$OUT/resume/bp35"
    cp -R "$SRC/ws/bp35" "$OUT/ws/bp35"; cp -R "$SRC/ws/.workspace_blobs" "$OUT/ws/.workspace_blobs"
    cp -R "$SRC/status/bp35" "$OUT/status/bp35"
    env -i "${BASE_ENV[@]}" "${POLICY[@]}" ANTHROPIC_API_KEY=redacted ARC_API_KEY=redacted \
      "$PY" "${0:A:h}/build_spec.py" "$SRC/run_spec.json" "$OUT" "$CONFIG" "$GAMES_JSON" \
      "$ALLOW" ;;
  go|dry)
    [[ -f $OUT/run_spec.json ]] || { echo "no run_spec in $OUT (run prep first)" >&2; exit 2; }
    if [[ $CMD == dry ]]; then
      # Stop at action 100, before any model call. The spec was written for the live caps, so the dry run
      # uses a throwaway copy of the run directory with its own spec.
      DRY=$BASE/runs/$NAME-dry; rm -rf "$DRY"; cp -R "$OUT" "$DRY"; rm -f "$DRY/run_spec.json" "$DRY/run_spec_override.json"
      POLICY=(${POLICY:#TYCHO_MAX_GAME_ACTIONS=*} TYCHO_MAX_GAME_ACTIONS=$DRY_AT)
      env -i "${BASE_ENV[@]}" "${POLICY[@]}" ANTHROPIC_API_KEY=redacted ARC_API_KEY=redacted \
        "$PY" "${0:A:h}/build_spec.py" "$SRC/run_spec.json" "$DRY" "$CONFIG" "$GAMES_JSON" \
        "$ALLOW" >/dev/null
      OUT=$DRY; ANTHROPIC_KEY=invalid-dry-run-key; ARC_KEY=$(read_var /Users/dcw06/Desktop/AGI/.env ARC_API_KEY)
    else
      ANTHROPIC_KEY=$(read_var "$KEY_FILE" ANTHROPIC_API_KEY); ARC_KEY=$(read_var /Users/dcw06/Desktop/AGI/.env ARC_API_KEY)
      [[ $ANTHROPIC_KEY == sk-ant-* ]] || { echo "unexpected key format" >&2; exit 2; }
    fi
    exec env -i "${BASE_ENV[@]}" "${POLICY[@]}" ANTHROPIC_API_KEY="$ANTHROPIC_KEY" ARC_API_KEY="$ARC_KEY" \
      TYCHO_DIAGNOSTICS_DIR="$BASE/diagnostics/${OUT:t}" \
      "$PY" -m tycho.harness.run_parallel --approach tycho --games "$GAME" --out-dir "$OUT" \
      --config "$CONFIG" --operation-mode normal --max-workers 1 --resume ;;
  *) echo "usage: $0 prep|go|dry <name> <effort>" >&2; exit 2 ;;
esac
