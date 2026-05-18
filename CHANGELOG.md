# Changelog

All notable user-facing changes are documented here.

The project follows semantic versioning for the Python API. The vendored jpegli
commit is part of each release note because jpegli itself is pinned by commit.

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
