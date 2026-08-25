# CS Nature Paper v2

An evidence-bound research and publication orchestrator for computer science.
It helps an agent move from a research question to a defensible manuscript
without treating more experiments, more agents, or more prose as contributions
by themselves.

[中文说明](README_zh.md) · [v1 branch](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v1) · [MIT License](LICENSE)

## What changed in v2

Version 2 replaces the rigid, token-heavy pipeline in v1 with six scientific
gates organized around **claim, evidence, and mechanism**:

1. Define the stakeholder problem, construct, scope, mechanism, and falsifiers.
2. Map every load-bearing claim to required and observed evidence.
3. Freeze protocols and record amendments without overwriting prior evidence.
4. Add experiments only when they test a named threat or change a conclusion.
5. Write for an editor's first 90 seconds before optimizing specialist detail.
6. Validate citations, results, figures, artifacts, and live venue rules.

The familiar seven departments remain available, but they are activated only
when useful. A focused revision no longer triggers a full autonomous pipeline.

## Operating modes

| Mode | Typical use |
|---|---|
| `full` | Turn research materials into a staged submission package |
| `plan` | Establish positioning, research questions, and protocol |
| `execute` | Implement experiments and freeze reproducible evidence |
| `write` | Draft evidence-bound manuscript sections |
| `revision` | Recover from reviews or rejection without scope inflation |
| `review` | Run evidence-anchored editorial, domain, and method checks |
| `preflight` | Audit current venue rules and the submission package |

## Install

Clone or copy this directory into the skills directory used by your agent. For
Codex, a typical local installation is:

```bash
git clone --branch v2 https://github.com/KaiserIIII/cs-nature-paper-skill.git ~/.codex/skills/cs-nature-paper
```

Review third-party skill code and pin the version you intend to use. v2 does
not silently install dependencies, execute unreviewed hooks, publish artifacts,
or submit manuscripts.

## Quick start

Invoke the skill in plain language:

```text
Use $cs-nature-paper in revision mode. Keep the rejection letter private,
build a concern-to-change matrix, and identify which new experiments would
actually change the paper's claim.
```

For a substantial project, initialize the optional private control plane:

```bash
python scripts/research_state.py init /path/to/project --study-type empirical --mode full
python scripts/research_state.py audit /path/to/project --gate argument
```

This creates `/path/to/project/.research-state/` containing:

- `research_contract.json`: constructs, scope, mechanism, protocol, and venue provenance;
- `evidence_ledger.json`: claim status, evidence anchors, uncertainty, and counterevidence;
- `decision_log.md`: dated scientific decisions and amendments.

Initialization refuses to overwrite an existing state. The directory is
private by default; the author decides whether any sanitized part is released.

## Design boundaries

- A fixed target supports a fixed-target claim, not silent population-wide generalization.
- Dependency resolution or compilation may be a prerequisite for downstream execution, not proof of reproducibility.
- Association is not automatically decay, causation, confounding control, or maintenance cost.
- Repetitions, targets, baselines, and ablations follow the study design rather than universal counts.
- Simulated reviewer roles are assessments, not independent human reviewers or acceptance guarantees.
- Venue rules are verified from current primary sources at submission time; this repository does not freeze page-limit tables.

## Repository map

```text
SKILL.md                         Core routing and scientific gates
references/empirical-study-playbook.md
references/rejection-recovery.md
references/departments.md
references/manuscript-and-review.md
references/skill-sourcing.md
assets/templates/               Private research-state templates
scripts/research_state.py       Deterministic initialization and audits
tests/test_research_state.py    Standard-library behavior tests
docs/examples.md                Safe invocation examples
docs/venues.md                  Live venue-verification protocol
agents/openai.yaml              Codex interface metadata
```

## Influences

The v2 design draws on progressive-disclosure skill architecture, method-specific
empirical standards, claim verification, reproducible research workflows, and
outcome-based agent-skill evaluation. See
[references/skill-sourcing.md](references/skill-sourcing.md) for the curated
source list and adoption rules.

## Development

Run the tests and skill validator before publishing changes:

```bash
python -m unittest discover -s tests -v
python /path/to/skill-creator/scripts/quick_validate.py .
```

## License

[MIT](LICENSE)
