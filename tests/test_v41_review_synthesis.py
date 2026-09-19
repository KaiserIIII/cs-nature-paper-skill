import copy
import hashlib
import importlib.util
import json
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


def load_checker():
    spec = importlib.util.spec_from_file_location(
        "review_synthesis_checker", ROOT / "scripts" / "review_synthesis_checker.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rehash(artifact):
    unsigned = {key: value for key, value in artifact.items() if key != "synthesis_hash"}
    payload = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    artifact["synthesis_hash"] = "sha256:" + hashlib.sha256(payload).hexdigest()


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
        self.assertEqual(
            artifact["reviewer_producer_ids"],
            ["reviewer:domain", "reviewer:methods"],
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

    def test_empty_reviewer_set_is_rejected(self):
        runtime = load_module()
        artifact = runtime.produce_synthesis(
            "packet-1",
            [],
            packet_check(report_hashes=[]),
            synthesis_provider_id="synthesis:publication-review",
            checker_id="checker:publication-review",
        )
        self.assertEqual(artifact["status"], "SYNTHESIS_REJECTED")

    def test_public_entries_reject_non_list_reports_without_raising(self):
        producer = load_module()
        checker = load_checker()
        valid_artifact = producer.produce_synthesis(
            "packet-1",
            reports(),
            packet_check(),
            synthesis_provider_id="synthesis:publication-review",
            checker_id="checker:publication-review",
        )
        for malformed in (None, {}, "reports", 7):
            with self.subTest(entry="producer", malformed=malformed):
                produced = producer.produce_synthesis(
                    "packet-1",
                    malformed,
                    packet_check(),
                    synthesis_provider_id="synthesis:publication-review",
                    checker_id="checker:publication-review",
                )
                self.assertEqual(produced["status"], "SYNTHESIS_REJECTED")
            with self.subTest(entry="checker", malformed=malformed):
                checked = checker.check_synthesis(
                    valid_artifact,
                    malformed,
                    packet_check(),
                    checker_id="checker:publication-review",
                )
                self.assertEqual(checked["status"], "SYNTHESIS_REJECTED")

    def test_public_entries_reject_non_object_packet_checks_without_raising(self):
        producer = load_module()
        checker = load_checker()
        valid_artifact = producer.produce_synthesis(
            "packet-1",
            reports(),
            packet_check(),
            synthesis_provider_id="synthesis:publication-review",
            checker_id="checker:publication-review",
        )
        for malformed in (None, [], "packet-check", 7):
            with self.subTest(entry="producer", malformed=malformed):
                produced = producer.produce_synthesis(
                    "packet-1",
                    reports(),
                    malformed,
                    synthesis_provider_id="synthesis:publication-review",
                    checker_id="checker:publication-review",
                )
                self.assertEqual(produced["status"], "SYNTHESIS_REJECTED")
            with self.subTest(entry="checker", malformed=malformed):
                checked = checker.check_synthesis(
                    valid_artifact,
                    reports(),
                    malformed,
                    checker_id="checker:publication-review",
                )
                self.assertEqual(checked["status"], "SYNTHESIS_REJECTED")

    def test_synthesis_producer_cannot_be_a_reviewer(self):
        runtime = load_module()
        artifact = runtime.produce_synthesis(
            "packet-1",
            reports(),
            packet_check(),
            synthesis_provider_id="reviewer:methods",
            checker_id="checker:publication-review",
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

    def test_independent_checker_rejects_dropped_group_after_self_rehash(self):
        producer = load_module()
        checker = load_checker()
        artifact = producer.produce_synthesis(
            "packet-1",
            reports(),
            packet_check(),
            synthesis_provider_id="synthesis:publication-review",
            checker_id="checker:publication-review",
        )
        artifact["findings"] = artifact["findings"][:-1]
        rehash(artifact)
        before = copy.deepcopy(artifact)

        result = checker.check_synthesis(
            artifact,
            reports(),
            packet_check(),
            checker_id="checker:publication-review",
        )

        self.assertEqual(result["status"], "SYNTHESIS_REJECTED")
        self.assertTrue(any("finding" in item.lower() for item in result["findings"]))
        self.assertEqual(artifact, before)

    def test_independent_checker_cannot_be_a_reviewer(self):
        producer = load_module()
        checker = load_checker()
        artifact = producer.produce_synthesis(
            "packet-1",
            reports(),
            packet_check(),
            synthesis_provider_id="synthesis:publication-review",
            checker_id="reviewer:domain",
        )

        result = checker.check_synthesis(
            artifact,
            reports(),
            packet_check(),
            checker_id="reviewer:domain",
        )

        self.assertEqual(result["status"], "SYNTHESIS_REJECTED")
        self.assertTrue(any("reviewer" in item.lower() for item in result["findings"]))

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
        self.assertIn("reviewer_producer_ids", schema["required"])
        self.assertIn("source_report_hashes", schema["required"])


if __name__ == "__main__":
    unittest.main()
