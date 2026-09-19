# CUMCM Competition Profile

Use this profile only with `competition`, `competition-autopilot`, or
`competition-review`. It is a policy overlay on the existing Research OS. It
does not replace the canonical graph, claims, evidence, experiments, artifacts,
handoffs, or provenance contracts.

## Operating contract

```text
competition = CUMCM
team_size = 3
reference_time_budget = approximately 72 hours
primary_goal = maximize the defensible contest score
```

The actual contest duration is always computed from verified start and
deadline timestamps. Never assume that a particular contest is exactly 72
hours. Never promise an award or estimate award probability.

The shared objective is:

```text
Model + Explanation + Visualization + Paper
```

Prefer correctness, clarity, interpretability, completion, and presentation
over unnecessary sophistication. Do not fabricate data, execution, numerical
results, sensitivity findings, citations, or model effects.

## Modes

### `competition`

Execute an already selected problem through modeling, implementation,
validation, writing, review, repair, and preflight. Continue while author
action is `NONE`; ordinary scientific and implementation choices inherit the
v3.2 autonomy policy and do not create a second authorization system.

### `competition-autopilot`

Read every supplied problem before modeling. For each problem, produce:

```text
Structured question decomposition
Problem type
Core difficulty
Data requirement
Computation risk
Algorithm risk
Paper potential
Time-to-completion risk
Defensible 72-hour completion assessment
```

Select a problem from evidence and feasibility, not from how advanced a method
sounds. Use qualitative `HIGH` / `MEDIUM` / `LOW` profiles instead of false
precision. `AUTO_SELECT` a clear winner and record the rationale, rejected
alternatives, largest selection risk, and fallback. Ask the author only for a
material tie, missing decisive data, a rule-required choice, or unknown
author-owned external resources. Then continue the full Director lifecycle to
`COMPETITION_SUBMISSION_READY`.

### `competition-review`

Review from a contest evaluator's perspective. Attack problem understanding,
assumptions, formulas, model fit, solution, result credibility, validation,
sensitivity, innovation, figures, abstract, paper logic, and reproducibility.
Order findings `CRITICAL`, `MAJOR`, then `MINOR`. Repair only scoring-relevant
issues within the current clock policy.

## Verify current official rules

Do not hardcode a year's dates or rules. Before activation and submission,
verify current official primary sources for every item in
`competition_rules.json`:

```text
contest start and deadline
problem count and participant eligibility
AI-use policy
paper format and page limit
file naming and attachment requirements
code requirements
submission platform and method
anonymity and discipline requirements
```

Each item records `rule_id`, `status`, `official_source`, retrieval and
verification UTC, actor, and exact supporting region/evidence. Only an
official primary source may produce `VERIFIED`; prior-year material is
`BACKGROUND_ONLY`, and incompatible official statements are `CONFLICTING`.
Unverified rules do not block early modeling, but they fail submission
preflight closed.

## Competition Clock

The only authoritative time boundaries are timezone-aware ISO-8601 values:

```text
contest_start_utc
submission_deadline_utc
```

Run the Competition Runtime at every major action. It obtains system UTC and
computes:

```text
contest_duration = deadline - start
effective_now = system_now_utc + manual_time_offset_seconds
elapsed = effective_now - start
time_remaining = deadline - effective_now
elapsed_ratio = elapsed / contest_duration
```

The model must not estimate these values. `competition_clock.json` is a
derived snapshot. Configuration, verification, manual offset, pause, and
resume operations enter `.competition-clock-events.jsonl`, whose predecessor
and event hashes are checked before every update.

Manual correction requires:

```text
manual_time_offset_seconds
manual_override_reason
manual_override_actor
manual_override_utc
```

No correction is silent. An unverified clock may show provisional arithmetic,
but it cannot authorize deadline policy, timed jobs, or a claim that the
official deadline is confirmed.

Clock events are `CONFIGURE`, `VERIFY`, `ADJUST`, `OFFICIAL_EXTENSION`,
`PAUSE`, or `RESUME`. Every event contains `event_id`, `event_type`, before and
after snapshots, reason, actor, UTC, predecessor hash, and event hash. Any
chain mutation fails closed.

