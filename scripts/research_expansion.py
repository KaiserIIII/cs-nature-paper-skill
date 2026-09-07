#!/usr/bin/env python3
"""Translate publication insufficiency into a verified research campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_VERSION = "4.0.0"


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _package(
    package_id: str,
    capability: str,
    depends_on: list[str],
    claim_impact: str,
    artifact_names: list[str],
) -> dict[str, Any]:
    root = f".research-state/v4-expansion/{package_id}"
    return {
        "id": package_id,
        "capability": capability,
        "status": "PLANNED",
        "depends_on": depends_on,
        "command": f"python scripts/research_expansion.py run-package PROJECT --package {package_id}",
        "expected_artifacts": [f"{root}/{name}" for name in artifact_names],
        "checker": f"independent-{capability}-checker",
        "checker_receipt": f"{root}/checker_receipt.json",
        "claim_impact": claim_impact,
        "failure_policy": "preserve logs and partial artifacts; bounded retry; never promote partial evidence",
    }


def build_campaign(assessment: dict[str, Any], *, project_id: str) -> dict[str, Any]:
    findings = sorted({str(item) for item in assessment.get("findings", [])})
    packages = [
        _package("closest_work_expansion", "literature-and-prior-art", [], "bounds novelty against the closest current work", ["search_protocol.json", "closest_work_matrix.json"]),
        _package("dataset_benchmark_expansion", "dataset-benchmark-selection", [], "tests external validity beyond the pilot dataset", ["dataset_audit.json", "benchmark_manifest.json"]),
        _package("model_architecture_expansion", "implementation", ["dataset_benchmark_expansion"], "tests whether the phenomenon survives a publication-relevant model", ["implementation_tests.json", "model_manifest.json"]),
        _package("modern_baseline_expansion", "formal-experiment-execution", ["dataset_benchmark_expansion", "model_architecture_expansion"], "compares against current and strong simple baselines", ["protocol.json", "results_manifest.json"]),
        _package("mechanism_timing_repair", "theory-and-mechanism", ["dataset_benchmark_expansion", "model_architecture_expansion"], "measures predictors before the outcome and tests rival mechanisms", ["temporal_dag.json", "prospective_results.json"]),
        _package("ablation_matrix", "experimental-design", ["modern_baseline_expansion", "mechanism_timing_repair"], "isolates which components and budgets cause the observed effect", ["ablation_protocol.json", "ablation_results.json"]),
        _package("statistical_analysis", "statistics", ["modern_baseline_expansion", "mechanism_timing_repair", "ablation_matrix"], "quantifies effects, uncertainty, multiplicity, and robustness from actual results", ["analysis.json", "tables.json"]),
        _package("publication_figures", "scientific-visualization", ["statistical_analysis"], "shows the main effect, mechanism, uncertainty, and failure boundaries", ["figure_manifest.json", "figures.pdf"]),
        _package("adversarial_review", "peer-review", ["closest_work_expansion", "statistical_analysis", "publication_figures"], "turns reviewer attacks into evidence-bound required actions", ["review_findings.json", "required_experiments.json"]),
        _package("manuscript_revision", "scientific-writing", ["adversarial_review"], "revises every claim and section against completed evidence and review", ["claim_citation_matrix.json", "full_paper.pdf"]),
    ]
    return {
        "schema_version": "1.0.0",
        "skill_version": SKILL_VERSION,
        "campaign_id": f"{project_id}-publication-expansion-v1",
        "project_id": project_id,
        "created_utc": _utc(),
        "trigger_disposition": assessment.get("disposition"),
        "trigger_findings": findings,
        "status": "PLANNED",
        "submission_readiness": "FAIL",
        "resource_policy": {
            "background_execution": True,
            "checkpoint_required": True,
            "resume_required": True,
            "bounded_retries": 2,
            "preserve_failed_runs": True,
            "seeds": "fixed and recorded per protocol",
            "environment_snapshot": "required before formal execution"
        },
        "work_packages": packages,
        "completion_rule": "all artifacts must exist, match checker-recorded SHA-256 values, and pass independent checks; then rerun publication gates",
    }


def _verified(package: dict[str, Any], project: Path) -> tuple[bool, list[str]]:
    missing = [relative for relative in package["expected_artifacts"] if not (project / relative).is_file()]
    receipt_path = project / package["checker_receipt"]
    if not receipt_path.is_file():
        missing.append(package["checker_receipt"])
        return False, missing
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, missing + [f"{package['checker_receipt']}:invalid"]
    if receipt.get("status") != "PASS":
        return False, missing + [f"{package['checker_receipt']}:not-pass"]
    expected_hashes = receipt.get("artifact_sha256", {})
    for relative in package["expected_artifacts"]:
        path = project / relative
        if path.is_file():
            actual = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            if expected_hashes.get(relative) != actual:
                missing.append(f"{relative}:hash-mismatch")
    return not missing, missing


def verify_campaign(campaign: dict[str, Any], project: Path) -> dict[str, Any]:
    completed: set[str] = set()
    missing: list[str] = []
    for package in campaign.get("work_packages", []):
        passed, package_missing = _verified(package, project)
        if passed:
            completed.add(package["id"])
        else:
            missing.extend(package_missing)
    ready = [
        package["id"]
        for package in campaign.get("work_packages", [])
        if package["id"] not in completed and set(package["depends_on"]).issubset(completed)
    ]
    all_complete = bool(campaign.get("work_packages")) and len(completed) == len(campaign["work_packages"])
    return {
        "status": "PASS" if all_complete else "FAIL",
        "campaign_id": campaign.get("campaign_id"),
        "completed_packages": sorted(completed),
        "ready_packages": ready,
        "missing_artifacts": sorted(set(missing)),
        "disposition": "REASSESS_PUBLICATION_GATES" if all_complete else "EXPAND_RESEARCH",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("assessment", type=Path)
    build.add_argument("output", type=Path)
    build.add_argument("--project-id", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("campaign", type=Path)
    verify.add_argument("project", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        campaign = build_campaign(json.loads(args.assessment.read_text(encoding="utf-8")), project_id=args.project_id)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(campaign, indent=2) + "\n", encoding="utf-8")
        result = {"status": "PASS", "campaign": str(args.output)}
    else:
        result = verify_campaign(json.loads(args.campaign.read_text(encoding="utf-8")), args.project)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
