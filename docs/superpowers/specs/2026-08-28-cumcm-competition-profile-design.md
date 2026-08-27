# CUMCM Competition Profile Design

Date: 2026-08-28
Status: Approved for implementation
Base: `origin/main` at `6b34dcba551bdf200c2d7dd49bcb6b6057ef67c4`
Target branch: `feat/cumcm-competition-profile`

## 1. Objective

Add a CUMCM competition specialization to the existing `cs-nature-paper`
V3.1.1 control plane. The specialization is an overlay and policy layer, not a
second Research OS. It reuses the existing claims, evidence, experiment,
handoff, artifact, provenance, and generic research-graph contracts.

The feature adds three modes:

- `competition`
- `competition-autopilot`
- `competition-review`

It must not modify or move the `v3.1.1` tag, publish a release, create V3.2 or
V4, install another Skill, or add a third-party dependency.

## 2. Architectural Boundary

The approved architecture is a layered Competition Runtime:

```text
SKILL.md mode routing
        |
competition_runtime.py
        |
        +-- deterministic Competition Clock
        +-- graph policy and next-action scheduling
        +-- phase, STOP RULE, HARD FREEZE, and ETA gates
        |
        +-- competition_method_router.py
        |       +-- competition_method_router.json
        |
        +-- competition_review.py
                +-- contest rubric and score radar
```

The integration boundary is strict:

- `research_state.py` only recognizes the three modes and initializes the
  competition templates. Existing mode behavior remains byte-for-byte
  equivalent apart from the expanded mode choice list.
- `research_graph.py` stays generic. It receives no CUMCM conditionals.
- Competition scheduling reads the generic graph and uses its public
  transition functions. Graph mutations remain in the existing graph event
  chain.
- Competition clock changes use a separate append-only hash-chained event
  log. The clock snapshot is a derived projection.
- Existing `claims.json`, `evidence_ledger.json`,
  `experiment_registry.json`, `handoff.json`, and artifact manifests remain
  canonical. Competition state may reference their identifiers but may not
  duplicate their records.

## 3. Repository Layout

New runtime and content:

```text
references/competitions/cumcm.md
scripts/competition_runtime.py
scripts/competition_method_router.py
scripts/competition_review.py
scripts/competition_smoke_run.py
assets/competition/cumcm_profile.json
assets/registry/competition_method_router.json
assets/templates/competition/competition_clock.json
assets/templates/competition/competition_state.json
assets/templates/competition/competition_rules.json
assets/templates/competition/research_graph.json
assets/templates/competition/competition_review.json
assets/schemas/competition_clock.schema.json
assets/schemas/competition_state.schema.json
assets/schemas/competition_rules.schema.json
assets/schemas/competition_profile.schema.json
assets/schemas/competition_method_router.schema.json
assets/schemas/competition_review.schema.json
assets/fixtures/cumcm/synthetic_problem.json
tests/test_competition_runtime.py
tests/test_competition_e2e.py
```

Existing entrypoint, documentation, validation, CI, and generated manifest
files will receive narrowly scoped updates.

## 4. Competition State Initialization

For a competition mode, `research_state.init_state` performs the normal V3.1.1
initialization first, then:

1. Materializes the competition graph template as `research_graph.json`.
2. Refreshes `.research-graph-initial.json` from that graph.
3. Copies the four competition state templates.
4. Leaves every core evidence and provenance template unchanged.

Non-competition initialization continues to use `assets/templates/v3` only.

`competition_state.json` contains orchestration metadata and references:

```text
competition
profile_id
mode
selected_problem
question_decomposition[]
assumptions[]
candidate_models[]
current_best_model
completed_node_ids[]
running_node_ids[]
blocked_node_ids[]
largest_scoring_risk
highest_roi_next_action
submission_readiness
canonical_references
```

`canonical_references` points to the existing graph, claims, evidence,
experiment, artifact, and handoff files. It never embeds their contents.

Question records require:

```text
id, goal, inputs, decision_variables, state_variables, target, constraints,
outputs, required_evidence, assumptions, candidate_methods, validation,
dependencies
```

Assumption records require:

```text
id, assumption, reason, consequence, risk_if_violated,
validation_or_sensitivity, affected_questions
```

