#!/usr/bin/env python3
"""Run a small public-safe end-to-end research workflow fixture."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import evidence_anchor  # type: ignore  # noqa: E402
import experiment_planner  # type: ignore  # noqa: E402
import literature_runtime  # type: ignore  # noqa: E402
import method_router  # type: ignore  # noqa: E402
import research_graph  # type: ignore  # noqa: E402
import research_state  # type: ignore  # noqa: E402
import skill_router  # type: ignore  # noqa: E402


def _load_eval_runner():
    spec = importlib.util.spec_from_file_location("eval_runner", ROOT / "scripts" / "eval_runner.py")
    module = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(module); return module


def _fill_state(project: Path) -> None:
    state = project / ".research-state"
    contract_path = state / "research_contract.json"; contract = json.loads(contract_path.read_text(encoding="utf-8")); argument = contract["scientific_argument"]
    for field in ("stakeholder_problem", "phenomenon_or_artifact", "prior_knowledge", "gap", "mechanism_or_model", "target_population_and_scope", "contribution", "downstream_boundary"): argument[field] = f"bounded smoke fixture: {field}"
    argument["questions_or_goals"] = [{"id":"RQ1","text":"Does the small repair fixture expose a measurable difference?"}]; argument["constructs"] = [{"name":"repair success","conceptual_definition":"accepted patch on the fixed fixture","operationalization":"file-level test result","role":"outcome","known_gap":"does not establish ecosystem-wide reliability"}]
    contract["feasibility"] = {"decision":"GO","resource_inventory":"one local CPU fixture","cost":"zero network calls","risks":["synthetic scope"],"lower_resource_option":"single deterministic fixture"}
    contract["protocol"] = {"status":"frozen-v1","units":"fixture cases","outcomes":["pass"],"estimands":["proportion passing"],"denominators":["all fixture cases"],"missingness_and_exclusions":"report separately","clustering_and_dependence":"none within this fixture","repetition_rationale":"deterministic command run once and reproduced","multiplicity":"one registered outcome","stopping_and_failure_rules":"retain failures","frozen_inputs":["smoke-input-v1"]}
    contract_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    claims_path = state / "claims.json"; claims = json.loads(claims_path.read_text(encoding="utf-8")); claims["claims"] = [{"id":"C1","text":"The smoke fixture records one deterministic repair outcome.","type":"descriptive","scope":"the public synthetic fixture only","required_evidence":"verified fixture output","observed_evidence":["EA-SMOKE"],"counterevidence":[],"uncertainty":"synthetic scope","status":"SCOPED"}]; claims_path.write_text(json.dumps(claims, indent=2) + "\n", encoding="utf-8")


def run(output: Path | None = None) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="cs-nature-v31-smoke-") as directory:
        project = Path(directory) / "smoke-project"; project.mkdir(); research_state.init_state(project, "ml-benchmark", "copilot", "llm"); _fill_state(project)
        artifact = project / "smoke-result.txt"; artifact.write_text("repair_success=1\n", encoding="utf-8"); digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        anchor = {"anchor_id":"EA-SMOKE","claim_id":"C1","result_id":"R1","source_artifact":"smoke-result.txt#sha256=" + digest,"exact_region":"line 1","transformation":"identity","command":"python -c smoke-fixture","exit_status":0,"code_commit":"smoke-fixture","config_hash":"sha256:config","environment":"python-stdlib","input_hash":"sha256:input","uncertainty":"synthetic fixture","scope":"public smoke fixture","status":"VERIFIED","verified_utc":"2026-08-27T00:00:00Z"}
        anchor_path = project / "anchor.json"; anchor_path.write_text(json.dumps(anchor, indent=2) + "\n", encoding="utf-8"); anchor_result = evidence_anchor.validate_path(anchor_path, deep=True, root=project)
        graph_steps = [("brief","PASS"),("literature","PASS"),("innovation","PASS"),("feasibility","PASS"),("pilot","PASS"),("protocol_freeze","PASS"),("implementation","PASS"),("formal_experiment","PASS"),("analysis","PASS"),("evidence_update","PASS"),("figures","PASS"),("writing","PASS"),("validation","PASS"),("review","PASS"),("revision","PASS"),("venue_preflight","PASS"),("artifact_package","PASS"),("author_handoff","PASS")]
        graph_results = []
        for node, status in graph_steps:
            graph_results.append(research_graph.transition(project, node, status, "smoke fixture completed", "smoke-run", "EA-SMOKE"))
        options = project / "options.json"; options.write_text(json.dumps({"experiments":[{"experiment_id":"E-SMOKE","claim_ids":["C1"],"threat":"deterministic reproducibility","hypothesis_or_question":"does command reproduce?","design":"single fixture rerun","information_gain":1,"cost":1,"risk":0,"reversibility":1,"stage":"PILOT","formal_status":"REGISTERED","inputs":["smoke-input-v1"],"expected_results":"same output","interpretation_positive":"supports fixture claim","interpretation_negative":"investigate","interpretation_null":"not applicable","stop_rule":"one rerun","dependencies":[],"outputs":["smoke-result.txt"],"evidence_anchors":["EA-SMOKE"]}]}) + "\n", encoding="utf-8"); planner_result = experiment_planner.plan(options)
        router_result = skill_router.resolve("statistical-modeling"); method_result = method_router.route("Compare model metrics across seeds", "stochastic-ml")
        literature = project / "literature_registry.json"; literature.write_text(json.dumps({"schema_version":3,"skill_version":"3.1.0","sources":[]}) + "\n", encoding="utf-8"); literature_result = literature_runtime.record_query(project / "query_log.json", "LLM code repair benchmark", "synthetic-fixture", "none", 0, "smoke only", "none")
        eval_runner = _load_eval_runner(); cases = project / "smoke_cases.json"; cases.write_text(json.dumps({"schema_version":1,"skill_version":"3.1.0","cases":[{"id":"SMOKE-ROUTING","category":"routing","prompt":"Start from a vague student idea.","fixture":{},"required_behaviors":["creates a beginner brief","runs feasibility"],"forbidden_behaviors":["promises acceptance"],"required_artifacts":["brief"]}]}) + "\n", encoding="utf-8"); prepared = project / "eval"; eval_runner.prepare(cases, prepared); answer = project / "answer.txt"; answer.write_text("The system creates a beginner brief and runs feasibility before choosing an RQ. Findings remain evidence-bounded.", encoding="utf-8"); eval_runner.run_record(prepared / "manifest.json", "SMOKE-ROUTING", answer, model="local-deterministic", host="local", reasoning_mode="deterministic", network=False, tools=[]); scored = eval_runner.score(cases, prepared / "runs", project / "score.json"); eval_report = eval_runner.report(project / "score.json")
        result = {"status":"PASS" if anchor_result["status"] in {"PASS","CONDITIONAL"} and eval_report["status"] == "PASS" and all(item["status"] == "PASS" for item in graph_results) else "FAIL","project_fixture":"synthetic/private temp project","steps":["brief","literature","innovation","feasibility","pilot","protocol_freeze","implementation","formal_experiment","analysis","evidence_update","figures","writing","validation","review","revision","venue_preflight","artifact_package","author_handoff"],"graph_events":len(graph_results),"anchor":anchor_result,"planner":planner_result,"router":router_result,"method_router":method_result,"literature_query":literature_result,"behavior_eval":eval_report,"model_comparison":"NOT_RUN; no second model/API was available","note":"This is a deterministic workflow smoke test, not a scientific publication or venue claim."}
        if output:
            output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--output", type=Path); args = parser.parse_args(); value = run(args.output); print(json.dumps(value, indent=2, ensure_ascii=False)); sys.exit(0 if value["status"] == "PASS" else 1)
