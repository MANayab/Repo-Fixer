---
layout: default
title: "Repo Fixer — Make Any GitHub Repository Contributor-Ready"
description: "Run a local repository audit and generate safe starter files for review."
permalink: /
---

# Repo Fixer

**Make any GitHub repository contributor-ready in minutes.**

The current milestone adds local, confirmation-gated starter-file generation to the read-only audit and readiness score. These changes are under review and are not part of a published release. The tool does not connect to GitHub or make network requests.

## Quick start

```bash
python -m pip install .
repo-fixer scan
repo-fixer fix --dry-run
```

## Safety

Dry-run makes no changes. Existing files are skipped. Weak README content is proposed separately. Replacing a README requires explicit confirmation and a timestamped backup. License generation requires an explicit choice. No files are deleted and no GitHub integration is implemented.

See [usage](usage.md), [templates](templates.md), and [safety guarantees](safety.md).
