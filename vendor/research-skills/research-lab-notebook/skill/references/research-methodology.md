# Research methodology

Apply these rules before reporting a number or turning a run into a claim.

## Validate the instrument first

A manipulation is an empirical claim. Test it on the cheapest sufficient
instrument before paying for a large run. Examples include a small API sweep, a
short pilot, a reduced dataset, a synthetic control, or a low-cost model.

Record what the validation establishes and what it does not. A direction that
holds on one model, dataset, or population may reverse on another.

## Separate planned and exploratory analysis

Analyze preregistered primary outcomes first. Label additional analyses as
exploratory. Do not edit a priori predictions or thresholds after seeing the
result.

## Review analysis and interpretation

Pause after primary analysis and before synthesis. Give the human reviewer the
preregistration, exclusions, checks, observed values, uncertainty, exploratory
analyses, and proposed interpretation. Record corrections and the scope the
review licenses. A follow-up selected by a decision rule still waits for human
approval before new work is submitted.

## Report enough to assess the claim

Include, when applicable:

- sample size and independent unit;
- central estimate and uncertainty interval;
- effect size, not only a p-value;
- multiple-comparison procedure and the family of tests;
- seed, model, dataset, or subgroup variation;
- missing data and excluded runs;
- manipulation and negative controls;
- cost and runtime when they constrain interpretation; and
- exact code and data revisions.

Do not call a single seed, model, prompt family, or dataset a general result.
State the tested scope in the finding sentence.

## Check aggregation

Inspect subgroup results before relying on a pooled effect. Look for Simpson's
paradox, mixture shifts, class imbalance, duplicated observations, leakage, and
pseudoreplication. The independent unit must match the statistical test.

## Treat nulls carefully

A null result may indicate absence, low power, a failed manipulation, a noisy
instrument, or an insensitive outcome. Report sensitivity or detectable effect
size when possible. A failed counting or retrieval check must report its
false-void rate before it can justify abandoning a line of work.

## Attribute reversals

When a finding negates a claim, name who or what made the earlier claim: a paper,
an experiment, a preregistered prediction, or a working hypothesis. Avoid vague
phrasing that implies a consensus no source held.

## Keep claims proportional to evidence

- `supported`: direct evidence at the named scope with required checks.
- `provisional`: evidence exists but generality, power, or a key control is
  missing.
- `blocked`: the current instrument cannot adjudicate the claim.
- `refuted`: an adequately sensitive test contradicts the prediction at the
  named scope.

Use the narrowest label that remains true if the reader opens only the linked
evidence.
