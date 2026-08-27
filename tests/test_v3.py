import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


research_state = load("research_state")
research_graph = load("research_graph")
employee_registry = load("employee_registry")


class V3StateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / "project"
        self.project.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def read(self, state, name):
        return json.loads((state / name).read_text(encoding="utf-8"))

    def test_init_creates_v3_state_and_domain_routing(self):
        result = research_state.init_state(self.project, "ml-benchmark", "copilot", "machine-learning")
        self.assertEqual(result["status"], "PASS")
        state = self.project / ".research-state"
        expected = {"project.json", "research_contract.json", "research_graph.json", "claims.json", "evidence_ledger.json", "literature_registry.json", "experiment_registry.json", "artifact_manifest.json", "amendments.json", "risks.json", "venue_profile.json", "employee_registry.json", "decision_log.md"}
        self.assertTrue(expected <= {p.name for p in state.iterdir()})
        project = self.read(state, "project.json")
        self.assertEqual(project["skill_version"], "3.0.0")
        self.assertEqual(project["domain"], "machine-learning")

    def test_v2_migration_preserves_source(self):
        state = self.project / ".research-state"
        state.mkdir()
        contract = json.loads((ROOT / "assets/templates/research_contract.json").read_text(encoding="utf-8"))
        ledger = json.loads((ROOT / "assets/templates/evidence_ledger.json").read_text(encoding="utf-8"))
        (state / "research_contract.json").write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
        (state / "evidence_ledger.json").write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        before = {p.name: p.read_bytes() for p in state.iterdir()}
        result = research_state.migrate_v2(self.project)
        self.assertTrue(result["preserved"])
        self.assertEqual(before, {p.name: p.read_bytes() for p in state.iterdir()})
        target = self.project / ".research-state-v3"
        self.assertTrue((target / "research_graph.json").exists())
        self.assertTrue((target / "employee_registry.json").exists())
        self.assertEqual(self.read(target, "research_contract.json")["migrated_from"], "v2")
        self.assertEqual(self.read(target, "research_contract.json")["feasibility"]["decision"], "PILOT_FIRST")


class V3GraphTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / "project"
        self.project.mkdir()
        research_state.init_state(self.project, "empirical", "copilot", "systems")

    def tearDown(self):
        self.tmp.cleanup()

    def test_graph_requires_evidence_and_dependencies(self):
        graph = research_graph.status_graph(self.project)
        self.assertEqual(graph["status"], "PASS")
        with self.assertRaises(research_graph.GraphError):
            research_graph.transition(self.project, "brief", "PASS", "done", "test", None)
        research_graph.transition(self.project, "brief", "PASS", "brief complete", "test", "EA-1")
        research_graph.transition(self.project, "literature", "PASS", "sources verified", "test", "EA-2")
        self.assertEqual(research_graph.status_graph(self.project)["events"], 2)


class V3RoutingTests(unittest.TestCase):
    def test_profiles_and_contracts_are_present(self):
        self.assertGreaterEqual(len(list((ROOT / "references/domains").glob("*.md"))), 13)
        self.assertGreaterEqual(len(list((ROOT / "references/study-types").glob("*.md"))), 15)
        self.assertEqual(len(list((ROOT / "references/departments").glob("*.md"))), 7)
        value = employee_registry._read_json(ROOT / "assets/templates/employee_registry_v3.json")
        self.assertEqual(employee_registry.audit_registry(value)["status"], "PASS")

    def test_behavior_cases_have_v3_routing_and_safety_fields(self):
        value = json.loads((ROOT / "assets/evals/behavior_cases.json").read_text(encoding="utf-8"))
        self.assertEqual(value["skill_version"], "3.0.0")
        ids = [case["id"] for case in value["cases"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue({"AUTOPILOT-BEGINNER-ROUTING", "FEASIBILITY-NO-GO", "GRAPH-REOPEN-AMENDMENT", "V3-MIGRATION-NONDESTRUCTIVE"} <= set(ids))
        for case in value["cases"]:
            self.assertTrue(case["required_behaviors"])
            self.assertTrue(case["forbidden_behaviors"])
            self.assertTrue(case["required_artifacts"])


if __name__ == "__main__":
    unittest.main()
