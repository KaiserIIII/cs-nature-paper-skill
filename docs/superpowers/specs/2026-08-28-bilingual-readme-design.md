# Bilingual README Design

Date: 2026-08-28
Target release: v3.1.1

## Objective

Make the GitHub repository homepage a complete, approachable introduction to
CS Nature Paper V3.1.1 in both English and Chinese. A reader should be able to
understand what the project is, how it works, how the repository is organized,
how to install and invoke it, and what its validation does and does not prove.

## Files and Navigation

- `README.md` is the default English GitHub landing page.
- `README_zh.md` is the equivalent Chinese landing page.
- Both files begin with reciprocal language links and use the same section
  order, examples, version, commit, and validation statements.
- The existing MIT license and historical branch links remain discoverable,
  but release-candidate wording is removed from installation guidance.

## Content Contract

Each README contains:

1. A plain-language project position and non-goals.
2. A compact control-plane/execution-plane workflow diagram.
3. A directory map covering the entrypoint, references, assets, scripts,
   tests, documentation, and CI.
4. The seven dynamically activated departments.
5. The private research-state files and migration precedence.
6. The `DECLARED`, `OBSERVED`, and `VERIFIED` evidence levels.
7. Pinned installation instructions for the stable `v3.1.1` tag and expected
   commit `081aa693b907d8cc07104d1b8251d46301094ef7`.
8. A natural-language `$cs-nature-paper` example, operating modes, and a
   minimal PowerShell CLI workflow.
9. Validation status and explicit scientific and operational boundaries.

## Accuracy Boundaries

- Synthetic end-to-end execution is described only as `HARNESS_SELF_TEST`.
- Model-backed behavior evaluation remains `NOT_RUN` and is never presented as
  a real model evaluation.
- Tests and CI demonstrate bounded software behavior, not scientific truth,
  novelty, venue acceptance, or a Nature/top-conference guarantee.
- Live venue rules, paywalled sources, external skills, credentials, uploads,
  releases, and submissions require activation-time verification or explicit
  author authorization.

## Verification and Publication

The implementation will check reciprocal links, matching headings and factual
markers, stale RC installation wording, rendered Markdown structure, release
validation, and the full Python test suite. Only the two READMEs and this design
record are in scope. After verification, the documentation branch will be
committed and pushed to `main` without moving or recreating `v3.1.1`.
