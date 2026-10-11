"""Derive the feedback-action v1 live runner from the reviewed action-effect-history v1 closed-loop stack.

The action-effect-history v1 files ran live as attempt aeh1-4c75150a (review r3) and are reused, not edited. Each
derived file is its source with the global renames below and that file's own substitutions, each required to match an
exact number of times; a block substitution replaces the text between two anchors that must each occur exactly once.
Any remaining action-effect-history name fails the derivation. `--check` reports drift (a derived file that differs
from what the derivation produces now).

Derived: research/feedback_action_v1/live/{runner,engine,evidence,service}.py, the launch harness
research/feedback_action_v1/live/{worker,host,supervisor,monitor,resources}.py (successor runtime v1), and
scripts/{feedback_action_v1_launch,evaluate_feedback_action_v1}.py.
Hand-written (not derived): research/feedback_action_v1/live/{policy,fake_server,owner_gates,authority,rehearsal,
runtime}.py, protocol.json, runtime.json and owner_gates.json; the observation pipeline is reused unchanged via
action-effect-history v1's `contract.observation_payload`. The gate, notebook and launch accounting are derived from
the verified runtime by research/feedback_action_v1/derive_runtime.py.

Runtime substitutions in the harness replace only runtime bindings (installation, model mount and artifact, server
command and ownership, image and interpreter checks, session binding); the experiment's prompts, arms, schemas,
seeds, schedule, scoring and stop rules are not touched here.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BANNER = '# Derived from {source} by research/feedback_action_v1/derive.py; edit the derivation, not this file.\n'
GLOBAL = (('research.action_effect_history_v1', 'research.feedback_action_v1.live'),
          ('action_effect_history_run_v1', 'feedback_action_run_v1'),
          ('action_effect_history_evidence_v1', 'feedback_action_evidence_v1'),
          ('action-effect-history-v1', 'feedback-action-v1'),
          ('action_effect_history_v1', 'feedback_action_v1_live'))

RUNNER = (
    ('Two-block action-effect-history comparison runner (CPU-rehearsable; no launch authority here).',
     'Feedback-action v1 comparison runner, one block per session (CPU-rehearsable; no launch authority here).', 1),
    ('twelve isolated episodes,', 'six isolated episodes per session (one block),', 1),
    ('from research.action_effect_v1.records import effect_record, EffectHistory\n'
     'from research.feedback_action_v1.live.contract import policy_request\n',
     'from research.feedback_action_v1.live.policy import EpisodePolicy, raw_transition\n', 1),
    ("TERMINAL_EPISODE = ('action_cap', 'win', 'game_over', 'invalid_output', 'dispatch_failure')",
     "TERMINAL_EPISODE = ('action_cap', 'decision_cap', 'win', 'game_over', 'dispatch_failure')"
     "  # an invalid output never ends an episode", 1),
    ('def parse_action(raw, legal):\n'
     '    from certification.phase4_transient_v2.action_contract import validate_action\n'
     "    return validate_action(raw, legal)['action']\n",
     'def parse_action(raw, legal, request):\n'
     '    """The adapter\'s parse for the request\'s arm; both arms share the frozen action validator."""\n'
     '    from research.feedback_action_v1.live.policy import parse_action as arm_parse\n'
     '    return arm_parse(raw, legal, request)\n', 1),
    ('            action = parse_action(raw, obs.available_actions)\n',
     '            action = parse_action(raw, obs.available_actions, request)\n', 1),
    ("            history = EffectHistory(limit=16)  # isolated per episode and arm\n"
     "            for step_index in range(limits['actions_per_episode']):\n"
     "                check()\n",
     "            policy = EpisodePolicy(arm, episode_id, seed=limits['request_seed'])  # isolated per episode and arm\n"
     "            episode['model_statements'] = policy.statements\n"
     "            step_index = 0\n"
     "            while True:\n"
     "                check()\n", 1),
    ("                request = policy_request(runtime, arm, history if arm == 'history' else None, seed=limits['request_seed'])\n"
     "                action = call(episode, request, obs)\n"
     "                if action is None:\n"
     "                    episode['stop_reason'] = 'invalid_output'\n"
     "                    break\n",
     "                if step_index >= limits['actions_per_episode']:\n"
     "                    episode['stop_reason'] = 'action_cap'\n"
     "                    break\n"
     "                if len(episode['calls']) >= limits['decision_calls_per_episode']:\n"
     "                    episode['stop_reason'] = 'decision_cap'  # everything retained; the schedule continues\n"
     "                    break\n"
     "                request = policy.request(runtime, obs)\n"
     "                action = call(episode, request, obs)\n"
     "                policy.decided(episode['calls'][-1], obs)\n"
     "                if action is None:\n"
     "                    persist(episode)\n"
     "                    continue  # an invalid output consumes a call, never an action\n", 1),
    ("                record = effect_record(step['before'], action, outcome)\n"
     "                entry = history.append(record)\n"
     "                step.update(status=outcome['status'], effect_record=record, history_entry=entry, returned_at=now(),\n"
     "                            after=outcome.get('post'))\n",
     "                raw = raw_transition(episode_id, step_index, step['before'], action, outcome)\n"
     "                record = policy.dispatched(raw)\n"
     "                step.update(status=outcome['status'], raw_transition=raw, record_id=record['identity']['record_id'],\n"
     "                            returned_at=now(), after=outcome.get('post'))\n", 1),
    ("                obs = post\n"
     "            else:\n"
     "                # The cap was reached; a terminal state produced by the last action takes precedence.\n"
     "                episode['stop_reason'] = {'WIN': 'win', 'GAME_OVER': 'game_over'}.get(obs.state.value, 'action_cap')\n",
     "                obs = post\n"
     "                step_index += 1  # terminal states are checked before the caps at the top of the loop\n", 1),
    # ---- online session-abort rules (protocol v2 §10 F2a and F5; review finding P1 on e887e78)
    ('import hashlib\nimport json\n', 'from fractions import Fraction\nimport hashlib\nimport json\n', 1),
    ('class DispatchRejected(Exception):\n'
     '    """The request was refused before reaching the game (definitely not applied)."""\n',
     'class DispatchRejected(Exception):\n'
     '    """The request was refused before reaching the game (definitely not applied)."""\n'
     '\n\n'
     'class SessionAbort(Exception):\n'
     '    """A session-abort rule fired (protocol v2 §10: F2a invalid outputs, F5 dispatch failures). The session stops\n'
     '    at once: no further call, dispatch or episode; partial evidence is kept; the run is never complete."""\n'
     '\n'
     '    def __init__(self, rule, counts):\n'
     '        super().__init__(rule)\n'
     "        self.rule, self.record = rule, {'rule': rule, **counts}\n", 1),
    ("              'pairs': [], 'episodes': [], 'calls': 0, 'dispatches': 0, 'prompt_tokens': 0, 'completion_tokens': 0}\n",
     "              'pairs': [], 'episodes': [], 'calls': 0, 'dispatches': 0, 'prompt_tokens': 0, 'completion_tokens': 0,\n"
     "              'abort': None}\n"
     "    online = {'arm_calls': {}, 'arm_invalid': {}, 'dispatched': 0, 'dispatch_failures': 0}  # session-abort counters\n",
     1),
    ('    def call(episode, request, obs):\n',
     '    def abort_check_call(episode, invalid):\n'
     '        """F2a, online after every policy call: per arm, over that arm\'s first `invalid_output_calls` calls in this\n'
     '        session; abort at the call that makes invalid outputs exceed `invalid_output_rate` of that window (then the\n'
     '        window\'s rate is certain to exceed it). Calls after the window never count."""\n'
     "        rule = limits['session_abort']\n"
     "        arm, window = episode['arm'], rule['invalid_output_calls']\n"
     "        n = online['arm_calls'][arm] = online['arm_calls'].get(arm, 0) + 1\n"
     '        if invalid and n <= window:\n'
     "            online['arm_invalid'][arm] = online['arm_invalid'].get(arm, 0) + 1\n"
     "        bad = online['arm_invalid'].get(arm, 0)\n"
     "        if bad > Fraction(rule['invalid_output_rate']) * window:\n"
     "            raise SessionAbort('F2a_invalid_outputs', {\n"
     "                'arm': arm, 'invalid_outputs_in_window': bad, 'arm_calls': n, 'window_calls': window,\n"
     "                'threshold_rate': rule['invalid_output_rate'], 'episode_id': episode['episode_id']})\n"
     '\n'
     '    def abort_check_dispatch(episode, outcome):\n'
     '        """F5, online after every dispatch: the whole session (both arms); abort when failed plus unknown dispatches\n'
     '        exceed `dispatch_failure_rate` of the dispatches so far."""\n'
     "        rule = limits['session_abort']\n"
     "        online['dispatched'] += 1\n"
     "        if outcome['status'] != 'acknowledged':\n"
     "            online['dispatch_failures'] += 1\n"
     "        floor = rule.get('dispatch_denominator_floor', 0)  # 0 unless the owner gate records the floor option\n"
     "        if online['dispatch_failures'] > Fraction(rule['dispatch_failure_rate']) * max(online['dispatched'], floor):\n"
     "            raise SessionAbort('F5_dispatch_failures', {\n"
     "                'dispatch_failures': online['dispatch_failures'], 'dispatched': online['dispatched'],\n"
     "                'threshold_rate': rule['dispatch_failure_rate'], 'denominator_floor': floor,\n"
     "                'episode_id': episode['episode_id']})\n"
     '\n'
     '    def call(episode, request, obs):\n', 1),
    ("            row.update(status='invalid_output', error=str(exc)[:200])\n"
     "            persist(episode)\n"
     "            return None\n",
     "            row.update(status='invalid_output', error=str(exc)[:200])\n"
     "            persist(episode)\n"
     "            abort_check_call(episode, True)\n"
     "            return None\n", 1),
    ("        row['status'] = 'valid'\n"
     "        persist(episode)\n"
     "        return action\n",
     "        row['status'] = 'valid'\n"
     "        persist(episode)\n"
     "        abort_check_call(episode, False)\n"
     "        return action\n", 1),
    ("                persist(episode)\n"
     "                if outcome['status'] != 'acknowledged':\n",
     "                persist(episode)\n"
     "                abort_check_dispatch(episode, outcome)\n"
     "                if outcome['status'] != 'acknowledged':\n", 1),
    ("        except TechnicalFailure as exc:\n"
     "            episode.update(status='technical_failure', stop_reason='technical_failure', error=str(exc)[:200])\n"
     "            raise\n",
     "        except SessionAbort as exc:\n"
     "            episode.update(status='aborted', stop_reason='session_abort', abort=exc.record)\n"
     "            raise\n"
     "        except TechnicalFailure as exc:\n"
     "            episode.update(status='technical_failure', stop_reason='technical_failure', error=str(exc)[:200])\n"
     "            raise\n", 1),
    ("    except TechnicalFailure as exc:\n"
     "        report.update(status='technical_failure', error=str(exc)[:200])\n",
     "    except SessionAbort as exc:  # never complete; later pairs are recorded as not started\n"
     "        report.update(status='aborted', error='session abort: ' + exc.rule, abort=exc.record)\n"
     "        if report['pairs'] and report['pairs'][-1].get('status') == 'running':\n"
     "            report['pairs'][-1]['status'] = 'interrupted'\n"
     "    except TechnicalFailure as exc:\n"
     "        report.update(status='technical_failure', error=str(exc)[:200])\n", 1),
)

