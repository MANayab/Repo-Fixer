"""Tests for the command-line interface."""

import json
import runpy
import socket
import sys

import pytest
from click.testing import CliRunner

from repo_fixer import __version__
from repo_fixer.cli import main


def test_package_imports_with_version() -> None:
    assert __version__ == "0.2.0"


def test_help_lists_commands() -> None:
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    for command in ("version", "scan", "fix", "init", "score"):
        assert command in result.output


def test_version_command() -> None:
    result = CliRunner().invoke(main, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_init_creates_valid_configuration(tmp_path) -> None:
    path = tmp_path / "repo-fixer.yml"
    result = CliRunner().invoke(main, ["--config", str(path), "init"])
    assert result.exit_code == 0
    assert path.is_file()
    assert "license: MIT" in path.read_text(encoding="utf-8")


def test_init_refuses_to_overwrite_existing_file(tmp_path) -> None:
    path = tmp_path / "repo-fixer.yml"
    path.write_text("keep: me\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["--config", str(path), "init"])
    assert result.exit_code != 0
    assert "refusing to overwrite" in result.output
    assert path.read_text(encoding="utf-8") == "keep: me\n"


def test_init_reports_filesystem_error(tmp_path) -> None:
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("block", encoding="utf-8")
    config = blocker / "repo-fixer.yml"
    result = CliRunner().invoke(main, ["--config", str(config), "init"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_fix_dry_run_does_not_create_files(tmp_path) -> None:
    result = CliRunner().invoke(main, ["fix", "--dry-run", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "Repo Fixer Fix Plan" in result.output
    assert "No files were modified" in result.output
    assert list(tmp_path.iterdir()) == []


def test_fix_yes_creates_missing_files(tmp_path) -> None:
    result = CliRunner().invoke(
        main, ["fix", "--yes", "--license", "MIT", "--path", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert (tmp_path / "README.md").is_file()
    assert (tmp_path / "LICENSE").is_file()
    assert "Fix summary" in result.output


def test_fix_does_not_replace_existing_readme_without_force(tmp_path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Existing notes", encoding="utf-8")
    result = CliRunner().invoke(main, ["fix", "--yes", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert readme.read_text(encoding="utf-8") == "# Existing notes"
    assert (tmp_path / "repo-fixer-proposed-README.md").is_file()


def test_force_requires_explicit_confirmation_even_with_yes(tmp_path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Weak", encoding="utf-8")
    result = CliRunner().invoke(
        main, ["fix", "--force", "--yes", "--license", "MIT", "--path", str(tmp_path)],
        input="n\\n",
    )
    assert result.exit_code == 0
    assert readme.read_text(encoding="utf-8") == "# Weak"
    assert "Cancelled" in result.output


def test_cli_rejects_invalid_config(tmp_path) -> None:
    config = tmp_path / "repo-fixer.yml"
    config.write_text("unknown_setting: true\n", encoding="utf-8")
    result = CliRunner().invoke(
        main,
        ["--config", str(config), "scan", str(tmp_path)],
    )
    assert result.exit_code != 0
    assert "Invalid configuration" in result.output


def test_scan_cli_text_lists_findings(tmp_path) -> None:
    result = CliRunner().invoke(main, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert "Findings:" in result.output
    assert "[HIGH] README" in result.output


def test_scan_cli_text_reports_clean_repository(tmp_path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Project\n\n"
        "This project has a substantive description for users and contributors.\n\n"
        "## Installation\n\nInstall it.\n\n"
        "## Usage\n\nRun it.\n",
        encoding="utf-8",
    )
    for name in (
        "LICENSE",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "CHANGELOG.md",
        ".gitignore",
    ):
        (tmp_path / name).write_text("present\n", encoding="utf-8")
    issue_dir = tmp_path / ".github" / "ISSUE_TEMPLATE"
    issue_dir.mkdir(parents=True)
    (issue_dir / "bug.yml").write_text("name: Bug\n", encoding="utf-8")
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (tmp_path / ".github" / "PULL_REQUEST_TEMPLATE.md").write_text(
        "Summary\n",
        encoding="utf-8",
    )
    result = CliRunner().invoke(main, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert "No gaps found" in result.output


def test_score_cli_supports_json(tmp_path) -> None:
    result = CliRunner().invoke(
        main,
        ["score", str(tmp_path), "--format", "json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["score"] == 0
    assert payload["checks_total"] == 9


def test_cli_does_not_open_network_connections(monkeypatch, tmp_path) -> None:
    def blocked(*args, **kwargs):
        raise AssertionError("Unexpected network connection")

    monkeypatch.setattr(socket, "create_connection", blocked)
    result = CliRunner().invoke(
        main, ["--config", str(tmp_path / "none.yml"), "version"]
    )
    assert result.exit_code == 0


def test_python_module_entrypoint_runs(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["repo_fixer", "version"])
    with pytest.raises(SystemExit) as error:
        runpy.run_module("repo_fixer", run_name="__main__")
    assert error.value.code == 0
    assert "Repo Fixer 0.2.0" in capsys.readouterr().out
