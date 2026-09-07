---
name: novelty-competitive-audit
description: Use before submission to verify the manuscript's contribution is still novel and competitive against recent literature (last 2 years) — 출판 전 경쟁 검토, preemption 체크, novelty 감사. Detects preemption, re-verifies contribution altitude, runs a differentiation test, and issues PASS/CONCERN/BLOCK. Complements research-brainstorming Step 3 (design-time novelty) at submission time.
---

# Novelty Competitive Audit

## Overview

Eureka's internal rigor gates (`claims-audit`, `research-reviewer`, `figure-design`) verify that the manuscript is **internally consistent** — every number traces, every figure is reproducible, every statistical claim is sound. They do NOT verify **external competitiveness** — whether the field already knows this, whether someone preempted the work in the 6-12 months between design approval and submission, or whether the claimed contribution altitude is still defensible against recent literature.

This skill is the external competitiveness gate, fired **before submission**.

**Core premise**: editors' first desk-reject filter is "does this advance the field?" A manuscript with 96/100 PASS on internal rigor will still desk-reject if a preempt paper appeared during manuscript preparation. This skill catches that failure mode before submission.

## The Iron Law

```
NO SUBMISSION WITHOUT EXTERNAL NOVELTY VERIFICATION.
INTERNAL 96/100 PASS ≠ FIELD-LEVEL COMPETITIVENESS.
RIGOR IS NECESSARY. IT IS NOT SUFFICIENT.
```

Internal rigor can be perfect and the paper can still desk-reject on the editor's first read — because the field moved. This skill is not optional.

## When to Use

**Use this skill when:**

- Manuscript draft is complete (all sections passed `section-reviewer`, Abstract written last per `manuscript-writing` rules)
- Before invoking `submission-readiness` — this skill is the 5th prerequisite of that skill's Step 1 gate
- When a new preempt paper is spotted mid-revision — re-run to decide whether to reframe or narrow
- When target venue changes — different venues have different novelty bars (`narrative-guide.md` section "Venue-specific altitude tuning")

**Do NOT use when:**

- At design time — `research-brainstorming` Step 3 literature gap handles pre-data novelty. This skill is the submission-time complement, covering the 6-12 months of field drift since design approval
- Mid-experiment — too early to audit; claims aren't finalized yet
- To substitute for `research-brainstorming` Step 3 — the two are complementary, not interchangeable

## Checklist

You MUST create a task for each of these and complete them in order:

1. **Extract headline claims** — pull 3-5 declarative sentences from Abstract + Results + Discussion that capture what the paper contributes
2. **Define search strategy** — keywords, time window (2 years default), databases appropriate to the field (see `docs/references/novelty-audit-guide.md` section "Search strategy by field")
3. **Perform literature search** — agent or user performs the search. WebSearch tool may be used if available; manual search is equally valid. **Record what was searched** (terms, databases, date, hit count) in a search log (`docs/eureka/novelty-audit/YYYY-MM-DD-search-log.md`)
4. **Record candidate list** — for each promising hit: title, authors, year, venue, one-sentence claim. Target 5-15 candidates; more is a signal the search is too broad, fewer a signal of bias
5. **Evaluate each candidate on the preemption rubric** — 4 dimensions (primary claim / method / data / date) × 3 overlap levels (high / partial / low). See reference guide for rubric details
6. **Differentiation test** — for each high-overlap candidate, write one substantive sentence describing how the current paper differs. Hand-waved differentiation ("ours is different because we focus on X") is disallowed
7. **Altitude recheck** — given what exists in the field now, is the contribution altitude claimed in the manuscript (`narrative-guide.md` section "Contribution altitude — 4 tiers") still defensible?
8. **Issue verdict** — PASS / CONCERN / BLOCK (see gate below) and document the reasoning
9. **Dispatch `novelty-audit-reviewer` subagent** — fresh-eyes review of the audit report, including red-team mode (reviewer actively hunts for 2-3 preempts the author might have missed)
10. **Act on reviewer feedback** — if Must-fix issues raised, re-search or re-evaluate; if Should-fix issues raised, address before final submission; Advisory issues do not block

## HARD-GATE — Verdict decisions

<HARD-GATE>
The verdict is not negotiable. Submission cannot proceed until PASS.
</HARD-GATE>

