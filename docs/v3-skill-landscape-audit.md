# V3 external skill landscape audit

Audit date: 2026-08-27. Exact refs are the inspected default-branch heads
obtained with `git ls-remote`; maintenance fields are GitHub repository metadata
queried on the same date. A recommendation is not an approval to install or
execute. No external repository is vendored by V3.

| Skill / exact source and ref | License / maintained | Core capability and best idea | Risks and boundary | V3 recommendation / use |
|---|---|---|---|---|
| `google-research/paper-orchestra` `ca1b3fa01c29` (`main`) | Apache-2.0; pushed 2026-05-17; active | Staged outline, literature, plotting, section writing, refinement; clear raw-materials-to-LaTeX contracts | Conda/Python stack, model/API keys, optional SMTP credentials, dataset not bundled; README claims “submission-ready” but does not certify evidence | `SPECIALIST`; learn staged writing/plotting design; dynamically delegate only after employee trial |
| `SNL-UCSB/paper-writing-skill` `676f8520bba5` (`main`) | MIT; pushed 2026-07-31; active | Introduction-Twice, rhetorical moves, compression and venue-aware editing | Claude-oriented local conventions; prose guidance cannot validate results or citations | `APPROVED` as writing design source; delegate writing only with V3 claim checker |
| `SNL-UCSB/literature-survey-skill` `18475960526b` (`main`) | MIT; pushed 2026-03-27; active | Intent -> triage -> deepen -> synthesize; three-pass reading and calibration | Requires NotebookLM MCP; source ingestion and external backend may expose private PDFs; fixed student workflow | `SPECIALIST`; design lessons only unless backend permission and trial exist |
| `Imbad0202/academic-research-skills` `30ad279cdf10` (`main`) | GitHub reports `NOASSERTION`; pushed 2026-08-27; active | Broad research -> write -> review -> revise lifecycle and many task skills | Missing SPDX license is a redistribution blocker; large surface, external services and fast-changing branches | `PROVISIONAL` for design inspection; never vendor/copy; exact skill trial required |
| `Imbad0202/academic-research-skills-codex` `7600799a4126` (`main`) | GitHub reports `NOASSERTION`; README declares CC BY-NC 4.0; pushed 2026-08-24; active | Codex-native packaging and human checkpoints | License is non-commercial and metadata is inconsistent; large suite, hooks and runtime adapter raise permission/context cost | `QUARANTINED`; design-only until license, permissions and behavior evidence are resolved; never vendor into MIT V3 |
| `K-Dense-AI/scientific-agent-skills` `36d8f13a1e75` (`main`) | MIT; pushed 2026-08-24; active | Topic skills for lookup, statistics, visualization, scientific writing and evaluation | 160+ skills, optional packages/API keys, broad scientific assumptions; some rules are too prescriptive for CS | `PROVISIONAL`; use topical specialists (`paper-lookup`, `statistical-analysis`, `scientific-visualization`) only after qualification |
| `argahv/sisyphus-academica` `5fc165211d6a` (`main`) | MIT; pushed 2026-08-01; active | Contrarian, cross-pollination, assumption excavation, adversarial personas | Ideation can inflate novelty or token cost; generated hypotheses are not evidence | `SPECIALIST`; use generators only before closest-work and feasibility gates |
| `hyl-ailab/scholar-forge` `350e382c2840` (`master`) | MIT; pushed 2026-06-25; active | Citation integrity, venue intelligence, bilingual GB/T 7714 writing | Venue data can age; metadata alone cannot prove claim support; external API dependencies | `SPECIALIST`; delegate formatting/citation checks with live-source verification |
| `joshzyj/open-scholar-skill` `f50501a94c08` (`main`) | GitHub reports `NOASSERTION`; pushed 2026-08-26; active | Open scholar plugin with paper reading/writing/review skills | No declared license at audit; plugin/host actions and external services need review | `QUARANTINED`; design inspection only until license, permissions and tests are clear |
| `voidful/academic-skills` `71e9c42c6063` (`main`) | MIT; pushed 2026-04-04; active | Cross-host academic research suite and reusable prompts | Exact skill layout and runtime contract need inspection; broad suite can duplicate V3 | `PROVISIONAL`; learn portability patterns, do not wholesale install |

## Additional sources already inspected in V2

`google-deepmind/science-skills`, `obra/superpowers`,
`trailofbits/skills`, `KuangshiAi/SciVisAgentSkills`,
`huggingface/skills`, `github/awesome-copilot`, and
`anthropics/skills` remain useful design or specialist sources as recorded in
the V2 employee audit. Their status is carried forward as `PROVISIONAL` or
`SPECIALIST`, never as automatic approval.

## Selection rules

V3 inventories installed capabilities first, defines a vacancy, then reviews
the exact commit, license, scripts/hooks, dependencies, credentials, network
and write scope, output and failure behavior, tests, maintenance, and host
portability. A skill may be `APPROVED` only after static review, a capability
trial, department workflow trial, and relevant pressure cases. Results that
affect formal evidence require a distinct checker and a rollback record.

## Adopted ideas versus rejected patterns

Adopted: progressive disclosure, intent-aware reading, staged writing,
claim-to-evidence mapping, deterministic rendering, fresh verification,
source provenance, and specialist routing. Rejected: popularity as quality,
“submission-ready” as a scientific verdict, mandatory AI-generated figures,
automatic citation insertion, unbounded multi-agent expansion, hidden API keys,
and any workflow that treats simulated reviewer votes as acceptance evidence.
