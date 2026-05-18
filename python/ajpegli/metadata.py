from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from numpy.typing import NDArray

from .errors import InvalidInputError

_MAX_MARKER_CODE = 0xFF


@dataclass(frozen=True)
class Marker:
    code: int
    data: bytes

    def __post_init__(self) -> None:
        if not 0 <= self.code <= _MAX_MARKER_CODE:
            raise InvalidInputError("marker code must fit in one byte")
        if not isinstance(self.data, bytes):
            raise InvalidInputError("marker data must be bytes")


@dataclass(frozen=True)
class Metadata:
    icc_profile: bytes | None = None
    exif: bytes | None = None
    xmp: bytes | None = None
    comments: tuple[str, ...] = field(default_factory=tuple)
    markers: tuple[Marker, ...] = field(default_factory=tuple)

    def __init__(
        self,
        icc_profile: bytes | None = None,
        exif: bytes | None = None,
        xmp: bytes | None = None,
        comments: Sequence[str] = (),
        markers: Sequence[Marker] = (),
    ) -> None:
        object.__setattr__(self, "icc_profile", icc_profile)
        object.__setattr__(self, "exif", exif)
        object.__setattr__(self, "xmp", xmp)
        object.__setattr__(self, "comments", tuple(comments))
        object.__setattr__(self, "markers", tuple(markers))


@dataclass(frozen=True)
class DecodedImage:
    image: NDArray[Any]
    metadata: Metadata


@dataclass(frozen=True)
class JpegInfo:
    width: int
    height: int
    components: int
    mode: str
    progressive: bool
    subsampling: str | None
    density: tuple[int, int] | None
    has_icc_profile: bool
    has_exif: bool
    has_xmp: bool

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise InvalidInputError("JPEG dimensions must be positive")
        if self.components <= 0:
            raise InvalidInputError("JPEG components must be positive")