SERVICE_VALIDATE = (
    'def validate_policy_request(request):\n'
    '    """Exact frozen request contract for both arms (feedback-action v1: research/feedback_action_v1/live/policy.py);\n'
    '    raises ValueError before any transport."""\n'
    '    from research.feedback_action_v1.live.policy import validate_policy_request as validate\n'
    '    return validate(request)\n')

SERVICE = (
    ('MAX_POLICY_CALLS = 144', 'MAX_POLICY_CALLS = 192  # one session: 6 episodes x 32 decision calls', 1),
    ('"""One canary, then at most 144 contract-checked policy calls; raw evidence returned for retention."""',
     '"""One canary, then at most 192 contract-checked policy calls; raw evidence returned for retention."""', 1),
    ("raise ValueError('policy call ceiling (144)')", "raise ValueError('policy call ceiling (192)')", 1),
    (('def validate_policy_request(request):\n', '\n\nclass HistoryModelService'), SERVICE_VALIDATE, 'block'),
)

# ---- the launch harness (successor runtime v1) -------------------------------------------------------------------
# Renames shared by every harness file, after GLOBAL: the rehearsal opt-in variables become this study's own.
HARNESS = (('AEH_REHEARSAL', 'FA1_REHEARSAL'),)
# The live harness files sit one directory deeper than their sources, so the repository root is one more parent up.
DEEPER = (('ROOT = Path(__file__).resolve().parents[2]\n',
           'ROOT = Path(__file__).resolve().parents[3]  # one directory deeper than the source\n', 1),)

