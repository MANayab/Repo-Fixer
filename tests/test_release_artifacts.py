from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_release_artifacts", ROOT / "scripts" / "verify_release_artifacts.py"
)
assert SPEC is not None and SPEC.loader is not None
verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)


def make_wheel(
    path: Path,
    name: str,
    version: str,
    *,
    filename: str | None = None,
    license_expression: str | None = "MIT",
    declare_license_file: bool = True,
    include_license: bool = True,
) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    wheel_distribution = name.replace("-", "_")
    wheel_path = path / (filename or f"{wheel_distribution}-{version}-py3-none-any.whl")
    dist_info = f"{name.replace('-', '_')}-{version}.dist-info"
    metadata_lines = [
        "Metadata-Version: 2.4",
        f"Name: {name}",
        f"Version: {version}",
    ]
    if license_expression is not None:
        metadata_lines.append(f"License-Expression: {license_expression}")
    if declare_license_file:
        metadata_lines.append("License-File: LICENSE")
    metadata = "\n".join(metadata_lines) + "\n\n"
    with zipfile.ZipFile(wheel_path, "w") as archive:
        archive.writestr(f"{dist_info}/METADATA", metadata)
        if include_license:
            archive.writestr(f"{dist_info}/licenses/LICENSE", "MIT License\n")
        archive.writestr(
            f"{dist_info}/WHEEL",
            "Wheel-Version: 1.0\nGenerator: pytest\nRoot-Is-Purelib: true\n"
            "Tag: py3-none-any\n",
        )
    return wheel_path


def make_sdist(
    path: Path,
    name: str,
    version: str,
    *,
    license_expression: str | None = "MIT",
    declare_license_file: bool = True,
    include_license: bool = True,
) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    archive_path = path / f"{name}-{version}.tar.gz"
    info = tarfile.TarInfo(f"{name}-{version}/PKG-INFO")
    metadata_lines = [
        "Metadata-Version: 2.4",
        f"Name: {name}",
        f"Version: {version}",
    ]
    if license_expression is not None:
        metadata_lines.append(f"License-Expression: {license_expression}")
    if declare_license_file:
        metadata_lines.append("License-File: LICENSE")
    data = ("\n".join(metadata_lines) + "\n\n").encode()
    info.size = len(data)
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.addfile(info, io.BytesIO(data))
        if include_license:
            license_info = tarfile.TarInfo(f"{name}-{version}/LICENSE")
            license_data = b"MIT License\n"
            license_info.size = len(license_data)
            archive.addfile(license_info, io.BytesIO(license_data))
    return archive_path


def valid_wheelhouse(path: Path) -> None:
    make_wheel(path, "setuptools", "77.0.3")
    make_wheel(path, "wheel", "0.43.0")


def test_loads_verifier_as_a_real_module() -> None:
    assert callable(verifier.validate_wheel_artifact)
    assert callable(verifier.validate_sdist_artifact)


def test_wheel_integrity_and_metadata_are_read_from_archive(tmp_path: Path) -> None:
    wheel = make_wheel(tmp_path, "repo-fixer", "0.3.1")
    metadata = verifier.validate_wheel_artifact(wheel, "repo-fixer", "0.3.1")
    assert metadata["Name"] == "repo-fixer"
    assert metadata["Version"] == "0.3.1"
    assert metadata["License-Expression"] == "MIT"
    assert metadata["License-File"] == "LICENSE"
    with zipfile.ZipFile(wheel) as archive:
        assert "repo_fixer-0.3.1.dist-info/licenses/LICENSE" in archive.namelist()


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"license_expression": None}, "License-Expression"),
        ({"declare_license_file": False}, "License-File"),
        ({"include_license": False}, "packaged LICENSE"),
    ],
)
def test_wheel_rejects_missing_license_component(
    tmp_path: Path, kwargs: dict[str, object], message: str
) -> None:
    wheel = make_wheel(tmp_path, "repo-fixer", "0.3.1", **kwargs)
    with pytest.raises(verifier.VerificationError, match=message):
        verifier.validate_wheel_artifact(wheel, "repo-fixer", "0.3.1")


