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

## Candidate audit

Record:

- repository and exact version/commit;
- license and compatibility with intended reuse;
- maintainer and recent activity;
- required tools, credentials, network endpoints, and write scope;
- scripts/hooks/installers that could execute code;
- whether examples contain invented scientific results;
- whether the skill distinguishes advisory checks from verified facts;
- validation/tests and realistic benchmark evidence;
- target agent/harness and known portability limits.

Treat stars and marketing as discovery signals, not evidence of scientific
correctness.

## Curated sources to inspect, not blindly install

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
  evaluated across agent harnesses and realistic multi-step tasks.

## Design lessons for this orchestrator

- Keep the entrypoint short and route detail into references/scripts.
- Prefer deterministic helpers for parsing, hashing, linting, and schema
  validation; reserve scientific judgment for the author and explicit review.
- Keep a claim/evidence ledger and state verification boundaries.
- Make live venue rules and time-sensitive facts re-verifiable.
- Evaluate behavior with realistic tasks and outcome checks, not only syntax.
- Scope inflation is a defect: each phase must be bounded by the user's request
  and a stopping condition.
- Token cost is a property of the skill, model, harness, and task interaction;
  verbosity alone is not quality.

## Attribution

These sources inform architecture and routing. Do not copy their prose, code,
templates, or tests without checking the applicable license and providing the
required attribution. Maintain this project under its own MIT-licensed
implementation.
