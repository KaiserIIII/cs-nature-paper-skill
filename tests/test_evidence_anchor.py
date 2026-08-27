import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("evidence_anchor", ROOT / "scripts/evidence_anchor.py")
evidence_anchor = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(evidence_anchor)


def anchor(**changes):
    value = {
        "anchor_id": "EA-1", "claim_id": "C1", "result_id": "R1", "source_artifact": "results/table.csv",
        "exact_region": "row 2", "transformation": "scripts/analyze.py", "command": "python scripts/analyze.py",
        "exit_status": 0, "code_commit": "abc123", "config_hash": "sha256:config", "environment": "env.lock",
        "input_hash": "sha256:input", "uncertainty": "95% CI", "scope": "fixed sample", "status": "VERIFIED",
        "verified_utc": "2026-08-27T00:00:00Z",
    }
    value.update(changes)
    return value


class EvidenceAnchorTests(unittest.TestCase):
    def test_valid_anchor_passes(self):
        self.assertEqual(evidence_anchor.validate_anchor(anchor())["status"], "PASS")

    def test_verified_nonzero_and_missing_hash_fail(self):
        result = evidence_anchor.validate_anchor(anchor(provenance_level="VERIFIED", exit_status=1, input_hash=""))
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("exit_status 0" in x for x in result["findings"]))

    def test_ledger_collection_is_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            path.write_text(json.dumps({"anchors": [anchor(), anchor(anchor_id="EA-2", status="QUALIFIES")]}) + "\n", encoding="utf-8")
            result = evidence_anchor.validate_path(path)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["anchor_count"], 2)


if __name__ == "__main__":
    unittest.main()
