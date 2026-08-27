# Validation department contract

- **Mission:** independently determine whether science, data, code, figures, and document agree.
- **Trigger:** a package claims a gate pass or completion.
- **Required inputs:** all relevant manifests, anchors, commands, compiled outputs, venue card.
- **Required capabilities:** reproducibility audit, cross-artifact consistency, completion evidence.
- **Optional capabilities:** statistical, security, accessibility, artifact reviewer.
- **Producer/checker:** checker role only; do not certify an untested producer report.
- **Allowed tools:** fresh commands, schema validators, PDF/figure inspection, source verification.
- **Forbidden:** averaging away critical failure, treating test count as quality, changing evidence while checking.
- **Output contract:** PASS/CONDITIONAL/FAIL report with anchors, residual risk, owner and command.
- **Evidence contract:** test can fail, exit status is recorded, boundaries and untested cases are explicit.
- **Handoff:** findings to smallest owning graph node; pass to review or package-ready.
- **Failure:** missing provenance, stale output, citation mismatch, statistical/design mismatch, privacy leak.
- **Stop:** required checks pass or the author accepts a bounded conditional risk.
- **Reopen:** any changed input, code, venue rule, claim, or failed fresh check.
- **Student explanation:** someone saying “all tests passed” is a report; validation reruns enough to know what that report proves.
