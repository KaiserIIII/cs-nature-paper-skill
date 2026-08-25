# Manuscript, figures, review, and submission

## Argument allocation

The abstract and first two pages carry the editorial argument. They should make
the phenomenon/artifact, stakeholder, prior knowledge, gap, mechanism,
evidence, headline findings, contribution, and scope visible before detailed
protocol machinery.

Use a page/word budget derived from the current venue rules. Do not rely on a
static venue table. Retrieve the current author instructions, CFP, track rules,
template, anonymity policy, artifact policy, and AI disclosure policy from
primary venue sources and record the access date.

## Abstract audit

Check:

- problem and empirical/technical setting appear early;
- constructs are understandable without dense acronyms;
- design scope is concrete;
- only decision-relevant numbers remain;
- results map to RQs or propositions;
- contribution is stated as knowledge/capability, not analysis volume;
- non-claims are not smuggled in through words such as reproducible, robust,
  safe, general, or efficient.

Follow venue-specific length limits; do not impose a universal word count.

## Figure audit

Follow the complete producer/checker workflow in
[figure-department.md](figure-department.md); this section is the manuscript
selection summary.

Every figure needs a question. Prefer:

- mechanism/design diagrams for constructs and downstream boundaries;
- joint-state/transition views when outcomes are not strictly nested;
- interval/forest plots for comparable estimates;
- UpSet-style intersections for multi-target overlap;
- paired/common-success views for intervention tradeoffs;
- tables when exact mappings matter more than shapes.

Provide source CSV/JSON, deterministic code, vector PDF/SVG (and EPS only when
the venue requires it), alt text, a self-contained caption, and an explicit
encoding for unavailable/not-estimable results. Inspect the final embedded
size rather than only the standalone figure.

## Review synthesis

Follow the role selection, finding schema, revision loop, and stop condition in
[writing-validation-and-review-departments.md](writing-validation-and-review-departments.md).

Ask each review role for:

- strongest contribution in one sentence;
- strongest reason for rejection;
- evidence anchor for each finding;
- alternative explanation;
- smallest sufficient fix;
- severity: CRITICAL, MAJOR, or MINOR;
- recommendation confidence and missing information.

Review recommendations are not ground truth. Summarize agreement and
divergence. A polished review cannot establish that an experiment ran or a
claim is true.

## Submission preflight

Check source and compiled artifacts:

- current template/class/style options;
- page/word limits and what is excluded;
- anonymity and PDF metadata;
- required sections/checklists/declarations;
- references and cross-references;
- font embedding, vector figures, resolution, and accessibility;
- source archive flatness/path safety if required;
- artifact license, privacy, and public/private split;
- cover letter and submission-field consistency;
- author-confirmed names, affiliations, funding, conflicts, contributions, and
  AI-use disclosure.

A clean linter means no detected machine-checkable issue, not guaranteed
acceptance. Stop before uploading or submitting unless the author explicitly
requests that external action.