## Schedule phase and control mode

The 72-hour reference profile is:

| Reference time | Schedule phase | Primary work |
|---|---|---|
| 0-4h | `CONTEST_INTAKE_AND_SELECTION` | read, decompose, compare, select |
| 4-12h | `MVP_MODELING` | executable baseline and first interpretable result |
| 12-30h | `FORMAL_MODELING` | primary model and formal solution |
| 30-45h | `VALIDATION_AND_ROBUSTNESS` | validation, sensitivity, comparison, error analysis |
| 45-60h | `PAPER_AND_VISUALIZATION` | paper body, figures, abstract, result explanation |
| 60-68h | `REVIEW_AND_REVISION` | contest review and scoring-relevant repair |
| final 4h | `SUBMISSION_FREEZE` | consistency, format, and submission package |

For a different duration, map these boundaries proportionally unless the
selected competition profile declares valid explicit boundaries.

Control modes override schedule phases:

```text
remaining > 6h        NORMAL
2h < remaining <= 6h FINALIZATION_MODE
0h < remaining <= 2h HARD_FREEZE
remaining <= 0h       DEADLINE_PASSED
```

`SUBMISSION_FREEZE` is a normal schedule phase. `FINALIZATION_MODE` and
`HARD_FREEZE` are higher-priority policy overlays.

## Adaptive Competition Graph

The competition graph uses the generic Research Graph engine:

```text
Contest Intake
-> Problem Decomposition
-> Problem Selection
-> Assumptions
-> Method Candidates
-> Minimal Viable Model
-> Pilot Solve
-> Model Validation
-> Formal Solve
-> Sensitivity / Robustness
-> Model Improvement
-> Visualization
-> Paper Draft
-> Competition Review
-> Revision
-> Submission Preflight
```

Failure can reopen method candidates or assumptions, switch to a simpler
baseline, or reduce scope. Sunk cost never justifies retaining a clearly failed
model. Graph PASS transitions still require canonical evidence anchors.

The deterministic next-action rule is:

```text
Research Graph
+ Clock
+ Competition Phase
+ Scientific Risk
+ Scoring Risk
+ Decision Relevance
+ Expected Information Gain
+ ETA and Safety Margin
+ Paper / Validation / Complexity Debt
+ Autonomy Policy
= Next Action
```

Do not substitute conversational preference for this policy.

Temporary ETA, finalization, hard-freeze, or unverified-clock restrictions are
runtime policy projections such as `TEMPORARILY_BLOCKED`; they never overwrite
a scientifically `READY` canonical graph node. The node becomes eligible again
when the condition clears without a manual reopen.

For the reference 72-hour profile, a missing executable, interpretable MVP at
T+10h is high risk. At T+12h, trigger scope reduction or a simpler method.

## Job ETA gate

Before every new job, record:

```text
estimated_runtime
remaining_time
safety_margin
```

The strict admission condition is:

```text
estimated_runtime + safety_margin < time_remaining
```

Safety margins increase in finalization and hard freeze. A missing ETA blocks
the job. A non-critical 2.5-hour job with three hours remaining does not pass
the finalization gate.

## Dashboard

After each major operation, report Runtime-derived values:

```text
Competition / Problem selected:
Elapsed / Remaining / Phase / Control mode:
Completed / Running:
Blocked by science / policy / time:
Current best model / Baseline / Primary model:
Largest scientific risk / Largest scoring risk:
Paper debt / Validation debt / Complexity debt:
Highest-ROI next action:
Submission readiness:
Author action required:
```

Do not hand-calculate or rewrite elapsed and remaining time.

## Question decomposition

Transform each contest question into one record:

```text
ID
Goal
Inputs
Known data
Unknown data
Decision variables
State variables
Parameters
Target
Objective
Constraints
Required outputs
Required evidence
Dependencies
Candidate method families
Validation requirements
Likely paper section
Difficulty
Execution risk
```

