from __future__ import annotations

from ._version import __jpegli_commit__, __version__, features, jpegli_commit
from .api import decode, encode, info
from .errors import (
    AjpegliError,
    DecodeError,
    EncodeError,
    InvalidInputError,
    MetadataError,
    SecurityError,
    UnsupportedModeError,
)
from .metadata import DecodedImage, JpegInfo, Marker, Metadata
from .options import DecodeOptions, EncodeOptions

__all__ = [
    "AjpegliError",
    "DecodeError",
    "DecodeOptions",
    "DecodedImage",
    "EncodeError",
    "EncodeOptions",
    "InvalidInputError",
    "JpegInfo",
    "Marker",
    "Metadata",
    "MetadataError",
    "SecurityError",
    "UnsupportedModeError",
    "__jpegli_commit__",
    "__version__",
    "decode",
    "encode",
    "features",
    "info",
    "jpegli_commit",
]

