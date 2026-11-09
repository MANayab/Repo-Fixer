# Repo Fixer

**Make any GitHub repository contributor-ready in minutes.**

Repo Fixer is a local repository audit and safe file-generation tool. It identifies missing project essentials, calculates an explainable readiness score, and can create reviewable starter files on the developer's machine.

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
```

## Safe file generation

`fix --dry-run` previews planned creations without changing the filesystem. A normal `fix` asks before creating files. `--yes` skips that prompt only for new files. Existing files are skipped; a weak README is written to `repo-fixer-proposed-README.md` for manual review. Replacing the README requires `--force` and a separate explicit confirmation; a timestamped backup is created first.

A missing LICENSE is never selected automatically. Choose one explicitly with `--license` or the interactive prompt. Repo Fixer never deletes files, follows unsafe symlinks, writes outside the selected repository root, calls the GitHub API, or makes network requests.

## What it generates

README, CONTRIBUTING, Code of Conduct, GitHub issue and pull-request templates, language-aware CI workflow, CHANGELOG, and language-aware .gitignore. Unknown languages receive a clearly labelled workflow placeholder.

## Development

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pip install -e .
pytest --cov=repo_fixer
ruff check .
ruff format --check .
mypy repo_fixer
```

## License

The Repo Fixer application is MIT licensed. See [LICENSE](LICENSE).
