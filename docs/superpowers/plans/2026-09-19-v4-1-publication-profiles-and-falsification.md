# V4.1 Publication Profiles and Falsification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic adaptive publication profiles and profile-aware claim falsification obligations while preserving the V4 publication gate as the only authority.

**Architecture:** A pure resolver merges hash-bound profile layers in fixed specificity order and emits a derived artifact. A separate falsification module derives and checks claim obligations without mutating graph, evidence, claim, or publication state. Existing fixed publication-depth checks remain the conservative fallback.

**Tech Stack:** Python 3 standard library, JSON Schema, JSON registries/templates, `unittest`.

## Global Constraints

- Resolve layers only as `fallback -> domain -> study_type -> claim_type -> venue -> article_type -> design`.
- Fail closed on unresolved category conflicts, invalid N/A assignments, ambiguous overrides, or stale source hashes.
- Produce canonical input/output hashes and byte-stable sorted arrays.
- Falsification artifacts cannot promote claims, upgrade evidence, transition graph nodes, or authorize publication.
- Preserve all V4 fixed-field behavior when no resolved profile is supplied.

### Task 1: Deterministic Profile Resolver

**Files:**
- Create: `scripts/publication_profiles.py`
- Create: `tests/test_publication_profiles.py`
- Create: `assets/schemas/publication_profile.schema.json`
- Create: `assets/templates/publication_profile.json`
- Create: `assets/registry/publication_profiles.json`

**Interfaces:**
- `canonical_hash(value: Any) -> str`
- `resolve_profile(request: dict[str, Any], profiles: list[dict[str, Any]]) -> dict[str, Any]`

- [x] Write failing tests for layer order, repeatability, scope, conflicts, overrides, N/A justification, and stale hashes.
- [x] Run focused tests and observe the missing-module failure.
- [x] Implement the pure resolver and JSON contracts.
- [x] Run focused tests to green.

### Task 2: Profile-Aware Falsification Obligation

**Files:**
- Create: `scripts/falsification_obligation.py`
- Create: `tests/test_falsification_obligation.py`
- Create: `assets/schemas/falsification_obligation.schema.json`
- Create: `assets/templates/falsification_obligation.json`

**Interfaces:**
- `derive_obligation(claim: dict[str, Any], profile: dict[str, Any], *, producer_id: str) -> dict[str, Any]`
- `derive_project_obligation(project_dir, claim_id, *, producer_id) -> dict[str, Any]`
- `check_project_obligation(project_dir, claim_id, artifact, evidence, *, producer_id, checker_id) -> dict[str, Any]`
- `check_obligation(...)` is a fail-closed compatibility entry and never accepts caller-supplied authority.

- [x] Write and run failing tests first.
- [x] Implement domain/study-sensitive checks with conservative fallback.
- [x] Verify a distinct checker and immutable input handling.
- [x] Verify no claim, evidence, graph, or publication authority is granted.
- [x] Replay the resolved profile against the shipped registry and reject
  self-signed family, requirement, provenance, and scope substitutions.
- [x] Reject malformed public inputs before field access.
- [x] Bind the shipped profile registry to the fixed-path V4.1 release trust
  record and verifier anchor. `SHA256SUMS.txt` remains an inventory check rather
  than the trust root; formal checker replay uses V4 project control-plane
  claim/profile context.

### Task 3: Publication Gate Integration

**Files:**
- Modify: `scripts/publication_sufficiency.py`
- Modify: `tests/test_v4_publication_gates.py`

**Interfaces:**
- `research_depth_profile(profile)` consumes optional `publication_profile`.
- `assess(profile)` reports `profile_resolution` without changing its existing call signature.

- [x] Add failing tests for legal N/A and conflicted profiles.
- [x] Preserve the legacy fixed-dimension fallback.
- [x] Treat only resolved `required` dimensions as blocking and reject stale/conflicted artifacts.
- [x] Run focused tests to green.

### Task 4: Verification and Audit

**Files:**
- Modify: `docs/v4.1-final-capability-audit.md`
- Modify: `docs/superpowers/specs/2026-09-19-v4-1-specialist-integration-design.md`

- [x] Validate JSON, schemas, Python syntax, and Skill structure.
- [x] Run `git diff --check` and the complete regression suite on the final snapshot.
- [x] Record only verified implementation status; keep external behavior qualification and release fail-closed.
- [ ] Commit the isolated branch changes.
