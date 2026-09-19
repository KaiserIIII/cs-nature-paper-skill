#!/usr/bin/env python3
"""Host-neutral provider routing, handoff checking, and artifact freshness."""

from __future__ import annotations

import hashlib
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_VERSION = "4.0.0"
PROVIDER_TYPES = {"NATIVE", "HOST_LLM", "WEB", "EXTERNAL_SKILL", "INTERNAL_SPECIALIST", "TOOL"}
PROVIDER_STATUSES = {
    "AVAILABLE", "UNAVAILABLE", "QUALIFIED", "PROVISIONAL", "BLOCKED",
    "HOST_AVAILABLE", "HOST_REQUEST_CAPABLE", "HOST_BEHAVIOR_QUALIFIED",
}
QUALIFIED = {"QUALIFIED", "DELEGATION_READY", "HOST_BEHAVIOR_QUALIFIED"}
HOST_REQUEST_READY = {"HOST_REQUEST_CAPABLE", "HOST_BEHAVIOR_QUALIFIED"}
QUALITY_LEVELS = ("SCAFFOLD", "BASELINE", "GENERAL", "SPECIALIST", "FORMAL_QUALIFIED")
SPECIALIST_CAPABILITIES = {"novelty-analysis", "closest-work-analysis", "feasibility-analysis", "statistical-analysis", "scientific-visualization", "evidence-bound-writing", "evidence-bound-revision", "adversarial-review"}
SPECIALIST_TERMS = {
    "mixed effect", "mixed-effects", "bayesian", "causal inference", "survival",
    "multiple testing", "power analysis", "clustered", "hierarchical", "conformal",
    "risk control", "risk-controlled", "distribution shift", "selective prediction",
    "novelty", "closest work", "prior art", "formal proof", "publication-quality",
    "journal writing", "domain review", "method review", "statistics review",
}
REQUEST_FIELDS = {
    "task_id", "capability", "purpose", "formal", "inputs", "constraints",
    "required_outputs", "forbidden_claims", "evidence_requirements", "budget", "permissions",
}
HANDOFF_FIELDS = {
    "status", "artifacts", "claims", "uncertainties", "actions_taken", "tool_calls", "handoff",
}

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import internal_specialists  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def provider(
    provider_id: str,
    provider_type: str,
    capabilities: list[str],
    *,
    status: str = "QUALIFIED",
    qualification: str = "QUALIFIED",
    formal_eligible: bool = False,
    permissions: list[str] | None = None,
    network: bool = False,
    credentials_required: bool = False,
    cost_class: str = "FREE",
    checker_required: bool = True,
    input_contract: dict[str, Any] | None = None,
    output_contract: dict[str, Any] | None = None,
    failure_modes: list[str] | None = None,
    installed: bool | None = None,
    quality_level: str | None = None,
) -> dict[str, Any]:
    """Build a complete registry record; callers may persist the returned object."""
    # formal_eligible is an execution gate, not evidence that a provider is a
    # specialist.  Quality is explicit and conservative by default.
    inferred_quality = quality_level or (
        "SPECIALIST" if provider_type in {"EXTERNAL_SKILL", "INTERNAL_SPECIALIST"} else "GENERAL"
    )
    if inferred_quality not in QUALITY_LEVELS:
        raise ValueError(f"unknown provider quality level: {inferred_quality}")
    return {
        "provider_id": provider_id,
        "type": provider_type,
        "status": status,
        "capabilities": list(capabilities),
        "input_contract": input_contract or {"type": "object"},
        "output_contract": output_contract or {"type": "object", "typed_artifact": True},
        "permissions": list(permissions or []),
        "network": bool(network),
        "credentials_required": bool(credentials_required),
        "cost_class": cost_class,
        "formal_eligible": bool(formal_eligible),
        "checker_required": bool(checker_required),
        "qualification": qualification,
        "failure_modes": list(failure_modes or []),
        "installed": provider_type == "EXTERNAL_SKILL" if installed is None else bool(installed),
        "quality_level": inferred_quality,
    }


