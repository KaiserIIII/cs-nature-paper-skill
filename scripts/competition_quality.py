#!/usr/bin/env python3
"""Deterministic quality gates for competition results, figures, papers, and packages."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


REQUIRED_OFFICIAL_RULES = (
    "contest_time",
    "problem_count",
    "participant_eligibility",
    "ai_policy",
    "paper_format",
    "page_limit",
    "file_naming",
    "attachments",
    "code_requirements",
    "submission_platform",
    "submission_method",
    "anonymity",
    "discipline",
)


def _state_dir(project: Path) -> Path:
    project = project.resolve()
    for name in (".research-state-v31", ".research-state-v3", ".research-state"):
        candidate = project / name
        if candidate.is_dir():
            return candidate
    raise RuntimeError("research state is missing")


def _read(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def file_sha256(path: Path) -> str:
    """Return the canonical digest form used by competition manifests."""
    return _sha256(path)


def check_artifact_freshness(
    artifact: Path,
    dependencies: list[Path],
    *,
    recorded_dependency_hashes: list[str],
) -> dict[str, Any]:
    findings: list[str] = []
    if not artifact.is_file():
        findings.append(f"artifact is missing: {artifact}")
    if len(dependencies) != len(recorded_dependency_hashes):
        findings.append("dependency list and recorded hash list have different lengths")
    for index, dependency in enumerate(dependencies):
        if not dependency.is_file():
            findings.append(f"dependency is missing: {dependency}")
            continue
        if index >= len(recorded_dependency_hashes):
            continue
        if _sha256(dependency) != recorded_dependency_hashes[index]:
            findings.append(f"dependency hash is stale: {dependency}")
    return {
        "operation": "competition-artifact-freshness",
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
    }


def check_solver_result(
    problem: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    site_by_id = {
        str(item.get("id")): item
        for item in problem.get("sites", [])
        if isinstance(item, dict) and item.get("id") is not None
    }
    selected_id = str(result.get("selected_site", ""))
    selected = site_by_id.get(selected_id)
    demand = result.get("forecast_demand")
    cost = result.get("selected_total_cost")
    recalculated = result.get("objective_recalculated")
    if selected is None:
        findings.append({"issue": "selected site does not exist in the problem", "severity": "CRITICAL", "location": "selected_site"})
    if not isinstance(demand, (int, float)) or isinstance(demand, bool) or demand < 0:
        findings.append({"issue": "forecast demand is missing or outside non-negative bounds", "severity": "CRITICAL", "location": "forecast_demand"})
    if selected is not None and isinstance(demand, (int, float)) and float(selected.get("capacity", -1)) < float(demand):
        findings.append({"issue": "selected solution violates capacity", "severity": "CRITICAL", "location": "capacity"})
    selected_candidate = next(
        (item for item in result.get("candidates", []) if str(item.get("site")) == selected_id),
        None,
    )
    if not isinstance(selected_candidate, dict) or not selected_candidate.get("feasible"):
        findings.append({"issue": "selected candidate is not independently marked feasible", "severity": "CRITICAL", "location": "candidates"})
    if not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0:
        findings.append({"issue": "selected objective is missing or negative", "severity": "CRITICAL", "location": "selected_total_cost"})
    if not isinstance(recalculated, (int, float)) or not isinstance(cost, (int, float)) or not math.isclose(float(cost), float(recalculated), rel_tol=1e-9, abs_tol=1e-9):
        findings.append({"issue": "reported objective does not equal independent recalculation", "severity": "CRITICAL", "location": "objective_recalculated"})
    candidate_rows = [item for item in result.get("candidates", []) if isinstance(item, dict)]
    candidate_ids = [str(item.get("site", "")) for item in candidate_rows]
    if len(candidate_ids) != len(set(candidate_ids)):
        findings.append({"issue": "candidate solution list contains duplicate sites", "severity": "CRITICAL", "location": "candidates"})
    rate = problem.get("distance_cost_rate", 0.01)
    can_recalculate = (
        isinstance(demand, (int, float))
        and not isinstance(demand, bool)
        and isinstance(rate, (int, float))
        and not isinstance(rate, bool)
        and all(
            isinstance(site.get(field), (int, float))
            and not isinstance(site.get(field), bool)
            for site in site_by_id.values()
            for field in ("capacity", "fixed_cost", "distance")
        )
    )
    if can_recalculate:
        expected: dict[str, tuple[bool, float]] = {}
        for site_id, site in site_by_id.items():
            is_feasible = float(site["capacity"]) >= float(demand)
            expected_cost = float(site["fixed_cost"]) + float(site["distance"]) * float(demand) * float(rate)
            expected[site_id] = (is_feasible, expected_cost)
            row = next((item for item in candidate_rows if str(item.get("site")) == site_id), None)
            if not isinstance(row, dict):
                findings.append({"issue": f"independent verifier is missing candidate {site_id}", "severity": "CRITICAL", "location": "candidates"})
                continue
            if bool(row.get("feasible")) != is_feasible:
                findings.append({"issue": f"independent feasibility check disagrees for candidate {site_id}", "severity": "CRITICAL", "location": "candidates"})
            row_cost = row.get("total_cost")
            if not isinstance(row_cost, (int, float)) or isinstance(row_cost, bool) or not math.isclose(float(row_cost), expected_cost, rel_tol=1e-9, abs_tol=1e-9):
                findings.append({"issue": f"independent objective recalculation disagrees for candidate {site_id}", "severity": "CRITICAL", "location": "candidates"})
        if selected_id in expected:
            expected_selected_cost = expected[selected_id][1]
            if not isinstance(cost, (int, float)) or isinstance(cost, bool) or not math.isclose(float(cost), expected_selected_cost, rel_tol=1e-9, abs_tol=1e-9):
                findings.append({"issue": "selected objective fails independent formula recalculation", "severity": "CRITICAL", "location": "selected_total_cost"})
        feasible_expected = {
            site_id: expected_cost
            for site_id, (is_feasible, expected_cost) in expected.items()
            if is_feasible
        }
        if feasible_expected:
            optimal_id = min(feasible_expected, key=lambda site_id: (feasible_expected[site_id], site_id))
            if selected_id != optimal_id:
                findings.append({"issue": f"selected solution is not the independently verified optimal feasible site {optimal_id}", "severity": "CRITICAL", "location": "selected_site"})
    return {
        "operation": "competition-solver-result-check",
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
    }


def check_dimensions(
    symbols: list[dict[str, Any]], equations: list[dict[str, Any]]
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    seen_symbols: dict[str, str] = {}
    seen_meanings: dict[str, str] = {}
    required = ("variable", "symbol", "meaning", "unit", "range", "source")
    for index, record in enumerate(symbols):
        missing = [field for field in required if not str(record.get(field, "")).strip()]
        if missing:
            findings.append(
                {
                    "issue": f"symbol record {index} missing {missing}",
                    "severity": "MAJOR",
                    "location": f"symbols[{index}]",
                }
            )
            continue
        symbol = str(record["symbol"])
        meaning = str(record["meaning"])
        if symbol in seen_symbols and seen_symbols[symbol] != meaning:
            findings.append(
                {
                    "issue": f"symbol {symbol} has multiple meanings",
                    "severity": "CRITICAL",
                    "location": f"symbols[{index}]",
                }
            )
        if meaning in seen_meanings and seen_meanings[meaning] != symbol:
            findings.append(
                {
                    "issue": f"meaning {meaning} has multiple symbols",
                    "severity": "MAJOR",
                    "location": f"symbols[{index}]",
                }
            )
        seen_symbols[symbol] = meaning
        seen_meanings[meaning] = symbol
    for equation in equations:
        left = str(equation.get("left_unit", "")).strip()
        right = str(equation.get("right_unit", "")).strip()
        if not left or not right or left != right:
            findings.append(
                {
                    "issue": f"dimension mismatch: {left or '<missing>'} != {right or '<missing>'}",
                    "severity": "CRITICAL" if equation.get("core") else "MAJOR",
                    "location": f"equation:{equation.get('id', '<unknown>')}",
                }
            )
    return {
        "operation": "competition-dimension-check",
        "status": "FAIL" if any(item["severity"] == "CRITICAL" for item in findings) else ("CONDITIONAL" if findings else "PASS"),
        "findings": findings,
    }


def check_numeric_consistency(
    locations: dict[str, dict[str, int | float]], *, tolerance: float = 1e-9
) -> dict[str, Any]:
    by_key: dict[str, list[tuple[str, float]]] = {}
    for location, values in locations.items():
        if not isinstance(values, dict):
            continue
        for key, value in values.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            by_key.setdefault(str(key), []).append((str(location), float(value)))
    findings: list[dict[str, Any]] = []
    for key, observations in sorted(by_key.items()):
        baseline = observations[0][1]
        if any(not math.isclose(value, baseline, rel_tol=tolerance, abs_tol=tolerance) for _, value in observations[1:]):
            findings.append(
                {
                    "issue": f"numeric result {key} is inconsistent across locations",
                    "severity": "CRITICAL",
                    "location": ", ".join(location for location, _ in observations),
                    "observations": dict(observations),
                }
            )
    return {
        "operation": "competition-numeric-consistency",
        "status": "FAIL" if findings else "PASS",
        "findings": findings,
        "checked_keys": sorted(by_key),
    }


def classify_sensitivity(
    baseline_decision: str, scenarios: list[dict[str, Any]]
) -> dict[str, Any]:
    decisions = [str(item.get("decision", "")) for item in scenarios]
    reversals = [item for item in scenarios if str(item.get("decision", "")) != baseline_decision]
    magnitude = max((abs(float(item.get("relative_change", 0.0))) for item in scenarios), default=0.0)
    if reversals:
        classification = "conclusion reversal"
    elif magnitude > 0.10 + 1e-12:
        classification = "highly sensitive"
    elif magnitude > 0.05 + 1e-12:
        classification = "moderately sensitive"
    else:
        classification = "stable"
    return {
        "operation": "competition-sensitivity-classification",
        "status": "PASS",
        "classification": classification,
        "baseline_decision": baseline_decision,
        "scenario_decisions": decisions,
        "conclusion_reversal": bool(reversals),
        "disclosure_required": bool(reversals) or classification == "highly sensitive",
    }


def check_figure_traceability(project: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    project = project.resolve()
    findings: list[str] = []
    figures = manifest.get("figures") if isinstance(manifest, dict) else None
    if not isinstance(figures, list) or not figures:
        return {"operation": "competition-figure-traceability", "status": "FAIL", "findings": ["figure manifest has no figures"]}
    for index, figure in enumerate(figures):
        for field in ("path", "source_data", "code", "artifact_sha256", "source_sha256", "code_sha256", "proves", "axis", "unit", "legend", "caption"):
            if not figure.get(field):
                findings.append(f"figures[{index}].{field} is required")
        for field, hash_field in (("path", "artifact_sha256"), ("source_data", "source_sha256"), ("code", "code_sha256")):
            raw = str(figure.get(field, ""))
            path = (project / raw).resolve()
            try:
                path.relative_to(project)
            except ValueError:
                findings.append(f"figures[{index}].{field} escapes the project")
                continue
            if not path.is_file():
                findings.append(f"figures[{index}].{field} is missing: {raw}")
            elif figure.get(hash_field) != _sha256(path):
                findings.append(f"figures[{index}].{hash_field} does not match {raw}")
    return {
        "operation": "competition-figure-traceability",
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
    }


def check_paper(project: Path) -> dict[str, Any]:
    project = project.resolve()
    state = _read(_state_dir(project) / "competition_state.json", {}) or {}
    paper = project / "paper" / "cumcm_paper.md"
    findings: list[str] = []
    if not paper.is_file():
        findings.append("contest paper is missing")
        text = ""
    else:
        text = paper.read_text(encoding="utf-8")
    for token in ("TODO", "XXX", "待补充", "fake citation"):
        if token.casefold() in text.casefold():
            findings.append(f"paper contains placeholder or invalid citation marker: {token}")
    for question in state.get("question_decomposition", []):
        question_id = str(question.get("id", ""))
        if question_id and question_id not in text:
            findings.append(f"paper does not reference {question_id}")
    abstract = text.split("## 摘要", 1)[1].split("##", 1)[0] if "## 摘要" in text else ""
    for question in state.get("question_decomposition", []):
        question_id = str(question.get("id", ""))
        if question_id and question_id not in abstract:
            findings.append(f"abstract does not report an outcome for {question_id}")
    contract = state.get("paper_contract", {})
    for term in contract.get("main_model_terms", []):
        if str(term) not in text:
            findings.append(f"paper does not define main model term: {term}")
    for symbol in contract.get("key_symbols", []):
        if str(symbol) not in text:
            findings.append(f"paper does not define key variable: {symbol}")
    for category in ("figure_files", "table_files", "cited_artifacts"):
        for relative in contract.get(category, []):
            relative = str(relative)
            path = (project / relative).resolve()
            try:
                path.relative_to(project)
            except ValueError:
                findings.append(f"paper contract path escapes project: {relative}")
                continue
            if not path.is_file():
                findings.append(f"paper contract artifact is missing: {relative}")
            if relative not in text:
                findings.append(f"paper does not cite required artifact: {relative}")
    for heading in ("摘要", "问题重述", "模型假设", "模型求解", "结果分析", "模型检验", "敏感性", "结论"):
        if heading not in text:
            findings.append(f"paper section is missing: {heading}")
    return {
        "operation": "competition-paper-check",
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
    }


def submission_preflight(project: Path) -> dict[str, Any]:
    project = project.resolve()
    state_dir = _state_dir(project)
    state = _read(state_dir / "competition_state.json", {}) or {}
    rules = (_read(state_dir / "competition_rules.json", {}) or {}).get("rules", {})
    review = _read(state_dir / "competition_review.json", {}) or {}
    findings: list[str] = []
    unverified = [
        rule_id
        for rule_id in REQUIRED_OFFICIAL_RULES
        if not isinstance(rules.get(rule_id), dict) or rules[rule_id].get("status") != "VERIFIED"
    ]
    if unverified:
        findings.append(f"official rules are not fully verified: {unverified}")
    if not state.get("selected_problem"):
        findings.append("problem selection is missing")
    questions = state.get("question_decomposition", [])
    answers = state.get("question_answers", {})
    missing_answers = [item.get("id") for item in questions if item.get("id") not in answers]
    if not questions or missing_answers:
        findings.append(f"not all questions have explicit answers: {missing_answers}")
    required_files = (
        "results/formal_solution.json",
        "tables/sensitivity.csv",
        "figures/decision_summary.svg",
        "figures/figure_manifest.json",
        "paper/cumcm_paper.md",
        "logs/formal_execution.json",
    )
    for relative in required_files:
        if not (project / relative).is_file():
            findings.append(f"required submission artifact is missing: {relative}")
    unit_report = _read(project / "results" / "unit_check.json", {}) or {}
    validation = _read(project / "results" / "validation_report.json", {}) or {}
    sensitivity = _read(project / "results" / "sensitivity_report.json", {}) or {}
    numeric = _read(project / "results" / "numeric_consistency.json", {}) or {}
    for label, report in (("unit checks", unit_report), ("validation", validation), ("sensitivity", sensitivity), ("numeric consistency", numeric)):
        if report.get("status") != "PASS":
            findings.append(f"{label} did not pass")
    figure_manifest = _read(project / "figures" / "figure_manifest.json", {}) or {}
    if check_figure_traceability(project, figure_manifest)["status"] != "PASS":
        findings.append("figure traceability did not pass")
    if check_paper(project)["status"] != "PASS":
        findings.append("deterministic paper checks did not pass")
    unresolved = [
        item
        for item in review.get("findings", [])
        if item.get("severity") in {"CRITICAL", "MAJOR"} and item.get("status", "OPEN") != "RESOLVED"
    ]
    if unresolved:
        findings.append("competition review has unresolved CRITICAL or MAJOR findings")
    status = "READY" if not findings else "BLOCKED"
    return {
        "operation": "competition-submission-preflight",
        "status": status,
        "submission_readiness": "COMPETITION_SUBMISSION_READY" if status == "READY" else "NOT_READY",
        "findings": findings,
        "unverified_rules": unverified,
        "unresolved_review_findings": len(unresolved),
    }


def completion_contract(project: Path) -> dict[str, Any]:
    preflight = submission_preflight(project)
    return {
        "operation": "competition-completion-contract",
        "status": "PASS" if preflight["status"] == "READY" else "FAIL",
        "submission_readiness": preflight["submission_readiness"],
        "checks": {
            "problem_selected": not any("problem selection" in item for item in preflight["findings"]),
            "all_questions_answered": not any("not all questions" in item for item in preflight["findings"]),
            "official_rules_verified": not preflight["unverified_rules"],
            "submission_preflight": preflight["status"] == "READY",
            "no_unresolved_critical_or_major": preflight["unresolved_review_findings"] == 0,
        },
        "findings": preflight["findings"],
    }
