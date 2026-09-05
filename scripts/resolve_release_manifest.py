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
    value.update({
        "source_version": "3.2.0",
        "source_commit": commit,
        "source_commit_mode": "resolved",
        "source_branch": branch or value.get("source_branch", "v3.2"),
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
        ready = conclusion == "success" and matrix_status == "PASS"
        if branch == "hotfix/v321-specialist-routing-final":
            value["release_disposition"] = "CORRECT-BASE V3.2.1 RC" if ready else "CORRECT-BASE V3.2.1 RC BLOCKED"
        else:
            value["release_disposition"] = "V3.2.0 RELEASE READY" if ready else "V3.2.0 RELEASE BLOCKED"
    else:
        value["hosted_ci"] = {"run_id": None, "workflow": None, "branch": None, "head_sha": None, "conclusion": None, "matrix": {}}
        value["release_disposition"] = "V3.2.0 RELEASE BLOCKED; Hosted CI binding is incomplete"
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
