import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


research_state = load("research_state")
research_graph = load("research_graph")
competition_runtime = load("competition_runtime")


class CompetitionInitializationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.project = Path(self.tempdir.name) / "project"
        self.project.mkdir()

    def tearDown(self):
        self.tempdir.cleanup()

    def read(self, name):
        return json.loads(
            (self.project / ".research-state" / name).read_text(encoding="utf-8")
        )

    def test_competition_modes_are_supported(self):
        self.assertEqual(
            set(research_state.COMPETITION_MODES),
            {"competition", "competition-autopilot", "competition-review"},
        )
        self.assertTrue(set(research_state.COMPETITION_MODES) <= set(research_state.MODES))

    def test_competition_mode_selects_contest_graph_and_state(self):
        result = research_state.init_state(
            self.project,
            "algorithmic",
            "competition",
            "mathematical-modeling",
        )

        self.assertEqual(result["status"], "PASS")
        graph = self.read("research_graph.json")
        self.assertEqual(graph["profile"], "CUMCM")
        self.assertEqual(graph["nodes"][0]["id"], "contest_intake")
        self.assertEqual(research_graph.validate_project(self.project)["status"], "PASS")
        for name in (
            "competition_clock.json",
            "competition_state.json",
            "competition_rules.json",
            "competition_review.json",
        ):
            self.assertTrue((self.project / ".research-state" / name).exists(), name)
        self.assertEqual(self.read("competition_clock.json")["clock_status"], "UNVERIFIED")
        self.assertEqual(self.read("competition_state.json")["mode"], "competition")

    def test_research_mode_does_not_create_competition_state(self):
        research_state.init_state(self.project, "empirical", "copilot", "systems")

        state = self.project / ".research-state"
        self.assertFalse((state / "competition_clock.json").exists())
        self.assertFalse((state / "competition_state.json").exists())
        self.assertEqual(self.read("research_graph.json")["nodes"][0]["id"], "orientation")


class CompetitionClockTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.project = Path(self.tempdir.name) / "project"
        self.project.mkdir()
        research_state.init_state(
            self.project,
            "algorithmic",
            "competition",
            "mathematical-modeling",
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_clock_normalizes_offsets_and_uses_actual_duration(self):
        result = competition_runtime.configure_clock(
            self.project,
            "2026-09-10T18:00:00+08:00",
            "2026-09-13T22:00:00+08:00",
            "https://fixture.invalid/official-rules",
            "fixture-author",
            now_utc=datetime(2026, 9, 10, 12, tzinfo=timezone.utc),
        )

        clock = result["clock"]
        self.assertEqual(clock["contest_start_utc"], "2026-09-10T10:00:00Z")
        self.assertEqual(clock["submission_deadline_utc"], "2026-09-13T14:00:00Z")
        self.assertEqual(clock["contest_duration_seconds"], 76 * 3600)
        self.assertEqual(clock["elapsed_seconds"], 2 * 3600)
        self.assertEqual(clock["remaining_seconds"], 74 * 3600)

    def test_clock_rejects_naive_and_reversed_boundaries(self):
        with self.assertRaises(competition_runtime.CompetitionError):
            competition_runtime.configure_clock(
                self.project,
                "2026-09-10T10:00:00",
                "2026-09-13T10:00:00Z",
                "source",
                "actor",
            )
        with self.assertRaises(competition_runtime.CompetitionError):
            competition_runtime.configure_clock(
                self.project,
                "2026-09-13T10:00:00Z",
                "2026-09-10T10:00:00Z",
                "source",
                "actor",
            )

    def test_source_remains_unverified_until_explicit_verification(self):
        result = competition_runtime.configure_clock(
            self.project,
            "2026-09-10T10:00:00Z",
            "2026-09-13T10:00:00Z",
            "https://fixture.invalid/official-rules",
            "fixture-author",
            now_utc=datetime(2026, 9, 10, 11, tzinfo=timezone.utc),
        )

        self.assertEqual(result["clock"]["clock_status"], "UNVERIFIED")
        self.assertFalse(result["clock"]["authoritative_deadline"])
        verified = competition_runtime.verify_clock(
            self.project,
            "https://fixture.invalid/official-rules",
            "fixture-verifier",
            now_utc=datetime(2026, 9, 10, 11, tzinfo=timezone.utc),
        )
        self.assertEqual(verified["clock"]["clock_status"], "ACTIVE")
        self.assertTrue(verified["clock"]["authoritative_deadline"])
        self.assertEqual(verified["clock"]["source_verified_utc"], "2026-09-10T11:00:00Z")


class CompetitionClockEventTests(unittest.TestCase):
    START = datetime(2026, 9, 10, 10, tzinfo=timezone.utc)
    DEADLINE = START + timedelta(hours=72)

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.project = Path(self.tempdir.name) / "project"
        self.project.mkdir()
        research_state.init_state(
            self.project,
            "algorithmic",
            "competition-autopilot",
            "mathematical-modeling",
        )
        self.state = self.project / ".research-state"

    def tearDown(self):
        self.tempdir.cleanup()

    def configure_verified(self):
        competition_runtime.configure_clock(
            self.project,
            self.START.isoformat(),
            self.DEADLINE.isoformat(),
            "https://fixture.invalid/official-rules",
            "captain",
            now_utc=self.START,
        )
        competition_runtime.verify_clock(
            self.project,
            "https://fixture.invalid/official-rules",
            "captain",
            now_utc=self.START,
        )

    def test_manual_offset_is_replayed_from_hash_chain(self):
        self.configure_verified()
        at_hour_10 = self.START + timedelta(hours=10)
        competition_runtime.adjust_clock(
            self.project,
            -1800,
            "official pause correction",
            "captain",
            now_utc=at_hour_10,
        )

        result = competition_runtime.refresh_clock(self.project, now_utc=at_hour_10)
        self.assertEqual(result["clock"]["manual_time_offset_seconds"], -1800)
        self.assertEqual(result["clock"]["elapsed_seconds"], 9 * 3600 + 1800)
        events = (self.state / ".competition-clock-events.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        self.assertEqual(len(events), 3)
        self.assertEqual(json.loads(events[-1])["operation"], "ADJUST_CLOCK")

    def test_tampered_clock_event_fails_closed_without_rewriting_snapshot(self):
        self.configure_verified()
        at_hour_10 = self.START + timedelta(hours=10)
        competition_runtime.adjust_clock(
            self.project,
            60,
            "system clock correction",
            "captain",
            now_utc=at_hour_10,
        )
        snapshot_path = self.state / "competition_clock.json"
        snapshot_before = snapshot_path.read_bytes()
        event_path = self.state / ".competition-clock-events.jsonl"
        events = [
            json.loads(line)
            for line in event_path.read_text(encoding="utf-8").splitlines()
        ]
        events[-1]["reason"] = "tampered"
        event_path.write_text(
            "\n".join(json.dumps(item) for item in events) + "\n",
            encoding="utf-8",
        )

        with self.assertRaises(competition_runtime.CompetitionError):
            competition_runtime.refresh_clock(self.project, now_utc=at_hour_10)
        self.assertEqual(snapshot_path.read_bytes(), snapshot_before)

    def test_pause_and_resume_preserve_only_active_contest_elapsed_time(self):
        self.configure_verified()
        at_hour_10 = self.START + timedelta(hours=10)
        competition_runtime.pause_clock(
            self.project,
            "official pause",
            "captain",
            now_utc=at_hour_10,
        )

        paused = competition_runtime.refresh_clock(
            self.project,
            now_utc=self.START + timedelta(hours=12),
        )["clock"]
        self.assertEqual(paused["clock_status"], "PAUSED")
        self.assertEqual(paused["elapsed_seconds"], 10 * 3600)

        competition_runtime.resume_clock(
            self.project,
            "official resume",
            "captain",
            now_utc=self.START + timedelta(hours=12),
        )
        resumed = competition_runtime.refresh_clock(
            self.project,
            now_utc=self.START + timedelta(hours=13),
        )["clock"]
        self.assertEqual(resumed["clock_status"], "ACTIVE")
        self.assertEqual(resumed["manual_time_offset_seconds"], -2 * 3600)
        self.assertEqual(resumed["elapsed_seconds"], 11 * 3600)


class CompetitionPhaseTests(unittest.TestCase):
    START = datetime(2026, 9, 10, 10, tzinfo=timezone.utc)

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.project = Path(self.tempdir.name) / "project"
        self.project.mkdir()
        research_state.init_state(
            self.project,
            "algorithmic",
            "competition",
            "mathematical-modeling",
        )
        self.configure_duration(72)

    def tearDown(self):
        self.tempdir.cleanup()

    def configure_duration(self, hours):
        competition_runtime.configure_clock(
            self.project,
            self.START.isoformat(),
            (self.START + timedelta(hours=hours)).isoformat(),
            "https://fixture.invalid/official-rules",
            "captain",
            now_utc=self.START,
        )
        competition_runtime.verify_clock(
            self.project,
            "https://fixture.invalid/official-rules",
            "captain",
            now_utc=self.START,
        )

    def refresh_at_elapsed(self, hours):
        return competition_runtime.refresh_clock(
            self.project,
            now_utc=self.START + timedelta(hours=hours),
        )["clock"]

    def test_default_72_hour_boundaries_and_control_overlays(self):
        cases = [
            (3, "CONTEST_INTAKE_AND_SELECTION", "NORMAL", False, False),
            (10, "MVP_MODELING", "NORMAL", False, False),
            (31, "VALIDATION_AND_ROBUSTNESS", "NORMAL", False, False),
            (67, "REVIEW_AND_REVISION", "FINALIZATION_MODE", True, False),
            (69, "SUBMISSION_FREEZE", "FINALIZATION_MODE", True, False),
            (71, "SUBMISSION_FREEZE", "HARD_FREEZE", True, True),
        ]
        for hours, phase, control, stop, hard in cases:
            with self.subTest(hours=hours):
                clock = self.refresh_at_elapsed(hours)
                self.assertEqual(clock["current_phase"], phase)
                self.assertEqual(clock["control_mode"], control)
                self.assertEqual(clock["stop_rule_active"], stop)
                self.assertEqual(clock["hard_freeze_active"], hard)

    def test_non_72_hour_schedule_scales_proportionally(self):
        self.configure_duration(36)

        clock = self.refresh_at_elapsed(6)

        self.assertEqual(clock["contest_duration_seconds"], 36 * 3600)
        self.assertEqual(clock["current_phase"], "FORMAL_MODELING")
        self.assertEqual(clock["control_mode"], "NORMAL")

    def test_precontest_and_expired_states_are_explicit(self):
        before = self.refresh_at_elapsed(-1)
        after = self.refresh_at_elapsed(73)

        self.assertEqual(before["current_phase"], "PRE_CONTEST")
        self.assertEqual(before["clock_status"], "SCHEDULED")
        self.assertEqual(after["current_phase"], "DEADLINE_PASSED")
        self.assertEqual(after["control_mode"], "DEADLINE_PASSED")
        self.assertEqual(after["clock_status"], "EXPIRED")


class CompetitionSchedulerTests(unittest.TestCase):
    START = datetime(2026, 9, 10, 10, tzinfo=timezone.utc)
    DEADLINE = START + timedelta(hours=72)

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.project = Path(self.tempdir.name) / "project"
        self.project.mkdir()
        research_state.init_state(
            self.project,
            "algorithmic",
            "competition-autopilot",
            "mathematical-modeling",
        )
        self.state = self.project / ".research-state"
        self.configure_verified()

    def tearDown(self):
        self.tempdir.cleanup()

    def configure_verified(self):
        competition_runtime.configure_clock(
            self.project,
            self.START.isoformat(),
            self.DEADLINE.isoformat(),
            "https://fixture.invalid/official-rules",
            "captain",
            now_utc=self.START,
        )
        competition_runtime.verify_clock(
            self.project,
            "https://fixture.invalid/official-rules",
            "captain",
            now_utc=self.START,
        )

    def set_ready(self, *node_ids):
        path = self.state / "research_graph.json"
        graph = json.loads(path.read_text(encoding="utf-8"))
        selected = set(node_ids)
        for node in graph["nodes"]:
            node["status"] = "READY" if node["id"] in selected else "BLOCKED"
        path.write_text(
            json.dumps(graph, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def test_unverified_clock_does_not_apply_time_policy(self):
        competition_runtime.configure_clock(
            self.project,
            self.START.isoformat(),
            self.DEADLINE.isoformat(),
            "",
            "captain",
            now_utc=self.START + timedelta(hours=67),
        )
        self.set_ready("model_improvement")

        result = competition_runtime.schedule(
            self.project,
            job_estimates={"model_improvement": 60},
            now_utc=self.START + timedelta(hours=67),
        )

        self.assertEqual(result["status"], "CONDITIONAL")
        self.assertFalse(result["authoritative_deadline"])
        self.assertEqual(result["policy_actions"], [])

    def test_any_new_job_requires_an_eta(self):
        self.set_ready("formal_solve")

        result = competition_runtime.schedule(
            self.project,
            now_utc=self.START + timedelta(hours=20),
        )

        blocked = {item["node"]: item["reason"] for item in result["blocked"]}
        self.assertIn("formal_solve", blocked)
        self.assertIn("estimated runtime", blocked["formal_solve"])

    def test_eta_requires_strict_slack_after_late_stage_margin(self):
        self.set_ready("formal_solve")

        result = competition_runtime.schedule(
            self.project,
            job_estimates={"formal_solve": 9000},
            now_utc=self.START + timedelta(hours=69),
        )

        blocked = {item["node"]: item["reason"] for item in result["blocked"]}
        self.assertIn("formal_solve", blocked)
        self.assertIn("ETA", blocked["formal_solve"])

    def test_hard_freeze_allows_submission_work_but_blocks_model_change(self):
        self.set_ready("model_improvement", "revision")

        result = competition_runtime.schedule(
            self.project,
            job_estimates={"model_improvement": 60},
            now_utc=self.START + timedelta(hours=71),
        )

        self.assertNotIn("model_improvement", result["eligible"])
        self.assertIn("revision", result["eligible"])
        blocked = {item["node"]: item["reason"] for item in result["blocked"]}
        self.assertIn("HARD_FREEZE", blocked["model_improvement"])

    def test_schedule_is_read_only_and_advance_uses_graph_event_chain(self):
        self.set_ready("model_improvement", "revision")
        graph_path = self.state / "research_graph.json"
        before = graph_path.read_bytes()

        scheduled = competition_runtime.schedule(
            self.project,
            job_estimates={"model_improvement": 60},
            now_utc=self.START + timedelta(hours=69),
        )

        self.assertEqual(graph_path.read_bytes(), before)
        self.assertTrue(
            any(
                item["node"] == "model_improvement" and item["to"] == "BLOCKED"
                for item in scheduled["policy_actions"]
            )
        )
        advanced = competition_runtime.advance(
            self.project,
            "competition-scheduler",
            job_estimates={"model_improvement": 60},
            now_utc=self.START + timedelta(hours=69),
        )
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        by_id = {node["id"]: node for node in graph["nodes"]}
        self.assertEqual(by_id["model_improvement"]["status"], "BLOCKED")
        self.assertNotEqual(by_id["revision"]["status"], "PASS")
        self.assertTrue(advanced["changed"])
        self.assertTrue((self.state / ".research-graph-events.jsonl").exists())


class CompetitionMethodRouterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = load("competition_method_router")
        cls.registry_validator = load("validate_registry")

    def test_router_covers_required_problem_families(self):
        expected = {
            "evaluation",
            "prediction",
            "optimization",
            "classification-clustering",
            "graph-network",
            "time-series",
            "differential-equations",
            "simulation",
            "spatial-routing",
            "data-preparation",
        }

        self.assertEqual(
            {item["id"] for item in self.router._read()["categories"]},
            expected,
        )
        validation = self.registry_validator.validate()
        self.assertEqual(validation["status"], "PASS")
        self.assertEqual(validation["competition_method_category_count"], 10)

    def test_small_data_prediction_starts_with_simple_baseline(self):
        result = self.router.route(
            "predict a short annual time series with 18 observations"
        )

        self.assertIn(result["status"], {"PASS", "CONDITIONAL"})
        self.assertIn(
            result["recommended_baseline"],
            {"linear regression", "naive forecast", "exponential smoothing"},
        )
        self.assertNotEqual(result["recommended_primary_model"], "LSTM")
        self.assertTrue(result["complexity_upgrade_condition"])

    def test_evaluation_route_has_complete_decision_contract(self):
        result = self.router.route(
            "rank suppliers using weighted indicators and test weight sensitivity"
        )

        self.assertEqual(result["problem_type"], "evaluation and ranking")
        for field in (
            "candidate_models",
            "recommended_baseline",
            "recommended_primary_model",
            "optional_improvement",
            "why",
            "main_assumptions",
            "failure_risks",
            "validation_plan",
        ):
            self.assertTrue(result[field], field)

    def test_ambiguous_signal_is_conditional_and_names_conflicts(self):
        result = self.router.route("forecast network traffic as a time series")

        self.assertEqual(result["status"], "CONDITIONAL")
        self.assertTrue(result["conflicts"])

    def test_zero_match_is_unresolved_without_model_guess(self):
        result = self.router.route("an underspecified contest question")

        self.assertEqual(result["status"], "UNRESOLVED")
        self.assertEqual(result["candidate_models"], [])
        self.assertIsNone(result["recommended_baseline"])
        self.assertIsNone(result["recommended_primary_model"])
        self.assertIn("guess", result["failure_risks"][0])


if __name__ == "__main__":
    unittest.main()
