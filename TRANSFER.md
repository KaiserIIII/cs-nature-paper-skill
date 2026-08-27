# Offline transfer and recovery (V3)

The project uses only the Python standard library for its runtime helpers.
Transfer the complete `cs-nature-paper-skill` directory, including hidden files,
and keep the adjacent V1 backup if old behavior is needed.

## Verify

```bash
python -m unittest discover -s tests -v
python scripts/research_state.py --version
python scripts/employee_registry.py --version
python scripts/research_graph.py --help
```

If the destination has Codex's `skill-creator`, also run its
`scripts/quick_validate.py` against this directory. For a release or employee
change, execute `assets/evals/behavior_cases.json` under
`docs/behavior-evaluation.md`; these behavioral trials are separate from unit
tests.

## Install and recover

Copy or link the V3 directory into the destination agent's skill directory and
restart the agent if its skill catalog is cached. Use the V1 backup/branch or
the GitHub `v2` branch to recover historical versions. Do not mix entrypoints,
references, and scripts from different versions.

To migrate a project-local V2 state, run:

```bash
python scripts/research_state.py migrate-v2 PROJECT
```

The V2 `.research-state` is left untouched; V3 is copied to
`.research-state-v3` and can be removed recoverably by the author if needed.

## Privacy

Project-specific state, filled employee registries, review letters, editor
correspondence, private data, credentials, and unreleased manuscripts remain
outside public artifacts and move only through the author's approved channel.
