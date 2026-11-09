"""Command-line interface for Repo Fixer."""

# File writes are delegated to the confirmation-gated local generator.
import json
from pathlib import Path
from typing import Any, Protocol, cast

import click


class _TTYStream(Protocol):
    def isatty(self) -> bool: ...


from repo_fixer.config import load_config
from repo_fixer.constants import CONFIG_FILENAME, DEFAULT_CONFIG, __version__
from repo_fixer.generator import LICENSES, apply_plan, build_plan
from repo_fixer.scanner import AuditReport, audit_repository


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
@click.pass_context
def fix(
    ctx: click.Context,
    dry_run: bool,
    repository: Path,
    yes: bool,
    force: bool,
    license_name: str | None,
) -> None:
    """Preview and safely generate missing project files locally."""
    _validate_config(ctx.obj)
    try:
        plan = build_plan(repository, license_name=license_name, force=force)
        if (
            not dry_run
            and license_name is None
            and any(
                item.startswith("LICENSE — selection required") for item in plan.skipped
            )
        ):
            if not cast(_TTYStream, click.get_text_stream("stdin")).isatty():
                click.echo(
                    "LICENSE not generated: choose one with --license.", err=True
                )
            else:
                license_name = click.prompt(
                    "Choose a license", type=click.Choice(LICENSES), show_choices=True
                )
                plan = build_plan(repository, license_name=license_name, force=force)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    _show_plan(plan, dry_run=dry_run)
    if plan.empty:
        click.echo("No files need to be generated.")
        return
    if dry_run:
        click.echo("No files were modified.")
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
            f"- [{item.severity.upper()}] {item.check_id} — {item.affected_file}"
        )
        click.echo(f"  Evidence: {item.evidence}")
        click.echo(f"  Recommendation: {item.recommendation}")


def _validate_config(context: dict[str, Any]) -> None:
    """Validate the selected config before a command proceeds."""
    try:
        load_config(context["config"])
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
