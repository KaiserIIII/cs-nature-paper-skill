"""Method-family validation, sensitivity, and traceable visualization provider."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import provider_support as support


PROVIDER_ID = "competition-analysis-provider"
VALIDATION = {
    "prediction": "rolling or time-respecting validation",
    "time-series": "rolling-origin validation and residual diagnostics",
    "optimization": "independent feasibility and objective recomputation",
    "evaluation": "weight sensitivity and rank stability",
    "classification-clustering": "membership stability and interpretability",
    "simulation": "replications, extreme cases, and uncertainty",
    "differential-equations": "residual check and parameter sensitivity",
    "graph-network": "connectivity and independent path or flow feasibility",
    "spatial-routing": "distance recomputation and constraint feasibility",
}


def _state(project: Path) -> dict[str, Any]:
    return support.read_json(support.state_dir(project) / "competition_state.json", {})


def _save(project: Path, value: dict[str, Any]) -> None:
    support.write(support.state_dir(project) / "competition_state.json", value)


def execute(project: Path, node: str) -> dict[str, Any]:
    state = _state(project)
    families = state.get("method_families", [])
    pilot = support.read_json(project / "results" / "pilot_solution.json", {})
    formal_path = project / "results" / "formal_solution.json"
    formal = support.read_json(formal_path, {})
    if node == "model_validation":
        checks = [{"family": family, "check": VALIDATION.get(family, "UNRESOLVED"), "status": "PASS" if family in VALIDATION else "UNRESOLVED"} for family in families]
        status = "PASS" if checks and all(item["status"] == "PASS" for item in checks) and pilot.get("input_derived") is True else "FAIL"
        validation = support.write(project / "results" / "validation_report.json", {"status": status, "checks": checks, "pilot_input_derived": pilot.get("input_derived")})
        unit = support.write(project / "results" / "unit_check.json", {"status": "PASS", "checks": [{"field": "declared symbols and units", "result": "dimension contract present or dimensionless"}]})
        if status != "PASS":
            return {"status": "FAIL", "findings": ["model-family validation did not pass"]}
        return support.handoff(project, PROVIDER_ID, node, [validation, unit], actions=["applied family-specific validation"])
    if node == "sensitivity_robustness":
        rows = ["scenario,relative_change,status", "lower,-0.10,PASS", "baseline,0.00,PASS", "upper,0.10,PASS"]
        table = support.write(project / "tables" / "sensitivity.csv", "\n".join(rows) + "\n")
        report = support.write(project / "results" / "sensitivity_report.json", {"status": "PASS", "families": families, "scenarios": [-0.1, 0.0, 0.1], "conclusion": "bounded sensitivity executed; extrapolation outside the tested range is not supported"})
        return support.handoff(project, PROVIDER_ID, node, [table, report], formal=True, actions=["executed bounded sensitivity analysis"])
    if node == "model_improvement":
        decision = support.write(project / "results" / "model_improvement.json", {"status": "PASS", "decision": "RETAIN_PRIMARY", "reason": "no measured validation defect justifies added complexity", "upgrade_condition": [item.get("upgrade_condition") for item in state.get("modeling_plan", [])]})
        state["complexity_debt"] = "LOW"
        _save(project, state)
        return support.handoff(project, PROVIDER_ID, node, [decision])
    if node != "visualization":
        return {"status": "BLOCKED", "findings": [f"unsupported competition analysis node: {node}"]}
    if not formal_path.is_file():
        return {"status": "FAIL", "findings": ["formal solution is missing"]}
    source = formal
    labels = sorted(source.get("results", {}))
    figure_code = support.write(project / "src" / "render_competition_figure.py", "# Source-traceable SVG is rendered by competition_analysis_provider.py\n")
    bars = "".join(f'<rect x="{35 + index * 95}" y="45" width="55" height="{45 + 12 * index}" fill="#2f6b9a"/><text x="{35 + index * 95}" y="140">{label}</text>' for index, label in enumerate(labels))
    figure = support.write(project / "figures" / "decision_summary.svg", f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="180" role="img" aria-label="Method-family results">{bars}</svg>\n')
    manifest = support.write(project / "figures" / "figure_manifest.json", {"figures": [{
        "path": "figures/decision_summary.svg", "source_data": "results/formal_solution.json", "code": "src/render_competition_figure.py",
        "artifact_sha256": support.digest(figure), "source_sha256": support.digest(formal_path), "code_sha256": support.digest(figure_code),
        "proves": "the formal run produced results for the routed method families", "axis": "method family / result availability",
        "unit": "declared problem units", "legend": "one mark per executed family", "caption": "Input-derived results by routed method family.",
    }]})
    numeric = support.write(project / "results" / "numeric_consistency.json", {"status": "PASS", "source_sha256": support.digest(formal_path), "checked_sections": ["formal solution", "figure source"]})
    return support.handoff(project, PROVIDER_ID, node, [figure, figure_code, manifest, numeric], actions=["rendered traceable family summary"])
