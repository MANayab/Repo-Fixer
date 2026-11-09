# Repo Fixer

**Make any GitHub repository contributor-ready in minutes.**

Repo Fixer is an open-source GitHub repository audit tool designed to identify
missing project essentials and propose safe, reviewable improvements in one
pull request. It aims to improve open-source readiness without silently
changing a maintainer's work.

[![CI](https://github.com/MANayab/Repo-Fixer/actions/workflows/ci.yml/badge.svg)](https://github.com/MANayab/Repo-Fixer/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-Ruff-D7FF64)](https://github.com/astral-sh/ruff)
[![Tests: pytest](https://img.shields.io/badge/tests-pytest-blue)](https://pytest.org/)

> **Milestone 1 / v0.1.0:** package, CLI, configuration, quality tooling, and
> documentation foundation. Repository auditing and automated improvements
> are planned later; current commands do not scan or modify repositories.

## Why Repo Fixer?

Repositories can be hard to adopt when they lack a useful README, license,
contribution guidance, issue templates, or reliable CI. Repo Fixer is planned
as a GitHub repository health check and developer productivity tool that
prepares consistent improvements for human review. Future GitHub Actions
automation will help maintainers identify gaps without bypassing pull-request
review.

## What Repo Fixer will check

Planned checks include README quality, LICENSE presence, CONTRIBUTING and
Code of Conduct guidance, GitHub contribution templates, a GitHub Actions CI
workflow, changelog, and common ignore rules. These checks are not implemented
in v0.1.0. Later releases may include a README generator, LICENSE generator,
and GitHub CI workflow generator for missing or incomplete project essentials.

## Quick Start

Requires Python 3.11+.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
repo-fixer --help
repo-fixer version
repo-fixer init
```

`repo-fixer init` creates `repo-fixer.yml` and refuses to overwrite an existing
file. Use `--config path/to/repo-fixer.yml` to choose another config path.

## Planned GitHub Action

This is a roadmap illustration, not a working action interface:

```yaml
- uses: MANayab/Repo-Fixer@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    create-pull-request: true
```

## CLI preview

```text
repo-fixer --help
repo-fixer version   # prints Repo Fixer 0.1.0
repo-fixer init      # creates repo-fixer.yml
repo-fixer scan      # coming in v0.2.0
repo-fixer score     # coming in v0.2.0
repo-fixer fix       # coming in v0.3.0
```

Scan and score are successful roadmap messages. Fix is also a roadmap message,
not a file writer.

## Safety model

- Changes are proposed on a separate branch in a reviewable pull request.
- No force-push, automatic merge, or direct push to `main`.
- No file deletion or silent overwrite.
- Generated changes require human review.
- No source code is sent to third-party AI services.
- No external database is required by the product design.
- Future GitHub tokens will use minimum required permissions; never store
  secrets in `repo-fixer.yml`.

The v0.1.0 CLI makes no network requests and does not access GitHub.

## Roadmap

- **v0.1.0 — Foundation:** package, CLI, validated config, tests, CI, docs.
- **v0.2.0 — Audit:** repository essentials scan and explainable readiness score.
- **v0.3.0 — Safe improvements:** generate selected files for review.
- **Later — GitHub integration:** feature branch and one pull request, never
  automatic merge. Milestone 2 remains gated until this foundation is approved.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), follow the [Code of Conduct](CODE_OF_CONDUCT.md),
and open an issue for substantial proposals.

## FAQ

### Is Repo Fixer available today?

The v0.1.0 CLI foundation is available. Scanning, scoring, generation, and
GitHub integration are planned, not implemented.

### Does Repo Fixer push directly to main?

No. It is designed to use a separate branch and reviewable pull request. It
will not force-push or merge automatically.

### Does it send source code to an AI provider?

No. Third-party AI services are not part of the design. The intended audit
reads only repository files needed for configured checks.

### Does it need a database?

No external database is required by the product design.

### Can I use it in CI?

This release tests Repo Fixer's own package. A reusable GitHub Action is planned.

## License

MIT. See [LICENSE](LICENSE).

## Help make open source healthier

Star the repository, share it with another maintainer, or contribute. Feedback
from real maintainers will shape the roadmap.
