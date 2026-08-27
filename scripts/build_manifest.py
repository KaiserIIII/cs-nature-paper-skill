#!/usr/bin/env python3
"""Build or check a deterministic SHA256 manifest for public release files."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".research-state", ".research-state-v3", ".research-state-v31", "__pycache__", "SHA256SUMS.txt", "release_manifest.json"}


def entries(root: Path = ROOT) -> list[tuple[str, str]]:
    output: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in EXCLUDED for part in path.relative_to(root).parts): continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        output.append((digest, path.relative_to(root).as_posix()))
    return output


def render(root: Path = ROOT) -> str:
    return "".join(f"{digest}  {path}\n" for digest, path in entries(root))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--output", type=Path, default=ROOT / "SHA256SUMS.txt"); parser.add_argument("--check", action="store_true"); args = parser.parse_args(argv)
    expected = render(ROOT); current = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
    if args.check: print({"status":"PASS" if current == expected else "FAIL", "files":len(entries(ROOT)), "manifest":str(args.output)}); return 0 if current == expected else 1
    args.output.write_text(expected, encoding="utf-8", newline="\n"); print({"status":"PASS", "files":len(entries(ROOT)), "manifest":str(args.output)}); return 0


if __name__ == "__main__": sys.exit(main())
