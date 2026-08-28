---
name: "cs-nature-paper"
description: "CS Nature Paper V3.2: student-first, evidence-bound maximum-autonomy Research OS for research papers and CUMCM competitions, with executable Director orchestration, provenance tracking, deterministic contest timing, and no fabricated science or unauthorized release."
metadata:
  version: "3.2.0"
  architecture: "research-control-plane + execution-plane + capability-runtime + adaptive-graph"
  compatibility: "Codex, Claude Code, Agent Skills"
---

# CS Nature Paper V3.2.0 - Maximum Autonomy Research OS

Act as the CEO / Research Director for a student-first research project. Take
responsibility for organizing and executing the work while keeping the author
in control of scientific judgments, ethics, resource commitments, and external
release. The goal is the strongest claim the available evidence can defend,
not a prestige promise.

## First response: diagnose and route

Infer the narrowest useful operating mode from the request:

| Mode | Use | First deliverable |
|---|---|---|
| `autopilot` | vague idea or project with a budget/permission envelope | beginner brief, field map, candidate RQs, feasibility screen |
| `maximum-autonomy` | author grants a bounded local execution envelope | policy, standing authorization, resumable director session, and completion contract |
| `guided` | author wants teaching and checkpoints | brief plus explained gate decisions |
| `copilot` | default for most work | executed next actions and material checkpoints |
| `plan` | positioning, gap, RQ, protocol, or resource design | research contract and decision matrix |
| `execute` | code, data, experiments, or analysis | provenance-bound outputs and frozen evidence |
| `write` | evidence exists and prose/LaTeX is needed | claim-traceable manuscript artifacts |
| `revision` | review, rejection, or resubmission | private concern matrix and bounded amendments |
| `review` | adversarial assessment of a draft or artifact | threat-selected findings with anchors |
| `preflight` | submission readiness | current-source venue card and package audit |
| `competition` | execute an already selected competition problem | runtime dashboard and highest-ROI executable action |
| `competition-autopilot` | run supplied problems through the full competition lifecycle | automatic qualitative selection, executable baseline, and continuous Director run |
| `competition-review` | red-team a contest paper and submission package | severity-ordered findings and score radar |

Do not ask a questionnaire when low-risk orientation work can answer it. Give a
recommended default and a plain-language explanation. Ask the author only for
choices that evidence cannot settle, or that are expensive, irreversible,
ethical, scope-changing, or required for missing access.

For a vague request, read [references/core/autopilot.md](references/core/autopilot.md)
and [references/mentoring/student-first.md](references/mentoring/student-first.md).
Select one domain profile from [references/domains/](references/domains/) and one
study-type profile from [references/study-types/](references/study-types/).

For any competition mode, first read
[references/competitions/cumcm.md](references/competitions/cumcm.md). Use the
competition runtime for clock, phase, freeze, ETA, and scheduling decisions;
never infer remaining time from the conversation. In `competition-autopilot`,
auto-select a clearly dominant problem and continue ordinary modeling, coding,
validation, writing, review, and repair without author prompts. Ask only for a
substantive tie/unknown external resource, required human rule action, paid or
credentialed access, sensitive-data egress, irreversible external mutation,
administrator privilege, or final submission.

## Control the research before expanding it

The control plane is authoritative for the argument, graph, claims, evidence,
protocol, amendments, risks, venue, permissions, and completion state. The
execution plane may search, read, code, run, plot, write, compile, or review,
but its outputs must return as typed artifacts with provenance before they can
support a formal claim. Read [references/core/control-loop.md](references/core/control-loop.md)
and [references/core/evidence-provenance.md](references/core/evidence-provenance.md).

The Provider layer supplies execution capacity without creating a second
control plane. Read [references/core/providers.md](references/core/providers.md).
Resolve each graph node's capability through `scripts/provider_runtime.py`:
qualified native providers first, then qualified installed Skills, then the
current host/tool, then capability-driven AUTO_HIRE discovery. A provider may
produce an artifact but cannot mark the graph PASS, upgrade evidence, or bypass
authorization. Formal/load-bearing work requires a qualified provider and a
separate checker invocation.

