# V3 design audit: V1, V2, and replacement map

Audit date: 2026-08-27. Sources inspected: the V1 working copy and backup
archive, the V2 git history (`f5b30f1..e42e9d6`), every V2 reference, script,
template, test, metadata file, and the V2.1 release archives.

| Capability | V1 | V2/V2.1 | Keep | V3 design | Regression guard |
|---|---|---|---|---|---|
| CEO identity | Strong branded CEO and automatic staffing | PI/editor language, narrower routing | CEO/Research Director | Student-first CEO with diagnosis, budget, risk, routing and stopping authority | routing cases + student cases |
| Seven departments | Clear serial organization and handoffs | Adaptive capability contracts | Department names and handoff UX | Dynamic graph nodes with producer/checker contracts | graph/schema tests |
| Workflow | Fixed full pipeline, high execution energy | Seven modes and six gates | Automatic next-step discovery | `research_graph` with parallel, branch, rollback, reopen and bounded loops | graph transition tests |
| Argument | Checklist of novelty and venue goals | Claim, evidence, mechanism, constructs, scope, falsifiers, alternatives | Entire V2 scientific kernel | Control-plane `research_contract` + normalized claims | argument gate |
| Innovation | Six generators and 50-hypothesis quota | Closest-work, mechanism, falsifier, alternatives; no quota | Generators as optional ideation | Novelty Intelligence with closest-work and prior-art red team | scientific pressure cases |
| Feasibility | Implicit in implementation | Resource and study design cautions | Resource realism | Explicit GO / scope reduction / pilot / high risk / no-go gate | feasibility fixtures |
| Experiments | Universal five ablations, >=3 repetitions | Threat-selected additions, no quotas | Claim-driven decision logic | `experiment_decision_matrix`, discovery/pilot/formal labels, amendment history | protocol and provenance tests |
| Literature | Broad search and citation aspirations | Discovery, identity, claim-support verification | Seven-department intent | Three-layer literature registry and source matrix | citation pressure case |
| Evidence | Mostly narrative acceptance checks | Evidence ledger and anchors | Fail-closed evidence mapping | Machine-readable anchor: claim -> result -> data -> command -> commit -> env -> hash | anchor schema tests |
| Research memory | No private state | Contract, ledger, decision log | Private, non-overwrite state | Expanded V3 state with graph, registries, risks, venue and manifest; V2 migration | migration tests |
| Implementation | Aggressive code/experiment checklist | Environment contract, pilot/formal, debugging, fresh verification | Fresh command evidence and recovery | Execution-plane artifact events cannot promote claims | completion pressure case |
| Figures | Seven visual archetypes, vector and caption quotas | Source-data-first, seven-gate audit | Truthful figure contract | Claim-bound renderer manifest; no generated data marks | figure pressure case |
| Writing | Venue selection and Introduction-Twice UX | Claim-led, editor 90-second test, live venue sources | Editor-first clarity and evidence-bound prose | Progressive writing references routed by venue/study type | writing cases |
| Validation | 5+7 checklist and AI detector threshold | Fail-closed PASS/CONDITIONAL/FAIL | Independent verification | Three-layer audit plus explicit residual risk; no arbitrary score | audit rubrics |
| Review | Many personas and acceptance votes | Threat-selected findings and bounded revision | Adversarial roles where useful | Reviewer selection from actual threats; no acceptance probability | review pressure case |
| External skills | Silent install suggestions and popularity | Employee registry, pins, permissions, qualification | Capability-based staffing | Marketplace with statuses, context budget, adapter boundary and quarantine | supply-chain case |
| Autonomy | CEO executes and asks for continue | Author control for high-stakes actions | Execute routine work | Guided/Copilot/Autopilot with explicit budget and permission envelope | autonomy cases |
| User experience | Highly actionable, status summaries | Scientifically safer but more specialist | Status: done/current/next/risk | Beginner brief, just-in-time explanations, department dashboard | student UX cases |
| Portability | Primarily Claude/Codex shell snippets | Standard-library scripts and public contracts | Host-portable core | Codex/Claude adapters; dependency-light scripts | validator + host docs |

## Preserve, rewrite, move, remove, add

- Preserve V1 branding, seven department labels, department handoff language,
  execution-oriented status summaries, and the original branch/archive.
- Preserve V2 claim/evidence/mechanism, construct and scope limits, falsifiers,
  alternatives, frozen protocol, evidence ledger, decision log, amendments,
  live venue verification, producer/checker separation, employee lifecycle,
  capability staffing, behavior evaluation, fail-closed gates, bounded review,
  no quotas, no reviewer voting, no silent installation, and no auto-submit.
- Rewrite V2's phase-oriented entrypoint into graph routing and a student-first
  CEO; keep V2 readers and state files compatible.
- Move detailed department, domain, study-type, mentoring, host, and security
  guidance behind progressive-disclosure references.
- Remove only unsafe or scientifically weak V1 rules: universal hypothesis and
  ablation quotas, fixed repetition counts, AI-detection thresholds, reviewer
  unanimity/acceptance scoring, automatic public release, and unreviewed installs.
- Add research autopilot, feasibility gate, domain/study profiles, formal
  provenance anchors, graph events, budget/permissions, migration tooling,
  routing evaluations, and three independent release audits.

## Known audit limits

The V1 backup is a source snapshot rather than a git branch in this checkout;
the V2 repository currently has `v2` and its remote branch only. V3 therefore
creates a new candidate branch without rewriting either historical artifact.
External skill quality is time-bounded and cannot substitute for per-project
qualification. Public repository metadata and README claims were treated as
discovery evidence only; exact source files and executable behavior still need
local trials before formal evidence use.
