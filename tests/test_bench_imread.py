from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from benchmarks.bench_imread import _bench_reader, _parse_codecs, _positive_int


def test_parse_codecs_trims_and_rejects_empty_values() -> None:
    assert _parse_codecs("ajpegli, cv2,pillow") == ["ajpegli", "cv2", "pillow"]

    with pytest.raises(argparse.ArgumentTypeError):
        _parse_codecs("ajpegli,,cv2")


def test_bench_reader_cycles_paths_and_reports_throughput() -> None:
    paths = [Path("a.jpg"), Path("b.jpg")]
    calls: list[Path] = []
    ticks = iter([10.0, 12.0])

    def fake_reader(path: Path) -> tuple[int, ...]:
        calls.append(path)
        return (10, 20, 3)

    result = _bench_reader(fake_reader, paths, iterations=3, timer=lambda: next(ticks))

    assert calls == [Path("a.jpg"), Path("b.jpg"), Path("a.jpg")]
    assert result["images"] == 3
    assert result["seconds"] == 2.0
    assert result["images_per_second"] == 1.5
    assert result["last_shape"] == (10, 20, 3)


def test_positive_int_rejects_non_positive_values() -> None:
    assert _positive_int("3") == 3

    with pytest.raises(argparse.ArgumentTypeError):
        _positive_int("0")
