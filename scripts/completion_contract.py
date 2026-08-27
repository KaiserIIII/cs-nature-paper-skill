#!/usr/bin/env python3
"""Evaluate the v3.2 fail-closed completion contract."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SKILL_VERSION = "3.2.0"
REQUIRED = ("policy", "audit", "graph", "graph_rebuild", "argument", "feasibility", "protocol", "claims", "evidence", "e2e")


def _load(name: str):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("v32_" + name, path)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    spec.loader.exec_module(module)
    return module


autonomy = _load("autonomy")
graph = _load("research_graph")
state_runtime = _load("research_state")
anchor_runtime = _load("evidence_anchor")


def required_checks() -> tuple[str, ...]:
    return REQUIRED


def _state_dir(project: Path) -> Path:
    project = project.resolve()
    for name in (".research-state-v31", ".research-state-v3", ".research-state"):
        candidate = project / name
        if candidate.exists():
            return candidate
    return project / ".research-state"


def _read(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _commit(root: Path) -> str:
    candidates = [root.resolve()]
    repository_root = Path(__file__).resolve().parents[1]
    if repository_root not in candidates:
        candidates.append(repository_root)
    for candidate in candidates:
        try:
            return subprocess.run(["git", "-C", str(candidate), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            continue
    return "UNKNOWN"


def _check(status: str, findings: list[str] | None = None, **extra: Any) -> dict[str, Any]:
    value = {"status": status, "findings": findings or []}
    value.update(extra)
    return value


def _evidence_check(project: Path) -> dict[str, Any]:
    ledger_path = _state_dir(project) / "evidence_ledger.json"
    ledger = _read(ledger_path, {})
    anchors = ledger.get("anchors", []) if isinstance(ledger, dict) else []
    if not isinstance(anchors, list) or not anchors:
        return _check("FAIL", ["evidence ledger has no anchors"])
    valid = 0
    findings: list[str] = []
    for item in anchors:
        if not isinstance(item, dict):
            findings.append("evidence anchor is not an object")
            continue
        result = anchor_runtime.validate_anchor(item)
        if result.get("status") == "PASS" and result.get("provenance_level") in {"OBSERVED", "VERIFIED"}:
            valid += 1
    if valid == 0:
        findings.append("no observed or independently verified evidence anchor supports completion")
    return _check("PASS" if not findings else "FAIL", findings, anchor_count=len(anchors), qualifying_anchors=valid)


def _e2e_check(path: Path | None, project: Path) -> dict[str, Any]:
    if path is None or not path.exists():
        return _check("FAIL", ["e2e result is missing"])
    value = _read(path)
    if not isinstance(value, dict):
        return _check("FAIL", ["e2e result is not a JSON object"])
    findings: list[str] = []
    if value.get("status") != "PASS": findings.append("e2e status is not PASS")
    if value.get("evaluation_class") != "HARNESS_SELF_TEST": findings.append("e2e must be labeled HARNESS_SELF_TEST")
    if value.get("model_behavior") != "NOT_RUN": findings.append("e2e model_behavior must remain NOT_RUN")
    if value.get("skill_commit") != _commit(project): findings.append("e2e result commit is stale")
    completion = value.get("completion")
    if not isinstance(completion, dict) or completion.get("status") != "PASS": findings.append("e2e completion contract is not PASS")
    return _check("PASS" if not findings else "FAIL", findings, evaluation_class=value.get("evaluation_class"))


def evaluate(project: Path, *, e2e_result: Path | None = None, audit_path: Path | None = None) -> dict[str, Any]:
    project = project.resolve()
    state = _state_dir(project)
    checks: dict[str, dict[str, Any]] = {}
    policy_path = state / "autonomy_policy.json"
    if not policy_path.exists():
        checks["policy"] = _check("FAIL", ["autonomy_policy.json is missing"])
    else:
        try:
            value = autonomy.load_policy(policy_path)
            checks["policy"] = _check("PASS", [], policy_hash="sha256:" + hashlib.sha256(policy_path.read_bytes()).hexdigest(), mode=value.get("mode"))
        except Exception as exc:
            checks["policy"] = _check("FAIL", [str(exc)])
    audit_file = audit_path or state / ".autonomy-audit.jsonl"
    if not audit_file.exists():
        checks["audit"] = _check("FAIL", ["autonomy audit log is missing"])
    else:
        checks["audit"] = autonomy.verify_audit(audit_file)
    try:
        checks["graph"] = graph.validate_project(project)
        checks["graph_rebuild"] = _check("PASS" if checks["graph"].get("status") == "PASS" else "FAIL", list(checks["graph"].get("findings", [])), event_count=checks["graph"].get("event_count", 0))
    except Exception as exc:
        checks["graph"] = _check("FAIL", [str(exc)])
        checks["graph_rebuild"] = _check("FAIL", ["graph could not be validated or rebuilt"])
    for gate in ("argument", "feasibility", "protocol", "claims"):
        try:
            result = state_runtime.audit_state(project, gate)
            checks[gate] = _check(result.get("status", "FAIL"), result.get("findings", []), state_dir=result.get("state_dir"))
        except Exception as exc:
            checks[gate] = _check("FAIL", [str(exc)])
    checks["evidence"] = _evidence_check(project)
    checks["e2e"] = _e2e_check(e2e_result, project)
    critical_failures = [f"{name}: {finding}" for name, value in checks.items() if value.get("status") != "PASS" for finding in value.get("findings", [])]
    if not critical_failures:
        status = "PASS"
        disposition = "V3.2.0 RELEASE CANDIDATE READY"
    else:
        status = "FAIL"
        disposition = "V3.2.0 BLOCKED"
    project_doc = _read(state / "project.json", {})
    return {
        "operation": "completion-contract",
        "skill_version": SKILL_VERSION,
        "status": status,
        "checks": checks,
        "critical_failures": critical_failures,
        "release_disposition": disposition,
        "residual_risks": (_read(state / "risks.json", {}) or {}).get("risks", []),
        "author_actions": project_doc.get("author_actions", []) if isinstance(project_doc, dict) else [],
        "model_behavior": "NOT_RUN",
    }


def write(project: Path, value: dict[str, Any]) -> Path:
    path = _state_dir(project) / "completion_contract.json"
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--e2e", type=Path)
    parser.add_argument("--audit", type=Path)
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    result = evaluate(args.project, e2e_result=args.e2e, audit_path=args.audit)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["status"] == "PASS" else 1)
