"""Deterministically derive the first Milestone E package; no network, install, GPU or reservation.

Re-running verifies rather than overwrites immutable cases and derived sources with --check.
The successful smoke controller is retained unchanged; only new scoped derivatives are written.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.control_interface_action_selection_v1 import probe as P

OLD = 'certification/direct_publisher_smoke_v1'
NEW = P.PACKAGE
SCOPE = 'control-interface-action-selection-v1'
ARCHIVE = 'evidence/phase4-closed-loop-v1-r1-completed-v1.zip'
ARCHIVE_SHA = '994dc62307777a1adf301986aa2548bb9dad84ab438963d20392736abd493f9d'
PREFIX = 'output/phase4-closed-loop-v1/worker/'
HEADER = '# Derived by scripts/build_control_interface_action_selection_v1.py; edit the derivation.\n'


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=1) + '\n').encode()


def replace(text, old, new, count=1):
    if text.count(old) != count:
        raise ValueError(f'derivation anchor drift: {old[:100]!r}')
    return text.replace(old, new)


def build(root=ROOT):
    archive = root / ARCHIVE
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA:
        raise ValueError('source archive drift')
    cases, measurements = [], []
    with zipfile.ZipFile(archive) as z:
        state = json.loads(z.read(PREFIX + 'state.json'))
        episodes = [e for e in state['episodes'] if e['arm'] == 'no_concrete_examples']
        if len(episodes) != 15:
            raise ValueError('expected 15 retained no-example episodes')
        for episode in episodes:
            for step in (0, 10):
                member = PREFIX + episode['steps'][step]
                raw = z.read(member)
                record = json.loads(raw)
                observation = P.loads(record['request']['messages'][1]['content'])['observation']
                P.legal_ids(observation)
                cases.append({'case_id': f"{episode['episode_id']}-s{step:02d}", 'game_id': episode['game_id'],
                    'step': step, 'observation': observation, 'observation_sha256': P.digest(observation),
                    'source_member': member, 'source_member_sha256': hashlib.sha256(raw).hexdigest(),
                    'historical_system_sha256': hashlib.sha256(record['request']['messages'][0]['content'].encode()).hexdigest()})
                measurements.append({'case_id': cases[-1]['case_id'], **record['audit']})
    case_data = encoded({'schema': 'control_interface_retained_cases_v1', 'partition': 'development', 'cases': cases})
    lock = {'archive': ARCHIVE, 'archive_sha256': ARCHIVE_SHA, 'selection': 'all 15 no_concrete_examples games; steps 0 and 10',
            'cases_sha256': hashlib.sha256(case_data).hexdigest(), 'contexts': 30, 'games': 15,
            'distinct_observation_hashes': len({c['observation_sha256'] for c in cases}),
            'history_additions': False, 'synthetic_observations': False}
    protocol = json.loads((root / OLD / 'protocol.json').read_bytes())
    protocol.update(schema='control_interface_action_selection_v1_protocol', scope=SCOPE,
                    purpose='paired retained-observation development action selection; zero game actions; no solving or policy promotion',
                    placeholder_prefix='REPLACE_WITH_', kernel_id='REPLACE_WITH_OWNER/arc3-control-interface-action-selection-v1')
    protocol['model'].update(source_kind='dataset', kaggle_source='REPLACE_WITH_MODEL_OWNER/REPLACE_WITH_MODEL_DATASET/1',
        mounted_path='REPLACE_WITH_VERIFIED_MODEL_MOUNT', tree_sha256='b480ad92cda91474084c795d2ff64b07a6c477909b22d2784d24abf8fb4ef7df')
    protocol['server']['argv'] = ['--no-enable-prefix-caching' if a == '--enable-prefix-caching' else a
                                   for a in protocol['server']['argv']]
    protocol['limits']['maximum_model_requests'] = 131
    protocol['experiment'] = {'cases_sha256': lock['cases_sha256'], 'contexts': 30, 'games': 15, 'passes': 2,
        'research_requests': 120, 'research_seconds': 1500, 'max_tokens': 128, 'prefix_caching': False,
        'prompt_token_ceiling': 60000, 'decoder': 'shared json_object format only; semantic validation after response',
        'arms': list(P.ARMS), 'system_sha256': hashlib.sha256(P.SYSTEM.encode()).hexdigest(),
        'schedule': P.schedule(cases)}
    research = [{'id': item['id'], 'kind': 'action_selection', 'method': 'POST', 'path': '/v1/chat/completions',
                 'timeout_seconds': 60} for item in P.schedule(cases)]
    protocol['requests'][7:7] = research
    result = {NEW + '/cases.json': case_data, NEW + '/cases-lock.json': encoded(lock),
              NEW + '/protocol.json': encoded(protocol), NEW + '/proposal.json': encoded({
                  'status': 'proposal_only_no_approval_no_reservation', 'scope': SCOPE,
                  'purpose': protocol['purpose'], 'shared_controller_basis': '356095a',
                  'approval_status': 'new source/use/compute review required; prior smoke approvals and consumed attempts remain historical',
                  'game_environment': 'not installed, imported or dispatched', 'compute': protocol['limits']})}
    for name in ('trusted_manifest.json', 'trusted_requirements.lock'):
        result[NEW + '/' + name] = (root / OLD / name).read_bytes()
    provenance = {}
    for module in ('binding', 'evidence', 'run', 'notebook', 'launch'):
        data = (root / OLD / (module + '.py')).read_bytes()
        provenance[OLD + '/' + module + '.py'] = hashlib.sha256(data).hexdigest()
        text = data.decode()
        if module == 'run':
            text = replace(text, "NOT_ESTABLISHED = ['solving ability or task performance'", "NOT_ESTABLISHED = ['solving ability, level progress or action usefulness'")
            text = replace(text, 'from certification.direct_publisher_smoke_v1.evidence import Evidence',
                           'from research.control_interface_action_selection_v1.evidence import Evidence')
            text = replace(text, 'from certification.direct_publisher_smoke_v1.binding import require_live',
                           'from research.control_interface_action_selection_v1.binding import require_live')
            text = replace(text, 'trusted_inputs=None):', 'trusted_inputs=None, experiment_root=None):')
            text = replace(text, "        telemetry('after_inference')\n",
                "        telemetry('after_inference')\n"
                "        from research.control_interface_action_selection_v1.probe import run_cases\n"
                "        from research.control_interface_action_selection_v1.runtime_controls import verify_cache_disabled\n"
                "        if experiment_root is None:\n            raise ValueError('frozen experiment root required')\n"
                "        stage('cache_config', lambda: verify_cache_disabled(workdir / 'server.log'))\n"
                "        result['action_selection'] = stage('action_selection', lambda: run_cases(experiment_root, client, evidence, clock))\n"
                "        telemetry('after_action_selection')\n")
            text = replace(text, 'on_environment_cleanup=remove_environment)',
                           'on_environment_cleanup=remove_environment, experiment_root=root)')
            text = text.replace("prefix='direct-publisher-smoke-'", "prefix='control-interface-probe-'")
        elif module == 'evidence':
            text = replace(text, "LIVE = 'gpu_runtime_compatibility_attempt'", "LIVE = 'gpu_control_interface_action_selection_development_probe'")
            text = replace(text, "result['gpu_compatibility_evidence'] = bool(result.get('passed'))",
                           "result['gpu_compatibility_evidence'] = False\n"
                           "            result['model_action_selection_evidence'] = bool(result.get('passed'))\n"
                           "            result['evidence_scope'] = 'retained-observation development probe; no game progress measured'")
        else:
            text = text.replace('certification.direct_publisher_smoke_v1', 'research.control_interface_action_selection_v1')
            text = text.replace('certification/direct_publisher_smoke_v1', NEW)
            text = text.replace('direct_publisher_smoke_v1', 'control_interface_action_selection_v1')
            text = text.replace('direct-publisher-smoke-v1', SCOPE)
            if module == 'binding':
                text = text.replace('direct publisher smoke test live path refused:', 'control-interface action selection live path refused:')
                text = replace(text, "or not 0 < limits['maximum_model_requests'] <= 12", "or limits['maximum_model_requests'] != 131")
                text = replace(text, "    return protocol\n", "    from .runtime_controls import validate_protocol\n    validate_protocol(root, protocol)\n    return protocol\n")
                anchor = '    missing = sorted(required - set(lock.get(\'bindings\', {})))'
                text = replace(text, anchor,
                    "    required |= {p.relative_to(root).as_posix() for p in (Path(root) / 'certification/direct_publisher_smoke_v1').glob('*.py')}\n"
                    "    required |= {PACKAGE + '/cases.json', PACKAGE + '/cases-lock.json', PACKAGE + '/derivation.json', PACKAGE + '/token-audit.json'}\n"
                    "    required |= {'certification/direct_publisher_smoke_v1/' + n for n in ('trusted_manifest.json', 'trusted_requirements.lock')}\n" + anchor)
                text = text.replace("ATTEMPT = re.compile(r'dps-", "ATTEMPT = re.compile(r'cia-")
            elif module == 'notebook':
                text = replace(text, "    return names + [PROTOCOL,", "    names += sorted(p.relative_to(root).as_posix() for p in (Path(root) / 'certification/direct_publisher_smoke_v1').glob('*.py'))\n"
                    "    names += [PACKAGE + '/cases.json', PACKAGE + '/cases-lock.json', PACKAGE + '/derivation.json', PACKAGE + '/token-audit.json']\n"
                    "    names += ['certification/direct_publisher_smoke_v1/' + n for n in ('trusted_manifest.json', 'trusted_requirements.lock')]\n"
                    "    return names + [PROTOCOL,")
                text = text.replace('at most 12 counted', 'at most 131 counted')
                text = text.replace('Direct publisher smoke test v1 (runtime compatibility only)',
                                    'Milestone E paired action selection v1 (development observations only)')
                text = text.replace('No solving claim.', '120 paired research completions; zero game actions. No solving or game-progress claim.')
                text = text.replace('ARC3 Direct publisher Smoke V1 Review', 'ARC3 Control Interface Action Selection V1 Review')
        result[NEW + '/' + module + '.py'] = (HEADER + text).encode()
    result[NEW + '/derivation.json'] = encoded({'basis_commit': '356095a', 'controller_sources': provenance,
        'builder': 'scripts/build_control_interface_action_selection_v1.py',
        'changes': ['new scope and approval/attempt paths; no inherited authority',
                    '131 counted HTTP requests including 120 research calls; 0 game actions',
                    'research callback before cancellation; cache-disabled configuration verification',
                    'new development evidence label; complete shared import closure in source lock',
                    'unchanged process ownership, installation, watchdog, cleanup and final deadline logic']})
    result[NEW + '/historical-measurements.json'] = encoded({'archive_sha256': ARCHIVE_SHA, 'rows': measurements,
        'note': 'historical constrained-decoder/cache-enabled calls; timing clues only, not rates guaranteed for this new decoder/cache configuration'})
    script = (root / 'scripts/direct_publisher_smoke_package.py').read_text(encoding='utf-8')
    script = script.replace('certification.direct_publisher_smoke_v1', 'research.control_interface_action_selection_v1')
    script = script.replace('direct_publisher_smoke', 'control_interface_action_selection')
    script = script.replace('direct-publisher-smoke-v1', SCOPE)
    script = script.replace('direct-publisher-smoke-review-check-', 'control-interface-review-check-')
    script = replace(script, "        process = subprocess.run([sys.executable, '-I', '-c', code],",
                     "        cell_file = base / 'review_cell.py'\n"
                     "        cell_file.write_text(code, encoding='utf-8')\n"
                     "        process = subprocess.run([sys.executable, '-I', str(cell_file)],")
    result['scripts/control_interface_action_selection_package.py'] = (HEADER + script).encode()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    artifacts = build()
    for name, data in artifacts.items():
        path = ROOT / name
        if args.check:
            if path.read_bytes() != data:
                raise SystemExit('derivation drift: ' + name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print(json.dumps({'derived_files': len(artifacts), 'checked': args.check, 'network_calls': 0, 'gpu_launches': 0}))


if __name__ == '__main__':
    main()
