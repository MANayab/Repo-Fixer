from __future__ import annotations

import os

import pytest


@pytest.fixture
def symlink_supported(tmp_path):
    """Skip symlink tests when the current Windows user lacks permission."""
    target = tmp_path / "symlink-target"
    link = tmp_path / "symlink-link"

    target.write_text("test", encoding="utf-8")

    try:
        os.symlink(target, link)
    except OSError as exc:
        pytest.skip(f"Symlinks are not available on this system: {exc}")
    else:
        link.unlink()

    return True
