#!/usr/bin/env python3
"""Deterministic Director -> executor -> artifact -> evidence -> completion E2E."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SKILL_VERSION = "3.2.0"


def _load(name: str):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("v32_orchestration_e2e_" + name, path)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    spec.loader.exec_module(module)
    return module


state_runtime = _load("research_state")
director_runtime = _load("director_loop")
completion_runtime = _load("completion_contract")
executor_runtime = _load("research_executor")


def _commit() -> str:
    try:
        return subprocess.run(["git", "-C", str(Path(__file__).resolve().parents[1]), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        path.write_text(value, encoding="utf-8")
    else:
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _sanitize(value: Any, private_root: Path) -> Any:
    if isinstance(value, str):
        return value.replace(str(private_root), "<TEMP_PROJECT>")
    if isinstance(value, list):
        return [_sanitize(item, private_root) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize(item, private_root) for key, item in value.items()}
    return value


def _seed(project: Path) -> None:
    _write(project / "inputs" / "research_brief.json", {
        "title": "Evidence-bound autonomous research fixture",
        "question": "Does the normal Director runtime preserve output provenance for a deterministic fixture?",
        "scope": "public synthetic fixture only",
        "source_title": "Synthetic provenance source",
    })
    _write(project / "inputs" / "literature_source.txt", "Deterministic execution records connect commands to content-addressed outputs.\n")


def run(output: Path | None = None, *, root: Path | None = None) -> dict[str, Any]:
    base = (root or Path(__file__).resolve().parents[1]).resolve()
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".v32-director-e2e-", dir=str(base)) as temporary:
        project = Path(temporary)
        state_runtime.init_state(project, "engineering-system", "maximum-autonomy", "systems")
        _seed(project)
        director = director_runtime.run(project, max_iterations=40, actor="e2e", now="2026-08-28T00:00:00Z")
        skeleton = {
            "status": "PASS" if director.get("status") == "READY_FOR_SUBMISSION" else "FAIL",
            "evaluation_class": "DIRECTOR_ORCHESTRATION_E2E",
            "model_behavior": "NOT_RUN",
            "skill_commit": _commit(),
        }
        e2e_path = project / "director-orchestration-e2e.json"
        _write(e2e_path, skeleton)
        completion = completion_runtime.evaluate(project, e2e_result=e2e_path)
        execution = json.loads((project / "artifacts" / "formal_execution.json").read_text(encoding="utf-8")) if (project / "artifacts" / "formal_execution.json").exists() else {}
        literature = json.loads((project / "artifacts" / "literature.json").read_text(encoding="utf-8")) if (project / "artifacts" / "literature.json").exists() else {}
        artifact_names = ("formal_results.json", "analysis.json", "figure.svg", "manuscript.md", "package_manifest.json")
        artifacts = {
            name: "sha256:" + hashlib.sha256((project / "artifacts" / name).read_bytes()).hexdigest()
            for name in artifact_names if (project / "artifacts" / name).is_file()
        }
        ledger = json.loads((project / ".research-state" / "evidence_ledger.json").read_text(encoding="utf-8"))
        result = {
            "operation": "director-orchestration-e2e",
            "skill_version": SKILL_VERSION,
            "status": "PASS" if director.get("status") == "READY_FOR_SUBMISSION" and completion.get("status") == "PASS" else "FAIL",
            "evaluation_class": "DIRECTOR_ORCHESTRATION_E2E",
            "model_behavior": "NOT_RUN",
            "skill_commit": _commit(),
            "workflow": list(executor_runtime.MAIN_SEQUENCE),
            "director": director,
            "ordinary_author_prompts": director.get("ordinary_author_prompts"),
            "anchor_count": len(ledger.get("anchors", [])),
            "execution_record": {"status": execution.get("status"), "exit_status": execution.get("exit_status"), "outputs": execution.get("outputs", [])},
            "literature": {"sources": literature.get("sources", []), "retrieval_records": literature.get("retrieval_records", []), "verified_relations": literature.get("verified_relations", [])},
            "artifacts": artifacts,
            "completion": _sanitize(completion, project),
            "privacy": "synthetic temporary project; private absolute paths removed from public result",
        }
        if output is not None:
            _write(output, result)
        return result


def validate(result: dict[str, Any]) -> dict[str, Any]:
    findings = []
    if result.get("status") != "PASS": findings.append("orchestration status is not PASS")
    if result.get("evaluation_class") != "DIRECTOR_ORCHESTRATION_E2E": findings.append("wrong evaluation class")
    if result.get("model_behavior") != "NOT_RUN": findings.append("model behavior boundary was violated")
    if result.get("ordinary_author_prompts") != 0: findings.append("ordinary_author_prompts is not zero")
    if result.get("workflow") != list(executor_runtime.MAIN_SEQUENCE): findings.append("normal executor sequence was not used")
    return {"operation": "validate-director-orchestration-e2e", "status": "PASS" if not findings else "FAIL", "findings": findings}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--root", type=Path)
    args = parser.parse_args()
    result = run(args.output, root=args.root)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["status"] == "PASS" else 1)
