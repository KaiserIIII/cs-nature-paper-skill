---
name: research-lab-notebook
description: Set up and operate a durable, file-based research lab notebook with questions, priorities, experiments, preregistered predictions, job results, findings, plans, claims, and publication tracking. Use when creating or adapting a lab-notebook/ directory, editing its records, registering or processing experiments, connecting a local process or job system such as Dagu, Pueue, SkyPilot, Slurm, or Weft, or handing research work across agents and sessions.
---

# Research lab notebook

Treat the notebook as the durable research record. Job logs, chat history, and
metric dashboards are inputs, not substitutes. Existing notebook files are
records, not format specifications.

## Route the task

Read the matching reference before writing:

| Task | Read |
|---|---|
| Create or adopt a notebook | [Setup](references/setup.md), [Notebook structure](references/notebook-structure.md), and [Project instructions](references/project-instructions.md) |
| Decide where information belongs | [Notebook discipline](references/notebook-discipline.md) |
| Edit STATUS, QUESTIONS, GLOSSARY, BIBLIOGRAPHY, PRIORITIES, CHANGELOG, or indexes | [Notebook files](references/notebook-files.md) |
| Register an experiment or process a run | [Experiments](references/experiments.md) and [Job runners](references/job-runners.md) |
| Analyze results or state a conclusion | [Research methodology](references/research-methodology.md) |
| Write a cross-experiment synthesis | [Findings](references/findings.md) |
| Create, resume, or close a plan | [Plans](references/plans.md) |
| Curate claims or publication readiness | [Publication](references/publication.md) |
| Adapt a compute backend | [Runner adapters](references/runner-adapters.md) and, when needed, [Processed-job ledger](references/processed-job-ledger.md) |

## Before writing

1. Locate the notebook. Prefer `lab-notebook/` inside the project unless project
   instructions declare another path.
2. Read project instructions, `STATUS.md`, the relevant research question, and
   the authoritative record linked from the task.
3. Check whether the notebook has its own version-control boundary.
4. Preserve raw outputs. Record their job identity, code revision, parameters,
   provenance, location, and content hash when practical.
5. Write predictions and decision thresholds before inspecting outcomes. Never
   rewrite them after results are known.

## Pause for human review

Treat these as decision gates, not courtesy notifications:

1. Review a plan before any phase executes.
2. Review experiment design before preregistration.
3. Review the preregistration before outcome inspection.
4. Review analysis and interpretation before synthesis or publication use.
5. Review the plan after each executed phase, especially before crossing a gate.
6. Approve a gated follow-up before submitting more work.
7. Review claim promotion before strengthening its status or scope.

An agent may prepare the materials for review. It must not record its own output
as human approval. Record the decision and resulting scope in the owning plan,
experiment, or claim update.

## Place evidence once

- Keep one experiment's design, runs, results, and interpretation in its
  experiment file.
- Create a finding only when the conclusion depends on multiple experiments or
  evidence sources.
- Keep claims proportional to the tested instruments and scope.
- Update indexes and status pages with pointers instead of copied conclusions.
- Use a plan as a bounded research contract. Execution still requires the
  authority appropriate to each action.

## After writing

1. Update the relevant experiment or finding index and affected question,
   priority, claim, and publication pointers.
2. Add a changelog entry only for a result, decision, failure, consolidation, or
   publication milestone.
3. Run the bundled structural validator:

   ```bash
   python3 <skill-directory>/scripts/validate-notebook.py <project-or-notebook>
   ```

   Use `--strict` in automation to treat advisory warnings as failures.
   Use `--format json` when another tool consumes diagnostics. Add
   `--write-plan-index` to regenerate `plans/README.md` from frontmatter.

4. Make the update durable in the notebook's version-control boundary.
5. Mark a job processed only after its outputs are checked, the notebook update
   passes validation, and the durable write succeeds.

Stop at the user's requested boundary. Do not submit a real job, spend money,
publish, write externally, or start unattended execution without authorization.
