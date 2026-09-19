# Findings

A finding is an immutable, dated synthesis across experiments. Keep analysis
that belongs to one experiment in that experiment's `Results` and `Conclusion`
sections.

Create a finding only when all are true:

- the conclusion depends on two or more experiments or evidence sources;
- no single experiment can own the interpretation cleanly; and
- the synthesis is stable enough to cite from a report or paper.

## Template

```markdown
# Finding: Short claim

**Date**: YYYY-MM-DD
**Status**: supported | provisional | blocked | refuted
**Research questions**: [[RQ1]]
**Experiments**: [[EXP-003]], [[EXP-007]]

## Claim

One sentence at the tested scope.

## Evidence

- Experiment, estimate, uncertainty, and relevant control.
- Experiment, estimate, uncertainty, and relevant control.

## Synthesis

Explain what becomes visible only when the evidence is combined.

## Scope and threats to validity

Name instruments, populations, models, datasets, unresolved confounds, and
missing checks.

## Consequences

- Question status or answer that changes
- Follow-up experiment or publication claim that becomes justified

## Sources

- Artifact and code references
```

Do not silently revise a dated finding when later evidence changes the claim.
Create a new finding that links to and supersedes the earlier one, or add a short
correction pointer if the original statement is factually wrong.

Update `findings/README.md`, the research question, and any affected claim after
adding a finding.
