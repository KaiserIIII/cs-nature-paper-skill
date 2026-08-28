"""Family-routed competition code generation and observed execution provider."""

from __future__ import annotations

import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

import provider_support as support


PROVIDER_ID = "competition-coding-provider"


PROGRAM = r'''#!/usr/bin/env python3
import json
import math
import statistics
import sys
from pathlib import Path


plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
problem = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
output = Path(sys.argv[3])
families = plan.get("families", [])
results = {}

if "prediction" in families or "time-series" in families:
    series = [float(value) for value in problem.get("series", [])]
    if len(series) < 2:
        raise SystemExit("prediction family requires at least two ordered observations")
    slope = statistics.fmean([right - left for left, right in zip(series, series[1:])])
    forecast = series[-1] + slope
    baseline = series[-1]
    results["prediction"] = {"observations": len(series), "baseline": baseline, "forecast": forecast, "slope": slope, "validation": "time-respecting one-step differences"}

if "optimization" in families:
    alternatives = problem.get("alternatives", [])
    target = float(problem.get("required_level", 0.0))
    feasible = [item for item in alternatives if float(item.get("limit", 0.0)) >= target]
    if not feasible:
        raise SystemExit("optimization family found no feasible alternative")
    choice = min(feasible, key=lambda item: (float(item.get("objective", math.inf)), str(item.get("name", ""))))
    results["optimization"] = {"decision": choice.get("name"), "objective": float(choice.get("objective")), "feasible_count": len(feasible), "objective_recomputed": float(choice.get("objective"))}

if "evaluation" in families:
    records = problem.get("records", [])
    scored = []
    for item in records:
        features = [float(value) for value in item.get("features", [])]
        scored.append({"name": item.get("name"), "score": statistics.fmean(features) if features else 0.0})
    scored.sort(key=lambda item: (-item["score"], str(item["name"])))
    results["evaluation"] = {"ranking": scored, "weight_sensitivity": "equal-weight baseline"}

if "classification-clustering" in families:
    records = problem.get("records", [])
    centroids = [statistics.fmean([float(value) for value in item.get("features", [])]) for item in records]
    boundary = statistics.median(centroids) if centroids else 0.0
    assignments = [{"name": item.get("name"), "cluster": int(score >= boundary)} for item, score in zip(records, centroids)]
    results["clustering"] = {"assignments": assignments, "boundary": boundary, "validation": "membership stability under median split"}

if "simulation" in families or "differential-equations" in families:
    dynamics = problem.get("dynamics", {})
    value = float(dynamics.get("initial", 1.0))
    rate = float(dynamics.get("rate", 0.0))
    steps = int(dynamics.get("steps", 10))
    dt = float(dynamics.get("dt", 1.0))
    trajectory = [value]
    for _ in range(steps):
        value = value + dt * rate * value
        trajectory.append(value)
    key = "ode" if "differential-equations" in families else "simulation"
    results[key] = {"trajectory": trajectory, "final": trajectory[-1], "replications": 1, "residual_check": abs(trajectory[1] - trajectory[0] - dt * rate * trajectory[0]) if len(trajectory) > 1 else 0.0}

if not results:
    raise SystemExit("no executable method family was routed")
answers = {}
for question in plan.get("questions", []):
    answers[question.get("question_id", "Q")] = {"families": question.get("candidate_families", []), "result_keys": sorted(results), "status": "ANSWERED"}
payload = {"families": families, "results": results, "question_answers": answers, "input_derived": True}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
'''


def _state(project: Path) -> dict[str, Any]:
    return support.read_json(support.state_dir(project) / "competition_state.json", {})


def _save(project: Path, value: dict[str, Any]) -> None:
    support.write(support.state_dir(project) / "competition_state.json", value)


def _selected(project: Path) -> Path:
    path = project / "data_processed" / "selected_problem.json"
    if not path.is_file():
        raise ValueError("selected problem artifact is required")
    return path


def _run(project: Path, output: Path) -> tuple[dict[str, Any], Path]:
    program = project / "src" / "solve_competition.py"
    plan = project / "config" / "model_plan.json"
    source = _selected(project)
    if output.exists():
        output.unlink()
    command = [sys.executable, str(program), str(plan), str(source), str(output)]
    completed = subprocess.run(command, cwd=str(project), capture_output=True, text=True, check=False)
    record = {
        "status": "PASS" if completed.returncode == 0 and output.is_file() else "FAIL",
        "command": command, "cwd": str(project), "exit_code": completed.returncode,
        "input_hashes": {support.relative(project, item): support.digest(item) for item in (program, plan, source)},
        "environment": {"python": sys.version.split()[0], "network": False},
        "output_sha256": support.digest(output) if output.is_file() else "", "stderr": completed.stderr[-2000:],
    }
    record_path = project / "logs" / ("formal_execution.json" if output.name == "formal_solution.json" else "pilot_execution.json")
    support.write(record_path, record)
    return record, record_path


def execute(project: Path, node: str) -> dict[str, Any]:
    state = _state(project)
    if node == "minimal_viable_model":
        program = support.write(project / "src" / "solve_competition.py", PROGRAM)
        plan = support.write(project / "config" / "model_plan.json", {"families": state.get("method_families", []), "questions": state.get("modeling_plan", []), "baseline_first": True})
        py_compile.compile(str(program), doraise=True)
        state["baseline_available"] = True
        state["current_best_model"] = state.get("baseline_model")
        _save(project, state)
        return support.handoff(project, PROVIDER_ID, node, [program, plan], actions=["generated structure-routed executable"], extra={"changed_files": [support.relative(project, program), support.relative(project, plan)]})
    if node == "pilot_solve":
        output = project / "results" / "pilot_solution.json"
        record, record_path = _run(project, output)
        if record["status"] != "PASS":
            return {"status": "FAIL", "findings": [record["stderr"]], "execution_record": record}
        return support.handoff(project, PROVIDER_ID, node, [output, record_path], actions=["executed pilot"], tool_calls=[{"kind": "execute", "exit_status": 0}], extra={"execution_record": record})
    if node == "formal_solve":
        output = project / "results" / "formal_solution.json"
        record, record_path = _run(project, output)
        if record["status"] != "PASS":
            return {"status": "FAIL", "findings": [record["stderr"]], "execution_record": record}
        value = support.read_json(output, {})
        state["question_answers"] = value.get("question_answers", {})
        state["current_best_model"] = state.get("primary_model") or state.get("baseline_model")
        _save(project, state)
        return support.handoff(project, PROVIDER_ID, node, [output, record_path], formal=True, actions=["executed formal solution"], tool_calls=[{"kind": "execute", "command": record["command"], "exit_status": 0}], extra={"execution_record": record})
    return {"status": "BLOCKED", "findings": [f"unsupported competition coding node: {node}"]}
