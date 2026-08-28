import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


autonomy = load("autonomy")


def maximum_policy():
    return json.loads((ROOT / "assets" / "templates" / "v3" / "autonomy_policy.json").read_text(encoding="utf-8"))


def candidate(risk="LOW"):
    return {
        "id": "bounded-employee",
        "exact_ref": "a" * 40,
        "license": "MIT",
        "license_compatible": True,
        "source_audit": "PASS",
        "installer_audit": "PASS",
        "dependency_audit": "PASS",
        "behavior_trial": "PASS",
        "security_audit": "PASS",
        "permission_scope": ["analysis"],
        "credentials": False,
        "paid": False,
        "admin": False,
        "system_wide_write": False,
        "private_data_export": False,
        "dangerous_hooks": False,
        "isolated": True,
        "risk": risk,
    }


class MaximumAutonomyPolicyTests(unittest.TestCase):
    def test_network_research_is_enabled_and_audited_by_default(self):
        value = maximum_policy()
        self.assertTrue(value["permissions"]["network"])
        result = autonomy.authorize(value, "NETWORK_READ", scope="literature/public", risk="LOW")
        self.assertEqual(result["status"], "AUTHORIZED")
        self.assertEqual(result["decision"], "AUTO_WITH_AUDIT")

    def test_auto_hire_risk_tiers(self):
        value = maximum_policy()
        self.assertTrue(value["permissions"]["auto_hire"])
        low = autonomy.auto_hire_gate(value, candidate("LOW"))
        medium = autonomy.auto_hire_gate(value, candidate("MEDIUM"))
        high = autonomy.auto_hire_gate(value, candidate("HIGH"))
        self.assertEqual((low["status"], low["decision"]), ("AUTHORIZED", "AUTO"))
        self.assertEqual((medium["status"], medium["decision"]), ("AUTHORIZED", "AUTO_WITH_AUDIT"))
        self.assertEqual((high["status"], high["decision"]), ("BLOCKED", "ASK_AUTHOR"))

    def test_scientific_and_protocol_decisions_are_tiered(self):
        value = maximum_policy()
        ordinary = autonomy.authorize(
            value,
            "SCIENTIFIC_DECISION",
            scope="methods",
            risk="LOW",
            decision_kind="choose_baseline",
        )
        amendment = autonomy.authorize(
            value,
            "PROTOCOL_CHANGE",
            scope="protocol",
            risk="MEDIUM",
            decision_kind="bounded_protocol_amendment",
        )
        fundamental = autonomy.authorize(
            value,
            "SCIENTIFIC_DECISION",
            scope="research-question",
            risk="HIGH",
            decision_kind="replace_core_research_question",
        )
        self.assertEqual(ordinary["decision"], "AUTO")
        self.assertEqual(amendment["decision"], "AUTO_WITH_AUDIT")
        self.assertEqual((fundamental["status"], fundamental["decision"]), ("BLOCKED", "ASK_AUTHOR"))


class AutoHireLifecycleTests(unittest.TestCase):
    def test_low_risk_hire_reaches_execution_and_checker(self):
        marketplace = load("skill_marketplace_runtime")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            source = Path(tmp) / "candidate"
            project.mkdir()
            source.mkdir()
            (source / "SKILL.md").write_text("---\nname: bounded-employee\ndescription: Perform analysis on supplied data.\n---\n", encoding="utf-8")
            (source / "worker.py").write_text(
                "import json,sys\nfrom pathlib import Path\n"
                "payload=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))\n"
                "Path(sys.argv[2]).write_text(json.dumps({'value': payload['value'] + 1}), encoding='utf-8')\n",
                encoding="utf-8",
            )
            item = candidate("LOW") | {
                "source_path": str(source),
                "entrypoint": "worker.py",
                "capabilities": ["analysis"],
                "semantic_audit": {"status": "CONFIRMED", "actor": "recorded-host-audit", "evidence": ["SKILL.md", "worker.py"]},
                "behavior_trial": {"status": "PASS", "checker": "deterministic-output-checker", "output_contract": "PASS"},
            }
            result = marketplace.hire_and_execute(project, "analysis", [item], {"value": 2}, policy=maximum_policy())
            self.assertEqual(result["status"], "ACCEPTED")
            self.assertEqual(result["result"]["value"], 3)
            self.assertEqual(
                result["lifecycle"],
                [
                    "RESOLVED",
                    "MATERIALIZED",
                    "INSTALLED_ISOLATED",
                    "QUALIFIED",
                    "DELEGATION_READY",
                    "EXECUTED",
                    "HANDOFF_RECEIVED",
                    "CHECKED",
                    "ACCEPTED",
                ],
            )

    def test_unverified_direct_hire_cannot_execute(self):
        marketplace = load("skill_marketplace_runtime")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            source = Path(tmp) / "candidate"
            project.mkdir()
            source.mkdir()
            (source / "SKILL.md").write_text("---\nname: unverified\ndescription: Candidate.\n---\n", encoding="utf-8")
            (source / "worker.py").write_text("print('must not execute')\n", encoding="utf-8")
            item = candidate("LOW") | {
                "source_path": str(source),
                "entrypoint": "worker.py",
                "capabilities": ["analysis"],
                "capability_verification": {"status": "CONFIRMED", "formal_eligible": True},
            }
            result = marketplace.hire_and_execute(project, "analysis", [item], {}, policy=maximum_policy())
            self.assertEqual(result["status"], "BLOCKED")
            self.assertNotIn("EXECUTED", result["lifecycle"])

    def test_provisional_and_quarantined_candidates_never_execute(self):
        marketplace = load("skill_marketplace_runtime")
        for qualification in ("PROVISIONAL", "QUARANTINED", "REJECTED"):
            result = marketplace.can_execute({"qualification": qualification})
            self.assertFalse(result["allowed"], qualification)


if __name__ == "__main__":
    unittest.main()
