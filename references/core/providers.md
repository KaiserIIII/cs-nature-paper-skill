# Provider layer

The provider layer connects graph capabilities to native code, the current host, public-web tools, or isolated external Skills. It does not own scientific truth: every output is a typed artifact, a separate checker validates it, and the existing evidence/provenance and graph runtimes remain authoritative.

Resolution order is qualified native, qualified installed Skill, qualified host/tool, AUTO_HIRE discovery, bounded fallback or scope reduction, then author escalation only when unavoidable. Formal work requires a qualified, formally eligible provider and an independent checker. One host may perform two distinct invocations, recorded as `checker_independence=LIMITED`.

Host adapters expose the neutral capabilities `host.generate`, `host.search`, `host.read`, `host.code`, `host.execute`, and `host.review`. Vendor-specific details stay under `references/hosts/`. A host request names inputs, constraints, forbidden claims, evidence requirements, budget, and permissions. A host handoff reports artifacts, claims, uncertainties, actions, tool calls, and the continuation handoff. A host assertion never directly causes graph PASS.

Provider-created artifacts record input hashes, provider identity/version, command or tool record, upstream artifact IDs, and UTC creation time. Changed inputs mark artifacts and dependency descendants STALE so the Director reruns affected work.
