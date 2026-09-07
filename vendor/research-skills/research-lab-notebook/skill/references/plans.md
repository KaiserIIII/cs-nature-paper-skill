# Plans

A plan is a version-controlled contract for one bounded research objective. It
records scope, dependencies, decisions, handoffs, review gates, and exit
conditions across experiments, agents, harnesses, and sessions. Use `plans/`
when several experiments or phases serve that objective.

## Plans persist across sessions

A notebook plan preserves the research contract in version control. One agent
can draft it, a researcher can review it, another agent or harness can execute
an authorized phase, and a later agent can close it. Every participant reads
the same objective, evidence, dependencies, gates, risks, and terminal
conditions.

Claude Code and Codex planning surfaces organize and approve an agent's current
task. Use them to reason about creating or executing the notebook plan. Keep the
research contract in the plan file so it remains available across context
resets, products, collaborators, and sessions.

Plans are appropriate when at least one of these is true:

- the objective spans several experiments or decision-gated phases;
- creation, execution, and review may belong to different people or agents;
- work must resume after the current session or context window;
- a scheduler, CI job, or harness needs a stable machine-readable `next_action`;
- stopping, cost, or evidence gates must remain visible before execution.

## Frontmatter

```yaml
---
status: draft
summary: Determine whether the effect survives two control families
next_action: Design the first pilot
owner: researcher
reviewer: collaborator
current_phase: Phase 1
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

Required fields are `status`, `summary`, `next_action`, `created`, and `updated`.
Optional fields are `owner`, `reviewer`, and `current_phase`. Use `current_phase`
for active and blocked plans so a new executor can locate the live gate without
reconstructing the plan.

Statuses are `draft`, `active`, `blocked`, `gated`, `backlog`, `superseded`,
`completed`, and `abandoned`. Use a filename of the form
`YYYY-MM-DD-lowercase-topic.md`, where the date is the creation date. Active
plans live directly under `plans/`. Other plans live in the subdirectory named
for their status.

Status-specific fields preserve why work is waiting or ended:

| Status | Required metadata |
|---|---|
| `gated` | `gate` and either `revisit_when` or `promote_when` |
| `backlog` | Either `revisit_when` or `promote_when` |
| `superseded` | `superseded_by` |
| `abandoned` | `abandoned_because` |

`next_action` is a handoff pointer, not a task queue. Keep it bounded and update
it only after the owning phase's evidence and disposition are durable. It must
be non-empty for a nonterminal plan. Set it to an empty value or `none` when the
status is `superseded`, `completed`, or `abandoned`.

`superseded`, `completed`, and `abandoned` are terminal. Set their
`next_action` to an empty value, `none`, or `null`.

## Body

```markdown
# Plan title

## Objective

A falsifiable outcome and the decision it informs.

## Existing evidence

Links to questions, experiments, findings, and claims.

## Phases

### Phase 1: Cheap validation

- Inputs and dependencies
- Bounded work
- Acceptance and stop conditions
- Expected notebook updates

### Phase 2: Full measurement

Created only after Phase 1 passes its gate.

## Risks and controls

Scientific, operational, cost, and data-loss risks.

## Terminal conditions

- Completed when ...
- Blocked when ...
- Abandoned when ...
```

Every plan requires `Objective`, `Existing evidence`, `Phases`, `Risks and
controls`, and `Terminal conditions`. A completed or abandoned plan also
requires:

```markdown
## Disposition

Why the plan ended and which terminal condition applied.

## Evidence

Links to the experiments, findings, claims, and revisions that support closure.
```

## Execution boundary

A plan records intent and approved scope. An agent or harness may carry out only
the phase or actions the user authorized. Expensive, destructive, privileged,
publication, and external actions require their own authority. Keep
`next_action` bounded; never turn it into an infinite monitor or autonomous
loop.

Pause for human review before changing a draft plan to active. After each phase,
write its evidence and proposed disposition, then pause again. The reviewer
chooses whether to continue, revise, move the plan to `gated` or `backlog`, or
close it. A gated follow-up requires another explicit review before execution.
Record the gate and the condition that permits reconsideration.

When handing a phase to another agent or harness, pass the plan path and phase
name rather than copying its instructions into a prompt. The executor records
job IDs and outputs in experiment files, updates the plan's status and
`next_action`, and leaves scientific conclusions in experiments or findings.
The plan coordinates evidence production. Experiments and findings own the
evidence.

When the plan reaches a terminal state, write the disposition and evidence,
update indexes and pointers, then remove it from active queues.

Regenerate and validate the plan index with:

```bash
python3 <skill-directory>/scripts/validate-notebook.py <notebook> \
  --write-plan-index --strict
```

Use `--format json` when a dashboard, editor, or external research tool consumes
diagnostics. This interface is the integration boundary. The notebook format
remains application-independent.
