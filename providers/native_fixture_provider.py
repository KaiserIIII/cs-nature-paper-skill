#!/usr/bin/env python3
"""Deterministic research fixture provider retained only for harness tests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import py_compile
import shutil
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


SKILL_VERSION = "3.2.0"
MAIN_SEQUENCE = (
    "orientation",
    "brief",
    "literature",
    "innovation",
    "prior_art_red_team",
    "feasibility",
    "pilot",
    "protocol_freeze",
    "implementation",
    "formal_experiment",
    "analysis",
    "evidence_update",
    "figures",
    "writing",
    "validation",
    "review",
    "revision",
    "venue_preflight",
    "artifact_package",
    "author_handoff",
)


def _load(name: str):
    path = Path(__file__).resolve().parents[1] / "scripts" / (name + ".py")
    spec = importlib.util.spec_from_file_location("v32_executor_" + name, path)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    spec.loader.exec_module(module)
    return module


anchor_runtime = _load("evidence_anchor")


def _state(project: Path) -> Path:
    project = project.resolve()
    for name in (".research-state-v31", ".research-state-v3", ".research-state"):
        candidate = project / name
        if candidate.exists():
            return candidate
    return project / ".research-state"


def _read(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        path.write_text(value, encoding="utf-8")
    else:
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _relative(project: Path, path: Path) -> str:
    return path.resolve().relative_to(project.resolve()).as_posix()


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _anchor(
    project: Path,
    node: str,
    artifact: Path,
    artifact_type: str,
    *,
    provenance: str = "OBSERVED",
    extra: dict[str, Any] | None = None,
) -> str:
    digest = _hash(artifact)
    anchor_id = f"EA-{node.upper().replace('_', '-')}-{digest[:12]}"
    value: dict[str, Any] = {
        "anchor_id": anchor_id,
        "claim_id": "C1",
        "result_id": f"R-{node.upper()}",
        "source_artifact": f"{_relative(project, artifact)}#sha256={digest}",
        "source_sha256": digest,
        "exact_region": "line 1",
        "transformation": "identity or deterministic node transform",
        "uncertainty": "bounded to recorded inputs and synthetic fixture when used by E2E",
        "scope": "project research contract",
        "status": provenance,
        "provenance_level": provenance,
        "artifact_type": artifact_type,
        "artifact_acquisition_record_id": f"director:{node}",
    }
    value.update(extra or {})
    ledger_path = _state(project) / "evidence_ledger.json"
    ledger = _read(ledger_path, {})
    anchors = ledger.setdefault("anchors", [])
    anchors[:] = [item for item in anchors if item.get("anchor_id") != anchor_id]
    anchors.append(value)
    _write(ledger_path, ledger)
    return anchor_id


def _result(project: Path, node: str, artifact: Path, anchor_id: str, **extra: Any) -> dict[str, Any]:
    value = {
        "operation": "execute-node",
        "node": node,
        "status": "PASS",
        "artifacts": [_relative(project, artifact)],
        "evidence": [anchor_id],
        "actions": [],
    }
    value.update(extra)
    return value


def _brief(project: Path) -> dict[str, Any]:
    source = _read(project / "inputs" / "research_brief.json", {})
    if not isinstance(source, dict) or not source.get("question"):
        return {"status": "BLOCKED", "node": "brief", "findings": ["inputs/research_brief.json with a research question is required"]}
    contract_path = _state(project) / "research_contract.json"
    contract = _read(contract_path, {})
    question = str(source["question"])
    scope = str(source.get("scope") or "declared project scope")
    argument = contract.setdefault("scientific_argument", {})
    argument.update({
        "stakeholder_problem": question,
        "phenomenon_or_artifact": source.get("phenomenon", "deterministic research artifact provenance"),
        "prior_knowledge": source.get("prior_knowledge", "Recorded commands can be bound to content-addressed outputs."),
        "gap": source.get("gap", "End-to-end orchestration must prove rather than assert artifact production."),
        "mechanism_or_model": source.get("mechanism", "executor outputs are checked before graph transitions"),
        "target_population_and_scope": scope,
        "contribution": source.get("contribution", "an evidence-bound autonomous research workflow"),
        "downstream_boundary": source.get("boundary", "no claim beyond the recorded project inputs"),
        "questions_or_goals": [{"id": "RQ1", "text": question}],
        "falsifiers": ["missing or stale execution output"],
        "alternative_explanations": ["an artifact predated the claimed execution"],
    })
    _write(contract_path, contract)
    artifact = project / "artifacts" / "research_brief.json"
    _write(artifact, source | {"normalized": True})
    return _result(project, "brief", artifact, _anchor(project, "brief", artifact, "brief"))


def _orientation(project: Path) -> dict[str, Any]:
    artifact = project / "artifacts" / "orientation.json"
    _write(artifact, {"mode": "maximum-autonomy", "project": project.name, "boundaries": ["no publication", "no credentials", "no irreversible external writes"]})
    return _result(project, "orientation", artifact, _anchor(project, "orientation", artifact, "orientation"))


def _literature(project: Path) -> dict[str, Any]:
    source = project / "inputs" / "literature_source.txt"
    brief = _read(project / "inputs" / "research_brief.json", {})
    if not source.is_file() or not source.read_text(encoding="utf-8").strip():
        return {"status": "BLOCKED", "node": "literature", "findings": ["no retrievable literature source is available"]}
    digest = _hash(source)
    artifact = project / "artifacts" / "literature.json"
    value = {
        "queries": [brief.get("question", "project research question")],
        "sources": [{"id": "S1", "title": brief.get("source_title", "Project-provided source"), "stable_identifier": f"sha256:{digest}", "identity": "VERIFIED"}],
        "retrieval_records": [{"id": "RR1", "source": "inputs/literature_source.txt", "sha256": digest, "method": "project-local"}],
        "verified_relations": [{"source_id": "S1", "claim_id": "C1", "relation": "SUPPORTS", "exact_region": "line 1"}],
        "closest_work": brief.get("source_title", "Project-provided source"),
        "remaining_gap": "normal runtime execution and independent checking",
    }
    _write(artifact, value)
    registry = _read(_state(project) / "literature_registry.json", {})
    registry.update({"sources": value["sources"], "retrieval_records": value["retrieval_records"], "claim_relations": value["verified_relations"]})
    _write(_state(project) / "literature_registry.json", registry)
    anchor_id = _anchor(project, "literature", artifact, "literature", extra={"source_uri": "inputs/literature_source.txt", "exact_region": "line 1"})
    return _result(project, "literature", artifact, anchor_id, sources=value["sources"], retrieval_records=value["retrieval_records"], verified_relations=value["verified_relations"])


def _innovation(project: Path) -> dict[str, Any]:
    literature = _read(project / "artifacts" / "literature.json", {})
    artifact = project / "artifacts" / "innovation.json"
    value = {
        "closest_work": literature.get("closest_work"),
        "novelty_attack": "A graph transition alone is not evidence of completed work.",
        "refined_research_question": _read(project / "inputs" / "research_brief.json", {}).get("question"),
        "alternative_explanation": "pre-existing outputs could be mistaken for executed results",
        "contribution_boundary": "orchestration integrity, not general scientific validity",
    }
    _write(artifact, value)
    return _result(project, "innovation", artifact, _anchor(project, "innovation", artifact, "decision"))


def _prior_art(project: Path) -> dict[str, Any]:
    innovation = _read(project / "artifacts" / "innovation.json", {})
    artifact = project / "artifacts" / "prior_art_report.json"
    _write(artifact, {"attack": innovation.get("novelty_attack"), "surviving_gap": innovation.get("contribution_boundary"), "status": "SCOPED"})
    return _result(project, "prior_art_red_team", artifact, _anchor(project, "prior_art_red_team", artifact, "review"))


def _feasibility(project: Path) -> dict[str, Any]:
    contract_path = _state(project) / "research_contract.json"
    contract = _read(contract_path, {})
    contract["feasibility"] = {
        "decision": "GO",
        "resource_inventory": "Python standard library and project-local public fixture",
        "cost": "bounded local execution; no payment",
        "risks": ["synthetic E2E does not establish real-world model behavior"],
        "lower_resource_option": "retain deterministic fixture and skip model-backed evaluation",
    }
    _write(contract_path, contract)
    risks_path = _state(project) / "risks.json"
    risks = _read(risks_path, {})
    risks["risks"] = [{
        "id": "RISK-1",
        "category": "scientific",
        "description": "The deterministic fixture does not establish external scientific or model-behavior validity.",
        "severity": "MAJOR",
        "trigger": "a claim extends beyond the project fixture",
        "owner": "director",
        "mitigation": "scope all claims and keep MODEL_BEHAVIOR_EVAL as NOT_RUN",
        "residual_risk": "external validity remains untested",
        "status": "RESIDUAL_RISK_DOCUMENTED",
    }]
    _write(risks_path, risks)
    artifact = project / "artifacts" / "feasibility.json"
    _write(artifact, contract["feasibility"])
    anchor_id = _anchor(project, "feasibility", artifact, "feasibility", extra={"decision": "GO"})
    return _result(project, "feasibility", artifact, anchor_id)


def _pilot(project: Path) -> dict[str, Any]:
    artifact = project / "artifacts" / "pilot_results.json"
    _write(artifact, {"runs": 1, "values": [1.0], "status": "PASS", "purpose": "pipeline feasibility only"})
    return _result(project, "pilot", artifact, _anchor(project, "pilot", artifact, "experiment"))


def _protocol(project: Path) -> dict[str, Any]:
    contract_path = _state(project) / "research_contract.json"
    contract = _read(contract_path, {})
    contract.setdefault("protocol", {}).update({
        "status": "frozen",
        "evidence_label": "FORMAL",
        "units": "deterministic fixture runs",
        "sampling_frame": "project-provided public fixture",
        "outcomes": ["recorded numeric result and output hash"],
        "estimands": ["mean recorded value"],
        "denominators": ["three deterministic repetitions"],
        "missingness_and_exclusions": "fail closed on missing output",
        "clustering_and_dependence": "repetitions are deterministic and not treated as independent population samples",
        "repetition_rationale": "verify deterministic execution",
        "multiplicity": "one prespecified outcome",
        "stopping_and_failure_rules": "stop on non-zero exit or absent declared output",
        "frozen_inputs": ["inputs/research_brief.json", "inputs/literature_source.txt"],
        "phase_labels": ["DISCOVERY", "PILOT", "FORMAL", "EXPLORATORY_POST_HOC"],
    })
    _write(contract_path, contract)
    artifact = project / "artifacts" / "frozen_protocol.json"
    _write(artifact, contract["protocol"])
    return _result(project, "protocol_freeze", artifact, _anchor(project, "protocol_freeze", artifact, "protocol"))


def _implementation(project: Path) -> dict[str, Any]:
    path = project / "experiments" / "run_experiment.py"
    actions: list[str] = []
    if path.exists():
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError:
            actions.append("repaired_invalid_implementation")
    code = (
        "import json,sys\n"
        "from pathlib import Path\n"
        "values=[1.0,1.0,1.0]\n"
        "Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)\n"
        "Path(sys.argv[1]).write_text(json.dumps({'values':values,'mean':sum(values)/len(values),'runs':len(values)}), encoding='utf-8')\n"
    )
    previous = path.read_text(encoding="utf-8") if path.exists() else None
    _write(path, code)
    if previous != code and not actions:
        actions.append("created_or_updated_implementation")
    py_compile.compile(str(path), doraise=True)
    test = subprocess.run([sys.executable, "-m", "py_compile", str(path)], cwd=str(project), capture_output=True, text=True, check=False)
    if test.returncode != 0:
        return {"status": "FAIL", "node": "implementation", "findings": [test.stderr]}
    anchor_id = _anchor(project, "implementation", path, "implementation")
    return _result(project, "implementation", path, anchor_id, actions=actions, changed_files=[_relative(project, path)], minimal_test={"exit_status": test.returncode})


def _formal_experiment(project: Path) -> dict[str, Any]:
    implementation = project / "experiments" / "run_experiment.py"
    output = project / "artifacts" / "formal_results.json"
    record_path = project / "artifacts" / "formal_execution.json"
    if output.exists():
        output.unlink()
    execution = anchor_runtime.execution_record(
        record_path,
        [sys.executable, str(implementation), str(output)],
        cwd=project,
        input_paths=[implementation, project / "artifacts" / "frozen_protocol.json"],
        output_paths=[output],
        environment={"python": sys.version.split()[0], "network": False, "phase": "FORMAL"},
    )
    if execution.get("status") != "PASS":
        return {"status": "FAIL", "node": "formal_experiment", "findings": execution.get("findings", []), "failure_signature": f"formal:{execution.get('exit_status')}"}
    digest = _hash(output)
    anchor_id = _anchor(project, "formal_experiment", output, "formal_output", extra={
        "execution_record_id": _relative(project, record_path),
        "command": execution["command"],
        "cwd": execution["cwd"],
        "exit_status": execution["exit_status"],
        "source_sha256": digest,
    })
    return _result(project, "formal_experiment", output, anchor_id, execution_record=execution)


def _analysis(project: Path) -> dict[str, Any]:
    formal = _read(project / "artifacts" / "formal_results.json", {})
    values = formal.get("values", []) if isinstance(formal, dict) else []
    if not values:
        return {"status": "FAIL", "node": "analysis", "findings": ["formal output has no values"]}
    mean = statistics.fmean(values)
    stdev = statistics.pstdev(values)
    artifact = project / "artifacts" / "analysis.json"
    value = {
        "input": "artifacts/formal_results.json",
        "n": len(values),
        "mean": mean,
        "uncertainty": {"population_stdev": stdev, "interpretation": "deterministic repetitions; not population inference"},
        "error_analysis": {"max_absolute_deviation": max(abs(item - mean) for item in values)},
        "robustness": {"leave_one_out_means": [statistics.fmean(values[:i] + values[i + 1:]) for i in range(len(values))]},
        "sensitivity": {"rounded_mean": round(mean, 6)},
    }
    _write(artifact, value)
    return _result(project, "analysis", artifact, _anchor(project, "analysis", artifact, "analysis"), statistics=value)


def _evidence_update(project: Path) -> dict[str, Any]:
    ledger = _read(_state(project) / "evidence_ledger.json", {})
    formal_ids = [item.get("anchor_id") for item in ledger.get("anchors", []) if item.get("artifact_type") in {"formal_output", "analysis"}]
    claims_path = _state(project) / "claims.json"
    claims = _read(claims_path, {})
    claims["claims"] = [{
        "id": "C1",
        "text": "The project fixture preserves output provenance through the normal Director runtime.",
        "type": "descriptive",
        "scope": "project-provided public fixture only",
        "required_evidence": "observed formal execution and deterministic analysis",
        "observed_evidence": formal_ids,
        "status": "SCOPED",
    }]
    _write(claims_path, claims)
    artifact = project / "artifacts" / "evidence_update.json"
    _write(artifact, {"claims": ["C1"], "anchors": formal_ids, "unsupported_claims_removed": True})
    return _result(project, "evidence_update", artifact, _anchor(project, "evidence_update", artifact, "claim_support"))


def _figures(project: Path) -> dict[str, Any]:
    analysis = _read(project / "artifacts" / "analysis.json", {})
    source_hash = _hash(project / "artifacts" / "analysis.json")
    figure = project / "artifacts" / "figure.svg"
    mean = analysis.get("mean", 0)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="160" role="img" aria-label="Recorded mean"><rect x="20" y="20" width="{min(260, float(mean) * 200):.1f}" height="60" fill="#4472C4"/><text x="20" y="120">mean={mean}</text></svg>\n'
    _write(figure, svg)
    provenance = project / "artifacts" / "figure_provenance.json"
    _write(provenance, {"figure": "artifacts/figure.svg", "source_data": "artifacts/analysis.json", "source_sha256": source_hash, "transform": "bar width = mean * 200", "status": "TRACEABLE"})
    anchor_id = _anchor(project, "figures", figure, "figure", extra={"source_data": "artifacts/analysis.json"})
    result = _result(project, "figures", figure, anchor_id)
    result["artifacts"].append(_relative(project, provenance))
    return result


def _writing(project: Path) -> dict[str, Any]:
    brief = _read(project / "inputs" / "research_brief.json", {})
    analysis = _read(project / "artifacts" / "analysis.json", {})
    literature = _read(project / "artifacts" / "literature.json", {})
    manuscript = project / "artifacts" / "manuscript.md"
    text = (
        f"# {brief.get('title', 'Research manuscript')}\n\n"
        "## Abstract\n\nWe evaluate an evidence-bound deterministic fixture through the normal autonomous Director runtime. "
        "Claims are limited to the project-provided public fixture.\n\n"
        f"## Related Work\n\nThe verified source is {literature.get('closest_work', 'the project source')}.\n\n"
        "## Method\n\nA frozen protocol drives a generated implementation and a recorded formal command.\n\n"
        f"## Results\n\nThe recorded mean is {analysis.get('mean')} with population standard deviation {analysis.get('uncertainty', {}).get('population_stdev')}.\n\n"
        "## Limitations\n\nThis deterministic harness is not a model-behavior evaluation and does not establish external scientific validity.\n"
    )
    _write(manuscript, text)
    return _result(project, "writing", manuscript, _anchor(project, "writing", manuscript, "manuscript"), word_count=len(text.split()))


def _validation(project: Path) -> dict[str, Any]:
    required = ["formal_results.json", "analysis.json", "figure.svg", "figure_provenance.json", "manuscript.md"]
    findings = [name for name in required if not (project / "artifacts" / name).is_file()]
    artifact = project / "artifacts" / "validation_report.json"
    _write(artifact, {"status": "PASS" if not findings else "FAIL", "missing": findings, "checks": required})
    if findings:
        return {"status": "FAIL", "node": "validation", "findings": [f"missing {name}" for name in findings]}
    return _result(project, "validation", artifact, _anchor(project, "validation", artifact, "validation"))


def _review(project: Path) -> dict[str, Any]:
    manuscript = (project / "artifacts" / "manuscript.md").read_text(encoding="utf-8")
    findings = []
    if "## Reproducibility" not in manuscript:
        findings.append({"id": "RF-001", "severity": "MAJOR", "status": "OPEN", "finding": "Manuscript lacks a reproducibility section.", "smallest_sufficient_fix": "Add commands, inputs, outputs, and scope boundary."})
    artifact = project / "artifacts" / "review_findings.json"
    _write(artifact, {"status": "PASS", "findings": findings, "reviewed_artifact": "artifacts/manuscript.md"})
    return _result(project, "review", artifact, _anchor(project, "review", artifact, "review"), findings=findings)


def _revision(project: Path) -> dict[str, Any]:
    manuscript = project / "artifacts" / "manuscript.md"
    text = manuscript.read_text(encoding="utf-8")
    actions = []
    if "## Reproducibility" not in text:
        text += "\n## Reproducibility\n\nRun the recorded Python command against the frozen project inputs; verify the declared output hash, analysis source hash, and package manifest.\n"
        _write(manuscript, text)
        actions.append("RF-001:added_reproducibility_section")
    review_path = project / "artifacts" / "review_findings.json"
    review = _read(review_path, {})
    for finding in review.get("findings", []):
        if finding.get("id") == "RF-001":
            finding.update({"status": "RESOLVED", "resolution": "smallest sufficient manuscript fix applied and revalidated"})
    _write(review_path, review)
    artifact = project / "artifacts" / "revised_manuscript.md"
    shutil.copy2(manuscript, artifact)
    return _result(project, "revision", artifact, _anchor(project, "revision", artifact, "manuscript"), actions=actions)


def _venue_preflight(project: Path) -> dict[str, Any]:
    artifact = project / "artifacts" / "preflight_report.json"
    _write(artifact, {"status": "PASS", "scope": "software release fixture only", "submission": "NOT_PERFORMED", "venue_rules": "not applicable to deterministic harness"})
    return _result(project, "venue_preflight", artifact, _anchor(project, "venue_preflight", artifact, "validation"))


def _artifact_package(project: Path) -> dict[str, Any]:
    artifact = project / "artifacts" / "package_manifest.json"
    entries = []
    for path in sorted((project / "artifacts").glob("*")):
        if path.is_file() and path != artifact:
            entries.append({"path": _relative(project, path), "sha256": _hash(path), "bytes": path.stat().st_size})
    _write(artifact, {"status": "PASS", "artifacts": entries, "reproduction_command": "python experiments/run_experiment.py artifacts/formal_results.json"})
    return _result(project, "artifact_package", artifact, _anchor(project, "artifact_package", artifact, "package"), packaged=len(entries))


def _author_handoff(project: Path) -> dict[str, Any]:
    artifact = project / "artifacts" / "author_handoff.json"
    _write(artifact, {"status": "READY_FOR_SUBMISSION", "ordinary_author_prompts": 0, "external_actions_performed": [], "model_behavior_eval": "NOT_RUN"})
    return _result(project, "author_handoff", artifact, _anchor(project, "author_handoff", artifact, "handoff"))


EXECUTORS: dict[str, Callable[[Path], dict[str, Any]]] = {
    "orientation": _orientation,
    "brief": _brief,
    "literature": _literature,
    "innovation": _innovation,
    "prior_art_red_team": _prior_art,
    "feasibility": _feasibility,
    "pilot": _pilot,
    "protocol_freeze": _protocol,
    "implementation": _implementation,
    "formal_experiment": _formal_experiment,
    "analysis": _analysis,
    "evidence_update": _evidence_update,
    "figures": _figures,
    "writing": _writing,
    "validation": _validation,
    "review": _review,
    "revision": _revision,
    "venue_preflight": _venue_preflight,
    "artifact_package": _artifact_package,
    "author_handoff": _author_handoff,
}


def validate_output(project: Path, node: str, result: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    if result.get("status") != "PASS":
        findings.extend(result.get("findings", ["executor did not return PASS"]))
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        findings.append("node emitted no artifact")
    else:
        for relative in artifacts:
            path = (project / str(relative)).resolve()
            try:
                path.relative_to(project.resolve())
            except ValueError:
                findings.append(f"artifact escapes project: {relative}")
                continue
            if not path.is_file() or path.stat().st_size == 0:
                findings.append(f"artifact is missing or empty: {relative}")
    evidence = result.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        findings.append("node emitted no evidence anchor")
    if node == "formal_experiment" and result.get("execution_record", {}).get("status") != "PASS":
        findings.append("formal experiment has no passing execution record")
    if node == "literature" and not all(result.get(name) for name in ("sources", "retrieval_records", "verified_relations")):
        findings.append("literature output contract is incomplete")
    return {"operation": "validate-node-output", "node": node, "status": "PASS" if not findings else "FAIL", "findings": findings}


def execute_node(project: Path, node: str) -> dict[str, Any]:
    project = project.resolve()
    executor = EXECUTORS.get(node)
    if executor is None:
        return {"operation": "execute-node", "node": node, "status": "BLOCKED", "findings": ["no registered executor"]}
    try:
        result = executor(project)
    except Exception as exc:
        return {"operation": "execute-node", "node": node, "status": "FAIL", "findings": [f"{type(exc).__name__}: {exc}"], "failure_signature": f"{node}:{type(exc).__name__}:{exc}"}
    check = validate_output(project, node, result)
    if check["status"] != "PASS":
        return result | {"status": "FAIL", "findings": check["findings"], "output_validation": check, "failure_signature": f"{node}:output-contract"}
    return result | {"output_validation": check}
