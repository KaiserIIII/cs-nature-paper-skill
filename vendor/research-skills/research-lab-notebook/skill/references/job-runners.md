# Running research jobs

Research work may run on a laptop, shared cluster, cloud service, or workflow
system. The notebook needs stable procedures to submit work, inspect it,
retrieve its outputs, cancel it when authorized, and record that its evidence
has been processed. Record each procedure in the project's `RUNNER.md`. This
project-specific mapping is the runner contract.

## Required capabilities

| Capability | Required result |
|---|---|
| Submit | Stable job ID, experiment tag, bounded command or workload, code revision |
| Status | Queued, running, succeeded, failed, or canceled |
| Logs | Read-only stdout/stderr or service logs |
| Artifacts | Immutable or versioned outputs with retrieval metadata |
| Cancel | Explicitly targeted cancellation when authorized |
| Processed check | Whether this job's evidence has entered the notebook |
| Processed mark | Idempotent mark written after durable notebook updates |

Useful optional fields include host or cluster, accelerator, image or
environment, start and end times, exit code, runtime, cost, parent job, retry,
and artifact hashes.

## Tagging

Attach the experiment ID to each submission. Also attach the project ID when a
runner spans projects. A sweep may add a condition or shard tag, but the
experiment ID remains the primary join key.

## Processed state

Processing state answers a different question from completion:

- `completed`: the backend finished the computation.
- `processed`: the outputs were checked and incorporated into durable evidence.

Prefer a backend's native processed marker when it is durable, queryable, and
namespaced. Otherwise use the [processed-job ledger](processed-job-ledger.md).

Write the processed mark last. Store a pointer to the experiment or finding and
the notebook revision when the backend allows metadata.

## Failure behavior

Do not mark failed or partial jobs processed until their failure mode is
recorded. Preserve logs and partial artifacts that explain the failure. A retry
gets a new job ID and links to the original; it does not overwrite history.

Avoid open-ended local wait processes. Prefer one-shot status and log checks or
a bounded monitor that will finish in the current session.
