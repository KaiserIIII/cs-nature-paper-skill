# CS Nature Paper V3.1 - Executable Research OS

The student-first, evidence-bound research operating system for computer
science. It turns an idea, codebase, dataset, draft, or rejection into the
strongest research package that the available evidence and resources can defend.

[Chinese](README_zh.md) | [v3.1 branch](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v3.1) | [v3 branch](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v3) | [v2 branch](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v2) | [v1 branch](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v1) | [MIT License](LICENSE)

## What V3.1 adds

V3.1 keeps V3's claim/evidence/mechanism kernel and makes its control loop
executable:

- student-first mentoring and Guided/Copilot/Autopilot modes;
- control and execution planes connected by typed, provenance-bound artifacts;
- an adaptive research graph with feasibility, rollback, reopen, and amendment;
- domain profiles and independent study-type profiles instead of universal quotas;
- a capability-first runtime router and normalized delegation handoffs;
- an immutable graph event log with validated projection, readiness, advance,
  reopen, rollback, supersede, and rebuild commands;
- deep local evidence verification for artifacts, hashes, regions, commits,
  commands, exit status, and checker requirements;
- method, literature, experiment, job, review, ambition, dashboard, and
  answer-hidden behavior-evaluation runtimes;
- canonical V3 templates/schemas under `assets/templates/v3/` and explicit V2
  legacy templates under `assets/legacy/v2/`.

## Scientific boundaries retained

The seven departments remain adaptive capability contracts. V3.1 never invents
citations, results, statistics, novelty, or reviewer agreement; never promotes a
pilot to formal evidence; never silently installs skills; and never publishes or
submits without explicit author authorization.

## Operating modes

| Mode | Typical use |
|---|---|
| `autopilot` | Bounded orientation, field map, candidate RQs, feasibility, and next actions |
| `copilot` | Default execution with material checkpoints |
| `guided` | Explain each gate and request major decisions |
| `plan` / `execute` / `write` / `revision` / `review` / `preflight` | Focused V2-compatible modes |

## Install

```bash
git clone --branch v3 https://github.com/KaiserIIII/cs-nature-paper-skill.git ~/.codex/skills/cs-nature-paper
```

Review third-party skill code and pin the version you intend to use. V3.1 does
not silently install dependencies, execute unreviewed hooks, publish artifacts,
or submit manuscripts.

## Quick start

```text
Use $cs-nature-paper in copilot mode. I have an idea about LLM code repair but
limited CS research experience. Build the beginner brief, map closest work,
run a resource-aware feasibility screen, and execute the next safe step.
```

Initialize the private V3.1 control plane:

```bash
python scripts/research_state.py init /path/to/project --study-type empirical --mode copilot --domain machine-learning
python scripts/research_state.py audit /path/to/project --gate argument
python scripts/research_graph.py validate /path/to/project
python scripts/skill_router.py resolve /path/to/project --capability statistical-modeling
python scripts/evidence_anchor.py validate /path/to/project/anchor.json --deep --root /path/to/project
```

The state includes `research_contract.json`, `research_graph.json`,
`evidence_ledger.json`, literature/experiment/artifact registries, risks,
amendments, venue state, and a qualified employee registry. Initialization
refuses overwrite and is private by default.

To migrate an existing V2 or V3 project without deleting its state:

```bash
python scripts/research_state.py migrate-v2 /path/to/project
python scripts/research_state.py migrate-v3 /path/to/project
```

V2 remains in `.research-state`; V3 is copied to `.research-state-v3`, and V3.1
is copied to `.research-state-v31`. Each migration records provenance and
refuses to overwrite an existing destination.

## Repository map

`SKILL.md` is the compact router. Detailed control-loop, department, domain,
study-type, mentoring, host, security, venue, and marketplace guidance is in
`references/`. Deterministic state and graph helpers are in `scripts/`; unit,
schema, routing, security, and student cases are in `tests/` and `assets/evals/`.
Architecture, V1/V2 audit, landscape audit, and behavior protocol are in
`docs/`.

## Verification levels

V3.1 reports four distinct kinds of evidence:

1. Level 1: schema and deterministic unit tests prove local invariants.
2. Level 2: workflow integration tests prove state, graph, router, and
   provenance interactions.
3. Level 3: behavior cases and the answer-hidden runner exercise safety and
   user-facing decisions; unavailable model runs remain `NOT_RUN`.
4. Level 4: the synthetic/public-safe end-to-end smoke run proves that the
   executable workflow can complete without claiming publication results.

None of these levels proves venue acceptance or scientific truth for a new
study.

## Development

```bash
python -m unittest discover -s tests -v
python scripts/validate_registry.py
python scripts/validate_release.py
python scripts/smoke_run.py --output benchmarks/smoke-run-result.json
```

Before release, run the held-out behavior, routing, security, scientific
pressure, and student cases under `docs/behavior-evaluation.md`. A passing test
set is bounded evidence, not a guarantee of acceptance or scientific truth.

## License

[MIT](LICENSE)
