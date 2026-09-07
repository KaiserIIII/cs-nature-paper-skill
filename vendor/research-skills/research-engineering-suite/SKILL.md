---
name: research-engineering-suite
description: Use when scientific work combines literature research, manuscript or grant writing, experiment planning, code implementation, data analysis, debugging, reproducibility checks, citation verification, figure preparation, ablation studies, daily research planning, or local research artifacts such as DOCX, PDF, LaTeX, notebooks, scripts, figures, datasets, or lab outputs.
---

# Research Engineering Suite

## Purpose

Use this as an orchestration skill for end-to-end scientific work. It routes a task across research, writing, coding, debugging, and verification without letting any one track outrun the evidence.

This skill should usually activate other focused skills instead of duplicating them. Load only the skill or reference needed for the current phase.

## Activation Boundary

Use this skill when the request crosses at least two research tracks or when the user explicitly asks for a research workflow, research engineering, paper-to-code, code-to-paper, experiment-to-paper, reproducibility, ablation, submission, or figure pipeline.

For a single atomic task, use the focused skill directly:

- One DOCX edit: use `docx` or `documents`.
- One PDF inspection: use `pdf`.
- One traceback: use `systematic-debugging`.
- One feature or bugfix: use `test-driven-development`.
- One citation check or literature review: use `academic-research-suite`.

If the user supplies a mode word such as `full`, `research`, `write`, `code`, `debug`, `figure`, `reproduce`, or `daily`, treat it as the initial dominant mode, then switch tracks only when the evidence requires it.

## Operating Rule

Always identify the current dominant mode before acting:

| Dominant mode | Typical user request | First move |
|---|---|---|
| Research | literature review, hypothesis, evidence, citations, systematic review, meta-analysis | Use `academic-research-suite`; use `life-science-research:*` or web/primary sources when domain evidence is needed. |
| Writing | paper, grant, review comments, rebuttal, abstract, outline, polish, translate | Use `academic-research-suite`; use `docx`, `pdf`, `latex-tectonic`, `presentations`, or `spreadsheets` when the artifact requires it. |
| Coding | implement method, run experiment, analyze data, build pipeline, write scripts | Use `test-driven-development` for behavior changes; inspect the repo before editing; prefer existing project patterns. |
| Debugging | traceback, failed test, wrong result, broken service, reproducibility failure | Use `systematic-debugging`; reproduce and isolate before fixing. |
| Verification | "is this correct", final check, before completion, CI, manuscript integrity | Use `verification-before-completion`; tie claims to sources, tests, artifacts, or explicit uncertainty. |
| Figure | prepare panels, plots, schematics, figure legends, visual provenance | Verify source data, plotting code, export settings, labels, and manuscript references. |
| Reproduce | reproduce results, run ablations, sweep parameters, compare variants | Isolate runs, pin seeds and environment, record commands and machine-readable outputs. |
| Daily | plan today's research work, checkpoint progress, summarize next step | Choose one reviewable unit of work, preserve a traceable checkpoint, and log result/surprise/next action. |

If multiple modes apply, sequence them in this order unless the user gives a stricter order:

1. Intake and artifact inspection.
2. Evidence or failure-state collection.
3. Plan only as much as needed to execute.
4. Implement, write, or revise.
5. Verify against the original request.
6. Report outputs, limits, and next usable artifact.

## Intake

For non-trivial scientific tasks, establish the minimum viable frame:

- Objective: what decision, manuscript section, experiment, code path, or artifact must change.
- Inputs: exact paths, datasets, papers, drafts, figures, commands, logs, environment, and constraints.
- Output: answer, edited file, code patch, experiment plan, figure, table, review, or reproducibility report.
- Evidence standard: primary literature, official docs, local artifacts, tests, quantitative checks, or reviewer-style reasoning.
- Risk: what would make the result misleading if unchecked.

Ask a concise clarification only when a wrong assumption would materially change the result. Otherwise inspect the available files, repo, logs, or sources directly.

## Research Track

Use this track when the work depends on external knowledge, literature, datasets, scientific claims, or citation integrity.

Procedure:

1. Convert broad topics into answerable research questions before drafting conclusions.
2. Separate evidence, inference, and recommendation.
3. Prefer primary or authoritative sources for claims, policies, statistics, APIs, and current facts.
4. Never fabricate references, DOIs, journal policies, author names, dates, sample sizes, or effect sizes.
5. When sources conflict, state the conflict and explain which source has stronger authority for the specific claim.
6. For life-science work, route database lookups through the relevant `life-science-research:*` skill when useful.
7. For literature-heavy work, maintain a compact evidence matrix: claim, source, method/population/system, key result, limitation, confidence.

Use web browsing when the user asks for latest/current facts, exact citations, policies, datasets, software behavior, or when there is a meaningful chance memory is stale.

## Writing Track

