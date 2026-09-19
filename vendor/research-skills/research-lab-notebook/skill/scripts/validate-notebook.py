#!/usr/bin/env python3
"""Validate the portable structural invariants of a research notebook."""

from __future__ import annotations

import argparse
import datetime
import json
import re
import tempfile
import urllib.parse
from dataclasses import dataclass
from pathlib import Path


SCHEMA_PATH = Path(__file__).resolve().parent.parent / "references" / "notebook-schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
REQUIRED_FILES = tuple(SCHEMA["required_files"])
STATUSES = set(SCHEMA["experiment_statuses"])
FINDING_STATUSES = set(SCHEMA["finding_statuses"])
LEDGER_FIELDS = set(SCHEMA["ledger"]["required_fields"])
STATUS_RE = re.compile(r"^\*\*Status\*\*:\s*([a-z-]+)", re.MULTILINE)
DATE_RE = re.compile(r"^\*\*Date\*\*:\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE)
HEADING_ID_RE = re.compile(r"^#\s+([A-Z][A-Z0-9]*-[A-Z0-9]+)\s*:", re.MULTILINE)
FILE_ID_RE = re.compile(r"^([A-Z][A-Z0-9]*-[A-Z0-9]+)(?:-|\.md$)")
EXPERIMENT_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[A-Z0-9]+$")
FINDING_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
PLAN_FILE_RE = FINDING_FILE_RE
BACKEND_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EXPERIMENT_REF_RE = re.compile(r"\b[A-Z][A-Z0-9]*-[A-Z0-9]+\b")
CLAIM_ID_RE = re.compile(r"^C\d+$", re.IGNORECASE)
CLAIM_EXPERIMENT_PATH_RE = re.compile(
    r"(?i)(?:(?:lab-notebook/)?experiments/)[A-Za-z0-9_./-]+\.md"
)
CLAIM_FINDING_PATH_RE = re.compile(
    r"(?i)(?:(?:lab-notebook/)?findings/)[A-Za-z0-9_./-]+\.md"
)
CLAIM_PAPER_PATH_RE = re.compile(
    r"(?i)(?:(?:lab-notebook/)?papers/)[A-Za-z0-9_./-]+\.(?:md|typ|tex)"
)
MARKDOWN_LINK_RE = re.compile(r"\[[^]]+\]\(([^)]+)\)")


@dataclass(frozen=True)
class Issue:
    level: str
    path: Path
    message: str

    def render(self, root: Path) -> str:
        try:
            display = self.path.relative_to(root)
        except ValueError:
            display = self.path
        return f"{self.level}: {display}: {self.message}"

    def as_dict(self, root: Path) -> dict[str, str]:
        try:
            display = self.path.relative_to(root).as_posix()
        except ValueError:
            display = str(self.path)
        return {"level": self.level.lower(), "path": display, "message": self.message}


def notebook_path(candidate: Path) -> Path:
    nested = candidate / "lab-notebook"
    return nested if nested.is_dir() else candidate


def read_text(path: Path, issues: list[Issue]) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        issues.append(Issue("ERROR", path, "file is not valid UTF-8"))
    except OSError as error:
        issues.append(Issue("ERROR", path, f"could not read file: {error}"))
    return None


def has_heading(text: str, heading: str) -> bool:
    return re.search(rf"^#+\s+{re.escape(heading)}\s*$", text, re.MULTILINE) is not None


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip()] = value.strip().strip("'\"")
    return values


def valid_date(value: str) -> bool:
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def valid_timestamp(value: str) -> bool:
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def ledger_filename(job_id: str) -> str:
    encoded = urllib.parse.quote(job_id, safe="-_")
    if encoded in {".", ".."}:
        encoded = encoded.replace(".", "%2E")
    return f"{encoded}.json"


def validate_index_membership(
    index_path: Path,
    records: list[tuple[Path, tuple[str, ...]]],
    issues: list[Issue],
) -> None:
    text = read_text(index_path, issues)
    if text is None:
        return
    for path, identifiers in records:
        if not any(identifier in text for identifier in identifiers):
            issues.append(Issue("ERROR", path, f"not listed in {index_path.name}"))


