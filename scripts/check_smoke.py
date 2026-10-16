#!/usr/bin/env python3
"""Reject a smoke artifact produced by a different commit."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def current_commit(root: Path) -> str:
    root = root.resolve()
    try:
        # Git emits UTF-8 paths independently of Python's Windows locale.
        top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()
        if Path(top).resolve() != root:
            raise ValueError("Source root is not its own Git repository/worktree root")
        # Check index/HEAD and worktree/index separately: opposite changes can
        # cancel in `git diff HEAD` while the index still contains another source.
        for arguments in (("diff", "--cached", "--quiet", "HEAD", "--"), ("diff", "--quiet", "--")):
            result = subprocess.run(["git", "-C", str(root), *arguments], capture_output=True)
            if result.returncode == 1:
                raise ValueError("Source root has uncommitted tracked changes")
            result.check_returncode()
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("Source root has no verifiable Git commit") from exc


def check(path: Path, root: Path | None = None) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8")); root = root or Path(__file__).resolve().parents[1]; expected = current_commit(root); actual = value.get("skill_commit")
    if actual != expected:
        return {"status": "STALE", "expected_commit": expected, "actual_commit": actual, "path": str(path)}
    if value.get("status") != "PASS":
        return {"status": "FAIL", "reason": "smoke status is not PASS", "path": str(path)}
    return {"status": "PASS", "commit": expected, "path": str(path)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("smoke", type=Path)
    parser.add_argument("--root", type=Path)
    args = parser.parse_args()
    try:
        result = check(args.smoke, args.root)
    except ValueError:
        result = {"status": "UNVERIFIED", "reason": "Smoke/source identity is unavailable or invalid"}
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "PASS" else 1)