| Verdict | Condition | Action |
|---|---|---|
| **PASS** | No high-overlap candidates in the time window, OR every high-overlap candidate has a substantive differentiation AND the claimed altitude is defensible | Proceed to `submission-readiness` |
| **CONCERN** | ≥1 high-overlap candidate, differentiation defensible but the altitude needs narrowing, OR preempt requires pre-emptive citation and discussion added to the manuscript | Narrow the claim OR add preempt citations + discussion; re-fire `manuscript-writing` Step 3 (narrative-arc lock); re-run this audit to confirm |
| **BLOCK** | ≥1 high-overlap candidate claiming the same finding with same-tier evidence, differentiation fails | Action menu: (a) narrow to sub-question still novel, (b) change venue to one where the current claim is still original, (c) expand evidence (additional dataset, sensitivity analysis, mechanism), (d) abandon (archive per `submission-readiness` Option 4 — negative evidence is still evidence) |

## Per-Audit Workflow

### Step 1: Extract headline claims

Read the Abstract, final paragraph of the Results section, and the opening paragraph of the Discussion. Extract 3-5 declarative sentences that state what the paper claims as contribution. These should map 1:1 to the contributions enumerated in the Introduction (see `section-reviewer-prompt.md` Intro-Discussion symmetry rule).

### Step 2: Define search strategy

Choose search parameters in advance (not post-hoc — this is the novelty-audit analog of pre-registration).

- **Databases** — per field (see `novelty-audit-guide.md` section "Search strategy by field")
- **Time window** — 2 years default from the manuscript submission date. Justify any adjustment
- **Keywords** — include MeSH / controlled vocabulary + free-text + author names of known competitors
- **Preprints** — include bioRxiv / medRxiv / arXiv / SSRN / OSF per field. **Never exclude preprints silently**

### Step 3: Perform literature search

Agent/user executes search. This skill does not automate search (structured review pattern, not automated scraping — deliberate design choice to ensure domain judgment stays with the user/agent).

Record: what was searched, when, in what database, with what terms, how many hits, and the top 5-15 candidates for evaluation. This log is the object the reviewer subagent audits.

### Step 4: Record candidate list

For each candidate: `(title, authors, year, venue, one-sentence claim)`. Don't filter before recording — the reviewer subagent needs to see what was considered, including the ones you rejected fast.

### Step 5: Preemption rubric evaluation

For each candidate, fill the 4-dimensional rubric:

| Dimension | High | Partial | Low |
|---|---|---|---|
| Primary claim | Same effect/conclusion claimed | Related variable or narrower/broader claim | Different question entirely |
| Method | Same approach (algorithm/study design) | Related but meaningfully different | Orthogonal |
| Data / population | Same dataset/cohort | Similar but different sample | Different |
| Date | Published / preprinted after your registration | Around registration time | Before registration |

Any candidate with 3+ "high" is flagged high-overlap.

### Step 6: Differentiation test

For each high-overlap candidate, write:

> They used [method A] on [dataset D1] and reported [result R1]. We used [method B] on [dataset D2], which resolves [limitation L] and enables [new finding F] not accessible to their approach.

Hand-waved differentiations ("ours is different because we focus on X" without explaining how) are disallowed. See `novelty-audit-guide.md` for bad/good templates.

### Step 7: Altitude recheck

Re-read the manuscript's contribution altitude claim (reflects the decision made at `manuscript-writing` Step 3 narrative-arc lock). Is it still defensible given what now exists in the field?

- If the altitude was **new phenomenon** but a preempt establishes the phenomenon first → altitude drops to **method improvement** at best, or **falsification of a narrower assumption** if your result contradicts theirs
- If altitude was **new framework** but a preempt introduces the framework → altitude drops to **framework validation** or **method improvement under the new framework**
- If altitude was **method improvement** and preempt matches → the work is incremental; the question becomes whether the increment is large enough to justify publication at the target venue

### Step 8: Issue verdict

Use the HARD-GATE table above. Document the reasoning in the audit report.

### Step 9: Dispatch reviewer subagent