def validate_experiments(root: Path, issues: list[Issue]) -> None:
    experiment_dir = root / "experiments"
    seen: dict[str, Path] = {}
    records: list[tuple[Path, tuple[str, ...]]] = []
    for path in sorted(experiment_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        text = read_text(path, issues)
        if text is None:
            continue

        file_match = FILE_ID_RE.match(path.name)
        heading_match = HEADING_ID_RE.search(text)
        experiment_id = heading_match.group(1) if heading_match else None
        if not file_match:
            issues.append(Issue("ERROR", path, "filename does not start with an experiment ID"))
        if experiment_id is None:
            issues.append(Issue("ERROR", path, "first heading lacks an experiment ID"))
        elif file_match and experiment_id != file_match.group(1):
            issues.append(
                Issue(
                    "ERROR",
                    path,
                    f"heading ID {experiment_id} does not match filename ID {file_match.group(1)}",
                )
            )

        if experiment_id:
            previous = seen.get(experiment_id)
            if previous:
                issues.append(
                    Issue("ERROR", path, f"duplicate experiment ID also used by {previous.name}")
                )
            else:
                seen[experiment_id] = path
            records.append((path, (experiment_id, path.name, path.stem)))

        status_match = STATUS_RE.search(text)
        if not status_match:
            issues.append(Issue("ERROR", path, "missing **Status** field"))
            continue
        status = status_match.group(1)
        if status not in STATUSES:
            issues.append(Issue("ERROR", path, f"unknown experiment status {status!r}"))

        designed = {"planned", "queued", "running", "in-progress", "pilot-complete", "completed"}
        if status in designed:
            for heading in (
                "Hypothesis",
                "Method",
                "Preregistered predictions (a priori)",
                "Decision rule (a priori)",
            ):
                if not has_heading(text, heading):
                    issues.append(Issue("ERROR", path, f"missing ## {heading} section"))
        if status in {"queued", "running", "pilot-complete", "completed"}:
            if not has_heading(text, "Runs"):
                issues.append(Issue("ERROR", path, "missing ## Runs section"))
        if status == "completed":
            for heading in (
                "Results",
                "Outcomes against preregistered predictions",
                "Conclusion",
                "Artifacts",
            ):
                if not has_heading(text, heading):
                    issues.append(
                        Issue("ERROR", path, f"completed experiment lacks ## {heading}")
                    )
        if status == "proposed":
            for heading in ("Hypothesis", "Method"):
                if not has_heading(text, heading):
                    issues.append(Issue("WARNING", path, f"proposed experiment lacks ## {heading}"))
        if status == "abandoned" and not has_heading(text, "Conclusion"):
            issues.append(Issue("WARNING", path, "abandoned experiment lacks ## Conclusion"))

    validate_index_membership(experiment_dir / "README.md", records, issues)


def validate_findings(root: Path, issues: list[Issue]) -> None:
    finding_dir = root / "findings"
    records: list[tuple[Path, tuple[str, ...]]] = []
    for path in sorted(finding_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        text = read_text(path, issues)
        if text is None:
            continue
        file_match = FINDING_FILE_RE.fullmatch(path.name)
        if not file_match:
            issues.append(
                Issue("ERROR", path, "filename must be YYYY-MM-DD-lowercase-topic.md")
            )
        date_match = DATE_RE.search(text)
        if not date_match:
            issues.append(Issue("ERROR", path, "missing **Date** field"))
        else:
            date = date_match.group(1)
            if not valid_date(date):
                issues.append(Issue("ERROR", path, f"invalid date {date!r}"))
            if file_match and date != file_match.group(1):
                issues.append(Issue("ERROR", path, "Date field does not match filename"))
        status_match = STATUS_RE.search(text)
        if not status_match:
            issues.append(Issue("ERROR", path, "missing **Status** field"))
        elif status_match.group(1) not in FINDING_STATUSES:
            issues.append(
                Issue("ERROR", path, f"unknown finding status {status_match.group(1)!r}")
            )
        references = set(EXPERIMENT_REF_RE.findall(text))
        if len(references) < 2:
            issues.append(
                Issue("ERROR", path, "finding must link at least two experiments")
            )
        for heading in (
            "Claim",
            "Evidence",
            "Synthesis",
            "Scope and threats to validity",
            "Consequences",
            "Sources",
        ):
            if not has_heading(text, heading):
                issues.append(Issue("ERROR", path, f"missing ## {heading} section"))
        records.append((path, (path.name, path.stem)))
    validate_index_membership(finding_dir / "README.md", records, issues)


def table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def evidence_path(root: Path, reference: str) -> Path:
    relative = Path(reference)
    if relative.parts and relative.parts[0] == "lab-notebook":
        relative = Path(*relative.parts[1:])
    return root / relative


def experiment_exists(root: Path, experiment_id: str) -> bool:
    normalized = experiment_id.casefold()
    for path in (root / "experiments").glob("*.md"):
        stem = path.stem.casefold()
        if stem == normalized:
            return True
        if stem.startswith(normalized):
            suffix = stem[len(normalized):]
            if suffix and not suffix[0].isalnum():
                return True
    return False


def validate_claims(root: Path, issues: list[Issue]) -> None:
    path = root / "CLAIMS.md"
    if not path.is_file():
        return
    text = read_text(path, issues)
    if text is None:
        return
    lines = text.splitlines()
    expected_columns = SCHEMA["claim"]["columns"]
    header_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.lstrip().startswith("|") and table_cells(line) == expected_columns
        ),
        None,
    )
    if header_index is None:
        issues.append(
            Issue("ERROR", path, f"claim table must use columns: {' | '.join(expected_columns)}")
        )
        return
    seen: set[str] = set()
    saw_row = False
    for line_number, line in enumerate(lines[header_index + 2 :], start=header_index + 3):
        if not line.lstrip().startswith("|"):
            break
        cells = table_cells(line)
        if len(cells) != len(expected_columns):
            issues.append(Issue("ERROR", path, f"line {line_number}: claim row has {len(cells)} columns"))
            continue
        saw_row = True
        claim_id, role, claim, status, evidence, paper = cells
        if not CLAIM_ID_RE.fullmatch(claim_id):
            issues.append(Issue("ERROR", path, f"line {line_number}: invalid claim ID {claim_id!r}"))
        normalized_id = claim_id.casefold()
        if normalized_id in seen:
            issues.append(Issue("ERROR", path, f"line {line_number}: duplicate claim ID {claim_id}"))
        seen.add(normalized_id)
        if role not in SCHEMA["claim"]["roles"]:
            issues.append(Issue("ERROR", path, f"line {line_number}: invalid claim role {role!r}"))
        if not claim:
            issues.append(Issue("ERROR", path, f"line {line_number}: claim text is empty"))
        if status not in SCHEMA["claim"]["statuses"]:
            issues.append(Issue("ERROR", path, f"line {line_number}: invalid claim status {status!r}"))
        if not paper:
            issues.append(Issue("ERROR", path, f"line {line_number}: paper key is empty"))
        if not evidence:
            issues.append(Issue("ERROR", path, f"line {line_number}: evidence is empty"))
            continue

        experiment_paths = CLAIM_EXPERIMENT_PATH_RE.findall(evidence)
        evidence_without_paths = CLAIM_EXPERIMENT_PATH_RE.sub(" ", evidence)
        finding_paths = CLAIM_FINDING_PATH_RE.findall(evidence_without_paths)
        evidence_without_paths = CLAIM_FINDING_PATH_RE.sub(" ", evidence_without_paths)
        experiment_ids = sorted(set(EXPERIMENT_REF_RE.findall(evidence_without_paths)))
        resolved_experiment = False
        for reference in experiment_paths:
            target = evidence_path(root, reference)
            if target.is_file():
                resolved_experiment = True
            else:
                issues.append(Issue("ERROR", path, f"line {line_number}: missing experiment path {reference}"))
        for experiment_id in experiment_ids:
            if experiment_exists(root, experiment_id):
                resolved_experiment = True
            else:
                issues.append(Issue("ERROR", path, f"line {line_number}: no record for {experiment_id}"))
        for reference in finding_paths:
            if not evidence_path(root, reference).is_file():
                issues.append(Issue("ERROR", path, f"line {line_number}: missing finding path {reference}"))
        if CLAIM_PAPER_PATH_RE.search(evidence):
            issues.append(Issue("ERROR", path, f"line {line_number}: papers cannot be evidence sources"))
        if not resolved_experiment:
            issues.append(
                Issue(
                    "ERROR",
                    path,
                    f"line {line_number}: evidence must cite at least one experiment record; findings cannot replace it",
                )
            )
    if not saw_row:
        issues.append(Issue("WARNING", path, "claim table has no rows"))


