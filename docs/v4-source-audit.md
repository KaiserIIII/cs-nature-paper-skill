# V4 Third-Party Source Audit

Audit date: 2026-09-07. HEADs were resolved with `git ls-remote`; source trees
were downloaded as immutable GitHub commit archives. No repository was cloned
or installed.

All seven vendored repositories had the same current HEAD as the pinned archive
at audit time and contained an MIT license. The selected Skill directories were
copied completely, including local references, scripts, and assets. Static
review records scripts that can launch subprocesses or make network requests;
vendoring does not authorize those operations and the internal runtime loads the
Skill as inert guidance by default.

| Repository | Current HEAD | License | Decision |
|---|---|---|---|
| K-Dense-AI/scientific-agent-skills | `1e5eeffbdad3749125afe7ab48a39694e27f181c` | MIT | Selected bounded subtrees |
| JoeyJin-NJU/research-engineering-suite | `670d0be50c52595f9e13b684ebd995dff5831fb7` | MIT | Vendor complete Skill |
| osteele/agent-skills | `290d9680060b5446567e502206233645c2d91758` | MIT | Vendor research-lab-notebook |
| eins78/agent-skills | `acd4988e911965b98295e6fb6eec202ce3d4a376` | MIT | Vendor lab-notes |
| SNL-UCSB/paper-writing-skill | `676f8520bba54208eb4fe1d41620e365d9af6a24` | MIT | Vendor complete Skill |
| argahv/sisyphus-academica | `5fc165211d6a0c8f1a4ff1243311314ad26847b8` | MIT | Vendor four bounded roles |
| jeonnoin-alt/Eureka | `9f3d28a14b0b35010d8da6f2116aa3b4b8b790ff` | MIT | Vendor four rigor roles |
| Imbad0202/academic-research-skills-codex | `925975e933a20893b81681d925a3404e3b7f73b7` | CC BY-NC 4.0 | Do not vendor |
| Imbad0202/academic-research-skills | `6b7ee6dcae29c0fbb46e0017538f9cef84c3136b` | CC BY-NC 4.0 | Benchmark-only; do not vendor |
| Imbad0202/experiment-agent | `e291e7dc7ca268b2de7e1a9cf23bc2eef5dc0651` | CC BY-NC 4.0 | Do not vendor |

The requested K-Dense `scientific-brainstorming` directory was absent at the
pinned commit. V4 uses K-Dense `hypothesis-generation` plus Sisyphus
assumption, counterfactual, method, and skeptic Skills as the permissive
replacement. The runtime does not infer capability from repository names; each
entry has an explicit mapping and a local behavior trial.
