# Set up or adopt a notebook

Create the smallest notebook that serves the project. If the project launches
long-running work, record how agents submit it, inspect it, retrieve its
outputs, and mark its evidence processed.

## Inspect first

1. Read project instructions and command-runner files.
2. Find existing experiment, result, paper, and job-tracking conventions.
3. Identify version-control boundaries and ignored paths.
4. Identify the job backend and whether it records durable, queryable processed
   state.
5. Preserve existing names and data locations unless they conflict with a core
   notebook invariant.

## Create the baseline

Select and adapt templates from `assets/lab-notebook/`. Start with:

```text
lab-notebook/
  STATUS.md
  QUESTIONS.md
  PRIORITIES.md
  CHANGELOG.md
  experiments/README.md
  findings/README.md
```

Add optional files only when their question is current. See
[Notebook structure](notebook-structure.md).

## Configure compute

Read [Runner adapters](runner-adapters.md). Adapt the bundled `RUNNER.md`
template into `lab-notebook/RUNNER.md` when the project submits jobs. Record the
provisioning, scheduling, workflow, artifact, and processed-state layers, then
record submit, status, logs, artifacts, cancel, processed check, and processed
mark procedures. Keep credentials and private infrastructure out of committed
files.

Choose processed-state storage without asking the user for a backend-dependent
instruction. Use native state only when it is durable, queryable, and
namespaced. Otherwise add the [Processed-job ledger](processed-job-ledger.md).

Use [Project instructions](project-instructions.md) to leave a short agent-facing
handoff that points to the notebook and its runner contract.

## Verify

1. Create one harmless example experiment or adapt an existing one.
2. Confirm that its ID can be attached to a bounded test job.
3. Confirm that status, logs, and artifacts can be retrieved without mutation.
4. Confirm that processed state is queryable and idempotent.
5. Run the bundled notebook validator.
6. Remove example data that could be mistaken for a real result.

Do not submit a real job unless the user requested it. Do not add unattended
loops, hooks that execute experiments, or code-audit policy.
