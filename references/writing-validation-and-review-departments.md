# Writing, validation, and review departments

Use this reference for manuscript production, artifact integrity, adversarial
assessment, and submission readiness. These departments form a correction
loop, not a vote-generating acceptance simulator.

## Writing department

### Capability contract

Staff:

1. **Evidence-bound drafter:** writes only from the research contract, evidence
   ledger, verified sources, formal results, and declared exploratory analyses.
2. **Claim verifier:** maps every load-bearing sentence to evidence and checks
   construct, scope, uncertainty, and causal language.
3. **Editorial compressor:** makes the abstract and first pages legible to the
   venue audience without deleting scientific boundaries.
4. **Document engineer:** handles LaTeX/DOCX/BibTeX, cross-references, tables,
   supplement integration, and current template constraints.

### Draft order

Prefer:

1. results objects and exact finding sentences;
2. methods and protocol boundaries;
3. discussion, alternatives, and implications;
4. introduction from the source-backed argument brief;
5. abstract, title, and contribution list last;
6. supplement, declarations, data/code availability, and cover letter;
7. final consistency and disclosure pass.

This order reduces the temptation to write promises that later evidence cannot
support. A different project-native order is acceptable if claim traceability
is preserved.

### Section contracts

- **Title:** phenomenon/artifact plus bounded setting; no unsupported prestige
  or generality words.
- **Abstract:** problem, gap, scope/design, headline findings, contribution, and
  one essential boundary in the venue limit.
- **Introduction:** stakeholder decision, prior knowledge, unresolved gap,
  mechanism/propositions, design logic, contributions, and headline evidence.
- **Methods:** enough operational detail to understand units, estimands,
  protocol, exclusions, dependence, and reproduction path.
- **Results:** one question per subsection; denominator, estimate, uncertainty,
  and evidence anchor before interpretation.
- **Discussion:** knowledge gained, theory/mechanism relation, alternatives,
  practical meaning, boundary conditions, limitations, and falsifiable next
  predictions.
- **Conclusion:** narrow synthesis, not new evidence or generalized marketing.

Language/humanization checks may remove repetitive or artificial prose, but
must not conceal AI use, invent a personal voice, or alter technical meaning.

### Stop condition

Writing passes when the 90-second editor questions are answerable, every main
claim is traceable, terminology/numbers agree, the venue form is current, and
remaining limitations are explicit. Polishing stops when further edits are
stylistic churn rather than error correction or decision-relevant clarity.

## Validation department

### Independent evidence map

Build a fail-closed map:

`claim -> source/result -> exact region/artifact -> transformation -> manuscript location`

Represent supporting, contradictory, qualifying, and missing evidence. Never
invent confidence for an absent edge. Validation has layers:

1. **Scientific:** construct validity, estimand/design match, uncertainty,
   alternatives, and scope.
2. **Data/provenance:** source manifests, hashes, exclusions, amendments,
   public/private boundary, and non-overwrite history.
3. **Code/artifact:** fresh tests, reproduction entry points, environments,
   licenses, permissions, and expected failures.
4. **Cross-artifact consistency:** manuscript, tables, figures, supplement,
   repository, README, disclosure, and submission fields.
5. **Document:** compilation, unresolved references, fonts, vector/raster
   properties, metadata, anonymity, page/word limits, and visual inspection.
6. **Supply chain:** third-party skills/packages, exact pins, security warnings,
   credentials, network endpoints, and release integrity.

Machine checks return `PASS`, `CONDITIONAL`, or `FAIL` with evidence anchors.
They do not authenticate undocumented lab work or guarantee acceptance.

### Statistical validation

Use a study-appropriate methodologist. Recompute headline values, check units
and denominators, verify model/design assumptions, distinguish clustered
uncertainty from confounding control, report effect sizes and intervals, and
inspect missingness/multiplicity/sensitivity decisions. Generic statistical
skills are advisory; domain design and registered estimands control the final
analysis.

### Stop condition

All CRITICAL failures and claim-changing MAJOR failures are resolved, or the
claim is narrowed/withdrawn with the author's decision recorded. Known
non-critical limitations may remain as `CONDITIONAL`; they must not be hidden.

## Review department

### Select reviewers from threats

Use only roles relevant to the paper:

- editor/readability and venue contribution;
- closest domain competitor and prior art;
- empirical methods/statistics or theory/formal rigor;
- artifact/reproducibility/security;
- practitioner/deployment;
- ethics, human-subject, fairness, or dual-use;
- adversarial alternative explanation;
- newcomer/student for exposition when accessibility matters.

For a high-stakes full review, use at least an editor, a domain role, a method
role, and one role tied to the paper's largest residual threat. Independence is
about unseen reasoning and separate evidence review, not arbitrary reviewer
counts. If one agent simulates all roles sequentially, disclose that they are
perspectives from one system.

### Review output

Each finding needs:

- severity (`CRITICAL`, `MAJOR`, `MINOR`);
- manuscript/artifact anchor;
- violated claim, construct, standard, or reader need;
- evidence and uncertainty;
- smallest sufficient repair;
- whether new data are necessary;
- verification test and residual risk.

Reviewers state the strongest contribution, strongest rejection reason, and
strongest rival explanation. They must not be shown a desired verdict. Do not
convert recommendations into a majority vote or estimated acceptance chance.

### Revision loop

Triage findings into framing, construct, theory, design, implementation,
analysis, interpretation, writing, artifact, ethics, or venue. Fix root causes,
update the concern/claim matrices, and then run a fresh targeted re-review.
Accept/revert decisions require evidence, not an unbounded polishing loop.

### Stop condition

Review passes when no unresolved CRITICAL or material MAJOR finding invalidates
the bounded contribution, divergent assessments are documented, and an editor
can state why the design supports exactly the manuscript's limited claim. The
author retains the final venue and submission decision.
