"""Command-line interface for Repo Fixer."""

from pathlib import Path
from typing import Any

import click

from repo_fixer.config import load_config
from repo_fixer.constants import CONFIG_FILENAME, DEFAULT_CONFIG, __version__


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
@click.pass_context
def scan(ctx: click.Context) -> None:
    """Audit repository essentials (planned for v0.2.0)."""
    _validate_config(ctx.obj)
    click.echo("Repository scanning is coming in v0.2.0.")


@main.command()
@click.pass_context
def fix(ctx: click.Context) -> None:
    """Prepare safe repository improvements (planned for v0.3.0)."""
    _validate_config(ctx.obj)
    click.echo("Fix generation is coming in v0.3.0.")


@main.command()
@click.pass_context
def score(ctx: click.Context) -> None:
    """Calculate repository readiness (planned for v0.2.0)."""
    _validate_config(ctx.obj)
    click.echo("Readiness scoring is coming in v0.2.0.")


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


def _validate_config(context: dict[str, Any]) -> None:
    """Validate the selected config before a command proceeds."""
    try:
        load_config(context["config"])
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
