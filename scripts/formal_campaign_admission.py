#!/usr/bin/env python3
"""Validate scientific semantics before a formal campaign scales out."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SKILL_VERSION = "4.0.0"
REQUIRED_METHOD_CLASSES = {"SOURCE", "ADAPTIVE", "RECOVERY"}
REQUIRED_TRAJECTORIES = {"A-B-A", "A-B-C-A"}
REQUIRED_IDENTITIES = {"runner", "manifest", "dataset", "checkpoints", "environment", "protocol"}


def _sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 71
        and value.startswith("sha256:")
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def evaluate(record: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    if not record.get("campaign_id"):
        findings.append("campaign_id is required")
    if not isinstance(record.get("planned_jobs"), int) or record["planned_jobs"] < 1:
        findings.append("planned_jobs must be a positive integer")

    canary = record.get("semantic_canary", {})
    if canary.get("status") != "PASS":
        findings.append("semantic canary did not pass")
    coverage = canary.get("coverage", {})
    missing_classes = REQUIRED_METHOD_CLASSES - set(coverage.get("method_classes", []))
    if missing_classes:
        findings.append(f"semantic canary misses method classes: {sorted(missing_classes)}")
    missing_trajectories = REQUIRED_TRAJECTORIES - set(coverage.get("trajectories", []))
    if missing_trajectories:
        findings.append(f"semantic canary misses trajectories: {sorted(missing_trajectories)}")
    if len(set(coverage.get("seeds", []))) < 2:
        findings.append("semantic canary requires at least two seeds where practical")
    if not coverage.get("shifts"):
        findings.append("semantic canary requires a representative shift and severity")

    source = canary.get("source_immutability", {})
    source_checks = {
        "state_dict_identical": "source state_dict changed",
        "bn_running_mean_identical": "source BatchNorm running_mean changed",
        "bn_running_var_identical": "source BatchNorm running_var changed",
    }
    for field, message in source_checks.items():
        if source.get(field) is not True:
            findings.append(message)
    if source.get("optimizer_step_count") != 0:
        findings.append("source optimizer step count is not zero")
    if source.get("trainable_parameter_delta") != 0.0:
        findings.append("source trainable parameter delta is not zero")
    if source.get("entered_mutating_train_mode") is not False:
        findings.append("source entered a state-mutating train mode")

    contracts = record.get("method_state_contracts", {})
    if contracts.get("status") != "PASS" or not contracts.get("methods"):
        findings.append("method state-transition contracts did not pass")
    for method, outcome in contracts.get("methods", {}).items():
        if outcome.get("unexpected_mutations"):
            findings.append(f"{method} has unexpected state mutations")

    temporal = record.get("temporal_availability", {})
    if temporal.get("status") != "PASS" or temporal.get("all_measurement_steps_precede_outcomes") is not True:
        findings.append("prospective variables must satisfy measurement_time < outcome_time")
    if not isinstance(temporal.get("prospective_events_checked"), int) or temporal["prospective_events_checked"] < 1:
        findings.append("no prospective event IDs were checked")

    provenance = record.get("provenance_binding", {})
    if provenance.get("status") != "PASS" or provenance.get("all_shards_bound") is not True:
        findings.append("result shards are not all bound to the frozen campaign identity")
    frozen = provenance.get("frozen_hashes", {})
    missing_identities = REQUIRED_IDENTITIES - set(frozen)
    if missing_identities:
        findings.append(f"frozen provenance misses identities: {sorted(missing_identities)}")
    for name in REQUIRED_IDENTITIES & set(frozen):
        if not _sha256(frozen[name]):
            findings.append(f"frozen provenance identity is invalid: {name}")

    early = record.get("early_sanity_audit", {})
    if early.get("status") != "PASS" or not isinstance(early.get("completed_jobs_checked"), int) or early.get("completed_jobs_checked", 0) < 1:
        findings.append("early online sanity audit did not inspect completed formal jobs")
    for field in ("metric_ranges_valid", "event_order_valid", "provenance_valid", "state_mutations_valid"):
        if early.get(field) is not True:
            findings.append(f"early online sanity failed: {field}")

    passed = not findings
    return {
        "operation": "formal-campaign-admission",
        "skill_version": SKILL_VERSION,
        "status": "FORMAL_ADMISSION_PASS" if passed else "FORMAL_ADMISSION_FAIL",
        "scale_out_authorized": passed,
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    args = parser.parse_args(argv)
    result = evaluate(json.loads(args.record.read_text(encoding="utf-8")))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["scale_out_authorized"] else 1


if __name__ == "__main__":
    sys.exit(main())
