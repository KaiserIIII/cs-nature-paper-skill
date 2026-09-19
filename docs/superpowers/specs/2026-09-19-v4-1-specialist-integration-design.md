# V4.1 Specialist Integration Design

**Date:** 2026-09-19  
**Status:** Final expansion audit complete; Phase-1 and profile/falsification contracts implemented; adapters pending
**Baseline:** V4.0.0 at `b71b892b5277c0d2cd7dbdf7cd7c4da732c03796`  
**Branch:** `feat/v4.1-specialist-integration`

## Goal

Make CS Nature Paper stronger in contribution-to-evidence traceability,
publication-shape adaptation, scientific-figure QA, and independent manuscript
review while preserving the V4 Research Control Plane as the only authority.

V4.1 is an integration layer, not a replacement orchestrator. The public core
must remain fully usable offline, and no imported provider may promote evidence,
mark a research node `PASS`, alter a frozen protocol, or authorize release.

## Current context and protected invariants

- V4 has 14 internal roles, 29 audited vendored Skills, 17 routed capabilities,
  and a passing deterministic baseline of `275 passed, 24 subtests passed`.
- The current release remains `RC_NOT_RELEASED`; behavior benchmarks and hosted
  CI are fail-closed and must not be fabricated or silently upgraded.
- The V4 control plane remains authoritative for research questions, claims,
  protocol, amendments, evidence/provenance status, graph transitions,
  publication gates, permissions, and external execution authorization.
- Providers only produce typed artifacts. A provider result is never itself a
  scientific claim or graph transition.
- Producer/checker separation remains mandatory for formal and load-bearing work.
- Existing V4 `PASS` semantics may only be preserved or strengthened.

## Upstream audit snapshot

The audit resolves floating default branches to immutable commits before any
materialization. The complete upstream repositories are not vendored.

| Candidate | Exact commit | Repository license | Selected scope | Initial decision |
|---|---|---|---|---|
| PaperSpine5 | `99a84fe452ab7681e30cd81387fcb6263a676125` | MIT | Contribution-First, Results-as-Validation, exemplar-learning dossier, target-venue research, figure-story/reference QA, publication metadata/delivery concepts | bounded adapter/provider; no installer, runtime, UI, or whole application |
| Nature Skills | `9cecfef6ac683fa59d7d15d2e22f98fa71dacaf5` | Apache-2.0 | `nature-figure`, `nature-reviewer` first; Tier B skills remain audit/benchmark candidates | bounded adapter/provider; preserve Apache attribution and any subtree notices |

The final expansion-round audit adds the following bounded candidates. Their
repositories, exact commits, license decisions, security observations, and
classification are recorded in `assets/registry/v41_upstream_audits.json`.

| Candidate | Exact commit | Classification | V4.1 scope decision |
|---|---|---|---|
| AREX-Skill | `ac3fe1afa80fb9a09775ecfb2b6cc3ba850a2db6` | `ADAPTER_CANDIDATE` | discovery-only `AREX_DISCOVERY_PROVIDER`; never auto-download, install, execute, or qualify a discovered Skill |
| Systematic Literature Review | `955fcc435e651834b03768c136dca6b16ccbae08` | `METHODOLOGY_ONLY` | native `literature_recall_assurance` challenger; no repository code vendored because no repository license was detected |
| SkillLens | `ce8fcb89b00164569ed792d8737ee1315b070556` | `METHODOLOGY_ONLY` | strengthen utility/security behavior qualification; do not vendor its runtime or datasets |
| Curie | `db1b1f56159b591515f77e03c55bf473d5c1c201` | `ADAPTER_CANDIDATE` | subordinate `curie:experiment-backend`; accepts only a frozen V4 experiment contract |
| CORAL | `0123dfb939b35228cf2c1fde224cd0561e727408` | `ADAPTER_CANDIDATE` | subordinate `coral:parallel-search-backend`; cannot become Research Director or evidence authority |
| POPPER | `59611864e09dd15d7528e240ad87c7ddbb4a701c` | `REFERENCE_ONLY` | extract only high-level falsification principles; no code vendored because no repository license was detected |
| Autoresearch Paper | `ad40dcc605a834b879d2dc43b0d04de5cb4e0346` | `REFERENCE_ONLY` | architecture adversary for runtime invariants; no second control plane |

