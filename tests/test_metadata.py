from __future__ import annotations

from typing import Any

import ajpegli
import pytest


def test_metadata_defaults_are_immutable_tuples() -> None:
    metadata = ajpegli.Metadata()

    assert metadata.icc_profile is None
    assert metadata.exif is None
    assert metadata.xmp is None
    assert metadata.comments == ()
    assert metadata.markers == ()


def test_marker_validates_code_range() -> None:
    marker = ajpegli.Marker(code=0xE1, data=b"payload")

    assert marker.code == 0xE1
    assert marker.data == b"payload"


def test_marker_rejects_invalid_code() -> None:
    with pytest.raises(ajpegli.InvalidInputError, match="marker code"):
        ajpegli.Marker(code=0x100, data=b"payload")


def test_marker_rejects_non_bytes_data() -> None:
    data: Any = "payload"
    with pytest.raises(ajpegli.InvalidInputError, match="marker data"):
        ajpegli.Marker(code=0xE1, data=data)


def test_metadata_normalizes_sequences() -> None:
    marker = ajpegli.Marker(code=0xFE, data=b"comment")
    metadata = ajpegli.Metadata(comments=["a", "b"], markers=[marker])

    assert metadata.comments == ("a", "b")
    assert metadata.markers == (marker,)


def test_decoded_image_groups_array_and_metadata(rgb_uint8) -> None:
    metadata = ajpegli.Metadata(comments=["ok"])
    decoded = ajpegli.DecodedImage(image=rgb_uint8, metadata=metadata)

    assert decoded.image is rgb_uint8
    assert decoded.metadata is metadata


def test_jpeg_info_exposes_header_fields() -> None:
    info = ajpegli.JpegInfo(
        width=4,
        height=5,
        components=3,
        mode="RGB",
        progressive=False,
        subsampling="420",
        density=(72, 72),
        has_icc_profile=False,
        has_exif=True,
        has_xmp=False,
    )

    assert info.width == 4
    assert info.height == 5
    assert info.mode == "RGB"
    assert info.has_exif is True


def test_jpeg_info_rejects_invalid_dimensions() -> None:
    with pytest.raises(ajpegli.InvalidInputError, match="dimensions"):
        ajpegli.JpegInfo(
            width=0,
            height=1,
            components=3,
            mode="RGB",
            progressive=False,
            subsampling=None,
            density=None,
            has_icc_profile=False,
            has_exif=False,
            has_xmp=False,
        )


def test_jpeg_info_rejects_invalid_components() -> None:
    with pytest.raises(ajpegli.InvalidInputError, match="components"):
        ajpegli.JpegInfo(
            width=1,
            height=1,
            components=0,
            mode="RGB",
            progressive=False,
            subsampling=None,
            density=None,
            has_icc_profile=False,
            has_exif=False,
            has_xmp=False,
        )
