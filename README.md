# CS Nature Paper V3.1.1

An executable, student-first, evidence-bound research operating system for
computer science.

[中文](README_zh.md) | [Release v3.1.1](https://github.com/KaiserIIII/cs-nature-paper-skill/releases/tag/v3.1.1) | [MIT License](LICENSE)

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

The stable release is `v3.1.1` at commit
`081aa693b907d8cc07104d1b8251d46301094ef7`.

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
| `plan` | Positioning, gap, research questions, protocol, and resources |
| `execute` | Code, data, experiments, analysis, and provenance |
| `write` | Evidence-bound manuscript and LaTeX/document work |
| `revision` | Reviewer concerns, bounded amendments, and resubmission |
| `review` | Adversarial, threat-selected assessment |
| `preflight` | Current venue rules and package-readiness audit |

Autopilot does not remove author control. It stops at contradictory evidence,
missing provenance, budget limits, ethics issues, unqualified capabilities,
protocol amendments, and external actions.

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

## Validation status

The `v3.1.1` release passed 57 unit and integration tests and the required
[GitHub Actions run](https://github.com/KaiserIIII/cs-nature-paper-skill/actions/runs/33107704416)
on Ubuntu and Windows with Python 3.10, 3.11, and 3.12: 6/6 matrix jobs passed.

The validation layers have deliberately different meanings:

1. Schema and deterministic tests check local invariants.
2. Workflow integration checks state, graph, routing, migration, and provenance.
3. Answer-hidden behavior cases define safety and user-facing expectations.
4. A public synthetic smoke workflow checks that the runtime can execute end to end.

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
```

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
