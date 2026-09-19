#!/usr/bin/env python3
"""Produce and independently check V4.1 reviewer-synthesis artifacts."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from copy import deepcopy
from pathlib import Path
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
    if not isinstance(reports, list) or not reports:
        return ["reports must be a non-empty list"]
    if not isinstance(packet_check, dict):
        return ["packet check must be an object"]
    if packet_check.get("status") != "PASS":
        findings.append("packet check is not PASS")
    if packet_check.get("packet_id") != packet_id:
        findings.append("packet id mismatch")
    if any(not isinstance(report, dict) for report in reports):
        return ["every report must be an object"]
    report_hashes = [str(report.get("report_hash", "")) for report in reports]
    if len(set(report_hashes)) != len(report_hashes) or any(not item for item in report_hashes):
        findings.append("reports must have unique non-empty hashes")
    packet_hashes = packet_check.get("report_hashes")
    if not isinstance(packet_hashes, list) or sorted(report_hashes) != sorted(
        str(item) for item in packet_hashes
    ):
        findings.append("packet report hashes do not match reports")
    reviewer_ids = [str(report.get("producer_id", "")) for report in reports]
    if len(set(reviewer_ids)) != len(reviewer_ids) or any(not item for item in reviewer_ids):
        findings.append("reviewers must have unique non-empty producer ids")
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
    findings = _validate_inputs(packet_id, reports, packet_check)
    if findings:
        return _reject(*findings)
    reviewer_ids = {
        str(report.get("producer_id", ""))
        for report in reports
        if isinstance(report, dict)
    }
    if not synthesis_provider_id or not checker_id:
        return _reject("synthesis producer and checker ids must be non-empty")
    if synthesis_provider_id == checker_id:
        return _reject("synthesis producer and checker must be distinct")
    if synthesis_provider_id in reviewer_ids:
        return _reject("synthesis producer cannot be a reviewer")
    if checker_id in reviewer_ids:
        return _reject("synthesis checker cannot be a reviewer")

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
            group["source_findings"].append(deepcopy(source_finding))
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
        "reviewer_producer_ids": sorted(
            str(report["producer_id"]) for report in reports
        ),
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
    """Compatibility entry that delegates to the independent checker module."""
    path = Path(__file__).with_name("review_synthesis_checker.py")
    spec = importlib.util.spec_from_file_location("review_synthesis_checker", path)
    if spec is None or spec.loader is None:
        return _reject("independent synthesis checker is unavailable")
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    return checker.check_synthesis(
        artifact,
        reports,
        packet_check,
        checker_id=checker_id,
    )