WORKER = (
    ('"""Game worker (game interpreter): model host, bridge admission, and the comparison run."""',
     '"""Game worker (game interpreter): model host, bridge admission, and one session\'s comparison run (successor\n'
     'runtime v1: the session comes from the reserved execution lock)."""', 1),
    ("FAULTS = ('none', 'model_startup', 'transport', 'slow', 'invalid_history', 'storage', 'surviving_child')",
     "FAULTS = ('none', 'model_startup', 'transport', 'slow', 'always_invalid', 'truncated_candidate', 'storage',\n"
     "          'surviving_child', 'dispatch_failed', 'dispatch_unknown')", 1),
    ("def run_worker(output, scratch, environments, model_python, *, deadline, mode, fault='none'):\n"
     "    gate(mode)  # before model subprocess, game import or GPU access\n",
     "def run_worker(output, scratch, environments, model_python, *, deadline, mode, session, fault='none'):\n"
     "    execution = gate(mode)  # before model subprocess, game import or GPU access\n"
     "    if session not in (1, 2) or (mode == 'live' and execution.get('session') != session):\n"
     "        raise PermissionError('the session must be the one the execution lock reserves')\n", 1),
    ("    host_fault = fault if fault in ('model_startup', 'transport', 'slow', 'invalid_history') else 'none'\n",
     "    from .rehearsal import HOST_FAULTS, adapter_for\n"
     "    host_fault = fault if fault in HOST_FAULTS else 'none'\n", 1),
    ("        from .runner import run\n"
     "        report = run(output / 'worker/run', ProxyService(proxy),\n"
     "                     lambda game_id, arm, episode_id: DevelopmentAdapter(game_id, arm, episode_id, games,\n"
     "                                                                         scratch / 'recordings'),\n"
     "                     deadline_seconds=max(.01, deadline - time.monotonic()), cancel=cancel,\n",
     "        from .policy import session_spec\n"
     "        from .runner import run\n"
     "        report = run(output / 'worker/run', ProxyService(proxy),\n"
     "                     lambda game_id, arm, episode_id: adapter_for(fault, DevelopmentAdapter(\n"
     "                         game_id, arm, episode_id, games, scratch / 'recordings')),  # live: fault is 'none'\n"
     "                     deadline_seconds=max(.01, deadline - time.monotonic()), cancel=cancel,\n"
     "                     spec=session_spec(session),\n", 1),
    ("            host.wait(timeout=5)\n",
     "            host.wait(timeout=55)  # the host first stops the server's own group (30 s TERM + 10 s KILL grace)\n",
     1),
    ("                                          'dispatches': report['dispatches'], 'host_pid': host.pid, 'mode': mode})\n",
     "                                          'dispatches': report['dispatches'], 'host_pid': host.pid, 'mode': mode,\n"
     "                                          'session': session, 'abort': report.get('abort')})\n", 1),
    ("    parser.add_argument('--fault', default='none')\n"
     "    args = parser.parse_args()\n"
     "    gate(args.mode)\n"
     "    run_worker(args.output, args.scratch, args.environments, args.model_python, deadline=args.deadline,\n"
     "               mode=args.mode, fault=args.fault)\n",
     "    parser.add_argument('--session', type=int, required=True)\n"
     "    parser.add_argument('--fault', default='none')\n"
     "    args = parser.parse_args()\n"
     "    gate(args.mode)\n"
     "    run_worker(args.output, args.scratch, args.environments, args.model_python, deadline=args.deadline,\n"
     "               mode=args.mode, session=args.session, fault=args.fault)\n", 1),
)

