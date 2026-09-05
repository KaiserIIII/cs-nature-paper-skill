#!/usr/bin/env python3
"""Run the harness self-test through the normal Director orchestration runtime."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SKILL_VERSION = "3.2.1"


def _load(name: str):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("v32_full_e2e_" + name, path)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    spec.loader.exec_module(module)
    return module


orchestration = _load("director_orchestration_e2e")
WORKFLOW = list(orchestration.executor_runtime.MAIN_SEQUENCE)


def _commit() -> str:
    try:
        return subprocess.run(["git", "-C", str(Path(__file__).resolve().parents[1]), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def run(output: Path | None = None, *, root: Path | None = None) -> dict[str, Any]:
    director = orchestration.run(root=root)
    result = {
        "operation": "full-paper-e2e",
        "skill_version": SKILL_VERSION,
        "status": "PASS" if orchestration.validate(director)["status"] == "PASS" else "FAIL",
        "evaluation_class": "HARNESS_SELF_TEST",
        "model_behavior": "NOT_RUN",
        "skill_commit": _commit(),
        "workflow": WORKFLOW,
        "anchor_count": director.get("anchor_count", 0),
        "execution_record": director.get("execution_record", {}),
        "literature": director.get("literature", {}),
        "artifacts": director.get("artifacts", {}),
        "completion": director.get("completion", {}),
        "director_orchestration": director,
        "privacy": director.get("privacy"),
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def validate(result: dict[str, Any], root: Path) -> dict[str, Any]:
    findings = []
    if result.get("status") != "PASS": findings.append("e2e status is not PASS")
    if result.get("evaluation_class") != "HARNESS_SELF_TEST": findings.append("evaluation_class must be HARNESS_SELF_TEST")
    if result.get("model_behavior") != "NOT_RUN": findings.append("model_behavior must remain NOT_RUN")
    if result.get("skill_commit") != _commit(): findings.append("skill_commit is stale")
    if result.get("workflow") != WORKFLOW: findings.append("workflow is not the normal Director executor sequence")
    nested = result.get("director_orchestration", {})
    if nested.get("evaluation_class") != "DIRECTOR_ORCHESTRATION_E2E" or nested.get("status") != "PASS": findings.append("Director orchestration E2E did not pass")
    return {"operation": "validate-full-paper-e2e", "status": "PASS" if not findings else "FAIL", "findings": findings}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--root", type=Path)
    args = parser.parse_args()
    result = run(args.output, root=args.root)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result.get("status") == "PASS" else 1)
