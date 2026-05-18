# ajpegli

Production-ready Python bindings for Google jpegli.

This repository is being bootstrapped as a native Python package with a stable
Python facade, a C++/pybind11 extension boundary, NumPy-first APIs, strict
validation, and reproducible build tooling.

The first implementation slice establishes packaging, tests, and public API
contracts. Full jpegli encode/decode support is intentionally staged behind the
native extension boundary.

