#!/usr/bin/env python3
"""Validate and score hash-bound, counterbalanced Research OS comparisons."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SKILL_VERSION = "4.0.0"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = ROOT / "assets" / "evals" / "v4" / "research_os_benchmarks.json"
SYSTEM_IDS = {
    "ars",
    "k_dense",
    "ai_scientist",
    "paper_orchestra",
    "sisyphus_academica",
    "research_engineering_suite",
}
VERDICTS = {"BENCHMARK_BETTER", "TIE", "V4_BETTER"}


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load_suite(path: Path | None = None) -> dict[str, Any]:
    return _read(path or DEFAULT_SUITE)


def validate_suite(suite: Any, *, root: Path = ROOT) -> list[str]:
    if not isinstance(suite, dict):
        return ["suite root must be an object"]
    findings: list[str] = []
    if suite.get("skill_version") != SKILL_VERSION:
        findings.append(f"skill_version must be {SKILL_VERSION}")
    systems = suite.get("systems")
    if not isinstance(systems, list):
        return findings + ["systems must be a list"]
    ids = {item.get("id") for item in systems if isinstance(item, dict)}
    if ids != SYSTEM_IDS:
        findings.append(f"benchmark system set mismatch: {sorted(str(item) for item in ids)}")
    prohibited = {"agent_count", "code_size", "skill_count", "architecture_score"}
    for index, item in enumerate(systems):
        if not isinstance(item, dict):
            findings.append(f"systems[{index}] must be an object")
            continue
        prefix = f"systems[{index}]"
        for field in (
            "id",
            "name",
            "repository",
            "exact_commit",
            "license",
            "use_decision",
            "strongest_capabilities",
            "behavior_task",
            "parity_dimensions",
            "superiority_dimensions",
        ):
            if not item.get(field):
                findings.append(f"{prefix}.{field} is required")
        commit = item.get("exact_commit", "")
        if not isinstance(commit, str) or len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit):
            findings.append(f"{prefix}.exact_commit must be a lowercase 40-character SHA")
        dimensions = set(item.get("parity_dimensions", [])) | set(item.get("superiority_dimensions", []))
        overlap = dimensions & prohibited
        if overlap:
            findings.append(f"{prefix} uses prohibited proxy dimensions: {sorted(overlap)}")
        task = item.get("behavior_task", {})
        for relative in task.get("public_inputs", []) if isinstance(task, dict) else []:
            if not (root / relative).is_file():
                findings.append(f"{prefix} public input is missing: {relative}")
    ars = next((item for item in systems if item.get("id") == "ars"), {})
    if ars.get("license") != "CC-BY-NC-4.0" or ars.get("use_decision") != "BENCHMARK_ONLY_DO_NOT_VENDOR":
        findings.append("ARS must remain CC-BY-NC-4.0 benchmark-only material")
    return findings


def _system_result(system: dict[str, Any], run_root: Path) -> dict[str, Any]:
    system_id = system["id"]
    run = run_root / system_id
    required_files = {
        "manifest": run / "run_manifest.json",
        "benchmark_output": run / "benchmark_output.json",
        "v4_output": run / "v4_output.json",
        "judge_ab": run / "judge_ab.json",
        "judge_ba": run / "judge_ba.json",
    }
    missing = [name for name, path in required_files.items() if not path.is_file()]
    if missing:
        return {
            "system_id": system_id,
            "status": "NOT_RUN",
            "parity_gate": "FAIL",
            "superiority_gate": "FAIL",
            "findings": [f"{system_id}: NOT_RUN missing {', '.join(missing)}"],
        }
    try:
        manifest = _read(required_files["manifest"])
        judges = [_read(required_files["judge_ab"]), _read(required_files["judge_ba"])]
    except (OSError, json.JSONDecodeError) as exc:
        return {"system_id": system_id, "status": "FAIL", "findings": [f"{system_id}: invalid run artifact: {exc}"]}
    findings: list[str] = []
    hashes = {
        "benchmark": _sha256(required_files["benchmark_output"]),
        "v4": _sha256(required_files["v4_output"]),
    }
    if manifest.get("status") != "COMPLETED":
        findings.append(f"{system_id}: producer run is not COMPLETED")
    if manifest.get("system_id") != system_id or manifest.get("task_id") != system["behavior_task"]["id"]:
        findings.append(f"{system_id}: run identity mismatch")
    producers = manifest.get("producer_runs", {})
    for side in ("benchmark", "v4"):
        producer = producers.get(side, {}) if isinstance(producers, dict) else {}
        if not producer.get("model") or producer.get("output_sha256") != hashes[side]:
            findings.append(f"{system_id}: {side} producer is not bound to the output hash")
    expected_orders = (["benchmark", "v4"], ["v4", "benchmark"])
    all_dimensions = set(system["parity_dimensions"]) | set(system["superiority_dimensions"])
    for judge, expected_order in zip(judges, expected_orders):
        if judge.get("status") != "COMPLETED" or not judge.get("judge_model"):
            findings.append(f"{system_id}: incomplete blind judge record")
        if judge.get("order") != expected_order:
            findings.append(f"{system_id}: counterbalanced order mismatch")
        if judge.get("input_sha256") != hashes:
            findings.append(f"{system_id}: judge inputs are not hash-bound")
        verdicts = judge.get("verdicts", {})
        evidence = judge.get("evidence", {})
        for dimension in all_dimensions:
            if verdicts.get(dimension) not in VERDICTS:
                findings.append(f"{system_id}: missing verdict for {dimension}")
            if not str(evidence.get(dimension, "")).strip():
                findings.append(f"{system_id}: missing judgment evidence for {dimension}")
    parity = "PASS"
    superiority = "PASS"
    if findings:
        parity = superiority = "FAIL"
    else:
        for dimension in system["parity_dimensions"]:
            if any(judge["verdicts"][dimension] == "BENCHMARK_BETTER" for judge in judges):
                parity = "FAIL"
                findings.append(f"{system_id}: parity loss on {dimension}")
        for dimension in system["superiority_dimensions"]:
            if any(judge["verdicts"][dimension] != "V4_BETTER" for judge in judges):
                superiority = "FAIL"
                findings.append(f"{system_id}: superiority not demonstrated on {dimension}")
    return {
        "system_id": system_id,
        "status": "PASS" if parity == superiority == "PASS" else "FAIL",
        "parity_gate": parity,
        "superiority_gate": superiority,
        "output_sha256": hashes,
        "findings": findings,
    }


def evaluate_run(suite: dict[str, Any], run_root: Path) -> dict[str, Any]:
    suite_findings = validate_suite(suite)
    results = [_system_result(system, run_root) for system in suite.get("systems", [])] if not suite_findings else []
    findings = suite_findings + [finding for result in results for finding in result["findings"]]
    parity = "PASS" if results and all(result["parity_gate"] == "PASS" for result in results) else "FAIL"
    superiority = "PASS" if results and all(result["superiority_gate"] == "PASS" for result in results) else "FAIL"
    ars_result = next((result for result in results if result["system_id"] == "ars"), None)
    ars_parity = ars_result["parity_gate"] if ars_result else "FAIL"
    rc = "PASS" if parity == superiority == "PASS" else "FAIL"
    return {
        "suite_id": suite.get("suite_id"),
        "multi_system_parity_gate": parity,
        "ars_parity_gate": ars_parity,
        "v4_superiority_gate": superiority,
        "rc_status": rc,
        "recommended_merge": "YES" if rc == "PASS" else "NO",
        "systems": results,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("run_root", type=Path)
    args = parser.parse_args()
    suite = load_suite()
    result = {"status": "PASS" if not validate_suite(suite) else "FAIL", "findings": validate_suite(suite)} if args.command == "validate" else evaluate_run(suite, args.run_root)
    print(json.dumps(result, indent=2))
    return 0 if result.get("status", result.get("rc_status")) == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
