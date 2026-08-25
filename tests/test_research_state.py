import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "research_state.py"
SPEC = importlib.util.spec_from_file_location("research_state", MODULE_PATH)
research_state = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(research_state)


class ResearchStateTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.project = Path(self.tempdir.name) / "sample-project"
        self.project.mkdir()
        research_state.init_state(self.project, "empirical", "full")
        self.state = self.project / ".research-state"

    def tearDown(self):
        self.tempdir.cleanup()

    def read_json(self, name):
        return json.loads((self.state / name).read_text(encoding="utf-8"))

    def write_json(self, name, value):
        (self.state / name).write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    def fill_argument_and_claim(self):
        contract = self.read_json("research_contract.json")
        argument = contract["scientific_argument"]
        for field in (
            "stakeholder_problem",
            "phenomenon_or_artifact",
            "prior_knowledge",
            "gap",
            "mechanism_or_model",
            "target_population_and_scope",
            "contribution",
            "downstream_boundary",
        ):
            argument[field] = f"specified {field}"
        argument["questions_or_goals"] = [{"id": "RQ1", "text": "Where does failure occur?"}]
        argument["constructs"] = [
            {
                "name": "target artifact availability",
                "conceptual_definition": "availability for one declared target",
                "operationalization": "matching distribution file exists",
                "role": "outcome",
                "known_gap": "does not establish installation or execution",
            }
        ]
        self.write_json("research_contract.json", contract)

        ledger = self.read_json("evidence_ledger.json")
        ledger["claims"] = [
            {
                "id": "C1",
                "text": "Failures concentrate at the artifact layer for this target.",
                "type": "descriptive",
                "scope": "sampled snapshots under the fixed target",
                "required_evidence": "joint outcome counts with fixed denominator",
                "observed_evidence": [],
                "counterevidence": [],
                "uncertainty": "sampling and index-time dependence",
                "status": "PLANNED",
            }
        ]
        self.write_json("evidence_ledger.json", ledger)

    def fill_protocol(self):
        contract = self.read_json("research_contract.json")
        contract["protocol"].update(
            {
                "status": "frozen-v1",
                "units": "repository snapshots",
                "outcomes": ["candidate", "wheel", "resolver"],
                "estimands": ["layer-conditional proportions"],
                "denominators": ["all snapshots", "candidate-positive snapshots"],
                "missingness_and_exclusions": "report separately",
                "clustering_and_dependence": "repository and shared-package sensitivity",
                "repetition_rationale": "deterministic queries are cached; resolver calls are logged",
                "multiplicity": "three registered layer models",
                "stopping_and_failure_rules": "complete the frozen sample; retain failures",
                "frozen_inputs": ["snapshot-manifest.sha256"],
            }
        )
        self.write_json("research_contract.json", contract)

    def test_init_creates_private_state_and_refuses_overwrite(self):
        self.assertTrue((self.state / "research_contract.json").exists())
        self.assertTrue(self.read_json("research_contract.json")["private"])
        self.assertEqual(self.read_json("research_contract.json")["skill_version"], "2.1.0")
        self.assertFalse((self.project / ".gitignore").exists())
        with self.assertRaises(research_state.StateError):
            research_state.init_state(self.project, "empirical", "full")

    def test_blank_argument_fails_then_completed_argument_passes(self):
        self.assertEqual(research_state.audit_state(self.project, "argument")["status"], "FAIL")
        self.fill_argument_and_claim()
        self.assertEqual(research_state.audit_state(self.project, "argument")["status"], "PASS")

    def test_empirical_protocol_requires_frozen_design(self):
        self.assertEqual(research_state.audit_state(self.project, "protocol")["status"], "FAIL")
        self.fill_protocol()
        self.assertEqual(research_state.audit_state(self.project, "protocol")["status"], "PASS")

    def test_claim_gate_requires_final_status_and_evidence_anchor(self):
        self.fill_argument_and_claim()
        self.assertEqual(research_state.audit_state(self.project, "claims")["status"], "FAIL")
        ledger = self.read_json("evidence_ledger.json")
        ledger["claims"][0]["status"] = "SUPPORTED"
        self.write_json("evidence_ledger.json", ledger)
        self.assertEqual(research_state.audit_state(self.project, "claims")["status"], "FAIL")
        ledger["claims"][0]["observed_evidence"] = ["artifacts/joint-patterns.csv#sha256=example"]
        self.write_json("evidence_ledger.json", ledger)
        self.assertEqual(research_state.audit_state(self.project, "claims")["status"], "PASS")

    def test_submission_gate_requires_live_primary_venue_sources(self):
        self.fill_argument_and_claim()
        self.fill_protocol()
        ledger = self.read_json("evidence_ledger.json")
        ledger["claims"][0]["status"] = "SCOPED"
        ledger["claims"][0]["observed_evidence"] = ["results/table1.csv"]
        self.write_json("evidence_ledger.json", ledger)
        self.assertEqual(research_state.audit_state(self.project, "submission")["status"], "FAIL")
        contract = self.read_json("research_contract.json")
        contract["venue"] = {
            "rules_last_verified_utc": "2026-08-26T00:00:00Z",
            "primary_sources": ["https://example.org/official-call-for-papers"],
        }
        self.write_json("research_contract.json", contract)
        self.assertEqual(research_state.audit_state(self.project, "submission")["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