def validate_provider(value: Any) -> dict[str, Any]:
    required = {
        "provider_id", "type", "capabilities", "input_contract", "output_contract", "permissions",
        "network", "credentials_required", "cost_class", "formal_eligible", "checker_required",
        "qualification", "failure_modes",
    }
    findings: list[str] = []
    if not isinstance(value, dict):
        return {"status": "FAIL", "findings": ["provider must be an object"]}
    missing = sorted(required - set(value))
    if missing:
        findings.append("missing fields: " + ", ".join(missing))
    if value.get("type") not in PROVIDER_TYPES:
        findings.append("unknown provider type")
    if value.get("status", "AVAILABLE") not in PROVIDER_STATUSES:
        findings.append("unknown provider status")
    if not isinstance(value.get("capabilities"), list) or not value.get("capabilities"):
        findings.append("capabilities must be a non-empty list")
    if value.get("quality_level") is not None and value.get("quality_level") not in QUALITY_LEVELS:
        findings.append("quality_level must be one of " + ", ".join(QUALITY_LEVELS))
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def internal_specialist_provider(specialist_id: str, *, validate_pack: bool = True) -> dict[str, Any]:
    """Create a formal provider record from the validated V4 built-in pack."""
    if validate_pack:
        pack_check = internal_specialists.validate_pack()
        if pack_check["status"] != "PASS":
            raise ValueError("internal specialist pack is invalid: " + "; ".join(pack_check["findings"]))
    specialist = next(
        (item for item in internal_specialists.load_pack()["specialists"] if item["id"] == specialist_id),
        None,
    )
    if specialist is None:
        raise ValueError(f"unknown internal specialist: {specialist_id}")
    value = provider(
        f"internal-specialist:{specialist_id}",
        "INTERNAL_SPECIALIST",
        list(specialist["capabilities"]),
        status="QUALIFIED",
        qualification="QUALIFIED",
        formal_eligible=True,
        permissions=["local_read", "local_write"],
        network=False,
        credentials_required=False,
        checker_required=True,
        installed=True,
        quality_level="FORMAL_QUALIFIED",
        failure_modes=["vendored resource missing", "integrity mismatch", "output contract failure"],
    )
    value.update({
        "specialist_id": specialist_id,
        "quality_tier": internal_specialists.QUALITY_TIER,
        "checker": specialist["checker"],
        "source_kind": "VENDORED_BUILT_IN_TEAM",
    })
    return value


def specialist_requirement(capability: str, task: dict[str, Any] | None = None, formal: bool = False) -> bool:
    """Determine whether a task needs a specialist-quality provider."""
    task = task or {}
    if task.get("specialist_required") is True:
        return True
    text = " ".join(str(task.get(key, "")) for key in ("task", "description", "purpose", "node", "method", "methods")).lower()
    if any(term in text for term in SPECIALIST_TERMS):
        return capability in SPECIALIST_CAPABILITIES or capability in {"statistical-analysis", "evidence-bound-writing"}
    # A formal node is not automatically load-bearing. Callers mark the
    # invocations whose conclusions require specialist scrutiny.
    if formal and task.get("load_bearing", True) and capability in SPECIALIST_CAPABILITIES and capability != "statistical-analysis":
        return True
    return bool(formal and capability == "statistical-analysis" and task.get("load_bearing", False))


