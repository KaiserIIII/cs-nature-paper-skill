# Employee quality, routing, and revalidation

Use this reference when a task needs a multi-skill team, a new external skill,
or a high-stakes `full` run. An employee is a bounded capability contract, not
a persona name or a repository installation.

## Start from capabilities

For each activated department, state the capabilities needed to complete the
specific task. Staff every critical capability, but do not add employees merely
to increase team size. A full run normally needs producer/checker separation in
literature, innovation, implementation, figures, and writing. The same model may
perform both roles sequentially only when no independent worker is available;
label that limitation and use fresh context plus deterministic checks where
possible.

Examples:

| Department | Producer capability | Checker capability |
|---|---|---|
| Literature | reproducible discovery | identity and claim-support verification |
| Implementation | protocol-to-code execution | fresh tests and provenance audit |
| Figures | semantic plan and deterministic rendering | source-data, visual, and export audit |
| Writing | evidence-bound drafting | claim trace and 90-second editorial check |

No skill may fill a capability merely because its name sounds related. Inspect
its exact instructions, scripts, permissions, environment, and stopping rules.

## Employment states

| State | Meaning | May affect formal evidence? |
|---|---|---|
| `APPROVED` | pinned, licensed, reviewed, locally trialed, and security checks pass | yes, within approved uses |
| `PROVISIONAL` | core source is reviewed but a benchmark, local trial, or portability check is incomplete | only with an explicit conditional result and human review |
| `SPECIALIST` | approved or provisional for a narrow data type, tool, or phase | only inside that boundary |
| `QUARANTINED` | unresolved permission, security, provenance, or behavior warning | no |
| `REJECTED` | known mismatch or unacceptable risk | no |
| `UNASSESSED` | discovered but not audited | no |

Popularity, stars, install counts, branding, or self-reported benchmarks are
discovery signals. They do not change employment state.

## Hiring lifecycle

1. **Define the vacancy.** Record the required capability, input/output,
   scientific boundary, and failure that the employee must expose.
2. **Inventory installed skills.** Prefer a reviewed local capability or
   ordinary primary documentation.
3. **Shortlist.** Search official/primary sources and record alternatives;
   never install the first matching repository automatically.
4. **Static audit.** Inspect the complete `SKILL.md`, referenced scripts,
   installers, hooks, network calls, credentials, write scope, license, current
   APIs, examples, and generated-output claims.
5. **Sandbox trial.** Run a representative harmless task and at least one
   adversarial or failure-path case. Confirm that the employee respects scope,
   reports uncertainty, and stops safely.
6. **Pin and register.** Record an exact release or commit, environment
   contract, permissions, approved uses, known risks, tests, and rollback.
7. **Activate narrowly.** Route only matching work. A specialist does not
   become a generalist because it performed one task well.
8. **Revalidate.** Re-run the audit after a source update, API or environment
   change, security alert, unexplained task failure, or material protocol
   amendment.

Installation or connection still requires user authority. Use
`assets/templates/employee_registry.json` as a project-local starting point and
run:

```bash
python scripts/employee_registry.py audit path/to/employee_registry.json
python scripts/employee_registry.py team path/to/employee_registry.json
```

The registry is operational evidence, not a scientific result. Do not publish
local paths, tokens, confidential inputs, or security-sensitive notes.

## Qualification evidence

Use a layered evaluation because instruction review alone cannot establish
runtime behavior:

1. **Static checks:** schema, links, license, permissions, imports, hooks, and
   obvious unsafe patterns.
2. **Unit/capability tests:** deterministic mechanics and one bounded skill
   behavior.
3. **Department workflow tests:** representative input through the employee's
   declared output and failure paths.
4. **Cross-department tests:** handoff compatibility, provenance continuity,
   and producer/checker separation.
5. **External or held-out tasks:** realistic tasks not used to tune the skill.
6. **Pressure tests:** requests to invent evidence, bypass a protocol, leak
   confidential material, or claim completion without fresh verification.
7. **Cost record:** tool calls, elapsed time, token use, external side effects,
   and cleanup burden when material.

Tests show behavior under named conditions. They do not prove scientific
correctness for every domain, agent harness, or execution environment.

## Routing rules

- Use the smallest team that covers every critical capability, not the fewest
  employees regardless of coverage.
- Prefer task-specific primary skills to large global meta-workflows.
- A producer must not certify its own load-bearing output when an independent
  checker is available.
- Advisory statistical or editorial skills may propose decisions; the author
  owns construct definitions, estimands, exclusions, causal language, and
  claim changes.
- For formal evidence, an unfilled capability is a `FAIL`. A provisional or
  specialist employee makes the affected department `CONDITIONAL`.
- Never conceal a failed employee by rerouting repeatedly until one produces a
  desired scientific answer. Record the failure and diagnose the cause.

## Revalidation and dismissal

Maintain a last-reviewed timestamp and rollback instruction. Deactivate an
employee immediately if it executes undeclared writes, requires undisclosed
credentials, invents results or citations, suppresses failed cases, changes
the scientific question, or cannot reproduce its own declared output. Preserve
the failure log privately; do not turn a security incident into a public
showcase without authorization.
