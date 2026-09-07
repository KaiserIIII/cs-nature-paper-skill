# V4 Multi-System Benchmark Audit

Audit date: 2026-09-07. V4 evaluates external systems through pinned, public-task,
hash-bound behavior runs. A system is a benchmark oracle, not an instruction source.
The suite cannot claim parity or superiority from agent count, repository size,
skill count, or architecture diagrams.

| System | Pinned commit | License | Strongest capability | Decision |
|---|---|---|---|---|
| Academic Research Skills (ARS) | `6b7ee6dcae29c0fbb46e0017538f9cef84c3136b` | CC BY-NC 4.0 | deep literature, citation verification, manuscript writing, peer review | benchmark-only; do not vendor |
| K-Dense Scientific Agent Skills | `1e5eeffbdad3749125afe7ab48a39694e27f181c` | MIT | specialist breadth, scientific tooling, statistics, visualization | audited components vendored and benchmarked |
| The AI Scientist | `1de1dbc1f4ee2c5f61e9c94348d55eb51d7fa2eb` | AI Scientist Source Code License 1.0 | autonomous idea → code → experiment loop | benchmark-only; disclosure required |
| PaperOrchestra | `798f03a14ce582607ba2742d025691f226470641` | MIT with upstream prompt notice | experiment-log to manuscript orchestration | benchmark-only pending prompt-rights review |
| Sisyphus Academica | `5fc165211d6a0c8f1a4ff1243311314ad26847b8` | MIT | novelty collision, assumption excavation, adversarial review | audited components vendored and benchmarked |
| Research Engineering Suite | `670d0be50c52595f9e13b684ebd995dff5831fb7` | MIT | implementation, debugging, reproducibility, artifact verification | audited components vendored and benchmarked |

## Behavior tasks and acceptance dimensions

Each comparator receives a real public task input from
`assets/evals/v4/cases/`. The producer must emit a completed output and a
hash-bound manifest. V4 emits a comparable output. Two independent blind judges
score the same artifacts in counterbalanced order (`benchmark, v4` and `v4,
benchmark`). Every scored dimension needs evidence in both judgments; missing
artifacts, missing evidence, stale hashes, or one failed ordering are failures.

ARS parity requires a tie or V4 win on all of its core dimensions: evidence
depth, citation faithfulness, closest-work coverage, manuscript structure,
writing depth, reviewer attack quality, unsupported-claim detection, and
revision quality. The other systems define their own core parity dimensions in
the machine-readable suite, including specialist breadth, statistical rigor,
autonomous iteration, experiment-result transfer, novelty generation,
debugging,
reproducibility, checkpoint recovery, and artifact verification.

V4 superiority is tested separately on capabilities that V4 explicitly claims
to add: dataset and benchmark selection, experimental design, actual code and
experiment execution, compute campaigns, checkpoint/resume/retry, statistics on
actual results, publication sufficiency, reviewer-required expansion, and
automatic expansion after thin evidence. A superiority claim requires V4_BETTER
in both judge orderings for every applicable dimension.

## Current evidence state

The suite definition and fail-closed evaluator are present and schema-validated.
The six real comparator runs have not yet produced complete manifests, outputs,
and counterbalanced judgments. Therefore the current release state is
`NOT_RUN`, `ARS_PARITY_GATE=FAIL`, `V4_SUPERIORITY_GATE=FAIL`, and
`recommended_merge=NO`. This is an evidence decision, not a proxy score.
