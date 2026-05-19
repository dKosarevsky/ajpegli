# Changelog

All notable user-facing changes are documented here.

The project follows semantic versioning for the Python API. The vendored jpegli
commit is part of each release note because jpegli itself is pinned by commit.

## 0.1.4 - Unreleased

- Added version consistency checks for Python package metadata, CMake
  `PROJECT_VERSION`, and the native extension version.
- Added explicit `--thread-workers` benchmark CLI naming while keeping
  `--workers` as a compatibility alias.
- Added an internal `ajpegli-stdio` benchmark codec for comparing
  `jpegli_stdio_src` with the public `jpegli_mem_src` path.

Vendored jpegli commit: `7cdf212790241868c77dca777dbee14e98128cba`.

## 0.1.3 - 2026-05-19

- Published README installation polish and benchmark documentation updates.
- Published reproducible smoke benchmark and DataLoader baseline reports.

Vendored jpegli commit: `7cdf212790241868c77dca777dbee14e98128cba`.

## 0.1.0 - 2026-05-18

Initial alpha release focused on fast JPEG-to-NumPy loading.

- Added `ajpegli.imread(path) -> numpy.ndarray`.
- Added `ajpegli.decode(bytes) -> numpy.ndarray`.
- Added `RGB`, `BGR`, and `L` output modes for `uint8` images.
- Added native jpegli decode through the `_ajpegli` extension.
- Added GIL release around file I/O and jpegli decode work.
- Added prebuilt wheels for CPython 3.9-3.13 on manylinux x86_64/aarch64,
  macOS x86_64/arm64, and Windows x64.
- Added CI coverage badge generation, NumPy compatibility checks, and wheel
  smoke tests.

Vendored jpegli commit: `7cdf212790241868c77dca777dbee14e98128cba`.
