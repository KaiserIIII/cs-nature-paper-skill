# Research-skill sourcing and supply-chain policy

Use this reference only when a missing capability may justify another skill or
plugin.

## Selection order

1. use an already available, task-specific skill;
2. use primary documentation and ordinary tools when no skill is needed;
3. inspect a candidate skill before suggesting installation;
4. install only with user authorization and an available trusted installer;
5. pin a release or commit for reproducible research environments.

Do not install an entire large collection to obtain one small capability.
Apply the employment states, behavioral trials, and revalidation rules in
[employee-quality-and-routing.md](employee-quality-and-routing.md). An installed
skill is not automatically an active employee.

## Candidate audit

Record:

- repository and exact version/commit;
- license and compatibility with intended reuse;
- maintainer and recent activity;
- required tools, credentials, network endpoints, and write scope;
- scripts/hooks/installers that could execute code;
- whether examples contain invented scientific results;
- whether the skill distinguishes advisory checks from verified facts;
- validation/tests, failure-path tests, and realistic benchmark evidence;
- target agent/harness and known portability limits.

Treat stars and marketing as discovery signals, not evidence of scientific
correctness.

## Curated sources to inspect, not blindly install

- [`google-deepmind/science-skills`](https://github.com/google-deepmind/science-skills): official scientific skills with
  deterministic helpers and layered internal/external evaluation. Useful
  literature and tool-specific candidates still require exact-skill license,
  environment, terms, API-key, and local harness checks.
- [`K-Dense-AI/scientific-agent-skills`](https://github.com/K-Dense-AI/scientific-agent-skills): broad scientific lookup, statistics,
  visualization, writing, and review capabilities. Prefer topical installs,
  version pinning, and the repository's security guidance.
- [`Imbad0202/academic-research-skills`](https://github.com/Imbad0202/academic-research-skills): evidence-bound research/writing/review
  pipeline with human checkpoints, integrity boundaries, versioned releases,
  and experiment provenance intake.
- [`Ar9av/PaperOrchestra`](https://github.com/Ar9av/PaperOrchestra): structured transformation from raw research materials
  to LaTeX, with literature/figure stages and benchmark-based evaluation.
- [`SNL-UCSB/paper-writing-skill`](https://github.com/SNL-UCSB/paper-writing-skill): concise research-paper editorial guidance and
  figure/writing patterns.
- `K-Dense-AI` task skills such as `paper-lookup`, `literature-review`,
  `statistical-analysis`, `scientific-visualization`, `scientific-writing`, and
  `scholar-evaluation` when those exact tasks are needed.
- [`ShaishavMaisuria/research-paper-lifecycle-skills`](https://github.com/ShaishavMaisuria/research-paper-lifecycle-skills): narrow live-venue,
  claim-audit, preflight, review-triage, and artifact helpers. Inspect and use
  only the relevant skill.
- [`KuangshiAi/SciVisAgentSkills`](https://github.com/KuangshiAi/SciVisAgentSkills): an example of versioned procedural knowledge
  evaluated across agent harnesses and realistic multi-step tasks. Treat its
  ParaView/napari/VMD/TTK skills as domain-imaging specialists, not general
  chart employees.
- [`obra/superpowers`](https://github.com/obra/superpowers): useful systematic-debugging and fresh-verification
  disciplines. Adopt task-scoped practices; do not inherit its global workflow
  assumptions or force strict TDD on exploratory evidence generation.
- [`trailofbits/skills`](https://github.com/trailofbits/skills): strong security, property-based testing, supply-chain,
  and modern-Python specialists. Avoid project-wide toolchain migration unless
  it is explicitly in scope.
- [`huggingface/skills`](https://github.com/huggingface/skills): official ML evaluation, dataset, and tracking workflows for
  matching Hugging Face tasks. Audit tokens, network calls, uploads, remote
  writes, and public/private defaults before activation.
- [`github/awesome-copilot`](https://github.com/github/awesome-copilot): selected evidence-map and engineering patterns. Verify
  exact harness and script availability locally.
- [`anthropics/skills`](https://github.com/anthropics/skills): official document/PDF/slides/spreadsheet artifact skills. They can
  produce or inspect documents but cannot certify scientific claims.

The dated public-safe review is in
[`docs/employee-skill-audit-2026-08-26.md`](../docs/employee-skill-audit-2026-08-26.md).
High install counts with unresolved security warnings remain quarantined; for
example, inspected RigorPilot candidates were not promoted during this audit.

## Design lessons for this orchestrator

- Keep the entrypoint short and route detail into references/scripts.
- Prefer deterministic helpers for parsing, hashing, linting, and schema
  validation; reserve scientific judgment for the author and explicit review.
- Define a capability vacancy before selecting a repository and staff an
  independent checker for load-bearing outputs.
- Keep a claim/evidence ledger and state verification boundaries.
- Make live venue rules and time-sensitive facts re-verifiable.
- Evaluate behavior with realistic tasks and outcome checks, not only syntax.
- Combine static, unit/capability, department workflow, cross-department,
  external, and pressure tests; record environment and side-effect cost.
- Scope inflation is a defect: each phase must be bounded by the user's request
  and a stopping condition.
- Token cost is a property of the skill, model, harness, and task interaction;
  verbosity alone is not quality.

## Attribution

These sources inform architecture and routing. Do not copy their prose, code,
templates, or tests without checking the applicable license and providing the
required attribution. Maintain this project under its own MIT-licensed
implementation.
