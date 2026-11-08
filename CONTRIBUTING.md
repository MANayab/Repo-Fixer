# Contributing to Repo Fixer

Thanks for helping improve Repo Fixer. The project is developed in small,
reviewable milestones. Discuss substantial changes in an issue first.

## Development setup

Requires Python 3.11 or newer.

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pip install -e .
pre-commit install
```

## Checks before a pull request

```bash
ruff check .
ruff format --check .
mypy repo_fixer
pytest --cov=repo_fixer
```

Keep pull requests focused, add tests, and update documentation. Never include
tokens, private repository contents, or other secrets in issues, logs, fixtures,
or commits.

## Safety expectations

Preserve review-before-apply behavior. Do not add force-push, file deletion,
silent overwrites, or automatic merging. Generated changes must be reviewable.

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
