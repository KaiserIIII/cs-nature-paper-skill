"""Host-neutral deterministic scaffolding and typed host handoff requests."""

from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path
from typing import Any

import provider_support as support

SCRIPT_DIR = str(Path(__file__).resolve().parents[1] / "scripts")
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import host_provider_runtime  # noqa: E402


PROVIDER_ID = "host-research"


def _brief(project: Path) -> dict[str, Any]:
    brief = support.read_json(project / "inputs" / "research_brief.json", {})
    question = str(brief.get("question", "")).strip()
    if not question:
        return {"status": "BLOCKED", "findings": ["research question is required"]}
    contract_path = support.state_dir(project) / "research_contract.json"
    contract = support.read_json(contract_path, {})
    contract["scientific_argument"] = {
        "stakeholder_problem": question,
        "phenomenon_or_artifact": brief.get("phenomenon", brief.get("outcome", "declared outcome")),
        "prior_knowledge": brief.get("prior_knowledge", "UNRESOLVED pending verified literature"),
        "gap": brief.get("gap", "The declared question requires observed project evidence."),
        "mechanism_or_model": brief.get("mechanism", "selected after method routing"),
        "target_population_and_scope": brief.get("scope", "declared project scope"),
        "contribution": brief.get("contribution", "evidence-bound answer to the declared question"),
        "downstream_boundary": brief.get("boundary", "no inference beyond observed inputs"),
        "questions_or_goals": [{"id": "RQ1", "text": question}],
        "falsifiers": list(brief.get("falsifiers", ["observed results contradict the proposed relation"])),
        "alternative_explanations": list(brief.get("alternative_explanations", ["unmeasured factors"])),
    }
    support.write(contract_path, contract)
    artifact = support.write(project / "artifacts" / "research_brief.json", brief | {"normalized": True})
    return support.handoff(project, PROVIDER_ID, "brief", [artifact], actions=["structured research question"])


def execute(project: Path, node: str) -> dict[str, Any]:
    if node == "brief":
        return _brief(project)
    brief = support.read_json(project / "inputs" / "research_brief.json", {})
    contract = support.read_json(support.state_dir(project) / "research_contract.json", {})
    artifacts = project / "artifacts"
    if node == "orientation":
        path = support.write(artifacts / "orientation.json", {
            "mode": "maximum-autonomy", "project": project.name,
            "inventory": sorted(path.relative_to(project).as_posix() for path in project.rglob("*") if path.is_file())[:500],
            "boundaries": ["no publication", "no implicit credentials", "no irreversible external writes"],
        })
    elif node in {"innovation", "prior_art_red_team", "feasibility"}:
        literature = support.read_json(artifacts / "literature.json", {})
        values = {
            "innovation": {
                "question": brief.get("question"), "closest_work": literature.get("closest_work", []),
                "novelty_status": literature.get("novelty_status", "CONDITIONAL"),
                "literature_gate_status": literature.get("literature_gate_status", "CONDITIONAL"),
                "remaining_uncertainty": literature.get("remaining_uncertainty", []),
            },
            "prior_art_red_team": {
                "attack": "The proposed contribution may be explained by the closest verified work.",
                "surviving_gap": brief.get("gap", "UNRESOLVED"), "status": "SCOPED",
            },
            "feasibility": {
                "decision": "GO", "available_data": brief.get("data_file"),
                "candidate_methods": brief.get("method_candidates", []), "cost": "bounded local execution",
                "risks": ["external validity is limited to the declared input and design"],
            },
        }
        filename = {"innovation": "innovation.json", "prior_art_red_team": "prior_art_report.json", "feasibility": "feasibility.json"}[node]
        path = support.write(artifacts / filename, values[node])
        if node == "feasibility":
            contract["feasibility"] = values[node]
            support.write(support.state_dir(project) / "research_contract.json", contract)
    elif node == "protocol_freeze":
        protocol = {
            "status": "frozen", "evidence_label": "FORMAL", "research_question": brief.get("question"),
            "data_file": brief.get("data_file"), "outcome": brief.get("outcome"),
            "candidate_methods": brief.get("method_candidates", []),
            "stopping_and_failure_rules": "fail closed on non-zero command, missing output, or checker failure",
            "phase_labels": ["DISCOVERY", "PILOT", "FORMAL", "EXPLORATORY_POST_HOC"],
        }
        contract["protocol"] = protocol
        support.write(support.state_dir(project) / "research_contract.json", contract)
        path = support.write(artifacts / "frozen_protocol.json", protocol)
    elif node == "evidence_update":
        analysis = support.read_json(artifacts / "analysis.json", {})
        claims_path = support.state_dir(project) / "claims.json"
        claims = support.read_json(claims_path, {})
        claim = {
            "id": "C1", "text": analysis.get("claim", "Observed results are limited to the declared inputs."),
            "type": "descriptive", "scope": brief.get("scope", "declared project scope"),
            "required_evidence": "formal command output plus independent analysis checker",
            "observed_evidence": analysis.get("evidence", []), "status": "SCOPED",
        }
        claims["claims"] = [claim]
        support.write(claims_path, claims)
        path = support.write(artifacts / "evidence_update.json", {"claims": [claim], "unsupported_claims_removed": True})
    elif node == "validation":
        required = ["formal_results.json", "analysis.json", "figure.svg", "figure_provenance.json", "manuscript.md"]
        missing = [name for name in required if not (artifacts / name).is_file()]
        path = support.write(artifacts / "validation_report.json", {"status": "PASS" if not missing else "FAIL", "missing": missing})
        if missing:
            return {"status": "FAIL", "findings": ["missing " + name for name in missing]}
    elif node == "venue_preflight":
        path = support.write(artifacts / "preflight_report.json", {"status": "PASS", "submission": "NOT_PERFORMED", "venue_rules": "author must select and verify final venue"})
    elif node == "artifact_package":
        entries = [{"path": item.relative_to(project).as_posix(), "sha256": support.digest(item), "bytes": item.stat().st_size} for item in sorted(artifacts.glob("*")) if item.is_file() and item.name != "package_manifest.json"]
        path = support.write(artifacts / "package_manifest.json", {"status": "PASS", "artifacts": entries, "reproduction_command": "see artifacts/formal_execution.json"})
    elif node == "author_handoff":
        path = support.write(artifacts / "author_handoff.json", {"status": "READY_FOR_SUBMISSION", "ordinary_author_prompts": 0, "external_actions_performed": [], "model_behavior_eval": "NOT_RUN"})
    else:
        return {"status": "BLOCKED", "findings": [f"unsupported host research node: {node}"]}
    return support.handoff(project, PROVIDER_ID, node, [path], uncertainties=["host output remains checker-gated"])