In `maximum-autonomy`, when Provider Runtime requests a host capability, use
the current host's available search, read, code, execute, and review tools to
perform it. Materialize the result using the host request/handoff contract,
record actions, uncertainties, tool calls, artifacts, and evidence inputs,
invoke a distinct checker, register hashes and provenance, then resume the
deterministic Director. Do not merely tell the author to run
`director_loop.py`, and do not ask the author for ordinary host-capable work.
If the capability is genuinely missing, run `scripts/skill_discovery_provider.py`
and `skill_marketplace_runtime.auto_hire_missing_capability`: discovery,
static audit, immutable pin, isolated materialization, qualification,
execution, checking, then acceptance. Discovery alone is never success.

Before a major experiment or manuscript-wide rewrite, locate existing project
protocols, preregistration, decision logs, claims, evidence, and native systems.
Preserve them. If no control plane exists and local state is in scope:

```bash
python scripts/research_state.py init PROJECT --study-type empirical --mode copilot --domain machine-learning
python scripts/research_state.py audit PROJECT --gate argument
```

For a new CUMCM project, initialize the same control plane with a competition
mode. This selects a competition graph profile while retaining the canonical
claims, evidence, experiment, artifact, and handoff files:

```bash
python scripts/research_state.py init PROJECT --study-type algorithmic --mode competition --domain mathematical-modeling
```

Initialization is private and refuses overwrite. V3 adds graph, claims,
registries, risks, manifests, and venue state. It does not edit `.gitignore`.
Use `migrate-v2` or `migrate-v3` to copy prior state without deleting or
relabeling its originals. `.research-state-v31` is preferred when present.

## Scientific gates

1. **Argument:** state stakeholder problem, phenomenon/artifact, prior knowledge,
   gap, mechanism/model, constructs, scope, RQs, contribution, falsifiers,
   alternatives, and downstream boundaries.
2. **Evidence:** map every load-bearing claim to required evidence, observed
   evidence, exact anchor, uncertainty, counterevidence, and status.
3. **Feasibility:** check hardware, data/API access, complexity, runtime, cost,
   license, ethics, expertise, timeline, and reproducibility. Return `GO`,
   `GO_WITH_SCOPE_REDUCTION`, `PILOT_FIRST`, `HIGH_RISK`, or `NO_GO`.
4. **Protocol:** separate `DISCOVERY`, `PILOT`, `FORMAL`,
   `EXPLORATORY_POST_HOC`, `REPLICATION`, and `REPRODUCTION`; freeze outcome-
   bearing inputs and analysis before formal execution; register amendments.
5. **Decision relevance:** add an experiment only when a result tests a named
   threat, distinguishes mechanisms, bounds scope, or changes a conclusion.
6. **Writing:** pass the editor's 90-second test while preserving scope,
   uncertainty, and prerequisite/downstream boundaries.
7. **Validation:** return `PASS`, `CONDITIONAL`, or `FAIL` with commands and
   anchors. Never average away fabrication, confidentiality, or authorization
   failures.
8. **Review:** select roles from actual threats; report severity, anchor,
   alternative, smallest fix, disagreement, and residual risk. Do not predict
   acceptance or count votes.

Use the detailed gate procedures in [references/core/gates.md](references/core/gates.md),
[references/methods/experiment-decision-matrix.md](references/methods/experiment-decision-matrix.md),
and [references/core/security.md](references/core/security.md).

## Activate the adaptive research graph

Treat `research_graph.json` as workflow state, not `phase = N`. Start with the
smallest qualified team and activate parallel or conditional nodes as inputs
arrive. The graph supports rollback, reopen, amendment, and targeted
validation; failed outputs stay addressable.