The audit records repository metadata, exact commit, source paths, license and
notice findings, dependencies, network/subprocess/write behavior, credentials,
host assumptions, and required resources in
`assets/registry/v41_upstream_audits.json`. An audit entry is not a qualification
entry: a candidate remains `qualification_status=PROVISIONAL` (or
`REJECTED`) until the comparable behavior trial, typed output contract, and
independent checker pass.

## Scope decisions

### Tier A: implement now as subordinate providers

1. `paperspine:contribution`
   - Require an evidence-bounded contribution record before substantive
     manuscript optimization in submission-targeted/full-paper workflows.
   - Reuse the Contribution-First distinction between motivation and the
     contribution that a reviewer can accept or reject.
2. `paperspine:results-validation`
   - Require each major Results unit to map to a contribution/claim, evidence
     anchor, result artifact, figure/table, allowed interpretation, and
     forbidden overclaim.
3. `paperspine:target-exemplar`
   - Store a target-venue dossier that separates official requirements from
     observed exemplar style; never copy data, claims, or copyrighted prose.
4. `paperspine:publication-production`
   - Add bounded metadata, render, and delivery consistency checks; these are
     packaging checks only and cannot imply scientific validity.
5. `nature:figure`
   - Add source-data mapping, panel-role declarations, uncertainty/missingness
     checks, final-size inspection metadata, PDF collision/geometry checks, and
     journal-rule metadata.
6. `nature:reviewer`
   - Add immutable review-packet identity, reviewer-isolation metadata, and
     claim/evidence/figure/section anchors for findings.

These providers are initially `PROVISIONAL` or `SPECIALIST` and are only
formal-eligible after the behavior trial and checker gates pass. PUBLIC_CORE
remains the default selection until comparison returns `EXTERNAL_BETTER` or
verified `COMPLEMENTARY` value.

### Tier B: audit and benchmark only in V4.1

`nature-writing`, `nature-statistics`, `nature-academic-search`,
`nature-data`, and optionally `nature-citation` receive source audits and
behavior fixtures. They remain `qualification_status=PROVISIONAL` and are not
formal-eligible in this release unless a real, comparable behavior result demonstrates a non-redundant
capability that the existing core lacks.

### Discovery / Evaluation Tier

The final expansion round adds three non-authoritative capabilities to the
design, without making them formal providers:

1. `AREX_DISCOVERY_PROVIDER` can enumerate a missing specialized capability
   through the area -> family -> repository -> workflow hierarchy. Discovery
   returns provenance and a candidate reference only. Each discovered Skill
   separately requires an immutable pin, per-Skill license decision, static
   security audit, behavior trial, typed output contract, and independent
   checker. A repository-level license never clears an individual Skill.
2. `literature_recall_assurance` is a routed challenger for novelty-critical,
   first-of-kind, systematic-review, expensive-commitment, or final related-
   work claims. It may use seed/citation expansion, venue and author census,
   benchmark tracing, adversarial repair, corpus freeze, amendments, PRISMA
   accounting, and confidence grading. It does not replace ordinary evidence
   retrieval and cannot certify completeness by itself.
3. SkillLens-derived evaluation methodology requires utility and security to
   be measured separately with repeated executor rollouts, fixed provider and
   judge configuration, exact artifact hashes, and run-level metadata. SkillLens
   is not a scientific provider and its runtime/datasets are not vendored.

### System Adapter Tier

`curie:experiment-backend` and `coral:parallel-search-backend` remain
benchmark/adapter candidates. They receive only a frozen V4 objective or
experiment contract and return candidate artifacts. V4 checkers decide whether
those artifacts enter the evidence ledger. Neither adapter can redefine an RQ,
change a protocol, or promote evidence.

### Reference / Methodology Tier

POPPER contributes the reference concept of a claim-level falsification
obligation. Autoresearch Paper is an architecture adversary for evaluator
freeze, artifact-only acceptance, watchdogs, durable resume, resource
ownership, and evaluator identity drift. Neither source receives default
routing or control-plane authority.

