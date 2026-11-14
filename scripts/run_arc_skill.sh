#!/bin/zsh
# Play ARC-AGI-3 with arc-skill (github.com/pbshgthm/arc-skill, pinned copy) in the official Claude Code
# CLI, signed in with your Claude subscription. Nothing here uses the paid Anthropic API.
#
#   scripts/run_arc_skill.sh check                    login + model + permissions check (a few short model calls)
#   scripts/run_arc_skill.sh play <game> [tag]        interactive session in this terminal (as in the arc-skill README)
#   scripts/run_arc_skill.sh auto <game> [tag]        unattended: runs until the model stops; log in $WORK/logs
#   scripts/run_arc_skill.sh prefetch <game>...       download games into the local cache (uses the ARC key once)
#
# Rerunning play/auto with the same <game> and <tag> continues that run (same conversation, same game state).
# Compare a run with the published Opus 5 baseline: scripts/arc_skill_compare.py <game>-<tag>
#
# Defaults: Claude Opus 5 at effort high (Claude Code's own default for Opus 5). Override with
# ARC_SKILL_MODEL / ARC_SKILL_EFFORT. Every model call counts against your plan's usage limits.
# Turn OFF "usage credits" in claude.ai Settings > Usage if you do not want paid credits spent once the
# plan limit is reached: the CLI switches to them silently and this script cannot see that.
#
# Isolation (so a run starts cold and replicates do not see each other):
#   - each run gets its own project folder $WORK/runs/<game>-<tag> with its own copy of the skill;
#   - user-level Claude settings are not loaded (--setting-sources project,local), auto memory is off;
#   - the environment is rebuilt from scratch: no ANTHROPIC_* variable, no ARC key (games are played from
#     the local cache), nothing inherited from another Claude Code session;
#   - reads of the game cache, the AGI repo and other Claude sessions' files are denied by rule, and so
#     are web search and web fetch.
# These are permission rules, not an OS sandbox: `arc python` runs model-written Python as you.
set -euo pipefail
trap '' HUP

AGI=${0:A:h:h}
WORK=${ARC_SKILL_WORK:-$HOME/Desktop/arc-skill-work}
MASTER=$WORK/skill-master/arc-skill
VENV=$AGI/.cache/arc_skill/venv
CACHE=$HOME/.cache/arc-skill/arcade
MODEL=${ARC_SKILL_MODEL:-claude-opus-5}
EFFORT=${ARC_SKILL_EFFORT:-high}
CLAUDE_BIN=${CLAUDE_BIN:-$(command -v claude)}

[[ -x $MASTER/scripts/arc ]] || { echo "skill copy missing: $MASTER" >&2; exit 2; }
[[ -x $VENV/bin/python ]] || echo "note: $VENV missing; the skill will build its own Python runtime on first use" >&2

