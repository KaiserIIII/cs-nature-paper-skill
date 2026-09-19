# V4.1 Final Security Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the V4.1 registry trust, reviewer-synthesis isolation, and provider-qualification authority gaps without weakening P0-2 through P0-5 or claiming release readiness.

**Architecture:** A fixed-path release trust record is pinned by a reviewed digest in a dedicated verifier and binds security-critical registries plus provider validation evidence. Reviewer synthesis production and verification live in separate modules, and the checker independently reconstructs the complete canonical projection from frozen reports. Formal provider routing accepts only a provider identifier and derives state from trust-bound registry metadata and source-bound validation artifacts; caller-authored state is never authoritative.

**Tech Stack:** Python 3 standard library, JSON, `unittest`, existing release validator and manifest tooling.

## Global Constraints

- Work only in the already verified `<isolated-worktree>` checkout.
- Do not commit, merge, push, deploy, or modify either main installation.
- Keep `RC_NOT_RELEASED`, `recommended_merge=NO`, and behavior qualification fail-closed.
- A trust-root rotation requires an explicit code-reviewed anchor change; no runtime or caller-supplied override is accepted.
- Preserve P0-2 malformed-input rejection, P0-3 release inventory coverage, P0-4 exact `oneOf` and JSON-type-sensitive `const`, and P0-5 control-plane-only checking.

---

### Task 1: Independent Registry and Release Trust Root

**Files:**
- Create: `scripts/release_trust.py`
- Create: `assets/trust/v41_release_trust.json`
- Create: `tests/test_v41_release_trust.py`
- Modify: `scripts/falsification_obligation.py`
- Modify: `scripts/validate_release.py`
- Modify: `tests/test_falsification_obligation.py`

**Interfaces:**
- `validate_release_trust() -> dict[str, Any]`
- `load_trusted_json(relative_path: str) -> dict[str, Any] | None`
- The trust record binds only allowlisted relative paths and conservative release-state constraints.

- [x] Add attack tests proving registry plus `SHA256SUMS.txt` and registry plus manifest plus provenance rewrites are rejected.
- [x] Run the focused attack tests and confirm the existing implementation fails with `OBLIGATION_REQUIRED`.
- [x] Implement fixed-path trust loading, reviewed anchor verification, canonical file hashing, allowlist enforcement, and fail-closed release validation.
- [x] Route falsification registry loading through the trust verifier without adding caller-supplied trust parameters.
- [x] Run focused P0-1 through P0-5 tests to green.

### Task 2: Reviewer, Synthesizer, and Checker Isolation

**Files:**
- Modify: `scripts/review_synthesis.py`
- Create: `scripts/review_synthesis_checker.py`
- Modify: `tests/test_v41_review_synthesis.py`
- Modify: `assets/schemas/review_synthesis.schema.json`

**Interfaces:**
- `review_synthesis.produce_synthesis(...) -> dict[str, Any]`
- `review_synthesis_checker.check_synthesis(...) -> dict[str, Any]`

- [x] Add a failing replay that removes a grouped finding, recomputes `synthesis_hash`, and still expects rejection.
- [x] Add failing identity-collision cases across reviewer producers, synthesis producer, and checker.
- [x] Move checking into a separate module and independently reconstruct the exact findings projection from frozen reports.
- [x] Verify the checker never mutates the candidate artifact and never emits a repaired synthesis.
- [x] Run review-focused tests to green.

### Task 3: Evidence-Derived Provider Qualification

**Files:**
- Create: `assets/registry/v41_provider_registry.json`
- Create: `assets/registry/v41_provider_qualification.json`
- Modify: `scripts/v41_provider_contracts.py`
- Modify: `tests/test_v41_provider_contracts.py`
- Modify: `assets/schemas/v41_provider_contract.schema.json`
- Modify: `assets/trust/v41_release_trust.json`

**Interfaces:**
- `derive_qualification(registry_record, validation_bundle) -> dict[str, Any]` computes non-authoritative state from source-bound artifacts.
- `resolve_provider(provider_id, public_core, *, formal, capability=None) -> dict[str, Any]` loads only sealed fixed-path authority.

- [x] Add failing tests that self-report `QUALIFIED`, `PASS`, and `EXTERNAL_BETTER` and verify formal routing rejects them.
- [x] Add failing tests for missing artifacts, source/hash rebinding, producer/checker collision, and incomplete comparison evidence.
- [x] Derive qualification, comparison, utility, security, and eligibility from independently checked validation artifacts.
- [x] Bind provider registry and qualification bundle in the release trust record; ship no behavior-qualified external provider.
- [x] Verify formal routing remains `FALLBACK_BUILT_IN` for every shipped external provider.

### Task 4: Full Verification and Honest Audit

**Files:**
- Modify: `docs/v4.1-final-capability-audit.md`
- Modify: `docs/superpowers/specs/2026-09-19-v4-1-specialist-integration-design.md`
- Modify: `SHA256SUMS.txt`

- [x] Replay every original attack fixture plus the new registry, synthesis, and provider attacks.
- [x] Run `python -m unittest discover -s tests -v`.
- [x] Run `python scripts/build_manifest.py --check`.
- [x] Run `python scripts/validate_release.py`.
- [x] Run the Codex Skill validator against this worktree.
- [x] Run `git diff --check` and inspect the final diff/status.
- [ ] Request an independent read-only security/code review and resolve all critical or important findings.
- [x] Record unprovable behavior/hosted/release claims as `BLOCKED` or `PENDING_FINAL_REVIEW`; do not commit them as verified claims.