### Tier C: explicitly deferred

No public-core integration of daily-push infrastructure, Feishu/Obsidian
logging, paper-to-slide/patent utilities, promotional/product UI, bundled
runtimes, installers, update systems, or unrelated desktop/web applications.

## Architecture

### 1. Publication Argument Graph

Add a derived, machine-readable `publication_argument_graph.json` with stable
IDs and explicit edges:

```text
RQ -> Contribution -> Claim -> EvidenceRequirement -> EvidenceAnchor
   -> Result -> Figure/Table -> ManuscriptSection
   -> AllowedInterpretation -> ForbiddenOverclaim
```

The graph complements, and never replaces, `claims.json`,
`evidence_ledger.json`, `experiment_registry.json`, and `research_graph.json`.
It is derived from those authoritative records plus explicit manuscript/figure
links. It must support:

- stable node IDs and typed node kinds;
- edge IDs and relation types;
- provenance for every derived link;
- claim strength and evidence boundary;
- validation of missing contribution support;
- orphan major Results-section detection;
- fail-closed detection when manuscript language exceeds mapped evidence;
- deterministic rebuild without overwriting source-of-truth files.

Planned files:

- `assets/schemas/publication_argument_graph.schema.json`
- `assets/templates/publication_argument_graph.json`
- `scripts/publication_argument_graph.py`
- `tests/test_publication_argument_graph.py`

### 2. Adaptive publication profiles

Replace universal depth assumptions with a profile resolver that starts from
conservative fallback defaults and resolves requirements by:

- domain;
- study type;
- claim type;
- venue;
- article type;
- available research design.

Each profile declares `required`, `recommended`, and `not_applicable`
dimensions, an explicit justification for every N/A dimension, venue evidence,
and domain-specific external-validity concepts. Examples include repositories,
projects, developers, and commits for software engineering; workloads,
hardware, scale, and competing systems for systems; and participant design and
triangulation for HCI. Theory can mark dataset and experimental-baseline
dimensions N/A only with a written design justification.

The resolver must reject checklist gaming: an N/A dimension without a valid
profile rule and justification remains a failure. Existing publication gates
become fallback defaults rather than disappearing.

#### Deterministic profile merge and conflict semantics

Profile resolution is a pure, reproducible operation. The resolver applies
layers in this exact order:

```text
fallback -> domain -> study_type -> claim_type -> venue -> article_type -> design
```

Each layer is identified by a stable profile ID and source hash. Ordinary
`required`, `recommended`, and `not_applicable` entries are additive. A
dimension appearing in more than one category is a `PROFILE_CONFLICT`; the
resolver never silently chooses the later layer. A profile may resolve such a
conflict only with an explicit override record containing the dimension, prior
category, target category, non-empty scientific justification, applicable
scope, source identity, and profile version.

Overrides are applied from least-specific to most-specific scope and are
accepted only when the scope matches the request. An override cannot remove a
dimension without assigning it to `not_applicable`; an N/A assignment must
also carry a design-specific justification. Conflicting overrides at the same
specificity, missing scope, stale source hash, or a required dimension moved to
N/A without valid justification produce `PROFILE_CONFLICT` and fail closed.

The merged artifact records sorted dimension IDs, ordered applied profile IDs,
every conflict and resolution event, all N/A justifications, the canonical
input hash, and the canonical output hash. JSON serialization uses sorted keys
and stable arrays, so repeated resolution of identical inputs produces
byte-identical output. A profile merge never changes claims, evidence,
protocol, or graph state; publication sufficiency consumes the merged artifact
and remains the gate authority.

Planned files:

- `assets/schemas/publication_profile.schema.json`
- `assets/templates/publication_profile.json`
- `assets/registry/publication_profiles.json`
- `scripts/publication_profiles.py`
- `scripts/publication_sufficiency.py` (route profile-resolved dimensions,
  preserve conservative fallback behavior)
- `tests/test_publication_profiles.py`

### 3. Capability-level provider integration

