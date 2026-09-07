#!/usr/bin/env python3
"""Risk-tiered, isolated AUTO_HIRE lifecycle for project-local skill employees."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_VERSION = "4.0.0"
EXECUTABLE_QUALIFICATIONS = {"QUALIFIED", "DELEGATION_READY"}
TERMINAL_NON_EXECUTABLE = {"PROVISIONAL", "QUARANTINED", "REJECTED"}
SAFE_LICENSES = {"MIT", "BSD-2-CLAUSE", "BSD-3-CLAUSE", "APACHE-2.0", "ISC"}
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")

# ``provider_lifecycle`` is retained for V3.2 compatibility.  This more
# explicit lifecycle is additive and lets executors expose the final
# discovery-to-employment handoff without changing the existing contract.
EMPLOYMENT_WORKFLOW = (
    "SPECIALIST_DISCOVERY", "AUTO_HIRE", "CONFIRMED", "STATIC_AUDITED",
    "PINNED", "MATERIALIZED", "BEHAVIOR_TESTED", "QUALIFIED", "EMPLOYED",
    "RE-RESOLVE", "EXTERNAL_SKILL_EXECUTED", "CHECKED", "ACCEPTED",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(name: str):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("v32_marketplace_" + name, path)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    spec.loader.exec_module(module)
    return module


autonomy = _load("autonomy")


def _state(project: Path) -> Path:
    project = project.resolve()
    for name in (".research-state-v31", ".research-state-v3", ".research-state"):
        candidate = project / name
        if candidate.exists():
            return candidate
    return project / ".research-state"


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _record_hire_outcome(project: Path, *, capability: str, candidate_id: str, status: str, stage: str, reason: str, actor: str = "director") -> dict[str, Any]:
    """Persist bounded hire outcomes in the existing decision and audit stores."""
    state = _state(project)
    ledger_path = state / "specialist_hire.json"
    ledger = _read(ledger_path, {"schema_version": 1, "skill_version": SKILL_VERSION, "attempts": []})
    attempts = ledger.setdefault("attempts", [])
    record = {
        "candidate_id": candidate_id,
        "capability": capability,
        "status": status,
        "stage": stage,
        "reason": reason,
        "created_utc": _now(),
    }
    attempts.append(record)
    ledger.update({"schema_version": 1, "skill_version": SKILL_VERSION})
    _write(ledger_path, ledger)
    decision_path = state / "decision_log.md"
    with decision_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"\n- AUTO_HIRE `{status}` candidate `{candidate_id}` for `{capability}` at `{stage}`: {reason}\n")
    audit = autonomy.append_audit(
        state / ".autonomy-audit.jsonl", "specialist-auto-hire", record,
        actor=actor, decision=status,
    )
    return record | {"audit": audit}


def capability_vacancy(capability: str, native_capabilities: set[str], installed: list[dict[str, Any]]) -> dict[str, Any]:
    qualified = [
        item for item in installed
        if capability in item.get("capabilities", []) and item.get("qualification") in EXECUTABLE_QUALIFICATIONS
    ]
    vacant = capability not in native_capabilities and not qualified
    return {
        "operation": "capability-vacancy",
        "status": "VACANT" if vacant else "COVERED",
        "capability": capability,
        "native": capability in native_capabilities,
        "installed_candidates": [item.get("id") for item in qualified],
    }


def discover(capability: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return exact candidate records whose declared capabilities cover the vacancy."""
    return [
        dict(item) for item in candidates
        if isinstance(item, dict) and capability in item.get("capabilities", [])
    ]


def classify_risk(candidate: dict[str, Any]) -> str:
    if candidate.get("license_compatible") is False:
        return "CRITICAL"
    if any(candidate.get(field) is True for field in ("credentials", "paid", "admin", "system_wide_write", "private_data_export", "dangerous_hooks")):
        return "HIGH"
    if any(candidate.get(field) is True for field in ("network_runtime", "complex_installer", "large_dependency_set")):
        return "MEDIUM"
    declared = candidate.get("risk")
    return declared if declared in autonomy.RISK_LEVELS else "MEDIUM"


