#!/usr/bin/env python3
"""Reject private paths, credentials, and review material in public artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "__pycache__", ".research-state", ".research-state-v3", ".research-state-v31", ".eval", "runs", "prepared"}
PATTERNS = {
    "windows-user-path": re.compile(r"[A-Za-z]:\\Users\\[^\s\"']+", re.I),
    "windows-absolute-path": re.compile(r"(?<![A-Za-z])[A-Za-z]:\\[^\s\"']+", re.I),
    "posix-home-path": re.compile(r"/(?:home|Users)/[^\s\"']+", re.I),
    "secret-assignment": re.compile(r"(?i)\b(?:api[_ -]?key|access[_ -]?token|password|secret)\s*[:=]\s*[^\s,}\"]+"),
    "github-token": re.compile(r"\b(?:ghp|github_pat|sk)-[A-Za-z0-9_-]{12,}\b"),
    "private-review-marker": re.compile(r"(?i)\b(?:private review|editor correspondence|confidential manuscript|reviewer identity)\b"),
}
ALLOWED_PLACEHOLDERS = {"<HOME>", "<WORKSPACE>", "<TEMP_PROJECT>", "<REPO_ROOT>", "<REDACTED_SECRET>"}


def files(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    for path in paths:
        if path.is_file():
            found.append(path)
        elif path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and not any(part in SKIP_DIRS for part in child.relative_to(path).parts):
                    found.append(child)
    return sorted(found)


def lint(paths: list[Path], root: Path = ROOT) -> dict[str, object]:
    findings: list[dict[str, str]] = []
    for path in files(paths):
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            findings.append({"path": str(path), "kind": "unreadable", "detail": str(exc)})
            continue
        for kind, pattern in PATTERNS.items():
            for match in pattern.finditer(content):
                token = match.group(0)
                if token in ALLOWED_PLACEHOLDERS or "<" in token and ">" in token:
                    continue
                findings.append({"path": path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path), "kind": kind, "detail": token[:120]})
    return {"operation": "privacy-lint", "status": "PASS" if not findings else "FAIL", "scanned": len(files(paths)), "findings": findings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, default=[ROOT / "benchmarks", ROOT / "release_manifest.json"])
    args = parser.parse_args(argv)
    result = lint(args.paths)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