Extend the existing provider registry/runtime rather than adding a second
router. Every candidate provider record contains:

- provider identity and capability;
- exact upstream commit and selected source path;
- local file hashes and license/notice decision;
- permissions, network, credentials, subprocess, and write scope;
- output contract and required checker;
- a validation-bundle identity, fallback provider, and discovery-only policy;
- behavior-trial and checker references;
- rollback/fallback provider.

The trusted registry contains immutable provider metadata only. It does not
accept authored `qualification_status`, `comparison_decision`, utility/security
status, or `eligibility`. Those values are derived from source-bound validation
artifacts and a distinct checker artifact; only the fixed-path, trust-root-loaded
result can influence formal routing. Calling the pure derivation function does
not grant routing authority.

The three states are intentionally independent:

| State | Meaning | Examples |
|---|---|---|
| `qualification_status` | Whether the candidate passed immutable source, license, security, semantic, behavior, and output-contract checks | `UNAUDITED`, `AUDITED`, `PROVISIONAL`, `QUALIFIED`, `REJECTED` |
| `comparison_decision` | What the counterbalanced comparison with PUBLIC_CORE established; this does not qualify a candidate | `NOT_RUN`, `INTERNAL_BETTER`, `EXTERNAL_BETTER`, `COMPLEMENTARY`, `EQUIVALENT`, `INCONCLUSIVE` |
| `eligibility` | Deterministically derived permission to use the provider for a specific task | `DISCOVERY_ONLY`, `ADVISORY_ONLY`, `NON_LOAD_BEARING`, `FORMAL_ELIGIBLE`, `DISABLED` |

`eligibility` is never author-entered and never inferred from a README or
comparison result alone. It is recomputed from exact commit/hash, license
decision, qualification status, comparison decision, task capability, permissions,
network/credential policy, formal flag, checker requirement, and fallback
availability. The legacy `qualification`, `status`, and `formal_eligible`
fields remain readable for V4 compatibility, but V4.1 treats them as derived
compatibility projections; contradictory hand-edited values fail validation.

Resolution rules remain:

1. compute the candidate's three states independently;
2. qualified internal specialist first;
3. qualified external provider only after exact pin, static audit, behavior
   trial, typed output, checker, and a comparison state of `EXTERNAL_BETTER` or
   `COMPLEMENTARY`;
4. complementary providers may be selected only for declared non-overlapping
   capabilities;
5. otherwise use PUBLIC_CORE and record `FALLBACK_BUILT_IN` as the routing
   decision, without changing the candidate's qualification state;
6. no provider can directly alter graph or evidence status.

Planned files:

- `assets/registry/v41_provider_registry.json`
- `scripts/provider_runtime.py`
- `scripts/v41_provider_adapters.py`
- `scripts/vendor_skill_runtime.py` (selected-resource integrity loading only)
- `tests/test_v41_provider_integration.py`

### Utility and security qualification

Every candidate carries separate `UTILITY_STATUS` and `SECURITY_STATUS`.
Security review covers arbitrary shell execution, package installation,
runtime clone/download, secret access, credential leakage, uncontrolled
network, data egress, file-write/destructive behavior, hidden telemetry, and
subprocesses. Formal eligibility requires an acceptable security status and a
behavior-qualified utility result; scientific usefulness cannot waive a
security failure.

### 4. Nature Reviewer workflow

For formal high-stakes review, create one immutable review packet containing
the manuscript, claims, evidence ledger, figures, protocol identity, and source
hashes. When the host supports isolation, launch three independent reviewer
contexts without shared reports; each producer receives only the packet hash and
its assigned threat contract. Each report is frozen as an immutable artifact
before any synthesis input is made available. If isolation is unavailable,
record `isolation_status=UNAVAILABLE` and downgrade reviewer completeness
instead of manufacturing independence.

Each finding maps to claim IDs, evidence anchors, figure IDs, manuscript
locations, and graph nodes where applicable. The review workflow has two
distinct checker operations:

1. `review-packet-checker` verifies that every report is schema-valid, frozen,
   hash-bound to the same packet, produced by a distinct context, and does not
   contain another report as an input. It emits a verification record; it does
   not synthesize concerns or mark reviewer completeness.