def test_corrupt_well_named_wheel_is_rejected(tmp_path: Path) -> None:
    wheel = tmp_path / "repo_fixer-0.3.1-py3-none-any.whl"
    wheel.write_bytes(b"not a zip archive")
    with pytest.raises(verifier.VerificationError, match="repo_fixer-0.3.1"):
        verifier.validate_wheel_artifact(wheel, "repo-fixer", "0.3.1")


def test_wheel_filename_must_agree_with_embedded_metadata(tmp_path: Path) -> None:
    wheel = make_wheel(
        tmp_path,
        "wheel",
        "0.43.0",
        filename="setuptools-77.0.3-py3-none-any.whl",
    )
    with pytest.raises(verifier.VerificationError, match="filename"):
        verifier.validate_wheel_artifact(wheel, "wheel", "0.43.0")


def test_sdist_metadata_is_validated(tmp_path: Path) -> None:
    sdist = make_sdist(tmp_path, "repo-fixer", "0.3.1")
    metadata = verifier.validate_sdist_artifact(sdist, "repo-fixer", "0.3.1")
    assert metadata["Name"] == "repo-fixer"
    assert metadata["Version"] == "0.3.1"
    assert metadata["License-Expression"] == "MIT"
    assert metadata["License-File"] == "LICENSE"
    with tarfile.open(sdist, mode="r:gz") as archive:
        assert "repo-fixer-0.3.1/LICENSE" in archive.getnames()


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"license_expression": None}, "License-Expression"),
        ({"declare_license_file": False}, "License-File"),
        ({"include_license": False}, "packaged LICENSE"),
    ],
)
def test_sdist_rejects_missing_license_component(
    tmp_path: Path, kwargs: dict[str, object], message: str
) -> None:
    sdist = make_sdist(tmp_path, "repo-fixer", "0.3.1", **kwargs)
    with pytest.raises(verifier.VerificationError, match=message):
        verifier.validate_sdist_artifact(sdist, "repo-fixer", "0.3.1")


