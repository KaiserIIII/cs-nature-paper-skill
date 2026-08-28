#!/usr/bin/env python3
"""Run one production Competition Provider across three structural fixtures."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = str(Path(__file__).resolve().parent)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import competition_director  # noqa: E402
import competition_runtime  # noqa: E402


RULE_IDS = (
    "contest_time", "problem_count", "participant_eligibility", "ai_policy", "paper_format", "page_limit",
    "file_naming", "attachments", "code_requirements", "submission_platform", "submission_method", "anonymity", "discipline",
)


def _rules() -> list[dict[str, Any]]:
    return [
        {
            "rule_id": rule_id, "value": f"recorded fixture value for {rule_id}", "source_type": "OFFICIAL_PRIMARY",
            "official_source": "fixture://official-rules/current", "retrieved_utc": "2026-09-10T08:00:00Z",
            "exact_region": f"rules#{rule_id}",
        }
        for rule_id in RULE_IDS
    ]


def _base(problem: dict[str, Any]) -> dict[str, Any]:
    return {
        "competition": "Generic Mathematical Modeling Contest", "contest_start_utc": "2026-09-10T08:00:00Z",
        "submission_deadline_utc": "2026-09-13T08:00:00Z", "official_rules_source": "fixture://official-rules/current",
        "rules": _rules(), "problems": [problem],
    }


def fixtures() -> dict[str, dict[str, Any]]:
    return {
        "A": _base({
            "id": "PRED-OPT", "title": "Forecast observations and choose a constrained alternative",
            "series": [18, 21, 23, 26, 29], "required_level": 30,
            "alternatives": [{"name": "alpha", "limit": 28, "objective": 7.2}, {"name": "beta", "limit": 34, "objective": 8.1}, {"name": "gamma", "limit": 40, "objective": 9.4}],
            "questions": [
                {"id": "Q1", "goal": "Forecast the ordered time series with a transparent prediction baseline."},
                {"id": "Q2", "goal": "Optimize the allocation decision under a required-level constraint."},
            ],
        }),
        "B": _base({
            "id": "EVAL-CLUSTER", "title": "Evaluate alternatives and discover stable groups",
            "records": [{"name": "r1", "features": [0.2, 0.3, 0.4]}, {"name": "r2", "features": [0.8, 0.7, 0.9]}, {"name": "r3", "features": [0.45, 0.5, 0.4]}, {"name": "r4", "features": [0.9, 0.85, 0.8]}],
            "questions": [
                {"id": "Q1", "goal": "Evaluate and rank alternatives using weighted indicators."},
                {"id": "Q2", "goal": "Cluster observations into interpretable groups and test stability."},
            ],
        }),
        "C": _base({
            "id": "DYNAMIC", "title": "Simulate a continuous dynamic process",
            "dynamics": {"initial": 10.0, "rate": -0.08, "steps": 12, "dt": 0.5},
            "questions": [
                {"id": "Q1", "goal": "Simulate an ODE differential equation dynamic system and check residual and parameter sensitivity."},
            ],
        }),
    }


def _normalized(families: list[str]) -> list[str]:
    output = []
    for family in families:
        output.append("clustering" if family == "classification-clustering" else "ode" if family == "differential-equations" else family)
    return sorted(set(output))


def run(output: Path | None = None) -> dict[str, Any]:
    summaries = {}
    now = competition_runtime.parse_utc("2026-09-10T16:00:00Z")
    with tempfile.TemporaryDirectory(prefix="generic-competition-provider-") as temporary:
        base = Path(temporary)
        for label, value in fixtures().items():
            project = base / label
            project.mkdir()
            input_path = project / "competition_input.json"
            input_path.write_text(json.dumps(value, indent=2), encoding="utf-8")
            result = competition_director.run(project, input_path=input_path, now_utc=now, max_steps=48)
            state = json.loads((project / ".research-state" / "competition_state.json").read_text(encoding="utf-8"))
            execution = json.loads((project / "logs" / "formal_execution.json").read_text(encoding="utf-8")) if (project / "logs" / "formal_execution.json").is_file() else {}
            formal = json.loads((project / "results" / "formal_solution.json").read_text(encoding="utf-8")) if (project / "results" / "formal_solution.json").is_file() else {}
            summaries[label] = {
                "status": "PASS" if result.get("status") == "PASS" and formal.get("input_derived") is True else "FAIL",
                "families": _normalized(state.get("method_families", [])),
                "actual_execution": {"exit_status": execution.get("exit_code"), "output_sha256": execution.get("output_sha256")},
                "submission_readiness": result.get("submission_readiness"), "ordinary_author_prompts": result.get("ordinary_author_prompts"),
                "provider": "competition-modeling/coding/analysis/writing-provider",
            }
    summary = {
        "operation": "generic-competition-orchestration-e2e", "evaluation_class": "GENERIC_COMPETITION_ORCHESTRATION_E2E",
        "status": "PASS" if all(item["status"] == "PASS" for item in summaries.values()) else "FAIL",
        "model_behavior": "NOT_RUN", "fixtures": summaries,
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = run(args.output)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
