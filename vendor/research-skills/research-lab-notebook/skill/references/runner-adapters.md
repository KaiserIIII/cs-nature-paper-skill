# Connect a job system

Projects may launch research work through a command queue, cluster scheduler,
cloud service, workflow system, or local process. Map that system onto the
[research-job contract](job-runners.md), then record the mapping in
`RUNNER.md`. Check the installed version's help and project instructions before
using a command from this reference.

## Adapter record

Adapt `assets/lab-notebook/RUNNER.md` into the tracked notebook. Project
instructions should point to that file instead of copying its commands. The
result must name each execution layer and map every required capability:

```markdown
## Research job runner

**Backend**: slurm
**Experiment tag**: pass `EXP-NNN` through `--job-name` and output metadata

| Role | Tool or convention |
|---|---|
| Provisioning and placement | Existing institutional cluster |
| Queue and scheduling | Slurm |
| Workflow dependencies | Slurm dependencies and project wrappers |
| Artifact storage | `results/<experiment>/<job-id>/` on durable storage |
| Processed state | Notebook ledger configured during setup |

| Capability | Project command or procedure |
|---|---|
| Submit | `...` |
| Status | `...` |
| Logs | `...` |
| Artifacts | `...` |
| Cancel | `...` |
| Processed check | `...` |
| Processed mark | `...` |
```

Every command must identify the project, working directory, environment, code
revision, output location, and experiment ID or point to a wrapper that does.

## Compose layers deliberately

These tools cover different layers and can be combined. A project may use Dagu
to coordinate a multi-step workflow, Pueue to queue local commands, SkyPilot to
provision or target infrastructure, Slurm to schedule cluster allocations, or
Weft to cover several layers. A project artifact store plus notebook ledger
retains the evidence.

| Tool | Placement or provisioning | Queue or scheduler | Workflow dependencies | Artifact handling | Notebook processed state |
|---|---|---|---|---|---|
| Dagu | Targets local, SSH, container, or Kubernetes execution | Workflow scheduling | DAGs and retries | Logs; durable outputs need a project convention | Ledger |
| Pueue | No | Persistent local command queue | Groups and task dependencies | Logs; durable outputs need a project convention | Ledger |
| SkyPilot | Clouds, Kubernetes, Slurm, and existing machines | Managed jobs | Task-level dependencies, not a general local DAG engine | Workdir sync and configured storage | Ledger |
| Slurm | No | Cluster scheduler | Dependencies, arrays, and site extensions | Project convention required | Ledger |
| Weft | Yes | Yes | Sweeps, pipelines, and DAGs | Staging, retrieval, and job metadata | Native when retained and queryable |

## [Dagu](https://github.com/dagu-org/dagu)

Map the project's Dagu start, status, logs, stop, and artifact procedures. Dagu
can retain workflow history and run steps locally, through SSH/SFTP, or through
container backends, but a completed DAG run does not mean its evidence has been
incorporated into the notebook. Add the processed-job ledger.

Record the DAG/run ID, parameters, working revision, execution target, and
durable output paths. Do not treat Dagu's control-plane files as research
artifacts unless the project explicitly retains and backs them up.

## [Pueue](https://github.com/Nukesor/pueue)

Use Pueue for a durable single-machine command queue, not as a distributed
scheduler. Map add, status, log/follow, kill, and task ID operations. Add both a
durable artifact convention and the processed-job ledger. A Pueue task ID is a
stable execution handle, but it does not record notebook incorporation.

## [SkyPilot](https://docs.skypilot.ai/)

Prefer managed jobs when the controller must survive the local agent session.
Map submission, queue/status, logs, and cancellation from the installed
SkyPilot version. SkyPilot does not by itself define what it means for a result
to be incorporated into a notebook. Configure artifact storage and the
processed-job ledger separately.

Record the cluster or managed-job ID, cloud and region, accelerator request,
task YAML or command, workdir revision, and persistent output URI. Confirm the
project's teardown behavior before submitting paid compute.

## [Slurm](https://slurm.schedmd.com/)

Typical capabilities come from `sbatch`, `squeue` or `sacct`, scheduler output
files, and `scancel`. Inspect local wrappers and site policy before writing the
mapping. Slurm identifies execution but does not usually provide an artifact
registry or processed state.

The project adapter must therefore define:

- where stdout, stderr, checkpoints, metrics, and manifests live;
- how a job records its experiment ID and code revision;
- how array-task IDs join to conditions;
- how artifacts move from scratch storage to durable storage; and
- how the processed-job ledger is written.

## [Weft](https://github.com/osteele/weft)

Inspect the installed Weft skills and CLI help. Map its run, status, log,
artifact, cancel, and processed-state operations directly when available. Keep
Weft job IDs in experiment run tables. Use Weft's native processed marker only
if it is durable and queryable for the project's retention horizon.

Do not copy private placement rules, host names, asset identifiers, or account
configuration into a public or shared notebook.

## Local processes

Use a project task runner or a bounded foreground command for short jobs. For a
long job, choose a mechanism that returns a stable handle and persists status,
logs, and exit state. Do not teach agents to rediscover processes with broad
process-list searches.

A local adapter usually needs both a job registry and the processed-job ledger.
Do not treat a PID alone as a durable job ID.

## Other backends

Inspect the provider and implement the seven capabilities. If a capability is
missing, add a project-local wrapper or document a manual step. Do not pretend
that completion implies processing or that a log directory is an artifact
registry.

## Verification

Use a harmless bounded job that writes a known small artifact. Verify every
read-only capability, then verify processed check and mark. Test cancellation
only on the harmless job and only when the user has authorized it.
