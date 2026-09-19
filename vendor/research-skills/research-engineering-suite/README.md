# Research Engineering Suite for Codex

[![Version](https://img.shields.io/badge/version-v0.2.0-blue)](VERSION)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Codex%20Skill-111827)](SKILL.md)
[![GitHub](https://img.shields.io/badge/GitHub-JoeyJin--NJU-black?logo=github)](https://github.com/JoeyJin-NJU/research-engineering-suite)

English | [简体中文](README.zh-CN.md)

Most research work does not fail because one step is impossible. It fails because the steps stop talking to each other.

A literature claim drifts away from the code that produced the result. A figure looks right, but nobody can say which data file and parameters made it. A bug gets patched before the failure is understood. A manuscript sentence reads well, but the evidence behind it is thin.

`Research Engineering Suite` is a Codex skill for keeping those pieces tied together.

It gives Codex a research engineering workflow: when to search, when to write code, when to stop and debug, when to trace a figure back to its source, and when to admit that the result has not been verified.

This skill is less about one specific tool and more about order. What to inspect first. What to write second. When to continue. When to stop.

## Why this exists

Many research requests look like one task and behave like a chain of dependencies.

"Write the Methods" may require checking the command, parameters, and output files first.

"This figure looks wrong" may have nothing to do with plotting style; the issue may be data, coordinates, projection, contrast, or export.

"Respond to these reviewer comments" may require new experiments, revised figures, citation checks, and a different argument.

"The pipeline finished" does not mean the result is scientifically valid or reproducible.

Without a workflow, an agent can compress all of that into a fluent answer. Fluent is not enough.

`Research Engineering Suite` routes the task back into the right sequence:

- Evidence before polish.
- Reproduction before revision.
- Failure state before fix.
- Provenance before figure tweaks.
- Verification before completion claims.

## How it works

```text
Intake
  ↓
Evidence or failure-state collection
  ↓
Minimal plan
  ↓
Research / Writing / Coding / Debugging / Figure / Reproduction / Daily
  ↓
Verification gate
  ↓
Report or artifact
```

This is not ceremony. A single DOCX edit, PDF check, traceback, or citation lookup should go straight to the focused skill. `research-engineering-suite` is useful when the task crosses boundaries between research, writing, code, figures, reproduction, and verification.

See [docs/ARCHITECTURE.zh-CN.md](docs/ARCHITECTURE.zh-CN.md) for the detailed workflow.

## Tracks

| Track | Use it for | What it watches |
|---|---|---|
| Research | literature, hypotheses, citations, systematic review, fact checks | answerable research questions and claim-source alignment |
| Writing | papers, grants, reviews, rebuttals, abstracts, figure legends | whether the text matches evidence, figures, and audience |
| Coding | experiment scripts, data analysis, model training, pipelines | defined behavior, tests, and reproducible commands |
| Debugging | tracebacks, failed tests, wrong outputs, broken services | facts before hypothesis |
| Figure | plots, panels, schematics, captions, visual outputs | source data, parameters, export settings, and provenance |
| Reproduction | reproduced results, ablations, sweeps, method comparisons | seeds, environments, commands, outputs, and structured results |
| Daily | daily research planning, checkpoints, continuation | one reviewable unit of work and a next action |
| Verification | final checks, CI, artifact review, citation integrity | whether claims are supported by sources, tests, commands, or artifacts |

## Try it on a real task

```text
Use $research-engineering-suite to turn these experiment outputs into Methods and Results.
Check the commands, parameters, output files, and figures before drafting.
```

```text
Use $research-engineering-suite to debug this training run.
Do not patch first. Inspect logs, inputs, outputs, and the relevant functions.
```

```text
Use $research-engineering-suite to handle these reviewer comments.
Separate new experiments, figure changes, citation checks, and text-only responses.
```

```text
Use $research-engineering-suite to design an ablation plan.
I need every variant tied to a seed, parameters, result table, and final figure.
```

```text
Use $research-engineering-suite to verify this figure.
I care more about source data and parameters than whether the panel looks plausible.
```

More examples are in [examples/prompts.zh-CN.md](examples/prompts.zh-CN.md).

## What changes when you use it

| Asking Codex directly | Using this skill |
|---|---|
| Fast answer | First decide whether the task is research, code, debug, figure, writing, reproduction, or a mix |
| Polished claim | Claim must trace to a citation, experiment, file, command, or measurement |
| Guess at the bug | Reproduce or inspect the failure before hypothesizing |
| Accept a plausible figure | Check source data, parameters, export settings, and caption |
| Stop when code runs | Separate code correctness, scientific validity, and reproducibility |
| Finish with a subjective "looks done" | Pass through a verification gate |

It does not turn Codex into a domain expert. It makes Codex follow the dependencies that serious research work already has.

## Install

Windows PowerShell:

```powershell
git clone https://github.com/JoeyJin-NJU/research-engineering-suite.git "$env:USERPROFILE\.codex\skills\research-engineering-suite"
```

Update:

```powershell
cd "$env:USERPROFILE\.codex\skills\research-engineering-suite"
git pull
```

Custom `CODEX_HOME`:

```powershell
git clone https://github.com/JoeyJin-NJU/research-engineering-suite.git "$env:CODEX_HOME\skills\research-engineering-suite"
```

Then start a new Codex session and ask:

```text
Use $research-engineering-suite to handle this research task.
```

## Repository layout

```text
research-engineering-suite/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── docs/
│   ├── ARCHITECTURE.zh-CN.md
│   └── SETUP.zh-CN.md
├── examples/
│   └── prompts.zh-CN.md
├── README.md
├── README.zh-CN.md
├── VERSION
└── LICENSE
```

[SKILL.md](SKILL.md) is the actual Codex skill. The README is for humans.

## What it will not do

It will not replace experiments, domain judgment, statistical design, or citation checks. It should not invent DOIs, treat generated images as scientific evidence, or assume that a finished run proves a conclusion.

If evidence is missing, it should stop.

If figure provenance is unclear, it should trace it.

If verification has not run, it should not claim the work is done.

## License

MIT. See [LICENSE](LICENSE).
