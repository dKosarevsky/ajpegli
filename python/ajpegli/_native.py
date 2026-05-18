from __future__ import annotations

import importlib
from collections.abc import Mapping
from typing import Any

from .errors import DecodeError, EncodeError

_FEATURES = {
    "uint16": False,
    "float32": False,
    "float16": False,
    "icc": False,
    "exif": False,
    "xyb": False,
    "progressive": False,
}

try:
    _ext: Any | None = importlib.import_module("._ajpegli", __package__)
except ImportError:  # pragma: no cover - exercised only from an unbuilt source tree.
    _ext = None  # pragma: no cover


def native_available() -> bool:
    return _ext is not None


def jpegli_commit() -> str:
    if _ext is None:
        return "unvendored"
    return str(_ext.jpegli_commit())


def features() -> dict[str, bool]:
    if _ext is None:
        return dict(_FEATURES)
    raw_features: Mapping[str, Any] = _ext.features()
    return {name: bool(raw_features.get(name, False)) for name in _FEATURES}


def encode(*_args: Any, **_kwargs: Any) -> bytes:
    raise EncodeError("native jpegli extension is not available")


def decode(*_args: Any, **_kwargs: Any) -> Any:
    raise DecodeError("native jpegli extension is not available")


def info(*_args: Any, **_kwargs: Any) -> Any:
    raise DecodeError("native jpegli extension is not available")