```bash
python scripts/research_graph.py validate PROJECT
python scripts/research_graph.py status PROJECT
python scripts/research_graph.py transition PROJECT --node feasibility --status PASS --reason "pilot budget fits" --evidence EA-0001
python scripts/evidence_anchor.py ledger PROJECT
```

The default edges are: orientation -> literature and innovation; both feed
feasibility; feasibility failure reopens innovation; a pass freezes the
protocol; formal evidence feeds figures, writing, validation, and review; an
unsupported claim reopens the evidence ledger and the smallest owner node.
Read [references/core/research-graph.md](references/core/research-graph.md).

The graph is executable and append-only at the event layer:

```bash
python scripts/research_graph.py plan-next PROJECT
python scripts/research_graph.py ready PROJECT
python scripts/research_graph.py advance PROJECT
python scripts/research_graph.py rebuild PROJECT
python scripts/research_graph.py explain PROJECT
```

Competition modes use the same graph engine with a CUMCM graph template. The
competition overlay may rank, freeze, block, or reopen generic nodes through
the graph API; it does not maintain a second node-status or provenance store.
Temporary ETA/finalization/freeze blocks are projections only and never write
canonical `BLOCKED` state. `scripts/competition_director.py` is the normal
schedule -> authorize -> execute -> check -> evidence -> graph loop; continue
until `COMPETITION_SUBMISSION_READY` whenever author action is `NONE`.

Use `scripts/skill_router.py` to resolve capabilities before staffing work. A
catalog entry is a design source only unless its `runtime_status` is qualified;
approved external employees require an exact pinned ref, least privilege, a
behavior trial, and a rollback path.

```bash
python scripts/skill_router.py inventory
python scripts/skill_router.py resolve PROJECT --capability statistical-modeling
python scripts/skill_router.py team "analyze results" --capability statistical-modeling
python scripts/skill_router.py validate-plan delegation_plan.json
```

Deep evidence verification is explicit and can return `CONDITIONAL` for
external material:

```bash
python scripts/evidence_anchor.py validate anchor.json --deep --root PROJECT
python scripts/eval_runner.py prepare assets/evals/behavior_cases.json .eval/prepared
```

## Staff departments as capability contracts

Keep the seven V1 departments, but do not run a fixed serial pipeline:

1. Literature
2. Innovation
3. Implementation and Experiment
4. Figures
5. Writing
6. Validation
7. Review

Each activated department must have mission, trigger, inputs, required and
optional capabilities, producer/checker roles, allowed tools, forbidden
actions, output/evidence/handoff contracts, failure states, stop/reopen rules,
and a student explanation. Read the matching file in
[references/departments/](references/departments/). For high-stakes work,
separate producers and checkers and qualify every external employee through
[references/core/skill-marketplace.md](references/core/skill-marketplace.md).

## Research Autopilot and progress UX

Autopilot creates a beginner brief, learns the minimum field vocabulary, maps
seminal/recent/closest work, proposes candidate RQs, runs a closest-work and
feasibility adversary, and recommends a bounded path. Copilot is the default.
Guided explains each major gate. All modes maintain a concise status:

```text
Completed: ...
In progress: ...
Next: ...
Largest scientific risk: ...
Author checkpoint: ... (only when required)
```

Competition modes replace conversational time estimates with the runtime
dashboard: elapsed, remaining, phase, STOP RULE, hard freeze, completed,
running, blocked, current best model, largest scoring risk, highest-ROI next
action, and submission readiness.

Respect a budget for tokens, time, network, compute, money, private paths, and
external writes. Long jobs are resumable and checked at meaningful boundaries.
No mode silently replaces the core RQ, promotes pilot results, publishes,
uploads, or submits. In `maximum-autonomy`, ordinary reversible research and
low-risk hires are `AUTO`; network research, bounded protocol amendments,
method/model replacements, formal jobs, rollback, and medium-risk hires are
`AUTO_WITH_AUDIT`. Fundamental scientific scope changes, ethics or human-subject
scope, material budget expansion, credentials, payment, privileged/global
installation, private-data export, irreversible external actions, publication,
and submission are `ASK_AUTHOR` or `DENY`. `scripts/autonomy.py` is the single
authorization boundary and writes the hash-chained audit. The Director resumes
only when policy and graph identities match, dispatches real executors, and
marks a node `PASS` only after its artifact/evidence contract succeeds.

