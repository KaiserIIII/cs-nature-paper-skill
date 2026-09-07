import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "research_os_benchmark", ROOT / "scripts" / "research_os_benchmark.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


benchmark = load_module()


class V4BenchmarkSuiteTests(unittest.TestCase):
    def test_suite_has_six_pinned_behavior_benchmarks(self):
        suite = benchmark.load_suite()
        systems = {item["id"]: item for item in suite["systems"]}
        self.assertEqual(
            set(systems),
            {
                "ars",
                "k_dense",
                "ai_scientist",
                "paper_orchestra",
                "sisyphus_academica",
                "research_engineering_suite",
            },
        )
        self.assertEqual(
            systems["ars"]["exact_commit"],
            "6b7ee6dcae29c0fbb46e0017538f9cef84c3136b",
        )
        for item in systems.values():
            self.assertRegex(item["exact_commit"], r"^[0-9a-f]{40}$")
            self.assertTrue(item["strongest_capabilities"])
            self.assertTrue(item["behavior_task"]["public_inputs"])
            self.assertTrue(item["parity_dimensions"])
            self.assertTrue(item["superiority_dimensions"])
        self.assertEqual(benchmark.validate_suite(suite), [])

    def test_ars_is_benchmark_only_and_covers_required_quality_dimensions(self):
        suite = benchmark.load_suite()
        ars = next(item for item in suite["systems"] if item["id"] == "ars")
        self.assertEqual(ars["license"], "CC-BY-NC-4.0")
        self.assertEqual(ars["use_decision"], "BENCHMARK_ONLY_DO_NOT_VENDOR")
        self.assertEqual(
            set(ars["parity_dimensions"]),
            {
                "evidence_depth",
                "citation_faithfulness",
                "closest_work_coverage",
                "manuscript_structure",
                "writing_depth",
                "reviewer_attack_quality",
                "unsupported_claim_detection",
                "revision_quality",
            },
        )
        serialized = json.dumps(suite).lower()
        for forbidden in ("agent_count", "code_size", "skill_count", "architecture_score"):
            self.assertNotIn(forbidden, serialized)

    def test_missing_real_runs_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            result = benchmark.evaluate_run(benchmark.load_suite(), Path(td))
        self.assertEqual(result["ars_parity_gate"], "FAIL")
        self.assertEqual(result["v4_superiority_gate"], "FAIL")
        self.assertEqual(result["rc_status"], "FAIL")
        self.assertEqual(result["recommended_merge"], "NO")
        self.assertTrue(any("NOT_RUN" in finding for finding in result["findings"]))

    def test_counterbalanced_hash_bound_judgments_can_pass(self):
        suite = benchmark.load_suite()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for system in suite["systems"]:
                run = root / system["id"]
                run.mkdir(parents=True)
                benchmark_output = run / "benchmark_output.json"
                v4_output = run / "v4_output.json"
                benchmark_output.write_text('{"result":"benchmark"}\n', encoding="utf-8")
                v4_output.write_text('{"result":"v4"}\n', encoding="utf-8")
                hashes = {
                    "benchmark": "sha256:" + hashlib.sha256(benchmark_output.read_bytes()).hexdigest(),
                    "v4": "sha256:" + hashlib.sha256(v4_output.read_bytes()).hexdigest(),
                }
                (run / "run_manifest.json").write_text(
                    json.dumps(
                        {
                            "status": "COMPLETED",
                            "task_id": system["behavior_task"]["id"],
                            "system_id": system["id"],
                            "producer_runs": {
                                "benchmark": {"model": "test-producer", "output_sha256": hashes["benchmark"]},
                                "v4": {"model": "test-producer", "output_sha256": hashes["v4"]},
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                dimensions = set(system["parity_dimensions"]) | set(system["superiority_dimensions"])
                verdicts = {name: "V4_BETTER" for name in dimensions}
                for filename, order in (
                    ("judge_ab.json", ["benchmark", "v4"]),
                    ("judge_ba.json", ["v4", "benchmark"]),
                ):
                    (run / filename).write_text(
                        json.dumps(
                            {
                                "status": "COMPLETED",
                                "judge_model": "test-judge",
                                "order": order,
                                "input_sha256": hashes,
                                "verdicts": verdicts,
                                "evidence": {name: "artifact-grounded comparison" for name in dimensions},
                            }
                        ),
                        encoding="utf-8",
                    )
            result = benchmark.evaluate_run(suite, root)
        self.assertEqual(result["ars_parity_gate"], "PASS")
        self.assertEqual(result["v4_superiority_gate"], "PASS")
        self.assertEqual(result["rc_status"], "PASS")
        self.assertEqual(result["recommended_merge"], "YES")


if __name__ == "__main__":
    unittest.main()
