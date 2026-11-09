---
layout: default
title: "Repo Fixer — Make Any GitHub Repository Contributor-Ready"
description: "Run a local repository audit and generate safe starter files for review."
permalink: /
---

# Repo Fixer

**Make any GitHub repository contributor-ready in minutes.**

Repo Fixer audits repository essentials, calculates an explainable readiness score, and generates missing starter files locally. Optional GitHub integration can open a reviewable pull request on a separate branch.

## Quick start

```bash
python -m pip install .
repo-fixer scan
repo-fixer fix --dry-run
```

## Optional GitHub pull requests

Set a fine-grained `GITHUB_TOKEN` with Contents read/write and Pull requests read/write permissions for the target repository, then run `repo-fixer fix --create-pr`. Repo Fixer proposes additions on a separate branch and opens a pull request for human review. It never pushes to the default branch or merges automatically.

See [usage](usage.md), [templates](templates.md), [safety guarantees](safety.md), and [GitHub integration](github-integration.md).
