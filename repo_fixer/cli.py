"""Command-line interface for Repo Fixer."""
import json
from pathlib import Path
from typing import Any

import click

from repo_fixer.config import load_config
from repo_fixer.constants import CONFIG_FILENAME, DEFAULT_CONFIG, __version__
from repo_fixer.scanner import AuditReport, audit_repository


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--config", type=click.Path(path_type=Path, dir_okay=False), default=Path(CONFIG_FILENAME), show_default=True, help="Path to the Repo Fixer YAML configuration file.")
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
@click.argument("repository", type=click.Path(path_type=Path, file_okay=False), default=".")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text", show_default=True)
@click.pass_context
def scan(ctx: click.Context, repository: Path, output_format: str) -> None:
    """Audit repository essentials without changing repository files."""
    _validate_config(ctx.obj)
    _render_report(_run_audit(repository), output_format)


@main.command()
@click.argument("repository", type=click.Path(path_type=Path, file_okay=False), default=".")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text", show_default=True)
@click.pass_context
def score(ctx: click.Context, repository: Path, output_format: str) -> None:
    """Calculate an explainable repository readiness score."""
    _validate_config(ctx.obj)
    report = _run_audit(repository)
    if output_format == "json":
        click.echo(json.dumps({"repository": report.repository, "score": report.score, "grade": report.grade, "checks_passed": report.checks_passed, "checks_total": report.checks_total}, indent=2))
    else:
        click.echo(f"Readiness score: {report.score}/100 (Grade {report.grade})")
        click.echo(f"Checks passed: {report.checks_passed}/{report.checks_total}")
        click.echo("Scoring: each of the 9 checks has a fixed weight; a failed check loses its full weight.")


@main.command()
@click.pass_context
def fix(ctx: click.Context) -> None:
    """Prepare safe repository improvements (planned for v0.3.0)."""
    _validate_config(ctx.obj)
    click.echo("Fix generation is coming in v0.3.0.")


@main.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Create a starter repo-fixer.yml without overwriting existing files."""
    path: Path = ctx.obj["config"]
    if path.exists():
        raise click.ClickException(f"Config already exists at {path}; refusing to overwrite.")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(DEFAULT_CONFIG, encoding="utf-8")
        load_config(path)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Created {path}")


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
        click.echo(f"- [{item.severity.upper()}] {item.check_id} — {item.affected_file}")
        click.echo(f"  Evidence: {item.evidence}")
        click.echo(f"  Recommendation: {item.recommendation}")


def _validate_config(context: dict[str, Any]) -> None:
    """Validate the selected config before a command proceeds."""
    try:
        load_config(context["config"])
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
