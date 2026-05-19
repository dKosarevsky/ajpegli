from __future__ import annotations

from pathlib import Path

import pytest

from tools.check_versions import (
    VersionMismatchError,
    check_static_versions,
    read_cmake_project_version,
    read_pyproject_version,
)


def test_read_pyproject_version(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "ajpegli"
version = "1.2.3"
""",
        encoding="utf-8",
    )

    assert read_pyproject_version(pyproject) == "1.2.3"


def test_read_cmake_project_version(tmp_path: Path) -> None:
    cmake = tmp_path / "CMakeLists.txt"
    cmake.write_text(
        "project(ajpegli VERSION 1.2.3 LANGUAGES C CXX)\n",
        encoding="utf-8",
    )

    assert read_cmake_project_version(cmake) == "1.2.3"


def test_check_static_versions_rejects_mismatch(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    cmake = tmp_path / "CMakeLists.txt"
    pyproject.write_text(
        """
[project]
name = "ajpegli"
version = "1.2.3"
""",
        encoding="utf-8",
    )
    cmake.write_text(
        "project(ajpegli VERSION 1.2.4 LANGUAGES C CXX)\n",
        encoding="utf-8",
    )

    with pytest.raises(VersionMismatchError, match=r"pyproject\.toml=1\.2\.3"):
        check_static_versions(pyproject, cmake)
