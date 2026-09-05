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


def policy():
    return {
        "schema_version": 1,
        "skill_version": "3.2.1",
        "mode": "maximum-autonomy",
        "risk_cap": "MEDIUM",
        "fail_closed": True,
        "budgets": {"tokens": 1000, "minutes": 10, "money": 0, "compute": "local", "network": False},
        "permissions": {"local_read": True, "local_write": True, "execute": True, "network": False, "external_write": False, "publish": False, "submit": False},
        "standing_authorizations": [],
    }


class AutonomyAuthorizationTests(unittest.TestCase):
    def test_maximum_autonomy_allows_bounded_local_action(self):
        result = autonomy.authorize(policy(), "RUN_LOCAL_JOB", scope="project/artifacts", risk="LOW")
        self.assertEqual(result["status"], "AUTHORIZED")

    def test_unknown_and_external_actions_are_blocked(self):
        self.assertEqual(autonomy.authorize(policy(), "PUBLISH", scope="venue", risk="CRITICAL", reversible=False)["status"], "BLOCKED")
        self.assertEqual(autonomy.authorize(policy(), "UNKNOWN", scope="project")["status"], "BLOCKED")

    def test_standing_authorization_expiry_and_revocation(self):
        value = policy()
        grant = autonomy.create_standing_authorization(
            value,
            action="AUTO_HIRE",
            scope="literature",
            risk="HIGH",
            granted_by="author",
            expires_utc="2026-08-30T00:00:00Z",
        )
        self.assertEqual(grant["status"], "PASS")
        self.assertEqual(
            autonomy.authorize(value, "AUTO_HIRE", scope="literature", risk="HIGH", now="2026-08-29T00:00:00Z")["status"],
            "AUTHORIZED",
        )
        self.assertEqual(
            autonomy.authorize(value, "AUTO_HIRE", scope="literature", risk="HIGH", now="2026-08-31T00:00:00Z")["status"],
            "BLOCKED",
        )
        self.assertEqual(autonomy.revoke_standing_authorization(value, grant["authorization_id"], actor="author", reason="scope changed")["status"], "PASS")
        self.assertEqual(autonomy.authorize(value, "AUTO_HIRE", scope="literature", risk="HIGH", now="2026-08-29T00:00:00Z")["status"], "BLOCKED")

    def test_auto_hire_requires_pin_license_trials_and_authorization(self):
        candidate = {
            "id": "employee",
            "exact_ref": "a" * 40,
            "license": "MIT",
            "source_audit": "PASS",
            "behavior_trial": "PASS",
            "security_audit": "PASS",
            "permission_scope": ["literature"],
            "risk": "HIGH",
        }
        self.assertEqual(autonomy.auto_hire_gate(policy(), candidate)["status"], "BLOCKED")
        autonomy.create_standing_authorization(
            policy_value := policy(),
            action="AUTO_HIRE",
            scope="literature",
            risk="HIGH",
            granted_by="author",
            expires_utc="2026-08-30T00:00:00Z",
        )
        self.assertEqual(autonomy.auto_hire_gate(policy_value, candidate, now="2026-08-29T00:00:00Z")["status"], "AUTHORIZED")

    def test_malformed_policy_fails_closed(self):
        result = autonomy.authorize({"mode": "maximum-autonomy"}, "RUN_LOCAL_JOB", scope="project")
        self.assertEqual(result["status"], "BLOCKED")


class AutonomyAuditTests(unittest.TestCase):
    def test_audit_chain_appends_and_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".autonomy-audit.jsonl"
            autonomy.append_audit(path, "authorize", {"action": "RUN_LOCAL_JOB"}, actor="director", decision="AUTHORIZED", utc="2026-08-28T00:00:00Z")
            autonomy.append_audit(path, "resume", {"session": "S1"}, actor="director", decision="AUTHORIZED", utc="2026-08-28T00:00:01Z")
            self.assertEqual(autonomy.verify_audit(path)["status"], "PASS")

    def test_audit_tamper_reorder_truncate_and_malformed_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = Path(tmp) / "original.jsonl"
            autonomy.append_audit(original, "one", {}, actor="test", decision="AUTHORIZED", utc="2026-08-28T00:00:00Z")
            autonomy.append_audit(original, "two", {}, actor="test", decision="AUTHORIZED", utc="2026-08-28T00:00:01Z")
            lines = original.read_text(encoding="utf-8").splitlines()
            variants = {
                "mutated.jsonl": [lines[0].replace('"operation":"one"', '"operation":"changed"'), lines[1]],
                "reordered.jsonl": [lines[1], lines[0]],
                "truncated.jsonl": [lines[0]],
                "malformed.jsonl": ["{bad json"],
            }
            for name, changed in variants.items():
                path = Path(tmp) / name
                path.write_text("\n".join(changed) + "\n", encoding="utf-8")
                self.assertEqual(autonomy.verify_audit(path)["status"], "FAIL", name)


if __name__ == "__main__":
    unittest.main()
