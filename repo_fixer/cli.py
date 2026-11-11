"""Command-line interface for Repo Fixer."""

# File writes are delegated to the confirmation-gated local generator.
import configparser
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import click

from repo_fixer.config import RepoFixerConfig, load_config
from repo_fixer.constants import CONFIG_FILENAME, DEFAULT_CONFIG, __version__
from repo_fixer.generator import LICENSES, apply_plan, build_plan
from repo_fixer.github import GitHubClient, GitHubError
from repo_fixer.scanner import AuditReport, audit_repository

# fmt: off


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--config",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path(CONFIG_FILENAME),
    show_default=True,
    help="Path to the Repo Fixer YAML configuration file.",
)
@click.pass_context
def main(ctx: click.Context, config: Path) -> None:
    """Make any GitHub repository contributor-ready in minutes."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = config


@main.command()
def version() -> None:
    """Show the installed Repo Fixer version."""
    click.echo(f"Repo Fixer {__version__}")


@main.command()
@click.argument(
    "repository", type=click.Path(path_type=Path, file_okay=False), default="."
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
@click.pass_context
def scan(ctx: click.Context, repository: Path, output_format: str) -> None:
    """Audit repository essentials without changing repository files."""
    _validate_config(ctx.obj)
    _render_report(_run_audit(repository), output_format)


@main.command()
@click.argument(
    "repository", type=click.Path(path_type=Path, file_okay=False), default="."
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
@click.pass_context
def score(ctx: click.Context, repository: Path, output_format: str) -> None:
    """Calculate an explainable repository readiness score."""
    _validate_config(ctx.obj)
    report = _run_audit(repository)
    if output_format == "json":
        payload = {
            "repository": report.repository,
            "score": report.score,
            "grade": report.grade,
            "checks_passed": report.checks_passed,
            "checks_total": report.checks_total,
        }
        click.echo(json.dumps(payload, indent=2))
    else:
        click.echo(f"Readiness score: {report.score}/100 (Grade {report.grade})")
        click.echo(f"Checks passed: {report.checks_passed}/{report.checks_total}")
        click.echo(
            "Scoring: each of the 9 checks has a fixed weight; "
            "a failed check loses its full weight."
        )


@main.command()
@click.option("--dry-run", is_flag=True, help="Preview the plan without writing files.")
@click.option(
    "--path",
    "repository",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("."),
    show_default=True,
    help="Repository directory to fix.",
)
@click.option(
    "--yes", is_flag=True, help="Skip confirmation for new-file creation only."
)
@click.option(
    "--force",
    is_flag=True,
    help="Allow replacing a weak README after explicit confirmation.",
)
@click.option(
    "--license",
    "license_name",
    type=click.Choice(LICENSES),
    help="Explicit license choice when LICENSE is missing.",
)
@click.option(
    "--create-pr",
    is_flag=True,
    help="Create a reviewable GitHub pull request instead of writing local files.",
)
@click.pass_context
def fix(
    ctx: click.Context,
    dry_run: bool,
    repository: Path,
    yes: bool,
    force: bool,
    license_name: str | None,
    create_pr: bool,
) -> None:
    """Preview and safely generate missing project files locally or by PR."""
    config = _validate_config(ctx.obj)
    if create_pr and force:
        raise click.ClickException(
            "--force cannot be used with --create-pr; remote PR generation "
            "never replaces files."
        )
    try:
        plan = build_plan(
            repository,
            license_name=license_name,
            force=force,
            generate=config.generate,
        )
        if (
            not dry_run
            and license_name is None
            and any(
item.startswith(
    "LICENSE â€” selection required"
)
for item in plan.skipped            )
        ):
            if not _stdin_isatty():
                click.echo(
                    "LICENSE not generated: choose one with --license.", err=True
                )
            else:
                license_name = click.prompt(
                    "Choose a license", type=click.Choice(LICENSES), show_choices=True
                )
                plan = build_plan(
                    repository,
                    license_name=license_name,
                    force=force,
                    generate=config.generate,
                )
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    _show_plan(plan, dry_run=dry_run)
    if plan.empty:
        click.echo("No files need to be generated.")
        return
    if dry_run:
        click.echo("No files were modified and no pull request was created.")
        return

    if create_pr:
        try:
            repository_name = _github_repository_name(repository)
            files = [
                {"path": item.path, "content": item.content, "reason": item.reason}
                for item in plan.created + plan.proposed
                if not item.replace
            ]
            if not files:
                click.echo("No additions are available for a pull request.")
                return
            if not _stdin_isatty():
                raise click.ClickException(
                    "Refusing GitHub pull-request creation "
        "without interactive confirmation."
                )
            if not click.confirm(
                f"Create one GitHub pull request with {len(files)} new file(s)?",
                default=False,
            ):
                click.echo("Cancelled. No GitHub changes were made.")
                return
            client = GitHubClient.from_environment()
            result = client.create_improvement_pr(
                repository_name,
                files,
                audit_summary=(
                    f"Local audit planned {len(files)} new file(s) for review."
                ),
            )
        except (GitHubError, OSError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo("\nPull request created")
        click.echo(f"URL: {result.url}")
        click.echo(f"Branch: {result.branch}")
        click.echo(f"Base: {result.base}")
        click.echo(f"Commit: {result.commit_sha}")
        click.echo("No merge was performed. Review and merge manually if approved.")
        return

    if force:
        click.echo("WARNING: --force may replace an existing weak README.")
        if not click.confirm(
            "Create a timestamped backup and replace it?", default=False
        ):
            click.echo("Cancelled. No files were modified.")
            return
    elif not yes and not click.confirm(
        "Create the listed missing files?", default=False
    ):
        click.echo("Cancelled. No files were modified.")
        return

    try:
        created, skipped = apply_plan(plan, force=force)
    except (OSError, ValueError) as exc:
        raise click.ClickException(f"File generation stopped safely: {exc}") from exc
    click.echo("\nFix summary")
    click.echo(f"Created: {len([p for p in created if 'backup' not in p])}")
    for path in created:
        click.echo(f"  + {path}")
    if skipped:
        click.echo(f"Skipped: {len(skipped)}")
        for path in skipped:
            click.echo(f"  - {path}")
    if not created:
        click.echo("No files were created.")


@main.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Create a starter repo-fixer.yml without overwriting existing files."""
    path: Path = ctx.obj["config"]
    if path.exists():
        raise click.ClickException(
            f"Config already exists at {path}; refusing to overwrite."
        )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(DEFAULT_CONFIG, encoding="utf-8")
        load_config(path)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Created {path}")


