from __future__ import annotations

import importlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import ajpegli
import numpy as np
import pytest

SAMPLE_JPEG = Path("third_party/jpegli/testdata/jxl/jpeg_reconstruction/1x1_exif_xmp.jpg")
COLOR_JPEG = Path("third_party/jpegli/testdata/jxl/jpeg_reconstruction/sideways_bench.jpg")


def test_imread_returns_numpy_array_from_path() -> None:
    image = ajpegli.imread(SAMPLE_JPEG)

    assert isinstance(image, np.ndarray)
    assert image.dtype == np.uint8
    assert image.shape == (1, 1, 3)


def test_internal_stdio_imread_matches_default_path_reader() -> None:
    native = importlib.import_module("ajpegli._ajpegli")
    default = ajpegli.imread(COLOR_JPEG, mode="RGB")
    stdio = native.imread_stdio(
        str(COLOR_JPEG),
        mode="RGB",
        dtype="uint8",
        max_pixels=256_000_000,
        max_width=65_535,
        max_height=65_535,
        endianness="native",
    )

    np.testing.assert_array_equal(stdio, default)


def test_imread_supports_grayscale_mode() -> None:
    image = ajpegli.imread(SAMPLE_JPEG, mode="L")

    assert image.dtype == np.uint8
    assert image.shape == (1, 1)


def test_imread_supports_bgr_mode_without_python_channel_swap() -> None:
    rgb = ajpegli.imread(COLOR_JPEG, mode="RGB")
    bgr = ajpegli.imread(COLOR_JPEG, mode="BGR")
    row = rgb.shape[0] // 2
    col = rgb.shape[1] // 2

    assert rgb[row, col].tolist() == [38, 206, 51]
    assert bgr[row, col].tolist() == [51, 206, 38]
    assert bgr.flags.c_contiguous


def test_decode_returns_numpy_array_from_bytes() -> None:
    image = ajpegli.decode(SAMPLE_JPEG.read_bytes())

    assert isinstance(image, np.ndarray)
    assert image.dtype == np.uint8
    assert image.shape == (1, 1, 3)


@pytest.mark.parametrize(
    "factory",
    [
        pytest.param(bytearray, id="bytearray"),
        pytest.param(memoryview, id="memoryview"),
        pytest.param(lambda data: np.frombuffer(data, dtype=np.uint8), id="ndarray"),
    ],
)
def test_decode_accepts_bytes_like_buffers(factory) -> None:
    image = ajpegli.decode(factory(SAMPLE_JPEG.read_bytes()))

    assert isinstance(image, np.ndarray)
    assert image.dtype == np.uint8
    assert image.shape == (1, 1, 3)
    assert image.flags.c_contiguous


@pytest.mark.parametrize(
    ("mode", "expected_shape"),
    [
        ("BGR", (243, 201, 3)),
        ("L", (243, 201)),
    ],
)
def test_decode_bytes_supports_bgr_and_grayscale_modes(
    mode: str,
    expected_shape: tuple[int, ...],
) -> None:
    image = ajpegli.decode(COLOR_JPEG.read_bytes(), mode=mode)

    assert image.dtype == np.uint8
    assert image.shape == expected_shape
    assert image.flags.c_contiguous


def test_imread_missing_file_raises_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        ajpegli.imread("missing.jpg")


def test_imread_empty_file_raises_decode_error(tmp_path: Path) -> None:
    empty_jpeg = tmp_path / "empty.jpg"
    empty_jpeg.write_bytes(b"")

    with pytest.raises(ajpegli.DecodeError, match="jpegli decode failed"):
        ajpegli.imread(empty_jpeg)


def test_imread_respects_max_pixels_before_allocation() -> None:
    with pytest.raises(ajpegli.DecodeError, match="max_pixels"):
        ajpegli.imread(COLOR_JPEG, max_pixels=1)


def test_imread_is_safe_from_thread_pool() -> None:
    with ThreadPoolExecutor(max_workers=4) as executor:
        images = list(executor.map(ajpegli.imread, [SAMPLE_JPEG, COLOR_JPEG] * 4))

    assert images[0].shape == (1, 1, 3)
    assert images[1].shape == (243, 201, 3)
    assert all(image.dtype == np.uint8 for image in images)
