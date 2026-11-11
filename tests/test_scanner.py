"""Tests for read-only repository scanning and scoring."""

import json

import pytest
from click.testing import CliRunner

from repo_fixer.cli import main
from repo_fixer.scanner import _read, audit_repository


def make_complete_repo(root):
    readme = (
        "# Sample Project\n\n"
        "A useful project description with enough detail to explain its purpose.\n\n"
        "## Installation\n\nInstall it with pip.\n\n"
        "## Usage\n\nRun sample-command.\n"
    )
    (root / "README.md").write_text(readme, encoding="utf-8")
    required_files = (
        "LICENSE",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "CHANGELOG.md",
        ".gitignore",
    )
    for name in required_files:
        (root / name).write_text("present\n", encoding="utf-8")
    issue_dir = root / ".github" / "ISSUE_TEMPLATE"
    issue_dir.mkdir(parents=True)
    (issue_dir / "bug.yml").write_text("name: Bug\n", encoding="utf-8")
    workflow_dir = root / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    pr_template = root / ".github" / "PULL_REQUEST_TEMPLATE.md"
    pr_template.write_text("Summary\n", encoding="utf-8")


def test_complete_repository_scores_one_hundred(tmp_path):
    make_complete_repo(tmp_path)
    report = audit_repository(tmp_path)
    assert report.score == 100
    assert report.grade == "A"
    assert report.checks_passed == report.checks_total == 9
    assert report.findings == ()


def test_empty_repository_reports_all_nine_gaps(tmp_path):
    report = audit_repository(tmp_path)
    assert report.score == 0
    assert len(report.findings) == 9
    assert {item.check_id for item in report.findings} == {
        "README",
        "LICENSE",
        "CONTRIBUTING",
        "CODE_OF_CONDUCT",
        "ISSUE_TEMPLATES",
        "PR_TEMPLATE",
        "CI",
        "CHANGELOG",
        "GITIGNORE",
    }


def test_readme_quality_gaps_are_explained(tmp_path):
    (tmp_path / "README.md").write_text("# Name\n", encoding="utf-8")
    report = audit_repository(tmp_path)
    finding = next(item for item in report.findings if item.check_id == "README")
    assert finding.severity == "medium"
    assert "installation section" in finding.evidence
    assert finding.recommendation


def test_symlinked_license_does_not_count(tmp_path, symlink_supported: bool):
    outside = tmp_path.parent / "outside-license"
    outside.write_text("MIT", encoding="utf-8")
    (tmp_path / "LICENSE").symlink_to(outside)
    report = audit_repository(tmp_path)
    assert any(item.check_id == "LICENSE" for item in report.findings)


def test_invalid_repository_path_raises(tmp_path):
    with pytest.raises(ValueError, match="cannot be resolved"):
        audit_repository(tmp_path / "missing")


def test_file_path_is_rejected(tmp_path):
    file_path = tmp_path / "not-a-repo"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="not a directory"):
        audit_repository(file_path)


def test_scan_cli_supports_json_and_does_not_write(tmp_path):
    result = CliRunner().invoke(main, ["scan", str(tmp_path), "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["checks_total"] == 9
    assert not (tmp_path / "repo-fixer.yml").exists()


def test_score_cli_reports_explainable_score(tmp_path):
    result = CliRunner().invoke(main, ["score", str(tmp_path)])
    assert result.exit_code == 0
    assert "Readiness score: 0/100" in result.output
    assert "9 checks" in result.output


def test_scan_rejects_file_path(tmp_path):
    file_path = tmp_path / "not-a-repo"
    file_path.write_text("x", encoding="utf-8")
    result = CliRunner().invoke(main, ["scan", str(file_path)])
    assert result.exit_code != 0


def test_read_missing_file_returns_none(tmp_path) -> None:
    assert _read(tmp_path, "missing.txt") is None


def test_read_invalid_utf8_returns_none(tmp_path) -> None:
    (tmp_path / "README.md").write_bytes(b"\xff\xfe")
    assert _read(tmp_path, "README.md") is None
