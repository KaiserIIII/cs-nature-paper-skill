import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PROVIDERS = ROOT / "providers"
for folder in (str(SCRIPTS), str(PROVIDERS)):
    if folder not in sys.path:
        sys.path.insert(0, folder)


def load(name):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"discovery_execution_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class SpecialistDiscoveryExecutionTests(unittest.TestCase):
    def test_explicit_empty_backend_list_is_offline(self):
        discovery = load("skill_discovery_provider")
        with patch.object(discovery, "GitHubPublicBackend", side_effect=AssertionError("offline discovery contacted GitHub")):
            result = discovery.discover_capability("evidence-bound-writing", backends=[])

        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["queries"], [])

    def test_research_runs_discovery_once_before_host_fallback(self):
        state = load("research_state")
        executor = load("research_executor")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "paper"
            project.mkdir()
            state.init_state(project, "ml-benchmark", "maximum-autonomy", "machine-learning")
            inputs = project / "inputs"
            inputs.mkdir()
            (inputs / "research_brief.json").write_text(json.dumps({
                "question": "Does the method control acceptance risk?",
                "load_bearing_nodes": ["writing"],
                "method_candidates": ["risk-controlled acceptance"],
            }), encoding="utf-8")
            unavailable = {
                "operation": "skill-discovery",
                "status": "UNAVAILABLE",
                "capability": "evidence-bound-writing",
                "candidates": [],
            }
            with patch.object(executor.skill_discovery_provider, "discover_capability", return_value=unavailable) as discover:
                first = executor.execute_node(project, "writing")
                second = executor.execute_node(project, "writing")

            self.assertEqual(first["status"], "HOST_EXECUTION_REQUIRED")
            self.assertEqual(second["status"], "HOST_EXECUTION_REQUIRED")
            self.assertEqual(discover.call_count, 1)
            self.assertEqual(first["specialist_discovery"]["status"], "UNAVAILABLE")
            record = json.loads((project / ".research-state" / "specialist_discovery.json").read_text(encoding="utf-8"))
            self.assertEqual(record["attempts"]["writing:evidence-bound-writing"]["attempt_count"], 1)

    def test_competition_runs_discovery_once_before_host_fallback(self):
        state = load("research_state")
        executor = load("competition_executor")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "contest"
            project.mkdir()
            state.init_state(project, "algorithmic", "competition-autopilot", "mathematical-modeling")
            (project / ".research-state" / "competition_input.json").write_text(json.dumps({
                "competition": "Generic Contest",
                "specialist_nodes": ["model_validation"],
                "problems": [{"id": "Q1", "questions": [{"id": "Q1", "goal": "validate a model"}]}],
            }), encoding="utf-8")
            unavailable = {
                "operation": "skill-discovery",
                "status": "UNAVAILABLE",
                "capability": "model-validation",
                "candidates": [],
            }
            with patch.object(executor.skill_discovery_provider, "discover_capability", return_value=unavailable) as discover:
                first = executor.execute_node(project, "model_validation")
                second = executor.execute_node(project, "model_validation")

            self.assertEqual(first["status"], "HOST_EXECUTION_REQUIRED")
            self.assertEqual(second["status"], "HOST_EXECUTION_REQUIRED")
            self.assertEqual(discover.call_count, 1)
            self.assertEqual(first["specialist_discovery"]["status"], "UNAVAILABLE")
            record = json.loads((project / ".research-state" / "specialist_discovery.json").read_text(encoding="utf-8"))
            self.assertEqual(record["attempts"]["model_validation:model-validation"]["attempt_count"], 1)


if __name__ == "__main__":
    unittest.main()
