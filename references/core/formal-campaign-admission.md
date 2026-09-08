# Formal campaign admission

`FORMAL_CAMPAIGN_ADMISSION_GATE` runs before a pilot expands into a formal job
matrix. A successful process or CUDA smoke is insufficient. The gate requires
a scientific-semantic canary and fails closed.

The canary covers the source baseline, every adaptive method, every recovery
class, `A-B-A`, `A-B-C-A`, a representative shift/severity, and at least two
seeds where practical. It proves that source `state_dict` and BatchNorm running
statistics are identical before and after the trajectory, optimizer step count
and trainable-parameter delta are zero, and source never enters a mutating train
mode.

Each method declares whether parameters, BN affine state, BN running state,
optimizer state, and EMA/anchor/recovery state may change. Any undeclared
mutation returns `FORMAL_ADMISSION_FAIL`. Every prospective measurement has an
explicit event or step ID strictly earlier than its outcome.

Before launch, freeze hashes for the runner, manifest, dataset identity, initial
checkpoints, environment, and protocol. Every shard must bind to that identity.
Changing the runner or manifest stops the campaign and requires a new campaign
ID. After the first completed jobs, repeat source immutability, metric-range,
event-order, provenance, and expected-mutation checks.

The public regression fixture
`assets/evals/v4/regressions/formal_v1_invalid.json` records the failure that
motivated this gate without including project files or personal paths. The
failed campaign itself remains preserved in its private research workspace.

Validate a project-produced admission record with:

```bash
python scripts/formal_campaign_admission.py PATH_TO_ADMISSION_RECORD.json
```

Only `FORMAL_ADMISSION_PASS` authorizes scale-out.
