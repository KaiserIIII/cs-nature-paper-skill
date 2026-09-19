# Notebook discipline

## One owner for each fact

Every fact has one authoritative home. Other files point to it.

| Information | Owner |
|---|---|
| Current project orientation | `STATUS.md` |
| Open research questions | `QUESTIONS.md` |
| Next actions and predictions to test | `PRIORITIES.md` |
| One experiment's design, runs, and interpretation | its experiment file |
| A synthesis that needs several experiments | `findings/` |
| Research events and decisions over time | `CHANGELOG.md` |
| A bounded objective and its exit conditions | `plans/` |
| Claim roles, paper keys, and publication evidence | `CLAIMS.md` |
| Paper readiness and venue strategy | `PUBLICATION.md` |

Use this placement test:

> If this paragraph disappeared, which question would become unanswerable?

Move the paragraph to the file that owns that question. Split a paragraph that
answers two questions, then link the two records.

## Report by pointer

`STATUS.md` gives a short synthesis with links. It does not duplicate result
tables, paper trackers, or work queues. `QUESTIONS.md` carries a status and a
one-line answer for a resolved question, followed by a link to the evidence.
`PRIORITIES.md` names work and rationale, not result summaries.

## Preserve time direction

- Preserve a priori predictions and decision rules after results arrive.
- Keep raw outputs immutable.
- Put corrections beside a conclusion or supersede it with a linked record.
- Use version control for edit history. Use `CHANGELOG.md` for research history.
- Keep completed work out of active roadmaps and queues.

## Prefer durable evidence

A job log may expire. A chat transcript may be unavailable to the next agent.
A metric tracker may omit the reason a condition existed. Transfer the durable
parts into the experiment record: provenance, observed values, interpretation,
decision, and follow-up.

## Avoid shadow state

Do not maintain a second table of running jobs if the backend already provides
one. Do not create `SESSION.md` for facts available from the runner, version
control, experiment files, or `STATUS.md`. Shadow state goes stale because no
single system knows which copy is authoritative.