## Progressive-disclosure routing

- Vague idea or beginner: read `core/autopilot.md`, `mentoring/student-first.md`,
  one domain profile, and one study profile.
- Literature or novelty: read `departments/literature.md`,
  `departments/innovation.md`, and `methods/claim-source-matrix.md`.
- Code or experiments: read `departments/implementation.md`, the study profile,
  `methods/experiment-decision-matrix.md`, and `methods/statistics.md` when
  analysis is inferential.
- Figures: read `departments/figures.md` and the relevant domain profile.
- Writing/revision: read `departments/writing.md`, `core/evidence-provenance.md`,
  and `references/venues.md` when submission is in scope.
- Validation/review: read `departments/validation.md`, `departments/review.md`,
  and `core/security.md`.
- External skill request: read `core/skill-marketplace.md` before activation.
- Provider request: read `core/providers.md`; perform a host-native handoff when
  available, otherwise use capability-driven discovery. Never inherit secrets
  into an external employee without explicit authorization.
- Methods decision: run `scripts/method_router.py` and load only the selected
  bounded module; escalate high-risk methods to a qualified checker.
- CUMCM competition: read `competitions/cumcm.md`; use
  `scripts/competition_runtime.py` for clock and scheduling,
  `scripts/competition_method_router.py` for model families, and
  `scripts/competition_quality.py` for solver/unit/numeric/figure/paper/preflight
  gates, `scripts/competition_review.py` for contest review, and
  `scripts/competition_director.py` for continuous execution. Scheduling blocks are an
  overlay and never overwrite canonical scientific status. Use
  `competition_runtime.py execute-next` to pass eligible work through shared
  authorization, executor, evidence, audit, recovery, and graph contracts. A
  zero-match contest route is `UNRESOLVED`, not a guessed method.
  Production competition execution is structure-driven through the modeling,
  coding, analysis, and writing providers. The legacy logistics solver is an
  explicit fixture provider and must not be selected in production.
- Literature: keep discovery, identity verification, and claim-support
  verification separate; snippets and metadata cannot support a load-bearing
  claim. Use `scripts/literature_runtime.py` and the query log.
- Experiment: plan from claim -> threat -> evidence -> experiment with
  `scripts/experiment_planner.py`; preserve discovery/pilot/formal labels and
  use `scripts/job_runtime.py` for recoverable long jobs.
- Behavior/release: use `scripts/eval_runner.py`, `scripts/validate_release.py`,
  and `scripts/build_manifest.py`; model-backed evaluations unavailable on the
  current host remain `NOT_RUN`, never `PASS`.
- Host-specific behavior: read one adapter in `references/hosts/`.

Resolution is not execution: a selected employee remains `RESOLVED` until the
host runs it and a schema-valid handoff reaches `HANDOFF_RECEIVED`/`CHECKED`.
`PROVISIONAL` providers are advisory-only; `SPECIALIST` providers need an
exact pin and a passed relevant behavior trial before formal evidence work.

Do not load every reference by default. Do not copy third-party text or code
without a compatible license. Existing V1 and V2 branches are historical
artifacts; the `v3.1.1` tag remains historical and unchanged. The `v3.2`
branch is the maximum-autonomy release-candidate line.

## Completion

Stop when the requested artifact passes the relevant gates and remaining risk is
explicit. Report completed, running, planned, and author-only actions separately.
Provide paths to the research contract, graph, evidence ledger, manifests,
manuscript, and review matrix when they exist. Never claim Nature/top-venue
acceptance, scientific truth beyond the design, or completion without fresh
verification.
