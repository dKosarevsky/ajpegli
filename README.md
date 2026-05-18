# ajpegli

[![CI](https://github.com/dKosarevsky/ajpegli/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/dKosarevsky/ajpegli/actions/workflows/ci.yml)
![Coverage](badges/coverage.svg)
[![License: BSD-3-Clause](https://img.shields.io/badge/license-BSD--3--Clause-blue.svg)](LICENSE)

Fast JPEG-to-NumPy image loading powered by Google jpegli.

`ajpegli` is a dependency-light JPEG loader for Python: pass a file path, get a
NumPy array. Decoding is powered by Google jpegli and built for high-throughput
data pipelines.

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

bgr = ajpegli.imread("image.jpg", mode="BGR")  # for OpenCV-style pipelines
gray = ajpegli.imread("image.jpg", mode="L")
```

`imread()` reads the file in the native extension and returns a NumPy array.
The first decode slice supports `uint8` RGB, BGR, and grayscale output. File I/O
and jpegli decode work release the GIL so threaded callers and DataLoader
workers do not serialize on Python while the native codec is running.

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

For local comparison runs, install only what you want to measure in that
environment:

```bash
uv pip install opencv-python-headless pillow
uv pip install torch  # only for --include-dataloader
```