2. A dedicated `review-synthesis-provider` (or equivalent deterministic
   synthesis process), distinct from every reviewer producer and from both
   checkers, consumes only frozen reports plus the packet-check records. It
   produces the synthesis artifact by grouping overlapping findings, preserving
   disagreements, and mapping findings to authoritative IDs. The independent
   `review-synthesis-checker` then validates that artifact against the frozen
   reports, packet checks, schema, hashes, and preservation rules. The checker
   must not generate, repair, or rewrite the synthesis artifact it later
   validates.

The synthesis artifact has `SYNTHESIS_ACCEPTED` or `SYNTHESIS_CONDITIONAL`
status, never a graph `PASS` or publication `PASS`. Only the V4 control plane
may interpret the synthesis against reviewer-completeness requirements,
reopen graph nodes, or record a gate transition. No majority vote, concern
count, fabricated disagreement, or acceptance prediction is allowed. If
isolation is unavailable, synthesis may still be generated for advisory use,
but it is explicitly `SYNTHESIS_CONDITIONAL` and cannot satisfy the formal
independence requirement.
The producer and checker are implemented in separate modules. The checker
independently reconstructs the complete canonical grouping from frozen reports,
including source finding payloads, so deleting findings and recomputing the
candidate's self-hash is rejected. Reviewer producer IDs, the synthesis producer,
and the synthesis checker must be mutually disjoint.

### 5. Nature Figure workflow

The figure adapter accepts an explicit scientific question, panel roles,
source-data map, uncertainty/missingness declarations, target dimensions, and
output paths. It can produce a visual QA artifact with geometry, collision,
legend, axis, accessibility, and final-size observations. The artifact is
typed and hash-bound, but visual QA never upgrades scientific evidence or
claim status.

## Data flow and failure handling

```text
authoritative V4 state
        |
        v
derived argument/profile/review packet
        |
        v
provider resolution -> provider execution -> typed artifact
        |                                      |
        +-------------------------------> independent checker
                                               |
                              ACCEPTED / CONDITIONAL / REJECTED
```

- Missing or stale hashes: `REJECTED` and preserve the prior artifact.
- Candidate without exact commit, license decision, or behavior evidence:
  `qualification_status=PROVISIONAL` or `REJECTED`; route to PUBLIC_CORE.
- Provider output without required anchors: `CONDITIONAL` for advisory use,
  never formal evidence.
- Review isolation unavailable: record limitation and fail the relevant
  completeness dimension; do not synthesize independence.
- Review synthesis without frozen, same-packet, independently checked reports:
  `SYNTHESIS_REJECTED`; individual reports remain preserved for diagnosis.
- A synthesis checker that is also the synthesis producer:
  `SYNTHESIS_REJECTED` for formal use; preserve the provider artifact for
  advisory diagnosis only.
- Argument graph orphan or claim-strength violation: fail the graph validation
  and reopen the smallest owning node.
- Profile N/A without domain/study/venue justification: fail closed.
- Network/download/install attempt by a vendored provider: reject the
  invocation and retain offline PUBLIC_CORE operation.

## Behavior qualification

Add a V4.1 benchmark manifest and deterministic fixtures for identical
PUBLIC_CORE/candidate inputs covering:

1. scientific figure construction;
2. figure audit;
3. manuscript argument reconstruction;
4. contribution-to-results traceability;
5. statistical reporting audit;
6. literature evidence retrieval;
7. adversarial peer review;
8. full publication-package construction.

Every result records `run_id`, timestamp, provider ID, exact provider commit and
source hash, V4 commit, host model identity/version, system and provider
prompt/config hashes, toolset snapshot, network policy, token/compute/resource
budgets, temperature and sampling configuration, seed or
`seed_control=UNAVAILABLE`, retry count, input/output hashes, checker and judge
IDs/config hashes, artifact manifest, failures, and measurable wall-clock
duration. Use multiple rollouts where practical and require counterbalanced
order. Structural tests may pass without behavior qualification; the release
manifest must keep `BEHAVIOR_BENCHMARK=NOT_RUN` or `FAIL` until real behavior
evidence exists. Architecture alone cannot produce `EXTERNAL_BETTER`.