def _confirmed_specialist(item: dict[str, Any], capability: str) -> bool:
    """Require exact capability, pin, semantic verification, and trial evidence."""
    if item.get("type") == "INTERNAL_SPECIALIST":
        return (
            item.get("quality_level") == "FORMAL_QUALIFIED"
            and item.get("formal_eligible") is True
            and item.get("qualification") in QUALIFIED
            and item.get("checker_required") is True
            and item.get("source_kind") == "VENDORED_BUILT_IN_TEAM"
        )
    if item.get("type") != "EXTERNAL_SKILL":
        return item.get("quality_level") == "FORMAL_QUALIFIED" and item.get("formal_eligible") is True
    if item.get("installed") is not True:
        return False
    exact_ref = str(item.get("exact_ref", ""))
    if not __import__("re").fullmatch(r"[0-9a-f]{40}", exact_ref):
        return False
    if item.get("quality_level") not in {"SPECIALIST", "FORMAL_QUALIFIED"}:
        return False
    if item.get("formal_eligible") is not True or item.get("qualification") not in QUALIFIED or item.get("checker_required") is not True:
        return False
    verification = item.get("capability_verification")
    static = item.get("static_audit")
    if not isinstance(verification, dict) or verification.get("status") != "CONFIRMED" or verification.get("requested_capability") != capability or verification.get("formal_eligible") is not True:
        return False
    semantic = verification.get("semantic_audit") or {}
    trial = verification.get("behavior_trial") or {}
    if semantic.get("status") != "CONFIRMED" or not semantic.get("actor") or not semantic.get("evidence"):
        return False
    if trial.get("status") != "PASS" or trial.get("output_contract") != "PASS" or not trial.get("checker"):
        return False
    return isinstance(static, dict) and static.get("status") == "PASS" and static.get("exact_commit") == exact_ref


def _eligible(
    item: dict[str, Any], capability: str, formal: bool, permissions: set[str]
) -> bool:
    if validate_provider(item)["status"] != "PASS":
        return False
    if capability not in item.get("capabilities", []):
        return False
    if item.get("status", "AVAILABLE") in {"UNAVAILABLE", "BLOCKED"}:
        return False
    if not set(item.get("permissions", [])).issubset(permissions):
        return False
    if formal and (
        item.get("formal_eligible") is not True
        or item.get("qualification") not in QUALIFIED
        or item.get("checker_required") is not True
    ):
        return False
    return item.get("qualification") in QUALIFIED or (not formal and item.get("status") == "AVAILABLE")


def _host_request_eligible(
    item: dict[str, Any], capability: str, permissions: set[str]
) -> bool:
    return (
        validate_provider(item)["status"] == "PASS"
        and item.get("type") == "HOST_LLM"
        and capability in item.get("capabilities", [])
        and item.get("status") not in {"UNAVAILABLE", "BLOCKED"}
        and item.get("qualification") in HOST_REQUEST_READY
        and set(item.get("permissions", [])).issubset(permissions)
        and item.get("checker_required") is True
    )


