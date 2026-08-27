import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(module); return module


router = load("skill_router")
method = load("method_router")
anchor = load("evidence_anchor")
planner = load("experiment_planner")
handoff = load("handoff_runtime")
privacy = load("privacy_lint")
smoke_check = load("check_smoke")


class HardeningRegressionTests(unittest.TestCase):
    def test_provisional_cannot_produce_formal_evidence(self):
        result = router.resolve("statistical-modeling", purpose="formal", load_bearing=True, criticality="critical")
        self.assertEqual(result["status"], "CONDITIONAL")
        self.assertEqual(result["selected"], [])

    def test_static_specialist_is_not_formally_qualified(self):
        result = router.resolve("literature-discovery", purpose="formal", load_bearing=True)
        self.assertEqual(result["status"], "CONDITIONAL")

    def test_method_zero_hit_and_ambiguous(self):
        self.assertEqual(method.route("something unrelated") ["method"], None)
        result = method.route("repository data causal effect LLM benchmark")
        self.assertEqual(result["status"], "CONDITIONAL")
        self.assertTrue(result["specialist_required"])
        self.assertGreater(len(result["candidate_methods"]), 1)

    def test_fake_hash_and_declared_execution_are_rejected_for_observed(self):
        value = {"anchor_id":"A","claim_id":"C","result_id":"R","source_artifact":"x","exact_region":"line 1","transformation":"none","provenance_level":"OBSERVED","uncertainty":"u","scope":"s","status":"OBSERVED","config_hash":"sha256:config","input_hash":"sha256:input"}
        result = anchor.validate_anchor(value)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("execution_record_id" in item for item in result["findings"]))

    def test_handoff_requires_pinned_ref_and_outputs(self):
        result = handoff.validate({"producer":"p","skill":"s","exact_ref":"main","capability":"c","input_artifacts":[],"output_artifacts":[],"commands":[],"assumptions":[],"uncertainty":[],"permission_use":{},"evidence_anchors":[],"verification":{},"checker":""})
        self.assertEqual(result["status"], "FAIL")

    def test_privacy_lint_and_stale_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path = root / "public.json"; path.write_text(json.dumps({"path":"C:\\\\Users\\\\alice\\\\private.txt"}), encoding="utf-8")
            self.assertEqual(privacy.lint([path], root)["status"], "FAIL")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "smoke.json"; path.write_text(json.dumps({"skill_commit":"wrong","status":"PASS"}), encoding="utf-8")
            result = smoke_check.check(path, ROOT)
            self.assertEqual(result["status"], "STALE")

    def test_literature_and_planner_regressions(self):
        lit = load("literature_runtime")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lit.json"; path.write_text(json.dumps({"schema_version":1,"skill_version":"3.1.1","sources":[{"source_id":"S","discovery_source":"snippet","identity":{"title":"t"}}]}), encoding="utf-8")
            self.assertEqual(lit.verify_claim(path, "S", "C", "SUPPORTS", "abstract", "ABSTRACT_ONLY")["status"], "CONDITIONAL")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "exp.json"; path.write_text(json.dumps({"experiments":[{"experiment_id":"E","claim_ids":["C"],"threat":"t","priority":1.2345}]}), encoding="utf-8")
            self.assertEqual(planner.audit(path)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
