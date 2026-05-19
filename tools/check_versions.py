from __future__ import annotations

import argparse
import re
import sys
from importlib import metadata
from pathlib import Path

import ajpegli._native as native

PROJECT_SECTION = "[project]"
SECTION_PREFIX = "["
CMAKE_PROJECT_VERSION_PATTERN = re.compile(
    r"project\s*\(\s*ajpegli\s+VERSION\s+([0-9]+(?:\.[0-9]+)*(?:[A-Za-z0-9.+-]*)?)",
    re.IGNORECASE,
)
PYPROJECT_VERSION_PATTERN = re.compile(r'^version\s*=\s*"([^"]+)"\s*$')


class VersionMismatchError(RuntimeError):
    pass


def read_pyproject_version(path: Path) -> str:
    in_project_section = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == PROJECT_SECTION:
            in_project_section = True
            continue
        if in_project_section and line.startswith(SECTION_PREFIX):
            break
        if in_project_section:
            match = PYPROJECT_VERSION_PATTERN.match(line)
            if match is not None:
                return match.group(1)
    raise VersionMismatchError(f"unable to find [project].version in {path}")


def read_cmake_project_version(path: Path) -> str:
    match = CMAKE_PROJECT_VERSION_PATTERN.search(path.read_text(encoding="utf-8"))
    if match is None:
        raise VersionMismatchError(f"unable to find project(ajpegli VERSION ...) in {path}")
    return match.group(1)


def check_static_versions(pyproject: Path, cmake: Path) -> str:
    pyproject_version = read_pyproject_version(pyproject)
    cmake_version = read_cmake_project_version(cmake)
    if pyproject_version != cmake_version:
        raise VersionMismatchError(
            "version mismatch: "
            f"pyproject.toml={pyproject_version}, CMakeLists.txt={cmake_version}",
        )
    return pyproject_version


def check_runtime_versions(expected_version: str) -> None:
    installed_version = metadata.version("ajpegli")
    if installed_version != expected_version:
        raise VersionMismatchError(
            "version mismatch: "
            f"pyproject.toml={expected_version}, installed package={installed_version}",
        )

    native_version = native.native_version()
    if native_version != expected_version:
        raise VersionMismatchError(
            "version mismatch: "
            f"pyproject.toml={expected_version}, native extension={native_version}",
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check ajpegli version consistency.")
    parser.add_argument("--pyproject", type=Path, default=Path("pyproject.toml"))
    parser.add_argument("--cmake", type=Path, default=Path("CMakeLists.txt"))
    parser.add_argument("--skip-runtime", action="store_true")
    args = parser.parse_args(argv)

    try:
        expected_version = check_static_versions(args.pyproject, args.cmake)
        if not args.skip_runtime:
            check_runtime_versions(expected_version)
    except VersionMismatchError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
