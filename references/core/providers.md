# Provider layer

The provider layer connects graph capabilities to native code, the current host, public-web tools, or isolated external Skills. It does not own scientific truth: every output is a typed artifact, a separate checker validates it, and the existing evidence/provenance and graph runtimes remain authoritative.

Resolution order is qualified native, qualified installed Skill, qualified host/tool, AUTO_HIRE discovery, bounded fallback or scope reduction, then author escalation only when unavoidable. Formal work requires a qualified, formally eligible provider and an independent checker. One host may perform two distinct invocations, recorded as `checker_independence=LIMITED`.

Host adapters expose the neutral capabilities `host.generate`, `host.search`, `host.read`, `host.code`, `host.execute`, and `host.review`. Vendor-specific details stay under `references/hosts/`. Follow [host-provider.md](host-provider.md) for the real request/receive/check/resume loop. A host request names inputs, constraints, forbidden claims, evidence requirements, budget, and permissions. A host handoff reports artifacts, claims, uncertainties, actions, tool calls, commands, and checker notes. A host assertion never directly causes graph PASS.

Host availability states are `HOST_AVAILABLE`, `HOST_REQUEST_CAPABLE`, and
`HOST_BEHAVIOR_QUALIFIED`. The normal unresolved route is
`HOST_EXECUTION_REQUIRED`, not `PASS`. Only a behavior-qualified host or a
specific independently accepted handoff may enter formal work. Recorded CI
handoffs validate the lifecycle while model behavior remains `NOT_RUN`.

The research and competition coding providers are two-layer systems. Bounded
native algorithms are baselines and sanity checks; unsupported methods request
problem-specific host artifacts. Host code generation is separate from the
deterministic subprocess/job that creates observed outputs.

Provider-created artifacts record input hashes, provider identity/version, command or tool record, upstream artifact IDs, and UTC creation time. Changed inputs mark artifacts and dependency descendants STALE so the Director reruns affected work.

## Public core and private overlay

`PUBLIC_CORE` is the independently functional, distributable V4 team. It is
always available as the fallback and continues to use the normal Provider
Runtime, host handoffs, evidence ledger, and independent checkers.

`PRIVATE_ULTRA` is an optional local overlay. Its target provider map is
`references/private-ultra/team.json`; audited candidates and immutable source
commits are in `assets/registry/private_ultra_candidates.json`. Local
installations are described by a separate registry that is never committed.
Resolve them with:

```bash
python scripts/private_ultra_runtime.py resolve \
  --role experimental-design \
  --capability formal-experiment-design \
  --mode PRIVATE_ULTRA \
  --criticality critical \
  --local-registry PATH
```

The policy is `BEST_QUALIFIED_PROVIDER` or
`BEST_COMPLEMENTARY_ENSEMBLE` for the concrete task. Static inspection alone
does not qualify a provider. Formal eligibility requires an installed
entrypoint at the audited commit, a passed static audit, a passed capability
trial bound to an output hash, comparison with PUBLIC_CORE, and a checker whose
identity differs from the producer. A system benchmark additionally requires
a qualified adapter. Missing or stale evidence fails closed to PUBLIC_CORE, or
to `NO_QUALIFIED_PROVIDER` when the caller explicitly requires a private
provider.

V4 retains the research graph, evidence and protocol authority, publication
and reviewer-completeness gates, research expansion, authorization boundaries,
and release decision. No provider or external pipeline can change those
states directly.
