import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import competition_director
import competition_method_router
import competition_quality
import competition_runtime
import research_state


NOW = datetime(2026, 9, 10, 16, 0, tzinfo=timezone.utc)


def official_rules():
    rule_ids = (
        "contest_time",
        "problem_count",
        "participant_eligibility",
        "ai_policy",
        "paper_format",
        "page_limit",
        "file_naming",
        "attachments",
        "code_requirements",
        "submission_platform",
        "submission_method",
        "anonymity",
        "discipline",
    )
    return [
        {
            "rule_id": rule_id,
            "value": f"fixture value for {rule_id}",
            "source_type": "OFFICIAL_PRIMARY",
            "official_source": "fixture://official-cumcm/2026-rules",
            "retrieved_utc": "2026-09-10T08:00:00Z",
            "exact_region": f"rules#{rule_id}",
        }
        for rule_id in rule_ids
    ]


def contest_input():
    return {
        "provider_mode": "fixture",
        "competition": "CUMCM",
        "contest_start_utc": "2026-09-10T08:00:00Z",
        "submission_deadline_utc": "2026-09-13T08:00:00Z",
        "official_rules_source": "fixture://official-cumcm/2026-rules",
        "rules": official_rules(),
        "problems": [
            {
                "id": "A",
                "title": "Opaque sparse-data task",
                "decision_profile": {
                    "understanding_difficulty": "HIGH",
                    "data_availability": "LOW",
                    "implementation_difficulty": "HIGH",
                    "validation_feasibility": "LOW",
                    "paper_potential": "MEDIUM",
                    "interpretability": "LOW",
                    "completion_risk": "HIGH",
                    "capability_fit": "LOW",
                },
                "questions": [{"id": "A-Q1", "goal": "infer an unspecified mechanism"}],
            },
            {
                "id": "B",
                "title": "Facility evaluation, demand forecast, and allocation",
                "decision_profile": {
                    "understanding_difficulty": "LOW",
                    "data_availability": "HIGH",
                    "implementation_difficulty": "LOW",
                    "validation_feasibility": "HIGH",
                    "paper_potential": "HIGH",
                    "interpretability": "HIGH",
                    "completion_risk": "LOW",
                    "capability_fit": "HIGH",
                },
                "sites": [
                    {"id": "A", "capacity": 105.0, "fixed_cost": 12.0, "distance": 8.0},
                    {"id": "B", "capacity": 125.0, "fixed_cost": 14.0, "distance": 5.0},
                    {"id": "C", "capacity": 145.0, "fixed_cost": 19.0, "distance": 4.0},
                ],
                "demand_history": [92.0, 96.0, 100.0, 104.0],
                "questions": [
                    {"id": "B-Q1", "goal": "evaluate candidate facilities"},
                    {"id": "B-Q2", "goal": "forecast next-period demand"},
                    {"id": "B-Q3", "goal": "optimize facility choice and allocation"},
                    {"id": "B-Q4", "goal": "test sensitivity and scenarios"},
                ],
            },
        ],
    }


class CompetitionFinalSpecializationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.project = Path(self.tempdir.name)
        research_state.init_state(
            self.project,
            "algorithmic",
            "competition-autopilot",
            "mathematical-modeling",
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_only_current_official_primary_sources_can_verify_rules(self):
        records = official_rules()
        records[0] = records[0] | {"source_type": "PRIOR_YEAR_RULE"}

        result = competition_runtime.verify_rule_records(
            self.project, records, actor="competition-rule-verifier", now_utc=NOW
        )

        self.assertEqual(result["rules"]["contest_time"]["status"], "BACKGROUND_ONLY")
        self.assertEqual(result["status"], "CONDITIONAL")
        self.assertIn("contest_time", result["unverified"])
        self.assertEqual(result["rules"]["ai_policy"]["status"], "VERIFIED")
        self.assertEqual(result["rules"]["ai_policy"]["exact_region"], "rules#ai_policy")

    def test_official_extension_is_a_hash_chained_clock_event(self):
        competition_runtime.configure_clock(
            self.project,
            "2026-09-10T08:00:00Z",
            "2026-09-13T08:00:00Z",
            "https://official.example/rules",
            "competition-director",
            now_utc=NOW,
        )
        result = competition_runtime.official_extension(
            self.project,
            "2026-09-13T10:00:00Z",
            "https://official.example/extension",
            "official two-hour extension",
            "competition-rule-verifier",
            now_utc=NOW,
        )
        events = [
            json.loads(line)
            for line in (self.project / ".research-state" / ".competition-clock-events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]

        self.assertEqual(result["clock"]["submission_deadline_utc"], "2026-09-13T10:00:00Z")
        self.assertEqual(events[-1]["event_type"], "OFFICIAL_EXTENSION")
        self.assertIn("before", events[-1])
        self.assertIn("after", events[-1])
        self.assertTrue(events[-1]["event_hash"].startswith("sha256:"))

    def test_problem_decomposition_builds_complete_question_and_dependency_contract(self):
        result = competition_runtime.decompose_problems(contest_input()["problems"])

        self.assertEqual(result["status"], "PASS")
        selected = next(item for item in result["problems"] if item["problem_id"] == "B")
        self.assertEqual(selected["question_graph"]["B-Q3"], ["B-Q1", "B-Q2"])
        required = {
            "goal", "inputs", "known_data", "unknown_data", "decision_variables",
            "state_variables", "parameters", "target", "objective", "constraints",
            "required_outputs", "dependencies", "required_evidence",
            "candidate_method_families", "validation_requirements",
            "likely_paper_section", "difficulty", "execution_risk",
        }
        self.assertTrue(required <= set(selected["questions"][2]))

    def test_baseline_deadline_risks_and_full_dashboard_are_runtime_derived(self):
        competition_runtime.configure_clock(
            self.project,
            NOW.isoformat(),
            (NOW + timedelta(hours=72)).isoformat(),
            "https://official.example/rules",
            "competition-director",
            now_utc=NOW,
        )
        competition_runtime.verify_clock(
            self.project,
            "https://official.example/rules",
            "competition-rule-verifier",
            now_utc=NOW,
        )
        at_ten = competition_runtime.schedule(self.project, now_utc=NOW + timedelta(hours=10))
        at_twelve = competition_runtime.schedule(self.project, now_utc=NOW + timedelta(hours=12))
        dashboard = competition_runtime.dashboard(self.project, now_utc=NOW + timedelta(hours=10))
        risks = json.loads(
            (self.project / ".research-state" / "competition_risks.json").read_text(encoding="utf-8")
        )

        self.assertTrue(at_ten["baseline_rule"]["risk_high_at_t_plus_10h"])
        self.assertTrue(at_twelve["baseline_rule"]["scope_reduction_required_at_t_plus_12h"])
        self.assertEqual(len(risks["risks"]), 18)
        for key in (
            "blocked_by_science", "blocked_by_policy", "blocked_by_time",
            "baseline", "primary_model", "largest_scientific_risk",
            "largest_scoring_risk", "paper_debt", "validation_debt",
            "complexity_debt", "author_action_required",
        ):
            self.assertIn(key, dashboard)

    def test_qualitative_problem_selection_auto_selects_only_a_clear_winner(self):
        result = competition_runtime.select_problem(contest_input()["problems"])

        self.assertEqual(result["decision"], "AUTO_SELECT")
        self.assertEqual(result["selected_problem"], "B")
        self.assertEqual(result["fallback_problem"], "A")
        self.assertTrue(result["alternatives_rejected"])
        self.assertNotIn("score", json.dumps(result))

        with_unknown = contest_input()["problems"] + [
            {"id": "C", "title": "missing decision-critical profile", "questions": [{"id": "C-Q1", "goal": "evaluate"}]}
        ]
        self.assertEqual(
            competition_runtime.select_problem(with_unknown)["decision"],
            "ASK_AUTHOR",
        )

    def test_mixed_method_router_returns_primary_secondary_and_baseline_first_contract(self):
        result = competition_method_router.route(
            "Forecast demand, then optimize facility allocation on a network under capacity constraints"
        )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["primary_family"], "prediction")
        self.assertIn("optimization", result["secondary_families"])
        self.assertTrue(result["dependency"])
        self.assertEqual(result["baseline_first"]["decision"], "BASELINE_FIRST")

    def test_unit_dimension_engine_marks_core_mismatch_critical(self):
        result = competition_quality.check_dimensions(
            symbols=[
                {"variable": "distance", "symbol": "d", "meaning": "route length", "unit": "km", "range": ">=0", "source": "problem"},
                {"variable": "time", "symbol": "t", "meaning": "travel time", "unit": "h", "range": ">0", "source": "problem"},
            ],
            equations=[{"id": "E1", "left_unit": "km", "right_unit": "h", "core": True}],
        )

        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["findings"][0]["severity"], "CRITICAL")

    def test_numeric_consistency_checker_fails_closed(self):
        result = competition_quality.check_numeric_consistency(
            {
                "abstract": {"selected_cost": 13.27},
                "table": {"selected_cost": 13.72},
                "conclusion": {"selected_cost": 13.27},
            }
        )

        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["findings"][0]["severity"], "CRITICAL")

    def test_sensitivity_boundaries_do_not_inflate_from_float_rounding(self):
        result = competition_quality.classify_sensitivity(
            "B",
            [
                {"decision": "B", "relative_change": abs(0.90 - 1.0)},
                {"decision": "B", "relative_change": abs(1.10 - 1.0)},
            ],
        )

        self.assertEqual(result["classification"], "moderately sensitive")
        self.assertFalse(result["conclusion_reversal"])

    def test_solver_verifier_rejects_infeasible_or_miscalculated_output(self):
        result = competition_quality.check_solver_result(
            {
                "sites": [{"id": "A", "capacity": 80.0, "fixed_cost": 10.0, "distance": 5.0}],
            },
            {
                "forecast_demand": 100.0,
                "selected_site": "A",
                "selected_total_cost": 9.0,
                "objective_recalculated": 15.0,
                "candidates": [{"site": "A", "capacity": 80.0, "feasible": True, "total_cost": 15.0}],
            },
        )

        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(all(item["severity"] == "CRITICAL" for item in result["findings"]))

        independently_wrong = competition_quality.check_solver_result(
            {
                "sites": [
                    {"id": "A", "capacity": 100, "fixed_cost": 10, "distance": 2},
                    {"id": "B", "capacity": 100, "fixed_cost": 12, "distance": 3},
                ]
            },
            {
                "forecast_demand": 10,
                "selected_site": "B",
                "selected_total_cost": 15,
                "objective_recalculated": 15,
                "candidates": [
                    {"site": "A", "capacity": 100, "feasible": True, "total_cost": 10.2},
                    {"site": "B", "capacity": 100, "feasible": True, "total_cost": 15},
                ],
            },
        )
        self.assertEqual(independently_wrong["status"], "FAIL")
        issues = " ".join(item["issue"] for item in independently_wrong["findings"])
        self.assertIn("independent", issues)
        self.assertIn("optimal", issues)

    def test_stale_dependency_and_figure_source_mismatch_fail_closed(self):
        source = self.project / "results" / "source.json"
        code = self.project / "src" / "figure.py"
        figure = self.project / "figures" / "figure.svg"
        for path, content in ((source, "{}"), (code, "print('figure')"), (figure, "<svg/>")):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        manifest = {
            "figures": [
                {
                    "path": "figures/figure.svg",
                    "source_data": "results/source.json",
                    "code": "src/figure.py",
                    "artifact_sha256": competition_quality.file_sha256(figure),
                    "source_sha256": competition_quality.file_sha256(source),
                    "code_sha256": competition_quality.file_sha256(code),
                    "proves": "fixture",
                    "axis": "x/y",
                    "unit": "units",
                    "legend": "fixture",
                    "caption": "fixture",
                }
            ]
        }
        source.write_text('{"changed": true}', encoding="utf-8")

        trace = competition_quality.check_figure_traceability(self.project, manifest)
        freshness = competition_quality.check_artifact_freshness(
            figure, [source, code], recorded_dependency_hashes=[
                manifest["figures"][0]["source_sha256"],
                manifest["figures"][0]["code_sha256"],
            ]
        )

        self.assertEqual(trace["status"], "FAIL")
        self.assertEqual(freshness["status"], "FAIL")

    def test_unverified_rules_allow_modeling_but_block_submission_preflight(self):
        self.assertEqual(competition_runtime.audit_rules(self.project)["status"], "FAIL")
        preflight = competition_quality.submission_preflight(self.project)
        self.assertEqual(preflight["status"], "BLOCKED")
        self.assertTrue(any("official rules" in item for item in preflight["findings"]))

    def test_normal_competition_director_runs_real_code_repairs_and_reaches_ready(self):
        input_path = self.project / "competition_input.json"
        input_path.write_text(json.dumps(contest_input(), indent=2), encoding="utf-8")

        result = competition_director.run(
            self.project, input_path=input_path, now_utc=NOW, max_steps=40
        )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["submission_readiness"], "COMPETITION_SUBMISSION_READY")
        self.assertEqual(result["selected_problem"], "B")
        self.assertEqual(result["ordinary_author_prompts"], 0)
        self.assertGreaterEqual(result["executed_nodes"], 16)
        self.assertEqual(result["actual_code_execution"]["exit_code"], 0)
        self.assertTrue(result["actual_code_execution"]["output_sha256"].startswith("sha256:"))
        self.assertEqual(result["automatic_repair"], "PASS")
        self.assertEqual(result["completion_contract"]["status"], "PASS")
        self.assertEqual(result["unresolved"]["CRITICAL"], 0)
        self.assertEqual(result["unresolved"]["MAJOR"], 0)
        for relative in (
            "data_processed/selected_problem.json",
            "results/formal_solution.json",
            "tables/sensitivity.csv",
            "figures/decision_summary.svg",
            "paper/cumcm_paper.md",
            "paper/submission_preflight.json",
        ):
            self.assertTrue((self.project / relative).is_file(), relative)

        figure_manifest = json.loads(
            (self.project / "figures" / "figure_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(competition_quality.check_figure_traceability(self.project, figure_manifest)["status"], "PASS")
        paper_path = self.project / "paper" / "cumcm_paper.md"
        paper_text = paper_path.read_text(encoding="utf-8")
        self.assertIn("figures/decision_summary.svg", paper_text)
        self.assertIn("tables/sensitivity.csv", paper_text)
        self.assertEqual(competition_quality.check_paper(self.project)["status"], "PASS")
        paper_path.write_text(
            paper_text.replace("figures/decision_summary.svg", "figures/missing.svg"),
            encoding="utf-8",
        )
        self.assertEqual(competition_quality.check_paper(self.project)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