cached() { [[ -n $(print -l $CACHE/environment_files/$1/*/metadata.json(N)) ]]; }

prefetch() {
  local key; key=$(grep -E '^ARC_API_KEY=' "$AGI/.env" | head -1 | cut -d= -f2-)
  [[ -n $key ]] || { echo "no ARC_API_KEY in $AGI/.env" >&2; exit 2; }
  local g
  for g in "$@"; do
    if cached $g; then echo "cached: $g"; continue; fi
    (cd /tmp && ARC_API_KEY=$key "$VENV/bin/python" -I - "$g" "$CACHE" <<'PY'
import sys, tempfile, arc_agi
from arc_agi import OperationMode
game, cache = sys.argv[1], sys.argv[2]
arcade = arc_agi.Arcade(arc_api_key=__import__("os").environ["ARC_API_KEY"], operation_mode=OperationMode.NORMAL,
                        environments_dir=cache + "/environment_files", recordings_dir=tempfile.mkdtemp())
print("downloaded:" if arcade.make(game, seed=0) is not None else "FAILED:", game)
PY
    )
  done
}

# Build (or reuse) the per-run project folder and print its path. Permission rules go in a settings file
# outside the folder and are passed with --settings: rules inside a new, untrusted folder are ignored.
make_run() {
  local run=$WORK/runs/$1
  if [[ ! -d $run/.claude ]]; then
    mkdir -p "$run/.claude/skills" "$WORK/settings"
    cp -R "$MASTER" "$run/.claude/skills/arc-skill"
    local arc=$run/.claude/skills/arc-skill/scripts/arc
    cat > "$WORK/settings/$1.json" <<JSON
{
  "permissions": {
    "allow": [
      "Bash($arc)",
      "Bash($arc *)",
      "Bash(mkdir -p *)",
      "Bash(python3 *)"
    ],
    "deny": [
      "Read(/$HOME/.cache/arc-skill/**)",
      "Read(/$AGI/**)",
      "Read(/$HOME/.claude/projects/**)",
      "Read(//private/tmp/claude-501/**)",
      "WebFetch",
      "WebSearch"
    ]
  },
  "env": { "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1" }
}
JSON
  fi
  print -r -- "$run"
}

# Clean environment: nothing from the calling shell except what is listed here.
run_claude() {
  local run=$1; shift
  cd "$run"
  env -i HOME="$HOME" USER="$USER" LOGNAME="${LOGNAME:-$USER}" SHELL=/bin/zsh LANG="${LANG:-en_US.UTF-8}" \
    TERM="${TERM:-xterm-256color}" TMPDIR="${TMPDIR:-/tmp}" \
    PATH="$VENV/bin:${CLAUDE_BIN:h}:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
    ARC="$run/.claude/skills/arc-skill/scripts/arc" CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 \
    "$CLAUDE_BIN" --model "$MODEL" --effort "$EFFORT" --setting-sources project,local \
    --settings "$WORK/settings/${run:t}.json" --permission-mode acceptEdits "$@"
}

cmd=${1:-}; shift || true
case $cmd in
  prefetch) [[ $# -ge 1 ]] || { echo "usage: $0 prefetch <game>..." >&2; exit 2; }; prefetch "$@" ;;
  check)
    run=$(make_run "_check-$(date +%Y%m%d-%H%M%S)"); arc=$run/.claude/skills/arc-skill/scripts/arc
    log=$WORK/logs/${run:t}.jsonl
    run_claude "$run" -p --permission-prompts none --output-format stream-json --verbose \
      "Setup check only; do not play a game beyond the single action below. Run each of these six Bash commands exactly as written, one per tool call, in this order, then reply with one line per command saying RAN or DENIED: (1) $arc --help   (2) $arc start ls20   (3) $arc act ACTION1 --predict change   (4) python3 -c 'print(6*7)'   (5) cat $CACHE/environment_files/bp35/0a0ad940/metadata.json   (6) \"\$ARC\" --help" \
      < /dev/null > "$log" || true
    "$VENV/bin/python" -I "$AGI/scripts/arc_skill_compare.py" --check-log "$log"
    echo "expected: commands 1-4 ran, 5 (game cache read) and 6 (shell-variable form) denied"
    pid=$(sed -n 's/.*"pid": *\([0-9]*\).*/\1/p' "$run/.arc/broker.json" 2>/dev/null || true)
    [[ -n $pid ]] && kill "$pid" 2>/dev/null && echo "stopped the check's game process"
    echo "log: $log" ;;
  play|auto)
    game=${1:?game id, e.g. bp35}; tag=${2:-$(date +%Y%m%d-%H%M%S)}
    cached "$game" || prefetch "$game"
    cached "$game" || { echo "game $game is not in the local cache" >&2; exit 2; }
    fresh=1; [[ -d $WORK/runs/$game-$tag/.claude ]] && fresh=0
    run=$(make_run "$game-$tag")
    # Unattended runs cannot approve prompts, and a command written through a shell variable ("\$ARC" ...)
    # cannot be pre-approved, so the unattended prompt names the launcher's literal path. Nothing else is added.
    hint=""; [[ $cmd == auto ]] && hint=" Call the arc launcher by its full literal path, $WORK/runs/$game-$tag/.claude/skills/arc-skill/scripts/arc, never through a shell variable. The current directory is the run directory for this game; run one command per call."
    if (( fresh )); then args=("solve ARC-AGI-3 game $game.$hint")
    else args=(--continue "continue solving ARC-AGI-3 game $game; run the arc status command first.$hint"); fi
    echo "run folder: $run   model: $MODEL   effort: $EFFORT" >&2
    if [[ $cmd == play ]]; then
      run_claude "$run" "${args[@]}"
    else
      log=$WORK/logs/$game-$tag.jsonl
      echo "unattended; log: $log" >&2
      caffeinate -i -w $$ &          # keep the Mac awake while this script runs (lid closed still sleeps)
      run_claude "$run" -p --permission-prompts none --output-format stream-json --verbose "${args[@]}" < /dev/null >> "$log" &
      sub=$!
      # Stop switches, checked every 5 s from outside the session (the prompt is not changed):
      #   ARC_SKILL_STOP_LEVELS=N   stop once N levels are completed
      #   ARC_SKILL_MAX_ACTIONS=N   stop once N actions have been taken
      #   ARC_SKILL_MAX_MINUTES=N   stop after N minutes of wall time
      t0=$SECONDS; why="session ended by itself"
      while kill -0 $sub 2>/dev/null; do
        sleep 5
        ev=$(print -l $run/**/.arc/events.jsonl(N) | grep -v '/.claude/' | head -1)
        prog=(0 0)
        [[ -n $ev ]] && prog=($("$VENV/bin/python" -I -c '
import json, sys
lines = [l for l in open(sys.argv[1]) if l.strip()]
print(json.loads(lines[-1])["levels_completed"], len(lines) - 1)' "$ev" 2>/dev/null || echo 0 0))
        if [[ -n ${ARC_SKILL_STOP_LEVELS:-} ]] && (( prog[1] >= ARC_SKILL_STOP_LEVELS )); then why="level target reached ($prog[1] levels)"
        elif [[ -n ${ARC_SKILL_MAX_ACTIONS:-} ]] && (( prog[2] >= ARC_SKILL_MAX_ACTIONS )); then why="action cap reached ($prog[2] actions)"
        elif [[ -n ${ARC_SKILL_MAX_MINUTES:-} ]] && (( SECONDS - t0 >= ARC_SKILL_MAX_MINUTES * 60 )); then why="time cap reached"
        else continue; fi
        pkill -TERM -P $sub 2>/dev/null || true; kill -TERM $sub 2>/dev/null || true
        break
      done
      wait $sub 2>/dev/null || true
      for b in $run/**/.arc/broker.json(N); do
        pid=$(sed -n 's/.*"pid": *\([0-9]*\).*/\1/p' "$b"); [[ -n $pid ]] && kill "$pid" 2>/dev/null || true
      done
      echo "stopped: $why" >&2
      "$VENV/bin/python" -I "$AGI/scripts/arc_skill_compare.py" "$game-$tag" || true
    fi ;;
  *) sed -n '2,12p' "$0" >&2; exit 2 ;;
esac
