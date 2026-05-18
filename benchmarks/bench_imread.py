from __future__ import annotations

import argparse
import importlib
import json
import math
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import ajpegli
import numpy as np

Reader = Callable[[Path], tuple[int, ...]]
Timer = Callable[[], float]
SUPPORTED_CODECS = ("ajpegli", "cv2", "pillow")
SUPPORTED_MODES = ("RGB", "BGR", "L")
MIN_IMAGE_SHAPE_DIMS = 2


@dataclass(frozen=True)
class Codec:
    name: str
    reader: Reader


class AjpegliDataset:
    def __init__(self, paths: Sequence[Path], mode: str, length: int) -> None:
        self.paths = tuple(paths)
        self.mode = mode
        self.length = length

    def __len__(self) -> int:
        return self.length

    def __getitem__(self, index: int) -> np.ndarray[Any, np.dtype[np.uint8]]:
        return ajpegli.imread(self.paths[index % len(self.paths)], mode=self.mode)


def _identity_collate(batch: list[np.ndarray[Any, np.dtype[np.uint8]]]) -> list[Any]:
    return batch


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return parsed


def _parse_codecs(value: str) -> list[str]:
    codecs = [item.strip().lower() for item in value.split(",")]
    if not codecs or any(not item for item in codecs):
        raise argparse.ArgumentTypeError("codecs must be a comma-separated list")
    unknown = sorted(set(codecs) - set(SUPPORTED_CODECS))
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown codecs: {', '.join(unknown)}")
    return codecs


def _bench_reader(
    reader: Reader,
    paths: Sequence[Path],
    *,
    iterations: int,
    timer: Timer = perf_counter,
) -> dict[str, Any]:
    shape: tuple[int, ...] | None = None
    latencies: list[float] = []
    start = timer()
    for index in range(iterations):
        read_start = timer()
        shape = reader(paths[index % len(paths)])
        latencies.append(timer() - read_start)
    elapsed_seconds = timer() - start
    return _throughput_result(iterations, elapsed_seconds, shape, latencies=latencies)


def _bench_threaded_reader(
    reader: Reader,
    paths: Sequence[Path],
    *,
    iterations: int,
    workers: int,
    timer: Timer = perf_counter,
) -> dict[str, Any]:
    shape: tuple[int, ...] | None = None
    samples = [paths[index % len(paths)] for index in range(iterations)]
    start = timer()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for result_shape in executor.map(reader, samples):
            shape = result_shape
    elapsed_seconds = timer() - start
    result = _throughput_result(iterations, elapsed_seconds, shape)
    result["workers"] = workers
    return result


def _throughput_result(
    images: int,
    elapsed_seconds: float,
    shape: tuple[int, ...] | None,
    *,
    latencies: Sequence[float] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "images": images,
        "seconds": elapsed_seconds,
        "images_per_second": images / elapsed_seconds,
        "megapixels_per_second": _megapixels_per_second(images, elapsed_seconds, shape),
        "last_shape": shape,
    }
    if latencies is not None:
        result["p50_seconds"] = _percentile(latencies, 50)
        result["p95_seconds"] = _percentile(latencies, 95)
    return result


def _megapixels_per_second(
    images: int,
    elapsed_seconds: float,
    shape: tuple[int, ...] | None,
) -> float | None:
    if shape is None or len(shape) < MIN_IMAGE_SHAPE_DIMS:
        return None
    pixels = shape[0] * shape[1]
    return images * pixels / elapsed_seconds / 1_000_000


