"""CLI tests for the opt-in GitHub pull-request workflow."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from repo_fixer.cli import _github_repository_name, main
from repo_fixer.github import GitHubAPIError, GitHubClient, PullRequestResult

# fmt: off


class FakeGitHubClient:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, list[dict[str, str]]]] = []

    def create_improvement_pr(
        self,
        repository: str,
        files: list[dict[str, str]],
        *,
        audit_summary: str = "",
    ) -> PullRequestResult:
        self.calls.append((repository, files))
        if self.error:
            raise self.error
        return PullRequestResult(
            number=12,
            url="https://github.com/acme/project/pull/12",
            branch="repo-fixer/improvements-deadbeef",
            base="main",
            commit_sha="commit-sha",
        )


def invoke_create_pr(
    path: Path,
    *,
    extra: list[str] | None = None,
    input_text: str | None = None,
):
    return CliRunner().invoke(
        main,
        [
            "fix",
            "--path",
            str(path),
            "--create-pr",
            "--license",
            "MIT",
            *(extra or []),
        ],
        input=input_text,
    )


def test_create_pr_uses_mock_client_and_does_not_write_local_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeGitHubClient()
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/project")
    monkeypatch.setattr(
        GitHubClient,
        "from_environment",
        classmethod(lambda cls: fake),
    )
    result = invoke_create_pr(tmp_path, extra=["--yes"])
    assert result.exit_code == 0, result.output
    assert "https://github.com/acme/project/pull/12" in result.output
    assert "No merge was performed" in result.output
    assert fake.calls
    assert fake.calls[0][0] == "acme/project"
    assert fake.calls[0][1]
    assert list(tmp_path.iterdir()) == []


def test_create_pr_confirmation_can_be_declined(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/project")
    monkeypatch.setattr(
        GitHubClient,
        "from_environment",
        classmethod(lambda cls: pytest.fail("Client must not be created")),
    )
    result = invoke_create_pr(tmp_path, input_text="n\n")
    assert result.exit_code == 0
    assert "Cancelled. No GitHub changes were made." in result.output
    assert list(tmp_path.iterdir()) == []


def test_create_pr_dry_run_never_contacts_github(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        GitHubClient,
        "from_environment",
        classmethod(lambda cls: pytest.fail("Dry-run must not contact GitHub")),
    )
    result = invoke_create_pr(tmp_path, extra=["--dry-run"])
    assert result.exit_code == 0
    assert "No pull request was created" in result.output


def test_create_pr_rejects_force_flag(tmp_path: Path) -> None:
    result = invoke_create_pr(tmp_path, extra=["--force"])
    assert result.exit_code != 0
    assert "--force cannot be used with --create-pr" in result.output


def test_create_pr_reports_missing_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/project")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    result = invoke_create_pr(tmp_path, extra=["--yes"])
    assert result.exit_code != 0
    assert "GITHUB_TOKEN" in result.output


def test_create_pr_reports_api_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeGitHubClient(GitHubAPIError("mock API failure"))
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/project")
    monkeypatch.setattr(
        GitHubClient,
        "from_environment",
        classmethod(lambda cls: fake),
    )
    result = invoke_create_pr(tmp_path, extra=["--yes"])
    assert result.exit_code != 0
    assert "mock API failure" in result.output


@pytest.mark.parametrize(
    "remote",
    [
        "git@github.com:acme/project.git",
        "https://github.com/acme/project.git",
        "https://www.github.com/acme/project",
    ],
)
def test_repository_name_is_resolved_from_github_origin(
    tmp_path: Path,
    remote: str,
) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text(
        f'[remote "origin"]\n\turl = {remote}\n',
        encoding="utf-8",
    )
    assert _github_repository_name(tmp_path) == "acme/project"


def test_repository_name_prefers_github_repository_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repository")
    assert _github_repository_name(tmp_path) == "owner/repository"


def test_repository_name_rejects_non_github_origin(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text(
        '[remote "origin"]\n\turl = https://example.com/acme/project.git\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="github.com"):
        _github_repository_name(tmp_path)


def test_repository_name_requires_remote_or_environment(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="GITHUB_REPOSITORY"):
        _github_repository_name(tmp_path)


def test_repository_name_rejects_malformed_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "malformed")
    with pytest.raises(ValueError, match="owner/name"):
        _github_repository_name(tmp_path)
