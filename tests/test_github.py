"""Mocked tests for safe GitHub branch, commit, and PR operations."""

from __future__ import annotations

from io import BytesIO
from typing import Any
from urllib.error import HTTPError

import pytest

import repo_fixer.github as github_module
from repo_fixer.github import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubClient,
    GitHubPermissionError,
    GitHubRateLimitError,
    _validate_path,
    build_pull_request_body,
)

# ruff: noqa: E501
# fmt: off


def client() -> GitHubClient:
    return GitHubClient("test-token")


def test_missing_token_is_rejected() -> None:
    with pytest.raises(GitHubAuthenticationError, match="GITHUB_TOKEN"):
        GitHubClient("")


@pytest.mark.parametrize("path", ["", "/root", "../escape", "a/../b", "a//b", "a\\b"])
def test_unsafe_paths_are_rejected(path: str) -> None:
    with pytest.raises(ValueError):
        _validate_path(path)


def test_pr_body_lists_files_and_safety_contract() -> None:
    body = build_pull_request_body(
        [{"path": "CONTRIBUTING.md", "reason": "Missing contributor guide"}],
        "main",
        "Audit found 2 missing files.",
    )
    assert "`CONTRIBUTING.md`" in body
    assert "Audit found 2 missing files." in body
    assert "no existing file was replaced or deleted" in body
    assert "not approved for automatic merging" in body


def test_successful_flow_creates_branch_commit_and_pr(monkeypatch: pytest.MonkeyPatch) -> None:
    api_calls: list[tuple[str, str, dict[str, Any] | None]] = []
    responses = {
        ("GET", "/repos/acme/project"): ({"default_branch": "main", "permissions": {"push": True}}, {}),
        ("GET", "/repos/acme/project/git/ref/heads/main"): ({"object": {"sha": "base-sha"}}, {}),
        ("GET", "/repos/acme/project/git/commits/base-sha"): ({"tree": {"sha": "base-tree"}}, {}),
        ("GET", "/repos/acme/project/git/trees/base-tree?recursive=1"): ({"truncated": False, "tree": [{"path": "README.md"}]}, {}),
        ("POST", "/repos/acme/project/git/refs"): ({}, {}),
        ("POST", "/repos/acme/project/git/blobs"): ({"sha": "blob-sha"}, {}),
        ("POST", "/repos/acme/project/git/trees"): ({"sha": "tree-sha"}, {}),
        ("POST", "/repos/acme/project/git/commits"): ({"sha": "new-commit"}, {}),
        ("PATCH",): ({"ok": True}, {}),
        ("POST", "/repos/acme/project/pulls"): ({"number": 7, "html_url": "https://github.com/acme/project/pull/7"}, {}),
    }
    instance = client()

    def fake_request(method: str, endpoint: str, payload: dict[str, Any] | None = None):
        api_calls.append((method, endpoint, payload))
        if method == "PATCH":
            assert endpoint.endswith("/git/refs/heads/" + branch_name[0])
            assert payload == {"sha": "new-commit", "force": False}
            return {"ok": True}, {}
        if (method, endpoint) not in responses:
            raise AssertionError((method, endpoint))
        if method == "POST" and endpoint.endswith("/git/refs"):
            branch_name.append(payload["ref"].removeprefix("refs/heads/"))
        return responses[(method, endpoint)]

    branch_name: list[str] = []
    monkeypatch.setattr(instance, "_request", fake_request)
    result = instance.create_improvement_pr(
        "acme/project",
        [{"path": "CONTRIBUTING.md", "content": "# Contributing", "reason": "missing"}],
    )
    assert result.number == 7
    assert result.base == "main"
    assert result.commit_sha == "new-commit"
    assert any(call[0] == "PATCH" for call in api_calls)
    assert api_calls[-1][0:2] == ("POST", "/repos/acme/project/pulls")
    pr_payload = api_calls[-1][2]
    assert pr_payload is not None
    assert pr_payload["base"] == "main"
    assert pr_payload["head"] == result.branch
    assert pr_payload["maintainer_can_modify"] is False


def test_no_push_permission_stops_before_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    instance = client()
    calls: list[str] = []

    def fake_request(method: str, endpoint: str, payload: dict[str, Any] | None = None):
        calls.append(method)
        return {"permissions": {"push": False}}, {}

    monkeypatch.setattr(instance, "_request", fake_request)
    with pytest.raises(GitHubPermissionError, match="Contents write"):
        instance.create_improvement_pr("acme/project", [{"path": "a.txt", "content": "x"}])
    assert calls == ["GET"]


