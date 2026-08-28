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
import competition_modeling_provider  # noqa: E402
import competition_coding_provider  # noqa: E402
import competition_analysis_provider  # noqa: E402
import competition_writing_provider  # noqa: E402


SKILL_VERSION = "3.2.0"
NODE_PROVIDER = {
    "contest_intake": ("competition-modeling-provider", "competition-intake"),
    "problem_decomposition": ("competition-modeling-provider", "question-decomposition"),
    "problem_selection": ("competition-modeling-provider", "problem-selection"),
    "assumptions": ("competition-modeling-provider", "mathematical-modeling"),
    "method_candidates": ("competition-modeling-provider", "mathematical-modeling"),
    "minimal_viable_model": ("competition-coding-provider", "code-generation"),
    "pilot_solve": ("competition-coding-provider", "execution"),
    "model_validation": ("competition-analysis-provider", "model-validation"),
    "formal_solve": ("competition-coding-provider", "experiment-execution"),
    "sensitivity_robustness": ("competition-analysis-provider", "sensitivity-analysis"),
    "model_improvement": ("competition-analysis-provider", "model-validation"),
    "visualization": ("competition-analysis-provider", "scientific-visualization"),
    "paper_draft": ("competition-writing-provider", "evidence-bound-writing"),
    "competition_review": ("competition-writing-provider", "adversarial-review"),
    "revision": ("competition-writing-provider", "evidence-bound-revision"),
    "submission_preflight": ("competition-writing-provider", "artifact-validation"),
}
FORMAL_NODES = {"minimal_viable_model", "pilot_solve", "model_validation", "formal_solve", "sensitivity_robustness", "visualization", "paper_draft", "competition_review", "revision", "submission_preflight"}


def _input(project: Path) -> dict[str, Any]:
    state = support.state_dir(project) / "competition_input.json"
    return support.read_json(state if state.is_file() else project / "competition_input.json", {})


def _fixture_mode(project: Path) -> bool:
    return _input(project).get("provider_mode") == "fixture"


def _fixture():
    path = PROVIDERS / "competition_fixture_provider.py"
    spec = importlib.util.spec_from_file_location("v32_competition_fixture_provider", path)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    spec.loader.exec_module(module)
    return module


def _providers() -> list[dict[str, Any]]:
    return [
        provider_runtime.provider("competition-modeling-provider", "NATIVE", ["competition-intake", "question-decomposition", "problem-selection", "mathematical-modeling"], qualification="QUALIFIED", formal_eligible=True, permissions=["local_read", "local_write"]),
        provider_runtime.provider("competition-coding-provider", "NATIVE", ["code-generation", "execution", "experiment-execution"], qualification="QUALIFIED", formal_eligible=True, permissions=["local_read", "local_write", "execute"]),
        provider_runtime.provider("competition-analysis-provider", "NATIVE", ["model-validation", "sensitivity-analysis", "scientific-visualization"], qualification="QUALIFIED", formal_eligible=True, permissions=["local_read", "local_write"]),
        provider_runtime.provider("competition-writing-provider", "HOST_LLM", ["evidence-bound-writing", "adversarial-review", "evidence-bound-revision", "artifact-validation"], qualification="QUALIFIED", formal_eligible=True, permissions=["local_read", "local_write"]),
    ]


def _invoke(project: Path, provider_id: str, node: str) -> dict[str, Any]:
    if provider_id == "competition-modeling-provider":
        return competition_modeling_provider.execute(project, node)
    if provider_id == "competition-coding-provider":
        return competition_coding_provider.execute(project, node)
    if provider_id == "competition-analysis-provider":
        return competition_analysis_provider.execute(project, node)
    return competition_writing_provider.execute(project, node)


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
    registry = _providers()
    support.write(support.state_dir(project) / "provider_registry.json", {"schema_version": 1, "skill_version": SKILL_VERSION, "providers": registry})
    entry = NODE_PROVIDER.get(node_id)
    if entry is None:
        return {"operation": "competition-execute-node", "status": "FAIL", "node": node_id, "findings": ["no provider capability mapping"]}
    expected_provider, capability = entry
    policy = support.read_json(support.state_dir(project) / "autonomy_policy.json", {})
    permissions = policy.get("permissions", {"local_read": True, "local_write": True, "execute": True})
    route = provider_runtime.resolve_provider(capability, {"node": node_id}, node_id in FORMAL_NODES, "LOW", permissions, registry)
    if route.get("status") != "PASS" or route["provider"]["provider_id"] != expected_provider:
        return {"operation": "competition-execute-node", "status": route.get("status", "FAIL"), "node": node_id, "findings": ["provider route did not resolve the required capability"], "provider_route": route}
    try:
        result = _invoke(project, expected_provider, node_id)
    except Exception as exc:
        return {"operation": "competition-execute-node", "status": "FAIL", "node": node_id, "findings": [f"{type(exc).__name__}: {exc}"]}
    check = _validate(project, result)
    if check["status"] != "PASS":
        return result | {"operation": "competition-execute-node", "status": "FAIL", "node": node_id, "findings": check["findings"], "checker": check, "provider_route": route}
    evidence, summary = _register(project, node_id, result)
    artifacts = [support.relative(project, summary)] + list(result["artifacts"])
    return result | {"operation": "competition-execute-node", "status": "PASS", "node": node_id, "artifacts": artifacts, "evidence": evidence, "checker": {"status": "PASS", "producer": expected_provider, "checker": "deterministic-output-checker"}, "provider_route": route}
