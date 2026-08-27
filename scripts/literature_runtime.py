#!/usr/bin/env python3
"""Record literature discovery separately from identity and claim verification."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SKILL_VERSION = "3.1.1"
RELATIONSHIPS = {"SUPPORTS", "PARTIALLY_SUPPORTS", "QUALIFIES", "CONTRADICTS", "DOES_NOT_SUPPORT", "INACCESSIBLE", "MISSING"}
FULL_TEXT = {"FULL_TEXT_INSPECTED", "ABSTRACT_ONLY", "SNIPPET_ONLY", "NOT_RETRIEVED"}
LOAD_BEARING_RELATIONSHIPS = {"SUPPORTS", "PARTIALLY_SUPPORTS", "QUALIFIES", "CONTRADICTS", "DOES_NOT_SUPPORT"}
REGION = re.compile(r"^lines?\s+(\d+)(?:\s*-\s*(\d+))?$", re.IGNORECASE)


class LiteratureError(RuntimeError):
    pass


def _now() -> str: return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
def _read(path: Path) -> dict[str, Any]:
    try: value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc: raise LiteratureError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict): raise LiteratureError("registry must be an object")
    return value
def _write(path: Path, value: dict[str, Any]) -> None: path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _source(registry: dict[str, Any], source_id: str) -> dict[str, Any] | None:
    return next((item for item in registry.setdefault("sources", []) if isinstance(item, dict) and item.get("source_id") == source_id), None)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _raw_hash(value: str) -> str:
    return value.removeprefix("sha256:").lower()


def _region_content(path: Path, exact_region: str) -> tuple[str | None, str | None]:
    match = REGION.fullmatch(exact_region.strip())
    if not match:
        return None, "exact_region must use line N or lines N-M"
    start = int(match.group(1)); end = int(match.group(2) or start)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    if start < 1 or end < start or end > len(lines):
        return None, "exact_region is outside the retrieved artifact"
    return "".join(lines[start - 1:end]), None


def record_query(path: Path, query: str, provider: str, filters: str, result_count: int, rationale: str, deduplication: str) -> dict[str, Any]:
    value = _read(path) if path.exists() else {"schema_version": 3, "skill_version": SKILL_VERSION, "queries": [], "sources": []}
    value.setdefault("queries", []).append({"query": query, "database_provider": provider, "date_utc": _now(), "filters": filters, "result_count": result_count, "selection_rationale": rationale, "deduplication": deduplication, "verification_status": "DISCOVERED"})
    _write(path, value); return {"operation": "query", "status": "PASS", "query": value["queries"][-1], "path": str(path)}


def verify_identity(path: Path, source_id: str, identity: dict[str, Any]) -> dict[str, Any]:
    registry = _read(path); sources = registry.setdefault("sources", []); source = _source(registry, source_id)
    if source is None: source = {"source_id": source_id}; sources.append(source)
    required = ("title", "authors", "year", "venue", "stable_identifier"); findings = [f"identity.{field} is required" for field in required if not identity.get(field)]
    source["identity"] = identity; source["stable_identifier"] = identity.get("stable_identifier"); source.setdefault("retrieval_status", "NOT_RETRIEVED"); source["verification_status"] = "IDENTITY_VERIFIED" if not findings else "IDENTITY_DECLARED"; source["identity_inspection_actor"] = identity.get("inspection_actor", "host")
    if identity.get("retrieval_status"): source["declared_retrieval_status"] = identity["retrieval_status"]
    _write(path, registry); return {"operation": "verify-identity", "status": "PASS" if not findings else "FAIL", "source_id": source_id, "findings": findings, "verification_status": source["verification_status"]}


def record_retrieval(path: Path, source_id: str, local_artifact: Path, *, retrieval_method: str, source_uri: str, inspection_actor: str, retrieved_utc: str | None = None, expected_source_hash: str = "") -> dict[str, Any]:
    registry = _read(path); source = _source(registry, source_id)
    if source is None: raise LiteratureError(f"unknown source_id: {source_id}; verify identity first")
    local_artifact = local_artifact.resolve(); findings: list[str] = []
    if not retrieval_method: findings.append("retrieval_method is required")
    if not source_uri: findings.append("source_uri is required")
    if not inspection_actor: findings.append("inspection_actor is required")
    if not local_artifact.exists() or not local_artifact.is_file():
        findings.append("retrieved artifact does not exist")
        digest = ""
    else:
        digest = _sha256(local_artifact)
        if expected_source_hash and digest != _raw_hash(expected_source_hash):
            findings.append("source hash mismatch")
    records = registry.setdefault("retrieval_records", [])
    retrieval_id = f"LR-{source_id}-{len(records) + 1:04d}"
    record = {
        "retrieval_id": retrieval_id,
        "source_id": source_id,
        "stable_identifier": source.get("stable_identifier", ""),
        "retrieval_method": retrieval_method,
        "source_uri": source_uri,
        "retrieved_utc": retrieved_utc or _now(),
        "local_artifact": str(local_artifact),
        "source_sha256": digest,
        "retrieval_status": "FULL_TEXT_RETRIEVED" if not findings else "FAILED",
        "inspection_actor": inspection_actor,
    }
    if expected_source_hash: record["expected_source_sha256"] = _raw_hash(expected_source_hash)
    if findings: record["findings"] = findings
    records.append(record); source.setdefault("retrieval_record_ids", []).append(retrieval_id)
    if not findings: source["retrieval_status"] = "FULL_TEXT_RETRIEVED"
    _write(path, registry)
    return {"operation": "retrieve", "status": "PASS" if not findings else "FAIL", "source_id": source_id, "retrieval_id": retrieval_id, "record": record, "findings": findings}


def verify_claim(path: Path, source_id: str, claim_id: str, relation: str, exact_region: str, full_text_status: str = "FULL_TEXT_INSPECTED", *, retrieval_record_id: str = "", retrieval_method: str = "host-open", source_uri: str = "", retrieved_utc: str | None = None, source_hash: str = "", inspection_actor: str = "host", checker: str = "", claim_strength: str = "bounded") -> dict[str, Any]:
    registry = _read(path); source = _source(registry, source_id)
    if source is None: raise LiteratureError(f"unknown source_id: {source_id}; verify identity first")
    errors: list[str] = []; conditional: list[str] = []; full_text_status = full_text_status.upper()
    if relation not in RELATIONSHIPS: errors.append(f"relationship must be one of {sorted(RELATIONSHIPS)}")
    if full_text_status not in FULL_TEXT: errors.append(f"full_text_status must be one of {sorted(FULL_TEXT)}")
    load_bearing = relation in LOAD_BEARING_RELATIONSHIPS
    if load_bearing and not exact_region.strip(): errors.append("source-region inspection is required for a claim relationship")
    if load_bearing and full_text_status != "FULL_TEXT_INSPECTED": conditional.append("abstract-only, snippet-only, or unretrieved content cannot verify claim support")
    if relation in {"SUPPORTS", "PARTIALLY_SUPPORTS"} and source.get("discovery_source", "").lower() in {"snippet", "google snippet", "search result snippet"}: conditional.append("snippet cannot support a load-bearing claim")

    # A local materialized artifact may be acquired inline, but external or
    # host-owned content must arrive with a prior retrieval record.
    if not retrieval_record_id and source_uri and source_hash:
        candidate = Path(source_uri)
        if candidate.exists() and candidate.is_file():
            acquired = record_retrieval(path, source_id, candidate, retrieval_method=retrieval_method, source_uri=source_uri, inspection_actor=inspection_actor, retrieved_utc=retrieved_utc, expected_source_hash=source_hash)
            retrieval_record_id = str(acquired["retrieval_id"])
            registry = _read(path); source = _source(registry, source_id)
            if acquired["status"] == "FAIL": errors.extend(acquired["findings"])

    retrieval = next((item for item in registry.get("retrieval_records", []) if isinstance(item, dict) and item.get("retrieval_id") == retrieval_record_id), None)
    region_sha256 = ""; materialized = ""
    if load_bearing and retrieval is None:
        conditional.append("a verified retrieval record is required")
    elif retrieval is not None:
        if retrieval.get("source_id") != source_id: errors.append("retrieval record source_id mismatch")
        if retrieval.get("retrieval_status") != "FULL_TEXT_RETRIEVED": errors.append("retrieval record did not complete successfully")
        if source_uri and retrieval.get("source_uri") != source_uri: errors.append("source_uri differs from retrieval record")
        if source_hash and _raw_hash(source_hash) != retrieval.get("source_sha256"): errors.append("source hash mismatch")
        artifact = Path(str(retrieval.get("local_artifact", "")))
        materialized = str(artifact)
        if not artifact.exists() or not artifact.is_file():
            errors.append("retrieved artifact is unavailable for verification")
        else:
            current_hash = _sha256(artifact)
            if current_hash != retrieval.get("source_sha256"): errors.append("source hash mismatch")
            if load_bearing:
                region_text, region_error = _region_content(artifact, exact_region)
                if region_error: errors.append(region_error)
                elif region_text is not None: region_sha256 = hashlib.sha256(region_text.encode("utf-8")).hexdigest()
    if load_bearing and not checker:
        conditional.append("an independent checker is required")
    elif load_bearing and checker == inspection_actor:
        conditional.append("checker must be independent from inspection_actor")

    verified = load_bearing and retrieval is not None and not errors and not conditional
    verification_status = "CLAIM_RELATION_VERIFIED" if verified else "CLAIM_RELATION_RECORDED"
    record = {
        "claim_id": claim_id,
        "relationship": relation,
        "exact_region": exact_region,
        "full_text_status": full_text_status,
        "retrieval_record_id": retrieval_record_id,
        "retrieval_method": retrieval.get("retrieval_method") if retrieval else retrieval_method,
        "source_uri": retrieval.get("source_uri") if retrieval else source_uri,
        "retrieved_utc": retrieval.get("retrieved_utc") if retrieval else retrieved_utc,
        "local_artifact": materialized,
        "source_sha256": retrieval.get("source_sha256") if retrieval else _raw_hash(source_hash),
        "region_sha256": region_sha256,
        "inspection_actor": inspection_actor,
        "checker": checker,
        "claim_strength": claim_strength,
        "verification_status": verification_status,
    }
    key = "claims_supported" if relation in {"SUPPORTS", "PARTIALLY_SUPPORTS"} else "claims_qualified" if relation == "QUALIFIES" else "claims_contradicted" if relation == "CONTRADICTS" else "claims_not_supported"
    source.setdefault(key, []).append(record)
    source["verification_status"] = verification_status
    source["claim_support_status"] = "REGION_INSPECTED" if verified else "CLAIM_RELATION_RECORDED"
    findings = errors + conditional
    if findings: record["findings"] = findings
    _write(path, registry)
    status = "FAIL" if errors else "CONDITIONAL" if conditional else "PASS"
    return {"operation": "verify-claim", "status": status, "source_id": source_id, "claim_id": claim_id, "relationship": relation, "verification_status": verification_status, "retrieval_record_id": retrieval_record_id, "region_sha256": region_sha256, "findings": findings}


def audit(path: Path) -> dict[str, Any]:
    registry = _read(path); findings: list[str] = []; retrievals = {item.get("retrieval_id"): item for item in registry.get("retrieval_records", []) if isinstance(item, dict)}
    for retrieval_id, retrieval in retrievals.items():
        if retrieval.get("retrieval_status") != "FULL_TEXT_RETRIEVED":
            continue
        artifact = Path(str(retrieval.get("local_artifact", "")))
        if not artifact.exists() or not artifact.is_file():
            findings.append(f"retrieval_records[{retrieval_id}] artifact is unavailable")
        elif _sha256(artifact) != retrieval.get("source_sha256"):
            findings.append(f"retrieval_records[{retrieval_id}] source hash mismatch")
    for index, source in enumerate(registry.get("sources", [])):
        if not isinstance(source, dict): findings.append(f"sources[{index}] must be an object"); continue
        if source.get("claims_supported") and source.get("discovery_source", "").lower() in {"snippet", "google snippet", "search result snippet"}: findings.append(f"sources[{index}] uses a snippet as claim support")
        claims: list[dict[str, Any]] = []
        for key in ("claims_supported", "claims_qualified", "claims_contradicted", "claims_not_supported"):
            if isinstance(source.get(key), list): claims.extend(item for item in source[key] if isinstance(item, dict))
        for claim in claims:
            if claim.get("verification_status") != "CLAIM_RELATION_VERIFIED": continue
            for field in ("retrieval_record_id", "source_uri", "retrieved_utc", "exact_region", "source_sha256", "region_sha256", "inspection_actor", "checker"):
                if not claim.get(field): findings.append(f"sources[{index}] verified relation missing {field}")
            retrieval = retrievals.get(claim.get("retrieval_record_id"))
            if not retrieval or retrieval.get("source_id") != source.get("source_id"): findings.append(f"sources[{index}] verified relation has no matching retrieval record")
            elif retrieval.get("stable_identifier") != source.get("stable_identifier"): findings.append(f"sources[{index}] verified relation stable identifier mismatch")
            if claim.get("full_text_status") != "FULL_TEXT_INSPECTED": findings.append(f"sources[{index}] verified relation is not full-text inspected")
            elif retrieval:
                artifact = Path(str(retrieval.get("local_artifact", "")))
                if artifact.exists() and artifact.is_file():
                    region_text, region_error = _region_content(artifact, str(claim.get("exact_region", "")))
                    if region_error or hashlib.sha256((region_text or "").encode("utf-8")).hexdigest() != claim.get("region_sha256"):
                        findings.append(f"sources[{index}] verified relation region mismatch")
        if source.get("verification_status") == "CLAIM_RELATION_VERIFIED" and not any(isinstance(item, dict) and item.get("verification_status") == "CLAIM_RELATION_VERIFIED" for item in claims): findings.append(f"sources[{index}] has claim-verified status without a verified relation")
    return {"operation": "audit", "status": "PASS" if not findings else "FAIL", "source_count": len(registry.get("sources", [])), "findings": findings}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("query"); p.add_argument("path", type=Path); p.add_argument("query"); p.add_argument("--provider", required=True); p.add_argument("--filters", default=""); p.add_argument("--result-count", type=int, default=0); p.add_argument("--rationale", default=""); p.add_argument("--deduplication", default="")
    p = sub.add_parser("verify-identity"); p.add_argument("path", type=Path); p.add_argument("source_id"); p.add_argument("identity_json", type=Path)
    p = sub.add_parser("retrieve"); p.add_argument("path", type=Path); p.add_argument("source_id"); p.add_argument("local_artifact", type=Path); p.add_argument("--retrieval-method", required=True); p.add_argument("--source-uri", required=True); p.add_argument("--inspection-actor", required=True); p.add_argument("--expected-source-hash", default="")
    p = sub.add_parser("verify-claim"); p.add_argument("path", type=Path); p.add_argument("source_id"); p.add_argument("claim_id"); p.add_argument("--relationship", required=True); p.add_argument("--exact-region", required=True); p.add_argument("--full-text-status", default="FULL_TEXT_INSPECTED"); p.add_argument("--retrieval-record-id", default=""); p.add_argument("--retrieval-method", default="host-open"); p.add_argument("--source-uri", default=""); p.add_argument("--inspection-actor", default="host"); p.add_argument("--checker", default="")
    p = sub.add_parser("audit"); p.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "query": result = record_query(args.path, args.query, args.provider, args.filters, args.result_count, args.rationale, args.deduplication)
        elif args.command == "verify-identity": result = verify_identity(args.path, args.source_id, _read(args.identity_json))
        elif args.command == "retrieve": result = record_retrieval(args.path, args.source_id, args.local_artifact, retrieval_method=args.retrieval_method, source_uri=args.source_uri, inspection_actor=args.inspection_actor, expected_source_hash=args.expected_source_hash)
        elif args.command == "verify-claim": result = verify_claim(args.path, args.source_id, args.claim_id, args.relationship, args.exact_region, args.full_text_status, retrieval_record_id=args.retrieval_record_id, retrieval_method=args.retrieval_method, source_uri=args.source_uri, inspection_actor=args.inspection_actor, checker=args.checker)
        else: result = audit(args.path)
    except LiteratureError as exc: print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False)); sys.exit(2)
    print(json.dumps(result, indent=2, ensure_ascii=False)); sys.exit(0 if result["status"] in {"PASS", "CONDITIONAL"} else 1)