def test_invalid_existing_artifact_is_rejected_without_replacement(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "repo_fixer-0.3.1-py3-none-any.whl"
    original = b"invalid existing artifact"
    artifact.write_bytes(original)
    with pytest.raises(verifier.VerificationError, match=str(artifact)):
        verifier.validate_existing_artifacts(tmp_path, "repo-fixer", "0.3.1")
    assert artifact.read_bytes() == original


def test_missing_setuptools_is_reported(tmp_path: Path) -> None:
    make_wheel(tmp_path, "wheel", "0.43.0")
    with pytest.raises(verifier.VerificationError, match="setuptools"):
        verifier.validate_wheelhouse(tmp_path)


def test_missing_wheel_is_reported(tmp_path: Path) -> None:
    make_wheel(tmp_path, "setuptools", "77.0.3")
    with pytest.raises(verifier.VerificationError, match="wheel"):
        verifier.validate_wheelhouse(tmp_path)


def test_old_setuptools_is_rejected(tmp_path: Path) -> None:
    make_wheel(tmp_path, "setuptools", "67.9.0")
    make_wheel(tmp_path, "wheel", "0.43.0")
    with pytest.raises(verifier.VerificationError, match="77.0.3"):
        verifier.validate_wheelhouse(tmp_path)


def test_wheelhouse_accepts_metadata_valid_build_dependencies(tmp_path: Path) -> None:
    valid_wheelhouse(tmp_path)
    result = verifier.validate_wheelhouse(tmp_path)
    assert set(result) == {"setuptools", "wheel"}


def test_wheelhouse_accepts_newer_setuptools(tmp_path: Path) -> None:
    make_wheel(tmp_path, "setuptools", "80.0.0")
    make_wheel(tmp_path, "wheel", "0.43.0")

    result = verifier.validate_wheelhouse(tmp_path)

    assert result["setuptools"].name == "setuptools-80.0.0-py3-none-any.whl"


def test_verifier_setuptools_floor_matches_pyproject() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    requirement = next(
        item
        for item in project["build-system"]["requires"]
        if item.startswith("setuptools")
    )

    assert requirement == f"setuptools>={verifier.MINIMUM_SETUPTOOLS}"


def test_well_named_but_misleading_dependency_wheel_is_not_accepted(
    tmp_path: Path,
) -> None:
    make_wheel(
        tmp_path,
        "wheel",
        "0.43.0",
        filename="setuptools-77.0.3-py3-none-any.whl",
    )
    with pytest.raises(verifier.VerificationError, match="filename"):
        verifier.validate_wheelhouse(tmp_path)


def test_checksum_conflict_leaves_every_existing_sidecar_unchanged(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.whl"
    second = tmp_path / "second.tar.gz"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    first_sidecar = Path(f"{first}.sha256")
    second_sidecar = Path(f"{second}.sha256")
    first_sidecar.write_bytes(b"keep-first\r\n")
    second_sidecar.write_bytes(b"keep-second\n")
    with pytest.raises(verifier.VerificationError, match="sidecar"):
        verifier.write_checksums([first, second])
    assert first_sidecar.read_bytes() == b"keep-first\r\n"
    assert second_sidecar.read_bytes() == b"keep-second\n"


def test_checksum_sidecars_are_created_exclusively(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.whl"
    artifact.write_bytes(b"payload")
    verifier.write_checksums([artifact])
    sidecar = Path(f"{artifact}.sha256")
    assert sidecar.read_text(encoding="utf-8").strip().split()[0] == (
        verifier.sha256_file(artifact)
    )


def test_cleanup_target_cannot_equal_or_contain_protected_paths(
    tmp_path: Path,
) -> None:
    checkout = tmp_path / "checkout"
    artifacts = checkout / "dist"
    checkout.mkdir()
    artifacts.mkdir()
    with pytest.raises(verifier.VerificationError):
        verifier.ensure_safe_cleanup_target(checkout, checkout, artifacts)
    with pytest.raises(verifier.VerificationError):
        verifier.ensure_safe_cleanup_target(tmp_path, checkout, artifacts)
    with pytest.raises(verifier.VerificationError):
        verifier.ensure_safe_cleanup_target(artifacts, checkout, artifacts)


def test_temporary_workspace_is_removed_after_success(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    artifacts = tmp_path / "dist"
    checkout.mkdir()
    artifacts.mkdir()
    with verifier.temporary_workspace(checkout, artifacts) as workspace:
        marker = workspace / "marker"
        marker.write_text("created", encoding="utf-8")
        assert marker.exists()
    assert not workspace.exists()


def test_temporary_workspace_is_removed_after_failure(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    artifacts = tmp_path / "dist"
    checkout.mkdir()
    artifacts.mkdir()
    workspace: Path | None = None
    with pytest.raises(RuntimeError, match="failure"):
        with verifier.temporary_workspace(checkout, artifacts) as created:
            workspace = created
            raise RuntimeError("failure")
    assert workspace is not None and not workspace.exists()


def test_venv_python_path_is_platform_specific(tmp_path: Path) -> None:
    environment = tmp_path / "venv"
    expected = (
        environment / "Scripts" / "python.exe"
        if os.name == "nt"
        else environment / "bin" / "python"
    )
    assert verifier.venv_python(environment) == expected


@pytest.mark.parametrize(
    ("wheelhouse", "no_index", "expected_flags"),
    [
        (None, False, []),
        (Path("local-wheels"), False, ["--find-links", "local-wheels"]),
        (Path("local-wheels"), True, ["--no-index", "--find-links", "local-wheels"]),
    ],
    ids=["normal-indexes-allowed", "wheelhouse-indexes-allowed", "offline"],
)
def test_pip_install_arguments_are_distinct(
    wheelhouse: Path | None, no_index: bool, expected_flags: list[str]
) -> None:
    command = verifier.pip_install_command(
        Path("venv-python"),
        Path("candidate.whl"),
        wheelhouse=wheelhouse,
        no_index=no_index,
    )
    assert command == [
        "venv-python",
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-input",
        *expected_flags,
        "candidate.whl",
    ]


def test_no_index_requires_a_wheelhouse() -> None:
    with pytest.raises(verifier.VerificationError, match="wheelhouse"):
        verifier.pip_install_command(
            Path("python"), Path("artifact.whl"), wheelhouse=None, no_index=True
        )


@pytest.mark.parametrize(
    ("wheelhouse", "no_index", "expected_flags"),
    [
        (None, False, []),
        (Path("local-wheels"), False, ["--find-links", "local-wheels"]),
        (Path("local-wheels"), True, ["--no-index", "--find-links", "local-wheels"]),
    ],
    ids=["normal-indexes-allowed", "wheelhouse-indexes-allowed", "offline"],
)
def test_build_and_install_share_exact_index_flags(
    wheelhouse: Path | None, no_index: bool, expected_flags: list[str]
) -> None:
    assert verifier.pip_index_arguments(wheelhouse, no_index) == expected_flags


@pytest.mark.parametrize(
    ("wheelhouse", "no_index", "expected_flags"),
    [
        (None, False, []),
        (Path("local-wheels"), False, ["--find-links", "local-wheels"]),
        (Path("local-wheels"), True, ["--no-index", "--find-links", "local-wheels"]),
    ],
)
def test_install_and_smoke_runs_real_flow_with_mocked_subprocess(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    wheelhouse: Path | None,
    no_index: bool,
    expected_flags: list[str],
) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: Any) -> Any:
        calls.append(command)
        return type("Completed", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(verifier.subprocess, "run", fake_run)
    artifact = tmp_path / "repo-fixer-0.3.1-py3-none-any.whl"
    artifact.write_bytes(b"test placeholder")
    checkout = tmp_path / "checkout"
    artifacts = tmp_path / "dist"
    checkout.mkdir()
    artifacts.mkdir()
    verifier.install_and_smoke(
        artifact,
        checkout=checkout,
        artifacts_dir=artifacts,
        wheelhouse=wheelhouse,
        no_index=no_index,
    )
    assert calls[0][1:4] == ["-m", "venv", str(calls[0][3])]
    assert calls[1] == [
        str(verifier.venv_python(Path(calls[0][3]))),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-input",
        *expected_flags,
        str(artifact),
    ]
    assert calls[2][0] == str(verifier.venv_python(Path(calls[0][3])))
    assert calls[2][1:3] == ["-m", "repo_fixer"]


@pytest.mark.parametrize("fail_on_call", [None, 2], ids=["success", "failure"])
def test_install_workspace_and_smoke_project_are_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_on_call: int | None
) -> None:
    original_workspace = verifier.temporary_workspace
    recorded: list[Path] = []
    call_number = 0

    from contextlib import contextmanager

    @contextmanager
    def recording_workspace(checkout: Path, artifacts_dir: Path):
        with original_workspace(checkout, artifacts_dir) as workspace:
            recorded.append(workspace)
            yield workspace

    def fake_run(command: list[str], **kwargs: Any) -> Any:
        nonlocal call_number
        call_number += 1
        if call_number == 1:
            Path(command[3]).mkdir()
        status = 1 if call_number == fail_on_call else 0
        return type(
            "Completed",
            (),
            {"returncode": status, "stdout": "", "stderr": "expected failure"},
        )()

    monkeypatch.setattr(verifier, "temporary_workspace", recording_workspace)
    monkeypatch.setattr(verifier.subprocess, "run", fake_run)
    checkout = tmp_path / "checkout"
    artifacts = tmp_path / "dist"
    checkout.mkdir()
    artifacts.mkdir()
    artifact = tmp_path / "candidate.whl"
    artifact.write_bytes(b"candidate")

    if fail_on_call is None:
        verifier.install_and_smoke(
            artifact,
            checkout=checkout,
            artifacts_dir=artifacts,
            wheelhouse=None,
            no_index=False,
        )
    else:
        with pytest.raises(verifier.VerificationError, match="status 1"):
            verifier.install_and_smoke(
                artifact,
                checkout=checkout,
                artifacts_dir=artifacts,
                wheelhouse=None,
                no_index=False,
            )

    assert len(recorded) == 1
    workspace = recorded[0]
    assert not workspace.exists()
    assert not (workspace / "venv").exists()
    assert not (workspace / "smoke-project").exists()


def test_build_refuses_nonempty_artifact_directory(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    artifacts = tmp_path / "dist"
    checkout.mkdir()
    artifacts.mkdir()
    sentinel = artifacts / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    with pytest.raises(verifier.VerificationError, match=str(sentinel)):
        verifier.ensure_empty_artifact_directory(artifacts)
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_cleanup_safety_handles_windows_style_separators_via_pathlib(
    tmp_path: Path,
) -> None:
    checkout = tmp_path / "work" / "repo"
    artifacts = checkout / "dist"
    checkout.mkdir(parents=True)
    artifacts.mkdir()
    child = checkout / "temporary"
    with pytest.raises(verifier.VerificationError):
        verifier.ensure_safe_cleanup_target(child, checkout, artifacts)


def _write_tiny_setuptools_project(checkout: Path) -> None:
    checkout.mkdir(parents=True, exist_ok=True)
    (checkout / "pyproject.toml").write_text(
        """[build-system]
requires = ["setuptools>=77.0.3", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "tiny-release-probe"
version = "1.2.3"
license = "MIT"
license-files = ["LICENSE"]

[tool.setuptools]
py-modules = ["tiny_release_probe"]
""",
        encoding="utf-8",
    )
    (checkout / "LICENSE").write_text("MIT License\n", encoding="utf-8")
    (checkout / "tiny_release_probe.py").write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )


def test_real_build_produces_wheel_and_sdist_without_modifying_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if importlib.util.find_spec("pip") is None:
        pytest.skip(
            "real build requires pip; setuptools and wheel are provisioned "
            "inside the isolated build environment"
        )

    for name in tuple(os.environ):
        if name.startswith("COV_CORE_") or name == "COVERAGE_PROCESS_START":
            monkeypatch.delenv(name, raising=False)

    checkout = tmp_path / "tiny-project"
    artifacts = tmp_path / "artifacts"
    _write_tiny_setuptools_project(checkout)

    before_listing = sorted(
        path.relative_to(checkout).as_posix() for path in checkout.rglob("*")
    )
    before_files = {
        path.relative_to(checkout).as_posix(): path.read_bytes()
        for path in checkout.rglob("*")
        if path.is_file()
    }

    wheels, sdists = verifier.build_artifacts(
        checkout, artifacts, wheelhouse=None, no_index=False
    )

    assert len(wheels) == 1
    assert len(sdists) == 1
    metadata = verifier.validate_sdist_artifact(
        sdists[0], "tiny-release-probe", "1.2.3"
    )
    assert metadata["Name"] == "tiny-release-probe"
    assert metadata["Version"] == "1.2.3"

    after_listing = sorted(
        path.relative_to(checkout).as_posix() for path in checkout.rglob("*")
    )
    after_files = {
        path.relative_to(checkout).as_posix(): path.read_bytes()
        for path in checkout.rglob("*")
        if path.is_file()
    }
    assert after_listing == before_listing
    assert after_files == before_files


def test_sdist_build_failure_names_step_and_includes_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkout = tmp_path / "tiny-project"
    artifacts = tmp_path / "artifacts"
    _write_tiny_setuptools_project(checkout)

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if "wheel" in command and "--wheel-dir" in command:
            wheel_dir = Path(command[command.index("--wheel-dir") + 1])
            make_wheel(wheel_dir, "tiny-release-probe", "1.2.3")
            return subprocess.CompletedProcess(command, 0, "wheel output", "")
        if command[1:3] == ["-m", "venv"]:
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[1:3] == ["-m", "pip"]:
            return subprocess.CompletedProcess(command, 0, "", "")
        if "-c" in command:
            return subprocess.CompletedProcess(
                command, 1, "backend stdout", "simulated sdist stderr"
            )
        pytest.fail(f"unexpected subprocess command: {command}")

    monkeypatch.setattr(verifier.subprocess, "run", fake_run)

    with pytest.raises(
        verifier.VerificationError, match="Source distribution build failed"
    ) as error:
        verifier.build_artifacts(checkout, artifacts, wheelhouse=None, no_index=False)

    assert "backend stdout" in str(error.value)
    assert "simulated sdist stderr" in str(error.value)


def make_wheel_with_layout(
    path: Path,
    filename: str,
    canonical_directories: list[tuple[str, str, str]],
    nested_metadata: list[tuple[str, str, str]] | None = None,
) -> Path:
    """Create a wheel with canonical and/or vendored nested dist-info metadata."""
    path.mkdir(parents=True, exist_ok=True)
    wheel_path = path / filename
    with zipfile.ZipFile(wheel_path, "w") as archive:
        for directory, name, version in canonical_directories:
            archive.writestr(
                f"{directory}/METADATA",
                f"Metadata-Version: 2.4\nName: {name}\nVersion: {version}\n"
                "License-Expression: MIT\nLicense-File: LICENSE\n\n",
            )
            archive.writestr(f"{directory}/licenses/LICENSE", "MIT License\n")
        for directory, name, version in nested_metadata or []:
            archive.writestr(
                f"setuptools/_vendor/{directory}/METADATA",
                f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n\n",
            )
    return wheel_path


def test_wheelhouse_uses_canonical_metadata_and_ignores_vendored_metadata(
    tmp_path: Path,
) -> None:
    make_wheel_with_layout(
        tmp_path,
        "setuptools-84.2.1-py3-none-any.whl",
        [("setuptools-84.2.1.dist-info", "setuptools", "84.2.1")],
        [("packaging-26.3.dist-info", "not-setuptools", "999.0")],
    )
    make_wheel_with_layout(
        tmp_path,
        "wheel-0.46.3-py3-none-any.whl",
        [("wheel-0.46.3.dist-info", "wheel", "0.46.3")],
    )
    found = verifier.validate_wheelhouse(tmp_path)
    assert set(found) == {"setuptools", "wheel"}
    assert found["setuptools"].name == "setuptools-84.2.1-py3-none-any.whl"


def test_wheelhouse_rejects_two_top_level_dist_info_directories(
    tmp_path: Path,
) -> None:
    make_wheel_with_layout(
        tmp_path,
        "setuptools-84.2.1-py3-none-any.whl",
        [
            ("setuptools-84.2.1.dist-info", "setuptools", "84.2.1"),
            ("other-1.0.dist-info", "other", "1.0"),
        ],
    )
    with pytest.raises(
        verifier.VerificationError, match="setuptools-84.2.1.*canonical"
    ):
        verifier.validate_wheelhouse(tmp_path)


def test_wheelhouse_rejects_only_nested_dist_info_metadata(tmp_path: Path) -> None:
    make_wheel_with_layout(
        tmp_path,
        "setuptools-84.2.1-py3-none-any.whl",
        [],
        [("setuptools-84.2.1.dist-info", "setuptools", "84.2.1")],
    )
    with pytest.raises(
        verifier.VerificationError, match="setuptools-84.2.1.*canonical"
    ):
        verifier.validate_wheelhouse(tmp_path)


@pytest.mark.parametrize(
    ("directory", "metadata_name", "metadata_version"),
    [
        ("setuptools-84.2.1.dist-info", "setuptools", "84.2.2"),
        ("setuptools-84.2.2.dist-info", "setuptools", "84.2.1"),
        ("other-84.2.1.dist-info", "setuptools", "84.2.1"),
    ],
    ids=[
        "metadata-version-disagrees",
        "directory-version-disagrees",
        "directory-name-disagrees",
    ],
)
def test_wheelhouse_rejects_canonical_directory_metadata_mismatch(
    tmp_path: Path, directory: str, metadata_name: str, metadata_version: str
) -> None:
    make_wheel_with_layout(
        tmp_path,
        "setuptools-84.2.1-py3-none-any.whl",
        [(directory, metadata_name, metadata_version)],
    )
    with pytest.raises(
        verifier.VerificationError, match="setuptools-84.2.1.*directory"
    ):
        verifier.validate_wheelhouse(tmp_path)


def test_wheelhouse_rejects_metadata_name_different_from_dependency(
    tmp_path: Path,
) -> None:
    make_wheel_with_layout(
        tmp_path,
        "setuptools-84.2.1-py3-none-any.whl",
        [("setuptools-84.2.1.dist-info", "not-setuptools", "84.2.1")],
    )
    with pytest.raises(verifier.VerificationError, match="setuptools-84.2.1"):
        verifier.validate_wheelhouse(tmp_path)


def test_wheelhouse_rejects_setuptools_below_minimum(tmp_path: Path) -> None:
    make_wheel_with_layout(
        tmp_path,
        "setuptools-67.9.0-py3-none-any.whl",
        [("setuptools-67.9.0.dist-info", "setuptools", "67.9.0")],
    )
    make_wheel_with_layout(
        tmp_path,
        "wheel-0.46.3-py3-none-any.whl",
        [("wheel-0.46.3.dist-info", "wheel", "0.46.3")],
    )
    with pytest.raises(verifier.VerificationError, match="77.0.3"):
        verifier.validate_wheelhouse(tmp_path)


def test_wheelhouse_accepts_parseable_wheel_version_without_minimum(
    tmp_path: Path,
) -> None:
    make_wheel_with_layout(
        tmp_path,
        "setuptools-84.2.1-py3-none-any.whl",
        [("setuptools-84.2.1.dist-info", "setuptools", "84.2.1")],
    )
    make_wheel_with_layout(
        tmp_path,
        "wheel-0.1-py3-none-any.whl",
        [("wheel-0.1.dist-info", "wheel", "0.1")],
    )
    found = verifier.validate_wheelhouse(tmp_path)
    assert found["wheel"].name == "wheel-0.1-py3-none-any.whl"


def test_wheelhouse_rejects_corrupt_well_named_wheel(tmp_path: Path) -> None:
    corrupt = tmp_path / "setuptools-84.2.1-py3-none-any.whl"
    corrupt.write_bytes(b"not a ZIP archive")
    with pytest.raises(verifier.VerificationError, match="setuptools-84.2.1"):
        verifier.validate_wheelhouse(tmp_path)


def test_repo_fixer_wheel_uses_canonical_metadata_and_ignores_nested(
    tmp_path: Path,
) -> None:
    wheel = make_wheel_with_layout(
        tmp_path,
        "repo_fixer-0.3.1-py3-none-any.whl",
        [("repo_fixer-0.3.1.dist-info", "repo-fixer", "0.3.1")],
        [("vendored-9.9.dist-info", "unrelated-vendor", "9.9")],
    )
    metadata = verifier.validate_wheel_artifact(wheel, "repo-fixer", "0.3.1")
    assert metadata == {
        "Name": "repo-fixer",
        "Version": "0.3.1",
        "License-Expression": "MIT",
        "License-File": "LICENSE",
    }


@pytest.mark.parametrize(
    "canonical_directories",
    [
        [
            ("repo_fixer-0.3.1.dist-info", "repo-fixer", "0.3.1"),
            ("other-1.0.dist-info", "other", "1.0"),
        ],
        [],
    ],
    ids=["multiple-canonical", "nested-only"],
)
def test_repo_fixer_wheel_rejects_non_unique_canonical_metadata(
    tmp_path: Path,
    canonical_directories: list[tuple[str, str, str]],
) -> None:
    nested = [("vendor-9.9.dist-info", "vendor", "9.9")]
    wheel = make_wheel_with_layout(
        tmp_path,
        "repo_fixer-0.3.1-py3-none-any.whl",
        canonical_directories,
        nested,
    )
    with pytest.raises(verifier.VerificationError, match="repo_fixer-0.3.1.*canonical"):
        verifier.validate_wheel_artifact(wheel, "repo-fixer", "0.3.1")


@pytest.mark.parametrize(
    ("directory", "name", "version"),
    [
        ("repo_fixer-0.3.1.dist-info", "repo-fixer", "0.3.2"),
        ("repo_fixer-0.3.2.dist-info", "repo-fixer", "0.3.1"),
    ],
    ids=["version-disagrees", "directory-disagrees"],
)
def test_repo_fixer_wheel_rejects_canonical_directory_disagreement(
    tmp_path: Path, directory: str, name: str, version: str
) -> None:
    wheel = make_wheel_with_layout(
        tmp_path,
        "repo_fixer-0.3.1-py3-none-any.whl",
        [(directory, name, version)],
    )
    with pytest.raises(verifier.VerificationError, match="repo_fixer-0.3.1.*directory"):
        verifier.validate_wheel_artifact(wheel, "repo-fixer", "0.3.1")


def test_repo_fixer_wheel_rejects_metadata_name_mismatch(tmp_path: Path) -> None:
    wheel = make_wheel_with_layout(
        tmp_path,
        "repo_fixer-0.3.1-py3-none-any.whl",
        [("repo_fixer-0.3.1.dist-info", "other-project", "0.3.1")],
    )
    with pytest.raises(verifier.VerificationError, match="repo_fixer-0.3.1"):
        verifier.validate_wheel_artifact(wheel, "repo-fixer", "0.3.1")


def test_real_offline_build_wheel_passes_canonical_metadata_rule(
    tmp_path: Path,
) -> None:
    wheelhouse = Path(os.environ.get("REPO_FIXER_TEST_WHEELHOUSE", ""))
    if not wheelhouse.is_dir():
        pytest.skip(
            "offline build-tool wheelhouse unavailable; set "
            "REPO_FIXER_TEST_WHEELHOUSE to a directory containing setuptools>=77.0.3 "
            "and wheel wheels"
        )
    try:
        verifier.validate_wheelhouse(wheelhouse)
    except verifier.VerificationError as exc:
        pytest.skip(f"offline build tools unavailable: {exc}")

    checkout = tmp_path / "tiny-project"
    artifacts = tmp_path / "artifacts"
    _write_tiny_setuptools_project(checkout)
    wheels, _sdists = verifier.build_artifacts(
        checkout, artifacts, wheelhouse=wheelhouse, no_index=True
    )
    assert len(wheels) == 1
    metadata = verifier.validate_wheel_artifact(
        wheels[0], "tiny-release-probe", "1.2.3"
    )
    assert metadata == {
        "Name": "tiny-release-probe",
        "Version": "1.2.3",
        "License-Expression": "MIT",
        "License-File": "LICENSE",
    }


def test_sdist_rejects_wrong_metadata_name(tmp_path: Path) -> None:
    sdist = make_sdist(tmp_path, "other-project", "0.3.1")
    with pytest.raises(verifier.VerificationError, match="expected distribution"):
        verifier.validate_sdist_artifact(sdist, "repo-fixer", "0.3.1")


def test_sdist_rejects_wrong_metadata_version(tmp_path: Path) -> None:
    sdist = make_sdist(tmp_path, "repo-fixer", "0.3.2")
    with pytest.raises(verifier.VerificationError, match="expected version"):
        verifier.validate_sdist_artifact(sdist, "repo-fixer", "0.3.1")


def test_sdist_rejects_missing_root_pkg_info(tmp_path: Path) -> None:
    archive_path = tmp_path / "repo-fixer-0.3.1.tar.gz"
    info = tarfile.TarInfo("repo-fixer-0.3.1/nested/PKG-INFO")
    data = b"Metadata-Version: 2.1\nName: repo-fixer\nVersion: 0.3.1\n\n"
    info.size = len(data)
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.addfile(info, io.BytesIO(data))
    with pytest.raises(verifier.VerificationError, match="exactly one PKG-INFO"):
        verifier.validate_sdist_artifact(archive_path, "repo-fixer", "0.3.1")


def test_repo_fixer_wheel_directory_name_uses_pep503_normalization(
    tmp_path: Path,
) -> None:
    wheel = make_wheel_with_layout(
        tmp_path,
        "repo_fixer-0.3.1-py3-none-any.whl",
        [("Repo.Fixer-0.3.1.dist-info", "Repo.Fixer", "0.3.1")],
    )
    metadata = verifier.validate_wheel_artifact(wheel, "repo-fixer", "0.3.1")
    assert metadata == {
        "Name": "Repo.Fixer",
        "Version": "0.3.1",
        "License-Expression": "MIT",
        "License-File": "LICENSE",
    }
