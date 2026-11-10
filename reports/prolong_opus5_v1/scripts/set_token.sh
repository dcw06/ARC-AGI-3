#!/bin/zsh
# Save the Claude Code subscription token for run_prolong.sh. Run this yourself in a terminal.
# The token is read with hidden input, checked, and written with mode 600. It is never echoed.
#   1) claude setup-token        (approve in the browser, then copy the token it prints)
#   2) scripts/set_token.sh      (paste when asked)
set -euo pipefail
F=${PROLONG_TOKEN_FILE:-$HOME/.config/prolong/claude_oauth.env}
read -s "TOK?Paste the token printed by 'claude setup-token', then press Enter: "; print
TOK=${TOK//[[:space:]]/}
if [[ $TOK != sk-ant-oat* ]]; then
  print -u2 "Not saved: this is not a subscription token (it should start with sk-ant-oat; got ${#TOK} characters of something else)."
  print -u2 "An API key will not work here. Copy the token from the 'claude setup-token' output and run this again."
  exit 2
fi
mkdir -p "${F:h}"; umask 077
print -r -- "CLAUDE_CODE_OAUTH_TOKEN=$TOK" > "$F"; chmod 600 "$F"; unset TOK
print "Saved to $F (mode 600)."
