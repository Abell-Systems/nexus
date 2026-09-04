#!/usr/bin/env python3
"""Docs-correctness gate: structural checks for docs/, no scientific validation duplicated.

Scope, deliberately kept small and deterministic:
- Every markdown file under docs/ is readable UTF-8, non-empty.
- Every ADR (docs/adr/NNNN-*.md) has the required header fields and a filename/number
  that matches its own title line, with no duplicate ADR numbers.
- Status is one of the vocabulary this repo already uses (Accepted, Proposed, Deprecated,
  Superseded) — not free text.
- Any "ADR NNNN" mention anywhere under docs/ refers to an ADR number that actually exists.
- Any relative markdown link ([text](path)) resolves to a real file. External (http/https)
  and in-page anchor (#...) links are skipped.

Explicitly out of scope: verifying hashes, config values, or scientific artifacts referenced
from prose (e.g. a specific policy_sha256 or model revision quoted in an ADR). That is what
the existing unit tests already verify against the real artifacts — duplicating it here would
be a second, weaker implementation of the same check, not a new guarantee.

Exit code 0 = all checks passed. Exit code 1 = at least one finding, printed to stdout.
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
ADR_DIR = DOCS_DIR / "adr"

ADR_FILENAME_RE = re.compile(r"^(\d{4})-[a-z0-9-]+\.md$")
ADR_TITLE_RE = re.compile(r"^# ADR (\d{4}):\s*\S")
STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(\S+)")
DATE_RE = re.compile(r"^\*\*Date:\*\*\s*\S")
ADR_MENTION_RE = re.compile(r"\bADR\s+(\d{4})\b")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

ALLOWED_STATUSES = {"Accepted", "Proposed", "Deprecated", "Superseded"}


def find_markdown_files() -> list[Path]:
    if not DOCS_DIR.exists():
        return []
    return sorted(DOCS_DIR.rglob("*.md"))


def check_readable(files: list[Path]) -> list[str]:
    findings = []
    for f in files:
        try:
            content = f.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            findings.append(f"{f.relative_to(REPO_ROOT)}: not valid UTF-8 ({e})")
            continue
        if not content.strip():
            findings.append(f"{f.relative_to(REPO_ROOT)}: empty file")
    return findings


def check_adr_structure() -> tuple[list[str], dict[str, Path]]:
    findings: list[str] = []
    numbers_seen: dict[str, Path] = {}

    if not ADR_DIR.exists():
        return findings, numbers_seen

    for f in sorted(ADR_DIR.glob("*.md")):
        rel = f.relative_to(REPO_ROOT)
        m = ADR_FILENAME_RE.match(f.name)
        if not m:
            findings.append(f"{rel}: filename does not match NNNN-slug.md")
            continue
        number = m.group(1)

        if number in numbers_seen:
            findings.append(
                f"{rel}: duplicate ADR number {number} (also used by "
                f"{numbers_seen[number].relative_to(REPO_ROOT)})"
            )
        else:
            numbers_seen[number] = f

        lines = f.read_text(encoding="utf-8").splitlines()
        title_line = next((line for line in lines if line.startswith("# ADR ")), None)
        if title_line is None:
            findings.append(f"{rel}: missing '# ADR NNNN: <title>' header line")
        else:
            title_match = ADR_TITLE_RE.match(title_line)
            if not title_match:
                findings.append(f"{rel}: title line does not match '# ADR NNNN: <title>': {title_line!r}")
            elif title_match.group(1) != number:
                findings.append(
                    f"{rel}: title declares ADR {title_match.group(1)} but filename number is {number}"
                )

        status_line = next((line for line in lines if line.startswith("**Status:**")), None)
        if status_line is None:
            findings.append(f"{rel}: missing '**Status:**' field")
        else:
            status_match = STATUS_RE.match(status_line)
            status = status_match.group(1) if status_match else None
            if status not in ALLOWED_STATUSES:
                findings.append(
                    f"{rel}: Status '{status}' not in allowed vocabulary {sorted(ALLOWED_STATUSES)}"
                )

        if not any(DATE_RE.match(line) for line in lines):
            findings.append(f"{rel}: missing '**Date:**' field")

    return findings, numbers_seen


def check_adr_cross_references(files: list[Path], known_adr_numbers: set[str]) -> list[str]:
    findings = []
    for f in files:
        content = f.read_text(encoding="utf-8")
        for match in ADR_MENTION_RE.finditer(content):
            number = match.group(1)
            if number not in known_adr_numbers:
                line_no = content.count("\n", 0, match.start()) + 1
                findings.append(
                    f"{f.relative_to(REPO_ROOT)}:{line_no}: references ADR {number}, "
                    "which does not exist under docs/adr/"
                )
    return findings


def check_relative_links(files: list[Path]) -> list[str]:
    """Verifies relative markdown links resolve to a real file inside the repo.

    A link target must resolve within REPO_ROOT before its existence is even checked — a
    path like `../../../../etc/passwd` must never be validated against the CI runner's
    filesystem, which has files this repo does not and should never care about. Escaping
    REPO_ROOT is itself a finding, independent of whether the escaped-to path happens to
    exist on whatever machine runs this check.
    """
    findings = []
    repo_root_resolved = REPO_ROOT.resolve()
    for f in files:
        content = f.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK_RE.finditer(content):
            target = match.group(1).strip()
            if not target or target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target_path = target.split("#", 1)[0]
            resolved = (f.parent / target_path).resolve()
            line_no = content.count("\n", 0, match.start()) + 1

            if not resolved.is_relative_to(repo_root_resolved):
                findings.append(
                    f"{f.relative_to(REPO_ROOT)}:{line_no}: link target escapes the repository: {target}"
                )
            elif not resolved.exists():
                findings.append(
                    f"{f.relative_to(REPO_ROOT)}:{line_no}: link target does not exist: {target}"
                )
    return findings


def main() -> int:
    files = find_markdown_files()
    if not files:
        print("No markdown files found under docs/ — nothing to check.")
        return 0

    findings: list[str] = []
    findings += check_readable(files)
    adr_findings, known_numbers = check_adr_structure()
    findings += adr_findings
    findings += check_adr_cross_references(files, set(known_numbers))
    findings += check_relative_links(files)

    if findings:
        print(f"Docs correctness gate: {len(findings)} finding(s):\n")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print(f"Docs correctness gate: PASS ({len(files)} markdown files, {len(known_numbers)} ADRs checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
