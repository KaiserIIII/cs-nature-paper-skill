# V4 Ultra Specialist Audit

Observed: 2026-09-08. Branch: `feat/v4-vendored-research-team`. This is a
review snapshot, not a release record.

## Decision

V4 now has an independently functional `PUBLIC_CORE` and an optional
`PRIVATE_ULTRA` provider layer. Private selection is based on real,
task-specific behavior evidence. No external private provider is currently
qualified because the comparable runs are `NOT_RUN`; routing therefore selects
PUBLIC_CORE. `recommended merge: NO` remains mandatory until behavior and TTA
publication gates pass.

## Candidate audit

Eighteen candidates were inspected at immutable commits. The registry records
repository, entrypoints, update basis, dependencies, execution and rigor
mechanisms, provenance, limitations, overlap, unique value, and qualification
state for ARS, ARS Codex, K-Dense, Orchestra Skills, Eureka, Sisyphus, SNL
paper writing, Research Engineering Suite, Research Lab Notebook, Lab Notes,
Neuromechanist Research Skills, OpenCite, Experiment Agent, Hermes research
writing, PaperOrchestra, AI Scientist v2, Agent Laboratory, and DeerFlow.

All eighteen are rejected from new PRIVATE_ULTRA formal work until a local,
hash-bound behavior trial passes with an independent checker. Existing audited
PUBLIC_CORE components remain available through the public team. PaperOrchestra,
AI Scientist v2, Agent Laboratory, and DeerFlow are additionally restricted to
system benchmark/adapter use and cannot enter the runtime as ordinary Skills.

## Current and target providers

| Role | Current selected provider | Target primary | Complementary targets |
|---|---|---|---|
| Research Director | V4 native control plane | V4 native | ARS pipeline; Orchestra Autoresearch |
| Literature & Evidence | V4 public specialist | ARS | K-Dense; OpenCite |
| Innovation / Prior Art | V4 public specialist | Sisyphus ensemble | Eureka; K-Dense; ARS |
| Theory & Mechanism | V4 public specialist | K-Dense | Eureka; Sisyphus |
| Data / Dataset | V4 public specialist | K-Dense EDA | K-Dense design; Orchestra domain specialists |
| Experimental Design | V4 public specialist | Eureka rigor stack | K-Dense; Experiment Agent; Sisyphus methodologist |
| Research Engineering / Compute | V4 public specialist | Orchestra Skills; Research Engineering Suite | Autoresearch; notebooks; Experiment Agent |
| Implementation | Host native coding | Host native coding | Orchestra Skills; Research Engineering Suite |
| Statistics | V4 public specialist | K-Dense statistics stack | Eureka integrity rules |
| Visualization | V4 public specialist | Neuromechanist figures | Orchestra; K-Dense; SNL |
| Scientific Writing | V4 public specialist | ARS paper | SNL; Orchestra; Hermes; Neuromechanist |
| Reproducibility / Integrity | V4 public specialist | Eureka; ARS | Research Engineering Suite; notebook; K-Dense; OpenCite |
| Adversarial Reviewer Board | V4 public review board | ARS; Sisyphus; Eureka; K-Dense; Neuromechanist | SNL craft review |
| Publication Editor | V4 Publication Sufficiency Gate | V4 native | ARS; Eureka; SNL; PaperOrchestra advisory |

Every role retains V4 evidence, protocol, graph, publication, authorization,
and release authority. A target mapping is not a qualification result.

## Behavior benchmark

The public suite contains 17 target comparisons across literature, novelty,
mechanism, experiment design, execution, writing, review, integrity, and
long-horizon orchestration. Outputs must be bound to the public input hashes,
the comparator commit, and two counterbalanced blind judgments. Missing files,
stale hashes, or any parity loss fail closed.

- Multi-system parity: `FAIL` (`NOT_RUN`)
- ARS parity: `FAIL` (`NOT_RUN`)
- V4 superiority: `FAIL` (`NOT_RUN`)
- Regressions: no deterministic V4 regression observed in focused tests; real
  behavior regressions remain unknown until comparator runs exist.

## TTA field regression

At `2026-09-08T09:46:40+08:00`, the scheduled campaign was `RUNNING`
with 820/1000 jobs completed, 180 remaining, four workers, zero current failed
jobs, and 80 historical failures preserved. The snapshot does not imply
experiment completion. Statistics, mechanism analysis, ablations, modern
baselines, reviewer completeness, research expansion, full manuscript review,
and revision remain open. Publication Sufficiency is `FAIL`.

## CI and remaining gaps

The complete deterministic suite passes 275 tests plus 24 subtests. The local CI smoke and
recorded-handoff E2E paths also pass after correcting the remaining V3.1.1
runtime metadata and the obsolete smoke expectation for V4's built-in formal
specialist. Hosted CI has not yet run against the commit containing this audit.

CRITICAL gaps: the 17 real comparator runs and blind judgments are absent; the
TTA campaign and publication expansion are incomplete.

MAJOR gaps: system adapters are not behavior-qualified; no external provider
has passed a local task trial; the final statistical, mechanism, ablation,
figure, manuscript, and adversarial-review artifacts do not yet exist.

Recommended merge: **NO**.
