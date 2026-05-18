# ajpegli

[![PyPI package](https://img.shields.io/pypi/v/ajpegli?label=pypi%20package)](https://pypi.org/project/ajpegli/)
[![CI](https://img.shields.io/github/actions/workflow/status/dKosarevsky/ajpegli/ci.yml?branch=main&label=CI&logo=github)](https://github.com/dKosarevsky/ajpegli/actions/workflows/ci.yml)
[![PyPI downloads](https://img.shields.io/pypi/dm/ajpegli?label=PyPI%20downloads)](https://pypistats.org/packages/ajpegli)
![Coverage](badges/coverage.svg)
[![License: BSD-3-Clause](https://img.shields.io/badge/license-BSD--3--Clause-blue.svg)](LICENSE)

Fast JPEG-to-NumPy image loading powered by Google jpegli.

`ajpegli` is a dependency-light JPEG loader for Python: pass a file path, get a
NumPy array. Decoding is powered by Google jpegli and built for high-throughput
data pipelines. The API is `cv2.imread`-like, but it is not a drop-in OpenCV
replacement: color images are returned as RGB by default. Pass `mode="BGR"` for
OpenCV-style pipelines.

## Development

Clone with submodules before building native wheels:

```bash
git submodule update --init --recursive
uv sync --extra dev
just check
just build
just bench-imread
```

`third_party/jpegli` is pinned as a submodule. The pinned commit is exposed at
runtime through `ajpegli.__jpegli_commit__` and `ajpegli.jpegli_commit()`.

## Quickstart

```python
import ajpegli

image = ajpegli.imread("image.jpg")
assert image.dtype == "uint8"
assert image.ndim == 3

rgb = ajpegli.imread("image.jpg", mode="RGB")  # default
bgr = ajpegli.imread("image.jpg", mode="BGR")  # for OpenCV-style pipelines
gray = ajpegli.imread("image.jpg", mode="L")
```

`imread()` reads the file in the native extension and returns a NumPy array.
The first decode slice supports `uint8` RGB, BGR, and grayscale output. File I/O
and jpegli decode work release the GIL so threaded callers and DataLoader
workers do not serialize on Python while the native codec is running.

NumPy is the only runtime dependency. OpenCV, Pillow, and PyTorch are optional
benchmark tools and are not required by `pip install ajpegli`.

`encode()` and full `info()` metadata output are still planned API surface, not
the release focus yet.

## Benchmarks

The benchmark script keeps comparison tools optional so `pip install ajpegli`
only needs NumPy at runtime.

```bash
just bench-imread path/to/a.jpg 1000 8 RGB ajpegli,cv2,pillow
just bench-imread-dataloader path/to/a.jpg 1000 4 RGB 32
```

`benchmarks/bench_imread.py` reports JSON with sequential throughput, threaded
throughput, and optional PyTorch `DataLoader` throughput. Missing optional
comparison packages are reported as skipped entries instead of failing the run.
Published benchmark and DataLoader scaling reports are planned before making
project-level speed claims against OpenCV or Pillow.

For local comparison runs, install only what you want to measure in that
environment:

```bash
uv pip install opencv-python-headless pillow
uv pip install torch  # only for --include-dataloader
```

## Wheels and publishing

Wheel builds run through cibuildwheel. Pull requests smoke-test the Linux
x86_64 wheel path; tag and manual runs build the full release matrix:

- manylinux x86_64
- manylinux aarch64
- macOS x86_64
- macOS arm64
- Windows x64

To publish from GitHub Actions, configure PyPI Trusted Publishing for this
repository first:

1. On TestPyPI, create or claim the `ajpegli` project and add a trusted
   publisher for repository `dKosarevsky/ajpegli`, workflow
   `.github/workflows/wheels.yml`, environment `testpypi`.
2. In GitHub repository settings, create a `testpypi` environment.
3. Run the `Wheels` workflow manually with `publish=testpypi`.
4. On PyPI, add the same trusted publisher with environment `pypi`.
5. In GitHub repository settings, create a protected `pypi` environment.
6. Publish a real release by pushing a `v*` tag, or run the `Wheels` workflow
   manually with `publish=pypi`.

No long-lived PyPI token is required for that flow.
