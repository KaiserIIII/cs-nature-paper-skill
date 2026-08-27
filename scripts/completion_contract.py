#!/usr/bin/env python3
"""Evaluate project readiness independently from software release readiness."""

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
REQUIRED = (
    "policy", "audit", "graph", "graph_rebuild", "argument", "feasibility", "protocol", "claims", "evidence",
    "literature_sufficiency", "experiment_completeness", "figure_traceability", "manuscript_complete",
    "review_resolution", "reproducibility", "artifact_package", "director_orchestration_e2e", "e2e",
)


def _load(name: str):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("v32_completion_" + name, path)
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
    for candidate in (root.resolve(), Path(__file__).resolve().parents[1]):
        try:
            return subprocess.run(["git", "-C", str(candidate), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            continue
    return "UNKNOWN"


def _check(status: str, findings: list[str] | None = None, **extra: Any) -> dict[str, Any]:
    return {"status": status, "findings": findings or []} | extra


def _evidence_check(project: Path) -> dict[str, Any]:
    ledger = _read(_state_dir(project) / "evidence_ledger.json", {})
    anchors = ledger.get("anchors", []) if isinstance(ledger, dict) else []
    if not isinstance(anchors, list) or not anchors:
        return _check("FAIL", ["evidence ledger has no anchors"])
    valid = 0
    findings: list[str] = []
    for item in anchors:
        result = anchor_runtime.validate_anchor(item)
        if result.get("status") == "PASS" and result.get("provenance_level") in {"OBSERVED", "VERIFIED"}:
            valid += 1
        elif result.get("status") != "PASS":
            findings.extend(result.get("findings", []))
    if valid == 0:
        findings.append("no observed or independently verified evidence anchor supports completion")
    return _check("PASS" if not findings else "FAIL", findings, anchor_count=len(anchors), qualifying_anchors=valid)


def _e2e_check(path: Path | None, project: Path) -> dict[str, Any]:
    if path is None or not path.exists():
        return _check("FAIL", ["director orchestration e2e result is missing"])
    value = _read(path)
    if not isinstance(value, dict):
        return _check("FAIL", ["e2e result is not a JSON object"])
    findings: list[str] = []
    if value.get("status") != "PASS":
        findings.append("e2e status is not PASS")
    if value.get("evaluation_class") not in {"HARNESS_SELF_TEST", "DIRECTOR_ORCHESTRATION_E2E"}:
        findings.append("e2e evaluation class is invalid")
    if value.get("model_behavior") != "NOT_RUN":
        findings.append("e2e model_behavior must remain NOT_RUN")
    if value.get("skill_commit") != _commit(project):
        findings.append("e2e result commit is stale")
    completion = value.get("completion")
    if completion is not None and (not isinstance(completion, dict) or completion.get("status") != "PASS"):
        findings.append("e2e completion contract is not PASS")
    return _check("PASS" if not findings else "FAIL", findings, evaluation_class=value.get("evaluation_class"))


def _literature(project: Path) -> dict[str, Any]:
    value = _read(project / "artifacts" / "literature.json", {})
    findings = []
    for field in ("sources", "retrieval_records", "verified_relations", "closest_work", "remaining_gap"):
        if not value.get(field):
            findings.append(f"literature output lacks {field}")
    return _check("PASS" if not findings else "FAIL", findings)


def _experiment(project: Path) -> dict[str, Any]:
    record = _read(project / "artifacts" / "formal_execution.json", {})
    output = project / "artifacts" / "formal_results.json"
    analysis = _read(project / "artifacts" / "analysis.json", {})
    findings = []
    if record.get("status") != "PASS" or record.get("exit_status") != 0:
        findings.append("formal execution record is absent or did not pass")
    if not output.is_file() or not record.get("outputs") or not all(item.get("produced_by_command") for item in record.get("outputs", [])):
        findings.append("formal output is not bound to an actual command")
    if not analysis.get("uncertainty") or not analysis.get("robustness") or not analysis.get("error_analysis"):
        findings.append("analysis lacks uncertainty, robustness, or error analysis")
    return _check("PASS" if not findings else "FAIL", findings)


def _figure(project: Path) -> dict[str, Any]:
    figure = project / "artifacts" / "figure.svg"
    provenance = _read(project / "artifacts" / "figure_provenance.json", {})
    analysis = project / "artifacts" / "analysis.json"
    findings = []
    if not figure.is_file() or figure.stat().st_size == 0:
        findings.append("figure artifact is missing")
    if not analysis.is_file() or provenance.get("source_sha256") != (hashlib.sha256(analysis.read_bytes()).hexdigest() if analysis.is_file() else None):
        findings.append("figure source-data hash is missing or stale")
    if provenance.get("status") != "TRACEABLE":
        findings.append("figure provenance is not TRACEABLE")
    return _check("PASS" if not findings else "FAIL", findings)


def _manuscript(project: Path) -> dict[str, Any]:
    path = project / "artifacts" / "manuscript.md"
    if not path.is_file():
        return _check("FAIL", ["manuscript artifact is missing"])
    text = path.read_text(encoding="utf-8")
    required = ("## Abstract", "## Related Work", "## Method", "## Results", "## Limitations", "## Reproducibility")
    findings = [f"manuscript lacks {heading}" for heading in required if heading not in text]
    if len(text.split()) < 75:
        findings.append("manuscript is not substantively complete")
    return _check("PASS" if not findings else "FAIL", findings, word_count=len(text.split()))


def _review(project: Path) -> dict[str, Any]:
    value = _read(project / "artifacts" / "review_findings.json", {})
    findings = value.get("findings", []) if isinstance(value, dict) else []
    if not isinstance(findings, list):
        return _check("FAIL", ["review finding collection is invalid"])
    unresolved_critical = [item for item in findings if item.get("severity") == "CRITICAL" and item.get("status") != "RESOLVED"]
    unresolved_major = [item for item in findings if item.get("severity") == "MAJOR" and item.get("status") not in {"RESOLVED", "RESIDUAL_RISK_DOCUMENTED"}]
    problems = []
    if value.get("status") != "PASS":
        problems.append("review output is missing or invalid")
    if unresolved_critical:
        problems.append("review has unresolved CRITICAL findings")
    if unresolved_major:
        problems.append("review has unresolved MAJOR findings")
    return _check("PASS" if not problems else "FAIL", problems, unresolved_critical=len(unresolved_critical), unresolved_major=len(unresolved_major))


def _reproducibility(project: Path) -> dict[str, Any]:
    manifest = _read(project / "artifacts" / "package_manifest.json", {})
    findings = []
    if not manifest.get("reproduction_command"):
        findings.append("package has no reproduction command")
    if not manifest.get("artifacts"):
        findings.append("package has no content-addressed artifacts")
    return _check("PASS" if not findings else "FAIL", findings)


def _package(project: Path) -> dict[str, Any]:
    value = _read(project / "artifacts" / "package_manifest.json", {})
    findings = []
    if value.get("status") != "PASS":
        findings.append("artifact package status is not PASS")
    for item in value.get("artifacts", []):
        path = project / str(item.get("path", ""))
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item.get("sha256"):
            findings.append(f"artifact package entry is missing or stale: {item.get('path')}")
    return _check("PASS" if not findings else "FAIL", findings, artifact_count=len(value.get("artifacts", [])))


def _director(project: Path) -> dict[str, Any]:
    value = _read(_state_dir(project) / "director_session.json", {})
    findings = []
    if value.get("status") != "READY_FOR_SUBMISSION":
        findings.append("Director did not reach READY_FOR_SUBMISSION")
    if value.get("ordinary_author_prompts") != 0:
        findings.append("ordinary_author_prompts is not zero")
    if len(value.get("completed", [])) < 20:
        findings.append("Director did not complete the normal executor sequence")
    return _check("PASS" if not findings else "FAIL", findings, completed=len(value.get("completed", [])), ordinary_author_prompts=value.get("ordinary_author_prompts"))


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
    checks["audit"] = autonomy.verify_audit(audit_file) if audit_file.exists() else _check("FAIL", ["autonomy audit log is missing"])
    try:
        checks["graph"] = graph.validate_project(project)
        rebuild = graph.rebuild(project)
        checks["graph_rebuild"] = _check("PASS" if rebuild.get("status") == "PASS" else "FAIL", rebuild.get("findings", []), event_count=rebuild.get("event_count", 0))
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
    checks["literature_sufficiency"] = _literature(project)
    checks["experiment_completeness"] = _experiment(project)
    checks["figure_traceability"] = _figure(project)
    checks["manuscript_complete"] = _manuscript(project)
    checks["review_resolution"] = _review(project)
    checks["reproducibility"] = _reproducibility(project)
    checks["artifact_package"] = _package(project)
    checks["director_orchestration_e2e"] = _director(project)
    checks["e2e"] = _e2e_check(e2e_result, project)
    critical_failures = [f"{name}: {finding}" for name, value in checks.items() if value.get("status") != "PASS" for finding in value.get("findings", [])]
    status = "PASS" if not critical_failures else "FAIL"
    disposition = "READY_FOR_SUBMISSION" if status == "PASS" else "BLOCKED"
    project_doc = _read(state / "project.json", {})
    return {
        "operation": "completion-contract",
        "skill_version": SKILL_VERSION,
        "status": status,
        "checks": checks,
        "critical_failures": critical_failures,
        "project_disposition": disposition,
        "release_disposition": disposition,
        "residual_risks": (_read(state / "risks.json", {}) or {}).get("risks", []),
        "author_actions": project_doc.get("author_actions", []) if isinstance(project_doc, dict) else [],
        "model_behavior": "NOT_RUN",
    }


def write(project: Path, value: dict[str, Any]) -> Path:
    path = _state_dir(project) / "completion_contract.json"
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--e2e", type=Path)
    parser.add_argument("--audit", type=Path)
    args = parser.parse_args()
    result = evaluate(args.project, e2e_result=args.e2e, audit_path=args.audit)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["status"] == "PASS" else 1)
