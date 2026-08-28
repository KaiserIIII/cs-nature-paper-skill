#!/usr/bin/env python3
"""Problem intake, decomposition, and qualitative selection for competitions."""

from __future__ import annotations

from typing import Any


LEVELS = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
BENEFIT_FIELDS = (
    "data_availability",
    "validation_feasibility",
    "paper_potential",
    "interpretability",
    "capability_fit",
)
COST_FIELDS = (
    "understanding_difficulty",
    "data_cleaning_cost",
    "modeling_difficulty",
    "implementation_difficulty",
    "compute_budget",
    "failure_risk",
    "completion_risk",
)


def _family(goal: str) -> tuple[list[str], list[str], list[str], str, str]:
    text = goal.casefold()
    if any(token in text for token in ("forecast", "predict", "预测", "需求")):
        return (
            ["prediction", "time-series"],
            ["naive last value", "moving average", "linear trend"],
            ["time-respecting validation", "residual diagnostics", "baseline comparison"],
            "结果分析",
            "forecast next-period demand without temporal leakage",
        )
    if any(token in text for token in ("optim", "allocation", "route", "facility", "选址", "配送", "优化")):
        return (
            ["optimization", "network"],
            ["exhaustive enumeration", "linear programming", "network optimization"],
            ["independent feasibility check", "objective recalculation", "boundary check"],
            "模型建立与求解",
            "minimize declared cost subject to capacity and feasibility constraints",
        )
    if any(token in text for token in ("sensitiv", "scenario", "robust", "敏感", "情景", "稳健")):
        return (
            ["sensitivity", "simulation"],
            ["one-at-a-time perturbation", "scenario analysis"],
            ["conclusion reversal check", "alternative scenario check"],
            "敏感性与稳健性",
            "measure whether the recommendation changes under justified perturbations",
        )
    return (
        ["evaluation"],
        ["transparent normalized indicator", "unweighted ranking"],
        ["rank stability", "alternative weight check"],
        "问题分析",
        "compare candidates using interpretable problem-supplied criteria",
    )


def decompose(problems: list[dict[str, Any]]) -> dict[str, Any]:
    decomposed: list[dict[str, Any]] = []
    findings: list[str] = []
    for problem in problems:
        problem_id = str(problem.get("id", "")).strip()
        source_questions = problem.get("questions")
        if not problem_id or not isinstance(source_questions, list) or not source_questions:
            findings.append(f"problem {problem_id or '<unknown>'} needs identified questions")
            continue
        questions: list[dict[str, Any]] = []
        graph: dict[str, list[str]] = {}
        ids = [str(item.get("id", "")).strip() for item in source_questions]
        for index, source in enumerate(source_questions):
            question_id = ids[index]
            goal = str(source.get("goal", "")).strip()
            families, methods, validations, section, objective = _family(goal)
            if not question_id or not goal:
                findings.append(f"problem {problem_id} has a question without id or goal")
                continue
            if index == 2 and len(ids) >= 3:
                dependencies = ids[:2]
            elif index > 2:
                dependencies = [ids[index - 1]]
            else:
                dependencies = []
            graph[question_id] = dependencies
            questions.append(
                {
                    "id": question_id,
                    "goal": goal,
                    "inputs": ["problem statement", "supplied data"],
                    "known_data": ["problem-supplied observations and constraints"],
                    "unknown_data": ["decision-relevant quantity requested by the question"],
                    "decision_variables": ["model decision or reported recommendation"],
                    "state_variables": ["problem state derived from supplied data"],
                    "parameters": ["problem-given or explicitly estimated parameters"],
                    "target": goal,
                    "objective": objective,
                    "constraints": ["problem-stated feasibility and consistency constraints"],
                    "required_outputs": ["numeric result", "interpretation", "decision consequence"],
                    "outputs": ["numeric result", "interpretation", "decision consequence"],
                    "dependencies": dependencies,
                    "required_evidence": ["executed result", "independent validation"],
                    "assumptions": [f"A-{question_id}"],
                    "candidate_method_families": families,
                    "candidate_methods": methods,
                    "validation_requirements": validations,
                    "validation": validations,
                    "likely_paper_section": section,
                    "difficulty": "MEDIUM",
                    "execution_risk": "MEDIUM",
                }
            )
        decomposed.append(
            {
                "problem_id": problem_id,
                "title": problem.get("title", problem_id),
                "questions": questions,
                "question_graph": graph,
                "shared_contract": {
                    "definitions": "single problem-wide definitions table",
                    "symbols": "single symbol registry",
                    "units": "single unit registry",
                    "data": "shared processed data snapshot",
                    "parameters": "shared parameter provenance",
                    "intermediate_results": "dependency-linked result identifiers",
                },
            }
        )
    return {
        "operation": "competition-problem-decomposition",
        "status": "PASS" if decomposed and not findings else "FAIL",
        "problems": decomposed,
        "findings": findings,
    }


