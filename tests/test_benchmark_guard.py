from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmark_guard import BenchmarkRegression, compare_benchmarks, main


def _benchmark(images_per_second: float, megapixels_per_second: float) -> dict:
    return {
        "codecs": {
            "ajpegli": {
                "sequential": {
                    "images_per_second": images_per_second,
                    "megapixels_per_second": megapixels_per_second,
                },
                "threaded": {
                    "images_per_second": images_per_second * 2,
                    "megapixels_per_second": megapixels_per_second * 2,
                },
            }
        }
    }


def test_compare_benchmarks_accepts_small_metric_drift() -> None:
    baseline = _benchmark(images_per_second=100.0, megapixels_per_second=200.0)
    current = _benchmark(images_per_second=86.0, megapixels_per_second=180.0)

    assert compare_benchmarks(baseline, current, max_regression=0.15) == []


def test_compare_benchmarks_reports_large_regression() -> None:
    baseline = _benchmark(images_per_second=100.0, megapixels_per_second=200.0)
    current = _benchmark(images_per_second=70.0, megapixels_per_second=180.0)

    regressions = compare_benchmarks(baseline, current, max_regression=0.15)

    assert regressions == [
        BenchmarkRegression(
            path="codecs.ajpegli.sequential.images_per_second",
            baseline=100.0,
            current=70.0,
            regression=0.30,
        ),
        BenchmarkRegression(
            path="codecs.ajpegli.threaded.images_per_second",
            baseline=200.0,
            current=140.0,
            regression=0.30,
        ),
    ]


def test_compare_benchmarks_ignores_missing_optional_metrics() -> None:
    baseline = {"codecs": {"cv2": {"skipped": "cv2 is not installed"}}}
    current = {"codecs": {"cv2": {"skipped": "cv2 is not installed"}}}

    assert compare_benchmarks(baseline, current, max_regression=0.15) == []


def test_benchmark_guard_cli_returns_nonzero_for_regression(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text(json.dumps(_benchmark(100.0, 200.0)), encoding="utf-8")
    current.write_text(json.dumps(_benchmark(70.0, 180.0)), encoding="utf-8")

    assert main([str(baseline), str(current), "--max-regression", "0.15"]) == 1

    captured = capsys.readouterr()
    assert "codecs.ajpegli.sequential.images_per_second" in captured.out
    assert "30.0%" in captured.out