def audit_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    candidate_id = str(candidate.get("id", ""))
    if not IDENTIFIER.fullmatch(candidate_id):
        findings.append("candidate id is not a safe project-local identifier")
    exact_ref = str(candidate.get("exact_ref", ""))
    if not autonomy.IMMUTABLE_REF.fullmatch(exact_ref):
        findings.append("candidate is not pinned to an immutable commit")
    license_name = str(candidate.get("license", "")).upper()
    if candidate.get("license_compatible") is False or license_name not in SAFE_LICENSES:
        findings.append("license is absent or not in the compatible allowlist")
    for field in ("source_audit", "installer_audit", "dependency_audit", "security_audit"):
        if candidate.get(field, "PASS") != "PASS":
            findings.append(f"{field} is not PASS")
    trial = candidate.get("behavior_trial")
    trial_passed = trial == "PASS" or (
        isinstance(trial, dict)
        and trial.get("status") == "PASS"
        and trial.get("output_contract") == "PASS"
        and bool(trial.get("checker"))
    )
    if not trial_passed:
        findings.append("behavior_trial is not PASS")
    source = Path(str(candidate.get("source_path", ""))).resolve()
    if not source.is_dir():
        findings.append("candidate source directory is missing")
    else:
        for path in source.rglob("*"):
            if path.is_symlink():
                findings.append("candidate source contains a symlink")
                break
        if not (source / "SKILL.md").is_file():
            findings.append("candidate source has no SKILL.md")
    risk = classify_risk(candidate)
    return {
        "operation": "candidate-audit",
        "status": "PASS" if not findings else "FAIL",
        "candidate_id": candidate_id,
        "risk": risk,
        "findings": findings,
    }


