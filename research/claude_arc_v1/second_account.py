"""Check a second Claude subscription before any run uses it. No model call unless --call is given.

A second account is used through a long-lived token from `claude setup-token`, kept in a private file
outside the repository and named by ARC_CLAUDE_TOKEN_FILE (see backends.subscription_token). This asks the
CLI who it is, once with the machine's signed-in subscription and once with the token, in the same narrow
environment the harness gives the CLI. It prints no account name, e-mail, organisation or token.

    second_account.py <token file>            who answers with and without the token
    second_account.py <token file> --call     the same, then one short model call with the token
    second_account.py <token file> --save     first ask for the token at a hidden prompt and write the file
                                              (run this one yourself, in a terminal), then check it

Usage (project environment), from the repository root.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.claude_arc_v1 import backends  # noqa: E402


def status(extra):
    env = {k: os.environ[k] for k in backends.CLI_ENVIRONMENT if k in os.environ}
    env.update(extra)
    done = subprocess.run(['claude', 'auth', 'status', '--json'], env=env, capture_output=True, text=True, timeout=60)
    try:
        value = json.loads(done.stdout)
    except ValueError:
        return {'readable': False, 'exit_code': done.returncode}
    who = '|'.join(str(value.get(k)) for k in ('email', 'orgId'))
    return {'readable': True, 'logged_in': value.get('loggedIn'), 'auth_method': value.get('authMethod'),
            'plan': value.get('subscriptionType'),
            # enough to tell two accounts apart, not enough to name either
            'account_fingerprint': hashlib.sha256(who.encode()).hexdigest()[:8] if value.get('email') or value.get('orgId') else None}


def save(path):
    """Ask for the token without showing it and write it where only its owner can read it."""
    import getpass
    target = Path(path).expanduser()
    token = getpass.getpass('Paste the token and press Return (it will not be shown): ').strip()
    if not token or any(ch.isspace() for ch in token) or len(token) < 40:
        raise SystemExit('That does not look like one token (%d characters%s). Nothing was written.'
                         % (len(token), ', with spaces in it' if any(ch.isspace() for ch in token) else ''))
    target.parent.mkdir(parents=True, exist_ok=True)
    handle = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(handle, 'w') as out:
        out.write(token + '\n')
    os.chmod(target, 0o600)
    print('saved %d characters to %s' % (len(token), target))


def main(path, call):
    token, name = backends.subscription_token({backends.TOKEN_FILE_VARIABLE: path})
    first, second = status({}), status({backends.TOKEN_VARIABLE: token})
    print('signed-in subscription:', json.dumps(first))
    print('with the token file %s:' % name, json.dumps(second))
    uses_token = second.get('auth_method') == 'oauth_token'
    both_known = first.get('account_fingerprint') and second.get('account_fingerprint')
    print('the CLI uses the token:', uses_token)
    print('a different account from the signed-in one:',
          first['account_fingerprint'] != second['account_fingerprint'] if both_known else 'cannot tell from the status output')
    if call:
        env = {k: os.environ[k] for k in backends.CLI_ENVIRONMENT if k in os.environ}
        env[backends.TOKEN_VARIABLE] = token
        env['DISABLE_AUTOUPDATER'] = '1'
        done = subprocess.run(['claude', '-p', '--model', 'claude-opus-5-5', '--output-format', 'json', '--tools', '',
                               '--no-session-persistence', '--setting-sources', '', '--strict-mcp-config',
                               '--disable-slash-commands'],
                              input='Reply with the single word: ready', env=env, capture_output=True, text=True, timeout=180)
        try:
            value = json.loads(done.stdout)
            print('one call with the token:', json.dumps({'is_error': value.get('is_error'), 'subtype': value.get('subtype'),
                                                         'result': str(value.get('result'))[:80],
                                                         'models': sorted((value.get('modelUsage') or {}))}))
        except ValueError:
            print('one call with the token: no JSON result, exit code', done.returncode)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    if '--save' in sys.argv[2:]:
        save(sys.argv[1])
    main(sys.argv[1], '--call' in sys.argv[2:])
