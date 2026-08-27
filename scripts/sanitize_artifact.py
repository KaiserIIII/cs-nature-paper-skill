#!/usr/bin/env python3
"""Sanitize public artifacts without exposing host-specific paths or secrets."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PATH_PATTERNS = (
    (re.compile(r"[A-Za-z]:\\Users\\[^\\\s\"']*\\AppData\\Local\\Temp\\[^\\\s\"']*", re.I), "<TEMP_PROJECT>"),
    (re.compile(r"[A-Za-z]:\\Users\\[^\\\s\"']+", re.I), "<HOME>"),
    (re.compile(r"[A-Za-z]:\\[^\s\"']+", re.I), "<WORKSPACE>"),
    (re.compile(r"/home/[^/\s\"']+(?:/[^\s\"']*)?", re.I), "<HOME>"),
    (re.compile(r"/Users/[^/\s\"']+(?:/[^\s\"']*)?", re.I), "<HOME>"),
    (re.compile(r"(?:^|[\\/])tmp[\\/][^\s\"']+", re.I), "<TEMP_PROJECT>"),
)
SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:api[_ -]?key|access[_ -]?token|secret|password)\s*[:=]\s*[^\s,}\"]+"),
    re.compile(r"\b(?:ghp|github_pat|sk)-[A-Za-z0-9_-]{12,}\b"),
)


def sanitize_text(value: str) -> str:
    result = value
    for pattern, replacement in PATH_PATTERNS:
        result = pattern.sub(replacement, result)
    for pattern in SECRET_PATTERNS:
        result = pattern.sub("<REDACTED_SECRET>", result)
    return result


def sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_value(item) for key, item in value.items()}
    return value


def sanitize_file(source: Path, destination: Path | None = None) -> Path:
    destination = destination or source
    raw = source.read_text(encoding="utf-8")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        destination.write_text(sanitize_text(raw), encoding="utf-8", newline="\n")
    else:
        destination.write_text(json.dumps(sanitize_value(value), indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return destination


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    print(json.dumps({"status": "PASS", "output": str(sanitize_file(args.source, args.output))}))