def _github_repository_name(repository: Path) -> str:
    """Resolve owner/name from GITHUB_REPOSITORY or the local origin URL."""
    configured = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if configured:
        if configured.count("/") == 1:
            return configured
        raise ValueError("GITHUB_REPOSITORY must use owner/name format.")
    config_path = repository.resolve() / ".git" / "config"
    if not config_path.is_file():
        raise ValueError(
            "Could not find .git/config. Set GITHUB_REPOSITORY=owner/name explicitly."
        )
    parser = configparser.ConfigParser()
    try:
        parser.read(config_path, encoding="utf-8")
        remote = parser.get('remote "origin"', "url")
    except (configparser.Error, OSError) as exc:
        raise ValueError("Could not read the origin remote from .git/config.") from exc
    if remote.startswith("git@github.com:"):
        name = remote.removeprefix("git@github.com:")
    else:
        parsed = urlparse(remote)
        if parsed.hostname not in {"github.com", "www.github.com"}:
            raise ValueError("The origin remote must point to github.com.")
        name = parsed.path.lstrip("/")
    if name.endswith(".git"):
        name = name[:-4]
    if name.count("/") != 1:
        raise ValueError("Could not resolve the GitHub origin as owner/name.")
    return name


def _show_plan(plan: Any, *, dry_run: bool) -> None:
    click.echo("Repo Fixer Fix Plan")
    if plan.created:
        click.echo("\nWould create:")
        for item in plan.created:
            click.echo(f"- {item.path} ({item.reason})")
    if plan.proposed:
        click.echo("\nWould propose:")
        for item in plan.proposed:
            click.echo(f"- {item.path} ({item.reason})")
    if plan.skipped:
        click.echo("\nWould skip:")
        for item in plan.skipped:
            click.echo(f"- {item}")
    if plan.unchanged:
        click.echo("\nUnchanged:")
        for item in plan.unchanged:
            click.echo(f"- {item}")
    if dry_run:
        click.echo("\nDry run: no files were modified.")


def _run_audit(repository: Path) -> AuditReport:
    try:
        return audit_repository(repository)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _render_report(report: AuditReport, output_format: str) -> None:
    if output_format == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
        return
    click.echo(f"Repository: {report.repository}")
    click.echo(f"Readiness: {report.score}/100 (Grade {report.grade})")
    click.echo(f"Checks passed: {report.checks_passed}/{report.checks_total}")
    if not report.findings:
        click.echo("No gaps found in the repository essentials checks.")
        return
    click.echo("\nFindings:")
    for item in report.findings:
        click.echo(
            f"- [{item.severity.upper()}] {item.check_id} Ã¢â‚¬â€ {item.affected_file}"
        )
        click.echo(f"  Evidence: {item.evidence}")
        click.echo(f"  Recommendation: {item.recommendation}")


def _stdin_isatty() -> bool:
    """Return whether standard input is interactive without Click's deprecated API."""
    stdin = getattr(sys, "stdin", None)
    isatty = getattr(stdin, "isatty", None)
    if not callable(isatty):
        return False
    try:
        return bool(isatty())
    except OSError:
        return False


def _validate_config(context: dict[str, Any]) -> RepoFixerConfig:
    """Validate and return the selected config before a command proceeds."""
    try:
        return load_config(context["config"])
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
