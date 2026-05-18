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

Release and publishing instructions live in [releasing.md](docs/releasing.md).

## Installation

Install from PyPI:

```bash
pip install ajpegli
```

With uv:

```bash
uv add ajpegli
```

## Quickstart

ajpegli ships prebuilt wheels for common Linux, macOS, and Windows CPython
builds. NumPy is the only runtime dependency.

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

For local source builds, clone with submodules:

```bash
git clone --recursive https://github.com/dKosarevsky/ajpegli.git
cd ajpegli
uv sync --extra dev
just check
```

## Benchmarks

The benchmark script keeps comparison tools optional so `pip install ajpegli`
only needs NumPy at runtime. See [Benchmarks](docs/benchmarks.md),
[Benchmark Results](docs/benchmark-results.md),
[DataLoader Benchmarking](docs/dataloader.md), and
[DataLoader Results](docs/dataloader-results.md).

```bash
just bench-imread path/to/a.jpg 1000 8 RGB ajpegli,cv2,pillow
just bench-imread-dataloader path/to/a.jpg 1000 4 RGB 32
```

`benchmarks/bench_imread.py` reports JSON with sequential throughput, threaded
throughput, and optional PyTorch `DataLoader` throughput. Missing optional
comparison packages are reported as skipped entries instead of failing the run.
The checked-in smoke reports are intentionally narrow; broader dataset reports
are still required before making project-level speed claims against OpenCV or
Pillow.

For local comparison runs, install only what you want to measure in that
environment:

```bash
uv pip install opencv-python-headless pillow
uv pip install torch  # only for --include-dataloader
```
