---
layout: default
title: "Repo Fixer — Make Any GitHub Repository Contributor-Ready"
description: "Run a local, read-only audit of repository essentials and get an explainable readiness score."
permalink: /
---

<head>
<link rel="canonical" href="https://manayab.github.io/Repo-Fixer/">
<meta name="description" content="Repo Fixer checks README quality, license, contribution guidance, templates, CI, changelog, and ignore rules locally without changing repository files.">
<meta property="og:type" content="website">
<meta property="og:title" content="Repo Fixer — Make Any GitHub Repository Contributor-Ready">
<meta property="og:description" content="Find repository gaps with a local read-only audit and transparent readiness score.">
<meta property="og:url" content="https://manayab.github.io/Repo-Fixer/">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"SoftwareApplication","name":"Repo Fixer","applicationCategory":"DeveloperApplication","operatingSystem":"Cross-platform","description":"A local read-only repository essentials audit and explainable readiness score.","softwareVersion":"0.2.0","license":"https://github.com/MANayab/Repo-Fixer/blob/main/LICENSE","url":"https://manayab.github.io/Repo-Fixer/","codeRepository":"https://github.com/MANayab/Repo-Fixer"}
</script>
</head>

# Repo Fixer

**Make any GitHub repository contributor-ready in minutes.**

Repo Fixer v0.2.0 audits a local repository and reports evidence-backed gaps across nine contributor-readiness checks. Scan and score do not modify files, access the network, or call the GitHub API.

## What it checks

- README presence and basic quality
- LICENSE
- CONTRIBUTING guide
- Code of Conduct
- GitHub issue templates
- Pull request template
- GitHub Actions workflow files
- CHANGELOG
- .gitignore

## Quick start

Install Python 3.11+ and run:

```bash
python -m pip install .
repo-fixer scan path/to/repository
repo-fixer score path/to/repository
```

Use `--format json` for structured output. Findings include a stable check ID, severity, affected path, evidence, and recommendation.

## Explainable score

The readiness score starts at 100. Nine checks have fixed weights totaling 100 points. A failed check loses its assigned weight. The score is a transparent checklist indicator, not a measure of code quality or security.

## Safety

The audit is local and read-only. It does not create, edit, rename, or delete files in the target repository. Scan and score make no network requests and do not access GitHub. Symlinked check targets are not followed.

## Roadmap

- **v0.1.0 — Foundation:** package, CLI, config, tests, CI, and documentation.
- **v0.2.0 — Audit:** read-only repository checks and explainable score.
- **v0.3.0 — Improvements:** safe file generation for human review.
- **Later — GitHub integration:** optional branch and pull-request workflow with no automatic merge.

See the [source repository](https://github.com/MANayab/Repo-Fixer), [contribution guide](https://github.com/MANayab/Repo-Fixer/blob/main/CONTRIBUTING.md), and [MIT license](https://github.com/MANayab/Repo-Fixer/blob/main/LICENSE).
