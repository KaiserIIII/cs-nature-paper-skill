#!/usr/bin/env python3
"""Bounded offline adapters for the approved V4.1 specialist resources.

These adapters make selected upstream implementations callable for advisory
work. They deliberately do not grant formal scientific evidence eligibility.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = Path("assets/registry/v41_provider_registry.json")
QUALIFICATION_PATH = Path("assets/registry/v41_provider_qualification.json")
SOURCE_MANIFEST_PATH = Path("vendor/selected/v41/source_manifest.json")
MODES = {"PUBLIC_CORE", "PRIVATE_ULTRA"}
SOURCE_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class AdapterError(RuntimeError):
    """A bounded provider could not be invoked safely."""


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return _sha256_bytes(payload)


def _bundle_hash(files: list[dict[str, Any]]) -> str:
    rows = [
        f"{item['path']}\0{item['sha256']}"
        for item in sorted(files, key=lambda row: (row["path"].casefold(), row["path"]))
    ]
    return _sha256_bytes("\n".join(rows).encode("utf-8"))


def _safe_resource(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise AdapterError(f"unsafe resource path: {relative}")
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as error:
        raise AdapterError(f"resource escapes install root: {relative}") from error
    if resolved.is_symlink() or not resolved.is_file():
        raise AdapterError(f"resource is unavailable or unsafe: {relative}")
    return resolved


def _load_runtime_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AdapterError(f"cannot load upstream module: {path}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
        raise
    return module


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _plain(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _local_input(value: Any, label: str, *, directory: bool = False) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise AdapterError(f"{label} must be a non-empty local path")
    if value.startswith(("http://", "https://", "ftp://", "s3://")):
        raise AdapterError(f"{label} must not be a network location")
    path = Path(value).expanduser()
    if str(path).startswith(("\\\\", "//")):
        raise AdapterError(f"{label} must not be a UNC path")
    if directory and not path.is_dir():
        raise AdapterError(f"{label} directory does not exist: {path}")
    if not directory and not path.is_file():
        raise AdapterError(f"{label} file does not exist: {path}")
    return path.resolve()


def _registry(root: Path) -> dict[str, dict[str, Any]]:
    value = _read_json(root / REGISTRY_PATH)
    providers = value.get("providers") if isinstance(value, dict) else None
    if not isinstance(providers, list):
        raise AdapterError("V4.1 provider registry is invalid")
    result = {
        item["provider_id"]: item
        for item in providers
        if isinstance(item, dict) and isinstance(item.get("provider_id"), str)
    }
    if len(result) != len(providers):
        raise AdapterError("V4.1 provider identities are missing or duplicated")
    return result


def _manifest(root: Path) -> dict[str, dict[str, Any]]:
    value = _read_json(root / SOURCE_MANIFEST_PATH)
    bundles = value.get("bundles") if isinstance(value, dict) else None
    if not isinstance(bundles, list):
        raise AdapterError("selected-resource source manifest is invalid")
    result = {
        item["provider_id"]: item
        for item in bundles
        if isinstance(item, dict) and isinstance(item.get("provider_id"), str)
    }
    if len(result) != len(bundles):
        raise AdapterError("selected-resource bundle identities are missing or duplicated")
    return result


def _qualification_status(root: Path, provider_id: str) -> str:
    try:
        value = _read_json(root / QUALIFICATION_PATH)
    except (OSError, ValueError, TypeError):
        return "UNAUDITED"
    bundles = value.get("bundles", []) if isinstance(value, dict) else []
    matches = [
        item
        for item in bundles
        if isinstance(item, dict) and item.get("provider_id") == provider_id
    ]
    if len(matches) != 1:
        return "UNAUDITED"
    status = matches[0].get("qualification_status")
    return status if status in {"PROVISIONAL", "QUALIFIED", "REJECTED"} else "UNAUDITED"


def audit_installation(*, root: Path | str = ROOT) -> dict[str, Any]:
    install_root = Path(root).resolve()
    findings: list[str] = []
    providers: dict[str, dict[str, Any]] = {}
    try:
        registry = _registry(install_root)
        manifest = _manifest(install_root)
    except (AdapterError, OSError, ValueError, TypeError) as error:
        return {
            "operation": "audit-v41-provider-installation",
            "status": "FAIL",
            "providers": {},
            "findings": [str(error)],
        }

    for provider_id, record in sorted(registry.items()):
        provider_findings: list[str] = []
        bundle = manifest.get(provider_id)
        files = bundle.get("files") if isinstance(bundle, dict) else None
        checked: list[str] = []
        if not isinstance(files, list) or not files:
            provider_findings.append("selected-resource bundle is absent or empty")
            files = []
        for descriptor in files:
            relative = descriptor.get("path") if isinstance(descriptor, dict) else None
            expected = descriptor.get("sha256") if isinstance(descriptor, dict) else None
            try:
                if not isinstance(relative, str) or SOURCE_HASH_RE.fullmatch(str(expected)) is None:
                    raise AdapterError("invalid source manifest descriptor")
                path = _safe_resource(install_root, relative)
                actual = _sha256_file(path)
                if actual != expected:
                    raise AdapterError(f"resource hash mismatch: {relative}")
                checked.append(relative)
            except (AdapterError, OSError) as error:
                provider_findings.append(str(error))
        manifest_hash = bundle.get("source_hash") if isinstance(bundle, dict) else None
        if files and _bundle_hash(files) != manifest_hash:
            provider_findings.append("selected-resource bundle hash mismatch")
        if record.get("source_hash") != manifest_hash:
            provider_findings.append("provider registry source hash is not bound to selected resources")
        entrypoint = record.get("entrypoint")
        if not isinstance(entrypoint, str) or not entrypoint.startswith("v41_provider_adapters:"):
            provider_findings.append("adapter entrypoint is missing or invalid")
        elif not callable(globals().get(entrypoint.partition(":")[2])):
            provider_findings.append("adapter entrypoint does not resolve to a callable")
        providers[provider_id] = {
            "integrity": "PASS" if not provider_findings else "FAIL",
            "source_hash": manifest_hash,
            "entrypoint": entrypoint,
            "executed_resources": checked,
            "findings": provider_findings,
        }
        findings.extend(f"{provider_id}: {item}" for item in provider_findings)
    for provider_id in sorted(set(manifest) - set(registry)):
        findings.append(f"{provider_id}: source bundle has no provider registry entry")
    return {
        "operation": "audit-v41-provider-installation",
        "status": "PASS" if not findings else "FAIL",
        "providers": providers,
        "findings": findings,
    }


def _paperspine_contribution(request: dict[str, Any], root: Path) -> tuple[dict[str, Any], list[str]]:
    output_dir = _local_input(request.get("output_dir"), "output_dir", directory=True)
    script = _safe_resource(
        root, "vendor/selected/v41/paperspine/src/scripts/contribution_check.py"
    )
    utility = _safe_resource(
        root, "vendor/selected/v41/paperspine/src/scripts/_paper_spine_utils.py"
    )
    module = _load_runtime_module("v41_paperspine_contribution_check", script)
    result = _plain(module.check_contribution(output_dir))
    return result, [str(script.relative_to(root)), str(utility.relative_to(root))]


def _paperspine_results(request: dict[str, Any], root: Path) -> tuple[dict[str, Any], list[str]]:
    artifact = _local_input(request.get("artifact_path"), "artifact_path")
    script = _safe_resource(
        root, "vendor/selected/v41/paperspine/src/scripts/results_validation_check.py"
    )
    utility = _safe_resource(
        root, "vendor/selected/v41/paperspine/src/scripts/_paper_spine_utils.py"
    )
    module = _load_runtime_module("v41_paperspine_results_validation_check", script)
    result = _plain(module.validate(artifact))
    return result, [str(script.relative_to(root)), str(utility.relative_to(root))]


def _paperspine_exemplar(request: dict[str, Any], root: Path) -> tuple[dict[str, Any], list[str]]:
    artifact = _local_input(request.get("artifact_path"), "artifact_path")
    script = _safe_resource(
        root, "vendor/selected/v41/paperspine/src/scripts/reference_inventory.py"
    )
    protocol = _safe_resource(
        root,
        "vendor/selected/v41/paperspine/src/skill/references/exemplar-learning-dossier.md",
    )
    module = _load_runtime_module("v41_paperspine_reference_inventory", script)
    inventory = [_plain(item) for item in module.make_items([artifact], "specified_paths", 50)]
    payload = _read_json(artifact)
    findings: list[str] = []
    venue = payload.get("target_venue") if isinstance(payload, dict) else None
    exemplars = payload.get("exemplars") if isinstance(payload, dict) else None
    if not isinstance(venue, str) or not venue.strip():
        findings.append("target_venue is required")
    if not isinstance(exemplars, list) or not exemplars:
        findings.append("at least one target exemplar is required")
        exemplars = []
    verified = 0
    for index, item in enumerate(exemplars, start=1):
        if not isinstance(item, dict):
            findings.append(f"exemplar {index} must be an object")
            continue
        for field in ("source_id", "title", "transferable_patterns", "non_transferable_content"):
            value = item.get(field)
            if field in {"transferable_patterns", "non_transferable_content"}:
                if not isinstance(value, list) or not value:
                    findings.append(f"exemplar {index} missing {field}")
            elif not isinstance(value, str) or not value.strip():
                findings.append(f"exemplar {index} missing {field}")
        if item.get("verified") is True:
            verified += 1
        else:
            findings.append(f"exemplar {index} is not identity-verified")
    result = {
        "ok": not findings,
        "target_venue": venue,
        "exemplar_count": len(exemplars),
        "verified_count": verified,
        "inventory": inventory,
        "protocol_sha256": _sha256_file(protocol),
        "findings": findings,
        "claim_boundary": "Patterns may be learned; claims, data, wording, and conclusions may not be copied.",
    }
    return result, [str(script.relative_to(root)), str(protocol.relative_to(root))]


def _paperspine_publication(request: dict[str, Any], root: Path) -> tuple[dict[str, Any], list[str]]:
    request_path = _local_input(request.get("request_path"), "request_path")
    script = _safe_resource(
        root, "vendor/selected/v41/paperspine/src/scripts/publication_cycle.py"
    )
    resource_names = [
        "vendor/selected/v41/paperspine/src/skill/references/publication-cycle-contracts.md",
        "vendor/selected/v41/paperspine/src/skill/references/publication-cycle-interface.md",
        "vendor/selected/v41/paperspine/src/skill/references/contracts/publication-cycle-invocation.schema.json",
        "vendor/selected/v41/paperspine/src/skill/references/contracts/publication-cycle-result.schema.json",
    ]
    resources = [_safe_resource(root, name) for name in resource_names]
    module = _load_runtime_module("v41_paperspine_publication_cycle", script)
    result = _plain(module.invoke_publication_cycle(request_path))
    descriptor = _plain(module.public_interface_descriptor())
    result["supported_operations"] = [item["id"] for item in descriptor["operations"]]
    result["interface_contract"] = descriptor["contract"]
    result["request_schema_sha256"] = _sha256_file(resources[2])
    result["result_schema_sha256"] = _sha256_file(resources[3])
    result["release_authorized"] = False
    return result, [str(script.relative_to(root)), *(str(path.relative_to(root)) for path in resources)]


def _nature_figure(request: dict[str, Any], root: Path) -> tuple[dict[str, Any], list[str]]:
    source_path = _local_input(request.get("source_path"), "source_path")
    script = _safe_resource(
        root,
        "vendor/selected/v41/nature-skills/skills/nature-figure/scripts/validate_figure.py",
    )
    contract = _safe_resource(
        root,
        "vendor/selected/v41/nature-skills/skills/nature-figure/references/figure-contract.md",
    )
    module = _load_runtime_module("v41_nature_figure_validate", script)
    backend = request.get("backend", "auto")
    if backend not in {"auto", "python", "r"}:
        raise AdapterError("backend must be auto, python, or r")
    if backend == "auto":
        backend = module.detect_backend(source_path, "auto")
    source = source_path.read_text(encoding="utf-8", errors="replace")
    findings = module.validate_source(source, backend)
    result = module.summarize(findings, bool(request.get("strict", False)))
    result.update(
        {
            "backend": backend,
            "findings": [_plain(item) for item in findings],
            "contract_sha256": _sha256_file(contract),
            "visual_inspection_required": True,
            "scientific_truth_validated": False,
        }
    )
    return _plain(result), [str(script.relative_to(root)), str(contract.relative_to(root))]


def _section_present(text: str, names: tuple[str, ...]) -> bool:
    headings = [
        match.group(1).strip().lower()
        for match in re.finditer(r"(?m)^#{1,6}\s+(.+?)\s*$", text)
    ]
    return any(any(name in heading for name in names) for heading in headings)


def _nature_reviewer(request: dict[str, Any], root: Path) -> tuple[dict[str, Any], list[str]]:
    manuscript = _local_input(request.get("manuscript_path"), "manuscript_path")
    resource_paths = [
        "vendor/selected/v41/nature-skills/skills/nature-reviewer/SKILL.md",
        "vendor/selected/v41/nature-skills/skills/nature-reviewer/references/review-axes.md",
        "vendor/selected/v41/nature-skills/skills/nature-reviewer/references/report-structure.md",
        "vendor/selected/v41/nature-skills/skills/nature-reviewer/references/qa-checklist.md",
    ]
    resources = [_safe_resource(root, item) for item in resource_paths]
    protocol = "\n".join(path.read_text(encoding="utf-8") for path in resources)
    text = manuscript.read_text(encoding="utf-8", errors="replace")
    lowered = text.lower()
    axes = [
        "originality",
        "scientific importance / significance",
        "interdisciplinary readership interest",
        "technical soundness / technical failings",
        "readability for nonspecialists",
    ]
    concerns: list[dict[str, str]] = []
    required_sections = {
        "methods": ("methods", "methodology"),
        "results": ("results", "findings"),
        "limitations": ("limitations", "limitations and threats"),
        "data/code availability": ("data and code availability", "data availability", "code availability"),
    }
    for label, aliases in required_sections.items():
        if not _section_present(text, aliases):
            concerns.append(
                {
                    "severity": "MAJOR" if label in {"methods", "results"} else "MINOR",
                    "axis": "technical soundness / technical failings",
                    "concern": f"The supplied manuscript has no identifiable {label} section.",
                    "evidence": "Not assessable from provided material",
                    "action": f"Add or identify the {label} section and bind its claims to evidence.",
                }
            )
    if not re.search(r"\b(novel|original|contribution|advance)\w*\b", lowered):
        concerns.append(
            {
                "severity": "MINOR",
                "axis": "originality",
                "concern": "The claimed advance is not explicit in the supplied manuscript.",
                "evidence": "No originality or contribution marker was found.",
                "action": "State the bounded advance and distinguish it from verified prior work.",
            }
        )
    if len(re.findall(r"\b[A-Z][A-Za-z-]{3,}\b", text)) > 80:
        concerns.append(
            {
                "severity": "MINOR",
                "axis": "readability for nonspecialists",
                "concern": "The manuscript may rely heavily on unexplained specialist terminology.",
                "evidence": "High capitalized-token density in the supplied text.",
                "action": "Add plain-language context for the main problem, method, and implications.",
            }
        )
    result = {
        "review_basis": "LOCAL_MANUSCRIPT",
        "protocol_sha256": _sha256_bytes(protocol.encode("utf-8")),
        "manuscript_sha256": _sha256_file(manuscript),
        "axes": axes,
        "concerns": concerns,
        "severity_counts": {
            severity: sum(item["severity"] == severity for item in concerns)
            for severity in ("MAJOR", "MINOR")
        },
        "recommendation": "ADVISORY_REVISE" if concerns else "ADVISORY_NO_STRUCTURAL_BLOCKER",
        "not_assessed": [
            "scientific truth",
            "novelty against current literature",
            "statistical correctness without underlying data",
            "formal publication readiness",
        ],
    }
    return result, resource_paths


DISPATCH: dict[str, Callable[[dict[str, Any], Path], tuple[dict[str, Any], list[str]]]] = {
    "paperspine:contribution": _paperspine_contribution,
    "paperspine:results-validation": _paperspine_results,
    "paperspine:target-exemplar": _paperspine_exemplar,
    "paperspine:publication-production": _paperspine_publication,
    "nature:figure": _nature_figure,
    "nature:reviewer": _nature_reviewer,
}


def list_capabilities(*, root: Path | str = ROOT) -> dict[str, Any]:
    install_root = Path(root).resolve()
    registry = _registry(install_root)
    audit = audit_installation(root=install_root)
    return {
        "operation": "list-v41-provider-capabilities",
        "status": audit["status"],
        "providers": [
            {
                "provider_id": provider_id,
                "capabilities": record.get("capabilities", []),
                "entrypoint": record.get("entrypoint"),
                "modes": record.get("modes", []),
                "execution_class": record.get("execution_class"),
                "integrity": audit.get("providers", {}).get(provider_id, {}).get("integrity", "FAIL"),
            }
            for provider_id, record in sorted(registry.items())
        ],
        "findings": audit["findings"],
    }


def invoke_provider(
    provider_id: str,
    request: dict[str, Any],
    *,
    mode: str = "PUBLIC_CORE",
    formal: bool = False,
    root: Path | str = ROOT,
) -> dict[str, Any]:
    install_root = Path(root).resolve()
    base = {
        "operation": "invoke-v41-provider",
        "provider_id": provider_id,
        "mode": mode,
        "advisory_only": True,
        "formal_eligible": False,
        "truth_authority": "V4_CONTROL_PLANE",
    }
    if formal:
        return {
            **base,
            "status": "BLOCKED",
            "reason": "FORMAL_EVIDENCE_INCOMPLETE",
            "qualification_status": "UNAUDITED",
        }
    if mode not in MODES:
        return {**base, "status": "FAIL", "reason": "UNSUPPORTED_EXECUTION_MODE"}
    if not isinstance(request, dict):
        return {**base, "status": "FAIL", "reason": "REQUEST_MUST_BE_AN_OBJECT"}
    try:
        registry = _registry(install_root)
        record = registry.get(provider_id)
        if record is None or provider_id not in DISPATCH:
            raise AdapterError("UNKNOWN_PROVIDER")
        if mode not in record.get("modes", []):
            raise AdapterError("PROVIDER_NOT_AVAILABLE_IN_MODE")
        audit = audit_installation(root=install_root)
        provider_audit = audit.get("providers", {}).get(provider_id, {})
        if provider_audit.get("integrity") != "PASS":
            return {
                **base,
                "status": "BLOCKED",
                "reason": "RESOURCE_INTEGRITY_FAILURE",
                "findings": provider_audit.get("findings", audit.get("findings", [])),
                "qualification_status": _qualification_status(install_root, provider_id),
            }
        required = record.get("input_contract", {}).get("required", [])
        missing = [field for field in required if field not in request]
        if missing:
            raise AdapterError("missing request fields: " + ", ".join(sorted(missing)))
        result, executed = DISPATCH[provider_id](request, install_root)
        output = {
            **base,
            "status": "PASS",
            "capabilities": record.get("capabilities", []),
            "qualification_status": _qualification_status(install_root, provider_id),
            "result": result,
            "evidence": {
                "source_hash": record.get("source_hash"),
                "input_hash": _canonical_hash(request),
                "executed_resources": executed,
            },
        }
        output["evidence"]["output_hash"] = _canonical_hash(result)
        return output
    except (AdapterError, OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        return {
            **base,
            "status": "FAIL",
            "reason": str(error),
            "qualification_status": _qualification_status(install_root, provider_id),
        }


def paperspine_contribution(
    request: dict[str, Any], *, mode: str = "PUBLIC_CORE", formal: bool = False,
    root: Path | str = ROOT,
) -> dict[str, Any]:
    return invoke_provider("paperspine:contribution", request, mode=mode, formal=formal, root=root)


def paperspine_results_validation(
    request: dict[str, Any], *, mode: str = "PUBLIC_CORE", formal: bool = False,
    root: Path | str = ROOT,
) -> dict[str, Any]:
    return invoke_provider("paperspine:results-validation", request, mode=mode, formal=formal, root=root)


def paperspine_target_exemplar(
    request: dict[str, Any], *, mode: str = "PUBLIC_CORE", formal: bool = False,
    root: Path | str = ROOT,
) -> dict[str, Any]:
    return invoke_provider("paperspine:target-exemplar", request, mode=mode, formal=formal, root=root)


def paperspine_publication_production(
    request: dict[str, Any], *, mode: str = "PUBLIC_CORE", formal: bool = False,
    root: Path | str = ROOT,
) -> dict[str, Any]:
    return invoke_provider("paperspine:publication-production", request, mode=mode, formal=formal, root=root)


def nature_figure(
    request: dict[str, Any], *, mode: str = "PUBLIC_CORE", formal: bool = False,
    root: Path | str = ROOT,
) -> dict[str, Any]:
    return invoke_provider("nature:figure", request, mode=mode, formal=formal, root=root)


def nature_reviewer(
    request: dict[str, Any], *, mode: str = "PUBLIC_CORE", formal: bool = False,
    root: Path | str = ROOT,
) -> dict[str, Any]:
    return invoke_provider("nature:reviewer", request, mode=mode, formal=formal, root=root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="List integrity-checked local specialist providers.")
    audit = subparsers.add_parser("audit", help="Audit selected resources and adapter bindings.")
    audit.set_defaults(command="audit")
    invoke = subparsers.add_parser("invoke", help="Invoke one advisory local provider.")
    invoke.add_argument("provider_id")
    invoke.add_argument("--request", required=True, type=Path)
    invoke.add_argument("--mode", choices=sorted(MODES), default="PUBLIC_CORE")
    invoke.add_argument("--formal", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "list":
        result = list_capabilities()
    elif args.command == "audit":
        result = audit_installation()
    else:
        try:
            request = _read_json(args.request)
        except (OSError, ValueError, TypeError) as error:
            result = {
                "operation": "invoke-v41-provider",
                "provider_id": args.provider_id,
                "status": "FAIL",
                "reason": f"request could not be loaded: {error}",
            }
        else:
            result = invoke_provider(
                args.provider_id, request, mode=args.mode, formal=args.formal
            )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
