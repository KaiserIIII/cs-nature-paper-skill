"""Build problem-specific research coding requests and consume checked host artifacts."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import coding_provider
import provider_support as support


SCRIPT_DIR = str(Path(__file__).resolve().parents[1] / "scripts")
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import host_provider_runtime  # noqa: E402


PROVIDER_ID = "host-coding-provider"


def _context(project: Path) -> dict[str, Any]:
    state = support.state_dir(project)
    brief = support.read_json(project / "inputs" / "research_brief.json", {})
    project_meta = support.read_json(state / "project.json", {})
    claims = support.read_json(state / "claims.json", {})
    protocol = support.read_json(project / "artifacts" / "frozen_protocol.json", {})
    if not protocol:
        protocol = support.read_json(state / "research_contract.json", {}).get("protocol", {})
    inventory = coding_provider.scan_project(project)
    data_inventory = []
    for path in sorted((project / "inputs").glob("*")) if (project / "inputs").is_dir() else []:
        if path.is_file():
            data_inventory.append({
                "path": support.relative(project, path),
                "suffix": path.suffix.casefold(),
                "bytes": path.stat().st_size,
                "sha256": support.digest(path),
            })
    existing_code = sorted({
        path
        for group in ("entrypoints", "loaders", "tests", "scripts", "notebooks", "models")
        for path in inventory.get(group, [])
    })
    return {
        "research_question": brief.get("question"),
        "domain": brief.get("domain") or project_meta.get("domain"),
        "study_type": brief.get("study_type") or project_meta.get("study_type") or project_meta.get("type"),
        "claims": claims.get("claims", []),
        "protocol": protocol,
        "method_plan": {
            "candidate_methods": brief.get("method_candidates", []),
            "outcome": brief.get("outcome"),
            "validation_plan": brief.get("validation_plan", ["run declared tests", "execute formal command", "validate expected outputs"]),
        },
        "existing_repository_inventory": inventory,
        "data_inventory": data_inventory,
        "existing_code": existing_code,
        "allowed_dependencies": brief.get("allowed_dependencies", ["python-standard-library"]),
        "required_outputs": [
            "changed_files", "entrypoint", "config", "tests", "commands",
            "expected_outputs", "limitations",
        ],
        "validation_plan": brief.get("validation_plan", ["syntax check", "test command", "formal deterministic execution", "output checker"]),
    }


def _task_id(project: Path, node: str, context: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(context, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]
    return f"{project.name}:{node}:{digest}"


def request(project: Path, node: str = "implementation") -> dict[str, Any]:
    context = _context(project)
    inputs = [item["path"] for item in context["data_inventory"]]
    value = {
        "task_id": _task_id(project, node, context),
        "node": node,
        "capability": "code-generation",
        "formal": False,
        "inputs": inputs,
        "constraints": [
            "inspect the existing repository before editing",
            "make the smallest sufficient project-local change",
            "separate code generation from deterministic execution",
            "do not claim unexecuted code works",
            "do not transition the research graph",
        ],
        "required_outputs": context["required_outputs"],
        "evidence_requirements": [
            "content-addressed changed files", "declared entrypoint and command",
            "tests or syntax check", "independent deterministic checker",
        ],
        "forbidden_claims": [
            "formal execution passed before the command runs",
            "unsupported scientific validity", "fabricated test result",
        ],
        "permissions": {"local_read": True, "local_write": True, "execute": True, "network": False, "external_write": False},
        "budget": {"money": 0, "dependency_policy": context["allowed_dependencies"]},
        **context,
    }
    return host_provider_runtime.create_request(project, value) | {"host_request": value}


def consume(project: Path, node: str = "implementation") -> dict[str, Any] | None:
    active = host_provider_runtime.active_for_node(project, node)
    if not active or active.get("status") != "ACCEPTED":
        return None
    handoff = active.get("handoff")
    if not isinstance(handoff, dict):
        return None
    contract = {
        "task_id": handoff.get("task_id"),
        "provider_id": handoff.get("provider_id"),
        "changed_files": handoff.get("changed_files", []),
        "entrypoint": handoff.get("entrypoint"),
        "config": handoff.get("config"),
        "tests": handoff.get("tests", []),
        "commands": handoff.get("commands", []),
        "expected_outputs": handoff.get("expected_outputs", []),
        "limitations": handoff.get("limitations", []),
        "checker": active.get("checker"),
        "model_behavior": "RECORDED_HANDOFF" if str(handoff.get("provider_id", "")).startswith("recorded-") else "HOST_HANDOFF",
    }
    contract_path = support.write(support.state_dir(project) / "host_code_contract.json", contract)
    artifacts = []
    for relative in handoff.get("artifacts", []):
        path = (project / str(relative)).resolve()
        if path.is_file() and project.resolve() in path.parents:
            artifacts.append(path)
    artifacts.append(contract_path)
    return support.handoff(
        project,
        str(handoff.get("provider_id") or PROVIDER_ID),
        node,
        artifacts,
        actions=list(handoff.get("actions_taken", [])),
        claims=list(handoff.get("claims", [])),
        uncertainties=list(handoff.get("uncertainties", [])),
        tool_calls=list(handoff.get("tool_calls", [])),
        extra={
            "host_request_created": True,
            "host_handoff_received": True,
            "host_lifecycle": active.get("lifecycle", []),
            "changed_files": handoff.get("changed_files", []),
            "entrypoint": handoff.get("entrypoint"),
            "commands": handoff.get("commands", []),
            "expected_outputs": handoff.get("expected_outputs", []),
            "limitations": handoff.get("limitations", []),
        },
    )


def request_or_consume(project: Path, node: str = "implementation") -> dict[str, Any]:
    accepted = consume(project, node)
    if accepted is not None:
        return accepted
    active = host_provider_runtime.active_for_node(project, node)
    if active:
        return active | {
            "operation": "host-coding-provider",
            "status": "HOST_EXECUTION_REQUIRED",
            "host_request_created": True,
        }
    return request(project, node) | {"operation": "host-coding-provider"}
