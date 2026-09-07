#!/usr/bin/env python3
"""Bind a release manifest to the exact successful Hosted CI run and commit."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_CI_MATRIX = (
    "ubuntu-latest / Python 3.10",
    "ubuntu-latest / Python 3.11",
    "ubuntu-latest / Python 3.12",
    "windows-latest / Python 3.10",
    "windows-latest / Python 3.11",
    "windows-latest / Python 3.12",
)


def resolve(
    source: Path,
    output: Path,
    commit: str,
    *,
    run_id: int | None = None,
    workflow: str | None = None,
    branch: str | None = None,
    conclusion: str | None = None,
    matrix_status: str | None = None,
) -> dict[str, object]:
    value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("release manifest must be an object")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
        raise ValueError("source commit must be a 40-character hexadecimal SHA")
    commit = commit.lower()
    source_version = str(value.get("source_version", ""))
    if source_version != "4.0.0":
        raise ValueError(f"release manifest source_version must be 4.0.0, got {source_version or 'missing'}")
    value.update({
        "source_commit": commit,
        "source_commit_mode": "resolved",
        "source_branch": branch or value.get("source_branch", "feat/v4-vendored-research-team"),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "e2e_commit": commit,
        "resolved_by": "hosted-ci-release-integrity",
    })
    if all(item is not None for item in (run_id, workflow, branch, conclusion, matrix_status)):
        value["hosted_ci"] = {
            "run_id": int(run_id),
            "workflow": workflow,
            "branch": branch,
            "head_sha": commit,
            "conclusion": conclusion,
            "matrix": {name: matrix_status for name in REQUIRED_CI_MATRIX},
        }
        ci_ready = conclusion == "success" and matrix_status == "PASS"
        benchmark = value.get("benchmark_suite", {})
        tta = value.get("tta_field_regression", {})
        research_ready = (
            value.get("model_behavior_eval") == "PASS"
            and isinstance(benchmark, dict)
            and benchmark.get("status") == "PASS"
            and benchmark.get("multi_system_parity_gate") == "PASS"
            and benchmark.get("v4_superiority_gate") == "PASS"
            and isinstance(tta, dict)
            and tta.get("formal_campaign") == "COMPLETED"
            and tta.get("publication_sufficiency") == "PASS"
            and tta.get("reviewer_completeness") == "PASS"
        )
        ready = ci_ready and research_ready
        value["recommended_merge"] = "YES" if ready else "NO"
        value["release_disposition"] = (
            "V4.0.0 RELEASE READY"
            if ready
            else "V4.0.0 RC FAIL; Hosted CI passed but behavior or field gates remain incomplete"
            if ci_ready
            else "V4.0.0 RC FAIL; Hosted CI did not pass"
        )
    else:
        value["hosted_ci"] = {"run_id": None, "workflow": None, "branch": None, "head_sha": None, "conclusion": None, "matrix": {}}
        value["recommended_merge"] = "NO"
        value["release_disposition"] = "V4.0.0 RC FAIL; Hosted CI binding is incomplete"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1] / "release_manifest.json")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--workflow")
    parser.add_argument("--branch")
    parser.add_argument("--conclusion", choices=("success", "failure", "cancelled", "pending"))
    parser.add_argument("--matrix-status", choices=("PASS", "FAIL", "PENDING"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        value = resolve(
            args.source,
            args.output,
            args.source_commit,
            run_id=args.run_id,
            workflow=args.workflow,
            branch=args.branch,
            conclusion=args.conclusion,
            matrix_status=args.matrix_status,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return 1
    print(json.dumps({"status": "PASS", "output": str(args.output), "source_commit": value["source_commit"], "release_disposition": value["release_disposition"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