HOST_FACTORY = '''def pinned_model_factory(retain, deadline, _fault='none', *, evidence_root, server_log):
    """Live only: verify the pinned model snapshot and start the verified-runtime vLLM server (its own process group,
    TCP readiness, prefix caching disabled and confirmed in its log) in this model interpreter."""
    if time.monotonic() >= deadline:
        raise TimeoutError('model startup admission closed')
    from certification.direct_publisher_smoke_v1.host import verify_model
    from certification.direct_publisher_smoke_v1.server import ModelServer, argv_for
    from certification.phase4_integrated_v2.model_transport import OpenAICompatibleCompletionClient
    from .runtime import load, verify_cache_disabled
    runtime = load(ROOT)
    for package, expected in runtime['model_host_packages'].items():
        if importlib.metadata.version(package) != expected:
            raise ValueError('pinned model package drift: ' + package)
    store = EvidenceStore(evidence_root, 'worker')
    startup = min(deadline, time.monotonic() + runtime['lifecycle']['startup_ceiling_seconds'])

    def within():
        if time.monotonic() >= startup:
            raise TimeoutError('model verification deadline')
    artifact = verify_model(runtime['model'], within)  # the complete tree digest before any model load
    store.save('model-artifact.json', artifact)
    if {'tree_sha256': artifact['tree_sha256']} != expected_artifact(ROOT):
        raise ValueError('verified model artifact differs from the reviewed snapshot')
    cfg = runtime['server']
    server = ModelServer(argv_for(cfg, sys.executable, artifact['mounted_path'], cfg['port']), cfg['env'], server_log,
                         cfg['host'], cfg['port'])
    owner = ServerOwner(server, cfg, store, server_log, evidence_root)
    try:
        server.start()
        store.save('model-server.json', {'pgid': server.pgid, 'pid': server.process.pid, 'argv': server.argv})
        server.wait_ready(startup)
        store.save('model-server-config.json', {'prefix_caching': verify_cache_disabled(server_log),
                                                'argv': server.argv, 'readiness': cfg['readiness']})
        client = OpenAICompatibleCompletionClient(f"http://{cfg['host']}:{cfg['port']}",
                                                  timeout_seconds=cfg['request_timeout_seconds'])
        service = HistoryModelService(artifact['mounted_path'], client.complete, retain_canary=retain)
        service.artifact = expected_artifact(ROOT)
        return service, owner
    except BaseException:
        owner.close()
        raise


class ServerOwner:
    """Stops the server's own process group (SIGTERM, then SIGKILL, verified absent) and retains its log tail."""

    def __init__(self, server, cfg, store, log, evidence_root):
        self.server, self.cfg, self.store, self.log, self.root = server, cfg, store, Path(log), evidence_root

    def close(self):
        grace, kill = self.cfg['terminate_grace_seconds'], self.cfg['kill_grace_seconds']
        receipt = self.server.stop(time.monotonic() + grace + kill + 5, grace, kill)
        self.store.save('model-server-cleanup.json', {'receipt': receipt})
        if self.log.is_file():
            with self.log.open('rb') as stream:
                stream.seek(max(0, self.log.stat().st_size - min(self.cfg['log_retained_bytes'], 1024**2)))
                tail = stream.read().decode('utf-8', errors='replace')
            EvidenceStore(self.root, 'logs').save('model-server.json', {'tail': tail})
        if not receipt['groups_absent']:
            raise RuntimeError('model server process group not verified absent')
        return receipt


'''

HOST_REHEARSAL = '''def rehearsal_factory(retain, deadline, fault='none', *, evidence_root=None, server_log=None):
    """CPU rehearsal only: scripted transport (optionally the pinned tokenizer and the pinned guided-decoding grammar);
    artifact labelled as rehearsal."""
    from .authority import rehearsal_gate
    from .fake_server import FixtureTokenizer
    from .rehearsal import rehearsal_transport
    rehearsal_gate()
    if fault == 'model_startup':
        raise TimeoutError('rehearsal model startup failure')
    transport, tokenizer = rehearsal_transport(fault)
    service = HistoryModelService('rehearsal', transport, tokenizer=tokenizer or FixtureTokenizer(),
                                  retain_canary=retain, check_versions=tokenizer is not None)
    service.artifact = {'rehearsal': 'scripted_model_not_target_evidence'}
    store = EvidenceStore(evidence_root, 'worker') if evidence_root is not None else None

    class Owner:
        def close(self):
            if store is not None:
                store.save('rehearsal-transport.json', transport.summary())
            return None
    return service, Owner()


'''

HOST = (
    ('"""Model host (model interpreter): start the model, run one canary, serve the bounded bridge."""',
     '"""Model host (model interpreter): verify the pinned model snapshot, start the verified-runtime server, run one\n'
     'canary, serve the bounded bridge (successor runtime v1)."""', 1),
    ('from dataclasses import replace\nimport importlib.metadata\nimport json\nimport math\nfrom pathlib import Path\n'
     'import time\n',
     'import functools\nimport importlib.metadata\nimport json\nimport math\nfrom pathlib import Path\nimport sys\n'
     'import time\n', 1),
    ("    from research.grounded_action_v1.artifact_contract import expected_artifact as frozen\n"
     "    return frozen(root)  # the same pinned model tree as every earlier run\n",
     "    from .runtime import expected_artifact as pinned\n"
     "    return pinned(root)  # the reviewed tree digest of the dataset-backed model snapshot (runtime.json)\n", 1),
    (("def pinned_model_factory(retain, deadline, _fault='none'):\n", 'def rehearsal_factory('), HOST_FACTORY, 'block'),
    (('def rehearsal_factory(', 'def serve_host('), HOST_REHEARSAL, 'block'),
    ("'scope': 'action_effect_history_model_host'", "'scope': 'feedback_action_v1_model_host'", 1),
    ("    if args.mode == 'live':\n"
     "        from .authority import require\n"
     "        require()  # before model import, subprocess or GPU query\n"
     "        if args.fault != 'none':\n"
     "            raise PermissionError('faults are rehearsal-only')\n"
     "        factory = pinned_model_factory\n"
     "    else:\n"
     "        factory = rehearsal_factory\n",
     "    bound = {'evidence_root': args.evidence, 'server_log': args.socket.parent / 'model-server.log'}\n"
     "    if args.mode == 'live':\n"
     "        from .authority import require\n"
     "        require()  # before model import, subprocess or GPU query\n"
     "        if args.fault != 'none':\n"
     "            raise PermissionError('faults are rehearsal-only')\n"
     "        factory = functools.partial(pinned_model_factory, **bound)\n"
     "    else:\n"
     "        factory = functools.partial(rehearsal_factory, **bound)\n", 1),
)

SUPERVISOR_SERVER = '''def stop_model_server(output, errors, report):
    """The verified-runtime server runs in its own process group. The host stops it; if the host was killed first,
    the recorded group is stopped here (SIGTERM, then SIGKILL) and verified gone. Never another group."""
    from scripts.run_grounded_action_v1_engine_local import group_exited
    record = Path(output) / 'worker/model-server.json'
    if not record.exists():
        report['model_server_group'] = {'recorded': False}
        return True
    try:
        if record.is_symlink() or record.stat().st_size > 65536:
            raise ValueError('model server record')
        pgid = json.loads(record.read_bytes()).get('pgid')
        if type(pgid) is not int or pgid <= 1 or pgid == os.getpgrp():
            raise ValueError('invalid model server group')
        signalled = []
        for sig, wait in ((signal.SIGTERM, 10), (signal.SIGKILL, 5)):
            if group_exited(pgid):
                break
            try:
                os.killpg(pgid, sig)
                signalled.append(sig.name)
            except ProcessLookupError:
                break
            until = time.monotonic() + wait
            while time.monotonic() < until and not group_exited(pgid):
                time.sleep(.1)
        exited = group_exited(pgid)
        report['model_server_group'] = {'recorded': True, 'pgid': pgid, 'signalled_by_supervisor': signalled,
                                        'exited': exited}
        return exited
    except Exception as exc:
        errors.append('model server group: ' + type(exc).__name__ + ': ' + str(exc)[:128])
        return False


def gate(mode):
'''

