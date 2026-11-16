# Release process

This runbook describes the maintainer-controlled release sequence for Repo Fixer. It does not publish packages, create tags, or create GitHub releases automatically.

## Release decisions required

Before preparing a release, explicitly decide and record:

- **Release version — decision required.** Choose the version only after reviewing the changes and release notes. The version in `pyproject.toml` is the package version source of truth.
- **PyPI project name — decision required.** Confirm the intended distribution name before creating or publishing a PyPI project. A PyPI JSON lookup returning HTTP 404 is only a point-in-time availability observation; it does not reserve the name.
- **Release notes — decision required.** Confirm the changelog entry and any compatibility or migration notes.

Do not infer or silently choose these values from branch names, tags, or prior releases.

## 1. Prepare the exact source revision

1. Wait until the release-related pull requests are reviewed and merged through the normal maintainer process.
2. Start from a fresh clone of the intended release commit.
3. Confirm the checkout is on the intended commit and has no uncommitted changes:
   ```bash
   git status --short
   git rev-parse HEAD
   ```
4. Confirm the version in `pyproject.toml` and the corresponding changelog heading agree. Do not edit a released tag or rewrite published history.

## 2. Run release verification in normal mode

Use a new, empty output directory. From the repository root:

```bash
python scripts/verify_release_artifacts.py --artifacts-dir artifacts-normal
```

The verifier builds a wheel and source distribution from isolated source copies, validates their metadata, installs each artifact in a temporary virtual environment, runs the installed CLI help smoke test, and writes SHA-256 sidecars.

A successful run exits with status zero and prints `VERIFIED:` lines for the wheel, sdist, and both checksum sidecars.

## 3. Run release verification in offline mode

Prepare a new, empty wheelhouse for the current Python/platform. Read the setuptools build requirement directly from `pyproject.toml`; do not maintain a second hard-coded minimum in release commands.

### Windows PowerShell

```powershell
$wheelhouse = Join-Path $env:TEMP ("repo-fixer-wheelhouse-" + [guid]::NewGuid().ToString("N"))
$artifacts = Join-Path $env:TEMP ("repo-fixer-artifacts-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $wheelhouse, $artifacts | Out-Null

$buildRequirement = python -c "import tomllib; p=tomllib.load(open('pyproject.toml','rb')); print(next(x for x in p['build-system']['requires'] if x.startswith('setuptools')))"
python -m pip download --only-binary=:all: --dest $wheelhouse $buildRequirement wheel -r requirements.txt
python scripts\verify_release_artifacts.py --wheelhouse $wheelhouse --no-index --artifacts-dir $artifacts
```

### macOS / Linux

```bash
wheelhouse="$(mktemp -d)"
artifacts="$(mktemp -d)"
build_requirement="$(python -c "import tomllib; p=tomllib.load(open('pyproject.toml','rb')); print(next(x for x in p['build-system']['requires'] if x.startswith('setuptools')))")"
python -m pip download --only-binary=:all: --dest "$wheelhouse" "$build_requirement" wheel -r requirements.txt
python scripts/verify_release_artifacts.py --wheelhouse "$wheelhouse" --no-index --artifacts-dir "$artifacts"
```

The offline invocation must include both `--wheelhouse` and `--no-index`. A wheelhouse alone still permits package-index fallback. Use a compatible wheelhouse for each target Python/platform.

## 4. Inspect the exact artifacts and checksums

Before publishing:

1. Confirm both the wheel and sdist are present and correspond to the version selected in `pyproject.toml`.
2. Inspect the wheel's `.dist-info/METADATA` and confirm the SPDX `License-Expression`, `License-File`, and packaged license file are present.
3. Inspect the sdist's root `PKG-INFO` and confirm its `LICENSE` file is present.
4. Verify the `.sha256` sidecars against the exact artifact files. On Windows:
   ```powershell
   Get-FileHash -Algorithm SHA256 .\artifacts-normal\*.whl
   Get-FileHash -Algorithm SHA256 .\artifacts-normal\*.tar.gz
   ```
5. Preserve the verified files. Do not rebuild after verification and then upload a different artifact under the same release.

## 5. Create the tag and GitHub release

Only after explicit maintainer approval of the version and release notes:

1. Confirm the selected tag does not already exist.
2. Create the version tag on the exact verified commit. Never move, delete, or recreate a published tag.
3. Push the new tag and create the GitHub release from that tag.
4. Attach the exact verified wheel, sdist, and checksum sidecars. Do not regenerate or rename them after verification.

The tag and GitHub release are separate maintainer actions; the verifier does neither.

## 6. Publish to PyPI through trusted publishing

Use the repository's trusted-publishing workflow only after its one-time PyPI publisher configuration and protected GitHub environment are complete. Review the workflow and release verification evidence before approving the publish job. Do not use a long-lived PyPI API token in repository secrets.

The publishing workflow must upload the exact wheel and sdist produced and verified by the release workflow; it must not rebuild them in the publishing job.

## 7. Verify the published installation

After publishing:

1. Confirm the PyPI project page lists the intended version and expected files.
2. In a clean virtual environment, install the published version from PyPI.
3. Run `repo-fixer --version` and confirm it reports the approved version.
4. Record the PyPI project URL, release tag, source commit, artifact filenames, and SHA-256 values in the release record.

## Stop conditions

Stop and ask for maintainer review if the package version and changelog disagree, the PyPI name has not been explicitly confirmed, either verifier mode fails, artifact metadata or license payload is missing, checksums differ, the tag already exists, or the trusted-publishing configuration is incomplete.