Fill `{AUDIT_REPORT_PATH}`, `{MANUSCRIPT_PATH}`, `{RESULTS_DIR}`, `{TARGET_VENUE}`, `{SEARCH_LOG_PATH}` placeholders in `skills/novelty-competitive-audit/novelty-audit-reviewer-prompt.md`. Dispatch via Task tool (`general-purpose` subagent).

The reviewer returns severity-tiered output: **Advisory** (does not block), **Should-fix** (address before submission), **Must-fix** (blocks verdict). In red-team mode the reviewer independently hunts for 2-3 preempts the author may have missed.

### Step 10: Act on feedback

- **Must-fix** → re-search, re-evaluate, or re-verdict. Re-run reviewer until no Must-fix remains
- **Should-fix** → address before submission; document resolution
- **Advisory** → improvement suggestions; not blocking

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "Ours is different because we focus on X" | Not a differentiation — a restatement of scope. State how the approach, data, or findings are substantively different |
| "The preempt is only a preprint, doesn't count" | Preprints count for novelty assessment. Editors and reviewers read them. Excluding preprints silently is biased search |
| "They used a smaller sample / different species / different cohort" | Sample-size-only differentiation is weak. State what the difference **enables** scientifically, not just that it exists |
| "The field is too fast-moving to keep up" | This is exactly when a novelty audit matters most. Fast-moving fields have the highest preempt rate |
| "We ran the experiment before they published" | Publication priority matters for the record, not for editorial novelty. If they published first, the editor reads their work as the field's baseline |
| "Our contribution is the combination of X, Y, Z" | Combination novelty is valid but needs a specific case. State why the combination enables a finding none of X, Y, Z alone could reach |
| "We have more citations" | Citation count is not a novelty argument. Cite specifically: what does your contribution add that existing citations don't? |
| "Our internal scores are all 95+" | Internal scores don't check external preemption. That's exactly why this skill exists |

## Red Flags — STOP

- Search with biased terms (only terms that favor your framing)
- Excluding preprints silently
- Differentiation that collapses to "our N is bigger"
- No search log recorded
- Cherry-picked candidates (only those that support your novelty claim)
- "I know the field; I don't need a search"
- Verdict BLOCK rationalized to CONCERN without changing the manuscript
- Claiming PASS without actually performing a structured search

## Orthogonality with existing skills

| Concern | Owned by |
|---|---|
| Pre-data literature gap, design-time | `research-brainstorming` Step 3 |
| Internal number traceability | `claims-audit` |
| Internal 7-dimension rigor scoring | `research-reviewer` agent |
| Figure integrity (script-generated) | `claims-audit` + `figure-design` |
| Figure design and reporting | `figure-design` + multi-gate |
| Narrative framing / contribution altitude | `manuscript-writing` Step 3 + `narrative-guide.md` |
| **External novelty at submission time** | **this skill** |
| Pre-submission fresh verification | `verification-before-publication` |
| 4-option submission decision | `submission-readiness` |

Each owns a distinct concern. No overlap. A manuscript must pass all that apply.

## Integration

- **Called by:** `eureka:using-eureka` when pre-submission intent detected; or explicit user request
- **Prerequisite:** manuscript first draft complete (Results + Discussion + Abstract written), passing `section-reviewer` for all sections
- **Invokes:** `novelty-audit-reviewer` subagent (per audit, after the inline verdict)
- **Blocks:** `submission-readiness` Step 1 prerequisites — this is the 5th gate alongside `verification-before-publication`, `research-reviewer` ≥95/100, `claims-audit`, venue-framing check
- **Complements:** `research-brainstorming` Step 3 (same concern, earlier phase)
- **Triggers re-fire of:** `manuscript-writing` Step 3 narrative-arc lock, if verdict is CONCERN or BLOCK and the manuscript's altitude needs adjustment
- **Reference:** `docs/references/novelty-audit-guide.md` — search strategies, preemption rubric, differentiation templates, verdict decision tree, worked examples, anti-patterns
- **Pairs with:** `research-journal` (log the audit verdict and action decisions for cross-session continuity)

## Skill Type

**RIGID** — The discipline (must run pre-submission, verdict is non-negotiable, structured rubric, reviewer subagent dispatch) does not flex. Search strategy and candidate evaluation are **FLEXIBLE by field** — a medical paper's databases differ from a CS paper's databases; see `novelty-audit-guide.md` for field-specific guidance.