def request_host_capability(project: Path, node: str, capability: str, inputs: list[str], formal: bool) -> Path:
    request = {
        "task_id": f"{project.name}:{node}", "capability": capability,
        "purpose": f"produce a typed artifact for research graph node {node}", "formal": formal,
        "inputs": inputs, "constraints": ["use observed project evidence", "do not transition the graph"],
        "required_outputs": ["typed artifact", "claims", "uncertainties", "actions_taken"],
        "forbidden_claims": ["unsupported causality", "fabricated execution", "fabricated source"],
        "evidence_requirements": ["artifact hash", "tool or command record", "independent checker"],
        "budget": {"money": 0}, "permissions": {"external_write": False, "publish": False},
    }
    return support.write(support.state_dir(project) / "host_requests" / f"{node}.json", request)


def _request_inputs(project: Path) -> list[str]:
    """Expose only project artifacts as host inputs; state remains local audit data."""
    return [
        support.relative(project, path)
        for path in sorted(project.rglob("*"))
        if path.is_file() and ".research-state" not in path.parts
    ][:500]


def request(project: Path, node: str, capability: str) -> dict[str, Any]:
    inputs = _request_inputs(project)
    task_id = f"{project.name}:{node}:{hashlib.sha256(json.dumps(inputs).encode('utf-8')).hexdigest()[:12]}"
    value = {
        "task_id": task_id,
        "node": node,
        "capability": capability,
        "formal": True,
        "inputs": inputs,
        "constraints": [
            "use observed project evidence only",
            "do not transition the research graph",
            "return a typed artifact with explicit uncertainties",
        ],
        "required_outputs": ["typed artifact", "claims", "uncertainties", "actions_taken"],
        "evidence_requirements": ["artifact hash", "tool or command record", "independent checker"],
        "forbidden_claims": ["unsupported scientific truth", "fabricated execution", "fabricated source"],
        "permissions": {"local_read": True, "local_write": True, "execute": False, "network": False, "external_write": False},
        "budget": {"money": 0},
    }
    return host_provider_runtime.create_request(project, value) | {"host_request": value, "capability": capability}


def consume(project: Path, node: str, active: dict[str, Any]) -> dict[str, Any] | None:
    if active.get("status") != "ACCEPTED" or not isinstance(active.get("handoff"), dict):
        return None
    handoff = active["handoff"]
    artifacts = []
    for relative in handoff.get("artifacts", []):
        path = (project / str(relative)).resolve()
        try:
            path.relative_to(project.resolve())
        except ValueError:
            continue
        if path.is_file() and path.stat().st_size > 0:
            artifacts.append(path)
    if not artifacts:
        return {"status": "FAIL", "findings": ["accepted host handoff has no observed artifact"]}
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


def request_or_consume(project: Path, node: str, capability: str) -> dict[str, Any]:
    active = host_provider_runtime.active_for_node(project, node)
    if active and active.get("status") == "ACCEPTED":
        result = consume(project, node, active)
        if result is not None:
            return result
    if active:
        return active | {
            "operation": "host-research-provider",
            "status": "HOST_EXECUTION_REQUIRED",
            "host_request_created": True,
            "capability": capability,
        }
    return request(project, node, capability) | {"operation": "host-research-provider"}
