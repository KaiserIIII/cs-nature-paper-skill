# Experiments

## Identity and lifecycle

Use stable IDs such as `EXP-001` or a project-specific ID such as `ACC-E1`.
IDs match `^[A-Z][A-Z0-9]*-[A-Z0-9]+$`, remain unique, and are recoverable
from the filename and first heading.

Canonical statuses:

| Status | Meaning |
|---|---|
| `proposed` | An idea exists; design is incomplete. |
| `planned` | Method and implementation are ready; no job is queued. |
| `queued` | Submitted but not running. |
| `running` | Executing now. |
| `in-progress` | Active work that is not queue-shaped. |
| `pilot-complete` | A bounded pilot finished; the full run awaits a decision. |
| `completed` | Runs finished and results are documented. |
| `abandoned` | Stopped; the reason is documented. |

Common path:

```text
proposed -> planned -> queued -> running -> pilot-complete -> completed
```

`abandoned` is a valid exit from any state. Skip `pilot-complete` when no pilot
gate exists.

## Experiment template

```markdown
# EXP-001: Short title

**Created**: YYYY-MM-DD
**Status**: proposed
**Research questions**: [[RQ1]]

## Hypothesis

A specific, falsifiable claim.

## Method

- **Instrument**: Model, apparatus, population, or system under test
- **Data**: Dataset, sampling, and preprocessing
- **Conditions**: Treatments, baselines, and controls
- **Metrics**: Primary and secondary outcomes
- **Script**: `scripts/exp_001.py`
- **Revision**: Commit or content identifier
- **Key command**: Minimal replication command

## Preregistered predictions (a priori)

- **P1: Primary metric**: predicted range; reasoning; null condition.

## Decision rule (a priori)

- **If outcome A**: next action and rationale.
- **If outcome B**: diagnostic or stop condition.

## Runs

| Backend | Job ID | Description | Status | Artifacts |
|---|---|---|---|---|

## Results

Observed values, uncertainty, effect sizes, and checks.

### Outcomes against preregistered predictions

| Prediction | Verdict | Predicted | Observed |
|---|---|---|---|
| P1 | confirmed / partial / refuted / null-confirmed / not-tested | ... | ... |

## Conclusion

Interpretation, scope, and threats to validity.

## Follow-ups

- [ ] A concrete next test caused by the result

## Artifacts

- Output path or URI, content hash, and retrieval date

## Findings

Links only to syntheses that use more than this experiment.
```

## Before running

1. Reserve the next ID using the project's coordination mechanism, if any.
2. Write the method, primary outcomes, controls, and instrument checks.
3. Pause for human review of the experiment design.
4. Write the predictions and decision rule, then pause for human review of the
   preregistration before inspecting outcomes.
5. Validate the manipulation or instrument on the cheapest sufficient test.
6. Run a bounded pilot when scale, cost, or failure risk warrants one.
7. Tag every job with the experiment ID.

## Processing a completed run

1. Confirm terminal status from the backend.
2. Retrieve logs, outputs, parameters, revision, environment, runtime, and cost
   when available.
3. Check that expected outputs exist and correspond to the intended run.
4. Analyze primary outcomes before post-hoc exploration.
5. Compare every prediction with its observed value.
6. Record anomalies, failures, and missing checks.
7. Write the conclusion at the tested scope.
8. Pause for human review of the analysis, interpretation, and any proposed
   follow-up branch.
9. Update question, status, index, priority, claim, and publication pointers as
   needed.
10. Validate and make the notebook update durable.
11. Mark the job processed through the backend or ledger.

Processing must be idempotent. If the job is already processed, verify the
linked notebook evidence rather than adding a second entry.
