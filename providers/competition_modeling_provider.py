"""Structure-driven competition intake, decomposition, and model reasoning provider."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import provider_support as support


SCRIPT_DIR = str(Path(__file__).resolve().parents[1] / "scripts")
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import competition_method_router  # noqa: E402


PROVIDER_ID = "competition-modeling-provider"


def _input(project: Path, *, allow_empty: bool = False) -> dict[str, Any]:
    state_path = support.state_dir(project) / "competition_input.json"
    value = support.read_json(state_path if state_path.is_file() else project / "competition_input.json", {})
    if allow_empty and not value:
        return {"competition": "competition", "problems": [], "rules": [], "official_rules_source": "", "intake_status": "AWAITING_PROBLEMS"}
    if not isinstance(value.get("problems"), list) or not value["problems"]:
        raise ValueError("competition input requires at least one problem")
    return value


def _state(project: Path) -> dict[str, Any]:
    return support.read_json(support.state_dir(project) / "competition_state.json", {})


def _save(project: Path, value: dict[str, Any]) -> None:
    support.write(support.state_dir(project) / "competition_state.json", value)


def _inventory(project: Path, problem: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    declared = problem.get("data_files", [])
    for raw in declared if isinstance(declared, list) else []:
        relative = str(raw)
        path = (project / relative).resolve()
        if project.resolve() not in path.parents or not path.is_file():
            records.append({"path": relative, "status": "MISSING"})
            continue
        suffix = path.suffix.casefold()
        kind = {
            ".csv": "CSV", ".xlsx": "EXCEL", ".xls": "EXCEL", ".json": "JSON", ".txt": "TXT",
            ".png": "IMAGE", ".jpg": "IMAGE", ".jpeg": "IMAGE",
        }.get(suffix, "BINARY")
        records.append({"path": relative, "status": "AVAILABLE", "kind": kind, "sha256": support.digest(path), "bytes": path.stat().st_size})
    embedded = []
    for key, value in problem.items():
        if key in {"id", "title", "questions", "decision_profile", "data_files"}:
            continue
        if isinstance(value, (list, dict)):
            embedded.append({"field": key, "structure": type(value).__name__, "records": len(value)})
    records.append({"path": "<embedded-problem-data>", "status": "AVAILABLE", "kind": "JSON", "schema": embedded})
    return records


def _dominant(problems: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(problems) == 1:
        return problems[0]
    good = {"LOW": 2, "MEDIUM": 1, "HIGH": 0}
    benefit = {"HIGH": 2, "MEDIUM": 1, "LOW": 0}
    ranked = []
    for problem in problems:
        profile = problem.get("decision_profile", {})
        if not profile:
            continue
        score = (
            good.get(profile.get("understanding_difficulty"), 0)
            + benefit.get(profile.get("data_availability"), 0)
            + good.get(profile.get("implementation_difficulty"), 0)
            + benefit.get(profile.get("validation_feasibility"), 0)
            + benefit.get(profile.get("capability_fit"), 0)
            + good.get(profile.get("completion_risk"), 0)
        )
        ranked.append((score, str(problem.get("id", "")), problem))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    if not ranked or (len(ranked) > 1 and ranked[0][0] - ranked[1][0] < 3):
        return None
    return ranked[0][2]


def _route_question(question: dict[str, Any]) -> dict[str, Any]:
    text = str(question.get("goal") or question.get("text") or question.get("question") or "")
    route = competition_method_router.route(text)
    families = list(route.get("candidate_families", []))
    if route.get("status") == "UNRESOLVED":
        explicit = question.get("method_family")
        if explicit:
            route = competition_method_router.route(text, str(explicit))
            families = [str(explicit)]
    return {
        "question_id": str(question.get("id", "Q")), "problem_formulation": text,
        "assumptions": list(route.get("main_assumptions", [])),
        "symbols": list(question.get("symbols", [])), "units": list(question.get("units", [])),
        "candidate_methods": list(route.get("candidate_models", [])),
        "candidate_families": families,
        "baseline_method": route.get("recommended_baseline"), "primary_method": route.get("recommended_primary_model"),
        "upgrade_condition": route.get("complexity_upgrade_condition"),
        "validation_plan": list(route.get("validation_plan", [])),
        "implementation_plan": f"generate one family-routed executable stage for {', '.join(families) or 'UNRESOLVED'}",
        "expected_outputs": list(question.get("required_outputs", ["answer", "validation"])),
        "routing_status": route.get("status"),
    }


def execute(project: Path, node: str) -> dict[str, Any]:
    source = _input(project, allow_empty=node == "contest_intake")
    state = _state(project)
    output_dir = project / "data_processed"
    if node == "contest_intake":
        value = {
            "competition": source.get("competition", "competition"), "problem_count": len(source["problems"]),
            "problem_ids": [item.get("id") for item in source["problems"]],
            "rules_source": source.get("official_rules_source"), "data_inventory": [_inventory(project, item) for item in source["problems"]],
        }
        state["competition"] = source.get("competition", "competition")
        path = support.write(output_dir / "contest_intake.json", value)
    elif node == "problem_decomposition":
        decomposed = []
        for problem in source["problems"]:
            decomposed.append({"problem_id": problem.get("id"), "title": problem.get("title"), "questions": [_route_question(item) for item in problem.get("questions", [])]})
        state["all_problem_decompositions"] = decomposed
        path = support.write(output_dir / "question_decomposition.json", {"problems": decomposed})
    elif node == "problem_selection":
        selected = _dominant(source["problems"])
        if selected is None:
            return {"status": "BLOCKED", "findings": ["no qualitatively dominant problem; substantive selection is required"]}
        state["selected_problem"] = selected.get("id")
        selected_decomposition = next((item for item in state.get("all_problem_decompositions", []) if item.get("problem_id") == selected.get("id")), None)
        state["question_decomposition"] = [
            {
                "id": item["question_id"], "goal": item["problem_formulation"], "inputs": [], "known_data": [],
                "unknown_data": [], "decision_variables": [], "state_variables": [], "parameters": [],
                "target": item["problem_formulation"], "objective": item["problem_formulation"], "constraints": [],
                "required_outputs": item["expected_outputs"], "dependencies": [], "required_evidence": ["observed command output"],
                "candidate_method_families": item["candidate_families"], "validation_requirements": item["validation_plan"],
                "likely_paper_section": "模型求解", "difficulty": "MEDIUM", "execution_risk": "MEDIUM",
            }
            for item in (selected_decomposition or {}).get("questions", [])
        ]
        state["modeling_plan"] = (selected_decomposition or {}).get("questions", [])
        selected_path = support.write(output_dir / "selected_problem.json", selected)
        path = support.write(output_dir / "problem_selection.json", {"decision": "AUTO_SELECT", "selected_problem": selected.get("id"), "selected_path": support.relative(project, selected_path)})
    elif node == "assumptions":
        assumptions = []
        for plan in state.get("modeling_plan", []):
            for text in plan.get("assumptions", []) or ["supplied observations and constraints represent the declared contest scope"]:
                assumptions.append({"question_id": plan["question_id"], "assumption": text, "reason": "required by selected family", "consequence": "limits interpretation", "risk": "MEDIUM", "check": "validation and sensitivity"})
        state["assumptions"] = assumptions
        path = support.write(output_dir / "assumptions.json", {"assumptions": assumptions})
    elif node == "method_candidates":
        plans = state.get("modeling_plan", [])
        if not plans or any(item.get("routing_status") == "UNRESOLVED" for item in plans):
            return {"status": "UNRESOLVED", "findings": ["at least one question has no defensible method-family match"]}
        families = []
        for plan in plans:
            families.extend(plan.get("candidate_families", []))
        state["candidate_models"] = plans
        state["baseline_model"] = "; ".join(str(item.get("baseline_method")) for item in plans)
        state["primary_model"] = "; ".join(str(item.get("primary_method")) for item in plans)
        state["method_families"] = sorted(set(families))
        path = support.write(output_dir / "method_candidates.json", {"questions": plans, "mixed_method": len(set(families)) > 1, "families": sorted(set(families)), "baseline_first": True})
    else:
        return {"status": "BLOCKED", "findings": [f"unsupported modeling node: {node}"]}
    _save(project, state)
    return support.handoff(project, PROVIDER_ID, node, [path], actions=["routed by problem structure"], extra={"modeling_plan": state.get("modeling_plan", [])})
