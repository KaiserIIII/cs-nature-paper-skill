# Traceability Auditor Prompt Template

**Purpose**: Automate the manual cross-reference of every quantitative claim in the manuscript against source files in `results/`. Eliminates the "23 numbers hand-cross-referenced to CSV rows" cognitive load that was one of the loudest external feedback items.

**This is Eureka's first COMPUTATIONAL subagent**. Unlike the qualitative reviewers (section-reviewer, figure-reviewer, design-document-reviewer, registration-reviewer, experiment-plan-reviewer, research-reviewer, novelty-audit-reviewer), this subagent performs structural computation: regex extraction, filesystem search, numeric diff. The output is a machine-readable table of matches/misses, not a judgment.

**Dispatch by**: `claims-audit` SKILL.md, as the FIRST step of its workflow (before the agent's own inline review). The agent consumes the subagent's table and then applies judgment to the unmatched/approximate cases.

**Dispatch after**: manuscript draft is complete (all sections written, at least one full pass through `manuscript-writing` has happened).

```
Task tool (general-purpose):
  description: "Traceability audit — extract manuscript numbers and match against results files"
  prompt: |
    You are the Traceability Auditor for the Eureka research rigor plugin. You were dispatched as a fresh subagent to perform a COMPUTATIONAL audit: extract every quantitative claim from the manuscript, then search the results directory for each value and produce a machine-readable diff.

    You are NOT a qualitative reviewer. Do not judge whether numbers are "correct scientifically." Your job is purely:
    1. Extract numbers from manuscript via regex
    2. Scan result files for each number
    3. Report matched / approximate / not_found

    The main agent consumes your table and applies judgment.

    **Manuscript**: {MANUSCRIPT_PATH}
    **Results directory**: {RESULTS_DIR}
    **Numeric tolerance** (default): {TOLERANCE} (0.01 for floats, 0 for integers — adjust if the project uses unusual precision)

    ## Workflow

    ### Step 1: Extract quantitative claims from manuscript

    Read `{MANUSCRIPT_PATH}` (LaTeX `.tex`, Markdown `.md`, or concatenated sections).

    Apply these regex patterns to capture every numeric claim. Each match records:
    - The numeric value
    - The surrounding 80 characters of context (what the number is OF)
    - The line number or section reference

    **How to read the pattern table:**
    - Patterns are **illustrative starting points**, not exhaustive or literal copy-paste. Adapt them for the manuscript's actual conventions (e.g., the field might write `R²` as the Unicode superscript, `R^2` in LaTeX source, `R-squared` in prose, or `R_squared` in a plot label — all are valid variants you should capture)
    - `...` in a pattern means "extend with the same numeric-capture shape" — e.g., `η²\s*=\s*...` should capture `η² = 0.42` by extending with `-?\d*\.?\d+` the way the correlation pattern does. Not literal ellipsis.
    - Unicode characters (`ρ`, `η²`, `±`, `–`) appear in both the patterns below and in manuscripts. Use them directly; don't escape them.
    - LaTeX source often uses `$r = 0.86$`, `$R^2 = 0.74$`, `$\rho = 0.5$` — strip the `$` delimiters and treat the math-mode content as regular text for matching
    - Over-extract deliberately — the downstream tolerance match will filter non-claims

    **Regex patterns** (non-exhaustive starting points; adapt for the specific manuscript):

    | Claim type | Pattern examples | Unicode / variant notes |
    |---|---|---|
    | Correlations | `r\s*=\s*-?\d*\.?\d+` | Also match: `ρ` (Unicode), `\rho` (LaTeX), `R²`, `R^2`, `R-squared`, `R\^2` (literal `R^2`) |
    | p-values | `p\s*(=\|<\|>)\s*\d*\.?\d+(e-?\d+)?` | Also: `p-value`, `P-value`, LaTeX `p<0.001` without spaces |
    | Sample sizes | `N\s*=\s*\d+`, `n\s*=\s*\d+` | Match both `N` (total) and `n` (subgroup); LaTeX `$n = 47$` |
    | Percentages | `\d+\.?\d*\s*%`, `\d+\.?\d*\s*percent` | LaTeX `$50\%$`; avoid matching `50%` inside `%` comments |
    | Effect sizes | `d\s*=\s*-?\d*\.?\d+` | Also: `η²`, `η^2`, `\eta^2`, `f²`, `OR`, `HR`, `RR`, `AOR`, Cohen's h |
    | Confidence intervals | `95%\s*CI\s*\[?\s*-?\d*\.?\d+\s*[,–\-]\s*-?\d*\.?\d+` | Capture both dash styles: `–` (en dash), `-`, and `,` separators |
    | AUC / sens / spec | `AUC\s*=\s*\d*\.?\d+` | Also: `sensitivity`, `specificity`, `PPV`, `NPV`, `C-index`, `balanced accuracy` |
    | Means / SDs | `\d+\.?\d*\s*±\s*\d+\.?\d*` | Also: `mean±SD`, `M = X.XX, SD = Y.YY`; `±` is Unicode U+00B1 |
    | Counts | `\d+\s+(subjects\|patients\|participants\|trials\|sessions\|samples\|cells\|mice\|runs\|seeds)` | Field-specific (extend for domain) |
    | Durations / rates | `\d+\.?\d*\s*(hours?\|minutes?\|days?\|weeks?\|months?\|years?)`, `\d+\.?\d*\s*/\s*(s\|min\|hour)` | |
    | Scientific notation | `\d+\.?\d*\s*[eE]-?\d+` | Also LaTeX: `\times\s*10\^{-?\d+}` |

    Also capture any number that appears as a **statistic claim** outside these patterns — err on the side of over-extraction; the downstream tolerance match will filter non-claims.

    ### Step 2: Check for inline source comments

    If the manuscript has inline comments:
    - LaTeX: `% source: results/file.json:key` or `% source: results/file.csv`
    - Markdown: `<!-- source: results/... -->`

    Record these as hints. A hint match + numeric match = **exact_with_hint**. A hint mismatch (number is there but at a different location than hint suggests) = **hint_mismatch** (flag).

    ### Step 3: Scan the results directory

    Recursively walk `{RESULTS_DIR}`. For each file matching `*.json`, `*.csv`, `*.tsv`, `*.txt`, `*.yaml`, `*.yml`, `*.md`:

    - JSON/YAML: load and flatten, keep key path → value
    - CSV/TSV: read with tolerance-aware numeric parse; record column names + row indices
    - TXT: grep for numeric patterns

    Build a search index: `{value: [(file, location)]}`.

    Files to skip: `*.png`, `*.pdf`, `*.svg`, `*.jpg`, `*.pkl`, `*.pt`, `*.npy`, `*.h5`, `*.nc`, binary formats.

    ### Step 4: Match each manuscript claim against the index

    For each extracted claim:

    1. **Exact match** — value found in at least one results file, within `{TOLERANCE}` (e.g., 0.01 for floats, 0 for integers). Record file + location.
    2. **Approximate match** — value found within 10% relative but outside `{TOLERANCE}`. Flag for review — could be rounding artifact or actual drift.
    3. **Not found** — value not found anywhere in results files. Flag as untraceable.

    **Important**: a value that matches many locations (e.g., `0.05` for a significance threshold) is not a meaningful trace — note this as `trivial_match` and don't consider it verified by the match alone. These need source-comment disambiguation.

    ### Step 5: Produce the output table

    ## Output Format

    ## Traceability Audit Report

    **Status**: Approved | Issues Found
    **Must-fix count**: N (untraceable values or hint mismatches)
    **Should-fix count**: N (approximate matches)
    **Advisory count**: N (trivial matches, suggestions for source comments)

    **Manuscript**: {MANUSCRIPT_PATH}
    **Results directory**: {RESULTS_DIR}
    **Tolerance used**: {TOLERANCE}
    **Files scanned**: N
    **Claims extracted**: N

    ### Summary

    - Exact matches: X/N (Y%)
    - Exact with hint verified: X
    - Approximate matches (need review): X
    - Hint mismatches (flagged): X
    - Untraceable (flagged): X
    - Trivial matches (e.g., `p < 0.05`): X

    ### Detailed table

    | # | Claim value | Manuscript location | Source file (if matched) | Match type | Context |
    |---|---|---|---|---|---|
    | 1 | r = 0.86 | Results §3.2 "CV accuracy" | results/cv_scores.csv:L14 | exact | "The cross-validation accuracy was r = 0.86 …" |
    | 2 | N = 749 | Methods "Participants" | results/cohort_sizes.json:N_total | exact | "… total cohort (N = 749) …" |
    | 3 | p = 0.003 | Results §3.4 | — | **NOT FOUND** | "… group difference was significant (p = 0.003)" |
    | 4 | 0.05 | Methods §2.3 | — | trivial | "α = 0.05 significance threshold" |
    | 5 | 0.88 | Results §3.5 | results/transfer_cohort.json:r_external | approximate (expected 0.886, found 0.88) | "… external-cohort transfer r = 0.88 …" |
    | … | … | … | … | … | … |

    ### Must-fix — untraceable values

    - Claim #3: `p = 0.003` in Results §3.4 is not found in any results file. Check: is the number correct? Was it from a file not in `{RESULTS_DIR}`? Add inline source comment or correct the value.
    - (list all untraceable)

    ### Must-fix — hint mismatches

    - (list any cases where the inline source comment points to a location that doesn't actually contain the value)

    ### Should-fix — approximate matches

    - Claim #5: manuscript says `0.88`, results file has `0.886`. Likely rounding; verify rounding direction and consider matching the reported precision to the source precision.
    - (list all approximate)

    ### Advisory — trivial matches / source-comment opportunities

    - Claim #4: `0.05` matches many locations (threshold, various statistics). Not a meaningful trace. Recommend adding inline source comment to disambiguate.
    - Numbers without source hints that match exactly: consider adding `% source: ...` inline comments to future-proof against manuscript-result drift.
```

**Subagent returns**: Status (Approved iff Must-fix = 0 | Issues Found otherwise), summary counts, detailed table, per-tier issue lists.

**Main agent's response** (in `claims-audit` skill workflow):

- **`Status: Approved`** (Must-fix = 0) → claims-audit proceeds to its own qualitative checks (figure integrity, negative-result reporting, etc.). Address Should-fix items by verifying rounding; Advisory items are optional.
- **`Status: Issues Found`** (Must-fix ≥ 1) → for each untraceable value, the main agent (or user) investigates: is the number correct? Is the source file missing? Is it a copy-paste error? Fix and re-dispatch.

## Architectural notes

This subagent establishes Eureka's **computational subagent pattern**, which differs from the qualitative reviewer pattern (section-reviewer, etc.). Future computational subagents may include:

- **Figure regeneration auditor**: given figure scripts and figure files, verify timestamps and hashes match
- **Citation-graph auditor**: verify all `\cite{}` keys resolve in the `.bib` file
- **Reproducibility smoke-test**: run `reproduce.sh` in a scratch environment and diff outputs against the archived versions

The pattern is: **subagent computes a machine-readable table; main agent applies judgment to the exceptions**. This keeps Eureka's "judgment is human + agent, not automated" principle while eliminating the mechanical drudgery that was the loudest feedback complaint.
