# Roadmap

This document separates work already present in the repository from ideas that have not been approved or committed. It contains no delivery dates or release promises.

## Shipped

- **v0.3.1 stabilization:** explicit confirmation for GitHub pull-request creation, consistent `generate.*` configuration handling, safer stdin detection, GitHub-token redaction, and a 90% branch-coverage gate.
- **Release artifact verification:** a verifier that builds and validates wheel and source-distribution artifacts, installs and smoke-tests them in isolated environments, and writes SHA-256 sidecars. The release-integrity guide documents normal, wheelhouse-assisted, and offline operation.
- **Project documentation:** the README, documentation home, usage and safety guides, template guidance, GitHub integration instructions, and release-integrity guide.

## In review

- **Permanent release-verification CI gate:** [PR #13](https://github.com/MANayab/Repo-Fixer/pull/13) proposes normal and offline verifier runs across Ubuntu and Windows. It is a draft pull request; it is not merged or part of a release.

## Proposed, not committed

The following are candidates only. They are not commitments, scheduled work, or current product capabilities.

- **Broaden starter-template coverage:** consider additional language or project ecosystems beyond the current Go, Node, Python, Rust, and generic templates.
- **Expand generated-template regression coverage:** add systematic checks across the existing ecosystem templates and the generated files they produce.
- **Strengthen optional GitHub integration validation:** consider additional end-to-end validation for the pull-request workflow. Current documentation states that GitHub API behavior is tested with mocked requests and CI does not use a live token.
- **Evaluate a PyPI publishing workflow:** decide whether publishing automation is wanted and, if so, design it around trusted publishing rather than a long-lived upload token. No publishing workflow is currently committed.

## Prioritization

These proposals need maintainer selection before implementation. Which proposed item should be considered first?
