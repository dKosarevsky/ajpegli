from __future__ import annotations

import argparse
import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MAX_REGRESSION = 0.20
METRIC_NAMES = frozenset(
    {
        "images_per_second",
        "megapixels_per_second",
    },
)


@dataclass(frozen=True)
class BenchmarkRegression:
    path: str
    baseline: float
    current: float
    regression: float


def compare_benchmarks(
    baseline: dict[str, Any],
    current: dict[str, Any],
    *,
    max_regression: float = DEFAULT_MAX_REGRESSION,
) -> list[BenchmarkRegression]:
    regressions: list[BenchmarkRegression] = []
    for path, baseline_value in _iter_metric_values(baseline):
        current_value = _lookup_number(current, path)
        if current_value is None or baseline_value <= 0:
            continue
        regression = (baseline_value - current_value) / baseline_value
        if regression > max_regression:
            regressions.append(
                BenchmarkRegression(
                    path=path,
                    baseline=baseline_value,
                    current=current_value,
                    regression=regression,
                )
            )
    return regressions


def _iter_metric_values(data: Any, prefix: str = "") -> Iterator[tuple[str, float]]:
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in METRIC_NAMES and isinstance(value, (int, float)):
                yield path, float(value)
            else:
                yield from _iter_metric_values(value, path)
    elif isinstance(data, list):
        for index, value in enumerate(data):
            path = f"{prefix}.{index}" if prefix else str(index)
            yield from _iter_metric_values(value, path)


def _lookup_number(data: Any, path: str) -> float | None:
    value = data
    for part in path.split("."):
        if isinstance(value, dict):
            if part not in value:
                return None
            value = value[part]
        elif isinstance(value, list):
            try:
                value = value[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare benchmark JSON against a baseline.")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("--max-regression", type=float, default=DEFAULT_MAX_REGRESSION)
    args = parser.parse_args(argv)

    regressions = compare_benchmarks(
        _read_json(args.baseline),
        _read_json(args.current),
        max_regression=args.max_regression,
    )
    if not regressions:
        print("No benchmark regressions found.")
        return 0

    for regression in regressions:
        print(
            f"{regression.path}: "
            f"{regression.current:.3f} < {regression.baseline:.3f} "
            f"({regression.regression:.1%} regression)"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
