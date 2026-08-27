#!/usr/bin/env python3
"""Run a truthful, public-safe, fully local end-to-end fixture."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import evidence_anchor  # type: ignore
import experiment_planner  # type: ignore
import literature_runtime  # type: ignore
import method_router  # type: ignore
import research_graph  # type: ignore
import research_state  # type: ignore
import skill_router  # type: ignore
from sanitize_artifact import sanitize_value  # type: ignore


def _load_eval_runner():
    spec = importlib.util.spec_from_file_location("eval_runner", ROOT / "scripts" / "eval_runner.py")
    module = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(module); return module


def _commit() -> str:
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _fill_state(project: Path) -> None:
    state = project / ".research-state"
    contract_path = state / "research_contract.json"; contract = json.loads(contract_path.read_text(encoding="utf-8")); argument = contract["scientific_argument"]
    for field in ("stakeholder_problem", "phenomenon_or_artifact", "prior_knowledge", "gap", "mechanism_or_model", "target_population_and_scope", "contribution", "downstream_boundary"): argument[field] = f"bounded public fixture: {field}"
    argument["questions_or_goals"] = [{"id": "RQ1", "text": "Does the deterministic fixture preserve a repair outcome?"}]
    argument["constructs"] = [{"name": "repair success", "conceptual_definition": "accepted patch on fixture", "operationalization": "fixture test result", "role": "outcome", "known_gap": "does not establish ecosystem reliability"}]
    contract["feasibility"] = {"decision": "GO", "resource_inventory": "one local CPU", "cost": "zero network calls", "risks": ["synthetic scope"], "lower_resource_option": "single fixture case"}
    contract["protocol"] = {"status": "frozen-v1", "units": "fixture cases", "outcomes": ["repair_success"], "estimands": ["proportion passing"], "denominators": ["all fixture cases"], "missingness_and_exclusions": "retain failures", "clustering_and_dependence": "none", "repetition_rationale": "deterministic command and independent rerun", "multiplicity": "one outcome", "stopping_and_failure_rules": "stop after reproducible run", "frozen_inputs": ["fixture-v1"]}
    _write(contract_path, contract)
    _write(state / "claims.json", {"schema_version": 1, "skill_version": "3.1.1", "claims": [{"id": "C1", "text": "The public fixture records one deterministic repair outcome.", "type": "descriptive", "scope": "public fixture only", "required_evidence": "observed fixture output", "observed_evidence": [], "status": "SCOPED"}]})


def _anchor(project: Path, anchor_id: str, artifact: Path, *, claim_id: str = "C1", artifact_type: str = "execution", level: str = "VERIFIED", **extra: Any) -> dict[str, Any]:
    state = project / ".research-state"; digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    value = {"anchor_id": anchor_id, "claim_id": claim_id, "result_id": anchor_id.replace("EA-", "R-"), "source_artifact": f"{artifact.relative_to(project).as_posix()}#sha256={digest}", "exact_region": "line 1", "transformation": "identity", "provenance_level": level, "uncertainty": "bounded synthetic fixture", "scope": "public fixture", "status": level, "artifact_type": artifact_type, "checker": "local-deterministic-checker", "checker_required": artifact_type in {"analysis", "validation", "review"}}
    value.update(extra)
    ledger_path = state / "evidence_ledger.json"; ledger = json.loads(ledger_path.read_text(encoding="utf-8")); ledger.setdefault("anchors", []).append(value); ledger_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return value


def _transition(project: Path, node: str, evidence: str) -> dict[str, Any]:
    return research_graph.transition(project, node, "PASS", f"node-specific fixture artifact {evidence}", "smoke-executor", evidence)


def run(output: Path | None = None) -> dict[str, Any]:
    tested_commit = _commit()
    with tempfile.TemporaryDirectory(prefix="cs-nature-v311-smoke-") as directory:
        project = Path(directory) / "fixture"; project.mkdir(); research_state.init_state(project, "engineering-system", "copilot", "software-engineering"); _fill_state(project)
        fixture = project / "fixture.py"; fixture.write_text("print('repair_success=1')\n", encoding="utf-8")
        output_artifact = project / "artifacts" / "execution.txt"; output_artifact.parent.mkdir(); output_artifact.write_text("repair_success=1\n", encoding="utf-8")
        execution_path = project / "artifacts" / "execution_record.json"; execution = evidence_anchor.execution_record(execution_path, [sys.executable, str(fixture)], cwd=project, output_paths=[output_artifact], environment={"network": False, "fixture": "public-v1"})
        if execution["exit_status"] != 0: raise RuntimeError("fixture command failed")
        # Orientation and brief are separate outputs, then the graph itself
        # determines which parallel nodes become ready.
        orient = project / "artifacts" / "orientation.txt"; orient.write_text("student request diagnosed\n", encoding="utf-8"); _anchor(project, "EA-ORIENT-001", orient, artifact_type="orientation"); _transition(project, "orientation", "EA-ORIENT-001")
        brief = project / "artifacts" / "brief.txt"; brief.write_text("bounded question and budget\n", encoding="utf-8"); _anchor(project, "EA-BRIEF-001", brief, artifact_type="brief"); _transition(project, "brief", "EA-BRIEF-001"); research_graph.advance(project)
        literature_file = project / "artifacts" / "literature.txt"; literature_file.write_text("Fixture prior work: deterministic repair checks are bounded.\n", encoding="utf-8")
        literature_registry = project / ".research-state" / "literature_registry.json"; query_log = project / ".research-state" / "query_log.json"; literature_runtime.record_query(query_log, "deterministic repair fixture", "local-fixture", "public", 1, "fixture discovery", "stable id")
        literature_runtime.verify_identity(literature_registry, "SRC-001", {"title": "Fixture prior work", "authors": ["Fixture Author"], "year": 2024, "venue": "Fixture Archive", "stable_identifier": "fixture:001", "retrieval_status": "FULL_TEXT_RETRIEVED"})
        literature_runtime.verify_claim(literature_registry, "SRC-001", "C1", "PARTIALLY_SUPPORTS", "line 1", retrieval_method="local-open", source_uri="fixture://literature.txt", inspection_actor="smoke-checker")
        _anchor(project, "EA-LIT-001", literature_file, artifact_type="literature", source_uri="fixture://literature.txt")
        innovation = project / "artifacts" / "innovation.txt"; innovation.write_text("RQ1 and falsifier recorded\n", encoding="utf-8"); _anchor(project, "EA-INNOV-001", innovation, artifact_type="innovation")
        _transition(project, "literature", "EA-LIT-001"); _transition(project, "innovation", "EA-INNOV-001"); research_graph.advance(project)
        feasibility = project / "artifacts" / "feasibility.json"; _write(feasibility, {"decision": "GO", "resource_assumptions": ["local CPU", "zero network"]}); _anchor(project, "EA-FEAS-001", feasibility, artifact_type="feasibility", decision="GO"); _transition(project, "feasibility", "EA-FEAS-001"); research_graph.advance(project)
        pilot = project / "artifacts" / "pilot.txt"; pilot.write_text("pilot_output=repair_success=1\n", encoding="utf-8"); _anchor(project, "EA-PILOT-001", pilot, artifact_type="execution", provenance_level="OBSERVED", execution_record_id="artifacts/execution_record.json", command=execution["command"], cwd="<TEMP_PROJECT>", exit_status=execution["exit_status"], started_utc=execution["started_utc"], finished_utc=execution["finished_utc"], stdout_sha256=execution["stdout_sha256"], stderr_sha256=execution["stderr_sha256"]); _transition(project, "pilot", "EA-PILOT-001"); research_graph.advance(project)
        freeze = project / "artifacts" / "protocol.json"; _write(freeze, {"status": "frozen-v1", "input": "fixture-v1", "analysis": "descriptive"}); _anchor(project, "EA-PROTOCOL-001", freeze, artifact_type="decision"); _transition(project, "protocol_freeze", "EA-PROTOCOL-001"); research_graph.advance(project)
        _anchor(project, "EA-IMPL-001", fixture, artifact_type="execution", provenance_level="OBSERVED", execution_record_id="artifacts/execution_record.json", command=execution["command"], cwd="<TEMP_PROJECT>", exit_status=execution["exit_status"], started_utc=execution["started_utc"], finished_utc=execution["finished_utc"], stdout_sha256=execution["stdout_sha256"], stderr_sha256=execution["stderr_sha256"]); _transition(project, "implementation", "EA-IMPL-001"); research_graph.advance(project)
        _anchor(project, "EA-EXP-001", output_artifact, artifact_type="formal_output", provenance_level="OBSERVED", execution_record_id="artifacts/execution_record.json", command=execution["command"], cwd="<TEMP_PROJECT>", exit_status=execution["exit_status"], started_utc=execution["started_utc"], finished_utc=execution["finished_utc"], stdout_sha256=execution["stdout_sha256"], stderr_sha256=execution["stderr_sha256"]); _transition(project, "formal_experiment", "EA-EXP-001"); research_graph.advance(project)
        analysis = project / "artifacts" / "analysis.txt"; analysis.write_text("n=1; repair_success proportion=1/1; scope=fixture\n", encoding="utf-8"); _anchor(project, "EA-ANALYSIS-001", analysis, artifact_type="analysis"); _transition(project, "analysis", "EA-ANALYSIS-001"); research_graph.advance(project)
        evidence = project / "artifacts" / "claim_trace.json"; _write(evidence, {"C1": ["EA-EXP-001", "EA-ANALYSIS-001"]}); _anchor(project, "EA-EVIDENCE-001", evidence, artifact_type="claim_support"); _transition(project, "evidence_update", "EA-EVIDENCE-001"); research_graph.advance(project)
        figure = project / "artifacts" / "figure.csv"; figure.write_text("metric,value\nrepair_success,1\n", encoding="utf-8"); _anchor(project, "EA-FIG-001", figure, artifact_type="figure"); _transition(project, "figures", "EA-FIG-001"); research_graph.advance(project)
        manuscript = project / "artifacts" / "short_writeup.md"; manuscript.write_text("The fixture recorded one repair outcome; this does not establish generality.\n", encoding="utf-8"); _anchor(project, "EA-WRITE-001", manuscript, artifact_type="manuscript"); _transition(project, "writing", "EA-WRITE-001"); research_graph.advance(project)
        validation = project / "artifacts" / "validation.json"; _write(validation, {"fresh_check": True, "output_hash_verified": True}); _anchor(project, "EA-VALID-001", validation, artifact_type="validation"); _transition(project, "validation", "EA-VALID-001"); research_graph.advance(project)
        review = project / "artifacts" / "review.json"; _write(review, {"findings": [{"id": "F1", "severity": "MINOR", "problem": "synthetic scope", "smallest_sufficient_fix": "retain scope"}]}); _anchor(project, "EA-REVIEW-001", review, artifact_type="review"); _transition(project, "review", "EA-REVIEW-001"); research_graph.advance(project)
        revision = project / "artifacts" / "revision.md"; revision.write_text("Scope retained after review.\n", encoding="utf-8"); _anchor(project, "EA-REVISION-001", revision, artifact_type="manuscript"); _transition(project, "revision", "EA-REVISION-001"); research_graph.advance(project)
        preflight = project / "artifacts" / "preflight.json"; _write(preflight, {"venue_rules": "not applicable to fixture", "public_boundary": "sanitized"}); _anchor(project, "EA-PREFLIGHT-001", preflight, artifact_type="validation"); _transition(project, "venue_preflight", "EA-PREFLIGHT-001"); research_graph.advance(project)
        package = project / "artifacts" / "package.json"; _write(package, {"public": ["fixture.py", "execution.txt"], "private": []}); _anchor(project, "EA-PACKAGE-001", package, artifact_type="validation"); _transition(project, "artifact_package", "EA-PACKAGE-001"); research_graph.advance(project)
        handoff = project / "artifacts" / "author_handoff.json"; _write(handoff, {"next": "author review", "residual_risks": ["synthetic scope"]}); _anchor(project, "EA-HANDOFF-001", handoff, artifact_type="handoff"); _transition(project, "author_handoff", "EA-HANDOFF-001")
        graph_check = research_graph.validate_project(project); rebuild = research_graph.rebuild(project); graph_check_after = research_graph.validate_project(project)
        planner_options = project / "planner.json"; _write(planner_options, {"experiments": [{"experiment_id": "E1", "claim_ids": ["C1"], "threat": "deterministic reproducibility", "information_gain": "HIGH", "cost": "LOW", "reversibility": "HIGH"}]}); planner_result = experiment_planner.plan(planner_options)
        route_result = skill_router.resolve("statistical-modeling", purpose="formal", load_bearing=True, criticality="critical")
        method_result = method_router.route("Compare model metrics across seeds", project=project)
        eval_runner = _load_eval_runner(); cases = project / "smoke_cases.json"; _write(cases, {"schema_version": 1, "skill_version": "3.1.1", "cases": [{"id": "SMOKE-ROUTING", "type": "harness", "category": "routing", "prompt": "Start from a vague student idea.", "fixture": {}, "required_behaviors": ["creates a beginner brief", "runs feasibility"], "forbidden_behaviors": ["promises acceptance"], "required_artifacts": ["brief"]}]}); prepared = project / "eval"; eval_runner.prepare(cases, prepared); answer = project / "answer.txt"; answer.write_text("The system creates a beginner brief and runs feasibility before choosing an RQ. Findings remain evidence-bounded.", encoding="utf-8"); eval_runner.run_record(prepared / "manifest.json", "SMOKE-ROUTING", answer, model="deterministic-harness", host="local", reasoning_mode="harness", network=False, tools=[]); eval_runner.score(cases, prepared / "runs", project / "score.json"); eval_report = eval_runner.report(project / "score.json")
        anchor_count = len(json.loads((project / ".research-state" / "evidence_ledger.json").read_text(encoding="utf-8")).get("anchors", []))
        result = {"status": "PASS" if graph_check["status"] == "PASS" and graph_check_after["status"] == "PASS" and rebuild["status"] == "PASS" and eval_report["status"] == "PASS" and anchor_count >= 19 and route_result["status"] == "CONDITIONAL" else "FAIL", "skill_commit": tested_commit, "skill_version": "3.1.1", "evaluation_class": "HARNESS_SELF_TEST", "project_fixture": "public synthetic fixture", "workflow": ["orientation", "brief", "literature_discovery", "identity_verification", "claim_support_verification", "innovation", "feasibility", "experiment_planning", "protocol_freeze", "executable_command", "observed_output", "evidence_anchor", "analysis", "figure_table", "writing", "validation", "review", "revision", "author_handoff"], "node_evidence": {anchor["anchor_id"]: anchor["artifact_type"] for anchor in json.loads((project / ".research-state" / "evidence_ledger.json").read_text(encoding="utf-8")).get("anchors", [])}, "graph_events": graph_check_after.get("event_count", 0), "anchor_count": anchor_count, "execution_record": {"exit_status": execution["exit_status"], "stdout_sha256": execution["stdout_sha256"], "stderr_sha256": execution["stderr_sha256"]}, "graph_validation": graph_check_after, "graph_rebuild": rebuild, "planner": planner_result, "router": route_result, "method_router": method_result, "literature": {"status": "CLAIM_RELATION_VERIFIED"}, "behavior_eval": eval_report, "model_behavior": "NOT_RUN; only harness self-test was executed", "privacy": "sanitized public output", "note": "True local fixture workflow; no scientific publication or venue claim."}
        result = sanitize_value(result)
        if output: output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return result


if __name__ == "__main__":
    parser = __import__("argparse").ArgumentParser(description=__doc__); parser.add_argument("--output", type=Path); args = parser.parse_args(); value = run(args.output); print(json.dumps(value, indent=2, ensure_ascii=False)); sys.exit(0 if value["status"] == "PASS" else 1)