Record dependencies such as `Q1 -> Q2 -> Q3`. Reuse definitions, units, data,
and identifiers across dependent questions.

## Assumption contract

Every assumption records:

```text
Assumption
Reason
Consequence
Risk if violated
Validation or sensitivity method
Affected questions
```

Do not write an unexplained "other factors remain unchanged" assumption. Name
the factors, why they may be excluded, and what failure would change.

## Method selection

Run `scripts/competition_method_router.py`. It covers evaluation, prediction,
optimization, classification/clustering, graph/network, time series,
differential equations, simulation, spatial/routing, and data preparation.

Required output:

```text
primary_family
secondary_families
dependency
baseline_first
candidate models
recommended baseline and primary model
optional justified improvement
assumptions, failure risks, and validation plan
```

If no category matches, return `UNRESOLVED`. Do not guess. Distinguish exact,
heuristic, and metaheuristic optimization. Use an exact formulation when it
fits the scale and time budget.

Prediction, optimization, evaluation, classification/clustering, simulation,
and differential-equation implementations are bounded native baselines. If the
question is unresolved or selects a family outside those baselines, keep the
node `RUNNING` and request a problem-specific Host Modeling plan. The accepted
plan must define each question's formulation, variables, parameters,
assumptions, objective, constraints, baseline, primary model, upgrade
condition, validation plan, and implementation plan. Then request actual host
solver code and pass it to deterministic pilot/formal execution. Do not assume
that arbitrary production problems contain `series`, `alternatives`, `records`,
or `dynamics`; those fields belong only to compatible bounded baselines.

The model-selection rule is:

```text
simplest model that explains the question
>
complex model that cannot be interpreted or completed
```

Before upgrading, answer:

```text
Which baseline defect does the new model fix?
Does observed validation show a real improvement?
Is that improvement worth the added paper and execution complexity?
```

Small datasets do not justify deep learning by default. Do not add neural
networks, random forests, genetic algorithms, or particle swarm optimization
for appearance.

## Computation and provenance

Use the existing experiment and evidence systems. Classify work as `PILOT`,
`FORMAL`, or `EXPLORATORY_POST_HOC`. A formal result records:

```text
code
input
configuration
command
output
hash
figure
table
```

Keep failures traceable. A pilot is not formal evidence. Prefer Python and the
project's existing dependencies; do not add packages merely because they are
common in modeling contests. A unified reproducible entry point such as
`python run.py` is preferred when the project owns one.

The Competition Executor creates `src/`, `data/`, `data_raw/`,
`data_processed/`, `results/`, `figures/`, `tables/`, `configs/`, `logs/`, and
`paper/`. Formal execution records command, exit code, runtime, input/config/
code/output hashes, environment, and stdout/stderr. It independently checks
feasibility, bounds, integrality, capacity, conservation, units, and objective
recalculation where applicable.

## Validation

Select checks from the model's actual threats:

```text
sanity check
boundary check
sensitivity analysis
robustness check
baseline comparison
error analysis
```

Important parameters should normally receive `+/-5%` and `+/-10%` checks or a
better justified domain range. If the conclusion reverses, state that the
model is highly sensitive. Never invent a sensitivity result.

Every variable records symbol, meaning, unit, range, and source. Core equation
dimension errors, rate/quantity confusion, percentage/proportion confusion,
or failed conversions are `CRITICAL`. Numeric values must agree across the
abstract, body, tables, figures, and conclusion.

## Paper and abstract

Begin writing when the formal route stabilizes; do not defer the paper until
the final six hours. The abstract is a priority artifact:

```text
Paragraph 1: problem and overall approach
For Q1: model, method, actual core result
For Q2: model, method, actual core result
For Q3: model, method, actual core result
Final paragraph: advantages, stability, and application value
```

Prefer actual numbers backed by evidence. Do not use vague success language in
place of results.

Each figure supports one conclusion. Check axis, unit, legend, caption, font,
resolution, and data consistency. Prioritize model structure, trend, fit,
error, sensitivity, optimization, spatial distribution, and model comparison
only when they answer the question.

