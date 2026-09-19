#!/usr/bin/env python3
"""Provider adapter for arbitrary competition problem structures."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ROOT / "providers"
for folder in (str(Path(__file__).resolve().parent), str(PROVIDERS)):
    if folder not in sys.path:
        sys.path.insert(0, folder)

import provider_runtime  # noqa: E402
import provider_support as support  # noqa: E402
import host_provider_runtime  # noqa: E402
import skill_discovery_provider  # noqa: E402
import skill_marketplace_runtime as marketplace_runtime  # noqa: E402
import competition_modeling_provider  # noqa: E402
import competition_coding_provider  # noqa: E402
import competition_analysis_provider  # noqa: E402
import competition_writing_provider  # noqa: E402
import competition_host_provider  # noqa: E402


SKILL_VERSION = "4.0.0"
NODE_PROVIDER = {
    "contest_intake": ("competition-modeling-provider", "competition-intake"),
    "problem_decomposition": ("competition-modeling-provider", "question-decomposition"),
    "problem_selection": ("competition-modeling-provider", "problem-selection"),
    "assumptions": ("competition-modeling-provider", "mathematical-modeling"),
    "method_candidates": ("competition-modeling-provider", "mathematical-modeling"),
    "minimal_viable_model": ("native-competition-baseline", "code-generation"),
    "pilot_solve": ("deterministic-competition-execution", "execution"),
    "model_validation": ("competition-analysis-provider", "model-validation"),
    "formal_solve": ("deterministic-competition-execution", "experiment-execution"),
    "sensitivity_robustness": ("competition-analysis-provider", "sensitivity-analysis"),
    "model_improvement": ("competition-analysis-provider", "model-validation"),
    "visualization": ("competition-analysis-provider", "scientific-visualization"),
    "paper_draft": ("competition-writing-provider", "evidence-bound-writing"),
    "competition_review": ("competition-writing-provider", "adversarial-review"),
    "revision": ("competition-writing-provider", "evidence-bound-revision"),
    "submission_preflight": ("competition-writing-provider", "artifact-validation"),
}
FORMAL_NODES = {"minimal_viable_model", "pilot_solve", "model_validation", "formal_solve", "sensitivity_robustness", "visualization", "paper_draft", "competition_review", "revision", "submission_preflight"}
SPECIALIST_NODES = {
    "model_validation", "sensitivity_robustness", "visualization", "paper_draft",
    "competition_review", "revision",
}


def _input(project: Path) -> dict[str, Any]:
    state = support.state_dir(project) / "competition_input.json"
    return support.read_json(state if state.is_file() else project / "competition_input.json", {})


def _specialist_required(project: Path, node_id: str) -> bool:
    """Require specialist execution only when the contest contract says so."""
    source = _input(project)
    declared = source.get("specialist_nodes", []) if isinstance(source, dict) else []
    if declared is True:
        return node_id in SPECIALIST_NODES
    return isinstance(declared, list) and node_id in declared


def _fixture_mode(project: Path) -> bool:
    return _input(project).get("provider_mode") == "fixture"


def _discovery_key(node: str, capability: str) -> str:
    return f"{node}:{capability}"


def _specialist_discovery(project: Path, node: str, capability: str) -> dict[str, Any]:
    """Perform and persist one specialist discovery attempt for a node."""
    path = support.state_dir(project) / "specialist_discovery.json"
    ledger = support.read_json(path, {})
    attempts = ledger.setdefault("attempts", {})
    key = _discovery_key(node, capability)
    existing = attempts.get(key)
    if isinstance(existing, dict) and existing.get("attempted") is True:
        return dict(existing.get("result") or {}) | {
            "attempted": False,
            "attempt_count": existing.get("attempt_count", 1),
        }

    registry = support.read_json(support.state_dir(project) / "employee_registry.json", {})
    installed = registry.get("employees", []) if isinstance(registry, dict) else []
    policy = support.read_json(support.state_dir(project) / "autonomy_policy.json", {})
    permissions = policy.get("permissions", {}) if isinstance(policy, dict) else {}
    try:
        # Discovery is metadata-only, but it is a real catalog/backend call
        # when network permission is available.  The current host remains the
        # fallback after this one required attempt; AUTO_HIRE still owns audit,
        # materialization, qualification, execution, and checking.
        kwargs = {"installed": installed if isinstance(installed, list) else []}
        if not bool(permissions.get("network", False)):
            kwargs["backends"] = []
        result = skill_discovery_provider.discover_capability(capability, **kwargs)
    except Exception as exc:  # discovery failure is recorded, never hidden
        result = {
            "operation": "skill-discovery",
            "status": "UNAVAILABLE",
            "capability": capability,
            "candidates": [],
            "error": f"{type(exc).__name__}: {exc}",
        }
    if not isinstance(result, dict):
        result = {
            "operation": "skill-discovery",
            "status": "UNAVAILABLE",
            "capability": capability,
            "candidates": [],
            "error": "discovery provider returned a non-object result",
        }
    attempt_count = int(existing.get("attempt_count", 0)) + 1 if isinstance(existing, dict) else 1
    attempts[key] = {
        "attempted": True,
        "attempt_count": attempt_count,
        "result": result,
        "created_utc": support.utc_now(),
    }
    ledger.update({"schema_version": 1, "skill_version": SKILL_VERSION})
    support.write(path, ledger)
    return dict(result) | {"attempted": True, "attempt_count": attempt_count}


def _discovery_attempted(project: Path, node: str, capability: str) -> bool:
    value = support.read_json(support.state_dir(project) / "specialist_discovery.json", {})
    attempts = value.get("attempts", {}) if isinstance(value, dict) else {}
    record = attempts.get(_discovery_key(node, capability)) if isinstance(attempts, dict) else None
    return isinstance(record, dict) and record.get("attempted") is True


def _recorded_host_context(project: Path) -> bool:
    """Recognize the checked recorded handoffs used by lifecycle E2E fixtures.

    A live host handoff keeps specialist routing strict.  Recorded handoffs
    already have an independent checker record and may be followed by local
    deterministic post-processing for the fixture's bounded outputs.
    """
    for node in ("method_candidates", "minimal_viable_model"):
        active = host_provider_runtime.active_for_node(project, node)
        handoff = active.get("handoff") if isinstance(active, dict) else None
        if active and active.get("status") == "ACCEPTED" and isinstance(handoff, dict):
            if str(handoff.get("provider_id", "")).startswith("recorded-"):
                return True
    return False


def _fixture():
    path = PROVIDERS / "competition_fixture_provider.py"
    spec = importlib.util.spec_from_file_location("v32_competition_fixture_provider", path)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    spec.loader.exec_module(module)
    return module


def _providers(project: Path) -> list[dict[str, Any]]:
    native_status = "QUALIFIED" if competition_coding_provider.native_available(project) else "UNAVAILABLE"
    records = [
        provider_runtime.provider("competition-modeling-provider", "NATIVE", ["competition-intake", "question-decomposition", "problem-selection", "mathematical-modeling"], qualification="QUALIFIED", formal_eligible=True, permissions=["local_read", "local_write"]),
        provider_runtime.provider("native-competition-baseline", "NATIVE", ["code-generation"], status=native_status, qualification="QUALIFIED", formal_eligible=True, permissions=["local_read", "local_write", "execute"]),
        provider_runtime.provider("deterministic-competition-execution", "NATIVE", ["execution", "experiment-execution"], qualification="QUALIFIED", formal_eligible=True, permissions=["local_read", "local_write", "execute"]),
        provider_runtime.provider("host-competition-modeling", "HOST_LLM", ["mathematical-modeling"], status="HOST_REQUEST_CAPABLE", qualification="HOST_REQUEST_CAPABLE", permissions=["local_read", "local_write"]),
        provider_runtime.provider("host-competition-coding", "HOST_LLM", ["code-generation"], status="HOST_REQUEST_CAPABLE", qualification="HOST_REQUEST_CAPABLE", permissions=["local_read", "local_write"]),
        provider_runtime.provider("host-competition-specialist", "HOST_LLM", [
            "model-validation", "sensitivity-analysis", "scientific-visualization",
            "evidence-bound-writing", "adversarial-review", "evidence-bound-revision",
        ], status="HOST_REQUEST_CAPABLE", qualification="HOST_REQUEST_CAPABLE", permissions=["local_read", "local_write"]),
        provider_runtime.provider("competition-analysis-provider", "NATIVE", ["model-validation", "sensitivity-analysis", "scientific-visualization"], qualification="QUALIFIED", formal_eligible=False, quality_level="BASELINE", permissions=["local_read", "local_write"]),
        provider_runtime.provider("competition-writing-provider", "NATIVE", ["evidence-bound-writing", "adversarial-review", "evidence-bound-revision", "artifact-validation"], qualification="QUALIFIED", formal_eligible=False, quality_level="BASELINE", permissions=["local_read", "local_write"]),
    ]
    employee_registry = support.read_json(support.state_dir(project) / "employee_registry.json", {})
    employees = employee_registry.get("employees", []) if isinstance(employee_registry, dict) else []
    for employee in employees:
        if not isinstance(employee, dict) or employee.get("status") != "SPECIALIST":
            continue
        capabilities = employee.get("capabilities", [])
        if not isinstance(capabilities, list) or employee.get("qualification_state") != "FORMAL_QUALIFIED":
            continue
        external = provider_runtime.provider(
            str(employee.get("provider_id") or employee.get("id")), "EXTERNAL_SKILL", capabilities,
            status="AVAILABLE", qualification=str(employee.get("qualification") or "DELEGATION_READY"),
            formal_eligible=True, permissions=employee.get("provider_permissions", ["local_read", "local_write", "execute"]),
            installed=True, quality_level="FORMAL_QUALIFIED",
        )
        external.update({
            "exact_ref": employee.get("exact_ref"),
            "capability_verification": employee.get("capability_verification"),
            "static_audit": employee.get("static_audit"),
            "behavior_trial": employee.get("behavior_trial"),
            "materialized_path": employee.get("materialized_path"),
            "entrypoint": employee.get("entrypoint", "worker.py"),
        })
        records.append(external)
    return records


def _invoke(project: Path, provider_id: str, node: str) -> dict[str, Any]:
    if provider_id == "competition-modeling-provider":
        return competition_modeling_provider.execute(project, node)
    if provider_id in {"native-competition-baseline", "deterministic-competition-execution"}:
        return competition_coding_provider.execute(project, node)
    if provider_id == "competition-analysis-provider":
        return competition_analysis_provider.execute(project, node)
    return competition_writing_provider.execute(project, node)


def _execute_external(project: Path, provider: dict[str, Any], node: str, task: dict[str, Any]) -> dict[str, Any]:
    execution = marketplace_runtime.execute_employed(project, str(provider["provider_id"]), task)
    if execution.get("status") != "PASS":
        return {
            "status": "FAIL", "provider_id": provider["provider_id"], "artifacts": [],
            "claims": [], "uncertainties": [execution.get("reason", "external employee execution failed")],
            "actions_taken": ["external specialist execution rejected"], "tool_calls": [], "handoff": {},
            "external_execution": execution,
        }
    raw = execution.get("result")
    artifact = project / "artifacts" / "external-specialists" / f"{node}.json"
    support.write(artifact, raw if isinstance(raw, dict) else {"value": raw})
    return support.handoff(
        project, str(provider["provider_id"]), node, [artifact], formal=True,
        actions=["execute accepted external specialist in isolated materialization"],
        tool_calls=[{"operation": "skill_marketplace_runtime.execute_employed", "provider_id": provider["provider_id"]}],
        extra={"result": raw, "external_execution": execution},
    )


def _validate(project: Path, result: dict[str, Any]) -> dict[str, Any]:
    findings = []
    if result.get("status") != "PASS":
        findings.extend(result.get("findings", ["provider did not return PASS"]))
    if provider_runtime.HANDOFF_FIELDS - set(result):
        findings.append("typed provider handoff is incomplete")
    for relative in result.get("artifacts", []):
        path = (project / str(relative)).resolve()
        try:
            path.relative_to(project.resolve())
        except ValueError:
            findings.append(f"artifact escapes project: {relative}")
            continue
        if not path.is_file() or path.stat().st_size == 0:
            findings.append(f"artifact is missing or empty: {relative}")
    if not result.get("artifacts"):
        findings.append("provider emitted no artifacts")
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def _register(project: Path, node: str, result: dict[str, Any]) -> tuple[list[str], Path]:
    input_path = support.state_dir(project) / "competition_input.json"
    inputs = [input_path] if input_path.is_file() else []
    manifest_path = support.state_dir(project) / "artifact_manifest.json"
    manifest = support.read_json(manifest_path, {})
    entries = manifest.setdefault("artifacts", [])
    evidence = []
    for relative in result.get("artifacts", []):
        path = (project / relative).resolve()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        anchor_id = f"EA-COMP-{node.upper().replace('_', '-')}-{digest[:12]}"
        evidence.append(anchor_id)
        ledger_path = support.state_dir(project) / "evidence_ledger.json"
        ledger = support.read_json(ledger_path, {})
        anchors = ledger.setdefault("anchors", [])
        if not any(item.get("anchor_id") == anchor_id for item in anchors):
            anchors.append({
                "anchor_id": anchor_id, "claim_id": "COMPETITION-RUNTIME", "result_id": f"R-{node.upper()}",
                "source_artifact": f"{relative}#sha256={digest}", "source_sha256": digest,
                "exact_region": "complete typed artifact", "transformation": f"provider:{result.get('provider_id')} plus deterministic checker",
                "uncertainty": "bounded to supplied contest data and declared assumptions", "scope": "competition project",
                "status": "OBSERVED", "provenance_level": "OBSERVED", "artifact_type": "competition_output",
                "artifact_acquisition_record_id": f"provider:{result.get('provider_id')}:{node}",
            })
            support.write(ledger_path, ledger)
        freshness = provider_runtime.artifact_record(project, path, result.get("provider_id", "unknown"), result.get("provider_version", SKILL_VERSION), inputs, [], command_or_tool=result.get("tool_calls", []))
        record = {"id": freshness["artifact_id"], "path": relative, "type": "competition_output", "sha256": support.digest(path), "created_by": f"provider:{result.get('provider_id')}:{node}", "status": "OBSERVED", "freshness": freshness}
        entries[:] = [item for item in entries if item.get("path") != relative]
        entries.append(record)
    support.write(manifest_path, manifest)
    summary = support.write(project / "artifacts" / "competition" / f"{node}.json", {"node": node, "status": "PASS", "provider_id": result.get("provider_id"), "artifacts": result.get("artifacts"), "evidence": evidence, "checker": "deterministic-output-checker"})
    return evidence, summary


def execute_node(project: Path, node_id: str) -> dict[str, Any]:
    project = project.resolve()
    if _fixture_mode(project):
        return _fixture().execute_node(project, node_id)
    registry = _providers(project)
    support.write(support.state_dir(project) / "provider_registry.json", {"schema_version": 1, "skill_version": SKILL_VERSION, "providers": registry})
    entry = NODE_PROVIDER.get(node_id)
    if entry is None:
        return {"operation": "competition-execute-node", "status": "FAIL", "node": node_id, "findings": ["no provider capability mapping"]}
    expected_provider, capability = entry
    policy = support.read_json(support.state_dir(project) / "autonomy_policy.json", {})
    permissions = policy.get("permissions", {"local_read": True, "local_write": True, "execute": True})
    recorded_host = _recorded_host_context(project)
    specialist_required = _specialist_required(project, node_id) and not recorded_host
    discovery_attempted = _discovery_attempted(project, node_id, capability)
    specialist_discovery = None
    specialist_hire = None
    employment_lifecycle: list[str] = []
    route = provider_runtime.resolve_provider(
        capability,
        {
            "node": node_id,
            "specialist_required": specialist_required,
            "load_bearing": specialist_required,
            "discovery_attempted": discovery_attempted,
        },
        node_id in FORMAL_NODES and (node_id not in SPECIALIST_NODES or specialist_required) and not recorded_host,
        "LOW",
        permissions,
        registry,
    )
    if route.get("status") == "SPECIALIST_DISCOVERY":
        specialist_discovery = _specialist_discovery(project, node_id, capability)
        discovery_attempted = True
        employment_lifecycle = ["SPECIALIST_DISCOVERY", "AUTO_HIRE"]
        if specialist_discovery.get("status") == "PASS" and specialist_discovery.get("candidates"):
            if permissions.get("auto_hire") is True:
                policy = support.read_json(support.state_dir(project) / "autonomy_policy.json", {})
                specialist_hire = marketplace_runtime.auto_hire_missing_capability(
                    project, capability, {"node": node_id, "project": project.name},
                    policy=policy, discovery_result=specialist_discovery, discovery_backends=[],
                )
                if specialist_hire.get("status") == "ACCEPTED":
                    registry = _providers(project)
                    employment_lifecycle = list(specialist_hire.get("employment_lifecycle", employment_lifecycle))
            else:
                specialist_hire = {
                    "operation": "auto-hire-missing-capability", "status": "BLOCKED",
                    "reason": "AUTO_HIRE is disabled by autonomy policy", "provider_lifecycle": ["DISCOVERY"],
                    "employment_lifecycle": employment_lifecycle,
                }
        else:
            specialist_hire = {
                "operation": "auto-hire-missing-capability", "status": "BLOCKED",
                "reason": "discovery returned no candidate", "provider_lifecycle": ["DISCOVERY"],
                "employment_lifecycle": employment_lifecycle,
            }
        route = provider_runtime.resolve_provider(
            capability,
            {
                "node": node_id,
                "specialist_required": specialist_required,
                "load_bearing": specialist_required,
                "discovery_attempted": discovery_attempted,
            },
            node_id in FORMAL_NODES and (node_id not in SPECIALIST_NODES or specialist_required) and not recorded_host,
            "LOW",
            permissions,
            registry,
        ) | {
            "specialist_discovery": specialist_discovery,
            "discovery_attempted": True,
            "specialist_hire": specialist_hire,
        }
        if specialist_hire and specialist_hire.get("status") == "ACCEPTED":
            employment_lifecycle = list(specialist_hire.get("employment_lifecycle", employment_lifecycle)) + ["RE-RESOLVE"]
    if specialist_discovery is not None:
        route = route | {
            "specialist_discovery": specialist_discovery,
            "discovery_attempted": True,
        }
    if specialist_hire and specialist_hire.get("employment_lifecycle") and not employment_lifecycle:
        employment_lifecycle = list(specialist_hire["employment_lifecycle"])
    if route.get("status") == "HOST_EXECUTION_REQUIRED":
        selected = route.get("provider", {})
        selected_id = str(selected.get("provider_id") or "")
        if selected_id == "host-competition-specialist":
            result = competition_host_provider.request_specialist(project, node_id, capability)
            if result.get("status") == "HOST_EXECUTION_REQUIRED":
                return result | {
                    "operation": "competition-execute-node", "node": node_id,
                    "capability": capability, "provider_route": route,
                    "host_request_created": True, "host_handoff_required": True,
                    "specialist_discovery": specialist_discovery,
                    "specialist_hire": specialist_hire,
                    "employment_lifecycle": employment_lifecycle,
                }
            expected_provider = selected_id
            # An accepted specialist handoff is checked and then consumed by
            # the normal typed-output path below.
            result = result
        else:
            capability_name = "competition-code-generation" if node_id == "minimal_viable_model" else "competition-modeling"
            result = competition_host_provider.request_or_consume(project, node_id, capability_name)
            if result.get("status") == "HOST_EXECUTION_REQUIRED":
                return result | {
                    "operation": "competition-execute-node", "node": node_id,
                    "provider_route": route, "host_request_created": True,
                    "specialist_discovery": specialist_discovery,
                    "specialist_hire": specialist_hire,
                    "employment_lifecycle": employment_lifecycle,
                }
            expected_provider = selected_id or expected_provider
    elif route.get("status") != "PASS":
        return {"operation": "competition-execute-node", "status": route.get("status", "FAIL"), "node": node_id, "findings": ["provider route did not resolve the required capability"], "provider_route": route, "specialist_discovery": specialist_discovery, "specialist_hire": specialist_hire, "employment_lifecycle": employment_lifecycle}
    else:
        selected = route["provider"]
        expected_provider = selected["provider_id"]
        try:
            result = _execute_external(project, selected, node_id, {"node": node_id, "project": project.name}) if selected.get("type") == "EXTERNAL_SKILL" else _invoke(project, expected_provider, node_id)
            if selected.get("type") == "EXTERNAL_SKILL":
                if "RE-RESOLVE" not in employment_lifecycle:
                    employment_lifecycle.append("RE-RESOLVE")
                employment_lifecycle.append("EXTERNAL_SKILL_EXECUTED")
        except Exception as exc:
            return {"operation": "competition-execute-node", "status": "FAIL", "node": node_id, "findings": [f"{type(exc).__name__}: {exc}"], "provider_route": route, "specialist_hire": specialist_hire, "employment_lifecycle": employment_lifecycle}
        if node_id == "method_candidates" and result.get("status") != "PASS":
            result = competition_host_provider.request_or_consume(project, node_id, "competition-modeling")
            if result.get("status") == "HOST_EXECUTION_REQUIRED":
                return result | {
                    "operation": "competition-execute-node", "node": node_id,
                    "provider_route": route, "host_request_created": True,
                    "employment_lifecycle": employment_lifecycle,
                }
            expected_provider = "host-competition-modeling"
    check = _validate(project, result)
    if check["status"] != "PASS":
        return result | {"operation": "competition-execute-node", "status": "FAIL", "node": node_id, "findings": check["findings"], "checker": check, "provider_route": route, "specialist_discovery": specialist_discovery, "specialist_hire": specialist_hire, "employment_lifecycle": employment_lifecycle}
    evidence, summary = _register(project, node_id, result)
    artifacts = [support.relative(project, summary)] + list(result["artifacts"])
    if selected.get("type") == "EXTERNAL_SKILL":
        if "RE-RESOLVE" not in employment_lifecycle:
            employment_lifecycle.append("RE-RESOLVE")
        if "EXTERNAL_SKILL_EXECUTED" not in employment_lifecycle:
            employment_lifecycle.append("EXTERNAL_SKILL_EXECUTED")
        employment_lifecycle.extend(["CHECKED", "ACCEPTED"])
        if specialist_hire is not None:
            specialist_hire = dict(specialist_hire)
            specialist_hire["employment_lifecycle"] = employment_lifecycle
            specialist_hire["workflow_lifecycle"] = list(marketplace_runtime.EMPLOYMENT_WORKFLOW)
    return result | {"operation": "competition-execute-node", "status": "PASS", "node": node_id, "artifacts": artifacts, "evidence": evidence, "checker": {"status": "PASS", "producer": expected_provider, "checker": "deterministic-output-checker"}, "provider_route": route, "specialist_discovery": specialist_discovery, "specialist_hire": specialist_hire, "employment_lifecycle": employment_lifecycle}