## 5. Competition Clock

### 5.1 Authoritative boundaries

`contest_start_utc` and `submission_deadline_utc` are the authoritative time
boundaries. Inputs must be timezone-aware ISO-8601 values. They are normalized
to UTC and serialized with a trailing `Z`. Naive timestamps, invalid timestamps,
and non-positive durations are rejected.

The runtime computes:

```text
contest_duration_seconds = deadline - start
effective_now = system_now_utc + manual_time_offset_seconds
elapsed_seconds = effective_now - start
remaining_seconds = deadline - effective_now
elapsed_ratio = elapsed / contest_duration
```

The runtime obtains system UTC on every operation. An internal `now_utc`
dependency-injection parameter exists only for deterministic tests and the
synthetic fixture; the normal CLI has no caller-supplied current-time flag.

### 5.2 Snapshot and source verification

`.research-state/competition_clock.json` is a current snapshot containing:

```text
competition
contest_start_utc
submission_deadline_utc
contest_duration_seconds
manual_time_offset_seconds
manual_override_reason
manual_override_actor
manual_override_utc
clock_status
time_source
official_source
source_verified_utc
last_checked_utc
effective_now_utc
elapsed_seconds
remaining_seconds
elapsed_ratio
current_phase
control_mode
stop_rule_active
hard_freeze_active
```

An unverified source yields `clock_status = UNVERIFIED`. The runtime may show
provisional arithmetic, but it sets `authoritative_deadline = false`, may not
claim the official time is confirmed, and may not apply time-based graph
mutations or approve a new timed job.

Once verified, lifecycle states are `SCHEDULED`, `ACTIVE`, `PAUSED`, and
`EXPIRED`. Verification requires a non-empty official source, actor, and
verification timestamp.

### 5.3 Append-only clock events

Clock configuration, verification, offset changes, pause, and resume operations
append to `.competition-clock-events.jsonl`. Each event contains:

```text
event_id
utc
actor
operation
reason
old_value
new_value
predecessor_hash
event_hash
```

Events use canonical JSON and SHA-256, following the generic graph event-chain
pattern without importing graph-specific semantics. The runtime verifies the
whole chain before appending or refreshing the snapshot. A mismatch fails
closed and leaves the snapshot untouched.

The latest valid event state is replayed when refreshing the snapshot. This
makes the event log authoritative for manual changes and the JSON snapshot
rebuildable.

Pause freezes `effective_now`. Resume records the pause duration by updating
the total manual offset, then resumes system-clock progression. No time change
is silent.

## 6. Phase Mapping and Control Modes

The bundled CUMCM profile declares a 72-hour reference schedule:

| Reference interval | Schedule phase |
|---|---|
| 0-4h | `CONTEST_INTAKE_AND_SELECTION` |
| 4-12h | `MVP_MODELING` |
| 12-30h | `FORMAL_MODELING` |
| 30-45h | `VALIDATION_AND_ROBUSTNESS` |
| 45-60h | `PAPER_AND_VISUALIZATION` |
| 60-68h | `REVIEW_AND_REVISION` |
| final 4h | `SUBMISSION_FREEZE` |

For a non-72-hour contest, the runtime maps the reference boundaries by
elapsed ratio. A profile may replace the boundaries with explicit ratios or
duration-relative values. Boundaries must be ordered, non-overlapping, and
cover the complete contest duration.

Before start, the phase is `PRE_CONTEST`; after the deadline it is
`DEADLINE_PASSED`.

Control modes overlay the schedule phase:

```text
remaining > 6h        NORMAL
2h < remaining <= 6h FINALIZATION_MODE
0h < remaining <= 2h HARD_FREEZE
remaining <= 0h       DEADLINE_PASSED
```

`FINALIZATION_MODE` activates the STOP RULE regardless of the schedule phase.
`HARD_FREEZE` overrides both normal scheduling and finalization. The profile
classifies graph nodes by risk and whether they are submission-critical.

## 7. Competition Graph

The competition graph is a valid instance of the existing generic graph
schema. Its main path is:

