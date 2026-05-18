from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter
from typing import Any

import ajpegli

Sample = tuple[str, str]


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def _read_once(sample: Sample) -> tuple[int, ...]:
    path, mode = sample
    return tuple(ajpegli.imread(path, mode=mode).shape)


def _bench_sequential(path: str, mode: str, iterations: int) -> dict[str, Any]:
    shape: tuple[int, ...] | None = None
    start = perf_counter()
    for _ in range(iterations):
        shape = _read_once((path, mode))
    elapsed_seconds = perf_counter() - start
    return {
        "images": iterations,
        "seconds": elapsed_seconds,
        "images_per_second": iterations / elapsed_seconds,
        "last_shape": shape,
    }


def _bench_threaded(path: str, mode: str, iterations: int, workers: int) -> dict[str, Any]:
    shape: tuple[int, ...] | None = None
    samples = [(path, mode)] * iterations
    start = perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for result_shape in executor.map(_read_once, samples):
            shape = result_shape
    elapsed_seconds = perf_counter() - start
    return {
        "images": iterations,
        "workers": workers,
        "seconds": elapsed_seconds,
        "images_per_second": iterations / elapsed_seconds,
        "last_shape": shape,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark ajpegli.imread throughput.")
    parser.add_argument("image", type=Path, help="JPEG file to decode")
    parser.add_argument("--mode", default="RGB", choices=["RGB", "L", "CMYK", "native"])
    parser.add_argument("--iterations", type=_positive_int, default=1000)
    parser.add_argument("--workers", type=_positive_int, default=8)
    parser.add_argument("--warmup", type=_positive_int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = str(args.image)
    for _ in range(args.warmup):
        _read_once((path, args.mode))

    result = {
        "image": path,
        "mode": args.mode,
        "sequential": _bench_sequential(path, args.mode, args.iterations),
        "threaded": _bench_threaded(path, args.mode, args.iterations, args.workers),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
