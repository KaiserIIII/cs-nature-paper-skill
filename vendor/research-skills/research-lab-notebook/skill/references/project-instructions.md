# Project instruction handoff

Add a short section to the project's agent instructions. Use the filename the
agent actually reads, such as `AGENTS.md`, and keep user-facing setup material in
the project README.

```markdown
## Research notebook

This project keeps its research record in `lab-notebook/`. Load the installed
`research-lab-notebook` skill before editing it. Existing notebook files are
records, not format specifications.

The notebook is [inside the code repository / a separate repository]. Run its
structural validator after edits.

## Research job runner

The tracked runner contract is `lab-notebook/RUNNER.md`. Read it before
submitting, monitoring, retrieving, canceling, or processing a research job.

Mark a job processed only after its outputs have been checked, its evidence has
been written to the notebook, validation passes, and the update is durable.
```

Adapt `RUNNER.md` from the bundled template and replace every placeholder.
Validate referenced command names, configuration keys, and files before saving
the instructions. Keep the full provider mapping there so project instructions
remain a short, stable handoff.

Keep credentials, account IDs, sensitive hosts, unpublished results, and
personal paths out of instructions that will be committed or shared.
