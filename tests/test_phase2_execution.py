"""Exercise the real runner factory and evidence-bound two-run comparison."""
import copy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agent.competition_loop import CompetitionAgentLoop
from agent.diagnostics import TransitionDiagnosticRecorder, canonical_sha256
from agent.e1_policy import binding_from_registry, E1Policy
from agent.feature_manifest import load_e1_feature_manifests
from agent.scheduler import QueuedInferenceExecutor
from evaluation.phase2_reproduction import compare_runs, GAME, SEED
from scripts.build_phase2_diagnostic_notebook import build
from scripts.run_e1_four_cell import _run_cell
from tests.test_phase2_diagnostics import CompletionClient, LoopClient, NoChangeAdapter

ROOT = Path(__file__).resolve().parents[1]


class ExecutionTests(unittest.TestCase):
    def test_real_cell_factory_returns_model_policy_and_calls_inference(self):
        protocol = json.loads((ROOT / "config/e1_experiment_protocol.yaml").read_text())
        protocol["development_game_seed_pairs"] = [{"game_id":GAME,"seed":SEED,"fold":2}]
        completion = CompletionClient(['{"action":{"action_id":1,"action_data":{}}}'])
        completion.session = SimpleNamespace(close=lambda:None)
        seen = []
        class Orchestrator:
            def __init__(self, adapter, games, **kw):
                self.kw = kw
            def run(self):
                client = Client()
                policy = self.kw["policy_factory"](client)
                if not isinstance(policy, E1Policy):
                    raise AssertionError("runner silently selected fallback")
                result = CompetitionAgentLoop(NoChangeAdapter(),client,policy=policy,max_actions=1).run()
                seen.append(result)
                return SimpleNamespace(results=[result],finalization_status="acknowledged",scorecard={"environments":[{"id":GAME,"score":0}]})
        # LoopClient's default game is a synthetic ar25 fixture; align it with cd82.
        from tests.test_phase2_diagnostics import observation
        from dataclasses import replace
        class Client(LoopClient):
            def __init__(self):
                super().__init__()
                self.game_id = GAME
                self.observation = replace(observation(), game_id=GAME)
        with patch("arc_agi.Arcade"), patch("scripts.run_e1_four_cell.LocalFrameworkAdapter") as adapter, patch("scripts.run_e1_four_cell.CompetitionOrchestrator",Orchestrator), patch("scripts.run_e1_four_cell.OpenAICompatibleCompletionClient",return_value=completion):
            adapter.return_value.list_game_ids.return_value = [GAME]
            _run_cell("E1S-R",protocol=protocol,manifests=load_e1_feature_manifests(ROOT / "config/e1_feature_manifests.yaml"),binding=binding_from_registry(ROOT / "config/e1_feature_manifests.yaml"),base_url="http://127.0.0.1:8000/v1",request_timeout_seconds=300,environments_dir=ROOT,remaining_seconds=3000,finalization_reserve_seconds=600)
        self.assertEqual(seen[0].inference_requests,1)
        self.assertEqual(seen[0].policy_failures,0)
        self.assertEqual(len(completion.requests),1)

    def envelope(self, run_id, lock):
        from dataclasses import replace
        client = LoopClient()
        client.game_id = GAME
        client.observation = replace(client.observation,game_id=GAME)
        class Adapter:
            def dispatch(self, client, decision):
                return client.observation
        recorder = TransitionDiagnosticRecorder(game_id=GAME,treatment_id="E1S-R",seed=SEED,run_id=run_id,capacity=80)
        with QueuedInferenceExecutor(worker_count=8) as queue:
            policy = E1Policy(manifest=load_e1_feature_manifests(ROOT / "config/e1_feature_manifests.yaml")["E1S-R"],binding=binding_from_registry(ROOT / "config/e1_feature_manifests.yaml"),client=CompletionClient(['{"action":{"action_id":1,"action_data":{}}}']*80),inference=queue,seed=SEED)
            result = CompetitionAgentLoop(Adapter(),client,policy=policy,max_actions=80,diagnostics=recorder).run()
        game = {**asdict(result),"seed":SEED,"score":0,"score_unit":"official_RHAE_percent"}
        return {
            "run_id":run_id,"game_id":GAME,"seed":SEED,"request_seed":SEED,
            "lock_sha256":canonical_sha256(lock),
            "model_artifact_sha256":lock["model_artifact_sha256"],
            "observed_gpu":"RTX PRO 6000 synthetic fixture",
            "observed_packages":json.loads((ROOT / "config/m0_launch_spec_q3vl30.json").read_text())["required_packages"],
            "elapsed_seconds":10,"bundle":recorder.bundle(),
            "cell":{"cell_id":"E1S-R","games":[game],"finalization_status":"acknowledged",
                "queue":{"policy":"minimum_fair_v1","capacity":110,"worker_count":8,"max_age_seconds":300},
                "fresh_runtime":{"block_id":run_id,"fresh_process":True,"completion_canary_passed":True,"peak_vram_bytes":1,"peak_ram_bytes":1}}}

    def test_cross_run_reproduction_and_negative_provenance(self):
        _, lock = build()
        first = self.envelope("fixture-run-1",lock)
        second = self.envelope("fixture-run-2",lock)
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory)/"a.json",Path(directory)/"b.json"]
            paths[0].write_text(json.dumps(first))
            paths[1].write_text(json.dumps(second))
            result = compare_runs(ROOT,paths,lock)
            self.assertTrue(result["failure_reproduced"])
            self.assertEqual(result["taxonomy_id"],"unsupported_other")
            self.assertFalse(result["admission_passed"])
            paths[1].write_text(json.dumps(first))
            with self.assertRaisesRegex(ValueError,"duplicate run"):
                compare_runs(ROOT,paths,lock)
            bad = copy.deepcopy(second)
            bad["lock_sha256"] = "0"*64
            paths[1].write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError,"provenance"):
                compare_runs(ROOT,paths,lock)

    def test_notebook_compiles_and_has_two_run_budget(self):
        notebook,lock = build()
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                compile(cell["source"],"notebook","exec")
        self.assertEqual(lock["runs"],2)
        self.assertEqual(lock["actions_per_run"],80)
        self.assertFalse(lock["automatic_admission"])

    def test_semantic_fallback_is_rejected_even_with_rehashed_bundle(self):
        _,lock = build()
        first = self.envelope("fixture-1",lock)
        second = self.envelope("fixture-2",lock)
        record = second["bundle"]["records"][0]
        record["proposal_or_fallback"]["executed_decision"]["source"] = "deterministic_fallback"
        record["failure_signature_sha256"] = canonical_sha256({k:v for k,v in record.items() if k != "failure_signature_sha256"})
        bundle = second["bundle"]
        bundle["bundle_sha256"] = canonical_sha256({k:v for k,v in bundle.items() if k != "bundle_sha256"})
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory)/"a.json",Path(directory)/"b.json"]
            for path,value in zip(paths,[first,second]):
                path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,"silent fallback"):
                compare_runs(ROOT,paths,lock)

    def test_parent_sources_import_in_isolated_notebook_bundle(self):
        import base64
        import subprocess
        import sys
        from scripts.build_e1_four_cell_notebook import bundled_sources
        files = bundled_sources()
        for relative in ("scripts/run_phase2_diagnostics.py","evaluation/phase2_reproduction.py"):
            files[relative] = base64.b64encode((ROOT/relative).read_bytes()).decode()
        with tempfile.TemporaryDirectory() as directory:
            for relative,payload in files.items():
                target = Path(directory)/relative
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(base64.b64decode(payload))
            result = subprocess.run([sys.executable,"-I","-c",
                "import sys; sys.path.insert(0,sys.argv[1]); import scripts.run_phase2_diagnostics; import evaluation.phase2_reproduction",directory],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)


if __name__ == "__main__":
    unittest.main()
