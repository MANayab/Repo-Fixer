"""Tests for configuration validation and loading."""

from repo_fixer.config import RepoFixerConfig, load_config


def test_missing_config_returns_sensible_defaults(tmp_path) -> None:
    config = load_config(tmp_path / "absent.yml")
    assert config == RepoFixerConfig()
    assert config.license == "MIT"
    assert config.default_branch == "main"
    assert config.generate.readme is True


def test_loads_custom_configuration(tmp_path) -> None:
    path = tmp_path / "repo-fixer.yml"
    path.write_text(
        "project_name: Example\ncreate_pull_request: false\ngenerate:\n  ci: false\n",
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.project_name == "Example"
    assert config.create_pull_request is False
    assert config.generate.ci is False
    assert config.generate.readme is True


def test_invalid_configuration_has_field_specific_error(tmp_path) -> None:
    path = tmp_path / "repo-fixer.yml"
    path.write_text("create_pull_request: maybe\n", encoding="utf-8")
    try:
        load_config(path)
    except ValueError as exc:
        assert "create_pull_request" in str(exc)
        assert "Invalid configuration" in str(exc)
    else:
        raise AssertionError("Invalid configuration should fail validation")


def test_unknown_keys_are_rejected(tmp_path) -> None:
    path = tmp_path / "repo-fixer.yml"
    path.write_text("api_token: do-not-store\n", encoding="utf-8")
    try:
        load_config(path)
    except ValueError as exc:
        assert "api_token" in str(exc)
    else:
        raise AssertionError("Unknown configuration keys should be rejected")
