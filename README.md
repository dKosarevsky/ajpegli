# ajpegli

Production-ready Python bindings for Google jpegli.

This repository is being bootstrapped as a native Python package with a stable
Python facade, a C++/pybind11 extension boundary, NumPy-first APIs, strict
validation, and reproducible build tooling.

The first implementation slice establishes packaging, tests, and public API
contracts. Full jpegli encode/decode support is intentionally staged behind the
native extension boundary.

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
```

`imread()` reads the file in the native extension and returns a NumPy array.
The first decode slice supports `uint8` RGB and grayscale output. File I/O and
jpegli decode work release the GIL so threaded callers and DataLoader workers do
not serialize on Python while the native codec is running.
