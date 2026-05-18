from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray


@pytest.fixture
def rgb_uint8() -> NDArray[np.uint8]:
    image = np.zeros((4, 5, 3), dtype=np.uint8)
    image[..., 0] = 32
    image[..., 1] = 64
    image[..., 2] = 128
    return image


@pytest.fixture
def rgba_uint8(rgb_uint8: NDArray[np.uint8]) -> NDArray[np.uint8]:
    alpha = np.full((*rgb_uint8.shape[:2], 1), 255, dtype=np.uint8)
    return np.concatenate([rgb_uint8, alpha], axis=2)


@pytest.fixture(params=[b"", b"not a jpeg"])
def invalid_jpeg_bytes(request: pytest.FixtureRequest) -> bytes:
    return request.param


