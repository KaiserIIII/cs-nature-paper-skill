# Empirical study playbook

Read this reference for repository mining, benchmarking, experiments, case
studies, human studies, data science, longitudinal analyses, or mixed methods.

## Select standards by study family

Do not apply one checklist to every empirical paper. Identify the primary and
secondary study families, then retrieve current method-specific standards from
the relevant scholarly community. For software engineering, start with the ACM
SIGSOFT Empirical Standards and choose the repository-mining, benchmarking,
experiment, longitudinal, case-study, engineering-research, or other applicable
standard. Record essential criteria, justified deviations, and inapplicable
criteria.

## Construct table

For every construct, create a row:

| Construct | Conceptual definition | Operational measure | Role | Known gap | Validation/sensitivity |
|---|---|---|---|---|---|

Roles include outcome, exposure, mediator/gate, covariate, sampling variable,
and diagnostic. A prerequisite should not be presented as the downstream
phenomenon it merely enables.

## Design table

Record before formal execution:

- target population and accessible frame;
- unit of analysis and repeated/clustered structure;
- sampling and weighting;
- treatment/exposure/target factors;
- outcomes and their denominators;
- estimands and contrasts;
- missingness and protocol exclusions;
- confounding strategy and what remains uncontrolled;
- stochastic repetitions and their rationale;
- multiplicity and confirmatory/exploratory roles;
- stopping, timeout, retry, and operational-unknown rules;
- data/code/environment freeze and amendment policy.

Robust or clustered standard errors change uncertainty estimates; they do not
by themselves remove cluster-level confounding. Prediction accuracy, causal
identification, descriptive estimation, and mechanism testing are different
goals.

## Mechanism-first analysis

Order analysis around the mechanism rather than tool complexity:

1. show the joint outcome states and denominators;
2. localize where the process fails or differs;
3. condition on prior gates only when the conditioning question is explicit;
4. estimate the registered contrasts with uncertainty;
5. test rival explanations and clustering/sharing sensitivities;
6. analyze interventions using their intended estimands;
7. demote prediction, calibration, extra curves, and implementation diagnostics
   unless they answer an RQ or a named threat.

When gates are not strictly nested, report all observed joint patterns instead
of forcing a funnel narrative.

## Cross-environment or cross-dataset extensions

Before adding targets, state whether the purpose is:

- construct validation;
- target-era or platform alignment;
- generalization within a named matrix;
- mechanism discrimination;
- robustness to implementation choices;
- artifact execution validation.

Use one observation window/index policy across targets. If the prior study used
a different time-indexed source, label the extension as a new version and do
not silently pool incompatible observations.

## Intervention or repair studies

Separate:

- coverage over all eligible failures;
- effort/calls/time over all eligible cases;
- edit magnitude only on a clearly defined success set;
- pairwise comparisons on common successes;
- performance by baseline failure layer.

Do not call a policy safer, cheaper, or more maintainable unless those
constructs were directly measured.

## Reporting boundaries

State what success permits next and what it does not prove. For example,
dependency resolution may be a necessary workflow gate but does not establish
installation, imports, tests, numerical equivalence, or scientific
reproducibility. Execution ladders should retain protocol exclusions rather
than recoding unavailable commands as failures.
