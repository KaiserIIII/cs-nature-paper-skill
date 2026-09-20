# V4.1 specialist runtime implementation plan

## Goal

Make the approved PaperSpine and Nature Figure/Reviewer resources genuinely callable offline while preserving the existing fail-closed qualification gates. The release must distinguish advisory execution from formal scientific evidence eligibility.

## Constraints

- Import only selected files from the pinned upstream commits; do not copy either repository wholesale.
- Preserve upstream MIT/Apache-2.0 license notices and record exact source paths, commit, and selected-bundle hashes.
- Do not install or implement AREX, Curie, CORAL, SkillLens, or POPPER beyond their already-approved discovery scope.
- PUBLIC_CORE must work without network or credentials; PRIVATE_ULTRA may mirror the same bounded runtime but cannot bypass qualification.
- Keep `assets/registry/v41_provider_qualification.json` pending until independently checked behavior evidence exists.
- Preserve unrelated existing edits, including `.github/workflows/ci.yml`.

## Implementation steps

1. Add failing contract and end-to-end tests for selected-resource integrity, adapter discovery, six capability entrypoints, PUBLIC_CORE offline execution, typed outputs, and missing-resource fail-closed behavior.
2. Materialize the minimum upstream PaperSpine and Nature files under `vendor/selected/v41/`, with license/attribution metadata and a generated source manifest.
3. Implement `scripts/v41_provider_adapters.py` as a deterministic local adapter layer. Each method delegates to the selected upstream script/resource where safe, normalizes the result into a typed advisory artifact, and never asserts formal readiness.
4. Extend the V4.1 registry/schema with local resource paths, adapter entrypoints, selected-bundle source hashes, explicit input/output contracts, offline permissions, and advisory status.
5. Add capability-runtime discovery/invocation through a single public `invoke_provider()` entrypoint and integrate it with existing V4.1 provider resolution without weakening formal routing.
6. Add behavior benchmark fixtures and a real executable benchmark that records candidate and PUBLIC_CORE output hashes, but leave qualification bundles empty until an independent checker can validate them.
7. Add the actual capability inventory/audit report, including PUBLIC_CORE/PRIVATE_ULTRA paths and explicit unavailable/qualification states.
8. Run targeted tests, full suite, manifest/release validation, and fresh E2E tests in the worktree, installed local skill, and F: `PRIVATE_ULTRA` mirror.
9. Request an independent code review, address findings, publish the merged main release, and synchronize both local installations from the merged tree.

## Acceptance criteria

- Every requested capability has a real local entrypoint and executes on a synthetic fixture.
- The E2E tests fail if upstream resources, contracts, or adapter routing disappear.
- PUBLIC_CORE execution is offline and produces non-placeholder advisory artifacts.
- Formal resolution still falls back until source-bound independent qualification evidence is present.
- GitHub main, local install, and F: PRIVATE_ULTRA contain the same released public tree; private-only material remains confined to F:.
