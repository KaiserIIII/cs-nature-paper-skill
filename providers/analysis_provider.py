"""Study-aware analysis and source-traceable figure provider."""

from __future__ import annotations

import math
import statistics
from pathlib import Path
from typing import Any

import provider_support as support


PROVIDER_ID = "analysis-provider"
ALLOWED_METHODS = {
    "empirical": ["descriptive_statistics", "confidence_interval", "effect_size", "bootstrap", "regression", "error_analysis", "robustness"],
    "engineering-system": ["descriptive_statistics", "confidence_interval", "time_series_diagnostics", "benchmark_aggregation", "error_analysis", "robustness"],
    "ml-benchmark": ["confidence_interval", "effect_size", "ablation_comparison", "benchmark_aggregation", "error_analysis", "robustness"],
    "observational": ["descriptive_statistics", "confidence_interval", "regression", "error_analysis", "robustness"],
}


def _study_type(project: Path) -> str:
    metadata = support.read_json(support.state_dir(project) / "project.json", {})
    return str(metadata.get("study_type") or metadata.get("type") or "empirical")


def execute(project: Path, node: str) -> dict[str, Any]:
    formal_path = project / "artifacts" / "formal_results.json"
    formal = support.read_json(formal_path, {})
    values = [float(value) for value in formal.get("values", []) if isinstance(value, (int, float)) and math.isfinite(float(value))]
    if not values:
        return {"status": "UNRESOLVED", "findings": ["formal output contains no analyzable numeric outcome"]}
    if node == "analysis":
        study = _study_type(project)
        methods = ALLOWED_METHODS.get(study)
        if not methods:
            return {"status": "UNRESOLVED", "findings": [f"method router has no analysis range for study type {study}"]}
        mean = statistics.fmean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0.0
        standard_error = stdev / math.sqrt(len(values)) if values else 0.0
        analysis = {
            "input": support.relative(project, formal_path), "input_sha256": support.digest(formal_path),
            "study_type": study, "allowed_methods": methods, "n": len(values), "mean": mean,
            "confidence_interval_95": [mean - 1.96 * standard_error, mean + 1.96 * standard_error],
            "population_stdev": statistics.pstdev(values), "sample_stdev": stdev,
            "time_series_diagnostics": {"slope": formal.get("slope"), "next_prediction": formal.get("next_prediction")},
            "method_comparison": formal.get("method_scores", {}), "selected_method": formal.get("selected_method"),
            "error_analysis": {"max_absolute_deviation": max(abs(value - mean) for value in values)},
            "robustness": {"leave_one_out_means": [statistics.fmean(values[:index] + values[index + 1:]) for index in range(len(values))] if len(values) > 1 else []},
            "claim": f"For the declared input, {formal.get('outcome', 'the outcome')} has observed mean {mean:.6g}; the selected method is {formal.get('selected_method')}.",
            "evidence": [support.digest(formal_path)],
        }
        path = support.write(project / "artifacts" / "analysis.json", analysis)
        return support.handoff(project, PROVIDER_ID, node, [path], formal=True, claims=[{"text": analysis["claim"], "scope": "declared input"}], extra={"statistics": analysis})
    if node != "figures":
        return {"status": "BLOCKED", "findings": [f"unsupported analysis node: {node}"]}
    analysis_path = project / "artifacts" / "analysis.json"
    analysis = support.read_json(analysis_path, {})
    width = max(1.0, min(300.0, abs(float(analysis.get("mean", 0.0))) * 10.0))
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="420" height="180" role="img" aria-label="Observed outcome summary">'
        f'<rect x="40" y="35" width="{width:.2f}" height="55" fill="#3264a8"/>'
        f'<text x="40" y="125">mean={analysis.get("mean")}</text>'
        f'<text x="40" y="150">method={analysis.get("selected_method")}</text></svg>\n'
    )
    figure = support.write(project / "artifacts" / "figure.svg", svg)
    provenance = support.write(project / "artifacts" / "figure_provenance.json", {
        "figure": "artifacts/figure.svg", "source_data": "artifacts/analysis.json",
        "source_sha256": support.digest(analysis_path), "generation_code": "providers/analysis_provider.py",
        "caption": "Observed outcome summary for the declared input.",
        "what_it_proves": analysis.get("claim"), "artifact_sha256": support.digest(figure), "status": "TRACEABLE",
    })
    return support.handoff(project, PROVIDER_ID, node, [figure, provenance], actions=["rendered source-traceable figure"])
