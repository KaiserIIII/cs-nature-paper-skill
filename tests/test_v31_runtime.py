import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


evidence_anchor = load("evidence_anchor")
eval_runner = load("eval_runner")
experiment_planner = load("experiment_planner")
job_runtime = load("job_runtime")
research_graph = load("research_graph")
research_state = load("research_state")
review_runtime = load("review_runtime")
skill_router = load("skill_router")


class RuntimeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.project = self.root / "project"
        self.project.mkdir()
        research_state.init_state(self.project, "empirical", "copilot", "systems")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_router_selects_smallest_provider_and_quarantines_bad_plan(self):
        result = skill_router.resolve("statistical-modeling")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["selected"][0]["skill_id"], "k-dense-statistics")
        plan = self.root / "delegation_plan.json"
        plan.write_text(json.dumps({
            "task": "analysis", "capability": "statistical-modeling",
            "employee": "academic-research-skills-codex", "exact_ref": "main",
            "input_artifacts": ["protocol"], "allowed_context": ["private review letters"],
            "forbidden_context": [], "allowed_tools": [], "forbidden_tools": [],
            "expected_output": "report", "output_schema": "handoff.json", "checker": "methodologist",
            "timeout": "10m", "cost_budget": 0, "failure_path": "block", "rollback": "native"
        }), encoding="utf-8")
        self.assertEqual(skill_router.validate_plan(plan)["status"], "FAIL")

    def test_graph_advance_records_conditional_feasibility_actions(self):
        research_graph.transition(self.project, "brief", "PASS", "brief complete", "test", "EA-brief")
        plan = research_graph.plan_next(self.project)
        self.assertEqual({"literature", "innovation"} <= set(plan["ready"]), True)
        contract_path = self.project / ".research-state" / "research_contract.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        contract["feasibility"]["decision"] = "NO_GO"
        contract_path.write_text(json.dumps(contract), encoding="utf-8")
        result = research_graph.advance(self.project)
        changed = {(item["node"], item["to"]) for item in result["changed"]}
        self.assertIn(("innovation", "REOPENED"), changed)
        self.assertIn(("formal_experiment", "BLOCKED"), changed)
        self.assertTrue((self.project / ".research-state" / ".research-graph-events.jsonl").exists())

    def test_graph_rebuild_rejects_tampered_event(self):
        research_graph.transition(self.project, "brief", "PASS", "brief complete", "test", "EA-brief")
        event_path = self.project / ".research-state" / ".research-graph-events.jsonl"
        event = json.loads(event_path.read_text(encoding="utf-8").splitlines()[0])
        event["reason"] = "tampered"
        event_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
        self.assertEqual(research_graph.rebuild(self.project)["status"], "FAIL")

    def test_deep_anchor_checks_hash_and_external_is_conditional(self):
        artifact = self.project / "result.txt"
        artifact.write_text("verified output\n", encoding="utf-8")
        import hashlib
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        anchor = {
            "anchor_id": "EA-1", "claim_id": "C1", "result_id": "R1",
            "source_artifact": f"result.txt#sha256={digest}", "exact_region": "line 1",
            "transformation": "none", "command": "python run.py", "exit_status": 0,
            "code_commit": "abc123", "config_hash": "sha256:config", "environment": "local",
            "input_hash": "sha256:input", "uncertainty": "fixture", "scope": "fixture",
            "status": "VERIFIED", "verified_utc": "2026-08-27T00:00:00Z"
        }
        self.assertEqual(evidence_anchor.deep_validate_anchor(anchor, self.project)["status"], "PASS")
        anchor["source_artifact"] = "https://example.org/result.txt"
        self.assertEqual(evidence_anchor.deep_validate_anchor(anchor, self.project)["status"], "CONDITIONAL")

    def test_planner_drops_unlinked_outcome_independent_work(self):
        options = self.root / "options.json"
        options.write_text(json.dumps({"experiments": [
            {"experiment_id": "E1", "threat": "claim falsifier", "claim_ids": ["C1"], "information_gain": 2, "cost": 1},
            {"experiment_id": "E2", "threat": "looks interesting", "claim_ids": [], "outcome_independent": True}
        ]}), encoding="utf-8")
        result = experiment_planner.plan(options)
        self.assertEqual([item["experiment_id"] for item in result["selected"]], ["E1"])
        self.assertEqual(result["dropped"][0]["experiment_id"], "E2")

    def test_job_resume_and_completion_require_real_output(self):
        output = self.root / "output.txt"
        manifest = self.root / "job.json"
        job_runtime.init(manifest, "python run.py", [str(output)])
        job_runtime.checkpoint(manifest, "pilot", 0.5, [])
        self.assertEqual(job_runtime.resume(manifest)["status"], "READY")
        self.assertEqual(job_runtime.complete(manifest, 0)["status"], "FAIL")
        output.write_text("done\n", encoding="utf-8")
        self.assertEqual(job_runtime.complete(manifest, 0)["status"], "VERIFIED")

    def test_behavior_runner_hides_rubric_and_rejects_acceptance_theater(self):
        cases = self.root / "cases.json"
        prepared = self.root / "prepared"
        cases.write_text(json.dumps({"cases": [{
            "id": "CASE-1", "prompt": "route", "fixture": {},
            "required_behaviors": ["evidence boundary"],
            "forbidden_behaviors": ["acceptance probability"], "required_artifacts": ["brief"]
        }]}), encoding="utf-8")
        eval_runner.prepare(cases, prepared)
        public = json.loads((prepared / "CASE-1.json").read_text(encoding="utf-8"))
        self.assertNotIn("required_behaviors", public)
        answer = self.root / "answer.txt"
        answer.write_text("I report the evidence boundary.", encoding="utf-8")
        eval_runner.run_record(prepared / "manifest.json", "CASE-1", answer, model="deterministic", host="local", reasoning_mode="test", network=False, tools=[])
        eval_runner.score(cases, prepared / "runs", self.root / "score.json")
        self.assertEqual(eval_runner.report(self.root / "score.json")["status"], "PASS")

    def test_review_runtime_uses_threats_and_rejects_theater(self):
        selected = review_runtime.select(["statistics", "leakage", "prior_art"])
        self.assertIn("Statistics attack", selected["attacks"])
        finding = self.root / "finding.json"
        finding.write_text(json.dumps({"findings": [{
            "id": "F1", "role": "methodologist", "severity": "MAJOR", "anchor": "EA-1",
            "affected_claim": "C1", "problem": "unclear estimand", "evidence": "protocol",
            "uncertainty": "unknown", "smallest_sufficient_fix": "define estimand",
            "new_data_required": False, "verification": "rerun audit", "residual_risk": "sampling"
        }]}), encoding="utf-8")
        self.assertEqual(review_runtime.audit(finding)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
