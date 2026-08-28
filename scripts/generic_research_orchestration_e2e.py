#!/usr/bin/env python3
"""Network-recorded, input-derived generic research Provider orchestration E2E."""

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
import research_state  # noqa: E402


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        path.write_text(value, encoding="utf-8", newline="\n")
    else:
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(output: Path | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="generic-research-provider-") as temporary:
        project = Path(temporary)
        research_state.init_state(project, "engineering-system", "maximum-autonomy", "software-engineering")
        _write(project / "inputs" / "research_brief.json", {
            "title": "Build latency trend study",
            "question": "Which of two simple candidate methods better summarizes the observed build-latency trend?",
            "scope": "the eight supplied public build observations",
            "phenomenon": "build latency over ordered releases",
            "outcome": "latency_ms",
            "data_file": "inputs/build_latency.csv",
            "method_candidates": ["constant_mean", "linear_trend"],
            "gap": "The repository lacks an input-derived comparison of two transparent baselines.",
        })
        _write(project / "inputs" / "build_latency.csv", "release,latency_ms\n1,120\n2,118\n3,115\n4,112\n5,109\n6,108\n7,104\n8,101\n")
        _write(project / "inputs" / "literature_candidates.json", [
            {
                "title": "Regression diagnostics for empirical software engineering",
                "doi": "10.1145/recorded.fixture.1", "url": "https://doi.org/10.1145/recorded.fixture.1",
                "identity": "VERIFIED_METADATA", "retrieved": False, "exact_region": "UNRESOLVED",
            },
            {
                "title": "Time-respecting validation for software measurements",
                "doi": "10.1145/recorded.fixture.2", "url": "https://doi.org/10.1145/recorded.fixture.2",
                "identity": "VERIFIED_METADATA", "retrieved": False, "exact_region": "UNRESOLVED",
            },
        ])
        director = director_loop.run(project, max_iterations=48, actor="generic-e2e", now="2026-08-28T00:00:00Z")
        formal = json.loads((project / "artifacts" / "formal_results.json").read_text(encoding="utf-8")) if (project / "artifacts" / "formal_results.json").is_file() else {}
        execution = json.loads((project / "artifacts" / "formal_execution.json").read_text(encoding="utf-8")) if (project / "artifacts" / "formal_execution.json").is_file() else {}
        review = json.loads((project / "artifacts" / "review_findings.json").read_text(encoding="utf-8")) if (project / "artifacts" / "review_findings.json").is_file() else {}
        repaired = bool(review.get("findings")) and all(item.get("status") == "RESOLVED" for item in review.get("findings", []))
        result = {
            "operation": "generic-research-orchestration-e2e",
            "evaluation_class": "GENERIC_RESEARCH_ORCHESTRATION_E2E",
            "status": "PASS" if director.get("status") == "READY_FOR_SUBMISSION" and execution.get("exit_status") == 0 and repaired else "FAIL",
            "model_behavior": "NOT_RUN",
            "ordinary_author_prompts": director.get("ordinary_author_prompts"),
            "provider_id": "coding-provider",
            "selected_method": formal.get("selected_method"),
            "actual_command": {"exit_status": execution.get("exit_status"), "command": execution.get("command")},
            "input_derived": formal.get("values") == [120.0, 118.0, 115.0, 112.0, 109.0, 108.0, 104.0, 101.0],
            "review_repair": "PASS" if repaired else "FAIL",
            "submission_readiness": director.get("status"),
            "director_diagnostics": director if director.get("status") != "READY_FOR_SUBMISSION" else {},
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
