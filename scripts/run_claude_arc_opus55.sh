#!/usr/bin/env bash
# Run Claude Opus 5.5 on ARC-AGI-3 through your Claude subscription (Claude Code CLI), not the paid API.
#
#   scripts/run_claude_arc_opus55.sh smoke         # 2 games (ft09, ls20), 15 actions each
#   scripts/run_claude_arc_opus55.sh competition   # every available game, one scorecard
#
# Each model call counts against your Claude plan's usage limits. Check /usage in Claude Code before and after.
# Before a long run, turn OFF "usage credits" in claude.ai Settings > Usage if you do not want paid credits spent
# once the plan limit is reached: the CLI switches to them silently, and this script cannot see that switch.
# Avoid starting other Claude Code terminal sessions during the run: they may auto-update the shared CLI.
# The ARC scorecard link is printed at the end; open it to see the score.
set -euo pipefail
# Closing the terminal (SIGHUP) must not kill the run before it closes its scorecard and writes its summary.
trap '' HUP
cd "$(dirname "$0")/.."

case "${1:-}" in
  smoke) config=config/claude_arc_v1.opus55_smoke.json; extra=() ;;
  competition) config=config/claude_arc_v1.opus55_competition.json; extra=(--confirm-competition) ;;
  *) echo "usage: $0 smoke|competition" >&2; exit 2 ;;
esac

# Only the ARC key is exported. The Anthropic API key in .env is deliberately not loaded:
# the backend also strips it, because with it present the CLI would bill the paid API.
ARC_API_KEY="$(grep -E '^ARC_API_KEY=' .env | head -1 | cut -d= -f2-)"
[ -n "$ARC_API_KEY" ] || { echo "ARC_API_KEY is missing from .env" >&2; exit 2; }
export ARC_API_KEY
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN

claude_bin="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['claude_cli'])" "$config")"
echo "Claude Code CLI: $(command -v "$claude_bin") ($("$claude_bin" --version)); Opus 5.5 needs 2.1.280 or newer."

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
output=".cache/claude_arc_runs/opus55-$1-$stamp"
mkdir -p .cache/claude_arc_runs
echo "Evidence folder: $output"

# caffeinate -i keeps the Mac awake for the whole run (a sleeping Mac lets the scorecard go idle and close).
status=0
caffeinate -i .venv/bin/python -m research.claude_arc_v1.cli --config "$config" --execute \
  --confirm-online-arc --confirm-subscription-usage ${extra[@]+"${extra[@]}"} --output "$output" \
  2> >(tee "$output.stderr.log" >&2) || status=$?

if [ -f "$output/summary.json" ]; then
  .venv/bin/python -m research.claude_arc_v1.audit "$output" || true
  python3 - "$output/summary.json" <<'EOF'
import json, sys
s = json.load(open(sys.argv[1]))
print('\nScorecard:', s.get('scorecard_url'))
card = s.get('official_scorecard') or {}
if isinstance(card, dict) and 'score' in card:
    print('Official score reported at close:', card['score'])
print('Model calls:', s['budget']['model_calls_attempted'])
for g in s['games']:
    print(f"  {g['game_id']:<16} levels {g['levels_completed']}  actions {g['actions_acknowledged']:>3}  stop {g['stop_reason']}")
if s['games_not_started']:
    print('Not started:', ', '.join(s['games_not_started']))
if s['problems']:
    print('Problems:', '; '.join(s['problems']))
EOF
fi
exit "$status"
