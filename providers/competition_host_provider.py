"""Host modeling/coding requests for competition methods outside native baselines."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import provider_support as support


SCRIPT_DIR = str(Path(__file__).resolve().parents[1] / "scripts")
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import host_provider_runtime  # noqa: E402


PROVIDER_ID = "competition-host-provider"
PLAN_FIELDS = {
    "question_id", "formulation", "variables", "parameters", "assumptions",
    "objective", "constraints", "baseline", "primary_model", "upgrade_condition",
    "validation_plan", "implementation_plan", "candidate_families",
}


def _source(project: Path) -> dict[str, Any]:
    state_path = support.state_dir(project) / "competition_input.json"
    return support.read_json(state_path if state_path.is_file() else project / "competition_input.json", {})


def _state(project: Path) -> dict[str, Any]:
    return support.read_json(support.state_dir(project) / "competition_state.json", {})


def _inventory(project: Path) -> list[dict[str, Any]]:
    output = []
    kind_map = {
        ".csv": "CSV", ".xlsx": "XLSX", ".xls": "XLSX", ".json": "JSON",
        ".txt": "TXT", ".png": "IMAGE", ".jpg": "IMAGE", ".jpeg": "IMAGE",
    }
    for path in sorted(project.rglob("*")):
        if not path.is_file() or ".research-state" in path.parts:
            continue
        suffix = path.suffix.casefold()
        kind = kind_map.get(suffix)
        if kind:
            output.append({
                "path": support.relative(project, path), "kind": kind,
                "bytes": path.stat().st_size, "sha256": support.digest(path),
            })
    source = _source(project)
    for problem in source.get("problems", []):
        for key, value in problem.items():
            if isinstance(value, (list, dict)) and key not in {"questions", "decision_profile", "data_files"}:
                output.append({"path": f"<embedded:{problem.get('id')}:{key}>", "kind": "JSON", "structure": type(value).__name__})
    return output


def _clock(project: Path) -> dict[str, Any]:
    return support.read_json(support.state_dir(project) / "competition_clock.json", {})


def _context(project: Path, node: str, capability: str) -> dict[str, Any]:
    source = _source(project)
    state = _state(project)
    selected = state.get("selected_problem")
    problem = next((item for item in source.get("problems", []) if item.get("id") == selected), None)
    if problem is None and len(source.get("problems", [])) == 1:
        problem = source["problems"][0]
    return {
        "problem_statement": problem or {},
        "all_questions": (problem or {}).get("questions", []),
        "data_inventory": _inventory(project),
        "constraints": (problem or {}).get("constraints", []),
        "clock": _clock(project),
        "phase": state.get("phase", node),
        "candidate_families": sorted({
            family
            for item in state.get("modeling_plan", [])
            for family in item.get("candidate_families", [])
        }),
        "resource_budget": {"money": 0, "network": False, "deadline": _clock(project).get("submission_deadline_utc")},
        "existing_modeling_plan": state.get("modeling_plan", []),
        "capability": capability,
    }


def _task_id(project: Path, node: str, context: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(context, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]
    return f"{project.name}:{node}:{digest}"


def request(project: Path, node: str, capability: str) -> dict[str, Any]:
    context = _context(project, node, capability)
    coding = "code" in capability
    required = (
        ["changed_files", "entrypoint", "config", "tests", "commands", "expected_outputs", "limitations"]
        if coding
        else [
            "per-question formulation", "variables", "parameters", "assumptions", "objective",
            "constraints", "baseline", "primary model", "upgrade condition", "validation plan",
            "implementation plan",
        ]
    )
    value = {
        "task_id": _task_id(project, node, context),
        "node": node,
        "capability": capability,
        "formal": False,
        "inputs": [item["path"] for item in context["data_inventory"]],
        "constraints": [
            "derive the plan from the supplied problem and data inventory",
            "do not assume series, alternatives, records, or dynamics exist",
            "preserve the existing repository and contest clock",
            "do not transition the graph",
        ],
        "required_outputs": required,
        "evidence_requirements": ["typed artifact", "artifact hash", "independent checker", "deterministic execution for solver code"],
        "forbidden_claims": ["unexecuted solver is valid", "unverified optimum", "fabricated input field"],
        "permissions": {"local_read": True, "local_write": True, "execute": coding, "network": False, "external_write": False},
        "budget": context["resource_budget"],
        **context,
    }
    return host_provider_runtime.create_request(project, value) | {"host_request": value}


def _artifacts(project: Path, handoff: dict[str, Any]) -> list[Path]:
    output = []
    for relative in handoff.get("artifacts", []):
        path = (project / str(relative)).resolve()
        if path.is_file() and project.resolve() in path.parents:
            output.append(path)
    return output


def _consume_modeling(project: Path, node: str, active: dict[str, Any], handoff: dict[str, Any]) -> dict[str, Any]:
    artifacts = _artifacts(project, handoff)
    plan_artifact = next((path for path in artifacts if path.suffix.casefold() == ".json"), None)
    value = support.read_json(plan_artifact, {}) if plan_artifact else {}
    plans = value.get("questions", value.get("modeling_plan", [])) if isinstance(value, dict) else []
    findings = []
    if not isinstance(plans, list) or not plans:
        findings.append("host modeling handoff has no per-question plan")
    else:
        for index, plan in enumerate(plans):
            if not isinstance(plan, dict) or PLAN_FIELDS - set(plan):
                findings.append(f"modeling plan {index} is incomplete")
    if findings:
        return {"status": "FAIL", "findings": findings}
    state = _state(project)
    families = sorted({str(family) for plan in plans for family in plan.get("candidate_families", [])})
    state["modeling_plan"] = plans
    state["candidate_models"] = plans
    state["method_families"] = families
    state["baseline_model"] = "; ".join(str(plan.get("baseline")) for plan in plans)
    state["primary_model"] = "; ".join(str(plan.get("primary_model")) for plan in plans)
    state["host_modeling_task_id"] = handoff.get("task_id")
    support.write(support.state_dir(project) / "competition_state.json", state)
    return support.handoff(
        project, str(handoff.get("provider_id") or PROVIDER_ID), node, artifacts,
        actions=list(handoff.get("actions_taken", [])),
        uncertainties=list(handoff.get("uncertainties", [])),
        extra={
            "host_request_created": True, "host_handoff_received": True,
            "host_lifecycle": active.get("lifecycle", []), "modeling_plan": plans,
        },
    )


def _consume_coding(project: Path, node: str, active: dict[str, Any], handoff: dict[str, Any]) -> dict[str, Any]:
    artifacts = _artifacts(project, handoff)
    contract = {
        "task_id": handoff.get("task_id"), "provider_id": handoff.get("provider_id"),
        "changed_files": handoff.get("changed_files", []), "entrypoint": handoff.get("entrypoint"),
        "config": handoff.get("config"), "tests": handoff.get("tests", []),
        "commands": handoff.get("commands", []), "expected_outputs": handoff.get("expected_outputs", []),
        "limitations": handoff.get("limitations", []), "checker": active.get("checker"),
    }
    contract_path = support.write(support.state_dir(project) / "competition_host_code_contract.json", contract)
    artifacts.append(contract_path)
    return support.handoff(
        project, str(handoff.get("provider_id") or PROVIDER_ID), node, artifacts,
        actions=list(handoff.get("actions_taken", [])),
        uncertainties=list(handoff.get("uncertainties", [])),
        tool_calls=list(handoff.get("tool_calls", [])),
        extra={
            "host_request_created": True, "host_handoff_received": True,
            "host_lifecycle": active.get("lifecycle", []), "changed_files": handoff.get("changed_files", []),
            "entrypoint": handoff.get("entrypoint"), "commands": handoff.get("commands", []),
        },
    )


def request_or_consume(project: Path, node: str, capability: str) -> dict[str, Any]:
    active = host_provider_runtime.active_for_node(project, node)
    if active and active.get("status") == "ACCEPTED" and isinstance(active.get("handoff"), dict):
        if capability == "competition-modeling":
            return _consume_modeling(project, node, active, active["handoff"])
        return _consume_coding(project, node, active, active["handoff"])
    if active:
        return active | {
            "operation": "competition-host-provider", "status": "HOST_EXECUTION_REQUIRED",
            "host_request_created": True, "capability": capability,
        }
    return request(project, node, capability) | {"operation": "competition-host-provider", "capability": capability}


def request_specialist(project: Path, node: str, capability: str) -> dict[str, Any]:
    """Create or consume a generic scientific specialist handoff.

    Specialist outputs are deliberately opaque to this adapter: the independent
    host lifecycle checker validates the typed artifact and the competition
    runtime remains the sole authority allowed to advance the graph.
    """
    active = host_provider_runtime.active_for_node(project, node)
    if active and active.get("status") == "ACCEPTED" and isinstance(active.get("handoff"), dict):
        handoff = active["handoff"]
        artifacts = _artifacts(project, handoff)
        if not artifacts:
            return {"status": "FAIL", "findings": ["accepted specialist handoff has no observed artifact"]}
        return support.handoff(
            project,
            str(handoff.get("provider_id") or PROVIDER_ID),
            node,
            artifacts,
            formal=True,
            actions=list(handoff.get("actions_taken", [])),
            claims=list(handoff.get("claims", [])),
            uncertainties=list(handoff.get("uncertainties", [])),
            tool_calls=list(handoff.get("tool_calls", [])),
            extra={
                "host_request_created": True,
                "host_handoff_received": True,
                "host_lifecycle": active.get("lifecycle", []),
                "model_behavior": "RECORDED_HANDOFF" if str(handoff.get("provider_id", "")).startswith("recorded-") else "HOST_HANDOFF",
            },
        )
    if active:
        return active | {
            "operation": "competition-host-specialist",
            "status": "HOST_EXECUTION_REQUIRED",
            "host_request_created": True,
            "capability": capability,
        }
    context = _context(project, node, capability)
    task_id = _task_id(project, node, context)
    value = {
        "task_id": task_id,
        "node": node,
        "capability": capability,
        "formal": True,
        "inputs": [item["path"] for item in context["data_inventory"]],
        "constraints": [
            "use supplied contest evidence only",
            "return typed artifacts and explicit uncertainties",
            "do not transition the graph or claim optimality without evidence",
        ],
        "required_outputs": ["typed artifact", "claims", "uncertainties", "actions_taken"],
        "evidence_requirements": ["artifact hash", "independent checker"],
        "forbidden_claims": ["unverified optimum", "fabricated execution", "unsupported scientific validity"],
        "permissions": {"local_read": True, "local_write": True, "execute": False, "network": False, "external_write": False},
        "budget": context["resource_budget"],
    }
    return host_provider_runtime.create_request(project, value) | {
        "operation": "competition-host-specialist",
        "capability": capability,
        "host_request": value,
    }
