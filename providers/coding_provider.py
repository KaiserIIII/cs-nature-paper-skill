"""Project-aware research implementation and observed command execution provider."""

from __future__ import annotations

import json
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

import provider_support as support


PROVIDER_ID = "coding-provider"


PROGRAM = r'''#!/usr/bin/env python3
import csv
import json
import math
import sys
from pathlib import Path


def numeric(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


config = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
data_path = Path(sys.argv[2])
output_path = Path(sys.argv[3])
with data_path.open(encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle))
if not rows:
    raise SystemExit("input data has no rows")
columns = list(rows[0])
numeric_columns = [name for name in columns if any(numeric(row.get(name)) is not None for row in rows)]
target = config.get("outcome") if config.get("outcome") in numeric_columns else numeric_columns[-1]
values = [numeric(row.get(target)) for row in rows]
values = [value for value in values if value is not None and math.isfinite(value)]
if len(values) < 2:
    raise SystemExit("at least two finite outcome values are required")
x = list(range(len(values)))
mean = sum(values) / len(values)
denominator = sum((item - sum(x) / len(x)) ** 2 for item in x)
slope = sum((item - sum(x) / len(x)) * (value - mean) for item, value in zip(x, values)) / denominator if denominator else 0.0
intercept = mean - slope * (sum(x) / len(x))
constant_predictions = [mean for _ in values]
trend_predictions = [intercept + slope * item for item in x]
mae = lambda predictions: sum(abs(value - predicted) for value, predicted in zip(values, predictions)) / len(values)
scores = {"constant_mean": mae(constant_predictions), "linear_trend": mae(trend_predictions)}
requested = config.get("method_candidates") or list(scores)
eligible = [name for name in requested if name in scores] or list(scores)
selected = min(eligible, key=lambda name: (scores[name], name))
result = {
    "input_rows": len(rows), "columns": columns, "numeric_columns": numeric_columns,
    "outcome": target, "values": values, "mean": mean, "slope": slope,
    "method_scores": scores, "candidate_methods": eligible, "selected_method": selected,
    "next_prediction": mean if selected == "constant_mean" else intercept + slope * len(values),
}
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
'''


def scan_project(project: Path) -> dict[str, Any]:
    patterns = {
        "entrypoints": {"main.py", "app.py", "run.py", "cli.py"},
        "loaders": {"loader.py", "data.py", "dataset.py"},
        "configs": {"pyproject.toml", "requirements.txt", "environment.yml"},
        "tests": set(), "scripts": set(), "notebooks": set(), "models": set(), "outputs": set(),
    }
    inventory = {key: [] for key in patterns}
    for path in project.rglob("*"):
        if not path.is_file() or ".research-state" in path.parts:
            continue
        relative = path.relative_to(project).as_posix()
        if path.name in patterns["entrypoints"]:
            inventory["entrypoints"].append(relative)
        if path.name in patterns["loaders"]:
            inventory["loaders"].append(relative)
        if path.name in patterns["configs"]:
            inventory["configs"].append(relative)
        if "tests" in path.parts or path.name.startswith("test_"):
            inventory["tests"].append(relative)
        if "scripts" in path.parts or "experiments" in path.parts:
            inventory["scripts"].append(relative)
        if path.suffix == ".ipynb":
            inventory["notebooks"].append(relative)
        if "models" in path.parts:
            inventory["models"].append(relative)
        if any(name in path.parts for name in ("outputs", "results", "artifacts")):
            inventory["outputs"].append(relative)
    return inventory


def _data_path(project: Path, brief: dict[str, Any]) -> Path:
    relative = brief.get("data_file")
    if relative:
        path = (project / str(relative)).resolve()
        if path.is_file() and project.resolve() in path.parents:
            return path
    candidates = sorted((project / "inputs").glob("*.csv")) if (project / "inputs").is_dir() else []
    if not candidates:
        raise ValueError("a project-local CSV data file is required")
    return candidates[0]


def execute(project: Path, node: str) -> dict[str, Any]:
    brief = support.read_json(project / "inputs" / "research_brief.json", {})
    data = _data_path(project, brief)
    artifacts = project / "artifacts"
    if node == "pilot":
        inventory = scan_project(project)
        path = support.write(artifacts / "pilot_results.json", {
            "status": "PASS", "data_file": data.relative_to(project).as_posix(),
            "input_sha256": support.digest(data), "candidate_methods": brief.get("method_candidates", []),
            "project_inventory": inventory, "purpose": "feasibility and schema check",
        })
        return support.handoff(project, PROVIDER_ID, node, [path], actions=["scanned repository", "checked input data"])
    implementation = project / "experiments" / "run_research.py"
    config = project / "experiments" / "research_config.json"
    if node == "implementation":
        actions = []
        if implementation.exists():
            try:
                py_compile.compile(str(implementation), doraise=True)
            except py_compile.PyCompileError:
                actions.append("repaired_invalid_implementation")
        previous = implementation.read_text(encoding="utf-8") if implementation.exists() else None
        support.write(implementation, PROGRAM)
        support.write(config, {
            "research_question": brief.get("question"), "outcome": brief.get("outcome"),
            "method_candidates": brief.get("method_candidates", ["constant_mean", "linear_trend"]),
        })
        if previous != PROGRAM and not actions:
            actions.append("created_or_updated_project_aware_implementation")
        py_compile.compile(str(implementation), doraise=True)
        check = subprocess.run([sys.executable, "-m", "py_compile", str(implementation)], cwd=str(project), capture_output=True, text=True, check=False)
        if check.returncode:
            return {"status": "FAIL", "findings": [check.stderr]}
        return support.handoff(project, PROVIDER_ID, node, [implementation, config], actions=actions, extra={"changed_files": [support.relative(project, implementation), support.relative(project, config)], "tests": [{"command": "python -m py_compile", "exit_status": 0}]})
    if node != "formal_experiment":
        return {"status": "BLOCKED", "findings": [f"unsupported coding node: {node}"]}
    output = artifacts / "formal_results.json"
    record_path = artifacts / "formal_execution.json"
    if output.exists():
        output.unlink()
    command = [sys.executable, str(implementation), str(config), str(data), str(output)]
    completed = subprocess.run(command, cwd=str(project), capture_output=True, text=True, check=False)
    record = {
        "status": "PASS" if completed.returncode == 0 and output.is_file() else "FAIL",
        "command": command, "cwd": str(project), "exit_status": completed.returncode,
        "input_hashes": {support.relative(project, path): support.digest(path) for path in (implementation, config, data)},
        "environment": {"python": sys.version.split()[0], "network": False, "phase": "FORMAL"},
        "outputs": [{"path": support.relative(project, output), "sha256": support.digest(output), "produced_by_command": True}] if output.is_file() else [],
        "stderr": completed.stderr[-2000:], "stdout": completed.stdout[-2000:],
    }
    support.write(record_path, record)
    if record["status"] != "PASS":
        return {"status": "FAIL", "findings": ["formal command failed"], "execution_record": record}
    return support.handoff(project, PROVIDER_ID, node, [output, record_path], formal=True, actions=["executed formal command"], tool_calls=[{"kind": "execute", "command": command, "exit_status": completed.returncode}], extra={"execution_record": record})
