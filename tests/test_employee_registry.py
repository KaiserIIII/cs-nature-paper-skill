import importlib.util
import unittest
from copy import deepcopy
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "employee_registry.py"
SPEC = importlib.util.spec_from_file_location("employee_registry", MODULE_PATH)
employee_registry = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(employee_registry)


def approved_employee(employee_id, roles, capabilities):
    return {
        "id": employee_id,
        "source": "https://github.com/example/reviewed-skill",
        "ref": "v1.2.3",
        "license": "MIT",
        "status": "APPROVED",
        "departments": ["figures"],
        "roles": roles,
        "capabilities": capabilities,
        "trigger_scope": "Publication figures backed by frozen source data.",
        "do_not_use_for": "Do not infer or invent scientific results.",
        "permissions": {
            "network": False,
            "credentials": [],
            "writes": ["declared output directory"],
            "executes_scripts": True,
        },
        "environment_contract": "Python 3.11, pinned plotting libraries, headless backend.",
        "quality_evidence": {
            "source_reviewed": True,
            "license_reviewed": True,
            "scripts_reviewed": True,
            "tests": {
                "unit": ["tests validate export manifest"],
                "workflow": ["render and inspect a representative multi-panel figure"],
                "external": [],
            },
            "security_audits": ["local-static-audit: PASS"],
        },
        "known_risks": [],
        "approved_uses": ["figures from explicit source tables"],
        "rollback": "Disable employee and restore the prior pinned ref.",
        "last_reviewed_utc": "2026-08-26T00:00:00Z",
    }


def registry(employees):
    return {
        "schema_version": 1,
        "skill_version": "2.1.0",
        "last_reviewed_utc": "2026-08-26T00:00:00Z",
        "employees": employees,
        "department_contracts": [
            {
                "department": "figures",
                "required_capabilities": [
                    "figure-semantics",
                    "deterministic-rendering",
                    "independent-visual-audit",
                ],
                "required_roles": ["producer", "checker"],
                "producer_checker_separation": True,
            }
        ],
    }


class EmployeeRegistryTests(unittest.TestCase):
    def setUp(self):
        self.producer = approved_employee(
            "figure-producer",
            ["producer"],
            ["figure-semantics", "deterministic-rendering"],
        )
        self.checker = approved_employee(
            "figure-checker",
            ["checker"],
            ["independent-visual-audit"],
        )

    def test_approved_pair_passes_audit_and_team_check(self):
        value = registry([self.producer, self.checker])
        self.assertEqual(employee_registry.audit_registry(value)["status"], "PASS")
        self.assertEqual(employee_registry.check_team(value)["status"], "PASS")

    def test_public_template_is_valid_and_covers_all_departments(self):
        template_path = MODULE_PATH.parents[1] / "assets" / "templates" / "employee_registry.json"
        value = employee_registry._read_json(template_path)
        self.assertEqual(employee_registry.audit_registry(value)["status"], "PASS")
        self.assertEqual(len(value["department_contracts"]), 7)

    def test_floating_ref_blocks_approval(self):
        value = registry([self.producer, self.checker])
        value["employees"][0]["ref"] = "main"
        result = employee_registry.audit_registry(value)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("floating branch" in finding for finding in result["findings"]))

    def test_security_warning_blocks_approval(self):
        value = registry([self.producer, self.checker])
        value["employees"][0]["quality_evidence"]["security_audits"] = ["scanner: WARN"]
        self.assertEqual(employee_registry.audit_registry(value)["status"], "FAIL")

    def test_quarantined_employee_cannot_cover_a_capability(self):
        quarantined = {
            "id": "unsafe-renderer",
            "source": "https://github.com/example/unsafe-renderer",
            "status": "QUARANTINED",
            "departments": ["figures"],
            "capabilities": ["deterministic-rendering"],
            "known_risks": ["unresolved install-hook warning"],
        }
        producer = deepcopy(self.producer)
        producer["capabilities"] = ["figure-semantics"]
        result = employee_registry.check_team(registry([producer, self.checker, quarantined]))
        self.assertEqual(result["status"], "FAIL")
        self.assertIn(
            "deterministic-rendering",
            result["departments"][0]["missing_capabilities"],
        )

    def test_provisional_coverage_is_conditional(self):
        provisional = deepcopy(self.checker)
        provisional["status"] = "PROVISIONAL"
        provisional["known_risks"] = ["external benchmark not yet run"]
        result = employee_registry.check_team(registry([self.producer, provisional]))
        self.assertEqual(result["status"], "CONDITIONAL")
        self.assertEqual(result["departments"][0]["conditional_employees"], ["figure-checker"])

    def test_one_employee_cannot_self_check_when_separation_is_required(self):
        combined = deepcopy(self.producer)
        combined["roles"] = ["producer", "checker"]
        combined["capabilities"].append("independent-visual-audit")
        result = employee_registry.check_team(registry([combined]))
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["departments"][0]["producer_checker_separation"])

    def test_unassessed_employee_produces_warning(self):
        unassessed = {
            "id": "candidate",
            "source": "https://github.com/example/candidate",
            "status": "UNASSESSED",
            "departments": ["figures"],
            "capabilities": ["deterministic-rendering"],
        }
        result = employee_registry.audit_registry(registry([unassessed]))
        self.assertEqual(result["status"], "CONDITIONAL")
        self.assertTrue(result["warnings"])


if __name__ == "__main__":
    unittest.main()
