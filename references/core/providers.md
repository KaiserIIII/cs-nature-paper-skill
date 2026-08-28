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
