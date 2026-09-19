# Research job runner

**Backend**: Replace with the execution backend or stack
**Experiment tag**: Replace with how `EXP-NNN` is attached to every job

## Layers

| Role | Tool or convention |
|---|---|
| Provisioning and placement | Replace or state not applicable |
| Queue and scheduling | Replace |
| Workflow dependencies | Replace or state not applicable |
| Artifact storage | Replace with a durable path or URI convention |
| Processed state | Replace with native state or `jobs/processed/<backend>/` |

## Capabilities

| Capability | Project command or procedure |
|---|---|
| Submit | Replace with a bounded submission that returns a stable job ID |
| Status | Replace with a one-shot read-only check |
| Logs | Replace with read-only retrieval |
| Artifacts | Replace with durable retrieval and provenance |
| Cancel | Replace with explicitly targeted cancellation |
| Processed check | Replace with a native query or ledger lookup |
| Processed mark | Replace with a native mark or ledger write protocol |

## Identity and artifacts

Record the project, experiment ID, code revision, environment, parameters,
working directory, job ID, and durable output location for every run. Record
array tasks, retries, and parent jobs without reusing a job ID.

## Verification

Verify the mapping with one harmless bounded job. Confirm status, logs,
artifacts, and processed-state behavior before relying on the adapter. Test
cancellation only when it is authorized.
