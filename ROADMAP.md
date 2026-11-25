# Roadmap

This document separates work already present in the repository from ideas that have not been approved or committed. It contains no delivery dates or release promises.

## Shipped

- **v0.3.1 stabilization:** explicit confirmation for GitHub pull-request creation, consistent `generate.*` configuration handling, safer stdin detection, GitHub-token redaction, and a 90% branch-coverage gate.
- **Release artifact verification:** a verifier that builds and validates wheel and source-distribution artifacts, installs and smoke-tests them in isolated environments, and writes SHA-256 sidecars. The release-integrity guide documents normal, wheelhouse-assisted, and offline operation.
- **Permanent release-verification CI gate:** [`.github/workflows/release-verification.yml`](.github/workflows/release-verification.yml) runs normal and offline verifier modes on Ubuntu and Windows with Python 3.11 and 3.12, plus a non-blocking experimental Windows/Python 3.14 job. It also runs for version tags and manual dispatch.
- **PyPI trusted publishing:** v0.3.2 published to PyPI.
- **Project documentation:** the README, documentation home, usage and safety guides, template guidance, GitHub integration instructions, and release-integrity guide.

## Proposed, not committed

The following are candidates only. They are not commitments, scheduled work, or current product capabilities.

1. **Expand generated-template regression coverage:** add systematic regression checks across the existing ecosystem templates and the generated files they produce. This would strengthen checks for generated output without changing the supported template set.
2. **Broaden starter-template coverage:** consider additional language or project ecosystems beyond the current Go, Node, Python, Rust, and generic templates. This would expand the set of project types for which Repo Fixer provides starter templates.
3. **Strengthen GitHub integration validation:** consider additional end-to-end validation for the pull-request workflow. This would be manual and opt-in, not part of CI; current documentation states that GitHub API behavior is tested with mocked requests and CI does not use a live token.
