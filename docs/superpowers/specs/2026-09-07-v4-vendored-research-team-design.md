# CS Nature Paper V4 Vendored Research Team Design

## Goal

Upgrade the accepted `6f13161601854763b500cdb596dbe52df3a0fd19` baseline to
V4.0.0 on `feat/v4-vendored-research-team`. V4 must have a usable offline
research team built from audited third-party Skills at immutable commits while
keeping the existing control plane authoritative.

## Architecture

V4 has four separate layers:

1. The existing control plane owns graph transitions, evidence status,
   protocol state, security, authorization, and final readiness.
2. An internal specialist pack maps fourteen publication roles to operating
   contracts and vendored Skills. Each contract defines decisions, quality
   criteria, forbidden actions, outputs, and checker requirements.
3. Provider runtime resolves vendored internal specialists before host or
   external providers. Specialized work may trigger
   `QUALITY_UPGRADE_DISCOVERY`, but failed or inferior discovery falls back to
   the internal specialist.
4. Publication assessment evaluates scientific validity, evidence sufficiency,
   publication sufficiency, reviewer completeness, and submission readiness as
   distinct gates. Failure at publication breadth produces an expansion plan.

## Vendoring

Only source archives tied to an exact 40-character commit are eligible. The
audit reads the repository license, subtree contents, scripts, references, and
assets. MIT-licensed candidates may be copied with their required resources and
license. Missing, unclear, non-commercial, or no-derivatives licenses fail
closed and remain optional online candidates.

`vendor/research-skills/THIRD_PARTY_MANIFEST.json` records source repository,
source path, exact commit, license, redistributed files, modifications,
security audit, behavior trial, capabilities, and assigned specialists.
`THIRD_PARTY_NOTICES.md` preserves attribution and license locations.

The selected initial pack is intentionally bounded: K-Dense scientific Skills
for literature, ideation, design, data, statistics, visualization, writing, and
review; Research Engineering Suite for orchestration and implementation;
Research Lab Notebook for durable experiment provenance; and permissive
writing/research-rigor Skills only when they add a concrete capability.

## Provider Decisions

Every formal decision records the internal baseline, discovery status,
comparison, selected provider, and fallback. Outcomes are
`INTERNAL_BETTER`, `EXTERNAL_BETTER`, `COMPLEMENTARY`, `UNVERIFIED`, and
`FALLBACK_BUILT_IN`.

Ordinary file work, basic Python, descriptive summaries, and standard paired
bootstrap analysis use the internal team without discovery. Novelty audits,
specialized methods, and publication-grade manuscript/reviewer work trigger
quality-upgrade discovery when allowed. Discovery cannot block an available
internal specialist and cannot grant graph truth authority.

## Offline Execution

The runtime loads the complete vendored Skill resource, resolves its local
references, emits a typed invocation record, and delegates reasoning or scripts
under the existing evidence and checker contracts. It never clones or downloads
a Skill at runtime. Offline E2E tests must execute literature, statistics,
writing, review, and research-engineering routes and prove the loaded resource
comes from `vendor/research-skills`.

## Publication Gates

Scientific validity asks whether the bounded claims are supported. Evidence
sufficiency asks whether load-bearing claims have traceable evidence.
Publication sufficiency asks whether the study is broad and deep enough for the
declared article type and venue ambition. Reviewer completeness checks novelty,
domain, methods, statistics, experimental breadth, reproducibility, and
adversarial review. Submission readiness requires every preceding gate to pass.

Research depth is assessed from dataset coverage, model and baseline breadth,
ablations, external validity, mechanism tests, related work, manuscript depth,
and reproducibility. Repetition count cannot substitute for breadth.

The `ccta_tta` field regression must preserve bounded scientific validity while
returning publication sufficiency `FAIL` and `EXPAND_RESEARCH` for its known
breadth and mechanism defects.

## Compatibility And Release Boundary

Active runtime metadata becomes `4.0.0`; explicit legacy readers continue to
accept historical state where migration is already supported. V4 validation
checks the vendored manifest, licenses, contracts, offline loading, provider
decisions, publication gates, regression fixture, and existing V3.2.1 behavior.
The branch is not merged, tagged, released, or externally published.

