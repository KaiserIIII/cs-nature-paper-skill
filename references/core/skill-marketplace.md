# Skill marketplace and employee lifecycle

## Vacancy-first routing

Define the missing capability, required inputs/outputs, permissions, runtime,
and checker need before looking for a repository. Inventory installed skills and
prefer a small topical skill over a global suite.

## Candidate audit

Record repository URL, exact commit/tag, license, maintainer activity, SKILL.md,
scripts, hooks/installers, dependencies, credentials, network endpoints,
external writes, output schema, verification and failure behavior, tests,
context/runtime cost, host portability, and rollback. README claims and stars
are discovery signals only. Never execute an unreviewed installer.

## Employment states

- `APPROVED`: static review and relevant behavior trials passed;
- `PROVISIONAL`: safe advisory use, but cannot affect formal evidence;
- `SPECIALIST`: activated only for a named domain or artifact;
- `QUARANTINED`: unresolved license, security, permission, or behavior issue;
- `REJECTED`: failed a critical check;
- `UNASSESSED`: discovered but not reviewed.

An employee registry entry includes the exact ref, allowed tools, denied tools,
environment, approved uses, risks, behavioral evidence, reviewer, review date,
and rollback path. Formal evidence needs a checker distinct from its producer
when the contract calls for separation.
