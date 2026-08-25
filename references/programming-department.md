# Programming and implementation department

Use this reference for research software, experiments, analysis pipelines,
artifact packaging, or long-running jobs. The programming department converts
a frozen protocol into inspectable evidence; it does not choose a preferred
scientific conclusion.

## Required roles

1. **Protocol translator:** maps units, estimands, exclusions, failure states,
   and frozen inputs to code/configuration.
2. **Domain implementer:** writes the smallest project-native change needed for
   the experiment or artifact.
3. **Root-cause debugger:** reproduces failures, traces boundaries, tests one
   explanation at a time, and records operational failures.
4. **Verifier:** runs fresh tests and reproduction commands from declared
   inputs; it must not rely on the producer's completion claim.
5. **Risk specialist, when triggered:** property-based, mutation, security,
   performance, numerical, distributed, or ML-evaluation checks selected by an
   identified threat.

These roles can be staffed by fewer people or agents only if coverage and the
loss of independence are explicit.

## Environment contract

Before formal execution, record what can change the result:

- code revision and uncommitted-diff policy;
- data/input manifest, hashes, licenses, and private/public boundary;
- operating system, architecture, runtime, package manager, dependency lock,
  container or virtual-machine image, and relevant drivers;
- configuration, commands, seeds, target order, locale, time zone, clocks, and
  network/index snapshot when material;
- CPU/GPU/RAM/storage budget and timeout/retry policy;
- expected outputs, schemas, checkpoints, logs, and failure codes;
- permitted external writes, credentials, services, and cleanup/rollback.

Do not migrate package managers, language versions, build systems, or style
tooling simply because a candidate skill prefers another stack. Project-native
constraints and the registered design win.

## Pilot-to-formal workflow

1. Reproduce the current state and run the narrowest existing checks.
2. Trace protocol fields to code paths and identify unimplemented ambiguity.
3. For stable behavior changes, write a failing test or executable oracle,
   implement the minimum change, then refactor with tests green.
4. Exploratory notebooks and one-off pilots may precede tests, but their outputs
   are not formal evidence. Promote the chosen path into a deterministic,
   tested entry point before it supports a paper claim.
5. Use systematic debugging for failures: reproduce, collect boundary
   evidence, state one hypothesis, test minimally, and verify the real command.
6. Freeze formal inputs and execute without overwriting earlier evidence.
7. Bind outputs to code, config, environment, and input hashes; retain failed
   cases and protocol exclusions.
8. Re-run from the documented public entry point or state the exact boundary
   that prevents it.

## Select tests by failure risk

| Risk | Useful check |
|---|---|
| stable transformation or parser | example tests plus property-based invariants |
| silent boundary/branch errors | boundary cases, metamorphic relations, mutation testing if justified |
| numerical inference | reference cases, tolerances, sensitivity and platform checks |
| stochastic ML | registered seeds/repetitions, distributional checks, data leakage audit |
| external API/index | pinned snapshot or cached evidence, schema/timeout/rate-limit failure tests |
| packaging/environment | clean-environment install and minimal smoke path |
| long campaign | resume/idempotence, checkpoint integrity, partial-output quarantine |
| security-sensitive artifact | dependency, secret, permission, and supply-chain review |

Coverage percentages are diagnostics, not a universal quality threshold.
Property-based or mutation testing is useful only when the project has a clear
oracle or invariant; do not add dependencies without authority.

## Long-running experiments

Prefer a recoverable batch command with a manifest, per-unit state, structured
logs, bounded retries, and periodic checkpoints. The foreground agent should
not burn tokens by repeatedly polling an unchanged job. Use the host's job,
thread, or automation mechanism when available; otherwise provide a stable
status command and inspect only at meaningful boundaries. A job is complete
only when the process exits, expected outputs validate, and hashes/logs agree.

## ML-specific employees

Model evaluation, dataset access, and experiment tracking skills can be useful
for Hugging Face or similar workflows, but they may require network access,
tokens, public-by-default dashboards, or remote writes. Activate them only for
matching ML tasks, record dataset/model revisions, separate local smoke tests
from formal evaluation, and obtain authority before uploading results or
changing repository visibility.

## Completion evidence

Report the exact commands run, exit status, test count by type, unresolved
warnings, changed files, output anchors, and what was not tested. Fresh
verification is mandatory before saying that an implementation works. Passing
tests do not authenticate raw data, validate a construct, or establish the
paper's causal/theoretical interpretation.
