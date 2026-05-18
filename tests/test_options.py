from __future__ import annotations

from typing import Any

import pytest
from ajpegli import DecodeOptions, EncodeOptions, InvalidInputError


@pytest.mark.parametrize(
    ("quality", "distance", "psnr"),
    [
        (90, 1.0, None),
        (90, None, 42.0),
        (None, 1.0, 42.0),
        (90, 1.0, 42.0),
    ],
)
def test_encode_options_reject_conflicting_quality_controls(
    quality: int | None,
    distance: float | None,
    psnr: float | None,
) -> None:
    with pytest.raises(
        InvalidInputError,
        match="quality, distance, and psnr are mutually exclusive",
    ):
        EncodeOptions(quality=quality, distance=distance, psnr=psnr)


@pytest.mark.parametrize(
    ("progressive", "expected"),
    [
        (False, 0),
        (True, 2),
        (0, 0),
        (1, 1),
        (2, 2),
        (3, 3),
    ],
)
def test_encode_options_normalize_progressive(progressive: object, expected: int) -> None:
    assert EncodeOptions(progressive=progressive).progressive == expected


def test_encode_options_allow_distance_when_quality_is_omitted() -> None:
    options = EncodeOptions(distance=1.0)

    assert options.quality is None
    assert options.distance == 1.0


@pytest.mark.parametrize("quality", [0, 101])
def test_encode_options_reject_invalid_quality(quality: int) -> None:
    with pytest.raises(InvalidInputError, match="quality must be between 1 and 100"):
        EncodeOptions(quality=quality)


@pytest.mark.parametrize("dtype", ["uint8", "uint16", "float32", "float16"])
def test_decode_options_accept_supported_dtypes(dtype: str) -> None:
    assert DecodeOptions(dtype=dtype).dtype == dtype


def test_decode_options_accept_bgr_mode() -> None:
    assert DecodeOptions(mode="BGR").mode == "BGR"


@pytest.mark.parametrize("max_pixels", [0, -1])
def test_decode_options_reject_invalid_max_pixels(max_pixels: int) -> None:
    with pytest.raises(InvalidInputError, match="max_pixels must be positive"):
        DecodeOptions(max_pixels=max_pixels)


def test_encode_options_reject_invalid_quality_type() -> None:
    with pytest.raises(InvalidInputError, match="quality must be an integer"):
        EncodeOptions(quality=object())


def test_encode_options_reject_invalid_progressive() -> None:
    with pytest.raises(InvalidInputError, match="progressive must be a bool"):
        EncodeOptions(progressive=4)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"subsampling": "411"}, "subsampling must be one of"),
        ({"mode": "RGBA"}, "mode must be one of"),
        ({"dtype": "int32"}, "dtype must be one of"),
        ({"alpha": "silent"}, "alpha must be one of"),
    ],
)
def test_encode_options_reject_invalid_choices(
    kwargs: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(InvalidInputError, match=message):
        EncodeOptions(**kwargs)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"mode": "RGBA"}, "mode must be one of"),
        ({"dtype": "int32"}, "dtype must be one of"),
        ({"endianness": "middle"}, "endianness must be one of"),
        ({"max_width": 0}, "max_width must be positive"),
        ({"max_height": 0}, "max_height must be positive"),
        ({"max_metadata_bytes": 0}, "max_metadata_bytes must be positive"),
    ],
)
def test_decode_options_reject_invalid_values(
    kwargs: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(InvalidInputError, match=message):
        DecodeOptions(**kwargs)
