#!/usr/bin/env python3
"""Capability-driven public Skill discovery with static audit and immutable pins."""

from __future__ import annotations

import json
import argparse
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import sys


SKILL_VERSION = "3.2.0"
IMMUTABLE_REF = re.compile(r"^[0-9a-f]{40}$")
SAFE_LICENSES = {"MIT", "BSD-2-CLAUSE", "BSD-3-CLAUSE", "APACHE-2.0", "ISC"}
AUDIT_FILES = (
    "README.md", "SKILL.md", "LICENSE", "LICENSE.md", "pyproject.toml", "requirements.txt",
    "setup.py", "setup.cfg", "package.json", ".github/workflows", "hooks", "install.sh", "install.ps1",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def vacancy_queries(capability: str) -> list[str]:
    normalized = " ".join(capability.replace("_", "-").split()).strip()
    if not normalized:
        raise ValueError("capability vacancy is required")
    return [
        f'{normalized} "SKILL.md" agent skill',
        f'{normalized} scientific research skill',
    ]


class GitHubPublicBackend:
    """Credential-free GitHub REST adapter; CI should inject a recorded backend instead."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def _get(self, url: str) -> Any:
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "cs-nature-paper-provider/3.2.0"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:  # nosec B310: explicit public GitHub adapter
            return json.loads(response.read().decode("utf-8"))

    def search(self, query: str) -> list[dict[str, Any]]:
        endpoint = "https://api.github.com/search/repositories?q=" + urllib.parse.quote(query) + "&per_page=10"
        payload = self._get(endpoint)
        output = []
        for item in payload.get("items", []):
            repo = item.get("full_name")
            default_branch = item.get("default_branch", "main")
            if not repo:
                continue
            branch = self._get(f"https://api.github.com/repos/{repo}/commits/{urllib.parse.quote(default_branch)}")
            exact_ref = branch.get("sha")
            files = self._audit_files(repo, exact_ref) if IMMUTABLE_REF.fullmatch(str(exact_ref or "")) else {}
            output.append({
                "id": repo.casefold().replace("/", "-"),
                "repo": repo,
                "repo_url": item.get("clone_url"),
                "exact_ref": exact_ref,
                "license": ((item.get("license") or {}).get("spdx_id") or "UNKNOWN").upper(),
                "capabilities": [],
                "files": files,
                "dependencies": [],
                "credentials": False,
                "network_runtime": False,
                "external_writes": False,
                "install_hooks": False,
                "system_writes": False,
                "tests": any(path.startswith(("tests/", "test/")) or "/tests/" in path for path in files),
                "maintainer_activity": item.get("pushed_at"),
                "search_query": query,
            })
        return output

    def _audit_files(self, repo: str, exact_ref: str) -> dict[str, str]:
        tree = self._get(f"https://api.github.com/repos/{repo}/git/trees/{exact_ref}?recursive=1")
        selected = []
        for item in tree.get("tree", []):
            path = str(item.get("path", ""))
            name = Path(path).name.casefold()
            if item.get("type") != "blob" or int(item.get("size") or 0) > 200_000:
                continue
            if (
                name in {"readme.md", "skill.md", "license", "license.md", "pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "package.json"}
                or path.startswith(".github/workflows/")
                or "hook" in name
                or name.startswith("install.")
            ):
                selected.append(path)
        files = {}
        for path in selected[:40]:
            raw = f"https://raw.githubusercontent.com/{repo}/{exact_ref}/{urllib.parse.quote(path)}"
            request = urllib.request.Request(raw, headers={"User-Agent": "cs-nature-paper-provider/3.2.0"})
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:  # nosec B310: pinned public GitHub content
                    files[path] = response.read(200_001).decode("utf-8", errors="replace")
            except urllib.error.URLError:
                continue
        return files


def _deduplicate(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for candidate in candidates:
        key = (str(candidate.get("repo", candidate.get("id", ""))), str(candidate.get("exact_ref", "")))
        if key in seen:
            continue
        seen.add(key)
        output.append(dict(candidate))
    return output


def _capability_tokens(capability: str) -> list[str]:
    stop = {"and", "or", "the", "a", "an", "skill", "provider"}
    return [
        token for token in re.findall(r"[a-z0-9]+", capability.casefold().replace("_", "-"))
        if len(token) > 1 and token not in stop
    ]


def verify_capability(candidate: dict[str, Any], capability: str) -> dict[str, Any]:
    """Verify capability from content plus an explicit semantic audit and behavior trial."""
    files = dict(candidate.get("files") or {})
    source_value = candidate.get("source_path")
    if source_value and Path(str(source_value)).is_dir():
        files.update(_source_files(Path(str(source_value))))
    relevant = {
        path: content
        for path, content in files.items()
        if Path(path).name.casefold() in {
            "skill.md", "readme.md", "pyproject.toml", "package.json", "setup.cfg", "setup.py",
        }
        or path.casefold().startswith(("tests/", "test/"))
        or Path(path).suffix.casefold() in {".py", ".js", ".ts"}
    }
    joined = "\n".join(f"{path}\n{content}" for path, content in relevant.items()).casefold()
    tokens = _capability_tokens(capability)
    matched = [token for token in tokens if token in joined]
    if not matched:
        status = "MISMATCH"
        findings = ["repository content does not substantiate the requested capability"]
    elif len(matched) < len(tokens):
        status = "PARTIAL"
        findings = ["repository content only partially matches the requested capability"]
    else:
        semantic = candidate.get("semantic_audit")
        trial = candidate.get("behavior_trial")
        semantic_ok = (
            isinstance(semantic, dict)
            and semantic.get("status") == "CONFIRMED"
            and bool(semantic.get("actor"))
            and isinstance(semantic.get("evidence"), list)
            and bool(semantic.get("evidence"))
        )
        trial_ok = (
            isinstance(trial, dict)
            and trial.get("status") == "PASS"
            and trial.get("output_contract") == "PASS"
            and bool(trial.get("checker"))
        )
        if semantic_ok and trial_ok:
            status = "CONFIRMED"
            findings = []
        else:
            status = "UNVERIFIED"
            findings = []
            if not semantic_ok:
                findings.append("host semantic audit is unavailable or incomplete")
            if not trial_ok:
                findings.append("checked behavior trial is unavailable or incomplete")
    return {
        "operation": "capability-verification",
        "status": status,
        "requested_capability": capability,
        "prefilter_tokens": tokens,
        "matched_tokens": matched,
        "files_inspected": sorted(relevant),
        "semantic_audit": candidate.get("semantic_audit"),
        "behavior_trial": candidate.get("behavior_trial"),
        "formal_eligible": status == "CONFIRMED",
        "findings": findings,
    }


def discover_capability(
    capability: str,
    *,
    backends: list[Any] | None = None,
    known_catalog: list[dict[str, Any]] | None = None,
    installed: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Discover metadata only. This function never installs or executes a candidate."""
    queries = vacancy_queries(capability)
    candidates = [
        dict(item) for item in (known_catalog or []) + (installed or [])
        if capability in item.get("capabilities", [])
    ]
    used = []
    for backend in backends or [GitHubPublicBackend()]:
        for query in queries:
            used.append(query)
            try:
                found = backend.search(query)
            except (OSError, ValueError, TimeoutError, urllib.error.URLError):
                continue
            for candidate in found:
                value = dict(candidate)
                candidates.append(value)
    candidates = _deduplicate(candidates)
    for candidate in candidates:
        candidate["requested_capability"] = capability
        candidate["capability_verification"] = verify_capability(candidate, capability)
    return {
        "operation": "skill-discovery", "status": "PASS" if candidates else "UNAVAILABLE",
        "capability": capability, "queries": used, "candidates": candidates,
        "discovery_is_installation": False,
    }


def _source_files(source: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for name in AUDIT_FILES:
        path = source / name
        if path.is_file():
            try:
                files[name] = path.read_text(encoding="utf-8", errors="replace")[:200_000]
            except OSError:
                pass
        elif path.is_dir():
            for nested in sorted(path.rglob("*")):
                if nested.is_file():
                    relative = nested.relative_to(source).as_posix()
                    files[relative] = nested.read_text(encoding="utf-8", errors="replace")[:200_000]
    return files


def static_audit(candidate: dict[str, Any]) -> dict[str, Any]:
    files = dict(candidate.get("files") or {})
    source_value = candidate.get("source_path")
    if source_value and Path(str(source_value)).is_dir():
        files.update(_source_files(Path(str(source_value))))
    findings: list[str] = []
    indicators: list[str] = []
    exact_ref = str(candidate.get("exact_ref", ""))
    if not IMMUTABLE_REF.fullmatch(exact_ref):
        findings.append("formal employee ref must be a 40-character immutable commit SHA")
    license_name = str(candidate.get("license", "UNKNOWN")).upper()
    if license_name not in SAFE_LICENSES:
        findings.append("license is absent, unsafe, or incompatible")
    skill_files = [name for name in files if Path(name).name.casefold() == "skill.md"]
    if not skill_files:
        findings.append("SKILL.md was not available for static audit")
    joined = "\n".join([*files.keys(), *files.values()]).casefold()
    dependencies = list(candidate.get("dependencies", []))
    for name, content in files.items():
        if Path(name).name.casefold() == "requirements.txt":
            dependencies.extend(line.strip() for line in content.splitlines() if line.strip() and not line.lstrip().startswith("#"))
        elif Path(name).name.casefold() == "package.json":
            try:
                package = json.loads(content)
                dependencies.extend(sorted((package.get("dependencies") or {}).keys()))
            except json.JSONDecodeError:
                findings.append("package.json could not be parsed during static audit")
    dangerous_patterns = {
        "install_hooks": ("postinstall", "preinstall", "setup.py", "install.sh", "install.ps1"),
        "system_writes": ("/etc/", "system32", "program files", "sudo "),
        "credentials": ("api_key", "github_token", "secret_key", "credentials"),
        "external_writes": ("upload", "publish", "git push", "http post"),
    }
    flags = {}
    for field, patterns in dangerous_patterns.items():
        declared = bool(candidate.get(field))
        detected = any(pattern in joined for pattern in patterns)
        flags[field] = declared or detected
        if flags[field]:
            indicators.append(field)
    network = bool(candidate.get("network_runtime")) or any(token in joined for token in ("requests.", "urllib", "http://", "https://"))
    if network:
        indicators.append("network")
    if flags["credentials"] or flags["system_writes"] or flags["install_hooks"]:
        risk = "HIGH"
    elif candidate.get("license_compatible") is False:
        risk = "CRITICAL"
    elif network or flags["external_writes"] or candidate.get("large_dependency_set"):
        risk = "MEDIUM"
    else:
        risk = "LOW"
    authorization = {"LOW": "AUTO", "MEDIUM": "AUTO_WITH_AUDIT", "HIGH": "ASK_AUTHOR", "CRITICAL": "DENY"}[risk]
    status = "PASS" if not findings and risk != "CRITICAL" else "FAIL"
    capability = str(candidate.get("requested_capability", "")).strip()
    capability_verification = (
        verify_capability(candidate, capability) if capability
        else candidate.get("capability_verification")
    )
    return {
        "operation": "skill-static-audit", "status": status, "candidate_id": candidate.get("id"),
        "repo": candidate.get("repo"), "exact_commit": exact_ref, "license": license_name,
        "dependencies": sorted(set(dependencies)), "credentials": flags["credentials"],
        "network": network, "external_writes": flags["external_writes"],
        "install_hooks": flags["install_hooks"], "system_writes": flags["system_writes"],
        "tests": bool(candidate.get("tests")), "maintainer_activity": candidate.get("maintainer_activity"),
        "capabilities": list(candidate.get("capabilities", [])), "files_audited": sorted(files), "skill_files": sorted(skill_files),
        "capability_verification": capability_verification,
        "risk_indicators": sorted(set(indicators)), "risk": risk, "authorization": authorization,
        "findings": findings, "installer_executed": False,
    }


def materialize(project: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    """Copy or fetch an audited exact commit. Arbitrary installers are never run."""
    audit = static_audit(candidate)
    if audit["status"] != "PASS":
        return {"operation": "skill-materialize", "status": "REJECTED", "audit": audit}
    if audit["authorization"] in {"ASK_AUTHOR", "DENY"}:
        return {"operation": "skill-materialize", "status": "BLOCKED", "audit": audit}
    exact_ref = str(candidate["exact_ref"])
    destination = project.resolve() / ".research-state" / "employees" / str(candidate["id"]) / exact_ref
    if destination.is_dir():
        return {"operation": "skill-materialize", "status": "MATERIALIZED", "path": str(destination), "audit": audit, "reused": True}
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_value = candidate.get("source_path")
    if source_value and Path(str(source_value)).is_dir():
        shutil.copytree(Path(str(source_value)).resolve(), destination)
    else:
        repo_url = str(candidate.get("repo_url", ""))
        if not repo_url.startswith(("https://github.com/", "git@github.com:")):
            return {"operation": "skill-materialize", "status": "REJECTED", "audit": audit, "reason": "unsupported repository URL"}
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", repo_url, str(destination)], check=True, capture_output=True, text=True)
        subprocess.run(["git", "-C", str(destination), "fetch", "--depth", "1", "origin", exact_ref], check=True, capture_output=True, text=True)
        subprocess.run(["git", "-C", str(destination), "checkout", "--detach", exact_ref], check=True, capture_output=True, text=True)
    log = {
        "operation": "skill-materialize", "status": "MATERIALIZED", "path": str(destination),
        "repo": candidate.get("repo"), "exact_commit": exact_ref, "audit": audit,
        "environment_policy": "NO_SECRETS_ALLOWLIST", "installer_executed": False, "created_utc": _now(),
    }
    _write(project.resolve() / ".research-state" / "skill-discovery-audit" / f"{candidate['id']}-{exact_ref}.json", log)
    return log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    discover_parser = sub.add_parser("discover")
    discover_parser.add_argument("capability")
    audit_parser = sub.add_parser("audit")
    audit_parser.add_argument("candidate", type=Path)
    materialize_parser = sub.add_parser("materialize")
    materialize_parser.add_argument("project", type=Path)
    materialize_parser.add_argument("candidate", type=Path)
    args = parser.parse_args(argv)
    if args.command == "discover":
        result = discover_capability(args.capability)
    else:
        candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
        result = static_audit(candidate) if args.command == "audit" else materialize(args.project, candidate)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") in {"PASS", "MATERIALIZED"} else 1


if __name__ == "__main__":
    sys.exit(main())
