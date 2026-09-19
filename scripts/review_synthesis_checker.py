#!/usr/bin/env python3
"""Independently verify reviewer synthesis without producing or repairing it."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
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
    packet_id: str, reports: Any, packet_check: Any
) -> tuple[list[str], list[str]]:
    findings: list[str] = []
    if not isinstance(reports, list) or not reports:
        return ["reports must be a non-empty list"], []
    if not isinstance(packet_check, dict):
        return ["packet check must be an object"], []
    if packet_check.get("status") != "PASS":
        findings.append("packet check is not PASS")
    if packet_check.get("packet_id") != packet_id:
        findings.append("packet id mismatch")
    report_hashes: list[str] = []
    reviewer_ids: list[str] = []
    for report in reports:
        if not isinstance(report, dict):
            findings.append("every report must be an object")
            continue
        report_hashes.append(str(report.get("report_hash", "")))
        reviewer_ids.append(str(report.get("producer_id", "")))
        if report.get("packet_id") != packet_id:
            findings.append("report packet mismatch")
        if not report.get("report_id"):
            findings.append("report id is missing")
        if not isinstance(report.get("findings"), list):
            findings.append("report findings must be a list")
            continue
        for source_finding in report["findings"]:
            if not isinstance(source_finding, dict) or not source_finding.get("id"):
                findings.append("every source finding needs a stable id")
    if len(set(report_hashes)) != len(report_hashes) or any(not item for item in report_hashes):
        findings.append("reports must have unique non-empty hashes")
    packet_hashes = packet_check.get("report_hashes")
    if not isinstance(packet_hashes, list) or sorted(report_hashes) != sorted(
        str(item) for item in packet_hashes
    ):
        findings.append("packet report hashes do not match reports")
    if len(set(reviewer_ids)) != len(reviewer_ids) or any(not item for item in reviewer_ids):
        findings.append("reviewers must have unique non-empty producer ids")
    return findings, reviewer_ids


def _expected_groups(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for report in reports:
        if not isinstance(report, dict) or not isinstance(report.get("findings"), list):
            continue
        for source_finding in report["findings"]:
            if not isinstance(source_finding, dict) or not source_finding.get("id"):
                continue
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
            group["source_report_ids"].append(report.get("report_id"))
            group["source_report_hashes"].append(report.get("report_hash"))
            group["source_findings"].append(deepcopy(source_finding))
    expected: list[dict[str, Any]] = []
    for finding_id in sorted(groups):
        group = groups[finding_id]
        group["source_report_ids"] = sorted(set(group["source_report_ids"]))
        group["source_report_hashes"] = sorted(set(group["source_report_hashes"]))
        group["disagreement"] = len({_canonical(item) for item in group["source_findings"]}) > 1
        expected.append(group)
    return expected


def check_synthesis(
    artifact: dict[str, Any],
    reports: list[dict[str, Any]],
    packet_check: dict[str, Any],
    *,
    checker_id: str,
) -> dict[str, Any]:
    """Validate the candidate against a separately derived exact projection."""
    if not isinstance(artifact, dict):
        return _reject("synthesis artifact must be an object")
    findings: list[str] = []
    if artifact.get("status") != "SYNTHESIS_PRODUCED":
        findings.append("artifact was not produced by the synthesis provider")
    producer_id = artifact.get("producer_id")
    if not isinstance(producer_id, str) or not producer_id:
        findings.append("artifact synthesis producer is missing")
    if not isinstance(checker_id, str) or not checker_id:
        findings.append("checker id is missing")
    if producer_id == checker_id:
        findings.append("checker cannot be the synthesis producer")
    if artifact.get("checker_id") != checker_id:
        findings.append("artifact checker id does not match checker invocation")
    packet_id = str(artifact.get("packet_id", ""))
    input_findings, reviewer_ids = _validate_inputs(packet_id, reports, packet_check)
    findings.extend(input_findings)
    if not isinstance(reports, list) or not isinstance(packet_check, dict):
        return _reject(*findings)
    if producer_id in reviewer_ids:
        findings.append("synthesis producer cannot be a reviewer")
    if checker_id in reviewer_ids:
        findings.append("synthesis checker cannot be a reviewer")
    if artifact.get("reviewer_producer_ids") != sorted(reviewer_ids):
        findings.append("artifact reviewer producer ids do not match frozen reports")
    expected_report_hashes = sorted(
        str(report.get("report_hash", ""))
        for report in reports
        if isinstance(report, dict)
    )
    source_report_hashes = artifact.get("source_report_hashes")
    if not isinstance(source_report_hashes, list) or sorted(
        str(item) for item in source_report_hashes
    ) != expected_report_hashes:
        findings.append("artifact source report hashes do not match reports")
    expected_groups = _expected_groups(reports)
    expected_finding_ids = [group["id"] for group in expected_groups]
    source_finding_ids = artifact.get("source_finding_ids")
    if not isinstance(source_finding_ids, list) or sorted(
        str(item) for item in source_finding_ids
    ) != expected_finding_ids:
        findings.append("artifact dropped or added a source finding id")
    if artifact.get("findings") != expected_groups:
        findings.append("artifact findings do not exactly preserve source findings")
    if artifact.get("isolation_status") != packet_check.get(
        "isolation_status", "UNAVAILABLE"
    ):
        findings.append("artifact isolation status does not match packet check")
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
        "source_finding_ids": expected_finding_ids,
        "findings": [],
        "graph_transition_authorized": False,
        "publication_pass": False,
    }
