# CS Nature Paper V3.2.0

An executable, student-first, evidence-bound research operating system for
computer science.

[中文](README_zh.md) | [Historical release v3.1.1](https://github.com/KaiserIIII/cs-nature-paper-skill/releases/tag/v3.1.1) | [MIT License](LICENSE)

## What this project is

CS Nature Paper is an Agent Skill that helps turn a research idea, codebase,
dataset, draft, review, or rejection into the strongest research package that
the available evidence and resources can defend. It acts as a research director:
it explains unfamiliar decisions, organizes the work, executes safe and
reversible tasks, and stops for the author when a choice is scientific,
expensive, ethical, scope-changing, public, or irreversible.

The project is not a paper generator, model, SaaS product, acceptance predictor,
or automatic publisher. Its job is to keep research questions, protocols,
experiments, claims, evidence, figures, writing, and review connected by explicit
records instead of allowing polished prose to outrun the evidence.

The `v3.1.1` tag remains the historical stable release at commit
`081aa693b907d8cc07104d1b8251d46301094ef7`. This branch adds the
`v3.2` maximum-autonomy release candidate from baseline
`6b34dcba551bdf200c2d7dd49bcb6b6057ef67c4`.

## How it works

```text
Idea, code, data, draft, review, or rejection
                       |
                       v
              SKILL.md diagnosis and routing
                       |
          +------------+------------+
          |                         |
          v                         v
 Research control plane      Research execution plane
 RQs, claims, protocol,      Search, read, code, run,
 evidence, risks, budget,    analyze, plot, write,
 permissions, graph state    compile, validate, review
          |                         |
          +------------+------------+
                       |
                       v
        Typed artifacts with provenance anchors
                       |
                       v
          PASS / CONDITIONAL / FAIL
                       |
                       v
        Continue, narrow, amend, reopen, or stop
```

The **control plane** owns scientific meaning: the research question, scope,
claims, evidence relationships, frozen protocol, amendments, risks, permissions,
and completion state. The **execution plane** performs bounded work. An output
does not become formal evidence merely because a command ran; it must return as
a typed artifact with its inputs, command, environment, hashes, uncertainty,
scope, code version, and verification status.

Workflow state lives in an adaptive `research_graph.json`, not a fixed phase
number. Nodes can run in parallel, fail, reopen, roll back, or be superseded.
Transitions are also written to an append-only, hash-linked event log so the
graph can be rebuilt and tampering can be detected.

## Repository map

```text
SKILL.md                  Natural-language router, policies, and entrypoint
agents/openai.yaml        Codex/OpenAI metadata for $cs-nature-paper

references/
  core/                   Control loop, graph, evidence, security, marketplace
  departments/            Seven department contracts and handoffs
  domains/                13 CS domain profiles
  study-types/            Empirical, benchmark, theory, causal, and other designs
  methods/                Statistics, experiment decisions, source relationships
  mentoring/              Student-first explanation contract
  reviewing/              Threat-driven review and bounded revision
  hosts/                  Codex and Claude Code adapters

assets/
  templates/v3/           Private state templates for new projects
  schemas/                Machine-readable JSON contracts
  registry/               Capability, method, domain, study, and skill catalogs
  evals/                  Behavior, routing, and security pressure cases
  legacy/v2/              Preserved migration inputs, not new-project templates

scripts/                  Deterministic Python CLI and runtime helpers
tests/                    Unit, integration, security, and regression tests
benchmarks/               Committed runtime benchmark records
docs/                     Architecture, audits, examples, and release reports
.github/                   Ubuntu/Windows continuous integration
```

`SKILL.md` stays compact by loading references only when a mode, domain, study
type, method, threat, or host requires them. The runtime helpers use the Python
standard library only.

## Seven research departments

The departments are capability contracts activated by the research graph, not
a mandatory serial pipeline.

| Department | Responsibility | Critical boundary |
|---|---|---|
| Literature | Discovery, source identity, retrieval, and exact-region claim support | A snippet or metadata record cannot support a load-bearing claim |
| Innovation | Gap, mechanism, closest work, alternatives, falsifiers, and contribution scope | Novelty is tested, never asserted from absence of a quick search |
| Implementation and Experiment | Protocol-to-code, pilots, formal runs, statistics, and recoverable jobs | Pilot and exploratory results cannot silently become formal evidence |
| Figures | Source-data-bound rendering, uncertainty, accessibility, and export audit | A figure cannot introduce a stronger result than its source data |
| Writing | Evidence-traceable, venue-aware drafting and claim traces | Prose cannot strengthen unsupported scope or certainty |
| Validation | Independent, fail-closed science, data, code, and document checks | Fabrication, confidentiality, and authorization failures cannot be averaged away |
| Review | Threat-selected review, severity, smallest repair, and residual risk | Reviewer counts are not consensus or acceptance prediction |

For load-bearing work, producer and checker roles are separated. External skills
are treated as employees: formal evidence work requires an exact pinned source,
least privilege, a relevant behavior trial, and a rollback path.

## Research state and evidence

Initializing a project creates a private `.research-state/` directory. It does
not edit `.gitignore` and refuses to overwrite existing state.

```text
project.json              Identity, mode, domain, budget, permissions
research_contract.json    Argument, constructs, scope, protocol, venue
research_graph.json       Nodes, edges, current state, event history
claims.json               Normalized claims, scope, and falsifiers
evidence_ledger.json      Evidence relations, uncertainty, alternatives
literature_registry.json  Source identity, retrieval, claim support
experiment_registry.json Discovery, pilot, formal, and amended runs
artifact_manifest.json    Files, hashes, commands, environment, public boundary
decision_log.md           Human-readable material decisions
amendments.json           Append-only protocol and analysis changes
risks.json                Risks, triggers, owners, mitigation, residual risk
employee_registry.json    Qualified capabilities and permissions
venue_profile.json        Current requirements backed by primary sources
```

Migration preserves the originals: V2 state is copied from `.research-state`
to `.research-state-v3`, and V3 state is copied to `.research-state-v31`.
Readers prefer `.research-state-v31`, then `.research-state-v3`, then
`.research-state`.

Evidence provenance has three levels:

| Level | Meaning |
|---|---|
| `DECLARED` | Someone asserted the record, but the runtime did not observe it |
| `OBSERVED` | A real command or acquisition ran with timestamps, exit status, outputs, and hashes |
| `VERIFIED` | An independent checker rechecked the produced output and its inputs, configuration, and code version |

Legacy records that say `status=VERIFIED` without provenance migrate to
`DECLARED`; they cannot support a formal pass. Literature uses the same
fail-closed principle: discovery, source identity, materialized retrieval, and
exact-region claim support are separate operations.

## Install

Install the reviewed stable tag into a new directory, then verify its commit.

PowerShell:

```powershell
$SkillRoot = "$env:USERPROFILE\.codex\skills\cs-nature-paper"
git clone --branch v3.1.1 --depth 1 https://github.com/KaiserIIII/cs-nature-paper-skill.git $SkillRoot
git -C $SkillRoot rev-parse HEAD
```

Bash:

```bash
git clone --branch v3.1.1 --depth 1 \
  https://github.com/KaiserIIII/cs-nature-paper-skill.git \
  ~/.codex/skills/cs-nature-paper
git -C ~/.codex/skills/cs-nature-paper rev-parse HEAD
```

The expected output is:

```text
081aa693b907d8cc07104d1b8251d46301094ef7
```

Do not overwrite an existing installation with local changes. Review external
skill code and keep every formal dependency pinned to an audited commit.

## Use it in natural language

The normal interface is a research request, not a CLI questionnaire. For
example:

```text
Use $cs-nature-paper in copilot mode.

I want to study LLM-based repair of Python projects. I have limited research
experience and a personal-computer budget with limited API spend. First build
the field map, verify the closest literature, propose bounded research
questions, and run the feasibility gate. Stop for my approval before formal
experiments, scope changes, paid resources, uploads, releases, or submission.
```

You can also start from existing material:

```text
Use $cs-nature-paper in review mode on this draft and its experiment artifacts.
Trace every load-bearing claim to evidence, select reviewers from the actual
threats, and report the smallest defensible repairs. Do not predict acceptance.
```

## Operating modes

| Mode | Use |
|---|---|
| `copilot` | Default: execute routine work and stop at material checkpoints |
| `guided` | Explain each major gate before asking for a decision |
| `autopilot` | Continue within an explicit budget and permission envelope |
| `maximum-autonomy` | Continue bounded local work with standing authorization, resumable sessions, and fail-closed completion checks |
| `plan` | Positioning, gap, research questions, protocol, and resources |
| `execute` | Code, data, experiments, analysis, and provenance |
| `write` | Evidence-bound manuscript and LaTeX/document work |
| `revision` | Reviewer concerns, bounded amendments, and resubmission |
| `review` | Adversarial, threat-selected assessment |
| `preflight` | Current venue rules and package-readiness audit |
| `competition` | Execute an already selected CUMCM problem through preflight |
| `competition-autopilot` | Auto-select and run the full competition lifecycle |
| `competition-review` | Red-team a contest paper and submission package |

Autopilot does not remove author control. It stops at contradictory evidence,
missing provenance, budget limits, ethics issues, unqualified capabilities,
protocol amendments, and external actions.

Maximum autonomy uses `scripts/autonomy.py` as the single policy and
authorization boundary. Ordinary reversible research work is automatic;
network research, bounded protocol amendments, and medium-risk hires run with
hash-chained audit records. Only fundamental scientific scope changes, ethics,
credentials, payment, privileged/global installation, private-data transfer,
irreversible external actions, publication, and submission require the author.
`scripts/director_loop.py` dispatches real executors and transitions graph nodes
only after artifacts and evidence pass their contracts. Project completion is
`READY_FOR_SUBMISSION`; software release readiness is validated separately.

## Provider-driven execution

V3.2.0 separates four validation layers that must not be conflated:

- **Deterministic runtime:** graph, authorization, commands, artifact hashes,
  checkers, evidence, provenance, freshness, and dependency invalidation.
- **Host Provider:** the current Codex/Claude-style host may search, read, code,
  execute, write, or review through a neutral typed request/handoff contract.
  A request enters `HOST_EXECUTION_REQUIRED`; a separate invocation/checker must
  receive and accept a real artifact before graph PASS. Python does not generate
  a substitute host answer.
- **External Skill Provider:** a capability vacancy can trigger catalog,
  installed-Skill, marketplace, and GitHub discovery. Candidates are statically
  audited, pinned to an exact 40-character commit, isolated, qualified, run
  without inherited secrets, checked, and only then accepted.
- **Model Behavior:** host/model quality is a separate evaluation. It remains
  `NOT_RUN` when no genuinely isolated host-backed adapter was executed.

Host availability uses `HOST_AVAILABLE`, `HOST_REQUEST_CAPABLE`, and
`HOST_BEHAVIOR_QUALIFIED`. Recorded CI handoffs validate the lifecycle, not a
live model. GitHub discovery results likewise remain `MISMATCH`, `PARTIAL`, or
`UNVERIFIED` unless repository content, a semantic audit, and a checked behavior
trial establish `CONFIRMED`; formal AUTO_HIRE accepts only `CONFIRMED`.

`scripts/research_executor.py` and `scripts/competition_executor.py` are now
Provider adapters. `constant_mean`/`linear_trend` and the bounded competition
method families remain transparent native baselines. Native-unsupported work
routes to problem-specific host modeling/coding, followed by deterministic
execution and checking. This architecture supports host/tool/Skill execution;
general model-backed autonomous behavior remains `NOT_RUN` until separately
evaluated. Legacy research and logistics examples live only in explicit fixture
providers.

Literature retrieval distinguishes `METADATA_ONLY`, `FULLTEXT_RETRIEVED`,
`EXACT_REGION_VERIFIED`, and `UNAVAILABLE`. Metadata is useful for discovery and
identity, but a load-bearing novelty, closest-work, method, or factual claim
requires full text and an independently verified exact region.

## CUMCM competition overlay

Competition mode is a policy overlay on the same Research Graph, evidence
ledger, claims, experiments, artifacts, provenance, and handoffs used by the
general Research OS. It does not create a second scientific state system.
The runtime may rank, temporarily block, freeze, or release generic graph
nodes according to the clock, scientific and scoring risk, decision relevance,
information gain, ETA, and paper/validation/complexity debt. Temporary policy
blocks remain overlay state and never pollute the canonical scientific graph.

The only authoritative time boundaries are timezone-aware ISO-8601
`contest_start_utc` and `submission_deadline_utc`. The runtime converts them
to UTC and computes the actual duration, elapsed time, remaining time, phase,
STOP RULE, and HARD FREEZE from the system clock. A configured clock remains
`UNVERIFIED` until a person explicitly records the current official source.
While it is unverified, the runtime does not authorize deadline-based jobs or
claim that official rules are confirmed. Manual offset, pause, and resume
operations require an actor and reason and are appended to a SHA-256 chained
event log; `competition_clock.json` is only the latest derived snapshot.

Typical requests are:

```text
Use $cs-nature-paper in competition mode.
Execute this selected CUMCM problem through baseline, formal solve, validation,
sensitivity, figures, paper, review, repair, and submission preflight. Continue
while author action is NONE.
```

```text
Use $cs-nature-paper in competition-autopilot mode.
Read the supplied contest problems and current competition state. Verify the
official rules and clock source, decompose and compare every problem, and
auto-select a clear winner. Run the full Director lifecycle and stop only at
COMPETITION_SUBMISSION_READY or a genuine author-only boundary.
```

```text
Use $cs-nature-paper in competition-review mode.
Audit this contest paper and submission package. Return severity-ordered,
evidence-anchored findings and the ten-axis score radar. Do not predict an
award or invent current official rules.
```

The default CUMCM profile uses the approved 72-hour phase boundaries. Other
durations are mapped proportionally unless the profile supplies explicit
boundaries. `SUBMISSION_FREEZE` is a planned phase; the absolute six-hour
`FINALIZATION_MODE` and two-hour `HARD_FREEZE` override normal scheduling.
Every new executable job must satisfy the runtime ETA plus the stage-specific
safety margin before it can start.

## Minimal CLI workflow

The CLI exposes the deterministic control plane. In PowerShell:

```powershell
$SkillRoot = "$env:USERPROFILE\.codex\skills\cs-nature-paper"
$Project = "D:\research\llm-repair"

python "$SkillRoot\scripts\research_state.py" init $Project `
  --study-type ml-benchmark --mode copilot --domain llm

python "$SkillRoot\scripts\research_state.py" audit $Project --gate argument
python "$SkillRoot\scripts\research_graph.py" validate $Project
python "$SkillRoot\scripts\research_graph.py" status $Project
python "$SkillRoot\scripts\research_graph.py" plan-next $Project
python "$SkillRoot\scripts\research_graph.py" ready $Project
python "$SkillRoot\scripts\research_graph.py" advance $Project
python "$SkillRoot\scripts\evidence_anchor.py" ledger $Project --deep
```

Initialize and operate the competition overlay:

```powershell
python "$SkillRoot\scripts\research_state.py" init $Project `
  --study-type algorithmic --mode competition-autopilot `
  --domain mathematical-modeling

python "$SkillRoot\scripts\competition_runtime.py" configure-clock $Project `
  --start "2026-09-10T10:00:00Z" `
  --deadline "2026-09-13T10:00:00Z" `
  --official-source "https://official.example/rules" --actor "team-captain"

python "$SkillRoot\scripts\competition_runtime.py" verify-clock $Project `
  --official-source "https://official.example/rules" --actor "team-captain"

python "$SkillRoot\scripts\competition_runtime.py" dashboard $Project
python "$SkillRoot\scripts\competition_runtime.py" status $Project
python "$SkillRoot\scripts\competition_runtime.py" schedule $Project
python "$SkillRoot\scripts\competition_method_router.py" route `
  "Minimize facility cost subject to capacity constraints"
python "$SkillRoot\scripts\competition_review.py" audit competition-review.json
python "$SkillRoot\scripts\competition_director.py" $Project `
  --input competition_input.json
```

`configure-clock` records candidate boundaries but does not verify their
authority. Re-check the real event's official source before `verify-clock`.
For a documented clock correction, use `adjust-clock --offset-seconds ...
--reason ... --actor ...`; never edit the snapshot or event log by hand.

Resolve a capability or methods playbook without confusing selection with
execution:

```powershell
python "$SkillRoot\scripts\skill_router.py" resolve `
  --project $Project --capability statistical-modeling

python "$SkillRoot\scripts\method_router.py" route `
  "Compare repair rates across repositories and random seeds" --project $Project
```

Specialized runtimes are available for literature verification,
claim-driven experiment planning, resumable jobs, evidence execution and
validation, reviews, handoffs, dashboards, privacy checks, security pressure
cases, behavior cases, and release validation. Run any script with `--help` to
inspect its exact contract.

When a Director pauses for host work, inspect and receive the real handoff, then
resume the same session:

```powershell
python "$SkillRoot\scripts\host_provider_runtime.py" pending $Project
python "$SkillRoot\scripts\host_provider_runtime.py" receive $Project host-handoff.json `
  --checker deterministic-output-checker
python "$SkillRoot\scripts\director_loop.py" resume $Project
```

The current host should normally perform this loop automatically. See
[the Host Provider contract](references/core/host-provider.md).

## Validation status

The `v3.1.1` release passed 57 unit and integration tests and the required
[GitHub Actions run](https://github.com/KaiserIIII/cs-nature-paper-skill/actions/runs/33107704416)
on Ubuntu and Windows with Python 3.10, 3.11, and 3.12: 6/6 matrix jobs passed.

The validation layers have deliberately different meanings:

1. Schema and deterministic tests check local invariants.
2. Workflow integration checks state, graph, routing, migration, and provenance.
3. Answer-hidden behavior cases define safety and user-facing expectations.
4. A public synthetic smoke workflow checks infrastructure integration.
5. The competition orchestration E2E advances all 16 nodes through the normal
   Director and actually executes code, validation, figures, paper, review,
   repair, and preflight; ten corruption/policy cases must fail closed.

The synthetic workflow is classified as `HARNESS_SELF_TEST`; it is not
scientific evidence and not an evaluation of a research model. Model-backed
behavior evaluation remains `NOT_RUN`. A harness self-test must never be
reported as a real model evaluation.

For development verification:

```bash
python -m unittest discover -s tests -v
python scripts/validate_registry.py
python scripts/validate_release.py
python scripts/smoke_run.py --output .ci-smoke-result.json
python scripts/check_smoke.py .ci-smoke-result.json
python scripts/competition_smoke_run.py --output .competition-smoke-result.json
python scripts/competition_orchestration_e2e.py
python scripts/generic_research_orchestration_e2e.py
python scripts/generic_competition_orchestration_e2e.py
python scripts/host_provider_handoff_e2e.py
python scripts/generic_host_research_e2e.py
python scripts/generic_host_competition_e2e.py
```

The competition smoke uses a finite synthetic facility-selection fixture and
standard-library enumeration. It tests runtime integration only. Its class is
`HARNESS_SELF_TEST`, and model-backed behavior evaluation remains `NOT_RUN`.
The orchestration E2E is a deterministic runtime orchestration test, not a
model-behavior evaluation; `MODEL_BEHAVIOR_EVAL` remains `NOT_RUN` unless an
authorized model adapter is supplied.

The generic research E2E uses a small CSV, compares two transparent candidate
methods, executes generated project code, analyzes the observed output, writes
from the evidence state, reviews, repairs, and reaches `READY_FOR_SUBMISSION`.
The generic competition E2E runs the same production providers on three
different structures. These deterministic tests demonstrate routing and
artifact contracts, not universal scientific validity or host-model quality.
The recorded Host E2Es add native-unsupported classification and graph-network
tasks, exercise real request/receive/check/resume transitions, and execute the
returned code. Their model behavior label is `RECORDED_HANDOFF`; the separate
model behavior evaluation remains `NOT_RUN`.

## What this project does not claim

- It does not promise Nature, top-conference, or any venue acceptance.
- It does not manufacture novelty, citations, data, statistics, or consensus.
- It does not turn a pilot, snippet, compilation, or passing unit test into
  stronger scientific evidence than it is.
- It does not silently install skills, use credentials, spend money, expose
  private material, upload artifacts, publish, or submit.
- It does not replace an advisor, domain expert, ethics board, artifact
  evaluator, reviewer, or current primary venue rules.
- Paywalled sources, live venue requirements, external skills, APIs, and model
  services still require activation-time access and verification.

The goal is not the largest claim. It is the strongest claim that the recorded
evidence, design, and resources can honestly defend.

## Documentation

- [V3 architecture](docs/V3_ARCHITECTURE.md)
- [V3.1 synthetic end-to-end example](docs/v3.1-end-to-end-example.md)
- [V3.1.1 release report](docs/v3.1.1-release-report.md)
- [Behavior evaluation protocol](docs/behavior-evaluation.md)
- [V1/V2/V3 replacement and migration audit](docs/v3-v1-v2-design-audit.md)
- Historical branches: [v3.1.1-hardening](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v3.1.1-hardening), [v3.1](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v3.1), [v3](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v3), [v2](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v2), [v1](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v1)

## License

[MIT](LICENSE)
