"""Deterministic manuscript contract checker.

This provider is intentionally limited to checks that can be established from
local artifacts and machine-readable contracts.  Scientific judgments such as
novelty, method validity, statistical validity, writing quality, and domain
interpretation require a qualified specialist and are reported as deferred.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import provider_support as support


PROVIDER_ID = "review-provider"
DETERMINISTIC_ROLES = ("schema", "contract", "traceability", "artifact_completeness", "reproducibility")
SCIENTIFIC_REVIEW_ROLES = ("method", "statistics", "novelty", "writing", "domain")
ROLES = DETERMINISTIC_ROLES
REQUIRED = {
    "id", "role", "severity", "location", "why", "evidence", "alternative",
    "smallest_sufficient_fix", "residual_risk", "status",
}
_ARTIFACT_REF = re.compile(r"(?<![A-Za-z0-9_.-])((?:artifacts|inputs)/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*)")
_REQUIRED_HEADINGS = ("## Abstract", "## Related Work", "## Method", "## Results", "## Limitations")


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
            elif finding.get("role") not in DETERMINISTIC_ROLES:
                errors.append(f"finding {index} uses a non-deterministic review role")
            elif finding.get("status") not in {"OPEN", "RESOLVED", "RESIDUAL_RISK_DOCUMENTED"}:
                errors.append(f"finding {index} has unknown status")
    return {"status": "PASS" if not errors else "FAIL", "findings": errors}


def _finding(
    finding_id: str,
    role: str,
    severity: str,
    location: str,
    why: str,
    evidence: str,
    alternative: str,
    smallest_sufficient_fix: str,
    residual_risk: str,
) -> dict[str, Any]:
    return {
        "id": finding_id,
        "role": role,
        "severity": severity,
        "location": location,
        "why": why,
        "evidence": evidence,
        "alternative": alternative,
        "smallest_sufficient_fix": smallest_sufficient_fix,
        "residual_risk": residual_risk,
        "status": "OPEN",
    }


def execute(project: Path) -> dict[str, Any]:
    manuscript_path = project / "artifacts" / "manuscript.md"
    if not manuscript_path.is_file():
        return {"status": "FAIL", "findings": [f"manuscript artifact is missing: {manuscript_path}"]}
    text = manuscript_path.read_text(encoding="utf-8")
    if not text.strip():
        return {"status": "FAIL", "findings": ["manuscript artifact is empty"]}

    findings: list[dict[str, Any]] = []
    checks: dict[str, dict[str, Any]] = {
        role: {"status": "PASS", "findings": []} for role in DETERMINISTIC_ROLES
    }

    def add(item: dict[str, Any]) -> None:
        findings.append(item)
        checks[item["role"]]["status"] = "FAIL"
        checks[item["role"]]["findings"].append(item["id"])

    if not text.lstrip().startswith("# "):
        add(_finding(
            "CT-001", "contract", "MAJOR", "document heading",
            "The manuscript has no top-level title required by the writing artifact contract.",
            "artifacts/manuscript.md", "Add a single top-level title.",
            "Add a '# ' heading before the first section.",
            "Downstream readers and package checks may not identify the manuscript.",
        ))
    for heading in _REQUIRED_HEADINGS:
        if heading not in text:
            add(_finding(
                f"SCHEMA-{heading[3:].upper().replace(' ', '-')}", "schema", "MAJOR", heading,
                f"The manuscript is missing the required {heading} section.",
                "artifacts/manuscript.md", f"Add the {heading} section with evidence-bound content.",
                f"Add the missing {heading} heading and scoped content.",
                "The manuscript contract remains incomplete until the section is present.",
            ))
    if "## Reproducibility" not in text:
        add(_finding(
            "RF-001", "reproducibility", "MAJOR", "after Limitations",
            "The manuscript does not state the exact reproduction path.",
            "artifacts/formal_execution.json", "Provide a command, frozen inputs, and expected hashes.",
            "Add a reproducibility section tied to the execution record.",
            "Environment differences may still affect reruns.",
        ))

    references = {match.group(1).rstrip(".,;:)]}") for match in _ARTIFACT_REF.finditer(text)}
    checks["traceability"]["checked_references"] = sorted(references)
    checks["artifact_completeness"]["checked_artifacts"] = sorted(references)
    for index, relative in enumerate(sorted(references), start=1):
        candidate = (project / relative).resolve()
        try:
            candidate.relative_to(project.resolve())
        except ValueError:
            add(_finding(
                f"TR-{index:03d}", "traceability", "MAJOR", relative,
                "The manuscript references an artifact outside the project root.",
                "artifacts/manuscript.md", "Reference only project-local artifacts.",
                "Replace the path with a project-local artifact reference.",
                "The referenced evidence cannot be verified safely.",
            ))
            continue
        if not candidate.is_file() or candidate.stat().st_size == 0:
            add(_finding(
                f"AC-{index:03d}", "artifact_completeness", "MAJOR", relative,
                "The manuscript references an artifact that is missing or empty.",
                "artifacts/manuscript.md", "Create the referenced artifact or remove the unsupported reference.",
                "Materialize the artifact and record its hash before relying on it.",
                "The corresponding evidence remains unavailable to a checker.",
            ))
    check = validate_findings(findings)
    if check["status"] != "PASS":
        return {"status": "FAIL", "findings": check["findings"]}
    deterministic_status = "PASS" if not findings else "CONDITIONAL"
    artifact = support.write(project / "artifacts" / "review_findings.json", {
        "status": "PASS", "review_status": deterministic_status,
        "roles": list(DETERMINISTIC_ROLES), "findings": findings,
        "reviewed_artifact": "artifacts/manuscript.md", "checker": check,
        "checks": checks,
        "scientific_review": {
            "status": "REQUIRED",
            "completed": False,
            "roles": list(SCIENTIFIC_REVIEW_ROLES),
            "reason": "Deterministic checks cannot assess scientific validity or novelty.",
        },
    })
    return support.handoff(project, PROVIDER_ID, "review", [artifact], extra={
        "findings": findings, "checker": check, "review_status": deterministic_status,
        "scientific_review_required": True, "scientific_review_roles": list(SCIENTIFIC_REVIEW_ROLES),
    })
