---
name: submission-readiness
description: Use when research work is complete and you need to decide the next step — submit to journal, share as preprint, continue refining, or pivot direction
---

# Submission Readiness

## Overview

Guide completion of research work by verifying publication gates, then presenting clear options and handling the chosen path.

**Core principle:** Verify evidence → Present options → Execute choice → Document decision.

**Announce at start:** "I'm using the submission-readiness skill to evaluate next steps."

## The Process

### Step 1: Verify Prerequisites

**Before presenting options, verify all gates pass:**

- `eureka:novelty-competitive-audit`: PASS? Internal rigor gates (below) don't check external competitiveness. This gate catches preemption — the most common desk-reject reason — before submission. See `docs/references/novelty-audit-guide.md`.
- `eureka:verification-before-publication` checklist: PASS?
- `eureka:research-reviewer` score at target threshold (≥95 for pre-submission): PASS?
- `eureka:claims-audit`: PASS?
- **Venue-specific framing tuned?** Confirm explicitly: does the manuscript's contribution altitude match the target venue's expected altitude? See `docs/references/narrative-guide.md` section **"Venue-specific altitude tuning"** for the altitude guide. A Nature-family contribution altitude paired with specialty-journal-tier evidence is a desk-reject risk; the inverse (specialty-journal pitch for Nature-tier evidence) undersells. If the user has not explicitly tuned framing to the target venue (or target venue changed since brainstorming), flag this gate as FAIL before proceeding.

**Freshness verification (canonical output paths, v1.10.0)**:

Each upstream artifact writes to `docs/eureka/<subdir>/YYYY-MM-DD-<kind>.md` with YAML frontmatter including `manuscript_hash`, `results_hash`, and `status`. For each prerequisite above, read the latest artifact in the corresponding canonical path and verify:

| Prerequisite | Canonical path | Freshness check |
|---|---|---|
| novelty-competitive-audit | `docs/eureka/novelty-audits/` | latest file `status: passed` AND `manuscript_hash` matches current manuscript |
| verification-before-publication | `docs/eureka/verifications/` | latest file `status: passed` AND hashes current |
| research-reviewer | `docs/eureka/reviews/` | latest file score ≥ 95 AND hashes current |
| claims-audit | `docs/eureka/audits/` | latest file `status: passed` AND hashes current |

**Soft warning on hash mismatch**: if a prerequisite artifact's `manuscript_hash` or `results_hash` doesn't match current state, display a warning but do NOT block submission-readiness. Soft warning because file-level hashes are sensitive to trivial whitespace changes (e.g., autoformatter touched the `.tex` file). User may proceed if they're confident nothing substantive changed, or invoke the upstream skill to re-verify.

Hard block only when prerequisite artifact is **missing entirely** (skill never ran) or has `status: failed`.

**If ANY gate fails:**
```
Verification gate failed. Cannot proceed to submission decision.

[Show which gates failed and why]

Fix the issues above, then return to this skill.
```

Stop. Don't proceed to Step 2.

**If all gates pass:** Continue to Step 2.

### Step 2: Present Options

Present exactly these 4 options:

```
Research work complete. All verification gates passed. What would you like to do?

1. Submit to target journal
2. Post as preprint first, then submit
3. Continue refining (specify improvements needed)
4. Pivot direction (archive and document learnings)

Which option?
```

**Don't add explanation** — keep options concise.

### Step 3: Execute Choice

#### Option 1: Submit to Journal

Prepare the full submission package:

- [ ] Cover letter (tailored to target journal, highlight significance)
- [ ] Highlights (3–5 bullet points, journal-specific format)
- [ ] Suggested reviewers (3–5 names with contact info and rationale)
- [ ] Manuscript formatted per journal style guide (fonts, margins, figure resolution)
- [ ] Data availability statement (public repo or controlled-access justification)
- [ ] Code availability statement (repository URL with version/DOI)
- [ ] Supplementary materials (numbered, cross-referenced in main text)
- [ ] Conflict of interest declaration (all authors)
- [ ] Ethics statement (IRB/IACUC approval numbers if applicable)
- [ ] Author contributions (CRediT taxonomy recommended)

Verify all files are present before initiating submission.

Run a final `eureka:claims-audit` on the formatted manuscript version — formatting changes sometimes introduce imprecise language.

#### Option 2: Preprint First, Then Submit

