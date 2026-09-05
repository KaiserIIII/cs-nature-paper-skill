#!/usr/bin/env python3
"""Provider-driven orchestration adapter for v3.2 research graph nodes."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


SKILL_VERSION = "3.2.1"
ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ROOT / "providers"
for folder in (str(Path(__file__).resolve().parent), str(PROVIDERS)):
    if folder not in sys.path:
        sys.path.insert(0, folder)

import provider_runtime  # noqa: E402
import provider_support as support  # noqa: E402
import host_provider_runtime  # noqa: E402
import skill_discovery_provider  # noqa: E402
import host_research_provider  # noqa: E402
import literature_provider  # noqa: E402
import coding_provider  # noqa: E402
import analysis_provider  # noqa: E402
import writing_provider  # noqa: E402
import review_provider  # noqa: E402
import host_coding_provider  # noqa: E402


MAIN_SEQUENCE = (
    "orientation", "brief", "literature", "innovation", "prior_art_red_team", "feasibility",
    "pilot", "protocol_freeze", "implementation", "formal_experiment", "analysis", "evidence_update",
    "figures", "writing", "validation", "review", "revision", "venue_preflight",
    "artifact_package", "author_handoff",
)
NODE_CAPABILITIES = {
    "orientation": ["project-orientation"],
    "brief": ["research-question-structuring"],
    "literature": ["literature-discovery", "literature-retrieval", "literature-verification"],
    "innovation": ["novelty-analysis", "closest-work-analysis"],
    "prior_art_red_team": ["closest-work-analysis"],
    "feasibility": ["feasibility-analysis"],
    "pilot": ["baseline-feasibility", "experimental-design", "execution"],
    "protocol_freeze": ["experimental-design"],
    "implementation": ["software-implementation"],
    "formal_experiment": ["experiment-execution"],
    "analysis": ["statistical-analysis"],
    "evidence_update": ["artifact-validation"],
    "figures": ["scientific-visualization"],
    "writing": ["evidence-bound-writing"],
    "validation": ["artifact-validation"],
    "review": ["adversarial-review"],
    "revision": ["evidence-bound-revision"],
    "venue_preflight": ["artifact-validation"],
    "artifact_package": ["artifact-validation"],
    "author_handoff": ["artifact-validation"],
}
FORMAL_NODES = {"implementation", "formal_experiment", "analysis", "figures", "writing", "validation", "review", "revision", "artifact_package"}
# These nodes carry claims or decisions that cannot be discharged by the
# deterministic baseline providers.  They must be specialist-backed or remain
# explicitly blocked behind the host handoff lifecycle.
LOAD_BEARING_NODES = {
    "analysis", "figures", "writing", "review", "revision",
}
FULL_PAPER_WORKFLOW_VALUES = {"full", "full-paper", "fullpaper"}
SUBMISSION_TARGETED_WORKFLOW_VALUES = {
    "submission", "submission-targeted", "submission-target", "submissiontargeted",
}


def _normalise_workflow_value(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-").replace(" ", "-")


def _workflow_documents(project: Path) -> list[dict[str, Any]]:
    """Read workflow descriptors without requiring a user load-bearing list."""
    paths = (
        project / "inputs" / "research_brief.json",
        support.state_dir(project) / "project.json",
        support.state_dir(project) / "research_contract.json",
    )
    documents: list[dict[str, Any]] = []
    for path in paths:
        value = support.read_json(path, {})
        if not isinstance(value, dict):
            continue
        documents.append(value)
        # research_contract keeps workflow and venue fields under `project`;
        # inspect that nested record using the same detection rules.
        for key in ("project", "submission", "venue"):
            nested = value.get(key)
            if isinstance(nested, dict):
                documents.append(nested)
    return documents


def _is_formal_full_paper_workflow(project: Path) -> bool:
    """Return whether the project explicitly requests a formal paper workflow."""
    for document in _workflow_documents(project):
        if any(document.get(key) is True for key in ("formal_workflow", "submission_targeted", "submission_target")):
            return True
        if any(_normalise_workflow_value(document.get(key)) in {"true", "yes", "formal"} for key in ("formal_workflow", "submission_targeted", "submission_target")):
            return True
        if any(str(document.get(key, "")).strip() for key in ("target_venue", "target_journal", "target_track")):
            return True
        for key in ("workflow", "workflow_mode", "pipeline", "purpose", "mode", "automation_mode"):
            value = _normalise_workflow_value(document.get(key))
            if value in FULL_PAPER_WORKFLOW_VALUES | SUBMISSION_TARGETED_WORKFLOW_VALUES:
                return True
    return False


def load_bearing_nodes(project: Path) -> set[str]:
    """Resolve load-bearing nodes, auto-promoting core nodes for formal papers."""
    project = project.resolve()
    brief = support.read_json(project / "inputs" / "research_brief.json", {})
    contract = support.read_json(support.state_dir(project) / "research_contract.json", {})
    declared = brief.get("load_bearing_nodes", contract.get("load_bearing_nodes", []))
    if declared is True:
        resolved = set(LOAD_BEARING_NODES)
    elif isinstance(declared, list):
        resolved = {str(node) for node in declared}
    else:
        resolved = set()
    if _is_formal_full_paper_workflow(project):
        resolved.update(LOAD_BEARING_NODES)
    return resolved


def _is_load_bearing(project: Path, node: str) -> bool:
    return node in load_bearing_nodes(project)


def _recorded_host_context(project: Path) -> bool:
    """Allow deterministic post-processing only for checked E2E handoffs."""
    active = host_provider_runtime.active_for_node(project, "implementation")
    handoff = active.get("handoff") if isinstance(active, dict) else None
    return bool(
        active and active.get("status") == "ACCEPTED" and isinstance(handoff, dict)
        and str(handoff.get("provider_id", "")).startswith("recorded-")
    )


def _load_fixture():
    path = PROVIDERS / "native_fixture_provider.py"
    spec = importlib.util.spec_from_file_location("v32_native_fixture_provider", path)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    spec.loader.exec_module(module)
    return module


def _fixture_mode(project: Path) -> bool:
    brief = support.read_json(project / "inputs" / "research_brief.json", {})
    mode = support.read_json(support.state_dir(project) / "provider_mode.json", {})
    return brief.get("provider_mode") == "fixture" or mode.get("mode") == "fixture"


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


def _registry(project: Path) -> list[dict[str, Any]]:
    native_research_status = "QUALIFIED" if coding_provider.native_available(project) else "UNAVAILABLE"
    records = [
        provider_runtime.provider("research-runtime-provider", "NATIVE", [
            "project-orientation", "research-question-structuring", "novelty-analysis", "closest-work-analysis",
            "feasibility-analysis", "experimental-design", "artifact-validation",
        ], qualification="QUALIFIED", formal_eligible=True, quality_level="BASELINE", permissions=["local_read", "local_write"]),
        provider_runtime.provider("literature-provider", "WEB", [
            "literature-discovery", "literature-retrieval", "literature-verification",
        ], qualification="QUALIFIED", formal_eligible=False, permissions=["local_read"]),
        provider_runtime.provider("native-research-pilot", "NATIVE", [
            "baseline-feasibility",
        ], qualification="QUALIFIED", formal_eligible=True, permissions=["local_read", "local_write", "execute"]),
        provider_runtime.provider("native-research-baseline", "NATIVE", [
            "software-implementation",
        ], status=native_research_status, qualification="QUALIFIED", formal_eligible=True, permissions=["local_read", "local_write", "execute"]),
        provider_runtime.provider("deterministic-execution-provider", "NATIVE", [
            "experiment-execution",
        ], qualification="QUALIFIED", formal_eligible=True, permissions=["local_read", "local_write", "execute"]),
        provider_runtime.provider("host-coding-provider", "HOST_LLM", [
            "software-implementation",
        ], status="HOST_REQUEST_CAPABLE", qualification="HOST_REQUEST_CAPABLE", formal_eligible=False, permissions=["local_read", "local_write"]),
        provider_runtime.provider("host-research-provider", "HOST_LLM", [
            "novelty-analysis", "closest-work-analysis", "feasibility-analysis",
            "statistical-analysis", "scientific-visualization", "evidence-bound-writing",
            "evidence-bound-revision", "adversarial-review",
        ], status="HOST_REQUEST_CAPABLE", qualification="HOST_REQUEST_CAPABLE", formal_eligible=False, permissions=["local_read", "local_write"]),
        provider_runtime.provider("analysis-provider", "NATIVE", [
            "statistical-analysis", "scientific-visualization",
        ], qualification="QUALIFIED", formal_eligible=False, quality_level="BASELINE", permissions=["local_read", "local_write"]),
        provider_runtime.provider("writing-provider", "NATIVE", [
            "evidence-bound-writing", "evidence-bound-revision",
        ], qualification="QUALIFIED", formal_eligible=False, quality_level="BASELINE", permissions=["local_read", "local_write"]),
        provider_runtime.provider("review-provider", "NATIVE", ["adversarial-review"], qualification="QUALIFIED", formal_eligible=False, quality_level="BASELINE", permissions=["local_read", "local_write"]),
    ]
    state_path = support.state_dir(project) / "provider_registry.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    support.write(state_path, {"schema_version": 1, "skill_version": SKILL_VERSION, "providers": records})
    return records


def _permissions(project: Path) -> dict[str, bool]:
    policy = support.read_json(support.state_dir(project) / "autonomy_policy.json", {})
    return policy.get("permissions", {"local_read": True, "local_write": True, "execute": True, "network": False, "auto_hire": False})


def _invoke(project: Path, provider_id: str, node: str) -> dict[str, Any]:
    if provider_id == "literature-provider":
        return literature_provider.execute(project)
    if provider_id in {"native-research-pilot", "native-research-baseline", "deterministic-execution-provider"}:
        return coding_provider.execute(project, node)
    if provider_id == "analysis-provider":
        return analysis_provider.execute(project, node)
    if provider_id == "writing-provider":
        return writing_provider.execute(project, node)
    if provider_id == "review-provider":
        return review_provider.execute(project)
    return host_research_provider.execute(project, node)


def _anchor(project: Path, node: str, artifact: Path, provider_id: str) -> str:
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    anchor_id = f"EA-{node.upper().replace('_', '-')}-{digest[:12]}"
    ledger_path = support.state_dir(project) / "evidence_ledger.json"
    ledger = support.read_json(ledger_path, {})
    anchors = ledger.setdefault("anchors", [])
    anchors[:] = [item for item in anchors if item.get("anchor_id") != anchor_id]
    artifact_types = {
        "literature": "literature", "feasibility": "feasibility", "formal_experiment": "formal_output",
        "analysis": "analysis", "figures": "figure", "writing": "manuscript", "validation": "validation",
        "review": "review",
    }
    extra = {}
    if node == "literature":
        extra.update({"source_uri": support.relative(project, artifact), "exact_region": "complete typed registry"})
    elif node == "feasibility":
        extra["decision"] = "GO"
    elif node == "formal_experiment":
        extra["execution_record_id"] = "artifacts/formal_execution.json"
    anchors.append({
        "anchor_id": anchor_id, "claim_id": "C1", "result_id": f"R-{node.upper()}",
        "source_artifact": f"{support.relative(project, artifact)}#sha256={digest}", "source_sha256": digest,
        "exact_region": "complete typed artifact", "transformation": f"provider:{provider_id}; checker:deterministic-output-checker",
        "uncertainty": "bounded to recorded project inputs", "scope": "project research contract",
        "status": "OBSERVED", "provenance_level": "OBSERVED", "artifact_type": artifact_types.get(node, "provider_output"),
        "artifact_acquisition_record_id": f"provider:{provider_id}:{node}",
        **extra,
    })
    support.write(ledger_path, ledger)
    return anchor_id


def _register_artifacts(project: Path, node: str, result: dict[str, Any]) -> list[str]:
    manifest_path = support.state_dir(project) / "artifact_manifest.json"
    manifest = support.read_json(manifest_path, {})
    entries = manifest.setdefault("artifacts", [])
    evidence = []
    input_paths = [path for path in (project / "inputs").glob("*") if path.is_file()] if (project / "inputs").is_dir() else []
    for relative in result.get("artifacts", []):
        artifact = (project / str(relative)).resolve()
        evidence.append(_anchor(project, node, artifact, result.get("provider_id", "unknown")))
        freshness = provider_runtime.artifact_record(project, artifact, result.get("provider_id", "unknown"), result.get("provider_version", SKILL_VERSION), input_paths, [], command_or_tool=result.get("tool_calls", []))
        record = {
            "id": freshness["artifact_id"], "path": support.relative(project, artifact), "type": "provider_output",
            "sha256": support.digest(artifact), "created_by": f"provider:{result.get('provider_id')}:{node}",
            "status": "OBSERVED", "freshness": freshness,
        }
        entries[:] = [item for item in entries if item.get("path") != record["path"]]
        entries.append(record)
    support.write(manifest_path, manifest)
    return evidence


def validate_output(project: Path, node: str, result: dict[str, Any]) -> dict[str, Any]:
    findings = []
    if result.get("status") != "PASS":
        findings.extend(result.get("findings", ["provider did not return PASS"]))
    required = provider_runtime.HANDOFF_FIELDS
    if required - set(result):
        findings.append("typed provider handoff is incomplete")
    artifacts = result.get("artifacts", [])
    if not artifacts:
        findings.append("provider emitted no artifact")
    for relative in artifacts:
        path = (project / str(relative)).resolve()
        try:
            path.relative_to(project.resolve())
        except ValueError:
            findings.append(f"artifact escapes project: {relative}")
            continue
        if not path.is_file() or path.stat().st_size == 0:
            findings.append(f"artifact is missing or empty: {relative}")
    if node == "formal_experiment" and result.get("execution_record", {}).get("status") != "PASS":
        findings.append("formal work lacks a passing observed execution record")
    if node == "literature" and any(field not in result for field in ("sources", "retrieval_records", "verified_relations")):
        findings.append("literature contract is incomplete")
    return {"operation": "validate-provider-output", "status": "PASS" if not findings else "FAIL", "findings": findings}


def execute_node(project: Path, node: str) -> dict[str, Any]:
    project = project.resolve()
    if node not in NODE_CAPABILITIES:
        return {"operation": "execute-node", "node": node, "status": "BLOCKED", "findings": ["no registered capability mapping"]}
    if _fixture_mode(project):
        return _load_fixture().execute_node(project, node)
    permissions = _permissions(project)
    capability = NODE_CAPABILITIES[node][0]
    recorded_host = _recorded_host_context(project)
    # Scientific escalation is opt-in for ordinary deterministic examples,
    # while an explicit load-bearing declaration (or a specialist-triggering
    # method in the project brief) still routes through the Host lifecycle.
    load_bearing = _is_load_bearing(project, node) and not recorded_host
    brief = support.read_json(project / "inputs" / "research_brief.json", {})
    task = {
        "node": node,
        "project": project.name,
        "load_bearing": load_bearing,
        "discovery_attempted": _discovery_attempted(project, node, capability),
        "purpose": brief.get("question", ""),
        "description": brief.get("description", ""),
        "method": " ".join(map(str, brief.get("method_candidates", []))),
    }
    formal = (node in FORMAL_NODES and (node not in LOAD_BEARING_NODES or load_bearing)) and not recorded_host
    specialist_discovery = None
    registry = _registry(project)
    route = provider_runtime.resolve_provider(
        capability,
        task,
        formal,
        "LOW",
        permissions,
        registry,
    )
    if route.get("status") == "SPECIALIST_DISCOVERY":
        specialist_discovery = _specialist_discovery(project, node, capability)
        task["discovery_attempted"] = True
        # A discovery result is metadata only. Resolve again so an existing
        # request-capable Host becomes the explicit fallback after discovery.
        route = provider_runtime.resolve_provider(
            capability,
            task,
            formal,
            "LOW",
            permissions,
            registry,
        ) | {
            "specialist_discovery": specialist_discovery,
            "discovery_attempted": True,
        }
    if specialist_discovery is not None:
        route = route | {
            "specialist_discovery": specialist_discovery,
            "discovery_attempted": True,
        }
    if route["status"] == "HOST_EXECUTION_REQUIRED" and route.get("provider", {}).get("provider_id") == "host-coding-provider":
        selected = route["provider"]
        result = host_coding_provider.request_or_consume(project, node)
        if result.get("status") == "HOST_EXECUTION_REQUIRED":
            return result | {
                "operation": "execute-node", "node": node, "capability": capability,
                "provider_route": route, "host_request_created": True,
                "specialist_discovery": specialist_discovery,
            }
    elif route["status"] == "HOST_EXECUTION_REQUIRED" and route.get("provider", {}).get("provider_id") == "host-research-provider":
        selected = route["provider"]
        result = host_research_provider.request_or_consume(project, node, capability)
        if result.get("status") == "HOST_EXECUTION_REQUIRED":
            return result | {
                "operation": "execute-node", "node": node, "capability": capability,
                "provider_route": route, "host_request_created": True,
                "specialist_discovery": specialist_discovery,
            }
    elif route["status"] != "PASS":
        return {"operation": "execute-node", "node": node, "status": route["status"], "findings": [f"provider route: {route['status']}"], "provider_route": route}
    else:
        selected = route["provider"]
        try:
            result = _invoke(project, selected["provider_id"], node)
        except Exception as exc:
            return {"operation": "execute-node", "node": node, "status": "FAIL", "findings": [f"{type(exc).__name__}: {exc}"], "failure_signature": f"{node}:{type(exc).__name__}:{exc}"}
    check = validate_output(project, node, result)
    if check["status"] != "PASS":
        return result | {"operation": "execute-node", "node": node, "status": "FAIL", "findings": check["findings"], "output_validation": check, "provider_route": route, "failure_signature": f"{node}:output-contract"}
    evidence = _register_artifacts(project, node, result)
    host_request = provider_runtime.host_request(
        task_id=f"{project.name}:{node}", capability=capability, purpose=f"complete graph node {node}", formal=node in FORMAL_NODES,
        inputs=result.get("artifacts", []), constraints=["provider cannot transition graph"], required_outputs=["typed artifact"],
        forbidden_claims=["unsupported scientific truth"], evidence_requirements=["artifact hash", "checker"], budget={"money": 0}, permissions=permissions,
    )
    handoff_check = provider_runtime.check_host_handoff(host_request, result, producer_id=f"{selected['provider_id']}:produce", checker_id="deterministic-output-checker:check")
    if handoff_check["status"] != "PASS":
        return result | {"operation": "execute-node", "node": node, "status": "FAIL", "findings": handoff_check["findings"], "checker": handoff_check}
    return result | {
        "operation": "execute-node", "node": node, "status": "PASS", "evidence": evidence,
        "actions": result.get("actions_taken", []), "output_validation": check, "checker": handoff_check,
        "provider_route": route, "specialist_discovery": specialist_discovery,
    }
