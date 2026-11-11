# Changelog

All notable changes to Repo Fixer are documented here.

## [Unreleased]

## [0.3.1] — Stabilization and Release Integrity

### Changed
- Enforced explicit interactive confirmation before GitHub pull-request creation, including when `--yes` is used.
- Applied `generate.*` configuration consistently through the CLI planning path.
- Replaced deprecated Click stdin access with safe standard-library stdin detection.
- Redacted configured GitHub tokens from HTTP and network error details.
- Raised the enforced branch-coverage gate to 90%.

### Fixed
- Preserved local-only fixing without requiring a GitHub token.

## [0.3.0] — Safe Fix Generation and Project Templates

### Added
- Local, confirmation-gated fix generation and Jinja2 project templates.
- Dry-run planning, explicit license selection, language-aware CI and ignore templates.
- Timestamped backups for explicitly confirmed README replacement.

## [0.2.0] — Read-only Repository Audit
- Implemented local, read-only repository essentials scanning and explainable readiness scoring.
- Added structured findings and text/JSON output.

## [0.1.0] — Project Foundation
- Established the Python package, CLI, validated configuration, tests, CI, and documentation.
