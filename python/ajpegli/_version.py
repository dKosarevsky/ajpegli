from __future__ import annotations

from importlib.metadata import version

from . import _native

__version__ = version("ajpegli")
__jpegli_commit__ = _native.jpegli_commit()


def jpegli_commit() -> str:
    return _native.jpegli_commit()


def features() -> dict[str, bool]:
    return _native.features()

