# Adaptive research graph

`research_graph.json` is the workflow source of truth. A node has:

```json
{
  "id": "feasibility",
  "kind": "gate",
  "status": "READY",
  "depends_on": ["literature", "innovation"],
  "inputs": ["candidate_rqs", "resource_inventory"],
  "outputs": ["feasibility_decision"],
  "required_capabilities": ["feasibility-screen"],
  "stop_when": ["decision is recorded with cost and residual risk"],
  "reopen_on": ["new closest work", "resource change"]
}
```

Edges have `condition`, `kind` (`parallel`, `success`, `failure`, `amendment`,
`rollback`), and `target`. Every transition appends an event; it never deletes
an earlier event or artifact. A failed node may reopen its owner, and a review
finding targets the smallest node that can change the claim.

The bundled default graph is deliberately small. Add nodes only when an input,
threat, or decision requires them. Do not create a node merely to increase agent
count or produce a status display.

## Transition invariants

- A node cannot be `PASS` without its required inputs and an evidence anchor.
- `FORMAL` experiments require a frozen protocol and a non-overwrite path.
- A graph transition cannot mutate claim text or protocol fields directly.
- `REOPENED` preserves the prior output and records the trigger.
- `package_ready` requires validation pass/conditional and explicit author
  authorization for any external action.
