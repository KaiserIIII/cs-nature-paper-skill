<p align="center">
  <img src="https://img.shields.io/badge/CS--Nature--Paper-Research%20Orchestrator-blue?style=for-the-badge&logo=academia" alt="CS Nature Paper">
</p>

# CS Nature Paper

> A single-entry research orchestrator for planning, writing, validating, and reviewing computer-science papers with Codex or Claude Code.

[中文说明](README_zh.md) · [License](LICENSE)

## What it does

CS Nature Paper acts as a "research CEO": it discovers available academic skills, installs missing capabilities when permitted, delegates work across seven specialized departments, and validates each stage before delivery.

```text
Literature → Novelty → Implementation → Figures → Writing → Validation → Review → Delivery
```

Use it for a complete paper pipeline or for a focused task such as novelty discovery, experiment planning, manuscript revision, or simulated peer review.

## Installation

### Codex

```bash
git clone https://github.com/KaiserIIII/cs-nature-paper-skill.git ~/.codex/skills/cs-nature-paper-skill
```

### Claude Code

```bash
git clone https://github.com/KaiserIIII/cs-nature-paper-skill.git ~/.claude/skills/cs-nature-paper
```

Restart the agent if it does not discover the skill immediately.

## Example requests

```text
Write a NeurIPS-style paper about an improved Transformer architecture.
Find novel directions for distributed database query optimization.
Review this systems paper as if it were submitted to OSDI.
Polish this manuscript, reduce it to ten pages, and remove generic AI phrasing.
```

## Seven-department pipeline

| Department | Responsibility | Typical capabilities |
|---|---|---|
| Literature | Search, citation verification, related work | deep-research, paper-lookup, literature-review |
| Novelty | Hypothesis generation and contribution scoring | sisyphus-academica |
| Implementation | Code, experiments, reproducibility package | PaperOrchestra, statistical-analysis |
| Figures | Scientific plots and CS diagrams | scientific-visualization, Python/R |
| Writing | Venue-aware manuscript drafting | academic-paper, scholar-forge, scientific-writing |
| Validation | Integrity, consistency, and quality gates | academic-pipeline, scholar-evaluation |
| Review | Multi-perspective simulated peer review | academic-paper-reviewer |

## Field and venue coverage

ML/AI · Systems · Theory · Security · Networking · PL/Compilers · Databases · HCI · Vision

Common targets include NeurIPS, ICML, ICLR, OSDI, SOSP, NSDI, STOC, FOCS, SODA, CCS, IEEE S&P, USENIX Security, SIGCOMM, PLDI, POPL, SIGMOD, VLDB, CHI, UIST, CVPR, ICCV, and SIGGRAPH.

## How orchestration works

1. Inventory installed academic skills.
2. Request or install missing capabilities according to the host agent's permissions.
3. Route the task through only the departments it needs.
4. Apply stage-specific quality checks.
5. Deliver the manuscript, figures, code, and reproducibility materials requested by the user.

## Important notes

- Review any third-party skill before allowing installation or execution.
- Generated citations must be verified against primary bibliographic sources.
- Human authors remain responsible for claims, authorship, disclosure, and venue compliance.

## License

MIT License. See [LICENSE](LICENSE).
