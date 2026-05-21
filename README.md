# ajpegli

[![PyPI package](https://img.shields.io/pypi/v/ajpegli?label=pypi%20package)](https://pypi.org/project/ajpegli/)
[![CI](https://img.shields.io/github/actions/workflow/status/dKosarevsky/ajpegli/ci.yml?branch=main&label=CI&logo=github)](https://github.com/dKosarevsky/ajpegli/actions/workflows/ci.yml)
[![ruff](https://img.shields.io/github/actions/workflow/status/dKosarevsky/ajpegli/ruff.yml?branch=main&label=ruff)](https://github.com/dKosarevsky/ajpegli/actions/workflows/ruff.yml)
[![ty](https://img.shields.io/github/actions/workflow/status/dKosarevsky/ajpegli/ty.yml?branch=main&label=ty)](https://github.com/dKosarevsky/ajpegli/actions/workflows/ty.yml)
[![PyPI downloads](https://img.shields.io/pypi/dm/ajpegli?label=PyPI%20downloads)](https://pypistats.org/packages/ajpegli)
![Coverage](badges/coverage.svg)
[![License: BSD-3-Clause](https://img.shields.io/badge/license-BSD--3--Clause-blue.svg)](LICENSE)

Fast JPEG-to-NumPy image loading powered by Google jpegli.

`ajpegli` is a dependency-light JPEG loader for Python: pass a file path or
preloaded JPEG bytes, get a NumPy array. Decoding is powered by Google jpegli
and built for high-throughput data pipelines. The path API is `cv2.imread`-like,
but it is not a drop-in OpenCV replacement: color images are returned as RGB by
default. Pass `mode="BGR"` for OpenCV-style pipelines.

Current status: stable Python API. `imread()` and `imdecode()` are the primary
loading APIs, with `encode()` and `info()` available for production use in the
documented v1 scope. Benchmarks are published as measured regression baselines,
not as claims that `ajpegli` is faster than OpenCV or Pillow.

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

with open("image.jpg", "rb") as file:
    data = file.read()

rgb_from_memory = ajpegli.imdecode(data, mode="RGB")
bgr_from_memory = ajpegli.imdecode(data, mode="BGR")

jpeg = ajpegli.encode(rgb_from_memory, quality=90, progressive=2)
header = ajpegli.info(jpeg)
assert header.width == rgb_from_memory.shape[1]
```

`imread()` reads the file in the native extension and returns a NumPy array.
`imdecode()` accepts JPEG `bytes` or another bytes-like object and decodes from
memory with the same mode options. `decode()` is kept as an equivalent alias.
The v1 decode API supports `uint8` RGB, BGR, grayscale, CMYK, and native output
modes. File I/O and jpegli decode work release the GIL so threaded callers and
DataLoader workers do not serialize on Python while the native codec is
running.

## RAM / bytes decode

Use `imdecode()` when the benchmark or input pipeline has already loaded JPEG
bytes into memory:

```python
from pathlib import Path

import ajpegli

data = Path("image.jpg").read_bytes()
image = ajpegli.imdecode(data, mode="RGB")
```

`imdecode()` is the direct comparison point for `cv2.imdecode()`. It accepts
`bytes`, `bytearray`, `memoryview`, and contiguous NumPy `uint8` buffers without
making a Python-side copy before entering the native decoder.

NumPy is the only runtime dependency. OpenCV, Pillow, and PyTorch are optional
benchmark tools and are not required by `pip install ajpegli`.

## Encode and Info

`encode()` writes JPEG bytes from `uint8` NumPy arrays. The stable v1 encode
scope is grayscale (`HxW` or `HxWx1`) and RGB (`HxWx3`) input with explicit
alpha rejection unless `alpha="drop"` is passed. It supports quality,
distance/PSNR controls, progressive level, RGB subsampling, adaptive
quantization, and raw ICC/EXIF/XMP/comment marker writing. `info()` reads JPEG
headers without full image decode and returns `JpegInfo` dimensions, component
count, mode, progressive flag, subsampling, density, and ICC/EXIF/XMP presence.

Unsupported paths fail explicitly instead of silently changing data. `uint16`,
`float32`, `float16`, CMYK encode, XYB encode, and parsed EXIF metadata are
outside the v1 stable scope.

## Stability Contract

Starting with `1.0.0`, ajpegli follows SemVer for the documented Python API.
Function names, keyword names, default values, exception classes, and return
types documented in this README are stable across `1.x`. The private
`ajpegli._ajpegli` extension module is not public API.

The exact JPEG bitstream produced by `encode()` and benchmark throughput are
not part of the stability contract: both can change when the pinned jpegli
commit changes. Runtime dependencies stay limited to NumPy throughout `1.x`
unless a future major version changes that contract.

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
Use `--thread-workers` for threaded reader throughput and
`--dataloader-workers` for PyTorch `DataLoader` worker count. Use
`--source bytes` when benchmarking preloaded JPEG bytes from RAM instead of
path reads.
The checked-in reports are intentionally honest: on the current vendored smoke
corpora, OpenCV and Pillow are still faster than `ajpegli`. Treat them as
regression baselines and do not make project-level speed claims without broader
dataset-specific measurements.

For local comparison runs, install only what you want to measure in that
environment:

```bash
uv pip install opencv-python-headless pillow
uv pip install torch  # only for --include-dataloader
```
