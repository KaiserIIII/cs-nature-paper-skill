# Host Provider execution and handoff

The Python runtime cannot impersonate host intelligence. It may create and
persist a request, keep the graph node `RUNNING`, validate a returned handoff,
and deterministically execute accepted code. The current Codex/Claude-style
host performs the requested search, reading, modeling, coding, or review work.

## Lifecycle

```text
REQUEST_CREATED
→ HOST_EXECUTION_REQUIRED
→ HOST_HANDOFF_RECEIVED
→ CHECKING
→ ACCEPTED | REJECTED
```

`HOST_EXECUTION_REQUIRED` is a resumable state, never a successful provider
result. The Director may mark the node `PASS` only after an observed artifact
is received, checked independently, registered, and accepted.

Host registry states are `HOST_AVAILABLE`, `HOST_REQUEST_CAPABLE`, and
`HOST_BEHAVIOR_QUALIFIED`. Static availability does not imply qualification.
A current request may proceed when its specific handoff passes the independent
checker; CI's recorded handoff exercises the protocol but does not qualify a
live model or turn `MODEL_BEHAVIOR_EVAL` into `PASS`.

## Automatic host loop

When a Director result is `HOST_EXECUTION_REQUIRED`, the current host must:

1. Read the persisted request and inspect every declared input plus the existing
   repository before creating files.
2. Perform the requested capability using currently authorized tools. For code,
   make the smallest sufficient project-local change and do not claim execution
   success yet.
3. Write a typed handoff containing the task ID, producer identity, actual
   artifacts, actions, uncertainties, tool calls, commands, and checker notes.
   Code handoffs also include `changed_files`, `entrypoint`, `config`, `tests`,
   `expected_outputs`, and `limitations`.
4. Submit the handoff to the runtime. A producer may not certify its own output.
5. Resume the same Director session. Deterministic execution and output checking
   occur after code acceptance.

Do this without an ordinary author prompt when the host has the capability and
the existing authorization covers it. Stop for credentials, payment, private
data egress, ethics, administrator access, irreversible external mutation, or
submission according to the autonomy policy.

## Manual validation path

Inspect pending requests:

```bash
python scripts/host_provider_runtime.py pending PROJECT
```

After the current host has performed the task and written `host-handoff.json`,
receive and independently check it:

```bash
python scripts/host_provider_runtime.py receive PROJECT host-handoff.json \
  --checker deterministic-output-checker
```

Resume research execution:

```bash
python scripts/director_loop.py resume PROJECT
```

For a competition project, rerun the same Competition Director command with the
same input after each accepted modeling or coding handoff. Its `RUNNING` node is
resumed rather than redispatched.

## Research and competition coding

`constant_mean` and `linear_trend` are transparent native research baselines.
Prediction, optimization, evaluation, clustering, simulation, and ODE are
transparent native competition baselines. A method outside those bounded sets
routes to host modeling/coding, then to deterministic command execution and a
checker. Native unavailability is not itself a project failure.

Accepted host code changes reopen completed dependency descendants such as the
formal experiment, analysis, figures, writing, and review. Existing repository
entrypoints, loaders, tests, configs, notebooks, scripts, models, and experiment
runners take priority over a new pipeline.
