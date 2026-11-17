# Release integrity verification

Repo Fixer's release verifier builds a wheel and source distribution (sdist), validates their embedded package metadata, installs each artifact in a temporary virtual environment, runs the installed CLI help as a smoke test, and writes SHA-256 sidecars.

Run the verifier from a clean checkout before every release. It checks the artifacts that were actually built, rather than trusting their filenames alone.

## What it verifies

- Builds one wheel and one sdist from temporary copies of the selected checkout. Build output is kept outside the checkout.
- Validates wheel ZIP integrity and the unique canonical top-level `.dist-info/METADATA` entry. Nested vendored metadata is ignored. The canonical directory name and version, embedded `Name` and `Version`, wheel filename, and expected project identity must agree.
- Validates the sdist archive and its single root-level `PKG-INFO`, including the expected distribution name and version.
- Validates SPDX `License-Expression: MIT` and `License-File: LICENSE` metadata, plus the packaged license file in both wheel and sdist.
- Installs the wheel and sdist separately in temporary virtual environments, then runs `python -m repo_fixer --help` from a temporary smoke-test directory.
- Writes SHA-256 sidecars for the wheel and sdist after successful validation and smoke tests.

The artifacts directory must be empty. The verifier refuses to build into a non-empty directory and creates checksum sidecars exclusively, refusing to replace existing sidecars.

## CLI

```text
python scripts/verify_release_artifacts.py [--checkout PATH] [--artifacts-dir EMPTY_DIR] [--wheelhouse DIR] [--no-index]
```

- `--checkout PATH`: source checkout to copy and build. Defaults to the checkout containing the script.
- `--artifacts-dir EMPTY_DIR`: destination for the newly built wheel, sdist, and checksum sidecars. Defaults to `dist/` in the script's repository.
- `--wheelhouse DIR`: also search this local directory for build and install dependencies. Package indexes remain enabled unless `--no-index` is also supplied.
- `--no-index`: disable package indexes. Requires `--wheelhouse`.

## The three dependency modes

Normal mode uses the configured package indexes:

```bash
python scripts/verify_release_artifacts.py
```

To search a local wheelhouse while keeping indexes available as fallback:

```bash
python scripts/verify_release_artifacts.py --wheelhouse <wheelhouse>
```

| Mode | Invocation | Dependency lookup |
|---|---|---|
| Normal | No wheelhouse options | Package indexes are enabled |
| Wheelhouse with indexes | `--wheelhouse DIR` | Local wheelhouse is searched first; indexes remain enabled as fallback |
| Offline | `--wheelhouse DIR --no-index` | Only the supplied wheelhouse is used; package indexes are disabled |

**A wheelhouse by itself is not offline.** The verifier passes `--find-links` when `--wheelhouse` is set. Only `--no-index` disables indexes. The combination `--no-index` without `--wheelhouse` is rejected.

## Verified offline recipe

Use a fresh, empty wheelhouse for each run. The download command collects the build tools and the project's runtime requirements as binary wheels. Run these commands from the repository root.

### Windows PowerShell

```powershell
$wheelhouse = Join-Path $env:TEMP ("repo-fixer-wheelhouse-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $wheelhouse | Out-Null

python -m pip download --only-binary=:all: --dest $wheelhouse "setuptools>=77.0.3" wheel -r requirements.txt

python scripts\verify_release_artifacts.py --wheelhouse $wheelhouse --no-index
```

### macOS / Linux

```bash
wheelhouse="$(mktemp -d)"

python -m pip download --only-binary=:all: --dest "$wheelhouse" "setuptools>=77.0.3" wheel -r requirements.txt

python scripts/verify_release_artifacts.py --wheelhouse "$wheelhouse" --no-index
```

The wheelhouse must contain compatible wheels for the current Python/platform, including `setuptools>=77.0.3`, `wheel`, and the dependencies needed to install the project. This floor matches the build-system requirement in `pyproject.toml`. Do not reuse a wheelhouse containing unrelated or malformed wheel files: every wheel in the directory is validated.

## Expected successful output

The verifier prints one progress line for each build/install/smoke-test phase, followed by `VERIFIED:` lines for both artifacts and both checksum sidecars. A successful run exits with status `0`.

```text
Building wheel...
Building sdist...
Installing wheel...
Smoke test...
Installing sdist...
Smoke test...
VERIFIED: <artifacts-dir>/<wheel-file>.whl
VERIFIED: <artifacts-dir>/<wheel-file>.whl.sha256
VERIFIED: <artifacts-dir>/<sdist-file>.tar.gz
VERIFIED: <artifacts-dir>/<sdist-file>.tar.gz.sha256
```

The paths and artifact filenames above are placeholders; the verifier prints the actual paths it created.

## Common errors

| Error | Meaning and next step |
|---|---|
| `refusing to build into a non-empty artifact directory` | The output directory already contains files. Choose a new empty directory or inspect and move the existing contents yourself; the verifier will not clear it. |
| `checksum sidecar conflict; refusing to overwrite` | A target `.sha256` file already exists. Preserve and inspect it, then choose a clean artifact directory. |
| `expected exactly one top-level .dist-info/METADATA file` | A wheel has no unique canonical metadata entry. Nested vendored metadata does not count. Re-download or rebuild the affected wheel from a trusted source. |
| `canonical directory rule failed` | The canonical `.dist-info` directory name/version disagrees with the embedded `Name` and `Version`. Treat the wheel as invalid. |
| `required setuptools wheel is missing` | The wheelhouse does not contain one valid wheel for that build tool. Rebuild the wheelhouse using the recipe above. |
| `setuptools>=77.0.3 is required` | The wheelhouse contains a setuptools version below the build-system floor declared in `pyproject.toml`. Download a compatible wheel. |
| `--no-index requires --wheelhouse` | Offline mode was requested without a local dependency directory. Supply both options. |
| pip reports `No matching distribution found` or a missing package | The required compatible dependency wheel is absent from the wheelhouse, or the wheel is incompatible with this Python/platform. Rebuild the wheelhouse for the environment and include the dependency. |

A wheelhouse validation error may identify a wheel other than setuptools or wheel: all wheel files in the supplied directory are checked for ZIP integrity, canonical metadata, and filename/metadata consistency.

## Recommended release practice

1. Start from a fresh clone of the exact commit intended for release.
2. Run the verifier in normal mode.
3. For an offline release check, prepare a fresh wheelhouse and run the verified offline recipe.
4. Confirm the process exits with status `0`, all four `VERIFIED:` lines appear, and the checkout remains clean.
5. Review the wheel, sdist, and checksum sidecars before publishing.

The verifier does not publish to a package index, create a Git tag, or create a GitHub release.
