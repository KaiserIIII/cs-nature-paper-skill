# Offline transfer and recovery

The project is designed to move between computers without a package manager.
All runtime code uses the Python standard library.

## Copy

Transfer the complete `cs-nature-paper-skill` directory, including hidden files.
Keep the adjacent `cs-nature-paper-skill-v1` backup if v1 behavior may be needed.
The release archive and `SHA256SUMS.txt` can be used to verify the copy.

## Verify on the destination computer

From the v2 directory:

```bash
python -m unittest discover -s tests -v
python scripts/research_state.py --version
python scripts/employee_registry.py --version
```

If the destination has Codex's `skill-creator`, also run its
`scripts/quick_validate.py` against this directory. On Windows with a non-UTF-8
locale, set `PYTHONUTF8=1` for that validator.

For a release or model/employee change, execute the harness-neutral cases in
`assets/evals/behavior_cases.json` using `docs/behavior-evaluation.md`; these are
behavioral trials, not part of the dependency-free unit-test command.

## Install locally

Copy or link the v2 directory into the destination agent's skill directory.
Keep only one active directory with the skill name `cs-nature-paper` to avoid
ambiguous discovery. Restart the agent if its skill catalog is cached.

## Recover v1

Use the adjacent v1 backup or the GitHub `v1` branch. Do not mix v1's `SKILL.md`
with v2 references and scripts; treat each version as a complete unit.

## Privacy

The skill code and blank templates are public-safe. Project-specific
`.research-state/` directories, filled employee registries, local security
notes, review letters, editor correspondence, private data, credentials, and
unreleased manuscripts are separate and should be moved only through the
author's approved secure channel.