def _quality(profile: dict[str, Any]) -> tuple[int | None, list[str]]:
    unknown: list[str] = []
    total = 0
    for field in BENEFIT_FIELDS:
        value = str(profile.get(field, "MEDIUM")).upper()
        if value not in LEVELS:
            unknown.append(field)
        else:
            total += LEVELS[value]
    for field in COST_FIELDS:
        value = str(profile.get(field, "MEDIUM")).upper()
        if value not in LEVELS:
            unknown.append(field)
        else:
            total += 4 - LEVELS[value]
    return (None if unknown else total), unknown


def select(problems: list[dict[str, Any]]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    internal: list[tuple[int, str, dict[str, Any]]] = []
    for problem in problems:
        problem_id = str(problem.get("id", "")).strip()
        profile = problem.get("decision_profile")
        if not problem_id or not isinstance(profile, dict):
            records.append({"problem_id": problem_id, "assessment": "UNKNOWN", "unknown": ["decision_profile"]})
            continue
        quality, unknown = _quality(profile)
        assessment = "UNKNOWN"
        if quality is not None:
            assessment = "HIGH" if quality >= 28 else "MEDIUM" if quality >= 20 else "LOW"
            internal.append((quality, problem_id, profile))
        records.append(
            {
                "problem_id": problem_id,
                "assessment": assessment,
                "decision_profile": profile,
                "unknown": unknown,
            }
        )
    internal.sort(key=lambda item: (-item[0], item[1]))
    if not internal or any(record.get("unknown") for record in records):
        return {
            "operation": "competition-problem-selection",
            "status": "CONDITIONAL",
            "decision": "ASK_AUTHOR",
            "selected_problem": None,
            "candidate_profiles": records,
            "selection_rationale": "a decision-critical profile is unknown",
        }
    gap = internal[0][0] - internal[1][0] if len(internal) > 1 else 99
    clear = gap >= 4
    if not clear:
        return {
            "operation": "competition-problem-selection",
            "status": "CONDITIONAL",
            "decision": "ASK_AUTHOR",
            "selected_problem": None,
            "candidate_profiles": records,
            "selection_rationale": "the leading problems are substantively tied",
        }
    selected = internal[0][1]
    fallback = internal[1][1] if len(internal) > 1 else None
    selected_profile = internal[0][2]
    largest_risk = next(
        (
            field
            for field in COST_FIELDS
            if str(selected_profile.get(field, "MEDIUM")).upper() == "HIGH"
        ),
        "completion time and interpretation remain monitored",
    )
    return {
        "operation": "competition-problem-selection",
        "status": "PASS",
        "decision": "AUTO_SELECT",
        "selected_problem": selected,
        "selection_rationale": f"{selected} is qualitatively dominant on completion, validation, interpretability, and capability fit",
        "alternatives_rejected": [
            {"problem_id": item[1], "reason": "weaker qualitative completion profile"}
            for item in internal[1:]
        ],
        "largest_selection_risk": largest_risk,
        "fallback_problem": fallback,
        "candidate_profiles": records,
    }
