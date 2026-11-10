#!/bin/zsh
# Launch the PRO-LONG ARC-AGI-3 harness (Claude Code backend) on a Claude subscription.
# No Anthropic API key is ever placed in the environment, so nothing can bill the paid API.
# Secrets are read from files and never echoed.
#   run_prolong.sh check                 -> no model call: images, CLI version in the sandbox, token file
#   run_prolong.sh smoke                 -> one tiny model call through the sandbox (uses plan quota)
#   run_prolong.sh run <run-name>        -> play GAMES and publish a scorecard
# Overrides: MODEL (claude-opus-5) EFFORT (high) GAMES (bp35) MAX_ACTIONS (1000) MODE (online)
set -euo pipefail
REPO=/Users/dcw06/Desktop/AGI/.cache/prolong/arc-agi-3     # under $HOME so Colima can bind-mount workspaces
TOKEN_FILE=${PROLONG_TOKEN_FILE:-$HOME/.config/prolong/claude_oauth.env}
ARC_ENV=/Users/dcw06/Desktop/AGI/.env
MODEL=${MODEL:-claude-opus-5}
EFFORT=${EFFORT:-high}
IMAGE=prolong-agent/claude-sandbox:latest
BASE_ENV=(HOME="$HOME" PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin" LANG=en_US.UTF-8)

read_var() {  # read_var FILE NAME -> value (quotes stripped), never printed
  local line
  line=$(grep -E "^$2=" "$1" | tail -n 1) || { echo "missing $2 in $1" >&2; exit 2; }
  line=${line#*=}; line=${line%\"}; line=${line#\"}; line=${line%\'}; line=${line#\'}
  print -rn -- "$line"
}

load_token() {
  [[ -f $TOKEN_FILE ]] || { echo "token file not found: $TOKEN_FILE (see README: claude setup-token)" >&2; exit 2; }
  local mode; mode=$(stat -f %Lp "$TOKEN_FILE")
  [[ $mode == 600 ]] || { echo "token file must be mode 600 (is $mode): chmod 600 $TOKEN_FILE" >&2; exit 2; }
  OAUTH=$(read_var "$TOKEN_FILE" CLAUDE_CODE_OAUTH_TOKEN)
  # Claude Code subscription tokens start with sk-ant-oat (the CLI's own marker). Anything else,
  # an API key in particular, is refused before any call is made.
  [[ $OAUTH == sk-ant-oat* && $OAUTH != *[[:space:]]* ]] || { echo "$TOKEN_FILE does not hold a subscription token (expected sk-ant-oat...). Run scripts/set_token.sh" >&2; exit 2; }
}

cd "$REPO"
case ${1:-} in
  check)
    env -i "${BASE_ENV[@]}" docker image inspect -f 'sandbox image: {{.Id}}' "$IMAGE"
    env -i "${BASE_ENV[@]}" docker image inspect -f 'proxy image:   {{.Id}}' prolong-anthropic-proxy
    print -n "Claude Code CLI in sandbox: "
    env -i "${BASE_ENV[@]}" docker run --rm --network none "$IMAGE" --version
    print "harness commit: $(cat UPSTREAM_COMMIT)  prompt from Strands commit: $(cat STRANDS_PROMPT_COMMIT)"
    if [[ -f $TOKEN_FILE ]]; then load_token; print "token file: present, mode 600, format ok"
    else print "token file: MISSING ($TOKEN_FILE)"; fi
    print "model: $MODEL  effort: $EFFORT" ;;
  smoke)
    # One short reply through the same sandbox image, network path and auth a run uses.
    load_token
    env -i "${BASE_ENV[@]}" .venv/bin/python -c 'from prolong_agent.utils import sandbox_net as s
s.ensure_secure_network("prolong-anthropic-proxy", "prolong-anthropic-proxy", "docker/anthropic-proxy")'
    P=http://prolong-anthropic-proxy:3128
    exec env -i "${BASE_ENV[@]}" CLAUDE_CODE_OAUTH_TOKEN="$OAUTH" docker run --rm -i --network prolong-internal \
      --user 1000:1000 --cap-drop=ALL --security-opt=no-new-privileges:true --tmpfs /tmp:rw,nosuid,size=64m \
      -e HOME=/home/sandbox -e DISABLE_AUTOUPDATER=1 -e CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
      -e HTTP_PROXY=$P -e HTTPS_PROXY=$P -e http_proxy=$P -e https_proxy=$P -e CLAUDE_CODE_OAUTH_TOKEN \
      "$IMAGE" -p "Reply with the single word: ready" --model "$MODEL" --effort low --max-turns 1 \
      --output-format json --disallowedTools "Bash,Read,Write,Edit,Grep,Glob,WebSearch,WebFetch,Agent,Task" ;;
  run)
    NAME=${2:?run name}
    load_token
    ARC_KEY=$(read_var "$ARC_ENV" ARC_API_KEY)
    exec env -i "${BASE_ENV[@]}" ARC_API_KEY="$ARC_KEY" CLAUDE_CODE_OAUTH_TOKEN="$OAUTH" \
      .venv/bin/python -m prolong_agent.agent.swarm --backend claude-code -m "$MODEL" --effort "$EFFORT" \
      --game "${GAMES:-bp35}" --max-actions "${MAX_ACTIONS:-1000}" --action-cap 20 --grid-mode ascii \
      --operation-mode "${MODE:-online}" --note "$NAME" --tags "prolong,claude-code,${MODEL},noprior-prompt" ;;
  *) echo "usage: $0 check | smoke | run <name>" >&2; exit 2 ;;
esac
