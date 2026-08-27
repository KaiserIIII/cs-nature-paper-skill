#!/usr/bin/env python3
"""Build a platform-independent manifest of release-controlled source files."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {".git", ".research-state", ".research-state-v3", ".research-state-v31", "__pycache__", ".eval", ".security-pressure-run", "runs", "prepared"}
EXCLUDED_FILES = {"SHA256SUMS.txt", "release_manifest.json", "benchmarks/smoke-run-result.json", ".ci-smoke-result.json"}
GENERATED_PREFIXES = ("benchmarks/security-pressure-run/", "benchmarks/smoke-run/")


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_release_controlled(path: Path, root: Path = ROOT) -> bool:
    rel = _relative(path, root)
    if rel in EXCLUDED_FILES or any(rel.startswith(prefix) for prefix in GENERATED_PREFIXES):
        return False
    if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
        return False
    # Generated benchmark runs are artifacts, not release-controlled source.
    if rel.startswith("benchmarks/") and "/" in rel[len("benchmarks/"):]:
        return rel == "benchmarks/README.md"
    return True


def canonical_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def entries(root: Path = ROOT) -> list[tuple[str, str]]:
    output: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*"), key=lambda item: _relative(item, root)):
        if not path.is_file() or not is_release_controlled(path, root):
            continue
        output.append((hashlib.sha256(canonical_bytes(path)).hexdigest(), _relative(path, root)))
    return output


def render(root: Path = ROOT) -> str:
    return "".join(f"{digest}  {path}\n" for digest, path in entries(root))


def current_commit(root: Path = ROOT) -> str:
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "SHA256SUMS.txt")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    expected = render(ROOT)
    current = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
    ok = current == expected
    result = {"status": "PASS" if ok else "FAIL", "files": len(entries(ROOT)), "manifest": str(args.output), "commit": current_commit()}
    if not ok:
        expected_lines = expected.splitlines()
        current_lines = current.splitlines()
        result["mismatches"] = [
            {"line": index + 1, "expected": expected_lines[index] if index < len(expected_lines) else None,
             "actual": current_lines[index] if index < len(current_lines) else None}
            for index in range(max(len(expected_lines), len(current_lines)))
            if (expected_lines[index] if index < len(expected_lines) else None) != (current_lines[index] if index < len(current_lines) else None)
        ][:10]
    if not args.check:
        args.output.write_text(expected, encoding="utf-8", newline="\n")
        result["status"] = "PASS"
    print(json.dumps(result) if args.json else result)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