def resolve_provider(
    capability: str,
    task: dict[str, Any],
    formal: bool,
    risk: str,
    permissions: set[str] | list[str] | dict[str, Any],
    available_providers: list[dict[str, Any]],
) -> dict[str, Any]:
    """Resolve by authority order without granting scientific truth to a provider."""
    if isinstance(permissions, dict):
        allowed = {key for key, enabled in permissions.items() if enabled is True}
    else:
        allowed = set(permissions)
    specialist_required = specialist_requirement(capability, task, formal)
    task_text = " ".join(
        str(task.get(key, "")) for key in ("task", "description", "purpose", "node", "method", "methods")
    ).strip()
    internal_candidates = [
        item for item in available_providers
        if item.get("type") == "INTERNAL_SPECIALIST" and _eligible(item, capability, formal, allowed)
    ]
    confirmed_external = [
        item for item in available_providers
        if item.get("type") == "EXTERNAL_SKILL"
        and _eligible(item, capability, formal, allowed)
        and (not specialist_required or _confirmed_specialist(item, capability))
    ]
    comparison = task.get("external_comparison")
    if comparison is None and confirmed_external and task.get("discovery_attempted"):
        comparison = "COMPLEMENTARY"
    decision = internal_specialists.provider_decision(
        capability,
        task=task_text,
        purpose="formal" if formal else str(task.get("purpose") or "advisory"),
        load_bearing=bool(task.get("load_bearing")),
        criticality=risk,
        internal_available=bool(internal_candidates),
        discovery_status=task.get("discovery_status") or (
            "PASS" if confirmed_external and task.get("discovery_attempted") else None
        ),
        discovery_attempted=bool(task.get("discovery_attempted")),
        external_comparison=comparison,
    )
    if decision["decision"] == "QUALITY_UPGRADE_DISCOVERY":
        fallback = sorted(internal_candidates, key=lambda item: str(item["provider_id"]))[0]
        return {
            "operation": "resolve-provider", "status": "SPECIALIST_DISCOVERY", "capability": capability,
            "formal": formal, "risk": risk, "specialist_required": specialist_required,
            "discovery_required": True, "fallback_provider": fallback,
            "provider_decision": decision, "truth_authority": "DETERMINISTIC_CHECKER",
            "next": "skill_discovery_provider",
        }
    candidates = [
        item for item in available_providers if _eligible(item, capability, formal, allowed)
    ]
    if specialist_required:
        candidates = [item for item in candidates if _confirmed_specialist(item, capability)]

    if decision["decision"] in {"EXTERNAL_BETTER", "COMPLEMENTARY"} and confirmed_external:
        candidates = confirmed_external
    elif internal_candidates:
        candidates = internal_candidates

    def priority(item: dict[str, Any]) -> tuple[int, str]:
        if item["type"] == "INTERNAL_SPECIALIST":
            rank = 0
        elif item["type"] == "NATIVE":
            rank = 1
        elif item["type"] == "EXTERNAL_SKILL" and item.get("installed"):
            rank = 2
        elif item["type"] in {"HOST_LLM", "TOOL", "WEB"}:
            rank = 3
        else:
            rank = 4
        return rank, str(item["provider_id"])

    if candidates:
        selected = sorted(candidates, key=priority)[0]
        if selected["type"] == "HOST_LLM":
            return {
                "operation": "resolve-provider", "status": "HOST_EXECUTION_REQUIRED",
                "capability": capability, "provider": selected, "formal": formal, "risk": risk,
                "truth_authority": "DETERMINISTIC_CHECKER", "task": task, "specialist_required": specialist_required,
                "discovery_required": False, "handoff_required": True, "checker_required": True,
                "provider_decision": decision,
            }
        return {
            "operation": "resolve-provider", "status": "PASS", "capability": capability,
            "provider": selected, "formal": formal, "risk": risk,
            "truth_authority": "DETERMINISTIC_CHECKER", "task": task, "specialist_required": specialist_required,
            "discovery_required": False, "provider_decision": decision,
        }
    host_candidates = [
        item for item in available_providers
        if _host_request_eligible(item, capability, allowed)
    ]
    # A request-capable Host must not suppress the required specialist
    # discovery attempt.  Discovery is metadata-only and does not require
    # installation permission; AUTO_HIRE permission is still checked later
    # before any materialization or execution.
    if specialist_required and not task.get("discovery_attempted") and ("auto_hire" in allowed or host_candidates):
        return {
            "operation": "resolve-provider", "status": "SPECIALIST_DISCOVERY", "capability": capability,
            "formal": formal, "risk": risk, "specialist_required": True, "discovery_required": True,
            "host_fallback": "HOST_EXECUTION_REQUIRED" if host_candidates else None,
            "truth_authority": "DETERMINISTIC_CHECKER", "next": "skill_discovery_provider",
            "provider_decision": decision,
        }
    if host_candidates:
        selected = sorted(host_candidates, key=lambda item: str(item["provider_id"]))[0]
        return {
            "operation": "resolve-provider", "status": "HOST_EXECUTION_REQUIRED",
            "capability": capability, "provider": selected, "formal": formal, "risk": risk,
            "truth_authority": "DETERMINISTIC_CHECKER", "task": task, "specialist_required": specialist_required,
            "discovery_required": False, "handoff_required": True, "checker_required": True, "evidence_required": True,
            "provider_decision": decision,
        }
    if "auto_hire" in allowed and risk in {"LOW", "MEDIUM"}:
        return {
            "operation": "resolve-provider", "status": "AUTO_HIRE", "capability": capability,
            "formal": formal, "risk": risk, "next": "skill_discovery_provider",
            "specialist_required": specialist_required, "discovery_required": True,
            "provider_decision": decision,
        }
    return {
        "operation": "resolve-provider", "status": "FALLBACK", "capability": capability,
        "formal": formal, "risk": risk,
        "recovery": ["RETRY", "REPAIR_INPUT", "ALTERNATE_PROVIDER", "AUTO_HIRE", "SIMPLIFY", "REDUCE_SCOPE", "ASK_AUTHOR"],
        "specialist_required": specialist_required, "discovery_required": False,
        "provider_decision": decision,
    }


