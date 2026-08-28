# Codex adapter

When Provider Runtime emits a host request, Codex may satisfy the neutral
`host.generate/search/read/code/execute/review` capability with its available
tools. It must write the typed handoff, materialize artifacts, record tool and
command evidence, invoke a distinct checker, and resume the deterministic
Director. The host never transitions the graph on its own.

Use the host's available filesystem, shell, browser, and installed skills. Keep
the core graph, schemas, permissions, and provenance host-neutral. Report tool
availability honestly; a missing browser or connector is a conditional limit,
not a reason to invent a source. Do not install plugins or connect accounts
without explicit authorization.