SUPERVISOR = (
    ('"""External ownership of the worker and monitor process groups, on one shared first-cell clock."""',
     '"""External ownership of the worker and monitor process groups and of the model server\'s own group (successor\n'
     'runtime v1), on one shared first-cell clock."""', 1),
    ('import secrets\nimport subprocess\n', 'import secrets\nimport signal\nimport subprocess\n', 1),
    ('def gate(mode):\n', SUPERVISOR_SERVER, 1),
    ("def run(output, working, game_python, model_python, environments, *, started, mode='live',\n",
     "def run(output, working, game_python, model_python, environments, *, started, session, mode='live',\n", 1),
    ("    report = {'scope': 'action_effect_history_' + mode, 'mode': mode, 'status': 'failed', 'error': None,\n",
     "    report = {'scope': 'feedback_action_v1_' + mode, 'mode': mode, 'session': session, 'status': 'failed',\n"
     "              'error': None,\n", 1),
    ("prefix='action-effect-history-'", "prefix='feedback-action-v1-'", 1),
    ("'--deadline', str(started + admission), '--mode', mode, '--fault', worker_fault],",
     "'--deadline', str(started + admission), '--mode', mode, '--session', str(session),\n"
     "                             '--fault', worker_fault],", 1),
    ("            try:\n"
     "                report['process_groups_exited'] = not cleanup_errors and all(group_exited(p.pid) for p in processes)\n",
     "            server_exited = stop_model_server(output, cleanup_errors, report)\n"
     "            try:\n"
     "                report['process_groups_exited'] = (not cleanup_errors and server_exited\n"
     "                                                   and all(group_exited(p.pid) for p in processes))\n", 1),
    ("    parser.add_argument('--fault', default='none')\n"
     "    args = parser.parse_args()\n",
     "    parser.add_argument('--session', type=int, required=True)\n"
     "    parser.add_argument('--fault', default='none')\n"
     "    args = parser.parse_args()\n", 1),
    ("                 started=args.started, mode=args.mode, internal_seconds=args.internal_seconds, fault=args.fault,\n",
     "                 started=args.started, session=args.session, mode=args.mode, internal_seconds=args.internal_seconds,\n"
     "                 fault=args.fault,\n", 1),
)

MONITOR = (
    ("SCOPES = {'live': 'action_effect_history_live_resource_monitor',\n"
     "          'rehearsal': 'action_effect_history_rehearsal_monitor_injected_gpu'}",
     "SCOPES = {'live': 'feedback_action_v1_live_resource_monitor',\n"
     "          'rehearsal': 'feedback_action_v1_rehearsal_monitor_injected_gpu'}", 1),
)

RESOURCES = (
    ("'scope': 'action_effect_history_independent_gpu_cleanup'", "'scope': 'feedback_action_v1_independent_gpu_cleanup'", 1),
)

LAUNCH_INSTALL = '''def install_pair(root, rootdir, output, bundle, mount, deadline):
    """Both interpreters through the verified install (runtime.prepare), every command in an owned process group.
    The receipt and the bounded install logs are retained before anything else runs, on success or failure."""
    import base64
    import gzip
    from certification.direct_publisher_smoke_v1.install import InstallationProcesses
    from research.feedback_action_v1.live.runtime import prepare
    processes = InstallationProcesses(30, 10)
    receipt = {'passed': False}
    try:
        return prepare(root, rootdir, bundle, mount, deadline, processes, receipt=receipt)
    finally:
        cleanup = processes.stop(time.monotonic() + 60)
        receipt['process_cleanup'] = {k: cleanup[k] for k in ('groups_absent', 'interrupted', 'error')}
        for role in ('model', 'game'):
            log = Path(rootdir) / f'{role}-install.log'
            if log.is_file():
                data = log.read_bytes()[-2 * 1024**2:]
                EvidenceStore(output, 'logs').save(f'install-{role}.json', {
                    'encoding': 'gzip-base64', 'data': base64.b64encode(gzip.compress(data)).decode()})
        EvidenceStore(output, 'control').save('installation.json', receipt)
        if not cleanup['groups_absent'] or cleanup['error']:
            raise RuntimeError('installation process groups not verified absent')


def run(output, working, *, started'''

