# Changelog

All notable changes to Repo Fixer are documented here.

## [0.2.0] — Read-only Repository Audit

- Implemented local, read-only repository essentials scanning.
- Added README presence and quality checks, license detection, contribution and community files, GitHub issue and pull request templates, Actions workflow detection, changelog, and .gitignore checks.
- Added structured findings with stable check IDs, severity, affected path, evidence, and recommendations.
- Added an explainable 100-point readiness score with fixed weights across nine checks.
- Added human-readable and JSON output for scan and score commands.
- Added safe path handling that rejects symlinked check targets and never writes to the audited repository.
- Kept fix generation and GitHub integration out of this milestone.

## [0.1.0] — Project Foundation

- Established the Python package, CLI, validated configuration, tests, CI, and documentation.