Use this track for papers, grant text, peer review, rebuttal, abstracts, outlines, cover letters, figure legends, slides, DOCX/PDF/LaTeX artifacts, and polished scientific prose.

Procedure:

1. Preserve the user's requested format, target venue, language, and concision level.
2. If the research question is vague, route to `academic-research-suite` scoping before outlining or drafting.
3. Build the argument from claims that can be supported, not from desired conclusions.
4. Keep reviewer-facing criticism concrete: novelty, method, controls, statistics, writing structure, interpretation, reproducibility, and missing evidence.
5. For revisions, maintain a trace from each reviewer concern to the manuscript change or response.
6. For DOCX/PDF/LaTeX/PPTX/XLSX work, use the corresponding file skill and verify the rendered or parsed artifact when feasible.
7. For Chinese editing, match the user's script and tone unless they request another style.

Avoid expanding concise user documents into verbose prose unless the user asks for a fuller version.

## Coding Track

Use this track when scientific work requires scripts, repository edits, notebooks, data processing, model training, simulation, visualization, or pipeline automation.

Procedure:

1. Inspect the repository and existing conventions before proposing implementation.
2. Define the behavior being changed and the smallest test or check that would catch a regression.
3. Use `test-driven-development` for features, bug fixes, refactors, and behavior changes unless the task is explicitly exploratory or generated/config-only.
4. Keep edits scoped to the relevant module, data path, or experiment.
5. Prefer structured parsers and project helpers over ad hoc string manipulation.
6. Preserve user data and source artifacts; default to non-destructive outputs unless overwrite is requested.
7. Record exact commands, parameters, input paths, and output paths for reproducibility.

For experiments, distinguish:

- Code correctness: does the implementation do the intended computation.
- Scientific validity: does the method answer the research question.
- Reproducibility: can the same command, seed, environment, and data reproduce the result.

## Debugging Track

Use this track when behavior is wrong, tests fail, tracebacks appear, services break, figures look incorrect, or results are scientifically implausible.

Procedure:

1. Reproduce or directly inspect the current failure state.
2. Capture the exact error, command, input, output, environment, listener/port, or artifact mismatch.
3. State the observed facts before hypothesizing.
4. Form the smallest falsifiable hypothesis.
5. Test that hypothesis with a targeted command, log check, unit test, visual check, or data assertion.
6. Patch the smallest root cause, not a broad rewrite.
7. Re-run the failing check and at least one nearby regression check.

For visual/data debugging, split source-data correctness from rendering, scaling, contrast, coordinate transforms, and export pacing. Do not defend a coordinate assumption before verifying it against the actual artifact.

## Figure Track

Use this track when the task involves paper figures, plots, schematics, visual panels, figure legends, screenshots, volume rendering, projection images, or provenance of visual outputs.

Procedure:

1. Identify whether the figure is data-derived, schematic, screenshot, rendering, or mixed.
2. Trace every data-derived panel back to its source file, command, parameter set, and processing step when feasible.
3. Check that visual correctness is not being substituted for provenance; a figure that looks plausible may still come from the wrong source, crop, scale, or version.
4. Separate source-data validity from plotting/rendering choices: axis scaling, contrast, projection, color mapping, labels, panel order, export size, and compression.
5. Prefer vector export for line art and plots when the target venue allows it; use sufficient DPI for raster panels.
6. Keep figure legends synchronized with the data, code, and manuscript claims.

For generated or edited images, use the image generation/editing tool only when the user wants visual creation or transformation. Do not use generated imagery as scientific evidence.

## Reproduction Track

Use this track for reproducing published or internal results, ablations, parameter sweeps, re-running experiments, benchmarking, or comparing method variants.

Procedure:

1. Define the exact claim or result to reproduce before running anything.
2. Record data version, code commit, command, parameters, seed, environment, hardware when relevant, and output path.
3. Use isolated branches, worktrees, output directories, or run IDs when variants could overwrite each other.
4. Store tabular results in machine-readable formats such as CSV, JSON, Parquet, or clearly structured logs.
5. Distinguish failure modes: code did not run, code ran but result differs, result matches numerically but not scientifically, or artifact export differs.
6. Summarize ablations with the changed factor, controlled factors, metric, uncertainty/statistics, and interpretation.

## Daily Track

Use this track when the user asks for daily research planning, lab workflow, project continuation, or a compact checkpoint.

Procedure:

1. Pick one primary task that can be finished and reviewed in the available work session.
2. Define the intended artifact: patch, experiment result, table, figure, paragraph, review note, or decision.
3. Prefer a traceable checkpoint such as a commit, saved output folder, run manifest, or concise log entry over an untracked temporary state.
4. End with result, surprise, blocker, and next action.

## Verification Gate

Before claiming the task is complete:

