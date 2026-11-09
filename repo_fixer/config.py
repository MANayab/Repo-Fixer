"""Configuration models and safe YAML loading."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class GenerateConfig(BaseModel):
    """Select which repository essentials may be generated."""

    model_config = ConfigDict(extra="forbid")

    readme: bool = True
    license: bool = True
    contributing: bool = True
    code_of_conduct: bool = True
    issue_templates: bool = True
    pull_request_template: bool = True
    ci: bool = True
    changelog: bool = True
    gitignore: bool = True


class RepoFixerConfig(BaseModel):
    """Validated, non-secret Repo Fixer settings."""

    model_config = ConfigDict(extra="forbid")

    license: str = "MIT"
    project_name: str = "My Project"
    project_description: str = "A short description of the project."
    default_branch: str = "main"
    create_pull_request: bool = True
    generate: GenerateConfig = Field(default_factory=GenerateConfig)


def load_config(path: Path | str = "repo-fixer.yml") -> RepoFixerConfig:
    """Load YAML configuration, falling back to defaults if the file is absent."""
    config_path = Path(path)
    if not config_path.exists():
        return RepoFixerConfig()
    try:
        raw: Any = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"Could not read configuration {config_path}: {exc}") from exc
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError(f"Configuration {config_path} must contain a YAML mapping.")
    try:
        return RepoFixerConfig.model_validate(raw)
    except ValidationError as exc:
        details = "; ".join(str(error) for error in exc.errors())
        raise ValueError(f"Invalid configuration {config_path}: {details}") from exc
