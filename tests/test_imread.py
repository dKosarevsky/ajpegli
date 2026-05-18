from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import ajpegli
import numpy as np
import pytest

SAMPLE_JPEG = Path("third_party/jpegli/testdata/jxl/jpeg_reconstruction/1x1_exif_xmp.jpg")


def test_imread_returns_numpy_array_from_path() -> None:
    image = ajpegli.imread(SAMPLE_JPEG)

    assert isinstance(image, np.ndarray)
    assert image.dtype == np.uint8
    assert image.shape == (1, 1, 3)


def test_imread_supports_grayscale_mode() -> None:
    image = ajpegli.imread(SAMPLE_JPEG, mode="L")

    assert image.dtype == np.uint8
    assert image.shape == (1, 1)


def test_decode_returns_numpy_array_from_bytes() -> None:
    image = ajpegli.decode(SAMPLE_JPEG.read_bytes())

    assert isinstance(image, np.ndarray)
    assert image.dtype == np.uint8
    assert image.shape == (1, 1, 3)


def test_imread_missing_file_raises_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        ajpegli.imread("missing.jpg")


def test_imread_is_safe_from_thread_pool() -> None:
    with ThreadPoolExecutor(max_workers=4) as executor:
        images = list(executor.map(ajpegli.imread, [SAMPLE_JPEG] * 8))

    assert all(image.shape == (1, 1, 3) for image in images)
    assert all(image.dtype == np.uint8 for image in images)
