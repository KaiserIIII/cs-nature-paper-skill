#!/usr/bin/env python3
"""Three-stage literature runtime: discovery, identity, and claim support."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RELATIONSHIPS = {"SUPPORTS", "PARTIALLY_SUPPORTS", "QUALIFIES", "CONTRADICTS", "DOES_NOT_SUPPORT", "INACCESSIBLE", "MISSING"}


class LiteratureError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise LiteratureError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise LiteratureError("registry must be an object")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def record_query(path: Path, query: str, provider: str, filters: str, result_count: int, rationale: str, deduplication: str) -> dict[str, Any]:
    value = _read(path) if path.exists() else {"schema_version": 3, "skill_version": "3.1.0", "queries": []}
    value.setdefault("queries", []).append({"query": query, "database_provider": provider, "date_utc": _now(), "filters": filters, "result_count": result_count, "selection_rationale": rationale, "deduplication": deduplication})
    _write(path, value)
    return {"operation": "query", "status": "PASS", "query": value["queries"][-1], "path": str(path)}


def verify_identity(path: Path, source_id: str, identity: dict[str, Any]) -> dict[str, Any]:
    registry = _read(path); sources = registry.setdefault("sources", [])
    source = next((item for item in sources if isinstance(item, dict) and item.get("source_id") == source_id), None)
    if source is None:
        source = {"source_id": source_id}; sources.append(source)
    required = ("title", "authors", "year", "venue")
    findings = [f"identity.{field} is required" for field in required if not identity.get(field)]
    if not identity.get("stable_identifier"):
        findings.append("stable_identifier is required (DOI, arXiv, DBLP, or equivalent)")
    source["identity"] = identity; source["stable_identifier"] = identity.get("stable_identifier"); source["retrieval_status"] = identity.get("retrieval_status", "RETRIEVED"); source["verification_status"] = "IDENTITY_VERIFIED" if not findings else "UNVERIFIED"
    _write(path, registry)
    return {"operation": "verify-identity", "status": "PASS" if not findings else "FAIL", "source_id": source_id, "findings": findings}


def verify_claim(path: Path, source_id: str, claim_id: str, relation: str, exact_region: str, full_text_status: str = "FULL_TEXT_INSPECTED") -> dict[str, Any]:
    registry = _read(path); sources = registry.setdefault("sources", [])
    source = next((item for item in sources if isinstance(item, dict) and item.get("source_id") == source_id), None)
    if source is None:
        raise LiteratureError(f"unknown source_id: {source_id}; verify identity first")
    findings: list[str] = []
    if relation not in RELATIONSHIPS:
        findings.append(f"relationship must be one of {sorted(RELATIONSHIPS)}")
    if relation in {"SUPPORTS", "PARTIALLY_SUPPORTS", "QUALIFIES", "CONTRADICTS", "DOES_NOT_SUPPORT"} and not exact_region.strip():
        findings.append("source-region inspection is required for a claim relationship")
    if source.get("discovery_source", "").lower() in {"snippet", "google snippet", "search result snippet"} and relation == "SUPPORTS":
        findings.append("snippet cannot support a load-bearing claim")
    claims = source.setdefault("claims_supported", []) if relation == "SUPPORTS" else source.setdefault("claims_qualified", []) if relation == "QUALIFIES" else source.setdefault("claims_contradicted", []) if relation == "CONTRADICTS" else source.setdefault("claims_not_supported", [])
    record = {"claim_id": claim_id, "relationship": relation, "exact_region": exact_region, "full_text_status": full_text_status, "verified_utc": _now()}
    claims.append(record)
    if full_text_status != "FULL_TEXT_INSPECTED" and relation == "SUPPORTS":
        source["verification_status"] = "CONDITIONAL"
        findings.append("full text was not inspected; support is conditional")
    elif not findings:
        source["verification_status"] = "CLAIM_VERIFIED"
    _write(path, registry)
    status = "FAIL" if any("snippet" in finding for finding in findings) else ("CONDITIONAL" if findings else "PASS")
    return {"operation": "verify-claim", "status": status, "source_id": source_id, "claim_id": claim_id, "relationship": relation, "findings": findings}


def audit(path: Path) -> dict[str, Any]:
    registry = _read(path); findings: list[str] = []
    for index, source in enumerate(registry.get("sources", [])):
        if not isinstance(source, dict):
            findings.append(f"sources[{index}] must be an object"); continue
        if source.get("claims_supported") and source.get("discovery_source", "").lower() in {"snippet", "google snippet", "search result snippet"}:
            findings.append(f"sources[{index}] uses a snippet as claim support")
        if source.get("verification_status") == "CLAIM_VERIFIED" and not source.get("claims_supported"):
            findings.append(f"sources[{index}] has claim-verified status without a support record")
    return {"operation": "audit", "status": "PASS" if not findings else "FAIL", "source_count": len(registry.get("sources", [])), "findings": findings}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("query"); p.add_argument("path", type=Path); p.add_argument("query"); p.add_argument("--provider", required=True); p.add_argument("--filters", default=""); p.add_argument("--result-count", type=int, default=0); p.add_argument("--rationale", default=""); p.add_argument("--deduplication", default="")
    p = sub.add_parser("verify-identity"); p.add_argument("path", type=Path); p.add_argument("source_id"); p.add_argument("identity_json", type=Path)
    p = sub.add_parser("verify-claim"); p.add_argument("path", type=Path); p.add_argument("source_id"); p.add_argument("claim_id"); p.add_argument("--relationship", required=True); p.add_argument("--exact-region", required=True); p.add_argument("--full-text-status", default="FULL_TEXT_INSPECTED")
    p = sub.add_parser("audit"); p.add_argument("path", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "query": result = record_query(args.path, args.query, args.provider, args.filters, args.result_count, args.rationale, args.deduplication)
        elif args.command == "verify-identity": result = verify_identity(args.path, args.source_id, _read(args.identity_json))
        elif args.command == "verify-claim": result = verify_claim(args.path, args.source_id, args.claim_id, args.relationship, args.exact_region, args.full_text_status)
        else: result = audit(args.path)
    except LiteratureError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False)); return 2
    print(json.dumps(result, indent=2, ensure_ascii=False)); return 0 if result["status"] in {"PASS", "CONDITIONAL"} else 1


if __name__ == "__main__": sys.exit(main())
