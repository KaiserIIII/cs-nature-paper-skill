#!/usr/bin/env python3
"""Record literature discovery separately from identity and claim verification."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SKILL_VERSION = "3.1.1"
RELATIONSHIPS = {"SUPPORTS", "PARTIALLY_SUPPORTS", "QUALIFIES", "CONTRADICTS", "DOES_NOT_SUPPORT", "INACCESSIBLE", "MISSING"}
FULL_TEXT = {"FULL_TEXT_INSPECTED", "ABSTRACT_ONLY", "SNIPPET_ONLY", "NOT_RETRIEVED"}


class LiteratureError(RuntimeError):
    pass


def _now() -> str: return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
def _read(path: Path) -> dict[str, Any]:
    try: value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc: raise LiteratureError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict): raise LiteratureError("registry must be an object")
    return value
def _write(path: Path, value: dict[str, Any]) -> None: path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def record_query(path: Path, query: str, provider: str, filters: str, result_count: int, rationale: str, deduplication: str) -> dict[str, Any]:
    value = _read(path) if path.exists() else {"schema_version": 3, "skill_version": SKILL_VERSION, "queries": [], "sources": []}
    value.setdefault("queries", []).append({"query": query, "database_provider": provider, "date_utc": _now(), "filters": filters, "result_count": result_count, "selection_rationale": rationale, "deduplication": deduplication, "verification_status": "DISCOVERED"})
    _write(path, value); return {"operation": "query", "status": "PASS", "query": value["queries"][-1], "path": str(path)}


def verify_identity(path: Path, source_id: str, identity: dict[str, Any]) -> dict[str, Any]:
    registry = _read(path); sources = registry.setdefault("sources", []); source = next((item for item in sources if isinstance(item, dict) and item.get("source_id") == source_id), None)
    if source is None: source = {"source_id": source_id}; sources.append(source)
    required = ("title", "authors", "year", "venue", "stable_identifier"); findings = [f"identity.{field} is required" for field in required if not identity.get(field)]
    source["identity"] = identity; source["stable_identifier"] = identity.get("stable_identifier"); source["retrieval_status"] = identity.get("retrieval_status", "IDENTITY_DECLARED"); source["verification_status"] = "IDENTITY_VERIFIED" if not findings else "IDENTITY_DECLARED"; source["identity_inspection_actor"] = identity.get("inspection_actor", "host")
    _write(path, registry); return {"operation": "verify-identity", "status": "PASS" if not findings else "FAIL", "source_id": source_id, "findings": findings, "verification_status": source["verification_status"]}


def verify_claim(path: Path, source_id: str, claim_id: str, relation: str, exact_region: str, full_text_status: str = "FULL_TEXT_INSPECTED", *, retrieval_method: str = "host-open", source_uri: str = "", retrieved_utc: str | None = None, source_hash: str = "", inspection_actor: str = "host", claim_strength: str = "bounded") -> dict[str, Any]:
    registry = _read(path); source = next((item for item in registry.setdefault("sources", []) if isinstance(item, dict) and item.get("source_id") == source_id), None)
    if source is None: raise LiteratureError(f"unknown source_id: {source_id}; verify identity first")
    findings: list[str] = []; full_text_status = full_text_status.upper()
    if relation not in RELATIONSHIPS: findings.append(f"relationship must be one of {sorted(RELATIONSHIPS)}")
    if full_text_status not in FULL_TEXT: findings.append(f"full_text_status must be one of {sorted(FULL_TEXT)}")
    if relation in {"SUPPORTS", "PARTIALLY_SUPPORTS", "QUALIFIES", "CONTRADICTS", "DOES_NOT_SUPPORT"} and not exact_region.strip(): findings.append("source-region inspection is required for a claim relationship")
    if relation in {"SUPPORTS", "PARTIALLY_SUPPORTS"} and source.get("discovery_source", "").lower() in {"snippet", "google snippet", "search result snippet"}: findings.append("snippet cannot support a load-bearing claim")
    if relation == "SUPPORTS" and full_text_status in {"SNIPPET_ONLY", "ABSTRACT_ONLY", "NOT_RETRIEVED"}: findings.append("abstract-only or snippet-only support is conditional")
    if relation == "SUPPORTS" and not retrieval_method: findings.append("retrieval_method is required")
    record = {"claim_id": claim_id, "relationship": relation, "exact_region": exact_region, "full_text_status": full_text_status, "retrieval_method": retrieval_method, "source_uri": source_uri, "retrieved_utc": retrieved_utc or _now(), "source_hash": source_hash, "inspection_actor": inspection_actor, "claim_strength": claim_strength}
    key = "claims_supported" if relation == "SUPPORTS" else "claims_qualified" if relation == "QUALIFIES" else "claims_contradicted" if relation == "CONTRADICTS" else "claims_not_supported"; source.setdefault(key, []).append(record)
    if findings: source["verification_status"] = "CONDITIONAL" if any("conditional" in f for f in findings) else source.get("verification_status", "IDENTITY_VERIFIED")
    else: source["verification_status"] = "CLAIM_RELATION_VERIFIED"; source["claim_support_status"] = "REGION_INSPECTED"
    _write(path, registry)
    status = "CONDITIONAL" if any("conditional" in f for f in findings) else "FAIL" if findings else "PASS"
    return {"operation": "verify-claim", "status": status, "source_id": source_id, "claim_id": claim_id, "relationship": relation, "verification_status": source["verification_status"], "findings": findings}


def audit(path: Path) -> dict[str, Any]:
    registry = _read(path); findings: list[str] = []
    for index, source in enumerate(registry.get("sources", [])):
        if not isinstance(source, dict): findings.append(f"sources[{index}] must be an object"); continue
        if source.get("claims_supported") and source.get("discovery_source", "").lower() in {"snippet", "google snippet", "search result snippet"}: findings.append(f"sources[{index}] uses a snippet as claim support")
        for claim in source.get("claims_supported", []):
            if not isinstance(claim, dict): findings.append(f"sources[{index}] support record must be an object"); continue
            for field in ("retrieval_method", "source_uri", "retrieved_utc", "exact_region", "inspection_actor"):
                if not claim.get(field): findings.append(f"sources[{index}] support record missing {field}")
            if claim.get("full_text_status") != "FULL_TEXT_INSPECTED": findings.append(f"sources[{index}] support record is not full-text inspected")
        if source.get("verification_status") == "CLAIM_RELATION_VERIFIED" and not source.get("claims_supported"): findings.append(f"sources[{index}] has claim-verified status without a support record")
    return {"operation": "audit", "status": "PASS" if not findings else "FAIL", "source_count": len(registry.get("sources", [])), "findings": findings}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("query"); p.add_argument("path", type=Path); p.add_argument("query"); p.add_argument("--provider", required=True); p.add_argument("--filters", default=""); p.add_argument("--result-count", type=int, default=0); p.add_argument("--rationale", default=""); p.add_argument("--deduplication", default="")
    p = sub.add_parser("verify-identity"); p.add_argument("path", type=Path); p.add_argument("source_id"); p.add_argument("identity_json", type=Path)
    p = sub.add_parser("verify-claim"); p.add_argument("path", type=Path); p.add_argument("source_id"); p.add_argument("claim_id"); p.add_argument("--relationship", required=True); p.add_argument("--exact-region", required=True); p.add_argument("--full-text-status", default="FULL_TEXT_INSPECTED"); p.add_argument("--retrieval-method", default="host-open"); p.add_argument("--source-uri", default="")
    p = sub.add_parser("audit"); p.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "query": result = record_query(args.path, args.query, args.provider, args.filters, args.result_count, args.rationale, args.deduplication)
        elif args.command == "verify-identity": result = verify_identity(args.path, args.source_id, _read(args.identity_json))
        elif args.command == "verify-claim": result = verify_claim(args.path, args.source_id, args.claim_id, args.relationship, args.exact_region, args.full_text_status, retrieval_method=args.retrieval_method, source_uri=args.source_uri)
        else: result = audit(args.path)
    except LiteratureError as exc: print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False)); sys.exit(2)
    print(json.dumps(result, indent=2, ensure_ascii=False)); sys.exit(0 if result["status"] in {"PASS", "CONDITIONAL"} else 1)
