# External employee-skill audit — 2026-08-26

This is a public-safe design record for CS Nature Paper v2.1. It contains no
private manuscript, reviewer, credential, or project data. Repositories were
reviewed as candidate capability sources; none is automatically installed or
granted `APPROVED` status by this document.

## Decision method

Candidates were judged on scientific scope, exact source visibility, license
and attribution, permissions, executable scripts/hooks, environment contract,
tests/CI, external behavioral evidence, failure handling, and fit with the
claim–evidence–mechanism architecture. Stars and installation counts were used
only for discovery. Before activation, the exact skill and all referenced code
must be pinned, registered, locally trialed, and re-audited.

The strongest quantitative evidence found was the Google DeepMind technical
report: on its 67-task internal capability benchmark, reported reliability rose
from 49% to 93% for one evaluated model and from 67% to 91% for another, with
lower mean token use. Its external BioReason subsets also improved. The same
report explicitly notes missing execution-environment standardization,
inevitable coverage gaps, and limited evaluation of very long workflows. v2.1
therefore adopts layered tests and environment contracts without treating one
vendor benchmark as universal proof.

## Findings

| Source | Best role | Preliminary disposition | Why / boundary |
|---|---|---|---|
| [Google DeepMind Science Skills](https://github.com/google-deepmind/science-skills) | literature search and scientific tooling patterns | `PROVISIONAL` source; local pin/trial required | Official collection with unit, workflow, capability, and external evaluation; execution environments and coverage remain limited |
| [K-Dense scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | scientific figures, statistics, lookup, writing | `PROVISIONAL`; topical skills only | Broad scientific scope, scripts/tests/CI, strong visualization integrity rules; individual statistical advice still needs method review |
| [Superpowers](https://github.com/obra/superpowers) | debugging and fresh verification | `PROVISIONAL`; TDD is `SPECIALIST` | Strong reproduce–diagnose–verify discipline; rigid test-first rules do not fit every exploratory notebook, generated file, or legacy migration |
| [Trail of Bits skills](https://github.com/trailofbits/skills) | property-based testing, security, supply chain, modern Python | `SPECIALIST` | High-quality engineering/security practices; some skills are toolchain-specific and must not silently migrate an existing project |
| [SciVisAgentSkills](https://github.com/KuangshiAi/SciVisAgentSkills) | ParaView, napari, VMD/MDAnalysis, and TTK workflows | `SPECIALIST` | Appropriate for matching 3D/imaging modalities, not a general statistical chart department |
| [Hugging Face skills](https://github.com/huggingface/skills) | model evaluation, datasets, experiment tracking | `SPECIALIST` | Useful for matching ML/HF workflows; network, tokens, uploads, and public-by-default tracking require explicit permission and privacy checks |
| [GitHub awesome-copilot](https://github.com/github/awesome-copilot) | evidence-map validation and selected engineering helpers | `PROVISIONAL` design source | The evidence-map pattern is auditable and fail-closed; exact harness support and referenced scripts require local testing |
| [Anthropic skills](https://github.com/anthropics/skills) | PDF/DOCX/PPTX/XLSX production and inspection | `SPECIALIST` | Useful for document artifacts, not a source of scientific inference or claim validation |
| [RigorPilot Skills](https://github.com/lllllllama/RigorPilot-Skills) | research workflow candidates | `QUARANTINED` pending exact audit | High visibility, but skills.sh reports warning states for inspected candidates; no activation until code/permissions and local behavior pass |

## Adopted architecture

1. Add an employee registry with pinned version, permissions, environment,
   tests, approved uses, risks, and rollback.
2. Separate producers and checkers for load-bearing literature, code, figures,
   and prose.
3. Qualify employees with static, unit/capability, department workflow,
   cross-department, external, and pressure tests.
4. Treat debugging, TDD, property testing, mutation testing, domain imaging,
   and remote ML services as selected tools, not universal rituals.
5. Make the figure department source-data-first, deterministic, accessible,
   and audited inside the compiled manuscript.
6. Make the programming department environment-bound, pilot/formal separated,
   recoverable for long runs, and unable to claim completion without fresh
   evidence.

## Primary evidence used

- [Google DeepMind Science Skills technical report](https://storage.googleapis.com/deepmind-media/papers/google_deepmind_science_skills_for_antigravity_towards_efficient_and_reliable_scientific_workflows.pdf)
- [skills.sh public skill directory](https://www.skills.sh/) and
  [security audits](https://www.skills.sh/audits)
- Each source repository and the specific `SKILL.md`, scripts, tests, license,
  and CI material linked from it at the audit date

The audit is time-bounded. A source update does not inherit this assessment;
revalidation is required.
