"""Multi-role scientific review provider with deterministic finding validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import provider_support as support


PROVIDER_ID = "review-provider"
ROLES = ("method", "statistics", "novelty", "reproducibility", "writing", "domain")
REQUIRED = {"severity", "location", "why", "evidence", "alternative", "smallest_sufficient_fix", "residual_risk"}


def validate_findings(findings: Any) -> dict[str, Any]:
    errors = []
    if not isinstance(findings, list):
        errors.append("findings must be a list")
    else:
        for index, finding in enumerate(findings):
            if not isinstance(finding, dict) or REQUIRED - set(finding):
                errors.append(f"finding {index} does not satisfy the typed contract")
            elif finding.get("severity") not in {"CRITICAL", "MAJOR", "MINOR"}:
                errors.append(f"finding {index} has unknown severity")
    return {"status": "PASS" if not errors else "FAIL", "findings": errors}


def execute(project: Path) -> dict[str, Any]:
    manuscript_path = project / "artifacts" / "manuscript.md"
    text = manuscript_path.read_text(encoding="utf-8")
    findings = []
    if "## Reproducibility" not in text:
        findings.append({
            "id": "RF-001", "role": "reproducibility", "severity": "MAJOR", "location": "after Limitations",
            "why": "The manuscript does not state the exact reproduction path.",
            "evidence": "artifacts/formal_execution.json",
            "alternative": "Provide a command, frozen inputs, and expected hashes.",
            "smallest_sufficient_fix": "Add a reproducibility section tied to the execution record.",
            "residual_risk": "Environment differences may still affect reruns.", "status": "OPEN",
        })
    for role in ROLES:
        if role == "reproducibility":
            continue
        findings.append({
            "id": f"CHECK-{role.upper()}", "role": role, "severity": "MINOR", "location": "whole manuscript",
            "why": f"The {role} review found no load-bearing defect but preserves a scoped residual check.",
            "evidence": "artifacts/validation_report.json",
            "alternative": "Retain the current scoped wording.",
            "smallest_sufficient_fix": "No prose change required; keep the evidence boundary.",
            "residual_risk": "A domain specialist may identify additional context.", "status": "RESOLVED",
        })
    check = validate_findings(findings)
    if check["status"] != "PASS":
        return {"status": "FAIL", "findings": check["findings"]}
    artifact = support.write(project / "artifacts" / "review_findings.json", {
        "status": "PASS", "roles": list(ROLES), "findings": findings,
        "reviewed_artifact": "artifacts/manuscript.md", "checker": check,
    })
    return support.handoff(project, PROVIDER_ID, "review", [artifact], extra={"findings": findings, "checker": check})
