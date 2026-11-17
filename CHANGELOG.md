# Changelog

All notable changes to Repo Fixer are documented here.

## [Unreleased]

## [0.3.2] - 2026-11-17

### Added
- Added a release-artifact verifier that builds, validates, installs, smoke-tests, and checksums wheel and source-distribution artifacts.
- Added release-verification CI for normal and offline artifact checks across supported Python versions on Linux and Windows.
- Added a maintainer release-process runbook covering exact-commit verification, artifact metadata, checksums, and post-release validation.

### Changed
- Raised the setuptools build requirement to `>=77.0.3` and enforced PEP 639 license metadata plus packaged LICENSE files in wheel and source-distribution artifacts.
- Added project homepage, repository, documentation, issue-tracker, and changelog URLs to package metadata; limited Python classifiers to 3.11 and 3.12.

### Fixed
- Prompted interactively when license selection is required and provided explicit `--license` guidance in non-interactive mode.
- Restored correct em-dash rendering in findings output and added regression coverage against Unicode mojibake.
- Linked the maintainer release-process runbook from the documentation home.

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
