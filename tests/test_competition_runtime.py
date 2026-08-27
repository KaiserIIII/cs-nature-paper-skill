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


research_state = load("research_state")
research_graph = load("research_graph")


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


if __name__ == "__main__":
    unittest.main()