Every figure traces to source data, rendering code, and hashes. The paper
checker requires all questions, main models, variables, figure/table files,
and cited artifacts; it rejects `TODO`, `XXX`, fake citations, missing units,
or an abstract without every question outcome.

## Competition review

Run `scripts/competition_review.py`. Findings require:

```text
Issue
Severity
Location
Why it matters
Smallest sufficient fix
Estimated scoring impact
Evidence anchors
```

CRITICAL includes wrong-task answers, mathematical or formula errors, leakage,
non-reproducible results, unit errors, paper/code numerical mismatch, and key
results without actual execution. MAJOR includes missing validation, overly
strong assumptions, unsupported parameter sources, weak model rationale,
insufficient sensitivity, weak explanation, or complexity without benefit.
MINOR includes figure, layout, wording, notation, and citation defects.

The diagnostic score radar has ten integer axes from 0 through 10:

```text
Problem understanding
Model appropriateness
Mathematical rigor
Implementation
Validation
Innovation
Visualization
Writing
Reproducibility
Overall coherence
```

Also report the strongest point, weakest point, largest award-level blocker,
and highest-ROI remaining improvement. These are diagnostic priorities, not
award probabilities.

Unresolved `CRITICAL` or `MAJOR` findings enter an automatic repair loop:
root-cause analysis, smallest sufficient authorized fix, affected-artifact
revalidation, figure/paper refresh, and repeat review. Do not ask the author
for ordinary repairs.

## Completion and submission boundary

`COMPETITION_SUBMISSION_READY` requires a selected problem, all questions
answered, complete formal outputs, observed or verified load-bearing results,
formula/unit/numeric checks, baseline, validation, sensitivity, traceable
figures, complete paper and abstract, no unresolved CRITICAL finding, resolved
or explicitly accepted residual MAJOR risk, verified official rules, and a
passing submission preflight. The Director keeps executing while author action
is `NONE`. Actual upload or submission remains `ASK_AUTHOR`.

## STOP RULE and HARD FREEZE

When `time_remaining <= 6 hours`, activate `FINALIZATION_MODE`. By default,
block a core-model replacement, full data-pipeline redesign, large refactor,
unsafe experiment, high-risk new model, or broad new search direction. Allow a
scoped CRITICAL correction, numerical and formula consistency checks, figure
checks, abstract strengthening, missing sensitivity evidence, citation checks,
layout, and submission-format checks.

When `time_remaining <= 2 hours`, activate `HARD_FREEZE`:

```text
NO NEW SCIENTIFIC DIRECTION
NO NEW MAJOR MODEL
NO HIGH-RISK EXPERIMENT
```

Priority becomes:

```text
CRITICAL correctness
> submission integrity
> abstract
> result consistency
> figures
> format
> minor wording
```

Only a documented CRITICAL scientific error can permit a locally scoped freeze
exception. The ETA gate still applies.

## Invocation examples

```text
Use $cs-nature-paper in competition-autopilot mode.
Read all supplied CUMCM problems and the verified competition clock. Compare
problem structure, data, computation, algorithm, paper, and time risk. Select
the clear winner automatically, build its question graph, and execute baseline,
formal solution, validation, sensitivity, figures, paper, review, repair, and
preflight. Stop only at COMPETITION_SUBMISSION_READY or a genuine author-only
boundary.
```

```text
Use $cs-nature-paper in competition mode.
Read current competition state. Refresh the clock and dashboard. Use the graph,
risk, decision relevance, and ETA to execute the highest-ROI eligible action.
Ask only for payment, credentials, sensitive-data disclosure, administrator
rights, a rule-required human action, irreversible external operation, or final
submission.
```

```text
Use $cs-nature-paper in competition-review mode.
Audit mathematical correctness, model fit, assumptions, data, paper/code result
consistency, sensitivity, abstract, figures, logic, and reproducibility. Sort
CRITICAL, MAJOR, and MINOR findings and fix only scoring-relevant issues allowed
by the current clock policy.
```