LAUNCH_SUPERVISOR = '''def run_supervisor(output, working, game_python, model_python, games, *, started, mode, internal_seconds,
                   session, fault='none', root=ROOT, spawn=subprocess.Popen):
    """Protect startup ownership and retain cleanup even if startup or logging is interrupted."""
    from certification.direct_publisher_smoke_v1.server import defer_startup_signals
    root, output = Path(root), Path(output)
    log, control = EvidenceStore(output, 'logs'), EvidenceStore(output, 'control')
    errors, retained, cleanup = [], bytearray(), {}
    process, thread, ownership = None, None, 'never_spawned'
    command = [str(game_python), '-m', 'research.feedback_action_v1.live.supervisor', '--output', str(output),
               '--working', str(working), '--game-python', str(game_python), '--model-python', str(model_python),
               '--environments', str(games), '--started', str(started), '--mode', mode,
               '--internal-seconds', str(internal_seconds), '--session', str(session), '--fault', fault]
    env = dict(os.environ)
    for key in ('PYTHONHOME', 'VIRTUAL_ENV'):
        env.pop(key, None)
    if mode == 'live':
        env.pop('PYTHONPATH', None)
    else:
        env['PYTHONPATH'] = str(root)
    env['PYTHONNOUSERSITE'], env['MPLBACKEND'] = '1', 'Agg'

    def drain():
        try:
            while chunk := process.stdout.read(4096):
                if len(retained) + len(chunk) > 3 * 1024**2:
                    raise ValueError('supervisor log evidence exhausted')
                retained.extend(chunk)
                log.write('supervisor.json', bytes(retained))
        except Exception as exc:
            errors.append(type(exc).__name__ + ': ' + str(exc)[:200])
        finally:
            process.stdout.close()

    try:
        with defer_startup_signals():
            ownership = 'uncertain'  # entering Popen does not prove that no child was created
            process = spawn(command, cwd=root, env=env, start_new_session=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            # start_new_session fixes ownership to this PID, including a leader that exits early.
            cleanup[str(process.pid)] = False
            ownership = 'registered'
        thread = threading.Thread(target=drain, daemon=True)
        thread.start()
        while process.poll() is None:
            if errors:
                raise RuntimeError('supervisor log retention failed: ' + errors[0])
            if time.monotonic() >= started + internal_seconds - 5:
                raise TimeoutError('first-cell supervisor deadline')
            time.sleep(.05)
    finally:
        # Handled signals cannot skip a kill, reap or receipt during emergency cleanup.
        with defer_startup_signals():
            if process is not None:
                groups = [process.pid]
                try:
                    groups = _owned_groups(output, process.pid)
                except BaseException as exc:
                    errors.append('ownership evidence: ' + type(exc).__name__)
                for pgid in groups:
                    try:
                        cleanup[str(pgid)] = _stop_group(pgid)
                    except BaseException as exc:
                        cleanup[str(pgid)] = type(exc).__name__ + ': ' + str(exc)[:128]
                        try:
                            os.killpg(pgid, signal.SIGKILL)
                            cleanup[str(pgid)] = _group_exited(pgid)
                        except BaseException:
                            pass
                try:
                    process.wait(timeout=5)
                except BaseException as exc:
                    errors.append('supervisor reap: ' + type(exc).__name__)
                if thread is not None and thread.ident is not None:
                    thread.join(timeout=3)
                elif process.stdout is not None:
                    process.stdout.close()
            absent = ownership == 'never_spawned' or (ownership == 'registered' and bool(cleanup)
                                                      and all(v is True for v in cleanup.values()))
            if ownership == 'uncertain':
                errors.append('spawn ownership uncertain; group absence cannot be verified')
            drained = thread is None or not thread.is_alive()
            control.save('first-cell-supervisor-cleanup.json', {
                'ownership': ownership, 'groups': cleanup, 'groups_absent': absent, 'drain_finished': drained,
                'returncode': process.returncode if process else None, 'errors': errors})
    report_path = output / 'control/outer.json'
    if report_path.is_symlink() or not report_path.is_file() or report_path.stat().st_size > 65536:
        raise RuntimeError('missing or oversized supervisor report')
    report = json.loads(report_path.read_bytes())
    report['first_cell_cleanup_verified'] = absent and drained and not errors
    return report


'''