```text
contest_intake
problem_decomposition
problem_selection
assumptions
method_candidates
minimal_viable_model
pilot_solve
model_validation
formal_solve
sensitivity_robustness
model_improvement
visualization
paper_draft
competition_review
revision
submission_preflight
```

Failure and recovery edges support reopening assumptions or method candidates,
switching to a simpler baseline, and reducing scope. The runtime does not keep
a separate node-status store.

Each node adds policy metadata tolerated by the generic schema:

```text
phase_affinity[]
decision_relevance
scientific_risk
submission_critical
high_risk_change
job_required
```

The generic graph remains responsible for dependencies, evidence-required
PASS transitions, status validation, the materialized graph projection, and
its existing append-only graph event log.

## 8. Deterministic Scheduler

Scheduling uses:

```text
Research Graph + Clock + Risk + Decision Relevance + ETA -> Next Action
```

The algorithm is deterministic:

1. Refresh and validate the clock and its event chain.
2. Validate the generic graph and obtain dependency-ready nodes.
3. Apply control-mode policy before ranking.
4. Reject jobs that lack a non-negative estimated runtime.
5. Reject jobs whose ETA plus the profile safety margin is not strictly less
   than authoritative remaining time.
6. Rank eligible nodes by control-mode permission, current-phase affinity,
   decision relevance, scientific risk, ETA slack, and graph order.
7. Return one next action plus all allowed, deferred, and blocked candidates
   with machine-readable reasons.

Safety margins are profile data and increase monotonically from normal mode to
finalization and hard freeze. In `FINALIZATION_MODE`, high-risk changes are
blocked unless marked as a CRITICAL correction. In `HARD_FREEZE`, only
submission-critical work and locally scoped CRITICAL correctness fixes are
eligible. New scientific directions and major models are always blocked.

`schedule` is read-only. `advance` applies only policy transitions through the
generic graph API, so every `READY`, `BLOCKED`, or `REOPENED` mutation remains
auditable in the standard graph event chain. It never marks scientific work
`PASS`.

## 9. Method Router

The competition router is separate from the academic method router and covers:

- evaluation and ranking
- prediction and regression
- optimization
- classification and clustering
- graph and network models
- time series
- differential and difference equations
- simulation
- spatial and routing problems
- data preparation

The registry records method family, candidate methods, simple baselines,
assumptions, failure risks, minimum validation, data-scale cautions, and exact
versus heuristic classification where applicable.

Output contract:

```text
Problem type
Candidate models
Recommended baseline
Recommended primary model
Optional improvement
Why
Main assumptions
Failure risks
Validation plan
```

Zero trigger matches return `status = UNRESOLVED` and no selected model.
Ambiguous matches return `CONDITIONAL` with explicit conflicts. The router must
prefer a defensible baseline and explain what defect would justify upgrading
to a more complex model.

## 10. Official Rules Gate

`competition_rules.json` tracks current-year verification separately for:

- contest time and deadline
- AI-use policy
- file format
- page limit
- submission method
- problem count
- discipline and conduct requirements

Each item contains status, official source, verified UTC, actor, and notes.
Templates contain no year-specific facts. Missing verification remains
`UNVERIFIED` and submission preflight cannot pass. Sources must be current
official primary sources; the runtime never fabricates or infers them.

## 11. Competition Review

Competition review validates findings with:

```text
Issue
Severity
Location
Why it matters
Smallest sufficient fix
Estimated scoring impact
Evidence anchors
```

Severities are `CRITICAL`, `MAJOR`, and `MINOR`. CRITICAL includes wrong-task
answers, mathematical errors, leakage, non-reproducible results, unit errors,
paper/code inconsistencies, and results without real execution evidence.

The score radar contains ten integer scores from 0 through 10:

```text
problem_understanding
model_appropriateness
mathematical_rigor
implementation
validation
innovation
visualization
writing
reproducibility
overall_coherence
```

It also requires strongest point, weakest point, largest award-level blocker,
and highest-ROI improvement. It is a diagnostic rubric, not an award
probability. Award guarantees and probability language fail validation.

## 12. Dashboard

Every major competition runtime operation returns a dashboard built from the
fresh clock snapshot and canonical graph/state references:

```text
Competition time
Elapsed
Remaining
Current phase
STOP RULE
Hard freeze
Completed
Running
Blocked
Current best model
Largest scoring risk
Highest-ROI next action
Submission readiness
```

