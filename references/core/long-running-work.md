# Long-running work handoff

V4 applies a two-hour interaction threshold to compute, retrieval, evaluation,
and experiment campaigns. Estimate wall-clock time from a pilot or observed
throughput. When the remaining work is expected to exceed two hours, do not
hold the conversation open.

Before yielding, launch the job through a durable mechanism that survives the
current host conversation. Record its launch ID, status file, heartbeat,
stdout/stderr logs, resume command, and frozen runner, manifest, and protocol
hashes. Bind each frozen hash to the local file that produced it and declare at
least one expected output file with a minimum size. Record an absolute working
directory and use absolute paths for all status, log, identity, and output
files, so resume behavior does not depend on a future shell's current directory. Run
`scripts/long_run_handoff.py assess`; only
`BACKGROUND_AND_YIELD` permits ending the turn while describing work as
running. `BLOCKED_NEEDS_DURABLE_LAUNCH` means the job has not been handed off.

On the next interaction, inspect the durable state. A fresh `RUNNING` heartbeat
returns `WAIT_AND_YIELD`. `COMPLETED` returns `VERIFY_BEFORE_CONTINUING` until
the runtime has recomputed the frozen file identities and checked every
declared output. A caller-supplied `outputs_verified` flag is not evidence.
Only `RESUME_RESEARCH` permits statistics, figures, claims, writing, or
publication gates to consume the job. Identity drift stops the campaign;
failed and partial runs remain in the audit trail and return to recovery.

```bash
python scripts/long_run_handoff.py assess --estimated-seconds 7201 --durable-record long-run.json
python scripts/long_run_handoff.py resume status.json --durable-record long-run.json
```

This interaction rule does not weaken scientific gates. A formal campaign must
also pass its scientific-semantic admission canary, immutable identity checks,
and early online sanity audit before its result shards become evidence.
