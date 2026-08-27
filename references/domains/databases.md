# Domain profile: databases

- Contributions: query engine, index, transaction protocol, storage, optimizer, or benchmark.
- RQs/evidence: latency, throughput, cost, freshness, consistency, or workload coverage with a declared workload and scale.
- Baselines: established engine and closest technique with equal hardware, indexes, warm-up, and tuning effort.
- Threats: cache state, query ordering, data skew, scale choice, omitted failure/maintenance cost, benchmark overfitting.
- Experiments/statistics: distributions, scale-out, sensitivity and recovery only for relevant claims; retain query-level logs.
- Artifacts/reviewer focus: schema/data generator/license, plans, configs, hardware, build revision, cleanup and replay commands.
- Fatal mistakes: hiding warm-cache status, comparing unlike indexes, reporting a geometric mean without raw workload coverage.
- Specialists: database benchmarking, systems measurement, privacy/licensing.
