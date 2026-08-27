#!/usr/bin/env python3
"""Resolve the publisher-injected commit in a release manifest artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def resolve(source: Path, output: Path, commit: str) -> dict[str, object]:
    value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("release manifest must be an object")
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit.lower()):
        raise ValueError("source commit must be a 40-character hexadecimal SHA")
    value["source_commit"] = commit.lower()
    value["source_commit_mode"] = "resolved"
    value["resolved_by"] = "publisher"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1] / "release_manifest.json")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        value = resolve(args.source, args.output, args.source_commit)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return 1
    print(json.dumps({"status": "PASS", "output": str(args.output), "source_commit": value["source_commit"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
