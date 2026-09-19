# V4 Private Ultra Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a behavior-qualified private provider overlay and expanded best-of-breed benchmark suite without weakening the V4 public core or release gates.

**Architecture:** Add a standalone runtime over two declarative registries: one for audited candidates and one for role assignments. Keep the existing provider runtime as the public fallback, and extend the existing hash-bound benchmark evaluator to the new comparator set.

**Tech Stack:** Python standard library, JSON registries, `unittest`, GitHub Actions.

## Global Constraints

- Continue from V4 commit `4a77836ac4dc4002f035717b7cce12bba25c46d8`.
- Do not merge, tag, or release.
- Do not rank quality by license, popularity, agent count, repository size, skill count, or architecture diagrams.
- Do not commit local provider contents or private filesystem paths.
- Preserve V4 evidence, protocol, publication, authorization, and release authority.
- Missing real behavior evidence fails closed.

---

### Task 1: Candidate and Role Registries

**Files:**
- Create: `assets/registry/private_ultra_candidates.json`
- Create: `references/private-ultra/team.json`
- Test: `tests/test_v4_private_ultra.py`

**Interfaces:**
- Consumes: pinned public repository metadata and V4's fourteen role IDs.
- Produces: `load_candidates()` and `load_team()` compatible JSON documents.

- [ ] Write tests requiring all requested candidates, exact commits, audit fields, fourteen roles, primary/complementary/checker mappings, and separate system benchmarks.
- [ ] Run the focused tests and confirm missing-file failures.
- [ ] Add the audit and role registries with no local paths or copied third-party content.
- [ ] Re-run focused tests.

### Task 2: Private Ultra Runtime

**Files:**
- Create: `scripts/private_ultra_runtime.py`
- Modify: `references/core/providers.md`
- Test: `tests/test_v4_private_ultra.py`

**Interfaces:**
- Consumes: `resolve(role_id, capability, mode, criticality, local_registry)`.
- Produces: a typed selection with `selection_outcome`, `primary`, `complementary`, `checker`, `fallback`, and findings.

- [ ] Write failing tests for public fallback, unqualified-candidate rejection, qualified primary selection, non-redundant ensemble selection, and checker separation.
- [ ] Confirm the tests fail because the runtime is absent.
- [ ] Implement validation and fail-closed task-specific selection.
- [ ] Run focused tests and the existing provider tests.

### Task 3: Expanded Behavior Benchmarks

**Files:**
- Modify: `assets/evals/v4/research_os_benchmarks.json`
- Modify: `scripts/research_os_benchmark.py`
- Modify: `tests/test_v4_benchmark_suite.py`
- Create: `assets/evals/v4/cases/literature_evidence_case.json`
- Create: `assets/evals/v4/cases/novelty_mechanism_case.json`
- Create: `assets/evals/v4/cases/experiment_design_case.json`
- Create: `assets/evals/v4/cases/review_integrity_case.json`
- Create: `assets/evals/v4/cases/long_horizon_orchestration_case.json`

**Interfaces:**
- Consumes: public benchmark cases and comparator outputs.
- Produces: fail-closed per-system parity/superiority results and aggregate gates.

- [ ] Update tests to require the full requested comparator set and prohibit proxy scoring.
- [ ] Confirm the old six-system suite fails the new tests.
- [ ] Add concrete cases and pinned comparator definitions.
- [ ] Make the evaluator validate the declared suite without assuming a six-system constant.
- [ ] Run benchmark tests and validate the empty-run FAIL state.

### Task 4: Audit, TTA State, and CI

**Files:**
- Create: `docs/v4-ultra-specialist-audit.md`
- Modify: `SKILL.md`
- Modify: `release_manifest.json`
- Modify: `.github/workflows/ci.yml`
- Modify: `SHA256SUMS.txt`

**Interfaces:**
- Consumes: online audit observations, local tests, TTA state, and Git state.
- Produces: a reviewer-facing audit and exact branch CI trigger.

- [ ] Record selected/rejected candidates, actual qualification state, role mapping, benchmark status, TTA state, CI state, and critical gaps.
- [ ] Document PRIVATE_ULTRA routing in the Skill entrypoint without weakening public fallback.
- [ ] Keep release and merge gates at `NO` while behavior and field regressions are incomplete.
- [ ] Add the current V4 feature branch to Hosted CI push triggers.
- [ ] Regenerate the source manifest and run the full local CI command set.
- [ ] Commit and push the feature branch; inspect the Hosted CI run without merging, tagging, or releasing.
