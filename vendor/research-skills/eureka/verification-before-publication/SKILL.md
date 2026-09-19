---
name: verification-before-publication
description: Use before claiming results are publication-ready, before submitting manuscripts, or before sharing findings externally — requires fresh verification evidence for every claim
---

# Verification Before Publication

## Overview

Claiming results are publication-ready without verification is not confidence — it is a liability to your co-authors, your field, and your career.

**Core principle:** Evidence before submission, always.

**Violating the letter of this rule is violating the spirit of this rule.**

## The Iron Law

```
NO SUBMISSION CLAIM WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't re-run the verification in this session, you cannot claim it is ready for submission.

## The Gate Function

```
BEFORE claiming publication-ready:

1. IDENTIFY: What evidence proves each claim?
2. RUN: Re-run key analyses fresh (not cached results)
3. READ: Full output, check every number
4. VERIFY: Does output match manuscript claims?
   - If NO: State actual values with evidence
   - If YES: State verification WITH evidence
5. ONLY THEN: Claim ready for submission

Skip any step = asserting, not verifying
```

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Results are accurate | claims-audit PASS | "I checked last week" |
| Figures are correct | Re-generated figures match manuscript | "They look right" |
| Analysis is reproducible | Single command reproduces all results | "It worked on my machine" |
| Statistics are proper | hypothesis-first INTERPRET standards met (effect size + CI + correction) | "p-values are significant" |
| All results reported | Experiment log cross-referenced with manuscript | "Main results are in" |

## Red Flags — STOP

- Using "should be", "probably fine", "I'm confident"
- Expressing readiness before verification ("It's ready", "We're good to go", "Just needs a polish")
- About to submit or share without re-running analyses
- Relying on results from a previous session
- Trusting cached outputs without checking they match current code
- Thinking "just this once — deadline is today"
- Under pressure from collaborators or journal deadlines
- **ANY wording implying submission-readiness without having run fresh verification**

## Rationalization Prevention

| Excuse | Reality |
|--------|---------|
| "Should be ready now" | RUN the verification |
| "I'm confident in the numbers" | Confidence is not evidence |
| "Checked last week" | Last week's check is not this week's evidence |
| "Just minor revisions since last check" | Minor changes can invalidate figures and tables |
| "Deadline pressure" | A retraction is worse than a delayed submission |
| "The reviewer will catch errors" | Peer review is not your QC pipeline |
| "I know this codebase" | Knowing the codebase does not prevent stale outputs |
| "Different wording so rule doesn't apply" | Spirit over letter |
| "Co-authors approved it" | Co-authors approved what they saw, not what is current |
| "The analysis passed review last month" | Results are only as valid as the last verified run |
| "We've published this method before" | This manuscript's numbers still need fresh verification |
| "The figures look identical to the last version" | Look identical is not verified identical |

## Publication-Specific Verification Checklist

Complete every item before claiming submission-ready. No skipping.

**Claims and Accuracy**
- [ ] claims-audit PASS — every manuscript claim has a traceable evidence source
- [ ] **Freshness check** — read the most recent `docs/eureka/audits/YYYY-MM-DD-claims-audit.md` frontmatter. Verify `manuscript_hash` and `results_hash` match the current manuscript + results. If hashes mismatch, **soft-warn**: the audit may be stale; consider re-running. Proceed at user's discretion (soft warning, not hard block)
- [ ] **Upstream artifact presence** — confirm the following canonical-path artifacts exist and are fresh (YAML frontmatter `status: passed`):
  - `docs/eureka/audits/YYYY-MM-DD-claims-audit.md`
  - `docs/eureka/reviews/YYYY-MM-DD-review.md` (research-reviewer ≥ 95/100)
  - `docs/eureka/novelty-audits/YYYY-MM-DD-novelty-audit.md` (novelty-competitive-audit PASS)

**Figures**
- [ ] Figures regenerated from scripts (not loaded from stale file)
- [ ] Every figure number and label matches the manuscript text
- [ ] Every figure legend states `n`, statistical test, error bar type (SEM/SD/95%CI), and center value (or confirms N/A for the figure type)
- [ ] Every figure with statistical inference has exact p-values OR in-legend-defined asterisks
- [ ] Every image panel labeled "representative of N independent experiments" or states quantification N
- [ ] No dynamite plots (bar + whisker of mean alone) where raw overlay is feasible (N per group ≤ 50)

**Reproducibility**
- [ ] Experiments reproducible from configs + recorded seeds
- [ ] Environment specification committed (requirements.txt / environment.yml)
- [ ] Seeds recorded for every experiment with stochastic components
- [ ] Single command reproduces the full results pipeline (reproduce.sh or equivalent)

**Review**
- [ ] research-reviewer PASS at pre-submission threshold (≥ 95/100)
- [ ] All CRITICAL issues resolved
- [ ] All MAJOR issues resolved (no open MAJOR issues deferred to revision)

**Reporting Completeness**
- [ ] Negative results reported, not selectively omitted
- [ ] All pre-registered outcomes reported, including null results

**Manuscript Metadata**
- [ ] Data availability statement present and accurate
- [ ] Data version and preprocessing pipeline version explicitly stated in Methods section
- [ ] Code availability statement present and accurate
- [ ] Author contributions clear and complete
- [ ] Conflicts of interest declared

## Reproducibility Sub-Check

These must pass independently before the main checklist is considered complete.

- [ ] Random seeds fixed and recorded for every experiment
- [ ] Config files saved alongside every result file
- [ ] Environment spec committed (requirements.txt / environment.yml)
- [ ] `reproduce.sh` or equivalent exists, is committed, and runs end-to-end
- [ ] Results directory has README explaining file structure and how outputs map to manuscript
- [ ] Raw → processed data is regeneratable from a single command (preprocessing pipeline scripted, versioned, and runnable)
- [ ] Data version claimed in the manuscript matches the data actually used in the analysis (verified by file hash comparison against the registration)

**Failure on any sub-check item means the analysis is not reproducible.** An irreproducible analysis cannot be submitted.

## Key Patterns

**Results match manuscript:**
```
PASS: [Re-run analysis] [Compare output values to Table 2] [All numbers match]
FAIL: "The numbers should match — I haven't changed anything"
```

**Figures regenerated:**
```
PASS: [Run figure scripts] [Diff outputs against manuscript PDFs] [Match confirmed]
FAIL: "The figure looks the same as last time"
```

**Reproducibility verified:**
```
PASS: [Run reproduce.sh from scratch in clean environment] [All results regenerated]
FAIL: "It worked on my machine before"
```

**Statistics verified:**
```
PASS: [Verify every result has effect size + 95% CI + correction method per docs/references/statistical-guide.md] [No uncorrected multiple comparisons]
FAIL: "The p-values are significant — statistics are fine"
```

**Completeness verified:**
```
PASS: [Cross-reference experiment log] [Every run in log accounted for in manuscript]
FAIL: "The main results are all in there"
```

## Why This Matters

Publication errors propagate. A wrong number in a published table becomes a cited number in the next paper, a misinterpreted figure becomes a consensus, and an irreproducible analysis becomes a failed replication. Post-publication corrections damage credibility and waste the field's resources. The gate function exists because the cost of verifying before submission is hours; the cost of a published error is years.

## When To Apply

**ALWAYS before:**
- Submitting to any journal, conference, or preprint server
- Sharing results externally (collaborators, supervisors, funders)
- ANY claim that results are publication-ready
- Responding to reviewer comments with "we have verified..."
- Uploading final manuscript files to any submission system

**Rule applies to:**
- Exact "ready to submit" phrases
- Paraphrases: "good to go", "polished", "final version"
- Implications of readiness
- ANY communication suggesting the manuscript is in final state

## Integration

- **Requires:** `eureka:claims-audit` PASS — every claim must be traceable before this skill's checklist begins
- **Requires:** `eureka:requesting-research-review` PASS at ≥ 95/100 — scientific rigor validated by independent review
- **Requires:** `eureka:hypothesis-first` INTERPRET standards met — every statistical result reports effect size, CI, and correction method
- **Requires:** `eureka:novelty-competitive-audit` PASS — external competitiveness verified against recent literature (internal rigor is necessary but not sufficient for submission)
- **Feeds into:** submission-readiness assessment — this gate is the final check before external submission
- **Called by:** `eureka:using-eureka` when submission intent is detected
- **Reference:** `docs/references/statistical-guide.md` — statistical reporting checklist
- **Reference:** `docs/references/data-checklist.md` — data version locking, preprocessing reproducibility, raw→processed regeneration
- **Reference:** `docs/references/figure-guide.md` — see sections **"Figure Legend Requirements (Reviewer-Grade)"** and **"Common Reviewer Rejection Reasons for Figures"** for the legend reporting checklist and the dynamite-plot anti-pattern
- **Reference:** `docs/references/novelty-audit-guide.md` — search strategy, preemption rubric, differentiation templates, verdict decision tree for the `novelty-competitive-audit` prerequisite

## The Bottom Line

No shortcuts for submission verification.

Re-run the analyses. Regenerate the figures. Check every number. THEN claim it is ready.

This is non-negotiable.

## Skill Type

**RIGID** — The checklist is not optional. The gate function sequence is enforced. The Iron Law is not a guideline.

The only flexibility is in the tooling used to re-run analyses — adapt scripts, commands, and environments to your domain. The requirement to produce fresh verification evidence before claiming submission-readiness does not flex.
