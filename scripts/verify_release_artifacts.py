#!/usr/bin/env python3
"""Build and independently smoke-test Repo Fixer release artifacts.

Only the Python standard library and pip are required. Build isolation is handled
by pip; the third-party `build` package is deliberately not used.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from email.parser import Parser
from pathlib import Path, PurePosixPath

from pip._vendor.packaging.utils import canonicalize_name, parse_wheel_filename
from pip._vendor.packaging.version import InvalidVersion, Version

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROJECT_FILE = REPOSITORY_ROOT / "pyproject.toml"
MINIMUM_SETUPTOOLS = Version("68")
RUN_TIMEOUT_SECONDS = 600


class VerificationError(RuntimeError):
    """A release artifact or verification operation failed safely."""


def _metadata_from_bytes(data: bytes, source: Path) -> dict[str, str]:
    try:
        message = Parser().parsestr(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise VerificationError(f"{source}: invalid package metadata: {exc}") from exc
    name = message.get("Name")
    version = message.get("Version")
    if not name or not version:
        raise VerificationError(f"{source}: metadata must contain Name and Version")
    try:
        Version(version)
    except InvalidVersion as exc:
        raise VerificationError(f"{source}: invalid version {version!r}") from exc
    return {"Name": name, "Version": version}


def _same_distribution(left: str, right: str) -> bool:
    return canonicalize_name(left) == canonicalize_name(right)


def _canonical_wheel_metadata(
    archive: zipfile.ZipFile, wheel_path: Path
) -> dict[str, str]:
    """Read the unique top-level dist-info metadata and verify its directory."""
    canonical_files = [
        PurePosixPath(member)
        for member in archive.namelist()
        if len(PurePosixPath(member).parts) == 2
        and PurePosixPath(member).parts[0].endswith(".dist-info")
        and PurePosixPath(member).parts[1] == "METADATA"
    ]
    if len(canonical_files) != 1:
        raise VerificationError(
            f"{wheel_path.name}: canonical metadata rule failed; expected exactly "
            f"one top-level .dist-info/METADATA file, found {len(canonical_files)}"
        )

    metadata_path = canonical_files[0]
    metadata = _metadata_from_bytes(archive.read(metadata_path.as_posix()), wheel_path)
    directory_stem = metadata_path.parts[0][: -len(".dist-info")]
    directory_name, separator, directory_version = directory_stem.rpartition("-")
    try:
        directory_version_matches = (
            bool(separator)
            and Version(directory_version) == Version(metadata["Version"])
        )
    except InvalidVersion:
        directory_version_matches = False
    if not (
        directory_name
        and _same_distribution(directory_name, metadata["Name"])
        and directory_version_matches
    ):
        raise VerificationError(
            f"{wheel_path.name}: canonical directory rule failed; directory "
            f"{metadata_path.parts[0]!r} disagrees with embedded Name and Version"
        )
    return metadata


def validate_wheel_artifact(
    wheel_path: Path, expected_name: str, expected_version: str
) -> dict[str, str]:
    """Validate ZIP integrity, wheel filename consistency, and embedded metadata."""
    wheel_path = Path(wheel_path)
    try:
        with zipfile.ZipFile(wheel_path) as archive:
            corrupt_member = archive.testzip()
            if corrupt_member is not None:
                raise VerificationError(
                    f"{wheel_path}: corrupt ZIP member {corrupt_member!r}"
                )
            metadata = _canonical_wheel_metadata(archive, wheel_path)
    except (OSError, zipfile.BadZipFile, RuntimeError, KeyError) as exc:
        if isinstance(exc, VerificationError):
            raise
        raise VerificationError(f"{wheel_path}: unreadable wheel: {exc}") from exc

    try:
        filename_name, filename_version, _build, _tags = parse_wheel_filename(
            wheel_path.name
        )
    except (InvalidVersion, ValueError) as exc:
        raise VerificationError(f"{wheel_path}: invalid wheel filename: {exc}") from exc

    if not _same_distribution(str(filename_name), metadata["Name"]):
        raise VerificationError(
            f"{wheel_path}: filename distribution does not match embedded metadata"
        )
    if str(filename_version) != metadata["Version"]:
        raise VerificationError(
            f"{wheel_path}: filename version does not match embedded metadata"
        )
    if not _same_distribution(metadata["Name"], expected_name):
        raise VerificationError(
            f"{wheel_path}: expected distribution {expected_name!r}, "
            f"found {metadata['Name']!r}"
        )
    if metadata["Version"] != expected_version:
        raise VerificationError(
            f"{wheel_path}: expected version {expected_version!r}, "
            f"found {metadata['Version']!r}"
        )
    return metadata


def validate_sdist_artifact(
    sdist_path: Path, expected_name: str, expected_version: str
) -> dict[str, str]:
    """Validate an sdist tar archive and its root PKG-INFO metadata."""
    sdist_path = Path(sdist_path)
    try:
        with tarfile.open(sdist_path, mode="r:*") as archive:
            all_members = archive.getmembers()
            for member in all_members:
                if member.isfile():
                    member_stream = archive.extractfile(member)
                    if member_stream is None:
                        raise VerificationError(
                            f"{sdist_path}: unreadable tar member {member.name!r}"
                        )
                    with member_stream:
                        while member_stream.read(1024 * 1024):
                            pass
            members = [
                member
                for member in all_members
                if member.isfile()
                and PurePosixPath(member.name).name == "PKG-INFO"
                and len(PurePosixPath(member.name).parts) == 2
            ]
            if len(members) != 1:
                raise VerificationError(
                    f"{sdist_path}: expected exactly one PKG-INFO file"
                )
            stream = archive.extractfile(members[0])
            if stream is None:
                raise VerificationError(f"{sdist_path}: PKG-INFO is unreadable")
            metadata = _metadata_from_bytes(stream.read(), sdist_path)
    except (OSError, tarfile.TarError, EOFError) as exc:
        raise VerificationError(f"{sdist_path}: unreadable sdist: {exc}") from exc

    if not _same_distribution(metadata["Name"], expected_name):
        raise VerificationError(
            f"{sdist_path}: expected distribution {expected_name!r}, "
            f"found {metadata['Name']!r}"
        )
    if metadata["Version"] != expected_version:
        raise VerificationError(
            f"{sdist_path}: expected version {expected_version!r}, "
            f"found {metadata['Version']!r}"
        )
    return metadata


def validate_existing_artifacts(
    artifact_dir: Path, expected_name: str, expected_version: str
) -> tuple[list[Path], list[Path]]:
    """Validate existing wheel and sdist files without modifying the directory."""
    artifact_dir = Path(artifact_dir)
    if not artifact_dir.is_dir():
        raise VerificationError(f"{artifact_dir}: artifact directory does not exist")
    wheels = sorted(artifact_dir.glob("*.whl"))
    sdists = sorted(
        path
        for path in artifact_dir.iterdir()
        if path.is_file() and path.name.endswith(".tar.gz")
    )
    if len(wheels) != 1 or len(sdists) != 1:
        existing = [*wheels, *sdists]
        offending = existing[0] if existing else artifact_dir
        raise VerificationError(
            f"{offending}: expected exactly one wheel and one sdist; "
            f"found {len(wheels)} wheel(s) and {len(sdists)} sdist(s)"
        )
    validate_wheel_artifact(wheels[0], expected_name, expected_version)
    validate_sdist_artifact(sdists[0], expected_name, expected_version)
    return wheels, sdists


def validate_wheelhouse(wheelhouse: Path) -> dict[str, Path]:
    """Validate wheel ZIPs and locate setuptools>=68 and wheel by metadata."""
    wheelhouse = Path(wheelhouse)
    if not wheelhouse.is_dir():
        raise VerificationError(f"{wheelhouse}: wheelhouse directory does not exist")
    candidates = sorted(wheelhouse.glob("*.whl"))
    found: dict[str, Path] = {}
    for candidate in candidates:
        try:
            with zipfile.ZipFile(candidate) as archive:
                corrupt_member = archive.testzip()
                if corrupt_member is not None:
                    raise VerificationError(
                        f"{candidate}: corrupt ZIP member {corrupt_member!r}"
                    )
                metadata = _canonical_wheel_metadata(archive, candidate)
        except (OSError, zipfile.BadZipFile, RuntimeError, KeyError) as exc:
            if isinstance(exc, VerificationError):
                raise
            raise VerificationError(f"{candidate}: invalid wheel: {exc}") from exc

        try:
            filename_name, filename_version, _build, _tags = parse_wheel_filename(
                candidate.name
            )
        except (InvalidVersion, ValueError) as exc:
            raise VerificationError(
                f"{candidate}: invalid wheel filename: {exc}"
            ) from exc
        if not _same_distribution(str(filename_name), metadata["Name"]):
            raise VerificationError(
                f"{candidate}: filename distribution does not match embedded metadata"
            )
        if str(filename_version) != metadata["Version"]:
            raise VerificationError(
                f"{candidate}: filename version does not match embedded metadata"
            )

        distribution = canonicalize_name(metadata["Name"])
        if distribution in {"setuptools", "wheel"}:
            if distribution in found:
                raise VerificationError(
                    f"{candidate}: duplicate {distribution} wheels in wheelhouse"
                )
            found[distribution] = candidate
            if distribution == "setuptools":
                try:
                    version = Version(metadata["Version"])
                except InvalidVersion as exc:
                    raise VerificationError(
                        f"{candidate}: invalid setuptools version"
                    ) from exc
                if version < MINIMUM_SETUPTOOLS:
                    raise VerificationError(
                        f"{candidate}: setuptools>=68 is required; "
                        f"found {metadata['Version']}"
                    )

    for required in ("setuptools", "wheel"):
        if required not in found:
            raise VerificationError(
                f"{wheelhouse}: required {required} wheel is missing"
            )
    return found


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksums(artifacts: Sequence[Path]) -> list[Path]:
    """Create checksum sidecars only when none of the target sidecars exist."""
    sidecars = [Path(f"{Path(artifact)}.sha256") for artifact in artifacts]
    conflicts = [sidecar for sidecar in sidecars if sidecar.exists()]
    if conflicts:
        raise VerificationError(
            "checksum sidecar conflict; refusing to overwrite: "
            + ", ".join(str(path) for path in conflicts)
        )

    created: list[Path] = []
    for artifact, sidecar in zip(artifacts, sidecars, strict=True):
        checksum = sha256_file(Path(artifact))
        with sidecar.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(f"{checksum}  {Path(artifact).name}\n")
        created.append(sidecar)
    return created


def ensure_empty_artifact_directory(artifact_dir: Path) -> None:
    """Reject any pre-existing content instead of mixing or replacing artifacts."""
    artifact_dir = Path(artifact_dir)
    if artifact_dir.exists() and not artifact_dir.is_dir():
        raise VerificationError(f"{artifact_dir}: artifact path is not a directory")
    if artifact_dir.is_dir():
        entries = sorted(artifact_dir.iterdir())
        if entries:
            raise VerificationError(
                f"{entries[0]}: refusing to build into a non-empty artifact directory"
            )


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def ensure_safe_cleanup_target(
    target: Path, checkout: Path, artifacts_dir: Path
) -> Path:
    """Require cleanup targets to be outside checkout and artifact directories."""
    resolved_target = Path(target).resolve()
    resolved_checkout = Path(checkout).resolve()
    resolved_artifacts = Path(artifacts_dir).resolve()
    protected = (resolved_checkout, resolved_artifacts)
    for protected_path in protected:
        if (
            resolved_target == protected_path
            or _is_relative_to(resolved_target, protected_path)
            or _is_relative_to(protected_path, resolved_target)
        ):
            raise VerificationError(
                f"refusing cleanup target {resolved_target}: it overlaps "
                f"protected path {protected_path}"
            )
    return resolved_target


@contextmanager
def temporary_workspace(checkout: Path, artifacts_dir: Path) -> Iterator[Path]:
    """Create a temporary workspace outside the checkout and artifact directory."""
    with tempfile.TemporaryDirectory(prefix="repo-fixer-release-") as temporary:
        workspace = ensure_safe_cleanup_target(Path(temporary), checkout, artifacts_dir)
        yield workspace


def venv_python(environment: Path) -> Path:
    """Return the platform-correct interpreter path for a virtual environment."""
    if os.name == "nt":
        return Path(environment) / "Scripts" / "python.exe"
    return Path(environment) / "bin" / "python"


def pip_index_arguments(wheelhouse: Path | None, no_index: bool) -> list[str]:
    """Return index flags shared by builds and installs."""
    if no_index and wheelhouse is None:
        raise VerificationError("--no-index requires --wheelhouse")
    flags: list[str] = []
    if no_index:
        flags.append("--no-index")
    if wheelhouse is not None:
        flags.extend(["--find-links", str(wheelhouse)])
    return flags


def pip_install_command(
    python: Path,
    artifact: Path,
    *,
    wheelhouse: Path | None,
    no_index: bool,
) -> list[str]:
    """Build the exact pip install command for normal, wheelhouse, or offline mode."""
    command = [
        str(python),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-input",
        *pip_index_arguments(wheelhouse, no_index),
        str(artifact),
    ]
    return command


def _run(command: Sequence[str], *, cwd: Path | None = None) -> None:
    try:
        result = subprocess.run(
            list(command),
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        raise VerificationError(
            f"command timed out: {' '.join(command)}\n"
            f"stdout:\n{stdout}\nstderr:\n{stderr}"
        ) from exc
    except OSError as exc:
        raise VerificationError(
            f"command failed to execute: {command[0]}: {exc}"
        ) from exc
    if result.returncode != 0:
        raise VerificationError(
            f"command exited with status {result.returncode}: "
            f"{' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def install_and_smoke(
    artifact: Path,
    *,
    checkout: Path,
    artifacts_dir: Path,
    wheelhouse: Path | None,
    no_index: bool,
) -> None:
    """Install one artifact in an isolated venv and execute its installed CLI."""
    with temporary_workspace(checkout, artifacts_dir) as workspace:
        environment = workspace / "venv"
        smoke_project = workspace / "smoke-project"
        smoke_project.mkdir()
        _run([sys.executable, "-m", "venv", str(environment)])
        python = venv_python(environment)
        _run(
            pip_install_command(
                python, Path(artifact), wheelhouse=wheelhouse, no_index=no_index
            )
        )
        print("Smoke test...", flush=True)
        _run([str(python), "-m", "repo_fixer", "--help"], cwd=smoke_project)


def _project_identity(project_file: Path = PROJECT_FILE) -> tuple[str, str]:
    try:
        with project_file.open("rb") as stream:
            project = tomllib.load(stream)["project"]
        return str(project["name"]), str(project["version"])
    except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
        message = f"{project_file}: cannot read project identity: {exc}"
        raise VerificationError(message) from exc


def _copy_checkout_for_build(checkout: Path, destination: Path, *, step: str) -> Path:
    """Copy project sources outside the checkout before invoking build backends."""
    try:
        return Path(
            shutil.copytree(
                checkout,
                destination,
                ignore=shutil.ignore_patterns(
                    ".git",
                    ".venv",
                    "__pycache__",
                    "*.py[cod]",
                    ".pytest_cache",
                    ".mypy_cache",
                    ".ruff_cache",
                    "build",
                    "dist",
                    "*.egg-info",
                ),
            )
        )
    except OSError as exc:
        raise VerificationError(
            f"{step} failed: could not prepare isolated build source "
            f"from {checkout}: {exc}"
        ) from exc


def _run_build_step(
    step: str, command: Sequence[str], *, cwd: Path | None = None
) -> None:
    """Run one named build step and retain the underlying command diagnostics."""
    try:
        _run(command, cwd=cwd)
    except VerificationError as exc:
        raise VerificationError(f"{step} failed:\n{exc}") from exc


def build_artifacts(
    checkout: Path,
    artifact_dir: Path,
    *,
    wheelhouse: Path | None,
    no_index: bool,
) -> tuple[list[Path], list[Path]]:
    """Build a wheel with pip and an sdist with setuptools' PEP 517 backend."""
    ensure_empty_artifact_directory(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    index_flags = pip_index_arguments(wheelhouse, no_index)

    with temporary_workspace(checkout, artifact_dir) as workspace:
        wheel_source = _copy_checkout_for_build(
            Path(checkout), workspace / "wheel-source", step="Wheel build"
        )
        print("Building wheel...", flush=True)
        wheel_command = [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--disable-pip-version-check",
            "--no-deps",
            *index_flags,
            "--wheel-dir",
            str(artifact_dir),
            str(wheel_source),
        ]
        _run_build_step("Wheel build", wheel_command, cwd=wheel_source)

        print("Building sdist...", flush=True)
        sdist_source = _copy_checkout_for_build(
            Path(checkout),
            workspace / "sdist-source",
            step="Source distribution build",
        )
        build_environment = workspace / "sdist-build-venv"
        _run_build_step(
            "Source distribution build",
            [sys.executable, "-m", "venv", str(build_environment)],
        )
        build_python = venv_python(build_environment)
        install_build_requirements = [
            str(build_python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            *index_flags,
            "setuptools>=68",
            "wheel",
        ]
        _run_build_step("Source distribution build", install_build_requirements)
        sdist_script = (
            "import sys\n"
            "from setuptools.build_meta import build_sdist\n"
            "print(build_sdist(sys.argv[1]))\n"
        )
        sdist_command = [
            str(build_python),
            "-c",
            sdist_script,
            str(artifact_dir),
        ]
        _run_build_step("Source distribution build", sdist_command, cwd=sdist_source)

    name, version = _project_identity(Path(checkout) / "pyproject.toml")
    return validate_existing_artifacts(artifact_dir, name, version)


def verify_release(
    checkout: Path,
    artifact_dir: Path,
    *,
    wheelhouse: Path | None,
    no_index: bool,
) -> list[Path]:
    """Build, validate, independently install, smoke-test, and checksum artifacts."""
    if no_index and wheelhouse is None:
        raise VerificationError("--no-index requires --wheelhouse")
    if wheelhouse is not None:
        validate_wheelhouse(wheelhouse)
    wheels, sdists = build_artifacts(
        checkout,
        artifact_dir,
        wheelhouse=wheelhouse,
        no_index=no_index,
    )
    artifacts = [*wheels, *sdists]
    expected_name, expected_version = _project_identity(
        Path(checkout) / "pyproject.toml"
    )
    for artifact in artifacts:
        if artifact.suffix == ".whl":
            validate_wheel_artifact(artifact, expected_name, expected_version)
        else:
            validate_sdist_artifact(artifact, expected_name, expected_version)
        install_phase = (
            "Installing wheel..." if artifact.suffix == ".whl" else "Installing sdist..."
        )
        print(install_phase, flush=True)
        install_and_smoke(
            artifact,
            checkout=checkout,
            artifacts_dir=artifact_dir,
            wheelhouse=wheelhouse,
            no_index=no_index,
        )
    write_checksums(artifacts)
    return artifacts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checkout",
        type=Path,
        default=REPOSITORY_ROOT,
        help="repository checkout to build (default: script's repository)",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=REPOSITORY_ROOT / "dist",
        help="empty directory for newly built artifacts",
    )
    parser.add_argument(
        "--wheelhouse",
        type=Path,
        help="local wheel directory; indexes remain enabled unless --no-index is set",
    )
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="disable package indexes (requires --wheelhouse)",
    )
    args = parser.parse_args(argv)
    try:
        artifacts = verify_release(
            args.checkout.resolve(),
            args.artifacts_dir.resolve(),
            wheelhouse=args.wheelhouse.resolve() if args.wheelhouse else None,
            no_index=args.no_index,
        )
    except VerificationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for artifact in artifacts:
        print(f"VERIFIED: {artifact}")
        print(f"VERIFIED: {artifact}.sha256")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
