#!/usr/bin/env python3
"""Clock-aware Competition Director built on the v3.2 authorization and graph plane."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = str(Path(__file__).resolve().parent)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import competition_quality  # noqa: E402
import competition_runtime  # noqa: E402
import research_graph  # noqa: E402
import research_state  # noqa: E402


JOB_ESTIMATES = {
    "minimal_viable_model": 30,
    "pilot_solve": 30,
    "model_validation": 30,
    "formal_solve": 30,
    "sensitivity_robustness": 60,
    "model_improvement": 30,
}


def _state_dir(project: Path) -> Path:
    for name in (".research-state-v31", ".research-state-v3", ".research-state"):
        candidate = project.resolve() / name
        if candidate.is_dir():
            return candidate
    raise RuntimeError("research state is missing")


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _ensure_state(project: Path) -> Path:
    try:
        return _state_dir(project)
    except RuntimeError:
        research_state.init_state(
            project,
            "algorithmic",
            "competition-autopilot",
            "mathematical-modeling",
        )
        return _state_dir(project)


def _unresolved_review(project: Path) -> dict[str, int]:
    review = _read(_state_dir(project) / "competition_review.json")
    counts = {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0}
    for finding in review.get("findings", []):
        severity = finding.get("severity")
        if severity in counts and finding.get("status", "OPEN") != "RESOLVED":
            counts[severity] += 1
    return counts


def run(
    project: Path,
    *,
    input_path: Path,
    now_utc: datetime | None = None,
    max_steps: int = 64,
) -> dict[str, Any]:
    """Run normal schedule→authorize→execute→check→evidence→graph until ready."""
    project = project.resolve()
    state_dir = _ensure_state(project)
    source = _read(input_path.resolve())
    _write(state_dir / "competition_input.json", source)
    if input_path.resolve() != (project / "competition_input.json").resolve():
        shutil.copy2(input_path, project / "competition_input.json")
    current = now_utc or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise RuntimeError("Competition Director requires a timezone-aware current time")

    rule_verification = competition_runtime.verify_rule_records(
        project,
        source.get("rules", []),
        actor="competition-rule-verifier",
        now_utc=current,
    )
    competition_runtime.configure_clock(
        project,
        str(source["contest_start_utc"]),
        str(source["submission_deadline_utc"]),
        str(source.get("official_rules_source", "")),
        "competition-director",
        now_utc=current,
    )
    competition_runtime.verify_clock(
        project,
        str(source.get("official_rules_source", "")),
        "competition-rule-verifier",
        now_utc=current,
    )

    history: list[dict[str, Any]] = []
    ordinary_author_prompts = 0
    for _ in range(max_steps):
        state = _read(state_dir / "competition_state.json")
        if state.get("submission_readiness") == "COMPETITION_SUBMISSION_READY":
            break
        result = competition_runtime.execute_next(
            project,
            actor="competition-director",
            job_estimates=JOB_ESTIMATES,
            now_utc=current,
        )
        history.append(
            {
                "status": result.get("status"),
                "node": result.get("node"),
                "authorization": (result.get("authorization") or {}).get("decision"),
                "reason": result.get("reason"),
            }
        )
        if (result.get("authorization") or {}).get("decision") == "ASK_AUTHOR":
            ordinary_author_prompts += 1
        if result.get("status") == "HOST_EXECUTION_REQUIRED":
            pending = {
                "operation": "competition-director-run",
                "status": "HOST_EXECUTION_REQUIRED",
                "competition": source.get("competition"),
                "node": result.get("node"),
                "request_path": result.get("request_path") or (result.get("execution") or {}).get("request_path"),
                "host_request_created": True,
                "ordinary_author_prompts": ordinary_author_prompts,
                "history": history,
                "model_behavior_eval": "NOT_RUN",
            }
            _write(state_dir / "competition_completion.json", pending)
            return pending
        if result.get("status") != "PASS":
            break

    state = _read(state_dir / "competition_state.json")
    completion = competition_quality.completion_contract(project)
    unresolved = _unresolved_review(project)
    graph_path, graph = research_graph.load_graph(project)
    graph_check = research_graph.validate_graph(graph)
    execution = _read(project / "logs" / "formal_execution.json") if (project / "logs" / "formal_execution.json").is_file() else {}
    review = _read(state_dir / "competition_review.json")
    repaired = bool(review.get("findings")) and all(
        finding.get("status") == "RESOLVED" for finding in review.get("findings", [])
    )
    status = (
        "PASS"
        if completion["status"] == "PASS"
        and graph_check["status"] == "PASS"
        and ordinary_author_prompts == 0
        else "FAIL"
    )
    final = {
        "operation": "competition-director-run",
        "status": status,
        "competition": state.get("competition"),
        "selected_problem": state.get("selected_problem"),
        "submission_readiness": state.get("submission_readiness", "NOT_READY"),
        "executed_nodes": sum(1 for item in graph.get("nodes", []) if item.get("status") == "PASS"),
        "history": history,
        "actual_code_execution": {
            "exit_code": execution.get("exit_code"),
            "output_sha256": execution.get("output_sha256", ""),
            "command": execution.get("command"),
        },
        "official_rule_verification": rule_verification["status"],
        "automatic_repair": "PASS" if repaired else "FAIL",
        "completion_contract": completion,
        "ordinary_author_prompts": ordinary_author_prompts,
        "unresolved": unresolved,
        "graph_validation": graph_check["status"],
        "graph_path": str(graph_path),
        "model_behavior_eval": "NOT_RUN",
        "harness_class": "COMPETITION_ORCHESTRATION_E2E",
    }
    _write(state_dir / "competition_completion.json", final)
    return final


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--max-steps", type=int, default=64)
    parser.add_argument("--now")
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    now = competition_runtime.parse_utc(args.now) if args.now else None
    try:
        result = run(args.project, input_path=args.input, now_utc=now, max_steps=args.max_steps)
    except (OSError, ValueError, KeyError, RuntimeError, competition_runtime.CompetitionError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2
    if args.output:
        _write(args.output, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
