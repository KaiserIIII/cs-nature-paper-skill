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


SKILL_VERSION = "3.2.0"
PROVIDER_TYPES = {"NATIVE", "HOST_LLM", "WEB", "EXTERNAL_SKILL", "TOOL"}
PROVIDER_STATUSES = {"AVAILABLE", "UNAVAILABLE", "QUALIFIED", "PROVISIONAL", "BLOCKED"}
QUALIFIED = {"QUALIFIED", "DELEGATION_READY"}
REQUEST_FIELDS = {
    "task_id", "capability", "purpose", "formal", "inputs", "constraints",
    "required_outputs", "forbidden_claims", "evidence_requirements", "budget", "permissions",
}
HANDOFF_FIELDS = {
    "status", "artifacts", "claims", "uncertainties", "actions_taken", "tool_calls", "handoff",
}


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
) -> dict[str, Any]:
    """Build a complete registry record; callers may persist the returned object."""
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
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


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
    candidates = [
        item for item in available_providers if _eligible(item, capability, formal, allowed)
    ]

    def priority(item: dict[str, Any]) -> tuple[int, str]:
        if item["type"] == "NATIVE":
            rank = 0
        elif item["type"] == "EXTERNAL_SKILL" and item.get("installed"):
            rank = 1
        elif item["type"] in {"HOST_LLM", "TOOL", "WEB"}:
            rank = 2
        else:
            rank = 3
        return rank, str(item["provider_id"])

    if candidates:
        selected = sorted(candidates, key=priority)[0]
        return {
            "operation": "resolve-provider", "status": "PASS", "capability": capability,
            "provider": selected, "formal": formal, "risk": risk,
            "truth_authority": "DETERMINISTIC_CHECKER", "task": task,
        }
    if "auto_hire" in allowed and risk in {"LOW", "MEDIUM"}:
        return {
            "operation": "resolve-provider", "status": "AUTO_HIRE", "capability": capability,
            "formal": formal, "risk": risk, "next": "skill_discovery_provider",
        }
    return {
        "operation": "resolve-provider", "status": "FALLBACK", "capability": capability,
        "formal": formal, "risk": risk,
        "recovery": ["RETRY", "REPAIR_INPUT", "ALTERNATE_PROVIDER", "AUTO_HIRE", "SIMPLIFY", "REDUCE_SCOPE", "ASK_AUTHOR"],
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
