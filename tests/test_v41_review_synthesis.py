import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "review_synthesis", ROOT / "scripts" / "review_synthesis.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reports():
    return [
        {
            "report_id": "review-1",
            "packet_id": "packet-1",
            "report_hash": "sha256:" + "1" * 64,
            "producer_id": "reviewer:methods",
            "findings": [
                {"id": "F-1", "severity": "MAJOR", "problem": "baseline is weak"},
                {"id": "F-2", "severity": "MINOR", "problem": "axis label is unclear"},
            ],
        },
        {
            "report_id": "review-2",
            "packet_id": "packet-1",
            "report_hash": "sha256:" + "2" * 64,
            "producer_id": "reviewer:domain",
            "findings": [
                {"id": "F-1", "severity": "MAJOR", "problem": "baseline is weak"},
                {"id": "F-3", "severity": "CRITICAL", "problem": "claim exceeds evidence"},
            ],
        },
    ]


def packet_check(**overrides):
    value = {
        "status": "PASS",
        "packet_id": "packet-1",
        "report_hashes": ["sha256:" + "1" * 64, "sha256:" + "2" * 64],
        "isolation_status": "AVAILABLE",
    }
    value.update(overrides)
    return value


class V41ReviewSynthesisTests(unittest.TestCase):
    def test_dedicated_synthesis_provider_produces_hash_bound_artifact(self):
        runtime = load_module()
        artifact = runtime.produce_synthesis(
            "packet-1",
            reports(),
            packet_check(),
            synthesis_provider_id="synthesis:publication-review",
            checker_id="checker:publication-review",
        )
        self.assertEqual(artifact["status"], "SYNTHESIS_PRODUCED")
        self.assertEqual(artifact["packet_id"], "packet-1")
        self.assertEqual(
            artifact["source_report_hashes"],
            ["sha256:" + "1" * 64, "sha256:" + "2" * 64],
        )
        self.assertTrue(artifact["synthesis_hash"].startswith("sha256:"))

    def test_same_producer_and_checker_is_rejected(self):
        runtime = load_module()
        artifact = runtime.produce_synthesis(
            "packet-1",
            reports(),
            packet_check(),
            synthesis_provider_id="same:id",
            checker_id="same:id",
        )
        self.assertEqual(artifact["status"], "SYNTHESIS_REJECTED")

    def test_checker_accepts_valid_synthesis_without_publication_pass(self):
        runtime = load_module()
        artifact = runtime.produce_synthesis(
            "packet-1",
            reports(),
            packet_check(),
            synthesis_provider_id="synthesis:publication-review",
            checker_id="checker:publication-review",
        )
        result = runtime.check_synthesis(
            artifact,
            reports(),
            packet_check(),
            checker_id="checker:publication-review",
        )
        self.assertEqual(result["status"], "SYNTHESIS_ACCEPTED")
        self.assertFalse(result["graph_transition_authorized"])
        self.assertFalse(result["publication_pass"])

    def test_checker_rejects_packet_mismatch(self):
        runtime = load_module()
        artifact = runtime.produce_synthesis(
            "packet-1",
            reports(),
            packet_check(),
            synthesis_provider_id="synthesis:publication-review",
            checker_id="checker:publication-review",
        )
        result = runtime.check_synthesis(
            artifact,
            reports(),
            packet_check(packet_id="packet-2"),
            checker_id="checker:publication-review",
        )
        self.assertEqual(result["status"], "SYNTHESIS_REJECTED")
        self.assertTrue(any("packet" in item.lower() for item in result["findings"]))

    def test_checker_rejects_missing_source_finding(self):
        runtime = load_module()
        artifact = runtime.produce_synthesis(
            "packet-1",
            reports(),
            packet_check(),
            synthesis_provider_id="synthesis:publication-review",
            checker_id="checker:publication-review",
        )
        artifact["source_finding_ids"] = ["F-1"]
        result = runtime.check_synthesis(
            artifact,
            reports(),
            packet_check(),
            checker_id="checker:publication-review",
        )
        self.assertEqual(result["status"], "SYNTHESIS_REJECTED")
        self.assertTrue(any("finding" in item.lower() for item in result["findings"]))

    def test_checker_does_not_rewrite_malformed_artifact(self):
        runtime = load_module()
        artifact = runtime.produce_synthesis(
            "packet-1",
            reports(),
            packet_check(),
            synthesis_provider_id="synthesis:publication-review",
            checker_id="checker:publication-review",
        )
        artifact["findings"] = artifact["findings"][:-1]
        before = copy.deepcopy(artifact)
        result = runtime.check_synthesis(
            artifact,
            reports(),
            packet_check(),
            checker_id="checker:publication-review",
        )
        self.assertEqual(result["status"], "SYNTHESIS_REJECTED")
        self.assertEqual(artifact, before)

    def test_unavailable_isolation_is_conditional_not_accepted(self):
        runtime = load_module()
        artifact = runtime.produce_synthesis(
            "packet-1",
            reports(),
            packet_check(isolation_status="UNAVAILABLE"),
            synthesis_provider_id="synthesis:publication-review",
            checker_id="checker:publication-review",
        )
        result = runtime.check_synthesis(
            artifact,
            reports(),
            packet_check(isolation_status="UNAVAILABLE"),
            checker_id="checker:publication-review",
        )
        self.assertEqual(result["status"], "SYNTHESIS_CONDITIONAL")

    def test_schema_declares_producer_and_checker_separation(self):
        import json

        schema = json.loads(
            (ROOT / "assets" / "schemas" / "review_synthesis.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("producer_id", schema["required"])
        self.assertIn("checker_id", schema["required"])
        self.assertIn("source_report_hashes", schema["required"])


if __name__ == "__main__":
    unittest.main()
