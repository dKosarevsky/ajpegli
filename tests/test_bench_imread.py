from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from benchmarks.bench_imread import _bench_reader, _parse_codecs, _positive_int, _throughput_result


def test_parse_codecs_trims_and_rejects_empty_values() -> None:
    assert _parse_codecs("ajpegli, cv2,pillow") == ["ajpegli", "cv2", "pillow"]

    with pytest.raises(argparse.ArgumentTypeError):
        _parse_codecs("ajpegli,,cv2")


def test_bench_reader_cycles_paths_and_reports_throughput() -> None:
    paths = [Path("a.jpg"), Path("b.jpg")]
    calls: list[Path] = []
    ticks = iter([10.0, 10.0, 10.1, 10.1, 10.3, 10.3, 10.6, 10.6])

    def fake_reader(path: Path) -> tuple[int, ...]:
        calls.append(path)
        return (10, 20, 3)

    result = _bench_reader(fake_reader, paths, iterations=3, timer=lambda: next(ticks))

    assert calls == [Path("a.jpg"), Path("b.jpg"), Path("a.jpg")]
    assert result["images"] == 3
    assert result["seconds"] == pytest.approx(0.6)
    assert result["images_per_second"] == pytest.approx(5.0)
    assert result["megapixels_per_second"] == pytest.approx(0.001)
    assert result["p50_seconds"] == pytest.approx(0.2)
    assert result["p95_seconds"] == pytest.approx(0.29)
    assert result["last_shape"] == (10, 20, 3)


def test_throughput_result_reports_megapixels_for_grayscale_images() -> None:
    result = _throughput_result(10, 2.0, (100, 200))

    assert result["megapixels_per_second"] == pytest.approx(0.1)


def test_positive_int_rejects_non_positive_values() -> None:
    assert _positive_int("3") == 3

    with pytest.raises(argparse.ArgumentTypeError):
        _positive_int("0")