def host_request(**value: Any) -> dict[str, Any]:
    missing = REQUEST_FIELDS - set(value)
    if missing:
        raise ValueError("host request missing fields: " + ", ".join(sorted(missing)))
    return {key: value[key] for key in REQUEST_FIELDS}


def check_host_handoff(
    request: dict[str, Any],
    handoff: dict[str, Any],
    *,
    producer_id: str,
    checker_id: str,
) -> dict[str, Any]:
    findings: list[str] = []
    if REQUEST_FIELDS - set(request):
        findings.append("request contract is incomplete")
    if HANDOFF_FIELDS - set(handoff):
        findings.append("handoff contract is incomplete")
    if handoff.get("status") != "PASS":
        findings.append("provider handoff is not PASS")
    if request.get("formal") and not handoff.get("artifacts"):
        findings.append("formal handoff has no observed artifact")
    if producer_id == checker_id:
        findings.append("producer and checker invocation are identical")
    same_host = producer_id.split(":", 1)[0] == checker_id.split(":", 1)[0]
    return {
        "operation": "check-host-handoff",
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "checker_independence": "LIMITED" if same_host and producer_id != checker_id else "INDEPENDENT",
        "graph_transition_authorized": not findings,
    }


def artifact_record(
    project: Path,
    artifact: Path,
    provider_id: str,
    provider_version: str,
    inputs: list[Path],
    upstream_artifact_ids: list[str],
    *,
    command_or_tool: Any = None,
) -> dict[str, Any]:
    root = project.resolve()
    hashes = {
        path.resolve().relative_to(root).as_posix(): _sha(path)
        for path in inputs if path.is_file()
    }
    return {
        "artifact_id": "PA-" + hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:16],
        "path": artifact.resolve().relative_to(root).as_posix(),
        "input_hashes": hashes,
        "provider_id": provider_id,
        "provider_version": provider_version,
        "command_or_tool_record": command_or_tool,
        "upstream_artifact_ids": list(upstream_artifact_ids),
        "created_utc": _now(),
        "status": "FRESH",
    }


def check_freshness(project: Path, record: dict[str, Any]) -> dict[str, Any]:
    changed = []
    for relative, expected in record.get("input_hashes", {}).items():
        path = project.resolve() / relative
        if not path.is_file() or _sha(path) != expected:
            changed.append(relative)
    return {"status": "STALE" if changed else "FRESH", "changed_inputs": changed}


def invalidate_downstream(graph: dict[str, Any], changed_node: str) -> list[str]:
    affected: list[str] = []
    frontier = {changed_node}
    while frontier:
        next_frontier: set[str] = set()
        for node in graph.get("nodes", []):
            if node.get("id") in affected or node.get("id") == changed_node:
                continue
            dependencies = set(node.get("dependencies", node.get("depends_on", [])))
            if dependencies & frontier:
                node["status"] = "STALE"
                affected.append(node["id"])
                next_frontier.add(node["id"])
        frontier = next_frontier
    return affected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-registry")
    validate.add_argument("path", type=Path)
    route = sub.add_parser("route")
    route.add_argument("path", type=Path)
    route.add_argument("capability")
    route.add_argument("--formal", action="store_true")
    route.add_argument("--risk", default="LOW")
    route.add_argument("--permission", action="append", default=[])
    args = parser.parse_args(argv)
    value = json.loads(args.path.read_text(encoding="utf-8"))
    records = value.get("providers", []) if isinstance(value, dict) else []
    if args.command == "validate-registry":
        checks = [validate_provider(item) for item in records]
        result = {"operation": "validate-provider-registry", "status": "PASS" if records and all(item["status"] == "PASS" for item in checks) else "FAIL", "checks": checks}
    else:
        result = resolve_provider(args.capability, {}, args.formal, args.risk, set(args.permission), records)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
