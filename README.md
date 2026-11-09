# Repo Fixer

**Make any GitHub repository contributor-ready in minutes.**

Repo Fixer is a local repository audit tool that identifies missing project essentials and calculates an explainable readiness score. It reads repository files and reports evidence-backed recommendations. It does not modify the audited repository, access the network, or connect to GitHub.

[![CI](https://github.com/MANayab/Repo-Fixer/actions/workflows/ci.yml/badge.svg)](https://github.com/MANayab/Repo-Fixer/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **v0.2.0:** read-only repository essentials audit and explainable readiness scoring.

## What it checks

Repo Fixer evaluates nine repository essentials:

1. README presence and basic quality (project heading, substantive overview, installation, usage)
2. LICENSE file
3. CONTRIBUTING guide
4. Code of Conduct
5. GitHub issue templates
6. Pull request template
7. GitHub Actions workflow files
8. CHANGELOG
9. .gitignore

Each finding includes a stable check ID, severity, affected path, evidence, and a practical recommendation.

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

Audit the current directory:

```bash
repo-fixer scan
repo-fixer score
```

Audit a selected repository:

```bash
repo-fixer scan path/to/repository
repo-fixer score path/to/repository
```

Get machine-readable output:

```bash
repo-fixer scan path/to/repository --format json
repo-fixer score path/to/repository --format json
```

Use `repo-fixer init` to create a starter `repo-fixer.yml`. It refuses to overwrite an existing file.

## Readiness score

The score starts at 100. Each of the nine checks has a fixed weight; a failed check deducts that check's full weight. The weights total 100:

| Check | Weight |
|---|---:|
| README | 20 |
| LICENSE | 15 |
| CONTRIBUTING | 10 |
| Code of Conduct | 8 |
| Issue templates | 10 |
| Pull request template | 7 |
| GitHub Actions CI | 15 |
| CHANGELOG | 8 |
| .gitignore | 7 |

Grades: A (90–100), B (80–89), C (70–79), D (60–69), F (below 60). README quality gaps fail the README check and deduct its full weight. The score is a transparent checklist indicator, not a measure of code correctness or security.

## Safety and privacy

- The audit is local and read-only.
- No repository files are created, edited, renamed, or deleted by scan or score.
- No GitHub API calls or network requests are made by scan or score.
- Symlinked check targets are not followed.
- Findings report paths and evidence, not file contents.
- No third-party AI service or external database is used.

The `fix` command remains a v0.3.0 placeholder. File generation, branch creation, GitHub integration, and pull-request automation are not part of v0.2.0.

## Development

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pip install -e .
pytest
ruff check .
ruff format --check .
mypy repo_fixer
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Roadmap

- **v0.1.0 — Foundation:** package, CLI, config, tests, CI, and documentation.
- **v0.2.0 — Audit:** read-only repository checks and explainable readiness score.
- **v0.3.0 — Safe improvements:** generate selected files for human review.
- **Later — GitHub integration:** optional feature branch and pull-request workflow, never automatic merge.

## License

MIT. See [LICENSE](LICENSE).
