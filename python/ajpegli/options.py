from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .errors import InvalidInputError

_QUALITY_UNSET = object()
_DEFAULT_QUALITY = 90
_MIN_QUALITY = 1
_MAX_QUALITY = 100
_DEFAULT_PROGRESSIVE_LEVEL = 2
_MAX_PROGRESSIVE_LEVEL = 3
_SUBSAMPLING_VALUES = {"444", "422", "420", "440", "gray"}
_ENCODE_MODE_VALUES = {"RGB", "L", "CMYK"}
_DTYPE_VALUES = {"uint8", "uint16", "float32", "float16"}
_DECODE_MODE_VALUES = {"RGB", "BGR", "L", "CMYK", "native"}
_ENDIANNESS_VALUES = {"native", "little", "big"}

EncodeMode = Literal["RGB", "L", "CMYK"]
EncodeDtype = Literal["uint8", "uint16", "float32", "float16"]
Subsampling = Literal["444", "422", "420", "440", "gray"]
AlphaPolicy = Literal["error", "drop"]
DecodeMode = Literal["RGB", "BGR", "L", "CMYK", "native"]
DecodeDtype = Literal["uint8", "uint16", "float32", "float16"]
Endianness = Literal["native", "little", "big"]


@dataclass(frozen=True, init=False)
class EncodeOptions:
    quality: int | None
    distance: float | None
    psnr: float | None
    progressive: int
    subsampling: str
    mode: str | None
    dtype: str | None
    adaptive_quantization: bool
    xyb: bool
    allow_copy: bool
    alpha: str

    def __init__(
        self,
        quality: object = _QUALITY_UNSET,
        distance: float | None = None,
        psnr: float | None = None,
        progressive: object = 2,
        subsampling: str = "420",
        mode: str | None = None,
        dtype: str | None = None,
        adaptive_quantization: bool = True,
        xyb: bool = False,
        allow_copy: bool = True,
        alpha: str = "error",
    ) -> None:
        resolved_quality = _resolve_quality(quality, distance, psnr)
        _validate_quality_controls(resolved_quality, distance, psnr, quality is not _QUALITY_UNSET)
        object.__setattr__(self, "quality", resolved_quality)
        object.__setattr__(self, "distance", distance)
        object.__setattr__(self, "psnr", psnr)
        object.__setattr__(self, "progressive", _normalize_progressive(progressive))
        object.__setattr__(
            self,
            "subsampling",
            _validate_choice(subsampling, _SUBSAMPLING_VALUES, "subsampling"),
        )
        object.__setattr__(
            self,
            "mode",
            _validate_optional_choice(mode, _ENCODE_MODE_VALUES, "mode"),
        )
        object.__setattr__(
            self,
            "dtype",
            _validate_optional_choice(dtype, _DTYPE_VALUES, "dtype"),
        )
        object.__setattr__(self, "adaptive_quantization", bool(adaptive_quantization))
        object.__setattr__(self, "xyb", bool(xyb))
        object.__setattr__(self, "allow_copy", bool(allow_copy))
        object.__setattr__(self, "alpha", _validate_choice(alpha, {"error", "drop"}, "alpha"))


@dataclass(frozen=True)
class DecodeOptions:
    mode: str = "RGB"
    dtype: str = "uint8"
    max_pixels: int = 256_000_000
    max_width: int = 65_535
    max_height: int = 65_535
    max_metadata_bytes: int = 64 * 1024 * 1024
    return_metadata: bool = False
    endianness: str = "native"

    def __post_init__(self) -> None:
        _validate_choice(self.mode, _DECODE_MODE_VALUES, "mode")
        _validate_choice(self.dtype, _DTYPE_VALUES, "dtype")
        _validate_choice(self.endianness, _ENDIANNESS_VALUES, "endianness")
        for name in ("max_pixels", "max_width", "max_height", "max_metadata_bytes"):
            if getattr(self, name) <= 0:
                raise InvalidInputError(f"{name} must be positive")


def _resolve_quality(
    quality: object,
    distance: float | None,
    psnr: float | None,
) -> int | None:
    if quality is _QUALITY_UNSET:
        return _DEFAULT_QUALITY if distance is None and psnr is None else None
    if quality is None:
        return None
    if not isinstance(quality, int):
        raise InvalidInputError("quality must be an integer between 1 and 100")
    if not _MIN_QUALITY <= quality <= _MAX_QUALITY:
        raise InvalidInputError("quality must be between 1 and 100")
    return quality


def _validate_quality_controls(
    quality: int | None,
    distance: float | None,
    psnr: float | None,
    explicit_quality: bool,
) -> None:
    controls = [
        explicit_quality and quality is not None,
        distance is not None,
        psnr is not None,
    ]
    if sum(controls) > 1:
        raise InvalidInputError("quality, distance, and psnr are mutually exclusive")


def _normalize_progressive(progressive: object) -> int:
    if isinstance(progressive, bool):
        return _DEFAULT_PROGRESSIVE_LEVEL if progressive else 0
    if not isinstance(progressive, int) or not 0 <= progressive <= _MAX_PROGRESSIVE_LEVEL:
        raise InvalidInputError("progressive must be a bool or an integer from 0 to 3")
    return progressive


def _validate_choice(value: str, allowed: set[str], name: str) -> str:
    if value not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise InvalidInputError(f"{name} must be one of: {allowed_values}")
    return value


def _validate_optional_choice(value: str | None, allowed: set[str], name: str) -> str | None:
    if value is None:
        return None
    return _validate_choice(value, allowed, name)
