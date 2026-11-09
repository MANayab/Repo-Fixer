"""Tests for the command-line interface."""

import socket

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


def test_fix_remains_a_v03_placeholder(tmp_path) -> None:
    result = CliRunner().invoke(
        main,
        ["--config", str(tmp_path / "missing.yml"), "fix"],
    )
    assert result.exit_code == 0
    assert "coming in v0.3.0" in result.output


def test_cli_does_not_open_network_connections(monkeypatch, tmp_path) -> None:
    def blocked(*args, **kwargs):
        raise AssertionError("Unexpected network connection")

    monkeypatch.setattr(socket, "create_connection", blocked)
    result = CliRunner().invoke(
        main, ["--config", str(tmp_path / "none.yml"), "version"]
    )
    assert result.exit_code == 0
