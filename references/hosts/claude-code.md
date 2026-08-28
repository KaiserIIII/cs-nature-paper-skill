# Claude Code adapter

When Provider Runtime emits a host request, Claude Code may satisfy the neutral
`host.generate/search/read/code/execute/review` capability with its available
tools. It must write the typed handoff, materialize artifacts, record tool and
command evidence, invoke a distinct checker, and resume the deterministic
Director. The host never transitions the graph on its own.

Map the same V3 control loop and graph to Claude Code skills and local files.
Do not assume NotebookLM, MCP, hooks, or a specific shell exists. Preserve the
same employee registry, privacy boundary, artifact anchors, and author-only
external actions. Host-specific commands belong in this adapter, not in the
scientific contract.
