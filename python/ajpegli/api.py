from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from . import _native
from .errors import DecodeError, InvalidInputError
from .metadata import JpegInfo
from .options import _QUALITY_UNSET, DecodeOptions, EncodeOptions

_GRAYSCALE_NDIM = 2
_CHANNEL_NDIM = 3
_ALPHA_CHANNELS = 4
_SUPPORTED_COLOR_CHANNELS = {1, 3}


def encode(
    image: Any,
    *,
    quality: object = _QUALITY_UNSET,
    distance: float | None = None,
    psnr: float | None = None,
    progressive: object = 2,
    subsampling: str = "420",
    mode: str | None = None,
    dtype: str | None = None,
    icc_profile: bytes | None = None,
    exif: bytes | None = None,
    xmp: bytes | None = None,
    comments: list[str] | None = None,
    optimize: bool = True,
    adaptive_quantization: bool = True,
    xyb: bool = False,
    allow_copy: bool = True,
    alpha: str = "error",
) -> bytes:
    options = EncodeOptions(
        quality=quality,
        distance=distance,
        psnr=psnr,
        progressive=progressive,
        subsampling=subsampling,
        mode=mode,
        dtype=dtype,
        adaptive_quantization=adaptive_quantization,
        xyb=xyb,
        allow_copy=allow_copy,
        alpha=alpha,
    )
    prepared = _prepare_image(image, options)
    return _native.encode(
        prepared,
        options=options,
        icc_profile=icc_profile,
        exif=exif,
        xmp=xmp,
        comments=comments,
        optimize=optimize,
    )


def decode(
    data: object,
    *,
    mode: str = "RGB",
    dtype: str = "uint8",
    max_pixels: int = 256_000_000,
    max_width: int = 65_535,
    max_height: int = 65_535,
    max_metadata_bytes: int = 64 * 1024 * 1024,
    return_metadata: bool = False,
    endianness: str = "native",
) -> NDArray[Any]:
    options = DecodeOptions(
        mode=mode,
        dtype=dtype,
        max_pixels=max_pixels,
        max_width=max_width,
        max_height=max_height,
        max_metadata_bytes=max_metadata_bytes,
        return_metadata=return_metadata,
        endianness=endianness,
    )
    return _native.decode(_as_bytes(data), options=options)


def info(data: object) -> JpegInfo:
    return _native.info(_as_bytes(data))


def _as_bytes(data: Any) -> bytes:
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    try:
        return memoryview(data).tobytes()
    except TypeError as exc:
        raise DecodeError("JPEG input must be bytes-like") from exc


def _prepare_image(image: Any, options: EncodeOptions) -> NDArray[Any]:
    if not isinstance(image, np.ndarray):
        raise InvalidInputError("image must be a numpy.ndarray")

    array = image
    if array.ndim not in {_GRAYSCALE_NDIM, _CHANNEL_NDIM}:
        raise InvalidInputError("expected image shape HxW, HxWx1, HxWx3, or HxWx4")

    if array.ndim == _CHANNEL_NDIM:
        channels = array.shape[2]
        if channels == _ALPHA_CHANNELS:
            if options.alpha == "error":
                raise InvalidInputError(
                    'JPEG does not support alpha. Pass alpha="drop" explicitly.'
                )
            array = array[..., :3]
        elif channels not in _SUPPORTED_COLOR_CHANNELS:
            raise InvalidInputError("expected image shape HxW, HxWx1, HxWx3, or HxWx4")

    if not array.flags.c_contiguous:
        if not options.allow_copy:
            raise InvalidInputError("non-contiguous arrays require allow_copy=True")
        array = np.ascontiguousarray(array)

    return array
