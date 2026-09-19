#!/usr/bin/env python3
"""Recorded host competition handoffs for graph modeling and executable solving."""

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
import host_provider_runtime  # noqa: E402


RULE_IDS = (
    "contest_time", "problem_count", "participant_eligibility", "ai_policy", "paper_format", "page_limit",
    "file_naming", "attachments", "code_requirements", "submission_platform", "submission_method", "anonymity", "discipline",
)


PROGRAM = r'''#!/usr/bin/env python3
import heapq
import json
import sys
from pathlib import Path


problem = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
output = Path(sys.argv[2])
vertices = {str(item) for item in problem.get("vertices", [])}
graph = {vertex: [] for vertex in vertices}
for edge in problem.get("edges", []):
    left, right, weight = str(edge["from"]), str(edge["to"]), float(edge["weight"])
    if weight < 0:
        raise SystemExit("Dijkstra requires non-negative edge weights")
    graph.setdefault(left, []).append((right, weight))
    graph.setdefault(right, []).append((left, weight))
source, target = str(problem["source"]), str(problem["target"])
queue = [(0.0, source, [source])]
best = {source: 0.0}
answer = None
while queue:
    distance, vertex, path = heapq.heappop(queue)
    if distance != best.get(vertex):
        continue
    if vertex == target:
        answer = {"distance": distance, "path": path}
        break
    for neighbor, weight in graph.get(vertex, []):
        candidate = distance + weight
        if candidate < best.get(neighbor, float("inf")):
            best[neighbor] = candidate
            heapq.heappush(queue, (candidate, neighbor, path + [neighbor]))
if answer is None:
    raise SystemExit("target is unreachable")
payload = {
    "families": ["graph-network"],
    "results": {"graph-network": answer},
    "question_answers": {"Q1": {"status": "ANSWERED", **answer}},
    "input_derived": True,
}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
'''


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        path.write_text(value, encoding="utf-8", newline="\n")
    else:
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _fixture() -> dict[str, Any]:
    rules = [
        {
            "rule_id": item,
            "value": f"recorded value for {item}",
            "source_type": "OFFICIAL_PRIMARY",
            "official_source": "fixture://official-rules/current",
            "retrieved_utc": "2026-09-10T08:00:00Z",
            "exact_region": f"rules#{item}",
        }
        for item in RULE_IDS
    ]
    return {
        "competition": "Generic Graph Modeling Contest",
        "contest_start_utc": "2026-09-10T08:00:00Z",
        "submission_deadline_utc": "2026-09-13T08:00:00Z",
        "official_rules_source": "fixture://official-rules/current",
        "rules": rules,
        "problems": [
            {
                "id": "GRAPH",
                "title": "Minimum weighted connection between named vertices",
                "vertices": ["A", "B", "C", "D"],
                "edges": [
                    {"from": "A", "to": "B", "weight": 1},
                    {"from": "B", "to": "D", "weight": 2},
                    {"from": "A", "to": "C", "weight": 4},
                    {"from": "C", "to": "D", "weight": 1},
                ],
                "source": "A",
                "target": "D",
                "questions": [
                    {
                        "id": "Q1",
                        "goal": "Determine the minimum weighted connection between the named vertices.",
                    }
                ],
            }
        ],
    }


def _model_handoff(project: Path, task_id: str) -> dict[str, Any]:
    artifact = "config/host_model_plan.json"
    plan = {
        "questions": [
            {
                "question_id": "Q1",
                "formulation": "shortest path in an undirected non-negative weighted graph",
                "variables": ["path vertex sequence"],
                "parameters": ["observed edge weights"],
                "assumptions": ["all supplied edge weights are non-negative"],
                "objective": "minimize total path weight from A to D",
                "constraints": ["successive path vertices must share a supplied edge"],
                "baseline": "enumerate simple paths on the small fixture",
                "primary_model": "Dijkstra shortest-path algorithm",
                "upgrade_condition": "use another solver only if negative weights are observed",
                "validation_plan": ["recompute path weight", "check every reported edge", "compare with bounded enumeration"],
                "implementation_plan": "parse the selected problem and execute Dijkstra deterministically",
                "candidate_families": ["graph-network"],
            }
        ]
    }
    _write(project / artifact, plan)
    return {
        "task_id": task_id,
        "provider_id": "recorded-host-competition-modeler",
        "status": "PASS",
        "artifacts": [artifact],
        "claims": [],
        "uncertainties": ["plan is scoped to a non-negative weighted graph"],
        "actions_taken": ["inspected graph structure", "created a per-question modeling plan"],
        "tool_calls": [{"kind": "write", "path": artifact}],
        "commands": [],
        "checker_notes": ["validate all required per-question fields independently"],
    }


