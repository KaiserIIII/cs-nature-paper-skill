# Domain profile: machine learning

- Contributions: model, objective, training method, analysis, evaluation, or dataset.
- RQs/evidence: performance, efficiency, reliability, mechanism, or generalization with task-appropriate estimands.
- Baselines: classical, strong tuned current, and mechanism-near; match data, budget, and tuning.
- Threats: leakage, split contamination, seed variance, tuning imbalance, distribution shift, metric gaming, compute confounding.
- Experiments/statistics: multi-seed when stochasticity matters, ablation or robustness only when claim-relevant; report intervals/effect size.
- Artifacts/reviewer focus: code, configs, data license, environment, training budget, failure cases, reproducible evaluation.
- Fatal mistakes: test-set tuning, single lucky seed, claiming generalization from one benchmark, hiding compute or failed runs.
- Specialists: statistical analysis, ML evaluation, dataset and tracking tools; approve permissions before network uploads.
