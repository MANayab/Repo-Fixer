# Repo Fixer

**Make any GitHub repository contributor-ready in minutes.**

Repo Fixer audits repository essentials, calculates an explainable readiness score, and safely generates starter files. Optional GitHub integration can open a reviewable pull request without pushing directly to the default branch.

[![CI](https://github.com/MANayab/Repo-Fixer/actions/workflows/ci.yml/badge.svg)](https://github.com/MANayab/Repo-Fixer/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Quick Start

Requires Python 3.11+.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
repo-fixer --help
```

## Commands

```bash
repo-fixer scan
repo-fixer scan ./my-project --format json
repo-fixer score
repo-fixer fix --dry-run
repo-fixer fix --path ./my-project
repo-fixer fix --yes
repo-fixer fix --license MIT
repo-fixer fix --force
repo-fixer fix --create-pr --license MIT
```

## Safe file generation

`fix --dry-run` previews planned changes without changing files. A normal `fix` asks before creating files. `--yes` skips that prompt only for new files. Existing files are skipped; a weak README is proposed separately. Replacing a README locally requires `--force`, explicit confirmation, and a timestamped backup.

A missing LICENSE is never selected automatically. Choose one explicitly with `--license` or the interactive prompt. Repo Fixer never deletes files or writes outside the selected repository root.

## Optional GitHub integration

Set `GITHUB_TOKEN` to a fine-grained token limited to the target repository with **Contents: Read and write**, **Pull requests: Read and write**, and mandatory **Metadata: Read-only** permissions. Then run:

```powershell
$env:GITHUB_TOKEN = "github_pat_..."
repo-fixer fix --create-pr --license MIT
```

The command creates a unique feature branch, commits additions only, and opens one pull request to the repository's default branch. It checks remote paths before writing and refuses to overwrite any existing path. It never pushes to the default branch, force-pushes, deletes files, or merges automatically. Review all generated content before merging.

See [GitHub integration and token permissions](docs/github-integration.md) and [safety guarantees](docs/safety.md).

## Development

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pip install -e .
pytest --cov=repo_fixer
ruff check .
ruff format --check .
mypy repo_fixer
```

GitHub API behavior is tested with mocked requests. CI does not use a live token or make live GitHub API calls.

## License

The Repo Fixer application is MIT licensed. See [LICENSE](LICENSE).