Planned files:

- `assets/evals/v41/specialist_integration_cases.json`
- `scripts/v41_behavior_benchmark.py`
- `tests/test_v41_behavior_benchmark.py`
- `docs/v4.1-specialist-integration-audit.md`

The final expansion round is frozen in
`assets/registry/v41_candidate_pool_freeze.json`; no additional provider search
is part of V4.1.

### Native falsification obligation

For load-bearing or high-strength claims, the graph may require a
profile-aware `falsification_obligation` containing a confirmation test,
falsification attempt, boundary-condition test, strongest surviving
alternative explanation, and residual confidence. The profile selects the
appropriate form: alternative baselines and leakage checks for ML; project,
operationalization, confounder, and temporal sensitivity for software
engineering; workload/hardware/scale/adversarial variation for systems;
counterexample and proof-dependency audits for theory; and measurement,
alternative-explanation, subgroup, or sensitivity analysis for human studies.
The obligation is a V4-native graph/evidence requirement, not a POPPER runtime
or a universal demand for experimental falsification.
The formal project checker loads claim/profile inputs inside the V4 project
control-plane boundary, binds the selected state files to an authority snapshot,
and re-derives the expected obligation. The public low-level checker never
accepts caller-named trusted dictionaries or caller-constructed context.
Missing control-plane context, stale state, a registry digest mismatch against
`SHA256SUMS.txt`, a release-trust mismatch, or artifact rebinding is rejected.
`assets/trust/v41_release_trust.json` binds the publication profile registry,
the provider registry, and the provider qualification bundle. Its canonical
digest is pinned in `scripts/release_trust.py`; callers cannot select another
root or path. The release validator also enforces conservative RC constraints.
This closes the registry-plus-manifest joint-rewrite attack: changing both files
still disagrees with the pinned release trust record. An attacker able to replace
the verifier code and its reviewed anchor is outside this local trust boundary;
no claim of resistance to arbitrary repository-code compromise is made.

## Duplicate Skill routing

The obsolete installation is not deleted. Before activating V4.1, preserve its
current diff as a patch/backup and change only its frontmatter identity to
`cs-nature-paper-v3-legacy` (or move it outside the active discovery path).
Then verify that exactly one active installation resolves as `cs-nature-paper`.
The backup path and post-change routing check are recorded in the audit.

## Tests and release gates

Implementation follows TDD. New tests must fail before production code is
written and must cover:

- duplicate routing elimination;
- immutable upstream pinning and license/notice preservation;
- selected file hashes and no runtime clone/download;
- provider fallback and provisional/unqualified behavior;
- independent checker requirement;
- argument graph schema, traceability, orphan Results, and claim-strength
  violations;
- adaptive profiles and justified domain-specific N/A dimensions;
- reviewer isolation metadata;
- figure, PaperSpine, and Nature adapter contracts;
- release manifest fail-closed behavior and privacy lint;
- all existing V4 regression tests.

No existing test may be weakened. The final release manifest separates
`SOFTWARE_INTEGRITY`, `PROVIDER_INTEGRITY`, `DETERMINISTIC_TESTS`,
`BEHAVIOR_BENCHMARK`, `PUBLICATION_FIELD_REGRESSION`, `HOSTED_CI`, and
`RELEASE_READINESS`.

## Non-goals

- No external provider becomes the authority for scientific truth.
- No upstream whole-repository vendoring.
- No automatic publication, submission, upload, or protocol replacement.
- No fabricated model behavior, hosted CI, or scientific evidence.
- No decorative agent/persona multiplication.
- No deletion of the obsolete installation or its local user changes.

## Acceptance criteria

V4.1 is structurally complete when all planned contracts, adapters, tests,
audits, and release bookkeeping are present and deterministic tests pass.
It is behaviorally stronger only if the comparable benchmark shows a
non-redundant improvement over PUBLIC_CORE. Until then, PUBLIC_CORE remains
the default and `recommended_merge` remains `NO` when behavior evidence is
missing.
