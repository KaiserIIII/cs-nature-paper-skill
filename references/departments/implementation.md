# Implementation and experiment department contract

- **Mission:** execute a frozen, decision-relevant design and produce fresh evidence.
- **Trigger:** feasibility is `GO`, `GO_WITH_SCOPE_REDUCTION`, or `PILOT_FIRST`.
- **Required inputs:** protocol, experiment decision matrix, environment and data access.
- **Required capabilities:** protocol-to-code, root-cause debugging, statistics, fresh verification, recoverable jobs.
- **Optional capabilities:** ML tracking, domain simulator, security/property testing.
- **Producer/checker:** implementer/runner and independent verifier for formal outputs.
- **Allowed tools:** project-native package manager, approved local/remote compute, deterministic scripts.
- **Forbidden:** promoting pilot outcomes, overwriting formal outputs, claiming tests prove a construct, hidden dependencies.
- **Output contract:** code diff, environment contract, run manifest, logs, raw/processed outputs, failure registry.
- **Evidence contract:** command, exit status, commit, config, environment, input hash, output hash, label and uncertainty.
- **Handoff:** formal artifacts to figures/writing; anomalies to debugging and methods check.
- **Failure:** timeout, partial run, missing input, dependency drift, seed/config mismatch, unexplained result.
- **Stop:** every decision-matrix priority has a verified result or an explicit unresolved boundary.
- **Reopen:** fresh verification fails, protocol amendment, anomalous result, or claim/evidence mismatch.
- **Student explanation:** a script finishing is not the same as a valid experiment; we keep the exact command and what it actually tested.