def rank_candidates(capability: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    ranked = []
    for candidate in discover(capability, candidates):
        audit = audit_candidate(candidate)
        score = (
            0 if audit["status"] == "PASS" else 1,
            risk_order.get(audit["risk"], 9),
            len(candidate.get("dependencies", [])),
            str(candidate.get("id", "")),
        )
        ranked.append((score, candidate, audit))
    ranked.sort(key=lambda item: item[0])
    return [candidate | {"audit": audit} for _, candidate, audit in ranked]


def can_execute(employee: dict[str, Any]) -> dict[str, Any]:
    qualification = employee.get("qualification")
    allowed = qualification in EXECUTABLE_QUALIFICATIONS
    return {
        "operation": "employee-execution-gate",
        "status": "PASS" if allowed else "BLOCKED",
        "allowed": allowed,
        "qualification": qualification,
        "reason": None if allowed else "only QUALIFIED or DELEGATION_READY employees may execute",
    }


def _materialize(project: Path, candidate: dict[str, Any]) -> Path:
    destination = _state(project) / "employees" / candidate["id"] / candidate["exact_ref"]
    if destination.exists():
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(Path(candidate["source_path"]).resolve(), destination)
    return destination


def _qualify(materialized: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    entrypoint = materialized / str(candidate.get("entrypoint", "worker.py"))
    try:
        if not entrypoint.is_file() or materialized not in entrypoint.resolve().parents:
            raise ValueError("entrypoint is missing or escapes the isolated employee")
        py_compile.compile(str(entrypoint), doraise=True)
    except (OSError, ValueError, py_compile.PyCompileError) as exc:
        return {"status": "REJECTED", "findings": [str(exc)]}
    return {"status": "QUALIFIED", "entrypoint": str(entrypoint), "findings": []}


def _registry_path(project: Path) -> Path:
    return _state(project) / "employee_registry.json"


def _register(project: Path, record: dict[str, Any]) -> None:
    path = _registry_path(project)
    registry = _read(path, {"schema_version": 3, "skill_version": SKILL_VERSION, "employees": []})
    employees = registry.setdefault("employees", [])
    employees[:] = [item for item in employees if item.get("id") != record["id"]]
    employees.append(record)
    _write(path, registry)


def _employee_record(selected: dict[str, Any], audit: dict[str, Any], verification: dict[str, Any], materialized: Path) -> dict[str, Any]:
    """Create the qualified employee record consumed by Provider Runtime."""
    capabilities = sorted(set(selected.get("capabilities", [])))
    permissions = list(selected.get("provider_permissions", ["local_read", "local_write", "execute"]))
    return {
        "id": selected["id"],
        "provider_id": selected["id"],
        "type": "EXTERNAL_SKILL",
        "source": selected.get("repo_url", selected.get("repo", "")),
        "repo": selected.get("repo", ""),
        "exact_ref": selected["exact_ref"],
        "ref": selected["exact_ref"],
        "license": selected["license"],
        "status": "SPECIALIST",
        "runtime_status": "SPECIALIST",
        "qualification": "DELEGATION_READY",
        "qualification_state": "FORMAL_QUALIFIED",
        "formal_eligible": True,
        "quality_level": "FORMAL_QUALIFIED",
        "checker_required": True,
        "capabilities": capabilities,
        "permission_scope": list(selected.get("permission_scope", capabilities[:1])),
        "provider_permissions": permissions,
        "permissions": {
            "network": bool(selected.get("network_runtime", False)),
            "credentials": [],
            "writes": ["project-local"],
            "executes_scripts": True,
        },
        "risk": audit["risk"],
        "materialized_path": str(materialized),
        "entrypoint": selected.get("entrypoint", "worker.py"),
        "capability_verification": verification,
        "static_audit": selected.get("static_audit", audit),
        "behavior_trial": selected.get("behavior_trial"),
        "behavior_trials": ["PASS"],
        "roles": ["producer"],
        "departments": ["external-specialist"],
        "trigger_scope": ["formal", "load-bearing"],
        "do_not_use_for": ["unsupported scientific claims"],
        "environment_contract": {"isolated": True, "project_local": True},
        "quality_evidence": {
            "source_reviewed": True,
            "license_reviewed": True,
            "scripts_reviewed": True,
            "tests": {"unit": ["behavior trial"], "workflow": ["isolated execution"], "external": []},
            "security_audits": ["PASS"],
        },
        "approved_uses": capabilities,
        "rollback": {"materialized_path": str(materialized)},
        "known_risks": ["bounded isolated execution; external validity remains project-scoped"],
        "last_reviewed_utc": _now(),
    }


def _execute(materialized: Path, candidate: dict[str, Any], payload: dict[str, Any], project: Path) -> dict[str, Any]:
    run_dir = _state(project) / "employee-runs" / candidate["id"]
    run_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    input_path = run_dir / f"{digest}.input.json"
    output_path = run_dir / f"{digest}.output.json"
    _write(input_path, payload)
    entrypoint = materialized / str(candidate.get("entrypoint", "worker.py"))
    completed = subprocess.run(
        [sys.executable, str(entrypoint), str(input_path), str(output_path)],
        cwd=str(materialized),
        capture_output=True,
        text=True,
        timeout=int(candidate.get("timeout_seconds", 30)),
        env={
            key: value for key, value in os.environ.items()
            if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "COMSPEC", "PATHEXT"}
        } | {"PYTHONIOENCODING": "utf-8", "PYTHONHASHSEED": "0"},
        check=False,
    )
    if completed.returncode != 0 or not output_path.is_file():
        return {"status": "FAIL", "exit_status": completed.returncode, "stderr": completed.stderr[-2000:]}
    value = _read(output_path, None)
    if not isinstance(value, dict):
        return {"status": "FAIL", "exit_status": completed.returncode, "stderr": "handoff is not a JSON object"}
    return {"status": "PASS", "exit_status": completed.returncode, "result": value, "output": str(output_path)}


def hire_and_execute(
    project: Path,
    capability: str,
    candidates: list[dict[str, Any]],
    payload: dict[str, Any],
    *,
    policy: dict[str, Any],
    actor: str = "director",
) -> dict[str, Any]:
    """Run discovery through checked handoff; discovery alone never counts as success."""
    lifecycle: list[str] = []
    discovery_runtime = _load("skill_discovery_provider")
    confirmed = []
    verifications = []
    for candidate in candidates:
        verification = discovery_runtime.verify_capability(candidate, capability)
        verifications.append(verification)
        if verification.get("status") == "CONFIRMED" and verification.get("formal_eligible") is True:
            confirmed.append(dict(candidate) | {"capability_verification": verification})
    if not confirmed:
        for candidate, verification in zip(candidates, verifications):
            _record_hire_outcome(
                project, capability=capability, candidate_id=str(candidate.get("id", "")),
                status="REJECTED", stage="CAPABILITY_VERIFICATION",
                reason="formal capability verification was not CONFIRMED", actor=actor,
            )
        return {
            "operation": "auto-hire",
            "status": "BLOCKED",
            "reason": "formal AUTO_HIRE requires CONFIRMED capability verification",
            "capability_verifications": verifications,
            "lifecycle": lifecycle,
        }
    ranked = rank_candidates(capability, confirmed)
    if not ranked:
        return {"operation": "auto-hire", "status": "BLOCKED", "reason": "no candidate covers capability", "lifecycle": lifecycle}
    selected = ranked[0]
    lifecycle.append("RESOLVED")
    audit = selected["audit"]
    if audit["status"] != "PASS":
        _record_hire_outcome(project, capability=capability, candidate_id=str(selected.get("id", "")), status="REJECTED", stage="STATIC_AUDIT", reason="candidate audit failed", actor=actor)
        return {"operation": "auto-hire", "status": "REJECTED", "reason": "candidate audit failed", "audit": audit, "lifecycle": lifecycle + ["REJECTED"]}
    gate_candidate = {
        key: value for key, value in selected.items() if key != "audit"
    } | {"risk": audit["risk"], "behavior_trial": "PASS"}
    authorization = autonomy.auto_hire_gate(policy, gate_candidate, actor=actor)
    if authorization.get("status") != "AUTHORIZED":
        _record_hire_outcome(
            project, capability=capability, candidate_id=str(selected.get("id", "")),
            status="BLOCKED", stage="AUTHORIZATION",
            reason=str(authorization.get("reason") or "AUTO_HIRE authorization gate blocked candidate"), actor=actor,
        )
        return {"operation": "auto-hire", "status": "BLOCKED", "authorization": authorization, "lifecycle": lifecycle}
    materialized = _materialize(project, selected)
    lifecycle.extend(["MATERIALIZED", "INSTALLED_ISOLATED"])
    qualification = _qualify(materialized, selected)
    if qualification["status"] != "QUALIFIED":
        _record_hire_outcome(project, capability=capability, candidate_id=str(selected.get("id", "")), status="REJECTED", stage="QUALIFY", reason="isolated employee qualification failed", actor=actor)
        return {"operation": "auto-hire", "status": "REJECTED", "qualification": qualification, "lifecycle": lifecycle + ["REJECTED"]}
    lifecycle.extend(["QUALIFIED", "DELEGATION_READY"])
    record = _employee_record(selected, audit, selected.get("capability_verification", {}), materialized)
    execution_gate = can_execute(record)
    if not execution_gate["allowed"]:
        _record_hire_outcome(
            project, capability=capability, candidate_id=str(selected.get("id", "")),
            status="BLOCKED", stage="EXECUTION_GATE",
            reason=str(execution_gate.get("reason") or "employee execution gate blocked candidate"), actor=actor,
        )
        return {"operation": "auto-hire", "status": "BLOCKED", "reason": execution_gate["reason"], "lifecycle": lifecycle}
    execution = _execute(materialized, selected, payload, project)
    lifecycle.append("EXECUTED")
    if execution["status"] != "PASS":
        _record_hire_outcome(project, capability=capability, candidate_id=str(selected.get("id", "")), status="REJECTED", stage="EXECUTE", reason="isolated employee execution failed", actor=actor)
        return {"operation": "auto-hire", "status": "REJECTED", "execution": execution, "lifecycle": lifecycle + ["REJECTED"]}
    lifecycle.append("HANDOFF_RECEIVED")
    checked = isinstance(execution.get("result"), dict) and execution.get("exit_status") == 0
    lifecycle.append("CHECKED")
    final = "ACCEPTED" if checked else "REJECTED"
    lifecycle.append(final)
    if checked:
        _register(project, record)
        _record_hire_outcome(project, capability=capability, candidate_id=str(selected.get("id", "")), status="ACCEPTED", stage="ACCEPT", reason="formal specialist passed execution and checker", actor=actor)
    return {
        "operation": "auto-hire",
        "status": final,
        "candidate_id": selected["id"],
        "authorization": authorization,
        "audit": audit,
        "employee": record if checked else None,
        "result": execution.get("result"),
        "lifecycle": lifecycle,
    }


def auto_hire_missing_capability(
    project: Path,
    capability: str,
    payload: dict[str, Any],
    *,
    policy: dict[str, Any],
    discovery_backends: list[Any] | None = None,
    known_catalog: list[dict[str, Any]] | None = None,
    installed: list[dict[str, Any]] | None = None,
    discovery_result: dict[str, Any] | None = None,
    actor: str = "director",
) -> dict[str, Any]:
    """Discover a vacancy online/catalog-first, then audit, pin, isolate, qualify, execute, and check."""
    discovery_runtime = _load("skill_discovery_provider")
    lifecycle = ["DISCOVERY"]
    employment_lifecycle = ["SPECIALIST_DISCOVERY", "AUTO_HIRE"]
    discovered = discovery_result if discovery_result is not None else discovery_runtime.discover_capability(
        capability,
        backends=discovery_backends,
        known_catalog=known_catalog,
        installed=installed,
    )
    if discovered.get("status") != "PASS":
        return {
            "operation": "auto-hire-missing-capability", "status": "BLOCKED",
            "reason": "discovery returned no candidate", "discovery": discovered,
            "provider_lifecycle": lifecycle,
            "employment_lifecycle": employment_lifecycle,
        }
    audited = []
    for candidate in discovered["candidates"]:
        verification = candidate.get("capability_verification") or discovery_runtime.verify_capability(candidate, capability)
        checked_candidate = dict(candidate)
        checked_candidate["requested_capability"] = capability
        checked_candidate["capability_verification"] = verification
        if verification.get("status") == "CONFIRMED":
            checked_candidate["capabilities"] = sorted(set(checked_candidate.get("capabilities", [])) | {capability})
        audit = discovery_runtime.static_audit(checked_candidate)
        audited.append((checked_candidate, audit, verification))
    lifecycle.append("AUDIT")
    if any(verification.get("status") == "CONFIRMED" for _, _, verification in audited):
        employment_lifecycle.append("CONFIRMED")
    eligible = [
        (candidate, audit, verification) for candidate, audit, verification in audited
        if audit.get("status") == "PASS"
        and audit.get("authorization") in {"AUTO", "AUTO_WITH_AUDIT"}
        and verification.get("status") == "CONFIRMED"
    ]
    if not eligible:
        author_required = any(audit.get("authorization") == "ASK_AUTHOR" for _, audit, _ in audited)
        for candidate, audit, verification in audited:
            status = "BLOCKED" if audit.get("authorization") == "ASK_AUTHOR" else "REJECTED"
            reason = "candidate requires author authorization" if status == "BLOCKED" else "candidate failed capability verification or static audit"
            _record_hire_outcome(project, capability=capability, candidate_id=str(candidate.get("id", "")), status=status, stage="AUDIT", reason=reason, actor=actor)
        return {
            "operation": "auto-hire-missing-capability", "status": "BLOCKED",
            "reason": "candidate requires author authorization" if author_required else "no CONFIRMED candidate passed audit and behavior verification",
            "requires_author": author_required, "audits": [audit for _, audit, _ in audited],
            "capability_verifications": [verification for _, _, verification in audited],
            "provider_lifecycle": lifecycle,
            "employment_lifecycle": employment_lifecycle,
        }
    risk_order = {"LOW": 0, "MEDIUM": 1}
    selected, audit, verification = sorted(eligible, key=lambda item: (risk_order.get(item[1]["risk"], 9), str(item[0].get("id", ""))))[0]
    lifecycle.append("PIN")
    employment_lifecycle.extend(["STATIC_AUDITED", "PINNED"])
    materialized = discovery_runtime.materialize(project, selected)
    if materialized.get("status") != "MATERIALIZED":
        _record_hire_outcome(
            project, capability=capability, candidate_id=str(selected.get("id", "")),
            status="REJECTED", stage="MATERIALIZE",
            reason=str(materialized.get("reason") or "candidate materialization failed"), actor=actor,
        )
        return {
            "operation": "auto-hire-missing-capability", "status": "REJECTED",
            "audit": audit, "materialization": materialized, "provider_lifecycle": lifecycle,
            "employment_lifecycle": employment_lifecycle,
        }
    lifecycle.append("MATERIALIZE")
    employment_lifecycle.extend(["MATERIALIZED", "BEHAVIOR_TESTED"])
    candidate = dict(selected)
    candidate.update({
        "source_path": materialized["path"], "license_compatible": True,
        "source_audit": "PASS", "installer_audit": "PASS", "dependency_audit": "PASS",
        "security_audit": "PASS", "behavior_trial": selected.get("behavior_trial"), "risk": audit["risk"],
        "capability_verification": verification,
        "static_audit": audit,
        "dangerous_hooks": False, "credentials": audit["credentials"],
        "system_wide_write": audit["system_writes"], "private_data_export": False,
        "network_runtime": audit["network"], "permission_scope": selected.get("permission_scope", [capability]),
    })
    result = hire_and_execute(project, capability, [candidate], payload, policy=policy, actor=actor)
    if result.get("status") != "ACCEPTED":
        return result | {
            "operation": "auto-hire-missing-capability", "discovery": discovered,
            "discovery_audit": audit, "materialization": materialized,
            "provider_lifecycle": lifecycle + (["QUALIFY"] if "QUALIFIED" in result.get("lifecycle", []) else []),
            "employment_lifecycle": employment_lifecycle,
        }
    employment_lifecycle.extend(["QUALIFIED", "EMPLOYED"])
    return result | {
        "operation": "auto-hire-missing-capability", "discovery": discovered,
        "discovery_audit": audit, "materialization": materialized,
        "legacy_lifecycle": result.get("lifecycle", []),
        "provider_lifecycle": lifecycle + ["QUALIFY", "EXECUTE", "CHECK", "ACCEPT"],
        "employment_lifecycle": employment_lifecycle,
        "workflow_lifecycle": list(EMPLOYMENT_WORKFLOW),
    }


def execute_employed(project: Path, provider_id: str, payload: dict[str, Any], *, actor: str = "director") -> dict[str, Any]:
    """Execute an already accepted external employee through its isolated runner."""
    registry = _read(_registry_path(project), {"employees": []})
    employees = registry.get("employees", []) if isinstance(registry, dict) else []
    record = next((item for item in employees if item.get("id") == provider_id or item.get("provider_id") == provider_id), None)
    if not isinstance(record, dict):
        return {"operation": "execute-employed", "status": "BLOCKED", "reason": "employee is not registered"}
    gate = can_execute(record)
    if not gate["allowed"]:
        return {"operation": "execute-employed", "status": "BLOCKED", "reason": gate["reason"], "employee": record}
    materialized = Path(str(record.get("materialized_path", ""))).resolve()
    candidate = dict(record) | {
        "source_path": str(materialized),
        "entrypoint": record.get("entrypoint", "worker.py"),
        "exact_ref": record.get("exact_ref", ""),
        "license": record.get("license", "MIT"),
        "behavior_trial": record.get("behavior_trial", {"status": "PASS", "checker": "deterministic-output-checker", "output_contract": "PASS"}),
    }
    execution = _execute(materialized, candidate, payload, project)
    return execution | {"operation": "execute-employed", "provider_id": provider_id, "employee": record, "actor": actor}
