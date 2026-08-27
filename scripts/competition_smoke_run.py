#!/usr/bin/env python3
"""Run a deterministic synthetic CUMCM workflow without model evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "assets" / "fixtures" / "cumcm" / "synthetic_problem.json"
SCRIPT_DIR = str(ROOT / "scripts")
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import competition_method_router  # noqa: E402
import competition_runtime  # noqa: E402
import evidence_anchor  # noqa: E402
import research_graph  # noqa: E402
import research_state  # noqa: E402


SOLVER_SOURCE = """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

problem = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
feasible = [
    site for site in problem["sites"]
    if site["capacity"] >= problem["minimum_capacity"]
]
selected = min(feasible, key=lambda site: (site["cost"], site["id"]))
result = {
    "method": "exhaustive enumeration",
    "selected_site": selected["id"],
    "cost": selected["cost"],
}
Path(sys.argv[2]).write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\\n",
    encoding="utf-8",
)
"""


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def solve_fixture(value: dict[str, Any]) -> dict[str, Any]:
    feasible = [
        site
        for site in value["sites"]
        if site["capacity"] >= value["minimum_capacity"]
    ]
    if not feasible:
        raise RuntimeError("synthetic fixture has no feasible facility")
    selected = min(feasible, key=lambda site: (site["cost"], site["id"]))
    return {
        "method": "exhaustive enumeration",
        "selected_site": selected["id"],
        "cost": selected["cost"],
    }


def _anchor_for_file(
    project: Path,
    anchor_id: str,
    artifact: Path,
    *,
    artifact_type: str,
    provenance_level: str = "DECLARED",
    execution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    digest = _sha256(artifact)
    relative = artifact.relative_to(project).as_posix()
    anchor: dict[str, Any] = {
        "anchor_id": anchor_id,
        "claim_id": "C1",
        "result_id": "R-SYNTHETIC-FACILITY",
        "source_artifact": f"{relative}#sha256={digest}",
        "source_sha256": digest,
        "exact_region": "complete synthetic artifact",
        "transformation": "deterministic harness",
        "provenance_level": provenance_level,
        "uncertainty": "none; finite synthetic fixture",
        "scope": "synthetic facility-selection fixture only",
        "status": provenance_level,
        "artifact_type": artifact_type,
    }
    if execution is not None:
        anchor.update(
            {
                "execution_record_id": "artifacts/execution_record.json",
                "command": execution["command"],
                "cwd": ".",
                "exit_status": execution["exit_status"],
                "started_utc": execution["started_utc"],
                "finished_utc": execution["finished_utc"],
                "stdout_sha256": execution["stdout_sha256"],
                "stderr_sha256": execution["stderr_sha256"],
                "config_hash": "sha256:" + _sha256(project / "config.json"),
                "input_hash": "sha256:" + _sha256(project / "inputs" / "problem.json"),
                "code_version_type": "content_hash",
                "code_version": "sha256:" + _sha256(project / "solver.py"),
            }
        )
    return anchor


def _append_anchor(project: Path, anchor: dict[str, Any]) -> None:
    ledger_path = project / ".research-state" / "evidence_ledger.json"
    ledger = _read_json(ledger_path)
    ledger.setdefault("anchors", []).append(anchor)
    _write_json(ledger_path, ledger)


def _record_artifact(
    project: Path,
    node_id: str,
    anchor_id: str,
    artifact: Path,
    *,
    artifact_type: str,
    provenance_level: str = "DECLARED",
    execution: dict[str, Any] | None = None,
) -> None:
    anchor = _anchor_for_file(
        project,
        anchor_id,
        artifact,
        artifact_type=artifact_type,
        provenance_level=provenance_level,
        execution=execution,
    )
    _append_anchor(project, anchor)
    research_graph.transition(
        project,
        node_id,
        "PASS",
        f"synthetic artifact recorded for {node_id}",
        "competition-smoke",
        anchor_id,
    )


def run(output: Path | None = None) -> dict[str, Any]:
    fixture = _read_json(FIXTURE)
    expected = solve_fixture(fixture)
    start = datetime(2026, 9, 10, 10, tzinfo=timezone.utc)
    deadline = start + timedelta(hours=72)

    with tempfile.TemporaryDirectory() as temporary:
        project = Path(temporary) / "competition-project"
        project.mkdir()
        research_state.init_state(
            project,
            "algorithmic",
            "competition-autopilot",
            "mathematical-modeling",
        )

        input_path = project / "inputs" / "problem.json"
        _write_json(input_path, fixture)
        config_path = project / "config.json"
        _write_json(config_path, {"solver": "exhaustive-enumeration", "seed": None})
        solver_path = project / "solver.py"
        solver_path.write_text(SOLVER_SOURCE, encoding="utf-8", newline="\n")
        result_path = project / "artifacts" / "solution.json"
        result_path.parent.mkdir()
        execution_path = project / "artifacts" / "execution_record.json"
        execution = evidence_anchor.execution_record(
            execution_path,
            [sys.executable, str(solver_path), str(input_path), str(result_path)],
            cwd=project,
            input_paths=[input_path, config_path, solver_path],
            output_paths=[result_path],
            environment={
                "network": False,
                "evaluation_class": "HARNESS_SELF_TEST",
                "python": sys.version.split()[0],
            },
        )
        observed = _read_json(result_path)

        intake_path = project / "artifacts" / "contest_intake.json"
        _write_json(
            intake_path,
            {
                "problem_ids": [fixture["id"]],
                "official_rules_source": "fixture://official-rules",
                "official_rules_scope": "synthetic harness only",
            },
        )
        decomposition_path = project / "artifacts" / "question_decomposition.json"
        _write_json(
            decomposition_path,
            {
                "goal": "minimize declared cost",
                "decision_variable": "selected facility",
                "constraint": f"capacity >= {fixture['minimum_capacity']}",
                "output": "one facility id",
            },
        )
        selection_path = project / "artifacts" / "problem_selection.json"
        _write_json(selection_path, {"selected_problem": fixture["id"]})
        assumptions_path = project / "artifacts" / "assumptions.json"
        _write_json(
            assumptions_path,
            {
                "assumptions": [
                    "declared capacities and costs are exact fixture inputs",
                    "exactly one facility is selected",
                ]
            },
        )
        method_route = competition_method_router.route(fixture["question"])
        route_path = project / "artifacts" / "method_route.json"
        _write_json(route_path, method_route)
        validation_path = project / "artifacts" / "validation.json"
        _write_json(
            validation_path,
            {
                "observed_equals_hand_checked": observed == expected,
                "matches_fixture_expectation": observed.get("selected_site")
                == fixture["expected_selected_site"],
                "feasible": next(
                    site["capacity"]
                    for site in fixture["sites"]
                    if site["id"] == observed.get("selected_site")
                )
                >= fixture["minimum_capacity"],
            },
        )

        for node_id, anchor_id, artifact, artifact_type in (
            ("contest_intake", "EA-COMP-INTAKE", intake_path, "decision"),
            (
                "problem_decomposition",
                "EA-COMP-DECOMPOSITION",
                decomposition_path,
                "analysis",
            ),
            ("problem_selection", "EA-COMP-SELECTION", selection_path, "decision"),
            ("assumptions", "EA-COMP-ASSUMPTIONS", assumptions_path, "analysis"),
            ("method_candidates", "EA-COMP-ROUTE", route_path, "decision"),
            ("minimal_viable_model", "EA-COMP-CODE", solver_path, "execution"),
        ):
            _record_artifact(
                project,
                node_id,
                anchor_id,
                artifact,
                artifact_type=artifact_type,
            )
        _record_artifact(
            project,
            "pilot_solve",
            "EA-COMP-PILOT",
            result_path,
            artifact_type="execution",
            provenance_level="OBSERVED",
            execution=execution,
        )
        _record_artifact(
            project,
            "model_validation",
            "EA-COMP-VALIDATION",
            validation_path,
            artifact_type="validation",
        )
        _record_artifact(
            project,
            "formal_solve",
            "EA-COMP-FORMAL",
            result_path,
            artifact_type="formal_output",
            provenance_level="OBSERVED",
            execution=execution,
        )

        graph_before_rebuild = research_graph.validate_project(project)
        graph_rebuild = research_graph.rebuild(project)
        graph_after_rebuild = research_graph.validate_project(project)
        evidence_check = evidence_anchor.validate_path(
            project / ".research-state" / "evidence_ledger.json",
            deep=True,
            root=project,
        )

        competition_runtime.configure_clock(
            project,
            start.isoformat(),
            deadline.isoformat(),
            "fixture://official-rules",
            "competition-smoke",
            now_utc=start,
        )
        competition_runtime.verify_clock(
            project,
            "fixture://official-rules",
            "competition-smoke",
            now_utc=start,
        )
        estimates = {"sensitivity_robustness": 60}
        normal = competition_runtime.schedule(
            project, job_estimates=estimates, now_utc=start + timedelta(hours=10)
        )
        finalization = competition_runtime.schedule(
            project, job_estimates=estimates, now_utc=deadline - timedelta(hours=4)
        )
        hard_freeze = competition_runtime.schedule(
            project, job_estimates=estimates, now_utc=deadline - timedelta(hours=1)
        )

        clock_checks = {
            "normal": normal["control_mode"],
            "finalization": finalization["control_mode"],
            "hard_freeze": hard_freeze["control_mode"],
        }
        output_sha256 = (
            execution["outputs"][0]["sha256"] if execution["outputs"] else ""
        )
        passed = all(
            (
                execution["status"] == "PASS",
                observed == expected,
                observed.get("selected_site") == fixture["expected_selected_site"],
                method_route["status"] in {"PASS", "CONDITIONAL"},
                evidence_check["status"] == "PASS",
                graph_before_rebuild["status"] == "PASS",
                graph_rebuild["status"] == "PASS",
                graph_after_rebuild["status"] == "PASS",
                clock_checks
                == {
                    "normal": "NORMAL",
                    "finalization": "FINALIZATION_MODE",
                    "hard_freeze": "HARD_FREEZE",
                },
            )
        )
        result = {
            "status": "PASS" if passed else "FAIL",
            "skill_version": "3.1.1",
            "competition": "CUMCM",
            "fixture_id": fixture["id"],
            "evaluation_class": "HARNESS_SELF_TEST",
            "model_behavior": "NOT_RUN; deterministic harness only",
            "baseline": observed,
            "method_route": {
                "status": method_route["status"],
                "problem_type": method_route.get("problem_type"),
            },
            "execution": {
                "status": execution["status"],
                "exit_status": execution["exit_status"],
                "output_sha256": output_sha256,
            },
            "clock_checks": clock_checks,
            "evidence_validation": evidence_check["status"],
            "evidence_anchors": evidence_check["anchor_count"],
            "graph_events": graph_after_rebuild["event_count"],
            "graph_validation": graph_after_rebuild["status"],
            "graph_rebuild": graph_rebuild["status"],
            "note": "Synthetic deterministic fixture; no real model behavior or award claim.",
        }

    if output is not None:
        _write_json(output.resolve(), result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = run(args.output)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