def test_existing_remote_path_is_never_overwritten(monkeypatch: pytest.MonkeyPatch) -> None:
    instance = client()
    calls: list[str] = []

    def fake_request(method: str, endpoint: str, payload: dict[str, Any] | None = None):
        calls.append(method)
        if endpoint == "/repos/acme/project":
            return {"default_branch": "main", "permissions": {"push": True}}, {}
        if endpoint.endswith("/git/ref/heads/main"):
            return {"object": {"sha": "base"}}, {}
        if endpoint.endswith("/git/commits/base"):
            return {"tree": {"sha": "tree"}}, {}
        if endpoint.endswith("/git/trees/tree?recursive=1"):
            return {"truncated": False, "tree": [{"path": "README.md"}]}, {}
        raise AssertionError("No write request should be made")

    monkeypatch.setattr(instance, "_request", fake_request)
    with pytest.raises(GitHubAPIError, match="Refusing to overwrite"):
        instance.create_improvement_pr(
            "acme/project", [{"path": "README.md", "content": "replacement"}]
        )
    assert calls == ["GET", "GET", "GET", "GET"]


def test_truncated_tree_aborts_before_branch_creation(monkeypatch: pytest.MonkeyPatch) -> None:
    instance = client()
    calls: list[str] = []

    def fake_request(method: str, endpoint: str, payload: dict[str, Any] | None = None):
        calls.append(method)
        if endpoint == "/repos/acme/project":
            return {"default_branch": "main", "permissions": {"push": True}}, {}
        if endpoint.endswith("/git/ref/heads/main"):
            return {"object": {"sha": "base"}}, {}
        if endpoint.endswith("/git/commits/base"):
            return {"tree": {"sha": "tree"}}, {}
        return {"truncated": True, "tree": []}, {}

    monkeypatch.setattr(instance, "_request", fake_request)
    with pytest.raises(GitHubAPIError, match="too large"):
        instance.create_improvement_pr("acme/project", [{"path": "a.txt", "content": "x"}])
    assert calls == ["GET", "GET", "GET", "GET"]


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (GitHubAuthenticationError("bad token"), "bad token"),
        (GitHubPermissionError("denied"), "denied"),
        (GitHubRateLimitError("slow down"), "slow down"),
        (GitHubAPIError("api failure"), "api failure"),
    ],
)
def test_typed_github_errors_are_actionable(error: Exception, expected: str) -> None:
    assert expected in str(error)


def test_duplicate_paths_are_rejected_before_api_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    instance = client()
    monkeypatch.setattr(
        instance,
        "_request",
        lambda *args, **kwargs: pytest.fail("API must not be called"),
    )
    with pytest.raises(ValueError, match="Duplicate"):
        instance.create_improvement_pr(
            "acme/project",
            [
                {"path": "new.txt", "content": "one"},
                {"path": "new.txt", "content": "two"},
            ],
        )


def test_invalid_repository_is_rejected_before_api_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    instance = client()
    monkeypatch.setattr(
        instance,
        "_request",
        lambda *args, **kwargs: pytest.fail("API must not be called"),
    )
    with pytest.raises(ValueError, match="owner/name"):
        instance.create_improvement_pr("not-a-repo", [{"path": "new.txt", "content": "x"}])


@pytest.mark.parametrize(
    ("status", "headers", "body", "error_type", "message"),
    [
        (401, {}, b'{"message":"Bad credentials"}', GitHubAuthenticationError, "GITHUB_TOKEN"),
        (403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1794229000"}, b'{"message":"API rate limit exceeded"}', GitHubRateLimitError, "Retry after"),
        (403, {"X-RateLimit-Remaining": "5"}, b'{"message":"Resource not accessible by integration"}', GitHubPermissionError, "Pull requests permissions"),
        (429, {"Retry-After": "30"}, b'{"message":"secondary rate limit"}', GitHubRateLimitError, "30 seconds"),
        (404, {}, b'{"message":"Not Found"}', GitHubAPIError, "not found"),
    ],
)
def test_http_errors_are_classified(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    headers: dict[str, str],
    body: bytes,
    error_type: type[Exception],
    message: str,
) -> None:
    def denied(*args: Any, **kwargs: Any) -> Any:
        raise HTTPError(
            "https://api.github.com/test",
            status,
            "error",
            headers,
            BytesIO(body),
        )

    monkeypatch.setattr(github_module, "urlopen", denied)
    with pytest.raises(error_type, match=message):
        client()._request("GET", "/test")
