# Domain profile: systems

- Contributions: architecture, scheduling, storage, runtime, reliability, or systems measurement.
- RQs/evidence: throughput, latency, tail behavior, resource cost, scaling, correctness, or failure response in a named workload.
- Baselines: production/common system and closest design under matched hardware, configuration, and workload.
- Threats: warm-up/order effects, hidden caching, workload selection, hardware confounding, omitted failures, instrumentation overhead.
- Experiments/statistics: repeated runs when variability matters, distributions/tails, scaling and failure tests only when claim-relevant.
- Artifacts/reviewer focus: hardware/software environment, workload generator, configs, logs, resource accounting, recovery instructions.
- Fatal mistakes: one-run speedup, incomparable hardware, average-only latency, claiming reliability without failure evidence.
- Specialists: performance measurement, artifact evaluation, distributed systems, security.
