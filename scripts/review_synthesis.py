#!/usr/bin/env python3
"""Produce and independently check V4.1 reviewer-synthesis artifacts."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _reject(*findings: str) -> dict[str, Any]:
    return {
        "status": "SYNTHESIS_REJECTED",
        "findings": list(findings),
        "graph_transition_authorized": False,
        "publication_pass": False,
    }


def _validate_inputs(
    packet_id: str, reports: list[dict[str, Any]], packet_check: dict[str, Any]
) -> list[str]:
    findings: list[str] = []
    if packet_check.get("status") != "PASS":
        findings.append("packet check is not PASS")
    if packet_check.get("packet_id") != packet_id:
        findings.append("packet id mismatch")
    report_hashes = [str(report.get("report_hash", "")) for report in reports]
    if len(set(report_hashes)) != len(report_hashes) or any(not item for item in report_hashes):
        findings.append("reports must have unique non-empty hashes")
    if sorted(report_hashes) != sorted(str(item) for item in packet_check.get("report_hashes", [])):
        findings.append("packet report hashes do not match reports")
    for report in reports:
        if report.get("packet_id") != packet_id:
            findings.append("report packet mismatch")
        if not report.get("report_id"):
            findings.append("report id is missing")
        if not isinstance(report.get("findings"), list):
            findings.append("report findings must be a list")
        for finding in report.get("findings", []):
            if not isinstance(finding, dict) or not finding.get("id"):
                findings.append("every source finding needs a stable id")
    return findings


def produce_synthesis(
    packet_id: str,
    reports: list[dict[str, Any]],
    packet_check: dict[str, Any],
    *,
    synthesis_provider_id: str,
    checker_id: str,
) -> dict[str, Any]:
    """Create a synthesis artifact; this is the only function that produces it."""
    if synthesis_provider_id == checker_id:
        return _reject("synthesis producer and checker must be distinct")
    findings = _validate_inputs(packet_id, reports, packet_check)
    if findings:
        return _reject(*findings)

    groups: dict[str, dict[str, Any]] = {}
    for report in reports:
        for source_finding in report["findings"]:
            finding_id = str(source_finding["id"])
            group = groups.setdefault(
                finding_id,
                {
                    "id": finding_id,
                    "source_report_ids": [],
                    "source_report_hashes": [],
                    "source_findings": [],
                },
            )
            group["source_report_ids"].append(report["report_id"])
            group["source_report_hashes"].append(report["report_hash"])
            group["source_findings"].append(source_finding)
    grouped = []
    for finding_id in sorted(groups):
        group = groups[finding_id]
        variants = {_canonical(item) for item in group["source_findings"]}
        group["source_report_ids"] = sorted(set(group["source_report_ids"]))
        group["source_report_hashes"] = sorted(set(group["source_report_hashes"]))
        group["disagreement"] = len(variants) > 1
        grouped.append(group)
    artifact: dict[str, Any] = {
        "status": "SYNTHESIS_PRODUCED",
        "packet_id": packet_id,
        "producer_id": synthesis_provider_id,
        "checker_id": checker_id,
        "source_report_hashes": sorted(str(report["report_hash"]) for report in reports),
        "source_finding_ids": sorted(groups),
        "findings": grouped,
        "isolation_status": packet_check.get("isolation_status", "UNAVAILABLE"),
        "graph_transition_authorized": False,
        "publication_pass": False,
    }
    artifact["synthesis_hash"] = _hash(artifact)
    return artifact


def check_synthesis(
    artifact: dict[str, Any],
    reports: list[dict[str, Any]],
    packet_check: dict[str, Any],
    *,
    checker_id: str,
) -> dict[str, Any]:
    """Validate an existing artifact without mutating or generating it."""
    findings: list[str] = []
    if not isinstance(artifact, dict):
        return _reject("synthesis artifact must be an object")
    if artifact.get("status") != "SYNTHESIS_PRODUCED":
        findings.append("artifact was not produced by the synthesis provider")
    if artifact.get("producer_id") == checker_id:
        findings.append("checker cannot be the synthesis producer")
    if artifact.get("checker_id") != checker_id:
        findings.append("artifact checker id does not match checker invocation")
    packet_id = str(artifact.get("packet_id", ""))
    findings.extend(_validate_inputs(packet_id, reports, packet_check))
    expected_report_hashes = sorted(str(report["report_hash"]) for report in reports)
    if sorted(str(item) for item in artifact.get("source_report_hashes", [])) != expected_report_hashes:
        findings.append("artifact source report hashes do not match reports")
    expected_finding_ids = sorted(
        str(source_finding["id"])
        for report in reports
        for source_finding in report.get("findings", [])
        if isinstance(source_finding, dict) and source_finding.get("id")
    )
    expected_unique_ids = sorted(set(expected_finding_ids))
    if sorted(str(item) for item in artifact.get("source_finding_ids", [])) != expected_unique_ids:
        findings.append("artifact dropped or added a source finding")
    if artifact.get("graph_transition_authorized") is not False:
        findings.append("synthesis cannot authorize a graph transition")
    if artifact.get("publication_pass") is not False:
        findings.append("synthesis cannot mark publication PASS")
    unsigned = dict(artifact)
    unsigned.pop("synthesis_hash", None)
    if artifact.get("synthesis_hash") != _hash(unsigned):
        findings.append("synthesis hash mismatch")
    if findings:
        return _reject(*findings)
    status = (
        "SYNTHESIS_ACCEPTED"
        if packet_check.get("isolation_status") == "AVAILABLE"
        else "SYNTHESIS_CONDITIONAL"
    )
    return {
        "status": status,
        "checker_id": checker_id,
        "artifact_hash": artifact["synthesis_hash"],
        "source_report_hashes": expected_report_hashes,
        "source_finding_ids": expected_unique_ids,
        "findings": [],
        "graph_transition_authorized": False,
        "publication_pass": False,
    }