LAUNCH = (
    ('"""First-cell lifecycle for the action-effect-history comparison (live needs separate reviewed authority)."""',
     '"""First-cell lifecycle for one feedback-action v1 session on the verified runtime (successor runtime v1; live\n'
     'needs separate reviewed authority)."""', 1),
    ("    return groups\n",
     "    server = output / 'worker/model-server.json'  # the verified-runtime server runs in its own process group\n"
     "    if server.is_file() and not server.is_symlink() and server.stat().st_size <= 65536:\n"
     "        pgid = json.loads(server.read_bytes()).get('pgid')\n"
     "        if type(pgid) is int and pgid > 1 and pgid not in groups:\n"
     "            groups.append(pgid)\n"
     "    return groups\n", 1),
    ("def run_supervisor(output, working, game_python, model_python, games, *, started, mode, internal_seconds,\n"
     "                   fault='none', root=ROOT, spawn=subprocess.Popen):\n",
     "def run_supervisor(output, working, game_python, model_python, games, *, started, mode, internal_seconds,\n"
     "                   session, fault='none', root=ROOT, spawn=subprocess.Popen):\n", 1),
    ("'--internal-seconds', str(internal_seconds), '--fault', fault]",
     "'--internal-seconds', str(internal_seconds), '--session', str(session), '--fault', fault]", 1),
    ("def run(output, working, *, started", LAUNCH_INSTALL, 1),
    ("root=ROOT, mode='live', internal_seconds=3300, fault='none'):\n",
     "root=ROOT, mode='live', internal_seconds=3300, fault='none', session=None):\n", 1),
    ("    if mode == 'live':\n"
     "        from research.feedback_action_v1.live.authority import consume_runtime, require\n"
     "        require(root)\n"
     "        if fault != 'none' or internal_seconds != 3300:\n"
     "            raise PermissionError('live mode uses the frozen lifecycle and no faults')\n"
     "        if not 0 <= time.monotonic() - started < 450:\n"
     "            raise TimeoutError('first-cell installation deadline')\n"
     "        consume_runtime(working, root)  # one attempt is consumed before installation\n"
     "    else:\n"
     "        from research.feedback_action_v1.live.authority import rehearsal_gate\n"
     "        rehearsal_gate()\n",
     "    from research.feedback_action_v1.live.runtime import load as load_runtime\n"
     "    runtime = load_runtime(root)\n"
     "    installation_seconds = runtime['lifecycle']['installation_seconds']\n"
     "    if mode == 'live':\n"
     "        from research.feedback_action_v1.live.authority import consume_runtime, require\n"
     "        execution = require(root)\n"
     "        if session is not None and session != execution['session']:\n"
     "            raise PermissionError('the session differs from the reserved execution lock')\n"
     "        session = execution['session']\n"
     "        if fault != 'none' or internal_seconds != runtime['lifecycle']['internal_seconds']:\n"
     "            raise PermissionError('live mode uses the frozen lifecycle and no faults')\n"
     "        if not 0 <= time.monotonic() - started < installation_seconds:\n"
     "            raise TimeoutError('first-cell installation deadline')\n"
     "        consume_runtime(working, root)  # one attempt is consumed before installation\n"
     "    else:\n"
     "        from research.feedback_action_v1.live.authority import rehearsal_gate\n"
     "        rehearsal_gate()\n"
     "        execution, session = None, session or 1\n", 1),
    (("        if mode == 'live':\n            manifest = ", "        else:\n            games = Path("),
     "        if mode == 'live':\n"
     "            from certification.direct_publisher_smoke_v1.host import dataset_mount, host_facts\n"
     "            from research.feedback_action_v1.live.runtime import competition_mount\n"
     "            manifest = json.loads((root / runtime['game']['manifest']).read_bytes())\n"
     "            control.save('host.json', host_facts(runtime['runtime']))  # CPython 3.12, x86_64, glibc >= 2.34\n"
     "            bundle = dataset_mount(runtime['dataset']['ref'], runtime['dataset']['version'])\n"
     "            mount = competition_mount(runtime['competition']['ref'])\n"
     "            with tempfile.TemporaryDirectory(prefix='feedback-action-v1-dependencies-') as folder:\n"
     "                from certification.phase4_integrated_v2.game_assets import stage_games\n"
     "                from certification.phase4_integrated_v2.dependencies import freeze, thaw\n"
     "                rootdir = Path(folder)\n"
     "                games = stage_games(mount / runtime['competition']['environment_files'], rootdir / 'games',\n"
     "                                    manifest)\n"
     "                pair = install_pair(root, rootdir, output, bundle, mount, started + installation_seconds)\n"
     "                try:\n"
     "                    freeze(rootdir)\n"
     "                    report = run_supervisor(output, working, pair['game'], pair['model'], games, started=started,\n"
     "                                            mode=mode, internal_seconds=internal_seconds, root=root,\n"
     "                                            session=session)\n"
     "                finally:\n"
     "                    thaw(rootdir)\n", 'block'),
    ("            report = run_supervisor(output, working, sys.executable, sys.executable, games,\n"
     "                                    started=started, mode=mode, internal_seconds=internal_seconds, fault=fault, root=root)\n",
     "            game_python = os.environ.get('FA1_REHEARSAL_GAME_PYTHON', sys.executable)\n"
     "            model_python = os.environ.get('FA1_REHEARSAL_MODEL_PYTHON', sys.executable)\n"
     "            report = run_supervisor(output, working, game_python, model_python, games, started=started, mode=mode,\n"
     "                                    internal_seconds=internal_seconds, fault=fault, root=root, session=session)\n",
     1),
    ("    receipt = {'scope': 'action_effect_history_first_cell', 'mode': mode, 'elapsed_seconds': elapsed, 'error': error,\n",
     "    receipt = {'scope': 'feedback_action_v1_first_cell', 'mode': mode, 'session': session,\n"
     "               'attempt_id': execution['attempt_id'] if execution else None,\n"
     "               'elapsed_seconds': elapsed, 'error': error,\n", 1),
    ("                      fault=os.environ.get('FA1_REHEARSAL_FAULT', 'none'))\n",
     "                      fault=os.environ.get('FA1_REHEARSAL_FAULT', 'none'),\n"
     "                      session=int(os.environ.get('FA1_REHEARSAL_SESSION', '1')))\n", 1),
    (('def run_supervisor(', 'def install_pair('), LAUNCH_SUPERVISOR, 'block'),
    ("fault='none', session=None):\n", "fault='none', session=None, source_cleanup=None):\n", 1),
    ("    except Exception as exc:\n        error = type(exc).__name__ + ': ' + str(exc)[:256]\n", "    except BaseException as exc:\n        error = type(exc).__name__ + ': ' + str(exc)[:256]\n", 1),
    ("    control.save('notebook-cost.json', receipt)\n    return receipt\n", "    # First retain a provisional receipt; a partial write can never certify completion.\n    receipt.update(lifecycle_finalized=False, extracted_source_removed=None)\n    control.save('notebook-cost.json', receipt)\n    try:\n        if source_cleanup is not None:\n            source_cleanup()\n            receipt['extracted_source_removed'] = True\n    except BaseException as exc:\n        receipt['extracted_source_removed'] = False\n        receipt['error'] = receipt['error'] or 'source cleanup: ' + type(exc).__name__\n    receipt['elapsed_seconds'] = time.monotonic() - started\n    if receipt['elapsed_seconds'] >= internal_seconds:\n        receipt['error'] = receipt['error'] or 'first-cell hard deadline exceeded during finalization'\n    receipt['lifecycle_finalized'] = True\n    control.save('notebook-cost.json', receipt)\n    # The certification write is charged too. Emergency failure recording is allowed after an overrun.\n    finalized = time.monotonic() - started\n    receipt['elapsed_seconds'] = finalized\n    if finalized >= internal_seconds:\n        receipt['error'] = receipt['error'] or 'first-cell hard deadline exceeded during final evidence write'\n        control.save('notebook-cost.json', receipt)\n    return receipt\n", 1),
    ("    if mode == 'live':\n        from research.feedback_action_v1.live.authority import require\n        require(source)\n", "    import shutil\n    remove_source = lambda: shutil.rmtree(source)\n    if mode == 'live':\n        from research.feedback_action_v1.live.authority import require\n        require(source)\n", 1),
    ("started=started, root=source, mode='live')", "started=started, root=source, mode='live', source_cleanup=remove_source)", 1),
    ("session=int(os.environ.get('FA1_REHEARSAL_SESSION', '1')))\n", "session=int(os.environ.get('FA1_REHEARSAL_SESSION', '1')), source_cleanup=remove_source)\n", 1),

)