Time fields are copied from runtime computation, never composed by an LLM.

## 13. CLI Surface

The runtime exposes bounded commands:

```text
competition_runtime.py configure-clock PROJECT --start ... --deadline ...
  [--official-source ...] --actor ...
competition_runtime.py verify-clock PROJECT --official-source ... --actor ...
competition_runtime.py adjust-clock PROJECT --offset-seconds ... --reason ...
  --actor ...
competition_runtime.py pause-clock PROJECT --reason ... --actor ...
competition_runtime.py resume-clock PROJECT --reason ... --actor ...
competition_runtime.py status PROJECT
competition_runtime.py schedule PROJECT [--job-eta-seconds ...]
competition_runtime.py advance PROJECT [--job-eta-seconds ...] --actor ...
competition_runtime.py validate PROJECT
competition_runtime.py dashboard PROJECT
```

Method routing and review use their dedicated scripts. CLI failures produce
machine-readable JSON and non-zero exit status.

## 14. Synthetic CUMCM E2E

The synthetic fixture is a small, deterministic facility-selection problem.
The E2E runner:

1. Creates a temporary competition project.
2. Initializes competition state and the competition graph.
3. Configures and verifies a fixture clock using injected test time.
4. Decomposes the fixture question and routes it to a simple exhaustive
   baseline before any optional heuristic.
5. Executes the baseline with Python standard-library code.
6. Stores command, input, configuration, output hash, table, and figure-like
   data artifacts through the existing evidence/provenance mechanisms.
7. Exercises graph scheduling, review, STOP RULE, and HARD FREEZE decisions.
8. Reports `HARNESS_SELF_TEST` and explicitly states model-backed behavior
   evaluation is `NOT_RUN`.

The fixture cannot be described as real CUMCM performance, a real model
evaluation, or evidence of award probability.

## 15. Test Strategy

Implementation follows RED-GREEN-REFACTOR. Tests are written and observed
failing before production changes.

Focused tests cover:

- competition-only initialization and unchanged research initialization
- timezone normalization and naive timestamp rejection
- actual-duration calculation
- 72-hour phases and proportional non-72-hour mapping
- unverified clock fail-closed behavior
- STOP RULE, HARD FREEZE, pre-start, pause/resume, and expired states
- append-only offset events, replay, and tamper rejection
- ETA margin enforcement and increasing late-stage margins
- scheduler ranking and overlay-only graph mutations
- router category coverage, simple-baseline preference, ambiguity, and
  `UNRESOLVED`
- official-rule preflight gate
- decomposition and assumption contracts
- reviewer severity, score bounds, and award-theater rejection
- dashboard fields sourced from runtime state
- synthetic competition E2E
- preservation of all existing 57 regression tests

Full verification also runs registry validation, release validation, manifest
checks, privacy lint, security pressure fixtures, the original E2E smoke, and
the new competition E2E smoke across the repository's supported Python
versions and operating systems through CI.

## 16. Failure and Integrity Rules

- No fabricated data, execution, sensitivity result, citation, or model effect.
- No model promotion based only on sophistication.
- Failed pilots remain traceable through existing experiment/provenance state.
- Clock-event tampering, malformed time, missing official verification, and
  missing ETA fail closed.
- The final six hours prioritize correctness and submission readiness.
- The final two hours prohibit new scientific direction except a locally
  scoped fix for a documented CRITICAL error.
- The runtime cannot publish, submit, or perform another irreversible external
  action.

## 17. Acceptance Criteria

The implementation is acceptable when:

1. All three modes initialize and route correctly.
2. Clock, phase, STOP RULE, HARD FREEZE, ETA, and scheduling decisions are
   deterministic and tested.
3. The generic Research Graph and canonical provenance contracts remain
   unchanged.
4. Router zero-match is `UNRESOLVED`.
5. Current-year official rules remain unverified until backed by explicit
   official sources.
6. The synthetic CUMCM E2E passes without claiming model evaluation.
7. Every new test and all 57 prior tests pass.
8. No third-party dependency, external Skill, tag change, release, or unrelated
   refactor is introduced.
