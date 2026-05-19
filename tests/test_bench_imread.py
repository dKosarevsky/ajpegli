from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from benchmarks.bench_imread import (
    DecodeSample,
    _bench_reader,
    _non_negative_int,
    _parse_args,
    _parse_codecs,
    _path_samples,
    _positive_int,
    _preload_samples,
    _resolve_codecs,
    _throughput_result,
)


def test_parse_codecs_trims_and_rejects_empty_values() -> None:
    assert _parse_codecs("ajpegli, ajpegli-stdio, cv2,pillow") == [
        "ajpegli",
        "ajpegli-stdio",
        "cv2",
        "pillow",
    ]

    with pytest.raises(argparse.ArgumentTypeError):
        _parse_codecs("ajpegli,,cv2")


def test_bench_reader_cycles_paths_and_reports_throughput() -> None:
    samples = [
        DecodeSample(path=Path("a.jpg"), data=b"a"),
        DecodeSample(path=Path("b.jpg"), data=b"b"),
    ]
    calls: list[DecodeSample] = []
    ticks = iter([10.0, 10.0, 10.1, 10.1, 10.3, 10.3, 10.6, 10.6])

    def fake_reader(sample: DecodeSample) -> tuple[int, ...]:
        calls.append(sample)
        return (10, 20, 3)

    result = _bench_reader(fake_reader, samples, iterations=3, timer=lambda: next(ticks))

    assert calls == [samples[0], samples[1], samples[0]]
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


def test_non_negative_int_accepts_zero_for_dataloader_workers() -> None:
    assert _non_negative_int("0") == 0
    assert _non_negative_int("3") == 3

    with pytest.raises(argparse.ArgumentTypeError):
        _non_negative_int("-1")


def test_parse_args_accepts_explicit_thread_workers() -> None:
    args = _parse_args(["image.jpg", "--thread-workers", "7"])

    assert args.thread_workers == 7


def test_parse_args_keeps_workers_as_thread_workers_alias() -> None:
    args = _parse_args(["image.jpg", "--workers", "5"])

    assert args.thread_workers == 5


def test_parse_args_accepts_bytes_source() -> None:
    args = _parse_args(["image.jpg", "--source", "bytes"])

    assert args.source == "bytes"


def test_preload_samples_reads_file_bytes_once(tmp_path: Path) -> None:
    image = tmp_path / "image.jpg"
    image.write_bytes(b"jpeg")

    samples = _preload_samples([image])

    assert samples == [DecodeSample(path=image, data=b"jpeg")]


def test_path_samples_do_not_preload_file_bytes() -> None:
    assert _path_samples([Path("image.jpg")]) == [
        DecodeSample(path=Path("image.jpg"), data=b"")
    ]


def test_bytes_source_skips_path_only_stdio_codec() -> None:
    codecs, skipped = _resolve_codecs(["ajpegli-stdio"], "RGB", "bytes")

    assert codecs == []
    assert skipped == {
        "ajpegli-stdio": {"skipped": "ajpegli-stdio does not support bytes source"}
    }
