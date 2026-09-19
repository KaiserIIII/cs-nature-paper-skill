#!/usr/bin/env python3
"""Run the normal Competition Director on a real executable synthetic contest."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = str(ROOT / "scripts")
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import competition_director  # noqa: E402
import competition_quality  # noqa: E402
import competition_runtime  # noqa: E402
import research_state  # noqa: E402


FIXTURE = ROOT / "assets" / "fixtures" / "cumcm" / "synthetic_problem.json"


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _set_ready(project: Path, node_id: str) -> None:
    graph_path = project / ".research-state" / "research_graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    for node in graph["nodes"]:
        node["status"] = "READY" if node["id"] == node_id else "BLOCKED"
    _write(graph_path, graph)


def _negative_cases() -> dict[str, str]:
    cases: dict[str, str] = {}
    cases["wrong_unit"] = "PASS" if competition_quality.check_dimensions(
        [{"variable":"x","symbol":"x","meaning":"distance","unit":"km","range":">=0","source":"fixture"}],
        [{"id":"bad","left_unit":"km","right_unit":"h","core":True}],
    )["status"] == "FAIL" else "FAIL"
    cases["infeasible_optimizer_output"] = "PASS" if competition_quality.check_solver_result(
        {"sites":[{"id":"A","capacity":1}]},
        {"forecast_demand":2,"selected_site":"A","selected_total_cost":1,"objective_recalculated":2,"candidates":[{"site":"A","capacity":1,"feasible":True,"total_cost":2}]},
    )["status"] == "FAIL" else "FAIL"
    cases["numeric_mismatch"] = "PASS" if competition_quality.check_numeric_consistency(
        {"paper":{"x":1.0},"table":{"x":2.0}}
    )["status"] == "FAIL" else "FAIL"

    with tempfile.TemporaryDirectory(prefix="competition-negative-") as temporary:
        project = Path(temporary)
        research_state.init_state(project, "algorithmic", "competition-autopilot", "mathematical-modeling")
        preflight = competition_quality.submission_preflight(project)
        cases["missing_result"] = "PASS" if any("formal_solution" in item for item in preflight["findings"]) else "FAIL"
        cases["submission_rule_unverified"] = "PASS" if preflight["unverified_rules"] else "FAIL"
        clock = competition_runtime.refresh_clock(project)
        cases["unverified_deadline"] = "PASS" if not clock["clock"]["authoritative_deadline"] else "FAIL"

        source = project / "results" / "source.json"
        code = project / "src" / "figure.py"
        figure = project / "figures" / "figure.svg"
        for path, content in ((source,"{}"),(code,"print(1)"),(figure,"<svg/>")):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        source_hash = competition_quality.file_sha256(source)
        code_hash = competition_quality.file_sha256(code)
        manifest = {"figures":[{
            "path":"figures/figure.svg","source_data":"results/source.json","code":"src/figure.py",
            "artifact_sha256":competition_quality.file_sha256(figure),"source_sha256":source_hash,"code_sha256":code_hash,
            "proves":"negative fixture","axis":"x/y","unit":"unit","legend":"fixture","caption":"fixture",
        }]}
        source.write_text('{"changed":true}', encoding="utf-8")
        cases["stale_artifact"] = "PASS" if competition_quality.check_artifact_freshness(
            figure, [source, code], recorded_dependency_hashes=[source_hash, code_hash]
        )["status"] == "FAIL" else "FAIL"
        cases["figure_source_mismatch"] = "PASS" if competition_quality.check_figure_traceability(
            project, manifest
        )["status"] == "FAIL" else "FAIL"

    with tempfile.TemporaryDirectory(prefix="competition-policy-") as temporary:
        project = Path(temporary)
        research_state.init_state(project, "algorithmic", "competition-autopilot", "mathematical-modeling")
        start = competition_runtime.parse_utc("2026-09-10T08:00:00Z")
        competition_runtime.configure_clock(project, "2026-09-10T08:00:00Z", "2026-09-13T08:00:00Z", "fixture://official", "fixture", now_utc=start)
        competition_runtime.verify_clock(project, "fixture://official", "fixture", now_utc=start)
        _set_ready(project, "model_improvement")
        eta = competition_runtime.schedule(project, {"model_improvement": 12 * 3600}, now_utc=start + timedelta(hours=60))
        cases["insufficient_eta"] = "PASS" if any(item["node"] == "model_improvement" for item in eta["blocked"]) else "FAIL"
        freeze = competition_runtime.schedule(project, {"model_improvement": 60}, now_utc=start + timedelta(hours=71))
        cases["hard_freeze_new_model"] = "PASS" if any("HARD_FREEZE" in item["reason"] for item in freeze["blocked"]) else "FAIL"
    return cases


def run(output: Path | None = None) -> dict[str, Any]:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    now = competition_runtime.parse_utc(fixture["fixture_now_utc"])
    with tempfile.TemporaryDirectory(prefix="competition-orchestration-") as temporary:
        project = Path(temporary)
        input_path = project / "competition_input.json"
        _write(input_path, fixture)
        result = competition_director.run(project, input_path=input_path, now_utc=now)
        failure_cases = _negative_cases()
        expected = (
            project / "results" / "formal_solution.json",
            project / "tables" / "sensitivity.csv",
            project / "figures" / "decision_summary.svg",
            project / "paper" / "cumcm_paper.md",
            project / "paper" / "submission_preflight.json",
        )
        summary = {
            "operation": "competition-orchestration-e2e",
            "status": "PASS" if result["status"] == "PASS" and all(value == "PASS" for value in failure_cases.values()) and all(path.is_file() for path in expected) else "FAIL",
            "evaluation_class": "COMPETITION_ORCHESTRATION_E2E",
            "model_behavior": "NOT_RUN",
            "selected_problem": result["selected_problem"],
            "submission_readiness": result["submission_readiness"],
            "executed_nodes": result["executed_nodes"],
            "ordinary_author_prompts": result["ordinary_author_prompts"],
            "actual_code_execution": {
                "exit_code": result["actual_code_execution"]["exit_code"],
                "output_sha256": result["actual_code_execution"]["output_sha256"],
                "command": "python src/run.py --input data_processed/selected_problem.json --output results/formal_solution.json --demand-factor 1.0",
            },
            "automatic_repair": result["automatic_repair"],
            "completion_contract": result["completion_contract"]["status"],
            "unresolved": result["unresolved"],
            "failure_cases": failure_cases,
            "failure_case_count": len(failure_cases),
            "artifacts": {
                path.relative_to(project).as_posix(): competition_quality.file_sha256(path)
                for path in expected
            },
            "privacy": "synthetic temporary project; no private absolute paths retained",
        }
    if output:
        _write(output, summary)
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
