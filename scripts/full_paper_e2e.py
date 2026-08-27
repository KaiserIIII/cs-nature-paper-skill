#!/usr/bin/env python3
"""Run a deterministic, public synthetic full-paper harness self-test."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SKILL_VERSION = "3.2.0"
WORKFLOW = [
    "brief",
    "literature_identity",
    "literature_retrieval",
    "claim_relation",
    "innovation",
    "feasibility",
    "protocol_freeze",
    "implementation",
    "formal_experiment",
    "analysis",
    "figures_table",
    "writing",
    "validation",
    "review",
    "artifact_package",
    "completion_contract",
]


def _load(name: str):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("v32_e2e_" + name, path)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    spec.loader.exec_module(module)
    return module


state_runtime = _load("research_state")
anchor_runtime = _load("evidence_anchor")
graph_runtime = _load("research_graph")
literature_runtime = _load("literature_runtime")
autonomy = _load("autonomy")
completion_runtime = _load("completion_contract")


def _commit() -> str:
    try:
        return subprocess.run(["git", "-C", str(Path(__file__).resolve().parents[1]), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        path.write_text(value, encoding="utf-8")
    else:
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _sanitize(value: Any, private_root: Path) -> Any:
    """Remove temporary absolute paths before a result crosses the public boundary."""
    if isinstance(value, str):
        return value.replace(str(private_root), "<TEMP_PROJECT>")
    if isinstance(value, list):
        return [_sanitize(item, private_root) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize(item, private_root) for key, item in value.items()}
    return value


def _fill_contract(project: Path, anchor_id: str) -> None:
    state = project / ".research-state"
    contract_path = state / "research_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["scientific_argument"].update({
        "stakeholder_problem": "Synthetic fixture reproducibility",
        "phenomenon_or_artifact": "A deterministic local repair command",
        "prior_knowledge": "A command can be checked through output hashes",
        "gap": "The harness needs one end-to-end provenance contract",
        "mechanism_or_model": "Every stage emits a bounded artifact record",
        "target_population_and_scope": "Public synthetic fixture only",
        "contribution": "A deterministic evidence-bound workflow harness",
        "downstream_boundary": "No publication, venue, or scientific generalization",
        "questions_or_goals": [{"id": "RQ1", "text": "Does the fixture preserve evidence provenance?"}],
        "falsifiers": ["missing output provenance"],
        "alternative_explanations": ["filesystem timestamp anomaly"],
    })
    contract["feasibility"] = {"decision": "GO", "resource_inventory": "stdlib and public fixture", "cost": "bounded local execution", "risks": ["synthetic scope"], "lower_resource_option": "skip external model"}
    contract["protocol"].update({
        "status": "frozen",
        "evidence_label": "FORMAL",
        "units": "one fixture run",
        "sampling_frame": "one public synthetic fixture",
        "outcomes": ["output hash"],
        "estimands": ["exact output identity"],
        "denominators": ["one run"],
        "missingness_and_exclusions": "none",
        "clustering_and_dependence": "none",
        "repetition_rationale": "determinism check",
        "multiplicity": "none",
        "stopping_and_failure_rules": "fail on missing or stale output",
        "frozen_inputs": ["public synthetic fixture"],
    })
    contract_path.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    claims_path = state / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"] = [{"id": "C1", "text": "The fixture preserves output provenance.", "type": "descriptive", "scope": "public synthetic fixture only", "required_evidence": "observed execution output", "observed_evidence": [anchor_id], "status": "SCOPED"}]
    claims_path.write_text(json.dumps(claims, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _append_anchor(project: Path, execution: dict[str, Any], output: Path) -> dict[str, Any]:
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    anchor = {
        "anchor_id": "EA-V32-001",
        "claim_id": "C1",
        "result_id": "R-V32-001",
        "source_artifact": f"artifacts/execution.txt#sha256={digest}",
        "exact_region": "line 1",
        "transformation": "identity",
        "provenance_level": "OBSERVED",
        "execution_record_id": "artifacts/execution_record.json",
        "command": execution["command"],
        "cwd": execution["cwd"],
        "exit_status": execution["exit_status"],
        "uncertainty": "bounded synthetic fixture",
        "scope": "public synthetic fixture",
        "status": "OBSERVED",
        "artifact_type": "formal_output",
    }
    ledger_path = project / ".research-state" / "evidence_ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger.setdefault("anchors", []).append(anchor)
    ledger_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return anchor


def _advance_graph(project: Path, evidence: str) -> None:
    sequence = [
        "brief", "literature", "innovation", "prior_art_red_team", "feasibility", "pilot",
        "protocol_freeze", "implementation", "formal_experiment", "analysis", "evidence_update",
        "figures", "writing", "validation", "review", "revision", "venue_preflight", "artifact_package", "author_handoff",
    ]
    for node_id in sequence:
        current = next(item for item in graph_runtime.load_graph(project)[1]["nodes"] if item.get("id") == node_id)
        if current.get("status") in {"PASS", "CONDITIONAL"}:
            continue
        graph_runtime.transition(project, node_id, "PASS", "deterministic public fixture stage", "test", evidence)


def run(output: Path | None = None, *, root: Path | None = None) -> dict[str, Any]:
    base = (root or Path(__file__).resolve().parents[1]).resolve()
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".v32-e2e-", dir=str(base)) as temporary:
        project = Path(temporary)
        state_runtime.init_state(project, "engineering-system", "maximum-autonomy", "systems")
        fixture = project / "fixture.py"
        _write(fixture, "from pathlib import Path\nPath('artifacts/execution.txt').parent.mkdir(parents=True, exist_ok=True)\nPath('artifacts/execution.txt').write_text('deterministic fixture output\\n', encoding='utf-8')\n")
        execution_path = project / "artifacts" / "execution_record.json"
        output_artifact = project / "artifacts" / "execution.txt"
        execution = anchor_runtime.execution_record(execution_path, [sys.executable, str(fixture)], cwd=project, output_paths=[output_artifact], environment={"network": False, "fixture": "public-v1"})
        if execution.get("status") != "PASS":
            raise RuntimeError("fixture command did not produce a valid observed output")
        registry = project / "literature.json"
        _write(registry, {"schema_version": 3, "skill_version": "3.1.1", "sources": [], "retrieval_records": []})
        source = project / "source.txt"
        _write(source, "A public synthetic source region.\n")
        literature_runtime.verify_identity(registry, "S1", {"title": "Synthetic fixture", "authors": ["Harness"], "year": 2026, "venue": "Local", "stable_identifier": "fixture:v32", "inspection_actor": "identity-checker"})
        retrieval = literature_runtime.record_retrieval(registry, "S1", source, retrieval_method="local-open", source_uri="fixture://v32-source", inspection_actor="retriever", retrieved_utc="2026-08-28T00:00:00Z")
        relation = literature_runtime.verify_claim(registry, "S1", "C1", "SUPPORTS", "line 1", retrieval_record_id=retrieval["retrieval_id"], source_uri="fixture://v32-source", inspection_actor="inspector", checker="independent-checker")
        anchor = _append_anchor(project, execution, output_artifact)
        _fill_contract(project, anchor["anchor_id"])
        policy_path = project / ".research-state" / "autonomy_policy.json"
        policy = autonomy.load_policy(policy_path)
        autonomy.append_audit(project / ".research-state" / ".autonomy-audit.jsonl", "full-paper-e2e", {"fixture": "public-v1", "relation": relation["verification_status"]}, actor="e2e", decision="PASS", utc="2026-08-28T00:00:00Z")
        _advance_graph(project, anchor["anchor_id"])
        for name, value in {
            "figure_table.json": {"figure": "source-data-bound", "table": "source-data-bound", "uncertainty": "bounded synthetic fixture"},
            "manuscript.md": "# Synthetic fixture manuscript\n\nThe output is scoped to the public fixture.\n",
            "package_manifest.json": {"artifacts": ["execution.txt", "figure_table.json", "manuscript.md"], "public_boundary": "synthetic fixture only"},
        }.items():
            _write(project / "artifacts" / name, value)
        skeleton = {"status": "PASS", "evaluation_class": "HARNESS_SELF_TEST", "model_behavior": "NOT_RUN", "skill_commit": _commit(), "completion": {"status": "PASS"}}
        e2e_path = project / "e2e-result.json"
        _write(e2e_path, skeleton)
        completion = completion_runtime.evaluate(project, e2e_result=e2e_path)
        result = {
            "operation": "full-paper-e2e",
            "skill_version": SKILL_VERSION,
            "status": "PASS" if completion["status"] == "PASS" and execution["status"] == "PASS" and relation["verification_status"] == "CLAIM_RELATION_VERIFIED" else "FAIL",
            "evaluation_class": "HARNESS_SELF_TEST",
            "model_behavior": "NOT_RUN",
            "skill_commit": _commit(),
            "workflow": WORKFLOW,
            "anchor_count": 1,
            "execution_record": {"status": execution["status"], "exit_status": execution["exit_status"], "outputs": execution["outputs"]},
            "literature": {"identity": "IDENTITY_VERIFIED", "retrieval": retrieval["retrieval_id"], "claim_relation": relation["verification_status"]},
            "artifacts": {name: "sha256:" + hashlib.sha256((project / "artifacts" / name).read_bytes()).hexdigest() for name in ("execution.txt", "figure_table.json", "manuscript.md", "package_manifest.json")},
            "completion": _sanitize(completion, project),
            "privacy": "synthetic temporary project; no private paths in result",
        }
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return result


def validate(result: dict[str, Any], root: Path) -> dict[str, Any]:
    findings: list[str] = []
    if result.get("status") != "PASS": findings.append("e2e status is not PASS")
    if result.get("evaluation_class") != "HARNESS_SELF_TEST": findings.append("evaluation_class must be HARNESS_SELF_TEST")
    if result.get("model_behavior") != "NOT_RUN": findings.append("model_behavior must remain NOT_RUN")
    if result.get("skill_commit") != _commit(): findings.append("skill_commit is stale")
    if not isinstance(result.get("workflow"), list) or result["workflow"] != WORKFLOW: findings.append("workflow is not the deterministic full-paper sequence")
    return {"operation": "validate-full-paper-e2e", "status": "PASS" if not findings else "FAIL", "findings": findings}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--root", type=Path)
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    result = run(args.output, root=args.root)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result.get("status") == "PASS" else 1)