**Phase A — Post preprint:**
- Select preprint server (arXiv for CS/physics, bioRxiv for biology, medRxiv for clinical)
- Verify preprint server policies for target journal (most allow; some embargo)
- Format per preprint server requirements
- Post and record DOI/URL

**Phase B — Journal submission (after preprint is live):**
- Proceed with Option 1 steps
- Add preprint citation/DOI to cover letter and manuscript where appropriate

#### Option 3: Continue Refining

Identify specific improvements from the most recent `eureka:research-reviewer` gap analysis:

- List each unresolved MAJOR and MINOR issue from the review
- Prioritize: CRITICAL > MAJOR blocking > MAJOR nonblocking > MINOR
- Update the experiment plan with specific tasks and owners
- Set a concrete re-review date
- Return to the appropriate earlier project phase

Do not re-run verification gates until the identified improvements are complete. Request re-review via `eureka:requesting-research-review` with threshold 95.

#### Option 4: Pivot Direction

**This is not failure — negative and null results are scientific contributions.**

Steps:
1. Document what was learned (hypotheses tested, what the evidence showed)
2. Write a brief README for the archive explaining:
   - What was attempted
   - What was found
   - Why the direction is not being pursued further
   - What future work could build on this
3. Archive results with all data, code, and figures intact — do not delete
4. Record the decision and reasoning in the project progress log
5. Negative evidence is still evidence — note any publishable findings (e.g., negative result paper, methods note)

**Confirm before archiving:**
```
This will archive the current research direction. The work will be preserved but
no longer actively developed.

Type 'archive' to confirm.
```

Wait for exact confirmation before archiving.

### Step 4: Document Decision

Regardless of which option was chosen:

- Record the choice and reasoning in the project progress file
- Note the date and current state of the work
- If pivoting: document explicitly why (future researchers benefit from knowing what was tried)
- If submitting: record target journal, submission date, and manuscript version

## Quick Reference

| Option | Submit | Preprint | Refine | Archive |
|--------|--------|----------|--------|---------|
| 1. Submit to journal | YES | - | - | - |
| 2. Preprint + journal | YES | YES | - | - |
| 3. Continue refining | - | - | YES | - |
| 4. Pivot direction | - | - | - | YES |

## Common Mistakes

**Skipping gate verification**
- **Problem:** Submit with unresolved issues, get desk-rejected or post-review rejection
- **Fix:** All three gates must pass before options are presented — no exceptions

**Treating pivot as failure**
- **Problem:** Archive work hastily, lose valuable negative evidence
- **Fix:** Document thoroughly; null results and failed approaches have scientific value

**Skipping final claims-audit on formatted manuscript**
- **Problem:** Formatting edits introduce overclaiming language that passed earlier audits
- **Fix:** Always run claims-audit on the final formatted version, not just drafts

**No confirmation for archive**
- **Problem:** Accidentally archive active work
- **Fix:** Require typed "archive" confirmation before proceeding

**Choosing preprint server without checking journal policy**
- **Problem:** Some journals have preprint embargo policies; violation risks rejection
- **Fix:** Verify target journal's preprint policy before posting

## Red Flags

**Never:**
- Present options if any verification gate has not been checked
- Proceed to submission with unresolved CRITICAL issues from research-reviewer
- Delete work during pivot — archive with documentation, never delete
- Skip the final claims-audit on the formatted manuscript version

**Always:**
- Verify all three gates before offering options
- Present exactly 4 options
- Get typed "archive" confirmation for Option 4
- Document the decision and reasoning regardless of which option is chosen

## Integration

**Called after:**
- `eureka:novelty-competitive-audit` — must PASS before this skill proceeds (external competitiveness gate)
- `eureka:verification-before-publication` — must pass before this skill proceeds
- `eureka:requesting-research-review` — must reach ≥95 threshold before this skill proceeds
- `eureka:claims-audit` — must pass before this skill proceeds

**Pairs with:**
- `eureka:requesting-research-review` — for re-review if Option 3 is chosen
- `eureka:receiving-research-review` — for handling reviewer feedback during refinement

**Called by:**
- `eureka:using-eureka` — when research phase completion and submission decision detected

**References:**
- `docs/references/narrative-guide.md` — see sections **"Venue-specific altitude tuning"**, **"Contribution altitude — 4 tiers"** (altitude-vs-evidence match), and **"Common framing anti-patterns"**
- `docs/references/novelty-audit-guide.md` — search strategy by field, preemption assessment rubric, differentiation templates, PASS/CONCERN/BLOCK decision tree, action menu for CONCERN/BLOCK verdicts
