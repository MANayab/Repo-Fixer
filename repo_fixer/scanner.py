"""Read-only repository essentials audit and explainable readiness scoring."""

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

Severity = Literal["critical", "high", "medium", "low", "info"]


@dataclass(frozen=True)
class Finding:
    """One evidence-backed audit finding."""

    check_id: str
    severity: Severity
    affected_file: str
    evidence: str
    recommendation: str


@dataclass(frozen=True)
class AuditReport:
    """Immutable audit results for one repository."""

    repository: str
    score: int
    grade: str
    checks_passed: int
    checks_total: int
    findings: tuple[Finding, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        return {
            "repository": self.repository,
            "score": self.score,
            "grade": self.grade,
            "checks_passed": self.checks_passed,
            "checks_total": self.checks_total,
            "findings": [asdict(item) for item in self.findings],
        }


_WEIGHTS = {
    "README": 20,
    "LICENSE": 15,
    "CONTRIBUTING": 10,
    "CODE_OF_CONDUCT": 8,
    "ISSUE_TEMPLATES": 10,
    "PR_TEMPLATE": 7,
    "CI": 15,
    "CHANGELOG": 8,
    "GITIGNORE": 7,
}
README_SECTIONS = {
    "installation": ("installation", "install", "getting started", "setup"),
    "usage": ("usage", "quick start", "quickstart", "examples"),
}


def _safe_file(root: Path, relative: str) -> Path | None:
    """Return a regular, non-symlink file contained by the repository."""
    candidate = root / relative
    try:
        if candidate.is_symlink() or not candidate.is_file():
            return None
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
        return resolved
    except (OSError, RuntimeError, ValueError):
        return None


def _safe_directory(root: Path, relative: str) -> Path | None:
    candidate = root / relative
    try:
        if candidate.is_symlink() or not candidate.is_dir():
            return None
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
        return resolved
    except (OSError, RuntimeError, ValueError):
        return None


def _read(root: Path, relative: str) -> str | None:
    path = _safe_file(root, relative)
    if path is None:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _finding(
    check_id: str,
    severity: Severity,
    path: str,
    evidence: str,
    recommendation: str,
) -> Finding:
    return Finding(check_id, severity, path, evidence, recommendation)


def audit_repository(repository: Path | str = ".") -> AuditReport:
    """Inspect repository essentials without writing files or accessing network."""
    supplied = Path(repository).expanduser()
    try:
        root = supplied.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError(
            f"Repository path cannot be resolved: {supplied}"
        ) from exc
    if not root.is_dir():
        raise ValueError(f"Repository path is not a directory: {root}")

    findings: list[Finding] = []
    passed: set[str] = set()
    readme_candidates = ("README.md", "README.rst", "README.txt", "README")
    readme_path = next(
        (name for name in readme_candidates if _safe_file(root, name)),
        None,
    )
    if readme_path is None:
        findings.append(
            _finding(
                "README",
                "high",
                "README.md",
                "No supported README file was found at the repository root.",
                (
                    "Add a README with a project overview, installation steps, "
                    "and usage examples."
                ),
            )
        )
    else:
        content = _read(root, readme_path) or ""
        missing: list[str] = []
        if not re.search(r"(?m)^#\s+\S", content):
            missing.append("top-level project heading")
        if len(re.sub(r"[#*\x60_>\-\s]", "", content)) < 80:
            missing.append("substantive project description")
        for label, aliases in README_SECTIONS.items():
            if not any(
                re.search(rf"(?im)^#+\s*.*{re.escape(alias)}", content)
                for alias in aliases
            ):
                missing.append(f"{label} section")
        if missing:
            findings.append(
                _finding(
                    "README",
                    "medium",
                    readme_path,
                    "Missing or weak elements: " + ", ".join(missing) + ".",
                    (
                        "Add a clear project heading, meaningful overview, "
                        "installation instructions, and practical usage examples."
                    ),
                )
            )
        else:
            passed.add("README")

    checks: list[tuple[str, tuple[str, ...], Severity, str]] = [
        (
            "LICENSE",
            ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"),
            "high",
            "Add a license file and state the chosen license clearly.",
        ),
        (
            "CONTRIBUTING",
            ("CONTRIBUTING.md", "CONTRIBUTING.rst", ".github/CONTRIBUTING.md"),
            "medium",
            (
                "Add contribution instructions covering setup, tests, "
                "and the review process."
            ),
        ),
        (
            "CODE_OF_CONDUCT",
            ("CODE_OF_CONDUCT.md", "CODE_OF_CONDUCT.rst", ".github/CODE_OF_CONDUCT.md"),
            "low",
            (
                "Add a Code of Conduct describing expected community behavior "
                "and reporting channels."
            ),
        ),
        (
            "PR_TEMPLATE",
            (
                ".github/PULL_REQUEST_TEMPLATE.md",
                ".github/pull_request_template.md",
                "PULL_REQUEST_TEMPLATE.md",
            ),
            "low",
            "Add a pull request template with summary, validation, and safety checks.",
        ),
        (
            "CHANGELOG",
            ("CHANGELOG.md", "CHANGES.md", "HISTORY.md"),
            "low",
            "Add a changelog to communicate user-visible changes between releases.",
        ),
        (
            "GITIGNORE",
            (".gitignore",),
            "low",
            (
                "Add a .gitignore for generated files, caches, virtual environments, "
                "and local secrets."
            ),
        ),
    ]
    for check_id, candidates, severity, recommendation in checks:
        found = next(
            (name for name in candidates if _safe_file(root, name)),
            None,
        )
        if found:
            passed.add(check_id)
        else:
            evidence = (
                "None of the recognized files were found: "
                + ", ".join(candidates)
                + "."
            )
            findings.append(
                _finding(
                    check_id,
                    severity,
                    candidates[0],
                    evidence,
                    recommendation,
                )
            )

    issue_dirs = (".github/ISSUE_TEMPLATE", ".github/issue_template")
    issue_dir = next(
        (name for name in issue_dirs if _safe_directory(root, name)),
        None,
    )
    issue_files: list[Path] = []
    if issue_dir:
        try:
            issue_files = [
                item
                for item in (root / issue_dir).iterdir()
                if not item.is_symlink() and item.is_file()
            ]
        except OSError:
            issue_files = []
    if issue_files:
        passed.add("ISSUE_TEMPLATES")
    else:
        findings.append(
            _finding(
                "ISSUE_TEMPLATES",
                "low",
                ".github/ISSUE_TEMPLATE/",
                (
                    "No recognized issue-template directory containing regular "
                    "files was found."
                ),
                (
                    "Add at least one GitHub issue template, such as a bug report "
                    "or feature request."
                ),
            )
        )

    workflows = _safe_directory(root, ".github/workflows")
    workflow_files: list[Path] = []
    if workflows:
        try:
            workflow_files = [
                item
                for item in workflows.iterdir()
                if not item.is_symlink()
                and item.is_file()
                and item.suffix.lower() in {".yml", ".yaml"}
            ]
        except OSError:
            workflow_files = []
    if workflow_files:
        passed.add("CI")
    else:
        findings.append(
            _finding(
                "CI",
                "medium",
                ".github/workflows/",
                (
                    "No regular .yml or .yaml workflow file was found "
                    "in .github/workflows/."
                ),
                (
                    "Add a GitHub Actions workflow that installs dependencies "
                    "and runs the project's relevant quality checks."
                ),
            )
        )

    total_weight = sum(_WEIGHTS.values())
    lost = sum(_WEIGHTS[item.check_id] for item in findings)
    score = max(0, round(100 * (total_weight - lost) / total_weight))
    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 60:
        grade = "D"
    else:
        grade = "F"
    return AuditReport(
        str(root),
        score,
        grade,
        len(passed),
        len(_WEIGHTS),
        tuple(findings),
    )
