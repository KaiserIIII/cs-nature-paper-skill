# CS Nature Paper V4 Vendored Research Team Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` or `superpowers:executing-plans` to
> implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Deliver V4.0.0 as a best-of-breed CS Research OS with audited
vendored research Skills, fourteen built-in specialists, behavior-level
multi-system benchmarks, publication sufficiency gates, autonomous research
expansion, and a real TTA field campaign.

**Architecture:** Keep the V3.2.1 control plane and add independent modules for
third-party validation, specialist contracts/runtime, and publication
assessment. Connect them through the existing router and executor without
granting providers graph authority.

**Tech stack:** Python standard library, unittest/pytest, JSON and Markdown
assets, existing provider and research-state runtimes.

## Global Constraints

- The release base is `6f13161601854763b500cdb596dbe52df3a0fd19` and the
  working branch is `feat/v4-vendored-research-team`.
- Do not merge, tag, release, or claim hosted CI before exact-SHA evidence.
- ARS is CC BY-NC 4.0 and remains benchmark-only outside `vendor/`; do not copy
  its instructions, prompts, schemas, or code into V4.
- Every external source is identified by repository, exact 40-character SHA,
  license decision, audit time, and strongest observed capability.
- Superiority cannot be inferred from agent count, code size, Skill count, or
  architecture diagrams.
- A missing comparator run, missing output hash, one-sided judge run, or
  unsupported score fails the RC gate.
- Private TTA project content is never sent to an external service.
- Formal ML runs fix seeds, record hardware/software, preserve failures,
  separate exploratory and confirmatory stages, and support checkpoint,
  resume, and bounded retry.

## Task 1: Lock V4 contracts with failing tests

**Files:** `tests/test_v4_internal_specialists.py`,
`tests/test_v4_vendor_runtime.py`, `tests/test_v4_publication_gates.py`

1. Assert the fourteen-role pack, contract completeness, internal routing,
   discovery fallback, real vendored loading, license fail-closed behavior,
   offline routes, publication gate ordering, and TTA disposition.
2. Run each V4 test file and record failures caused by missing production APIs.

## Task 2: Audit and vendor bounded third-party Skills

**Files:** `vendor/research-skills/**`,
`vendor/research-skills/THIRD_PARTY_MANIFEST.json`,
`vendor/research-skills/THIRD_PARTY_NOTICES.md`, `docs/v4-source-audit.md`

1. Resolve candidate HEADs without cloning and compare them to downloaded
   immutable archives.
2. Inspect root and subtree licenses, references, scripts, dependencies, and
   unsafe operations. Reject unclear or non-commercial sources.
3. Copy only required complete Skill directories and repository licenses.
4. Generate a file-level manifest and validate every path, SHA, license, and
   audit field.

## Task 3: Implement the internal specialist pack

**Files:** `references/internal-specialists/team.json`,
`references/internal-specialists/*.md`, `scripts/internal_specialists.py`

1. Define each role's capabilities, vendored sources, decisions, quality
   criteria, forbidden actions, output contract, and checker.
2. Implement pack loading, validation, capability mapping, local Skill loading,
   decision comparison, and serializable invocation records.
3. Run the specialist tests to green.

## Task 4: Integrate built-in-first provider routing

**Files:** `scripts/provider_runtime.py`, `scripts/skill_router.py`,
`scripts/research_executor.py`

1. Add the `INTERNAL_SPECIALIST` provider type and formal eligibility rules.
2. Resolve ordinary tasks directly to built-ins and expose a recorded
   `QUALITY_UPGRADE_DISCOVERY` decision for specialized tasks.
3. Fall back to a built-in after unsuccessful discovery; execute a loaded
   vendored Skill through a typed handoff and the existing checker boundary.
4. Run focused V4 and V3.2.1 provider tests.

## Task 5: Implement publication sufficiency

**Files:** `scripts/publication_sufficiency.py`,
`references/core/publication-sufficiency.md`,
`assets/templates/v4/publication_assessment.json`

1. Implement independent scientific-validity, evidence, publication,
   reviewer-completeness, and readiness results.
2. Implement the research-depth profile and deterministic expansion planner.
3. Add conservative artifact inspection for the TTA regression and assert its
   required findings and `EXPAND_RESEARCH` result.
4. Run publication and regression tests to green.

## Task 6: Upgrade skill documentation and metadata

**Files:** `SKILL.md`, `README.md`, `README_zh.md`, `CHANGELOG.md`, active
scripts, registries, templates, schemas, `release_manifest.json`

1. Document the V4 philosophy, team, routing, vendoring, and publication gates.
2. Set active metadata to `4.0.0` while retaining explicit legacy constants for
   compatibility.