EVALUATE_RUNTIME = '''    if mode == 'live':  # successor-runtime evidence: installation, the model server's own group, prefix caching
        try:
            installation = read(output, 'control/installation.json')
            server_config = read(output, 'worker/model-server-config.json')
            server_group = outer.get('model_server_group') or {}
            host_receipt = (read(output, 'worker/model-server-cleanup.json')['receipt']
                            if (output / 'worker/model-server-cleanup.json').is_file() else None)
            if (installation.get('passed') is not True
                    or (installation.get('process_cleanup') or {}).get('groups_absent') is not True
                    or server_config['prefix_caching'].get('disabled') is not True
                    or server_group.get('recorded') is not True or server_group.get('exited') is not True
                    or (host_receipt is not None and host_receipt.get('groups_absent') is not True)):
                raise ValueError('installation, model-server group cleanup or prefix caching not verified')
        except Exception as exc:
            lifecycle.append('successor runtime evidence: ' + type(exc).__name__ + ': ' + str(exc)[:120])
    # Deadlines are judged against the frozen limit, never a limit claimed by the report itself.
'''

EVALUATE = (
    ("    trees = cost.get('dependency_trees_removed')\n", "    if (cost.get('lifecycle_finalized') is not True\n            or (mode == 'live' and cost.get('extracted_source_removed') is not True)):\n        lifecycle.append('lifecycle finalization/source removal not certified')\n    trees = cost.get('dependency_trees_removed')\n", 1),
    ("            'exact_provider_billed_seconds': None, 'phase4_complete': False}\n",
     "            'exact_provider_billed_seconds': None, 'phase4_complete': False,\n"
     "            'session': outer.get('session'), 'attempt_id': cost.get('attempt_id')}\n", 1),
    ('"""Independent evaluation of a downloaded (or rehearsal) output tree. Read-only; no model or GPU."""',
     '"""Independent evaluation of one downloaded (or rehearsal) feedback-action v1 session output tree. Read-only; no\n'
     'model or GPU. Lifecycle checks are derived from action-effect history v1; the study evaluation is\n'
     'research/feedback_action_v1/live_evaluation.py (verified manifest, verify_history, carried statements, every\n'
     'rate, failure rules F1-F6)."""', 1),
    ('    from research.feedback_action_v1.live.evaluate import evaluate\n',
     '    from research.feedback_action_v1.live_evaluation import evaluate_session\n', 1),
    ('    # Deadlines are judged against the frozen limit, never a limit claimed by the report itself.\n',
     EVALUATE_RUNTIME, 1),
    ('        result = evaluate(run)\n',
     "        result = evaluate_session(run, session=outer.get('session'), mode=mode, output=output,\n"
     "                                  lifecycle_errors=lifecycle)\n", 1),
    ("        summary.update({k: value['evaluation'][k] for k in ('replay_passed', 'behaviour_result', 'solving_result',\n"
     "                                                            'reliability_by_arm', 'arm_specific_reliability_differences')})\n",
     "        summary.update({k: value['evaluation'][k] for k in ('replay_passed', 'session', 'failure_rules',\n"
     "                                                            'session_2_permitted', 'technical_validity')})\n", 1),
)

DERIVED = {
    'research/feedback_action_v1/live/runner.py': ('research/action_effect_history_v1/runner.py', RUNNER),
    'research/feedback_action_v1/live/engine.py': ('research/action_effect_history_v1/engine.py', ()),
    'research/feedback_action_v1/live/evidence.py': ('research/action_effect_history_v1/evidence.py', ()),
    'research/feedback_action_v1/live/service.py': ('research/action_effect_history_v1/service.py', SERVICE),
    'research/feedback_action_v1/live/worker.py': ('research/action_effect_history_v1/worker.py', HARNESS + DEEPER + WORKER),
    'research/feedback_action_v1/live/host.py': ('research/action_effect_history_v1/host.py', HARNESS + DEEPER + HOST),
    'research/feedback_action_v1/live/supervisor.py': ('research/action_effect_history_v1/supervisor.py',
                                                       HARNESS + DEEPER + SUPERVISOR),
    'research/feedback_action_v1/live/monitor.py': ('research/action_effect_history_v1/monitor.py', HARNESS + MONITOR),
    'research/feedback_action_v1/live/resources.py': ('research/action_effect_history_v1/resources.py',
                                                      HARNESS + RESOURCES),
    'scripts/feedback_action_v1_launch.py': ('scripts/action_effect_history_v1_launch.py', HARNESS + LAUNCH),
    'scripts/evaluate_feedback_action_v1.py': ('scripts/evaluate_action_effect_history_v1.py', HARNESS + EVALUATE),
}


def derive_one(target):
    source, substitutions = DERIVED[target]
    text = (ROOT / source).read_text(encoding='utf-8')
    for old, new in GLOBAL:
        text = text.replace(old, new)
    for item in substitutions:
        if len(item) == 2:  # a rename shared by the harness files (any number of occurrences)
            text = text.replace(*item)
            continue
        old, new, count = item
        if count == 'block':
            start, end = old
            for anchor in (start, end):
                if text.count(anchor) != 1:
                    raise ValueError(f'{target}: anchor {anchor[:50]!r} must occur once, found {text.count(anchor)}')
            i, j = text.index(start), text.index(end)
            if j <= i:
                raise ValueError(f'{target}: block anchors out of order')
            text = text[:i] + new + text[j:]
            continue
        found = text.count(old)
        if found != count:
            raise ValueError(f'{target}: expected {count} of {old[:70]!r}, found {found}')
        text = text.replace(old, new)
    if 'action_effect_history' in text or 'action-effect-history' in text or 'EffectHistory' in text or 'AEH_' in text:
        raise ValueError(f'{target}: unexpected remaining action-effect-history reference')
    return BANNER.format(source=source) + text


def derive():
    return {target: derive_one(target) for target in DERIVED}


def stale():
    return [t for t, text in derive().items()
            if not (ROOT / t).is_file() or (ROOT / t).read_text(encoding='utf-8') != text]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    if parser.parse_args().check:
        drift = stale()
        if drift:
            raise SystemExit('derived files differ from the derivation: ' + ', '.join(drift))
        print(f'{len(DERIVED)} derived files match the derivation')
        sys.exit(0)
    for target, text in derive().items():
        (ROOT / target).write_text(text, encoding='utf-8', newline='\n')
    print(f'wrote {len(DERIVED)} derived files')