def _code_handoff(project: Path, task_id: str) -> dict[str, Any]:
    entrypoint = "src/solve_graph.py"
    _write(project / entrypoint, PROGRAM)
    return {
        "task_id": task_id,
        "provider_id": "recorded-host-competition-coder",
        "status": "PASS",
        "artifacts": [entrypoint],
        "claims": [],
        "uncertainties": ["solver rejects negative weights and unreachable targets"],
        "actions_taken": ["inspected the accepted model plan", "implemented a problem-derived Dijkstra solver"],
        "tool_calls": [{"kind": "write", "path": entrypoint}],
        "commands": [
            {
                "argv": ["{python}", entrypoint, "data_processed/selected_problem.json", "{output}"],
                "cwd": ".",
                "expected_outputs": ["{output}"],
            }
        ],
        "checker_notes": ["syntax-check before deterministic pilot and formal executions"],
        "changed_files": [entrypoint],
        "entrypoint": entrypoint,
        "config": None,
        "tests": [f"python -m py_compile {entrypoint}"],
        "expected_outputs": ["{output}"],
        "limitations": ["non-negative undirected weighted graphs only"],
    }


def _accept(project: Path, handoff: dict[str, Any], checker: str) -> tuple[dict[str, Any], dict[str, Any]]:
    received = host_provider_runtime.receive(project, handoff)
    checked = host_provider_runtime.check(project, str(handoff["task_id"]), checker_id=checker)
    return received, checked


def run(output: Path | None = None) -> dict[str, Any]:
    now = competition_runtime.parse_utc("2026-09-10T16:00:00Z")
    with tempfile.TemporaryDirectory(prefix="generic-host-competition-") as temporary:
        project = Path(temporary) / "project"
        project.mkdir()
        input_path = project / "competition_input.json"
        _write(input_path, _fixture())
        first = competition_director.run(project, input_path=input_path, now_utc=now, max_steps=32)
        model_request = host_provider_runtime.pending(project)["requests"][0]
        model_received, model_checked = _accept(
            project,
            _model_handoff(project, str(model_request["task_id"])),
            "deterministic-modeling-checker",
        )
        second = competition_director.run(project, input_path=input_path, now_utc=now, max_steps=32)
        code_request = host_provider_runtime.pending(project)["requests"][0]
        code_received, code_checked = _accept(
            project,
            _code_handoff(project, str(code_request["task_id"])),
            "deterministic-code-checker",
        )
        final = competition_director.run(project, input_path=input_path, now_utc=now, max_steps=64)
        execution_path = project / "logs" / "formal_execution.json"
        execution = json.loads(execution_path.read_text(encoding="utf-8")) if execution_path.is_file() else {}
        formal_path = project / "results" / "formal_solution.json"
        formal = json.loads(formal_path.read_text(encoding="utf-8")) if formal_path.is_file() else {}
        passed = (
            first.get("status") == "HOST_EXECUTION_REQUIRED"
            and second.get("status") == "HOST_EXECUTION_REQUIRED"
            and model_checked.get("status") == "ACCEPTED"
            and code_checked.get("status") == "ACCEPTED"
            and final.get("status") == "PASS"
            and execution.get("status") == "PASS"
            and bool(execution.get("input_hashes"))
            and formal.get("input_derived") is True
            and formal.get("results", {}).get("graph-network", {}).get("distance") == 3.0
        )
        result = {
            "operation": "generic-host-competition-e2e",
            "evaluation_class": "RECORDED_HOST_HANDOFF_E2E",
            "status": "PASS" if passed else "FAIL",
            "host_request_created": first.get("host_request_created") is True and second.get("host_request_created") is True,
            "host_handoff_received": model_received.get("state") == "HOST_HANDOFF_RECEIVED" and code_received.get("state") == "HOST_HANDOFF_RECEIVED",
            "deterministic_execution": execution.get("status") == "PASS" and formal.get("input_derived") is True,
            "checker": "PASS" if model_checked.get("status") == "ACCEPTED" and code_checked.get("status") == "ACCEPTED" else "FAIL",
            "ordinary_author_prompts": final.get("ordinary_author_prompts", 0),
            "model_behavior": "RECORDED_HANDOFF",
            "model_behavior_eval": "NOT_RUN",
        }
    if output:
        _write(output, result)
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