- Check that the output answers the latest user request, not an earlier interpretation.
- Link major claims to citations, local files, tests, commands, or measured outputs.
- Run the relevant test, parser, renderer, linter, command, or artifact inspection when feasible.
- If verification is not feasible, say exactly what was not verified and why.
- Preserve any useful output path, command, or parameter set in the final response.

Use `verification-before-completion` for substantial code, manuscript, document, or experiment deliverables.

## General Quality Gate

Before delivering a substantial artifact, check these five dimensions:

| Gate | Check |
|---|---|
| Reproducible | Commands, seeds, environment, data version, and output paths are sufficient to re-run or audit. |
| Verifiable | At least one test, source check, parser, renderer, assertion, or measurement supports the result. |
| Interpretable | The answer explains why the chosen method or revision addresses the scientific question. |
| Traceable | Important changes, claims, figures, or runs can be traced to files, commits, sources, or parameters. |
| Clean | No stale TODOs, debug prints, unused placeholders, hardcoded temporary paths, or leftover instrumentation in the deliverable. |

## Project Context Awareness

This skill is project-agnostic. Do not hardcode any specific project path, dataset, method, bug list, or lab convention into the skill.

When working inside a project, absorb project context in this order:

1. Direct user request and explicit constraints.
2. Current repository instructions such as `AGENTS.md`, `CLAUDE.md`, `README`, configuration files, and existing code conventions.
3. Available memory or project notes when the active environment provides them.
4. Current files, logs, artifacts, and command outputs.
5. This skill's default workflow.

If project instructions conflict with this skill, follow the user's current instruction and the project's local rules unless they would make the result unverifiable or destructive.

## Cross-Track Handoffs

Consider these handoffs when evidence from one track changes the next step:

- Research to Writing: convert a narrowed question and evidence matrix into an outline, argument, or reviewer response.
- Research to Coding: convert a method claim into a testable implementation target or experiment design.
- Coding to Writing: convert confirmed experiment outputs into Methods, Results, figure legends, or limitations.
- Coding to Debugging: switch immediately when a run fails, output is implausible, or behavior differs from the defined check.
- Debugging to Coding: add or update a regression test after a root cause is fixed.
- Figure to Writing: update captions, panel references, and claims when a panel changes.
- Reproduction to Research: revisit literature or assumptions when reproduced results conflict with expected claims.

## Skill Routing Map

Activate these specialized skills when the condition matches:

| Need | Skill |
|---|---|
| Research question, literature review, citation checks, peer review, paper pipeline | `academic-research-suite` |
| Biology, chemistry, genomics, proteins, drugs, trials, biomedical databases | `life-science-research:*` |
| Feature, bugfix, refactor, scientific code behavior change | `test-driven-development` |
| Traceback, failed run, unexpected result, broken local service | `systematic-debugging` |
| Final proof before saying complete | `verification-before-completion` |
| Word document creation/editing/review | `docx` or `documents` |
| PDF reading/editing/review | `pdf` |
| LaTeX compile and paper build verification | `latex-tectonic` |
| Presentation deck work | `pptx` or `presentations` |
| Spreadsheet/data table work | `xlsx` or `spreadsheets` |
| GitHub PR, issue, CI, review comments | `github:*` |
| Hugging Face models, datasets, Spaces, jobs, evaluations | `hugging-face:*` |
| Browser/local web UI verification | `playwright` or `browser-use:browser` |
| Figures, plots, panels, or image-derived artifacts | Use project plotting tools, `python`/notebooks when appropriate, image tools only for visual creation/editing, and verify provenance separately. |
| Reproduction, ablation, parameter sweeps | Use isolated git branches/worktrees when useful, structured run manifests, and `verification-before-completion`. |

## Anti-Patterns

Do not:

- Draft a polished paper from a vague topic without first narrowing the research question.
- Invent citations or reuse a citation without checking that it supports the claim.
- Debug from guesses when logs, tests, source files, or artifacts can be inspected.
- Make broad rewrites when a minimal traceback-driven fix is available.
- Skip planning entirely when the task crosses research, writing, code, and artifact boundaries.
- Delete unfamiliar code without inspecting history, call sites, or tests.
- Leave debug instrumentation, temporary hardcoded paths, stale TODOs, or throwaway output assumptions in the final artifact.
- Use mock data as a substitute for real experimental evidence, except for narrow unit tests.
- Claim statistical significance without a defined statistical check.
- Claim completion without a verification step.
- Overwrite research data, figures, drafts, or generated outputs unless the user explicitly asked.
- Treat visual similarity as provenance when exact source tracing is possible.
- Expand concise user writing into long prose unless the user asked for a fuller version.

## Final Response Shape

Keep final responses concise and useful:

- Say what changed or what was found.
- Name the key output files or commands.
- State the verification performed.
- State residual uncertainty only when it affects use of the result.

For research and writing deliverables, separate evidence-backed conclusions from recommendations. For code/debug deliverables, separate root cause, fix, and verification.