def plan_paths(root: Path) -> list[Path]:
    plan_dir = root / "plans"
    if not plan_dir.is_dir():
        return []
    return [
        path
        for path in sorted(plan_dir.rglob("*.md"))
        if path.name != "README.md"
    ]


def plan_link_path(root: Path, source: Path, reference: str) -> Path:
    clean = reference.split("#", 1)[0]
    if clean.startswith("lab-notebook/"):
        return root / clean.removeprefix("lab-notebook/")
    if clean.startswith(("plans/", "experiments/", "findings/")):
        return root / clean
    return source.parent / clean


def validate_plan_links(root: Path, path: Path, text: str, issues: list[Issue]) -> None:
    for reference in MARKDOWN_LINK_RE.findall(text):
        if reference.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = plan_link_path(root, path, reference)
        if target.suffix.lower() == ".md" and not target.is_file():
            issues.append(Issue("ERROR", path, f"broken plan link {reference}"))


def validate_plans(root: Path, issues: list[Issue]) -> None:
    plan_dir = root / "plans"
    if not plan_dir.is_dir():
        return
    plan_schema = SCHEMA["plan"]
    seen_stems: dict[str, Path] = {}
    for path in plan_paths(root):
        relative = path.relative_to(plan_dir)
        previous = seen_stems.get(path.stem)
        if previous is not None:
            issues.append(
                Issue("ERROR", path, f"duplicate plan basename also used by {previous.as_posix()}")
            )
        seen_stems[path.stem] = relative
        text = read_text(path, issues)
        if text is None:
            continue
        file_match = PLAN_FILE_RE.fullmatch(path.name)
        if not file_match:
            issues.append(
                Issue("ERROR", path, "filename must be YYYY-MM-DD-lowercase-topic.md")
            )
        metadata = frontmatter(text)
        if not metadata:
            issues.append(Issue("ERROR", path, "missing YAML frontmatter"))
            continue
        missing = [
            key for key in plan_schema["required_frontmatter"] if key not in metadata
        ]
        if missing:
            issues.append(
                Issue("ERROR", path, f"missing frontmatter: {', '.join(missing)}")
            )
        status = metadata.get("status", "")
        if status not in plan_schema["statuses"]:
            issues.append(Issue("ERROR", path, f"unknown plan status {status!r}"))
        expected_dir = plan_schema["status_directories"].get(status)
        actual_dir = "." if relative.parent == Path(".") else relative.parts[0]
        if expected_dir is not None and actual_dir != expected_dir:
            issues.append(
                Issue("ERROR", path, f"status {status!r} belongs in {expected_dir}/")
            )
        for field in ("created", "updated"):
            value = metadata.get(field)
            if value is not None and not valid_date(value):
                issues.append(Issue("ERROR", path, f"{field} must be YYYY-MM-DD"))
        created = metadata.get("created", "")
        updated = metadata.get("updated", "")
        if file_match and valid_date(created) and created != file_match.group(1):
            issues.append(Issue("ERROR", path, "created date does not match filename"))
        if valid_date(created) and valid_date(updated) and updated < created:
            issues.append(Issue("ERROR", path, "updated date precedes created date"))
        if not metadata.get("summary", "").strip():
            issues.append(Issue("ERROR", path, "summary must be non-empty"))
        next_action = metadata.get("next_action", "").strip()
        if status in plan_schema["terminal_statuses"]:
            if next_action.lower() not in {"", "none", "null", "~"}:
                issues.append(
                    Issue("ERROR", path, "terminal plan next_action must be empty or none")
                )
            for heading in plan_schema["terminal_sections"]:
                if not has_heading(text, heading):
                    issues.append(
                        Issue("ERROR", path, f"terminal plan lacks ## {heading}")
                    )
        elif not next_action:
            issues.append(Issue("ERROR", path, "nonterminal plan needs next_action"))
        for field in plan_schema["required_frontmatter_by_status"].get(status, []):
            if not metadata.get(field, "").strip():
                issues.append(Issue("ERROR", path, f"{status} plan requires {field}"))
        alternatives = plan_schema["one_of_frontmatter_by_status"].get(status, [])
        if alternatives and not any(metadata.get(field, "").strip() for field in alternatives):
            issues.append(
                Issue("ERROR", path, f"{status} plan requires one of: {', '.join(alternatives)}")
            )
        if status in {"active", "blocked", "gated"} and not metadata.get("current_phase", "").strip():
            issues.append(Issue("WARNING", path, f"{status} plan has no current_phase"))
        for heading in plan_schema["required_sections"]:
            if not has_heading(text, heading):
                issues.append(Issue("ERROR", path, f"missing ## {heading} section"))
        validate_plan_links(root, path, text, issues)


