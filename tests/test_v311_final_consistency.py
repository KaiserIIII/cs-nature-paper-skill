import hashlib
import importlib.util
import json
import subprocess
import sys
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


anchor = load("evidence_anchor")
graph = load("research_graph")
literature = load("literature_runtime")
smoke = load("smoke_run")
release = load("validate_release")
manifest = load("build_manifest")


def base_anchor(**changes):
    value = {
        "anchor_id": "EA-1",
        "claim_id": "C1",
        "result_id": "R1",
        "source_artifact": "result.txt",
        "exact_region": "line 1",
        "transformation": "identity",
        "uncertainty": "fixture only",
        "scope": "fixture",
        "status": "VERIFIED",
    }
    value.update(changes)
    return value


def new_registry(path):
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "skill_version": "3.1.1",
                "sources": [
                    {
                        "source_id": "S1",
                        "stable_identifier": "fixture:source-1",
                        "verification_status": "IDENTITY_VERIFIED",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


class FinalConsistencyRegressionTests(unittest.TestCase):
    def test_ci_uploads_hidden_smoke_artifact(self):
        """CI artifacts must retain the hidden smoke result used for provenance checks."""
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("include-hidden-files: true", workflow)

    def test_ci_runs_competition_smoke_and_uploads_its_hidden_artifact(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "python scripts/competition_smoke_run.py --output .competition-smoke-result.json",
            workflow,
        )
        self.assertIn(".competition-smoke-result.json", workflow)

    def test_competition_schemas_map_to_release_validation_instances(self):
        expected = {
            "competition_clock": ROOT
            / "assets/templates/competition/competition_clock.json",
            "competition_method_router": ROOT
            / "assets/registry/competition_method_router.json",
            "competition_profile": ROOT / "assets/competition/cumcm_profile.json",
            "competition_review": ROOT
            / "assets/templates/competition/competition_review.json",
            "competition_rules": ROOT
            / "assets/templates/competition/competition_rules.json",
            "competition_state": ROOT
            / "assets/templates/competition/competition_state.json",
        }

        actual = {
            stem: release.schema_instance_path(stem, ROOT) for stem in expected
        }

        self.assertEqual(actual, expected)
        self.assertTrue(all(path.exists() for path in actual.values()))

    def test_competition_smoke_result_is_not_release_controlled_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            generated = [
                root / ".competition-smoke-result.json",
                root / ".competition-orchestration-e2e.json",
            ]
            for path in generated:
                path.write_text("{}\n", encoding="utf-8")

            self.assertTrue(
                all(not manifest.is_release_controlled(path, root) for path in generated)
            )

    def test_repository_release_manifest_is_explicitly_unresolved(self):
        manifest = json.loads((ROOT / "release_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest.get("source_commit_mode"), "publisher-injected")
        self.assertEqual(manifest.get("source_commit"), "release-process-injected")

    def test_publisher_generates_a_resolved_release_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "resolved_release_manifest.json"
            commit = "a" * 40
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "resolve_release_manifest.py"),
                    "--source-commit",
                    commit,
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            resolved = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(resolved["source_commit"], commit)
            self.assertEqual(resolved["source_commit_mode"], "resolved")

    def test_committed_benchmark_cannot_be_stale(self):
        """COMMITTED-BENCHMARK-CANNOT-BE-STALE"""
        self.assertFalse((ROOT / "benchmarks" / "smoke-run-result.json").exists())
        self.assertNotIn("benchmarks/smoke-run-result.json", manifest.EXCLUDED_FILES)

    def test_release_validation_rejects_a_committed_runtime_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "benchmarks").mkdir()
            (root / "benchmarks" / "smoke-run-result.json").write_text("{}", encoding="utf-8")
            validator = getattr(release, "validate_runtime_results", lambda _root: None)
            result = validator(root)
            self.assertEqual(result, ["benchmarks/smoke-run-result.json is a generated runtime artifact and must not be committed"])

    def test_command_must_produce_declared_output(self):
        """COMMAND-MUST-PRODUCE-DECLARED-OUTPUT"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "no_output.py"
            script.write_text("print('ran')\n", encoding="utf-8")
            output = root / "declared.txt"
            record = anchor.execution_record(
                root / "record.json",
                [sys.executable, str(script)],
                cwd=root,
                output_paths=[output],
            )
            self.assertEqual(record.get("status"), "FAIL")
            self.assertTrue(any("did not create" in item for item in record.get("findings", [])))

    def test_preexisting_output_cannot_be_claimed_as_execution_produced(self):
        """PREEXISTING-OUTPUT-CANNOT-BE-CLAIMED-AS-EXECUTION-PRODUCED"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "declared.txt"
            output.write_text("old\n", encoding="utf-8")
            marker = root / "command-ran.txt"
            script = root / "writer.py"
            script.write_text(
                "from pathlib import Path\n"
                "Path('command-ran.txt').write_text('yes', encoding='utf-8')\n"
                "Path('declared.txt').write_text('new', encoding='utf-8')\n",
                encoding="utf-8",
            )
            with self.assertRaises(anchor.AnchorError):
                anchor.execution_record(
                    root / "record.json",
                    [sys.executable, str(script)],
                    cwd=root,
                    output_paths=[output],
                )
            self.assertFalse(marker.exists(), "the command must not run after preflight rejection")

    def test_execution_anchor_must_reference_the_generated_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            generated = root / "generated.txt"
            generated.write_text("generated\n", encoding="utf-8")
            other = root / "result.txt"
            other.write_text("unrelated\n", encoding="utf-8")
            generated_hash = hashlib.sha256(generated.read_bytes()).hexdigest()
            other_hash = hashlib.sha256(other.read_bytes()).hexdigest()
            record_path = root / "record.json"
            record_path.write_text(
                json.dumps(
                    {
                        "record_id": "record",
                        "status": "PASS",
                        "command": "python writer.py generated.txt",
                        "cwd": str(root),
                        "exit_status": 0,
                        "started_utc": "2026-08-27T00:00:00Z",
                        "finished_utc": "2026-08-27T00:00:01Z",
                        "stdout_sha256": "sha256:" + "0" * 64,
                        "stderr_sha256": "sha256:" + "0" * 64,
                        "outputs": [
                            {
                                "path": "generated.txt",
                                "sha256": "sha256:" + generated_hash,
                                "produced_by_command": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            value = base_anchor(
                provenance_level="OBSERVED",
                status="OBSERVED",
                source_artifact=f"result.txt#sha256={other_hash}",
                execution_record_id="record.json",
                command="python writer.py generated.txt",
                cwd=str(root),
                exit_status=0,
            )
            result = anchor.deep_validate_anchor(value, root)
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("produced output" in item for item in result["findings"]))

    def test_legacy_verified_migrates_to_declared(self):
        """LEGACY-VERIFIED-MIGRATES-TO-DECLARED"""
        result = anchor.validate_anchor(base_anchor())
        self.assertEqual(result["provenance_level"], "DECLARED")
        self.assertEqual(result["legacy_status"], "VERIFIED")
        self.assertEqual(result["migration_state"], "LEGACY_DECLARED")

    def test_legacy_verified_cannot_support_formal_pass(self):
        """LEGACY-VERIFIED-CANNOT-SUPPORT-FORMAL-PASS"""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            state = project / ".research-state"
            state.mkdir()
            legacy = base_anchor(
                artifact_type="formal_output",
                execution_record_id="record.json",
            )
            (state / "evidence_ledger.json").write_text(
                json.dumps({"anchors": [legacy]}), encoding="utf-8"
            )
            findings = graph._pass_evidence_findings(
                project,
                {"id": "formal_experiment"},
                "EA-1",
                "runtime",
            )
            self.assertTrue(any("not strong enough" in item for item in findings))

    def test_declared_cannot_be_upgraded_without_observation(self):
        """DECLARED-CANNOT-BE-UPGRADED-WITHOUT-OBSERVATION"""
        result = anchor.validate_anchor(
            base_anchor(provenance_level="OBSERVED", status="OBSERVED")
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("execution_record_id" in item for item in result["findings"]))

    def test_verified_requires_independent_reverification_inputs(self):
        result = anchor.validate_anchor(
            base_anchor(
                provenance_level="VERIFIED",
                execution_record_id="record.json",
                command="python writer.py result.txt",
                cwd="<TEMP_PROJECT>",
                exit_status=0,
            )
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("checker" in item for item in result["findings"]))

    def test_claim_relation_without_retrieval_is_not_verified(self):
        """CLAIM-RELATION-WITHOUT-RETRIEVAL-IS-NOT-VERIFIED"""
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "literature.json"
            new_registry(registry)
            result = literature.verify_claim(
                registry,
                "S1",
                "C1",
                "SUPPORTS",
                "line 1",
                source_uri="fixture://source-1",
                inspection_actor="inspector",
            )
            self.assertEqual(result["status"], "CONDITIONAL")
            self.assertEqual(result["verification_status"], "CLAIM_RELATION_RECORDED")

    def test_invalid_region_cannot_verify_claim(self):
        """INVALID-REGION-CANNOT-VERIFY-CLAIM"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "literature.json"
            source = root / "source.txt"
            source.write_text("only one line\n", encoding="utf-8")
            new_registry(registry)
            result = literature.verify_claim(
                registry,
                "S1",
                "C1",
                "SUPPORTS",
                "line 9",
                source_uri=str(source),
                source_hash=hashlib.sha256(source.read_bytes()).hexdigest(),
                inspection_actor="inspector",
            )
            self.assertEqual(result["status"], "FAIL")
            self.assertNotEqual(result["verification_status"], "CLAIM_RELATION_VERIFIED")

    def test_source_hash_mismatch_fails_literature_verification(self):
        """SOURCE-HASH-MISMATCH-FAILS-LITERATURE-VERIFICATION"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "literature.json"
            source = root / "source.txt"
            source.write_text("source text\n", encoding="utf-8")
            new_registry(registry)
            result = literature.verify_claim(
                registry,
                "S1",
                "C1",
                "SUPPORTS",
                "line 1",
                source_uri=str(source),
                source_hash="0" * 64,
                inspection_actor="inspector",
            )
            self.assertEqual(result["status"], "FAIL")
            self.assertNotEqual(result["verification_status"], "CLAIM_RELATION_VERIFIED")

    def test_retrieval_record_binds_source_and_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "literature.json"
            source = root / "source.txt"
            source.write_text("first line\nsecond line\n", encoding="utf-8")
            new_registry(registry)
            retrieval = literature.record_retrieval(
                registry,
                "S1",
                source,
                retrieval_method="local-open",
                source_uri="fixture://source-1",
                inspection_actor="retriever",
            )
            self.assertEqual(retrieval["status"], "PASS")
            self.assertEqual(retrieval["record"].get("stable_identifier"), "fixture:source-1")
            result = literature.verify_claim(
                registry,
                "S1",
                "C1",
                "SUPPORTS",
                "lines 1-2",
                retrieval_record_id=retrieval["retrieval_id"],
                source_uri="fixture://source-1",
                inspection_actor="inspector",
                checker="independent-checker",
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["verification_status"], "CLAIM_RELATION_VERIFIED")
            self.assertEqual(literature.audit(registry)["status"], "PASS")
            source.write_text("tampered\n", encoding="utf-8")
            tampered = literature.verify_claim(
                registry,
                "S1",
                "C2",
                "SUPPORTS",
                "line 1",
                retrieval_record_id=retrieval["retrieval_id"],
                source_uri="fixture://source-1",
                inspection_actor="inspector",
                checker="independent-checker",
            )
            self.assertEqual(tampered["status"], "FAIL")
            self.assertEqual(literature.audit(registry)["status"], "FAIL")

    def test_abstract_only_remains_conditional(self):
        """ABSTRACT-ONLY-REMAINS-CONDITIONAL"""
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "literature.json"
            new_registry(registry)
            result = literature.verify_claim(
                registry,
                "S1",
                "C1",
                "PARTIALLY_SUPPORTS",
                "line 1",
                "ABSTRACT_ONLY",
                source_uri="fixture://source-1",
                inspection_actor="inspector",
            )
            self.assertEqual(result["status"], "CONDITIONAL")
            self.assertNotEqual(result["verification_status"], "CLAIM_RELATION_VERIFIED")

    def test_snippet_only_cannot_become_verified_support(self):
        """SNIPPET-ONLY-CANNOT-BECOME-VERIFIED-SUPPORT"""
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "literature.json"
            new_registry(registry)
            result = literature.verify_claim(
                registry,
                "S1",
                "C1",
                "SUPPORTS",
                "line 1",
                "SNIPPET_ONLY",
                source_uri="fixture://source-1",
                inspection_actor="inspector",
            )
            self.assertNotEqual(result["verification_status"], "CLAIM_RELATION_VERIFIED")

    def test_true_e2e_reports_command_generated_output(self):
        result = smoke.run()
        execution = result["execution_record"]
        self.assertEqual(execution.get("status"), "PASS")
        self.assertEqual(len(execution.get("outputs", [])), 1)
        self.assertTrue(execution["outputs"][0]["produced_by_command"])
        self.assertRegex(execution["outputs"][0]["sha256"], r"^sha256:[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
