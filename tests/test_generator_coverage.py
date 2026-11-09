"""Additional behavioral coverage for generator safety paths."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from repo_fixer.cli import main
from repo_fixer.config import load_config
from repo_fixer.generator import (
    FixPlan,
    PlannedFile,
    _license_text,
    _regular_file,
    _safe_target,
    apply_plan,
    build_plan,
    detect_language,
)


def test_detect_language_prefers_python_marker_order(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("", encoding="utf-8")
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    assert detect_language(tmp_path) == "python"


def test_detect_language_ignores_symlink_marker(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-package.json"
    outside.write_text("{}", encoding="utf-8")
    (tmp_path / "package.json").symlink_to(outside)
    assert detect_language(tmp_path) == "unknown"


def test_regular_file_rejects_directory(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").mkdir()
    assert _regular_file(tmp_path, "pyproject.toml") is False


@pytest.mark.parametrize("relative", ["/absolute", "../escape", "nested/../../escape"])
def test_safe_target_rejects_unsafe_relative_paths(
    tmp_path: Path, relative: str
) -> None:
    with pytest.raises(ValueError, match="Unsafe generated path"):
        _safe_target(tmp_path, relative)


def test_safe_target_rejects_symlink_component(tmp_path: Path) -> None:
    outside = tmp_path.parent / "repo-fixer-outside-target"
    outside.mkdir(exist_ok=True)
    (tmp_path / "nested").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        _safe_target(tmp_path, "nested/file.txt")


def test_license_text_rejects_unknown_license() -> None:
    with pytest.raises(ValueError, match="Choose one of"):
        _license_text("Unknown", 2026, "Owner")


def test_apply_plan_skips_existing_regular_file_without_force(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("keep", encoding="utf-8")
    plan = FixPlan(
        tmp_path,
        (PlannedFile("README.md", "new", "test"),),
        (),
        (),
        (),
    )
    created, skipped = apply_plan(plan)
    assert created == []
    assert target.read_text(encoding="utf-8") == "keep"
    assert skipped == ["README.md — already exists; existing file preserved"]


def test_apply_plan_refuses_force_replacement_of_directory(tmp_path: Path) -> None:
    (tmp_path / "README.md").mkdir()
    plan = FixPlan(
        tmp_path,
        (),
        (PlannedFile("README.md", "new", "replace", True),),
        (),
        (),
    )
    created, skipped = apply_plan(plan, force=True)
    assert created == []
    assert any("not a regular file" in item for item in skipped)


def test_apply_plan_preserves_license_selection_note_in_plan_only(tmp_path: Path) -> None:
    plan = FixPlan(
        tmp_path,
        (),
        (),
        ("LICENSE — selection required; choose one",),
        (),
    )
    created, skipped = apply_plan(plan)
    assert created == []
    assert skipped == []


def test_apply_plan_propagates_io_error_without_silent_overwrite(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plan = FixPlan(
        tmp_path,
        (PlannedFile("README.md", "content", "test"),),
        (),
        (),
        (),
    )

    def denied(*args: object, **kwargs: object) -> int:
        raise PermissionError("denied")

    monkeypatch.setattr(os, "open", denied)
    with pytest.raises(PermissionError, match="denied"):
        apply_plan(plan)
    assert not (tmp_path / "README.md").exists()


def test_build_plan_records_existing_license_as_unchanged(tmp_path: Path) -> None:
    (tmp_path / "LICENSE").write_text("custom", encoding="utf-8")
    plan = build_plan(tmp_path)
    assert "LICENSE — already present" in plan.unchanged
    assert not any(item.path == "LICENSE" for item in plan.created)


def test_build_plan_skips_existing_proposed_readme_target(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# weak", encoding="utf-8")
    (tmp_path / "repo-fixer-proposed-README.md").write_text(
        "keep", encoding="utf-8"
    )
    plan = build_plan(tmp_path)
    assert any("proposed file already exists" in item for item in plan.skipped)


def test_build_plan_rejects_file_as_repository(tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-repo"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="not a directory"):
        build_plan(file_path)


def test_empty_plan_property_is_true(tmp_path: Path) -> None:
    assert FixPlan(tmp_path, (), (), (), ()).empty is True


def test_cli_fix_decline_confirmation_creates_nothing(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        main,
        ["fix", "--license", "MIT", "--path", str(tmp_path)],
        input="n\n",
    )
    assert result.exit_code == 0
    assert "Cancelled. No files were modified." in result.output
    assert list(tmp_path.iterdir()) == []


def test_cli_fix_force_accepts_and_replaces_with_backup(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# weak", encoding="utf-8")
    result = CliRunner().invoke(
        main,
        ["fix", "--force", "--license", "MIT", "--path", str(tmp_path)],
        input="y\n",
    )
    assert result.exit_code == 0
    assert "Fix summary" in result.output
    assert readme.read_text(encoding="utf-8").startswith("<!-- Generated")
    assert list(tmp_path.glob("README.md.repo-fixer-backup-*"))


def test_cli_fix_invalid_path_has_nonzero_exit(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    result = CliRunner().invoke(main, ["fix", "--path", str(missing), "--dry-run"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_cli_scan_json_output_contains_findings(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        main, ["scan", str(tmp_path), "--format", "json"]
    )
    assert result.exit_code == 0
    import json

    payload = json.loads(result.output)
    assert payload["score"] == 0
    assert payload["findings"]
    assert payload["findings"][0]["check_id"]


def test_config_rejects_non_mapping_yaml(tmp_path: Path) -> None:
    path = tmp_path / "repo-fixer.yml"
    path.write_text("- not\n- a mapping\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain a YAML mapping"):
        load_config(path)


def test_config_reports_invalid_yaml(tmp_path: Path) -> None:
    path = tmp_path / "repo-fixer.yml"
    path.write_text("generate: [unterminated", encoding="utf-8")
    with pytest.raises(ValueError, match="Could not read configuration"):
        load_config(path)
