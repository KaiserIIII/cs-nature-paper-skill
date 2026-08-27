# Evidence provenance

Use one machine-readable edge for every load-bearing claim:

```json
{
  "anchor_id": "EA-0001",
  "claim_id": "C1",
  "result_id": "R1",
  "source_artifact": "results/table.csv",
  "exact_region": "rows 2-5, columns mean and ci95",
  "transformation": "scripts/analyze.py --config configs/formal.yaml",
  "command": "python scripts/analyze.py ...",
  "exit_status": 0,
  "code_commit": "abc1234",
  "config_hash": "sha256:...",
  "environment": "envs/formal.lock",
  "input_hash": "sha256:...",
  "uncertainty": "95% CI; clustered by repository",
  "scope": "12 fixed repositories, 2025 snapshots",
  "status": "VERIFIED",
  "verified_utc": "2026-08-27T00:00:00Z"
}
```

Allowed claim statuses are `PLANNED`, `SUPPORTED`, `SCOPED`, `WEAK`,
`UNSUPPORTED`, and `WITHDRAWN`. Evidence relations are `SUPPORTS`,
`PARTIALLY_SUPPORTS`, `QUALIFIES`, `CONTRADICTS`, `BACKGROUND_ONLY`,
`DOES_NOT_SUPPORT`, and `NOT_VERIFIED`.

Resolution, compilation, or a passing unit test may be a prerequisite for a
downstream result; they do not automatically establish execution success,
reproducibility, validity, causality, or maintenance cost. Missing or private
regions are recorded as such, never inferred.