def _percentile(values: Sequence[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    lower_value = ordered[lower]
    upper_value = ordered[upper]
    return lower_value + (upper_value - lower_value) * (position - lower)


def _make_ajpegli_reader(mode: str) -> Reader:
    def read(path: Path) -> tuple[int, ...]:
        return tuple(ajpegli.imread(path, mode=mode).shape)

    return read


def _make_cv2_reader(mode: str) -> Reader:
    cv2 = importlib.import_module("cv2")

    def read(path: Path) -> tuple[int, ...]:
        if mode == "L":
            image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        else:
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if image is not None and mode == "RGB":
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        if image is None:
            raise RuntimeError(f"cv2 failed to read JPEG: {path}")
        return tuple(image.shape)

    return read


def _make_pillow_reader(mode: str) -> Reader:
    image_module = importlib.import_module("PIL.Image")

    def read(path: Path) -> tuple[int, ...]:
        with image_module.open(path) as image:
            if mode == "BGR":
                array = np.asarray(image.convert("RGB"))[..., ::-1]
            else:
                array = np.asarray(image.convert(mode))
        return tuple(array.shape)

    return read


def _resolve_codecs(
    names: Sequence[str],
    mode: str,
) -> tuple[list[Codec], dict[str, dict[str, str]]]:
    codecs: list[Codec] = []
    skipped: dict[str, dict[str, str]] = {}
    factories: dict[str, Callable[[str], Reader]] = {
        "ajpegli": _make_ajpegli_reader,
        "cv2": _make_cv2_reader,
        "pillow": _make_pillow_reader,
    }
    for name in names:
        try:
            codecs.append(Codec(name=name, reader=factories[name](mode)))
        except ImportError as exc:
            skipped[name] = {"skipped": f"{name} is not installed: {exc.name}"}
    return codecs, skipped


def _bench_torch_dataloader(
    paths: Sequence[Path],
    *,
    mode: str,
    iterations: int,
    workers: int,
    batch_size: int,
    multiprocessing_context: str | None,
    timer: Timer = perf_counter,
) -> dict[str, Any]:
    try:
        torch = importlib.import_module("torch")
    except ImportError:
        return {"skipped": "torch is not installed"}

    dataset = AjpegliDataset(paths, mode, iterations)
    kwargs: dict[str, Any] = {
        "batch_size": batch_size,
        "collate_fn": _identity_collate,
        "num_workers": workers,
    }
    if workers > 0:
        kwargs["persistent_workers"] = True
        kwargs["prefetch_factor"] = 2
        if multiprocessing_context is not None:
            kwargs["multiprocessing_context"] = multiprocessing_context

    start = timer()
    images = 0
    shape: tuple[int, ...] | None = None
    for batch in torch.utils.data.DataLoader(dataset, **kwargs):
        images += len(batch)
        if batch:
            shape = tuple(batch[-1].shape)
        if images >= iterations:
            break
    elapsed_seconds = timer() - start
    result = _throughput_result(images, elapsed_seconds, shape)
    result["workers"] = workers
    result["batch_size"] = batch_size
    if multiprocessing_context is not None:
        result["multiprocessing_context"] = multiprocessing_context
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark JPEG-to-NumPy loading throughput.")
    parser.add_argument("images", nargs="+", type=Path, help="JPEG file(s) to decode")
    parser.add_argument("--mode", default="RGB", choices=SUPPORTED_MODES)
    parser.add_argument("--iterations", type=_positive_int, default=1000)
    parser.add_argument("--workers", type=_positive_int, default=8)
    parser.add_argument("--warmup", type=_positive_int, default=10)
    parser.add_argument("--codecs", type=_parse_codecs, default=list(SUPPORTED_CODECS))
    parser.add_argument("--include-dataloader", action="store_true")
    parser.add_argument("--batch-size", type=_positive_int, default=32)
    parser.add_argument(
        "--dataloader-workers",
        type=_non_negative_int,
        default=None,
        help="PyTorch DataLoader num_workers. Defaults to --workers.",
    )
    parser.add_argument(
        "--multiprocessing-context",
        choices=["fork", "spawn", "forkserver"],
        default=None,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = tuple(args.images)
    codecs, results = _resolve_codecs(args.codecs, args.mode)

    for codec in codecs:
        for index in range(args.warmup):
            codec.reader(paths[index % len(paths)])
        results[codec.name] = {
            "sequential": _bench_reader(
                codec.reader,
                paths,
                iterations=args.iterations,
            ),
            "threaded": _bench_threaded_reader(
                codec.reader,
                paths,
                iterations=args.iterations,
                workers=args.workers,
            ),
        }

    output: dict[str, Any] = {
        "images": [str(path) for path in paths],
        "mode": args.mode,
        "iterations": args.iterations,
        "codecs": results,
    }
    if args.include_dataloader:
        dataloader_workers = args.workers
        if args.dataloader_workers is not None:
            dataloader_workers = args.dataloader_workers
        output["torch_dataloader"] = _bench_torch_dataloader(
            paths,
            mode=args.mode,
            iterations=args.iterations,
            workers=dataloader_workers,
            batch_size=args.batch_size,
            multiprocessing_context=args.multiprocessing_context,
        )

    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
