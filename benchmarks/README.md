# V3.1 benchmarks

These public-safe fixtures test routing and scientific decisions, not paper
quality or venue acceptance. Each benchmark records the expected bounded
behaviors and the evidence needed to score them. They do not contain private
review letters, credentials, or unpublished data.

- `vague-llm-se.md`: undergraduate LLM/code-repair idea.
- `empirical-software-engineering.json`: repository-mining study.
- `systems-benchmarking.json`: workload and latency study.
- `rejected-paper-revision.json`: rejection recovery with preserved evidence.

The deterministic smoke runner uses the first fixture with synthetic artifacts.
Its execution result is generated in CI as `.ci-smoke-result.json` and is not
committed, so a source checkout cannot carry a stale runtime commit. Model-
backed comparisons remain `NOT_RUN` until an approved host adapter is available.
