# Claims and publication tracking

## CLAIMS.md

Add a claim when it could appear in an abstract, contribution list, result
heading, or central figure caption. Do not add every observation.

```markdown
| ID | Role | Claim | Status | Evidence | Paper |
|---|---|---|---|---|---|
| C1 | major | One sentence at the tested scope | provisional | [[EXP-004]]; synthesis: [[finding]] | paper-key |
```

Allowed roles: `major`, `candidate major`, and `supporting`. A paper may have
several major claims when they form one coherent contribution. The `Paper` cell
contains the stable key for the paper that uses the claim. Keep venue,
readiness, deadline, and submission state out of this table.

Allowed statuses: `supported`, `provisional`, `blocked`, `refuted`, `retired`.
Every row must cite at least one experiment record. A finding may also be cited
when its synthesis, correction, or interpretation is needed to recover the
claim, but it cannot replace experiment evidence. A paper section is an evidence
consumer, not an evidence source.

If a claim depends on an analysis that no experiment owns, create an analysis
experiment. Name its input experiments, method or script, artifacts, and result.
Label backfilled expectations as retrospective rather than preregistered.

State the tested population, instrument, model family, or workload in the claim
itself. Put a longer scope boundary or blocker in a detail block when the claim
sentence cannot carry it cleanly.

When evidence changes, update the row and link the new record. Retire a claim
that no longer belongs to the publication argument; do not keep stale claims in
the active set for historical completeness.

Promotion requires human review. Before changing a claim from provisional or
blocked to supported, or broadening its scope, present the direct experiments,
relevant synthesis, unresolved threats, and exact proposed wording. Record the
review decision in the claim update or publication plan. An agent may recommend
promotion but cannot approve it.

## PUBLICATION.md

Create this file when at least one paper is in active preparation. It answers
what blocks submission and where the paper might go.

```markdown
# Publication plan

**Last updated**: YYYY-MM-DD
**Status**: One sentence across active papers

## Paper: Working title

**Paper key**: paper-key
**Draft**: path or link
**Target venue**: name, verified deadline, and source

### Headline result

The named claim IDs followed by concrete evidence links.

### Blocking issues

| Issue | Severity | State | Action |
|---|---|---|---|

### Venues

| Venue | Deadline | Format limit | Fit | Source checked |
|---|---|---|---|---|
```

Verify current venue facts from primary sources before recording them. Include
the source and date checked. Remove resolved blocking items. Version control
already preserves their history.

Keep paper prose in the paper draft, next actions in `PRIORITIES.md`, and result
details in experiments or findings.

Keep each claim's role and paper key in `CLAIMS.md`. `PUBLICATION.md` owns the
paper's manuscript pointer, readiness, gates, venues, deadlines, and submission
state. It may cite claim IDs, but it does not duplicate their role mapping.