def first_heading(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def render_plan_index(root: Path) -> str:
    plan_dir = root / "plans"
    groups: dict[str, list[tuple[Path, str, dict[str, str]]]] = {
        status: [] for status in SCHEMA["plan"]["statuses"]
    }
    for path in plan_paths(root):
        text = path.read_text(encoding="utf-8")
        metadata = frontmatter(text)
        status = metadata.get("status", "")
        if status in groups:
            groups[status].append(
                (path.relative_to(plan_dir), first_heading(text, path.stem), metadata)
            )
    lines = [
        "# Plans",
        "",
        "Generated from plan frontmatter. Active plans live at the top level; other",
        "statuses live in matching subdirectories.",
        "",
    ]
    for status in SCHEMA["plan"]["statuses"]:
        records = groups[status]
        if not records:
            continue
        lines.extend((f"## {status.title()}", ""))
        for relative, title, metadata in sorted(records, key=lambda item: item[0].as_posix()):
            lines.append(f"- [{title}]({relative.as_posix()}): {metadata.get('summary', '').strip()}")
            next_action = metadata.get("next_action", "").strip()
            if next_action.lower() not in {"", "none", "null", "~"}:
                lines.append(f"  Next: {next_action}")
            for field, label in (
                ("gate", "Gate"),
                ("revisit_when", "Revisit"),
                ("promote_when", "Promote"),
                ("superseded_by", "Superseded by"),
                ("abandoned_because", "Abandoned because"),
            ):
                value = metadata.get(field, "").strip()
                if value:
                    lines.append(f"  {label}: {value}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def validate_ledger(root: Path, issues: list[Issue]) -> None:
    ledger_root = root / "jobs" / "processed"
    if not ledger_root.exists():
        return
    seen: set[tuple[str, str]] = set()
    for path in sorted(ledger_root.rglob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            issues.append(Issue("ERROR", path, f"invalid JSON: {error.msg}"))
            continue
        except UnicodeDecodeError:
            issues.append(Issue("ERROR", path, "file is not valid UTF-8"))
            continue
        except OSError as error:
            issues.append(Issue("ERROR", path, f"could not read file: {error}"))
            continue
        if not isinstance(record, dict):
            issues.append(Issue("ERROR", path, "ledger record must be a JSON object"))
            continue
        missing = sorted(LEDGER_FIELDS - record.keys())
        if missing:
            issues.append(Issue("ERROR", path, f"missing fields: {', '.join(missing)}"))
            continue
        backend = record["backend"]
        job_id = record["job_id"]
        if not isinstance(backend, str) or not isinstance(job_id, str):
            issues.append(Issue("ERROR", path, "backend and job_id must be strings"))
            continue
        key = (backend, job_id)
        if key in seen:
            issues.append(Issue("ERROR", path, f"duplicate ledger key {backend}:{job_id}"))
        seen.add(key)
        if path.parent.name != backend:
            issues.append(Issue("ERROR", path, "backend field does not match parent directory"))
        if not BACKEND_RE.fullmatch(backend):
            issues.append(Issue("ERROR", path, f"invalid normalized backend {backend!r}"))
        if path.name != ledger_filename(job_id):
            issues.append(Issue("ERROR", path, "filename is not the encoded job_id"))
        if record["schema_version"] != SCHEMA["ledger"]["schema_version"]:
            issues.append(Issue("ERROR", path, "unsupported schema_version"))
        if record["terminal_status"] not in SCHEMA["ledger"]["terminal_statuses"]:
            issues.append(Issue("ERROR", path, "invalid terminal_status"))
        experiment_id = record["experiment_id"]
        if not isinstance(experiment_id, str) or not EXPERIMENT_ID_RE.fullmatch(experiment_id):
            issues.append(Issue("ERROR", path, "experiment_id must be a non-empty experiment ID"))
        processed_at = record["processed_at"]
        if not isinstance(processed_at, str) or not valid_timestamp(processed_at):
            issues.append(Issue("ERROR", path, "processed_at must be an ISO 8601 timestamp with timezone"))
        revision = record["notebook_revision"]
        if not isinstance(revision, str) or not revision.strip():
            issues.append(Issue("ERROR", path, "notebook_revision must be a non-empty string"))
        evidence = record["evidence"]
        if not isinstance(evidence, list) or not evidence:
            issues.append(Issue("ERROR", path, "evidence must be a non-empty list"))
            continue
        for item in evidence:
            if not isinstance(item, str):
                issues.append(Issue("ERROR", path, "evidence entries must be strings"))
                continue
            relative = Path(item)
            if relative.is_absolute() or ".." in relative.parts:
                issues.append(Issue("ERROR", path, f"evidence path must stay inside notebook: {item}"))
                continue
            evidence_path = (root / relative).resolve()
            if not evidence_path.is_relative_to(root):
                issues.append(Issue("ERROR", path, f"evidence path escapes notebook: {item}"))
            elif not evidence_path.is_file():
                issues.append(Issue("ERROR", path, f"evidence path does not exist: {item}"))


def validate(candidate: Path) -> tuple[Path, list[Issue]]:
    root = notebook_path(candidate.resolve())
    issues: list[Issue] = []
    if not root.is_dir():
        return root, [Issue("ERROR", root, "notebook directory does not exist")]
    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.is_file():
            issues.append(Issue("ERROR", path, "required file is missing"))
    if (root / "experiments").is_dir():
        validate_experiments(root, issues)
    if (root / "findings").is_dir():
        validate_findings(root, issues)
    validate_claims(root, issues)
    validate_plans(root, issues)
    validate_ledger(root, issues)
    return root, issues


def diagnostics_report(root: Path, issues: list[Issue], strict: bool) -> dict[str, object]:
    errors = sum(issue.level == "ERROR" for issue in issues)
    warnings = sum(issue.level == "WARNING" for issue in issues)
    return {
        "schema_version": 1,
        "notebook_schema_version": SCHEMA["schema_version"],
        "notebook": str(root),
        "valid": errors == 0 and (warnings == 0 or not strict),
        "strict": strict,
        "counts": {"errors": errors, "warnings": warnings},
        "issues": [issue.as_dict(root) for issue in issues],
    }


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="validate-notebook-") as temporary:
        root = Path(temporary) / "lab-notebook"
        for relative in REQUIRED_FILES:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Placeholder\n", encoding="utf-8")
        experiment = root / "experiments" / "EXP-001-example.md"
        experiment.write_text(
            """# EXP-001: Example

**Status**: completed

## Hypothesis

Example.

## Method

Example.

## Preregistered predictions (a priori)

- **P1**: Example.

## Decision rule (a priori)

- **If P1 holds**: Continue.

## Runs

| Backend | Job ID |
|---|---|
| local | synthetic |

## Results

Example.

### Outcomes against preregistered predictions

| Prediction | Verdict |
|---|---|
| P1 | confirmed |

## Conclusion

Example.

## Artifacts

- `results/example.json`
""",
            encoding="utf-8",
        )
        (root / "experiments" / "README.md").write_text(
            "# Experiments\n\n- [[EXP-001-example]]\n", encoding="utf-8"
        )
        _, valid_issues = validate(root)
        if any(issue.level == "ERROR" for issue in valid_issues):
            for issue in valid_issues:
                print(issue.render(root))
            return 1
        experiment.write_text(
            experiment.read_text(encoding="utf-8").replace("completed", "finished"),
            encoding="utf-8",
        )
        _, invalid_issues = validate(root)
        if not any("unknown experiment status" in issue.message for issue in invalid_issues):
            print("ERROR: self-test did not detect an invalid status")
            return 1
    print("validate-notebook self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, help="project or notebook path")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Diagnostic output format",
    )
    parser.add_argument(
        "--write-plan-index",
        action="store_true",
        help="Regenerate plans/README.md from plan frontmatter before validation",
    )
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.path is None:
        parser.error("path is required unless --self-test is used")
    notebook = notebook_path(args.path.resolve())
    if args.write_plan_index:
        plan_dir = notebook / "plans"
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / "README.md").write_text(render_plan_index(notebook), encoding="utf-8")
    root, issues = validate(args.path)
    errors = sum(issue.level == "ERROR" for issue in issues)
    warnings = sum(issue.level == "WARNING" for issue in issues)
    if args.format == "json":
        print(json.dumps(diagnostics_report(root, issues, args.strict), indent=2))
        return 1 if errors or (args.strict and warnings) else 0
    for issue in issues:
        print(issue.render(root))
    if errors or (args.strict and warnings):
        print(f"{errors} error(s), {warnings} warning(s)")
        return 1
    print(f"Notebook structure valid ({warnings} warning(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
