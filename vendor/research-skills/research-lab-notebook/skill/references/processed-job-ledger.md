# Processed-job ledger

Add this ledger when the runner cannot answer whether a completed job has been
incorporated into durable research evidence.

## Default layout

Use one record per job to avoid append races:

```text
lab-notebook/
  jobs/
    processed/
      slurm/
        123456.json
      skypilot/
        managed-job-17.json
```

Normalize backend names to lowercase letters, digits, and hyphens. Encode a job
ID that is not safe as a filename with URL percent encoding and store the
original ID inside the record.

## Record schema

```json
{
  "schema_version": 1,
  "backend": "slurm",
  "job_id": "123456",
  "experiment_id": "EXP-012",
  "terminal_status": "succeeded",
  "processed_at": "2026-08-11T14:25:00Z",
  "evidence": [
    "experiments/EXP-012-example.md"
  ],
  "artifacts": [
    {
      "uri": "results/exp-012/job-123456/metrics.json",
      "sha256": "hex-digest"
    }
  ],
  "notebook_revision": "version-control-revision",
  "notes": "Primary and manipulation-check results incorporated."
}
```

Required fields are `schema_version`, `backend`, `job_id`, `experiment_id`,
`terminal_status`, `processed_at`, `evidence`, and `notebook_revision`.

## Write protocol

1. Check whether the record already exists.
2. Retrieve and verify outputs.
3. Update the experiment, evidence indexes, and changelog.
4. Validate the notebook.
5. Make the notebook update durable in its version-control system.
6. Write the JSON record to a temporary file in the same directory.
7. Atomically rename it to the final backend/job path.
8. Commit the ledger record if the notebook uses version control.

If several agents may process jobs, use the project's coordination or locking
mechanism around steps 1 through 8. Treat an existing record as an idempotency
signal. Verify its evidence links instead of overwriting it.

## Recovery between the two durable writes

`notebook_revision` identifies the revision that made the evidence durable,
not the later revision that adds the ledger record. If processing stops after
step 5 but before the record is installed:

1. confirm that the final ledger record is absent;
2. inspect the candidate notebook revision and verify that it incorporates this
   exact job ID, outputs, and experiment;
3. do not add the evidence a second time;
4. write the ledger record with that existing revision in `notebook_revision`;
5. validate and commit the ledger record.

If the evidence revision is missing, ambiguous, or does not match the job,
repeat evidence processing from the preserved artifacts. This ordering makes a
crash recoverable without treating an uncommitted notebook edit as processed.

## Failure and reprocessing

A failed job may be marked processed after its failure mode and useful partial
artifacts are recorded. Use its actual terminal status.

Do not overwrite a record to reprocess a job. Fix the linked evidence in version
control and add a `reprocessed` entry to `notes`, or adopt a versioned schema if
the lab needs a formal history. A retry is a new job with a new record.

## When SQLite is preferable

Use SQLite instead of individual JSON files when many writers, transactional
queries, or millions of jobs make the file ledger unsuitable. Keep the same
logical key `(backend, job_id)` and the same write ordering. Document backup,
locking, migrations, and how notebook revisions join to ledger rows.