3. Add V4 registry entries and release validation for all new invariants.

## Task 7: Verify release candidate

**Files:** `scripts/validate_release.py`, `docs/v4.0.0-rc-report.md`, generated
hash manifests

1. Run V4 unit/E2E tests, all existing tests, registry validation, vendor
   validation, offline execution, quality-upgrade discovery, license rejection,
   TTA regression, smoke checks, and release integrity.
2. Rebuild hashes only after the tree is final, rerun validation, and record
   exact pass counts and unverified hosted/model-backed checks.
3. Commit on `feat/v4-vendored-research-team`; do not merge, tag, release, or
   push unless separately requested.

## Task 8: Add the multi-system behavior benchmark

**Files:** `assets/evals/v4/research_os_benchmarks.json`,
`scripts/research_os_benchmark.py`, `tests/test_v4_benchmark_suite.py`,
`docs/v4-benchmark-audit.md`

1. Write failing tests requiring ARS, K-Dense Scientific Agent Skills,
   AI Scientist, PaperOrchestra, Sisyphus Academica, and Research Engineering
   Suite as distinct pinned benchmark systems.
2. Require each benchmark to declare its strongest capabilities, public task,
   parity dimensions, V4 superiority dimensions, source/license decision, and
   executable evidence contract.
3. Implement output-hash validation plus counterbalanced A/B and B/A blind
   judgments. Derive parity and superiority from the judgments; reject
   self-reported scores and structural proxy metrics.
4. Require ARS parity on evidence depth, citation faithfulness, closest-work
   coverage, manuscript structure, writing depth, reviewer attack quality,
   unsupported-claim detection, and revision quality.
5. Keep RC and recommended merge failed when any required task is `NOT_RUN`,
   stale, unbound, or weaker than its comparator.

## Task 9: Turn publication failure into an executable expansion campaign

**Files:** `scripts/research_expansion.py`,
`assets/templates/v4/research_expansion_campaign.json`,
`tests/test_v4_research_expansion.py`

1. Write failing tests showing the TTA thin-paper findings create named work
   packages for datasets, models, modern baselines, mechanism timing, ablations,
   statistics, figures, review, and revision.
2. Emit a dependency graph, frozen protocol inputs, commands, resource budget,
   expected artifacts, stop rules, checkpoint paths, retries, and claim impact.
3. Make `director_loop.py` return and persist this campaign when a
   submission-targeted project reaches `EXPAND_RESEARCH`.
4. Do not mark a campaign complete from a plan or process start; require result
   artifacts and independent checks.

## Task 10: Execute and register the TTA field expansion

**Files:** `<EXTERNAL_RESEARCH_PROJECT>/configs/expansion_*.json`,
`<EXTERNAL_RESEARCH_PROJECT>/run_expansion_supervisor.py`,
`<EXTERNAL_RESEARCH_PROJECT>/tests/test_expansion_campaign.py`, TTA research-state
registries and generated run artifacts

1. Reconcile the completed 960/960 Tier 1 jobs with the stale experiment
   registry while preserving the prior invalidated campaign.
2. Freeze a protocol amendment for at least a second real dataset, a CNN model,
   modern TTA baselines, prospective mechanism measurements, and decision-useful
   ablations.
3. Run smoke jobs in the current environment, capture a fresh environment
   snapshot, then launch the bounded formal campaign in the background with PID,
   heartbeat, checkpoint, resume, retry, logs, and failure registry.
4. Analyze only completed result files, produce uncertainty-aware statistics
   and figures, rerun publication/reviewer gates, and expand again if evidence
   remains thin.
5. Generate and compile the full paper only after the evidence and review gates
   pass; otherwise preserve `EXPAND_RESEARCH` and `Recommended merge: NO`.

## Task 11: Rebuild V4 RC identity and final report

**Files:** `release_manifest.json`, `scripts/validate_release.py`,
`docs/v4.0.0-rc-report.md`

1. Restore the unreleased V4 manifest with the exact base, branch, benchmark
   matrix, TTA campaign state, hosted-CI state, and honest release disposition.
2. Update release validation for V4 names, branches, tags, 6/6 CI, benchmark
   gates, vendor manifest, and non-vendored restricted benchmarks.
3. Run focused tests, full tests, all deterministic validators, fresh-venv
   minimal reproduction, benchmark behavior runs, TTA field gate, and release
   integrity in that order.
4. Record exact counts and unresolved evidence. Commit only when deterministic
   checks are green; keep merge/tag/release blocked unless every required
   external and experiment-backed gate passes.
