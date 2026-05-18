from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import ajpegli
import numpy as np
import pytest

FLOWER_DIR = Path("third_party/jpegli/testdata/jxl/flower")
RECONSTRUCTION_DIR = Path("third_party/jpegli/testdata/jxl/jpeg_reconstruction")

BASELINE_JPEG = FLOWER_DIR / "flower.png.im_q85_420.jpg"
PROGRESSIVE_JPEG = FLOWER_DIR / "flower.png.im_q85_420_progr.jpg"
GRAYSCALE_JPEG = FLOWER_DIR / "flower.png.im_q85_gray.jpg"
CMYK_JPEG = FLOWER_DIR / "flower_small.cmyk.jpg"
NON_INTERLEAVED_JPEG = FLOWER_DIR / "flower_small.q85_420_non_interleaved.jpg"
RESTART_MARKER_JPEG = RECONSTRUCTION_DIR / "bicycles_restarts.jpg"
SMALL_JPEG = RECONSTRUCTION_DIR / "1x1_exif_xmp.jpg"


def _read_shape_from_process(args: tuple[str, str]) -> tuple[tuple[int, ...], str, bool]:
    path, mode = args
    image = ajpegli.imread(path, mode=mode)
    return tuple(image.shape), str(image.dtype), bool(image.flags.c_contiguous)


@pytest.mark.parametrize(
    ("path", "mode", "shape"),
    [
        pytest.param(BASELINE_JPEG, "RGB", (1512, 2268, 3), id="baseline-rgb"),
        pytest.param(PROGRESSIVE_JPEG, "RGB", (1512, 2268, 3), id="progressive-rgb"),
        pytest.param(GRAYSCALE_JPEG, "L", (1512, 2268), id="grayscale-l"),
        pytest.param(CMYK_JPEG, "CMYK", (532, 510, 4), id="cmyk"),
        pytest.param(NON_INTERLEAVED_JPEG, "RGB", (532, 510, 3), id="non-interleaved"),
        pytest.param(RESTART_MARKER_JPEG, "RGB", (631, 1024, 3), id="restart-markers"),
    ],
)
def test_imread_decodes_representative_jpeg_corpus(
    path: Path,
    mode: str,
    shape: tuple[int, ...],
) -> None:
    image = ajpegli.imread(path, mode=mode)

    assert isinstance(image, np.ndarray)
    assert image.dtype == np.uint8
    assert image.shape == shape
    assert image.flags.c_contiguous


def test_imread_accepts_unicode_paths(tmp_path: Path) -> None:
    unicode_jpeg = tmp_path / "тестовая-картинка.jpg"
    unicode_jpeg.write_bytes(SMALL_JPEG.read_bytes())

    image = ajpegli.imread(unicode_jpeg)

    assert image.shape == (1, 1, 3)
    assert image.dtype == np.uint8


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        pytest.param("truncated.jpg", BASELINE_JPEG.read_bytes()[:128], id="truncated"),
        pytest.param("corrupt-marker.jpg", b"not a jpeg", id="corrupt-marker"),
    ],
)
def test_imread_rejects_malformed_corpus_inputs(
    tmp_path: Path,
    name: str,
    payload: bytes,
) -> None:
    malformed_jpeg = tmp_path / name
    malformed_jpeg.write_bytes(payload)

    with pytest.raises(ajpegli.DecodeError, match="jpegli decode failed"):
        ajpegli.imread(malformed_jpeg)


def test_imread_is_safe_from_process_pool() -> None:
    jobs = [
        (str(SMALL_JPEG), "RGB"),
        (str(CMYK_JPEG), "CMYK"),
        (str(NON_INTERLEAVED_JPEG), "RGB"),
    ]

    with ProcessPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(_read_shape_from_process, jobs))

    assert results == [
        ((1, 1, 3), "uint8", True),
        ((532, 510, 4), "uint8", True),
        ((532, 510, 3), "uint8", True),
    ]
