# Top-level notebook files

## STATUS.md

Keep the front door short. It answers where the project stands now.

```markdown
# Project status

One or two sentences describing the research scope.

## Snapshot

**Phase**: exploration | piloting | paper-ready | published | closed
**Science status**: What is established, provisional, or untested
**What's established**: One headline with an evidence link
**What's open**: [[QUESTIONS]]
**Next**: One line with a link to [[PRIORITIES]]
**Publication**: One gating fact or n/a; details in [[PUBLICATION]]
**Last updated**: YYYY-MM-DD

## Navigation

- Questions: [[QUESTIONS]]
- Priorities: [[PRIORITIES]]
- Experiments: [[experiments/README]]
- Findings: [[findings/README]]
```

Do not place per-experiment tables, venue lists, or task backlogs here.

## QUESTIONS.md

Give each question a stable ID and a status. Keep evidence in experiments and
findings.

```markdown
## RQ1. Short title

**Question**: A falsifiable research question
**Status**: open | in-progress | answered | blocked | retired
**Answer**: One line, present only when answered
**Evidence**: [[EXP-004-example]], [[2026-08-10-synthesis]]
```

## PRIORITIES.md

Keep one current focus, then a small queue grouped by impact. State why each
task matters and what it gates. Remove completed items.

```markdown
# Research priorities

Last updated: YYYY-MM-DD

## Current focus

One paragraph describing the next bounded unit of work.

## Queue

- [ ] **Task**: rationale and gating condition

## Testable predictions

| Source | Prediction | Test |
|---|---|---|
| [[finding]] | Expected observation | Proposed experiment |
```

Do not mirror the runner's live queue.

## GLOSSARY.md

Define project-specific terminology, symbols, acronyms, and nonstandard uses of
general terms. Use `##` headings for categories and one alphabetized `###`
heading per term. Keep definitions short and link to the evidence or method file
when a definition depends on a project decision.

## BIBLIOGRAPHY.md

Maintain an annotated bibliography when the project tracks related work or a
draft has citations. Organize references by thematic `##` sections. Give each
paper a `###` entry with a standard citation, a one- or two-sentence summary,
its relevance to the project, and source/local links.

Downloaded cited papers belong in `references/`; manuscripts authored by the
project belong in `papers/`. PDFs are a replaceable reading cache, while
`BIBLIOGRAPHY.md`, source inventories, manifests, and annotations are notebook
content. Use the `download-research-references` skill to populate the cache.

## CHANGELOG.md

Record research events, newest first, one event per line:

```text
YYYY-MM-DD: Processed job JOB-ID for EXP-012. Runtime ..., artifact ... . The
primary metric was ...; this supports/refutes ... . Recorded in ... and marked
the job processed.
```

Record results, decisions, failure modes, consolidation passes, and publication
milestones. Do not record routine headings, formatting, or status flips.

## Directory indexes

`experiments/README.md` groups experiment links by current status and research
question. `findings/README.md` lists dated findings with one-line claims and
source experiments. Update an index whenever its membership or status changes.
