#!/usr/bin/env python3
"""Recorded host research handoff that executes a native-unsupported classifier."""

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
import director_loop  # noqa: E402
import host_provider_runtime  # noqa: E402
import research_state  # noqa: E402


PROGRAM = r'''#!/usr/bin/env python3
import csv
import json
import sys
from pathlib import Path


source = Path(sys.argv[1])
output = Path(sys.argv[2])
with source.open(encoding="utf-8", newline="") as handle:
    rows = list(csv.DictReader(handle))
if not rows:
    raise SystemExit("classification input is empty")
observations = [(float(row["x"]), int(row["label"])) for row in rows]
class_zero = [value for value, label in observations if label == 0]
class_one = [value for value, label in observations if label == 1]
if not class_zero or not class_one:
    raise SystemExit("both observed classes are required")
threshold = (max(class_zero) + min(class_one)) / 2.0
predictions = [int(value >= threshold) for value, _ in observations]
correct = [int(prediction == label) for prediction, (_, label) in zip(predictions, observations)]
payload = {
    "values": correct,
    "outcome": "classification correctness",
    "selected_method": "observed-class threshold classifier",
    "method_scores": {"accuracy": sum(correct) / len(correct)},
    "threshold": threshold,
    "predictions": predictions,
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


def _seed(project: Path) -> None:
    research_state.init_state(project, "ml-benchmark", "maximum-autonomy", "machine-learning")
    _write(
        project / "inputs" / "research_brief.json",
        {
            "title": "Recorded host classifier generalization",
            "question": "Can a classifier separate the two observed classes?",
            "domain": "machine learning",
            "study_type": "ml-benchmark",
            "scope": "the supplied four-row deterministic fixture",
            "data_file": "inputs/classes.csv",
            "outcome": "label",
            "method_candidates": ["classification"],
        },
    )
    _write(project / "inputs" / "classes.csv", "x,label\n0,0\n1,0\n8,1\n9,1\n")
    _write(
        project / "inputs" / "literature_source.txt",
        "A recorded local source is background context and is not used as a load-bearing novelty claim.\n",
    )


def _handoff(project: Path, task_id: str) -> dict[str, Any]:
    entrypoint = "experiments/run_classifier.py"
    _write(project / entrypoint, PROGRAM)
    return {
        "task_id": task_id,
        "provider_id": "recorded-host-research",
        "status": "PASS",
        "artifacts": [entrypoint],
        "claims": [],
        "uncertainties": ["recorded handoff is not a live model-behavior evaluation"],
        "actions_taken": ["inspected the request and input schema", "implemented a problem-specific classifier"],
        "tool_calls": [{"kind": "write", "path": entrypoint}],
        "commands": [
            {
                "argv": ["{python}", entrypoint, "inputs/classes.csv", "artifacts/formal_results.json"],
                "cwd": ".",
                "expected_outputs": ["artifacts/formal_results.json"],
            }
        ],
        "checker_notes": ["independently syntax-check the entrypoint and execute only after acceptance"],
        "changed_files": [entrypoint],
        "entrypoint": entrypoint,
        "config": None,
        "tests": [f"python -m py_compile {entrypoint}"],
        "expected_outputs": ["artifacts/formal_results.json"],
        "limitations": ["valid only for the supplied numeric binary-class fixture"],
    }


def run(output: Path | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="generic-host-research-") as temporary:
        project = Path(temporary) / "project"
        project.mkdir()
        _seed(project)
        first = director_loop.run(project, max_iterations=32, now="2026-08-29T00:00:00Z")
        task_id = str(host_provider_runtime.pending(project)["requests"][0]["task_id"])
        received = host_provider_runtime.receive(project, _handoff(project, task_id))
        checked = host_provider_runtime.check(project, task_id, checker_id="deterministic-research-checker")
        final = director_loop.run(project, max_iterations=48, now="2026-08-29T00:00:00Z")
        execution_path = project / "artifacts" / "formal_execution.json"
        execution = json.loads(execution_path.read_text(encoding="utf-8")) if execution_path.is_file() else {}
        passed = (
            first.get("status") == "HOST_EXECUTION_REQUIRED"
            and received.get("state") == "HOST_HANDOFF_RECEIVED"
            and checked.get("status") == "ACCEPTED"
            and final.get("status") == "READY_FOR_SUBMISSION"
            and execution.get("status") == "PASS"
            and execution.get("host_provider_id") == "recorded-host-research"
        )
        result = {
            "operation": "generic-host-research-e2e",
            "evaluation_class": "RECORDED_HOST_HANDOFF_E2E",
            "status": "PASS" if passed else "FAIL",
            "host_request_created": first.get("host_request_created") is True,
            "host_handoff_received": received.get("state") == "HOST_HANDOFF_RECEIVED",
            "deterministic_execution": execution.get("status") == "PASS",
            "checker": (checked.get("checker") or {}).get("status", "FAIL"),
            "ordinary_author_prompts": final.get("ordinary_author_prompts", first.get("ordinary_author_prompts", 0)),
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
