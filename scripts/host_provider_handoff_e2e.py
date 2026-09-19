#!/usr/bin/env python3
"""Exercise the recorded request→receive→check→accept host lifecycle."""

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
import host_provider_runtime  # noqa: E402


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        path.write_text(value, encoding="utf-8", newline="\n")
    else:
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(output: Path | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="host-provider-handoff-") as temporary:
        project = Path(temporary)
        request = {
            "task_id": "recorded-handoff-e2e",
            "node": "implementation",
            "capability": "code-generation",
            "formal": False,
            "inputs": [],
            "constraints": ["local recorded fixture only"],
            "required_outputs": ["typed code handoff"],
            "evidence_requirements": ["artifact hash", "independent checker"],
            "forbidden_claims": ["unexecuted code passed"],
            "permissions": {"local_read": True, "local_write": True, "execute": True},
            "budget": {"money": 0},
        }
        created = host_provider_runtime.create_request(project, request)
        artifact = "src/recorded.py"
        _write(project / artifact, "print('recorded host handoff')\n")
        handoff = {
            "task_id": request["task_id"],
            "provider_id": "recorded-host-provider",
            "status": "PASS",
            "artifacts": [artifact],
            "claims": [],
            "uncertainties": ["not a live model evaluation"],
            "actions_taken": ["created a recorded fixture artifact"],
            "tool_calls": [{"kind": "write", "path": artifact}],
            "commands": [{"argv": ["{python}", artifact], "cwd": ".", "expected_outputs": []}],
            "checker_notes": ["syntax and containment are independently checked"],
            "changed_files": [artifact],
            "entrypoint": artifact,
            "config": None,
            "tests": [f"python -m py_compile {artifact}"],
            "expected_outputs": [],
            "limitations": ["lifecycle fixture only"],
        }
        received = host_provider_runtime.receive(project, handoff)
        checked = host_provider_runtime.check(project, request["task_id"], checker_id="recorded-independent-checker")
        expected_lifecycle = [
            "REQUEST_CREATED", "HOST_EXECUTION_REQUIRED", "HOST_HANDOFF_RECEIVED", "CHECKING", "ACCEPTED",
        ]
        passed = (
            created.get("status") == "HOST_EXECUTION_REQUIRED"
            and received.get("state") == "HOST_HANDOFF_RECEIVED"
            and checked.get("status") == "ACCEPTED"
            and checked.get("lifecycle") == expected_lifecycle
        )
        result = {
            "operation": "host-provider-handoff-e2e",
            "evaluation_class": "RECORDED_HOST_HANDOFF_E2E",
            "status": "PASS" if passed else "FAIL",
            "host_request_created": created.get("host_request_created") is True,
            "host_handoff_received": received.get("state") == "HOST_HANDOFF_RECEIVED",
            "checker": (checked.get("checker") or {}).get("status", "FAIL"),
            "lifecycle": checked.get("lifecycle", []),
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
