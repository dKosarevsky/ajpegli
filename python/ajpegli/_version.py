from __future__ import annotations

from . import _native

__version__ = "0.1.0"
__jpegli_commit__ = _native.jpegli_commit()


def jpegli_commit() -> str:
    return _native.jpegli_commit()


def features() -> dict[str, bool]:
    return _native.features()

