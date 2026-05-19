from __future__ import annotations

import argparse
import importlib
import io
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

SUPPORTED_SOURCES = ("path", "bytes")


@dataclass(frozen=True)
class DecodeSample:
    path: Path
    data: bytes


Reader = Callable[[DecodeSample], tuple[int, ...]]
Timer = Callable[[], float]
SUPPORTED_CODECS = ("ajpegli", "ajpegli-stdio", "cv2", "pillow")
SUPPORTED_MODES = ("RGB", "BGR", "L")
MIN_IMAGE_SHAPE_DIMS = 2


@dataclass(frozen=True)
class Codec:
    name: str
    reader: Reader


class AjpegliDataset:
    def __init__(
        self,
        samples: Sequence[DecodeSample],
        mode: str,
        length: int,
        source: str,
    ) -> None:
        self.samples = tuple(samples)
        self.mode = mode
        self.length = length
        self.source = source

    def __len__(self) -> int:
        return self.length

    def __getitem__(self, index: int) -> np.ndarray[Any, np.dtype[np.uint8]]:
        sample = self.samples[index % len(self.samples)]
        if self.source == "bytes":
            return ajpegli.decode(sample.data, mode=self.mode)
        return ajpegli.imread(sample.path, mode=self.mode)


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


def _preload_samples(paths: Sequence[Path]) -> list[DecodeSample]:
    return [DecodeSample(path=path, data=path.read_bytes()) for path in paths]


def _path_samples(paths: Sequence[Path]) -> list[DecodeSample]:
    return [DecodeSample(path=path, data=b"") for path in paths]


def _bench_reader(
    reader: Reader,
    samples: Sequence[DecodeSample],
    *,
    iterations: int,
    timer: Timer = perf_counter,
) -> dict[str, Any]:
    shape: tuple[int, ...] | None = None
    latencies: list[float] = []
    start = timer()
    for index in range(iterations):
        read_start = timer()
        shape = reader(samples[index % len(samples)])
        latencies.append(timer() - read_start)
    elapsed_seconds = timer() - start
    return _throughput_result(iterations, elapsed_seconds, shape, latencies=latencies)


def _bench_threaded_reader(
    reader: Reader,
    samples: Sequence[DecodeSample],
    *,
    iterations: int,
    workers: int,
    timer: Timer = perf_counter,
) -> dict[str, Any]:
    shape: tuple[int, ...] | None = None
    decoded_samples = [samples[index % len(samples)] for index in range(iterations)]
    start = timer()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for result_shape in executor.map(reader, decoded_samples):
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
    def read(sample: DecodeSample) -> tuple[int, ...]:
        return tuple(ajpegli.imread(sample.path, mode=mode).shape)

    return read


def _make_ajpegli_bytes_reader(mode: str) -> Reader:
    def read(sample: DecodeSample) -> tuple[int, ...]:
        return tuple(ajpegli.decode(sample.data, mode=mode).shape)

    return read


def _make_ajpegli_stdio_reader(mode: str) -> Reader:
    native = importlib.import_module("ajpegli._ajpegli")

    def read(sample: DecodeSample) -> tuple[int, ...]:
        image = native.imread_stdio(
            str(sample.path),
            mode=mode,
            dtype="uint8",
            max_pixels=256_000_000,
            max_width=65_535,
            max_height=65_535,
            endianness="native",
        )
        return tuple(image.shape)

    return read


def _make_cv2_reader(mode: str) -> Reader:
    cv2 = importlib.import_module("cv2")

    def read(sample: DecodeSample) -> tuple[int, ...]:
        if mode == "L":
            image = cv2.imread(str(sample.path), cv2.IMREAD_GRAYSCALE)
        else:
            image = cv2.imread(str(sample.path), cv2.IMREAD_COLOR)
            if image is not None and mode == "RGB":
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        if image is None:
            raise RuntimeError(f"cv2 failed to read JPEG: {sample.path}")
        return tuple(image.shape)

    return read


def _make_cv2_bytes_reader(mode: str) -> Reader:
    cv2 = importlib.import_module("cv2")

    def read(sample: DecodeSample) -> tuple[int, ...]:
        encoded = np.frombuffer(sample.data, dtype=np.uint8)
        if mode == "L":
            image = cv2.imdecode(encoded, cv2.IMREAD_GRAYSCALE)
        elif mode == "RGB" and hasattr(cv2, "IMREAD_COLOR_RGB"):
            image = cv2.imdecode(encoded, cv2.IMREAD_COLOR_RGB)
        else:
            flag = getattr(cv2, "IMREAD_COLOR_BGR", cv2.IMREAD_COLOR)
            image = cv2.imdecode(encoded, flag)
            if image is not None and mode == "RGB":
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        if image is None:
            raise RuntimeError(f"cv2 failed to decode JPEG bytes: {sample.path}")
        return tuple(image.shape)

    return read


def _make_pillow_reader(mode: str) -> Reader:
    image_module = importlib.import_module("PIL.Image")

    def read(sample: DecodeSample) -> tuple[int, ...]:
        with image_module.open(sample.path) as image:
            if mode == "BGR":
                array = np.asarray(image.convert("RGB"))[..., ::-1]
            else:
                array = np.asarray(image.convert(mode))
        return tuple(array.shape)

    return read


def _make_pillow_bytes_reader(mode: str) -> Reader:
    image_module = importlib.import_module("PIL.Image")

    def read(sample: DecodeSample) -> tuple[int, ...]:
        with image_module.open(io.BytesIO(sample.data)) as image:
            if mode == "BGR":
                array = np.asarray(image.convert("RGB"))[..., ::-1]
            else:
                array = np.asarray(image.convert(mode))
        return tuple(array.shape)

    return read


def _resolve_codecs(
    names: Sequence[str],
    mode: str,
    source: str,
) -> tuple[list[Codec], dict[str, dict[str, str]]]:
    codecs: list[Codec] = []
    skipped: dict[str, dict[str, str]] = {}
    if source == "bytes":
        factories: dict[str, Callable[[str], Reader]] = {
            "ajpegli": _make_ajpegli_bytes_reader,
            "cv2": _make_cv2_bytes_reader,
            "pillow": _make_pillow_bytes_reader,
        }
    else:
        factories = {
            "ajpegli": _make_ajpegli_reader,
            "ajpegli-stdio": _make_ajpegli_stdio_reader,
            "cv2": _make_cv2_reader,
            "pillow": _make_pillow_reader,
        }
    for name in names:
        if name not in factories:
            skipped[name] = {"skipped": f"{name} does not support {source} source"}
            continue
        try:
            codecs.append(Codec(name=name, reader=factories[name](mode)))
        except ImportError as exc:
            skipped[name] = {"skipped": f"{name} is not installed: {exc.name}"}
    return codecs, skipped


def _bench_torch_dataloader(
    samples: Sequence[DecodeSample],
    *,
    mode: str,
    source: str,
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

    dataset = AjpegliDataset(samples, mode, iterations, source)
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


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark JPEG-to-NumPy loading throughput.")
    parser.add_argument("images", nargs="+", type=Path, help="JPEG file(s) to decode")
    parser.add_argument("--mode", default="RGB", choices=SUPPORTED_MODES)
    parser.add_argument("--source", default="path", choices=SUPPORTED_SOURCES)
    parser.add_argument("--iterations", type=_positive_int, default=1000)
    parser.add_argument(
        "--thread-workers",
        dest="thread_workers",
        type=_positive_int,
        default=8,
        help="ThreadPoolExecutor worker count for threaded reader throughput.",
    )
    parser.add_argument(
        "--workers",
        dest="thread_workers",
        type=_positive_int,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--warmup", type=_positive_int, default=10)
    parser.add_argument("--codecs", type=_parse_codecs, default=list(SUPPORTED_CODECS))
    parser.add_argument("--include-dataloader", action="store_true")
    parser.add_argument("--batch-size", type=_positive_int, default=32)
    parser.add_argument(
        "--dataloader-workers",
        type=_non_negative_int,
        default=None,
        help="PyTorch DataLoader num_workers. Defaults to --thread-workers.",
    )
    parser.add_argument(
        "--multiprocessing-context",
        choices=["fork", "spawn", "forkserver"],
        default=None,
    )
    return parser.parse_args(argv)


def parse_args() -> argparse.Namespace:
    return _parse_args()


def main() -> int:
    args = parse_args()
    paths = tuple(args.images)
    samples = _preload_samples(paths) if args.source == "bytes" else _path_samples(paths)
    codecs, results = _resolve_codecs(args.codecs, args.mode, args.source)

    for codec in codecs:
        for index in range(args.warmup):
            codec.reader(samples[index % len(samples)])
        results[codec.name] = {
            "sequential": _bench_reader(
                codec.reader,
                samples,
                iterations=args.iterations,
            ),
            "threaded": _bench_threaded_reader(
                codec.reader,
                samples,
                iterations=args.iterations,
                workers=args.thread_workers,
            ),
        }

    output: dict[str, Any] = {
        "images": [str(path) for path in paths],
        "mode": args.mode,
        "source": args.source,
        "iterations": args.iterations,
        "codecs": results,
    }
    if args.include_dataloader:
        dataloader_workers = args.thread_workers
        if args.dataloader_workers is not None:
            dataloader_workers = args.dataloader_workers
        output["torch_dataloader"] = _bench_torch_dataloader(
            samples,
            mode=args.mode,
            source=args.source,
            iterations=args.iterations,
            workers=dataloader_workers,
            batch_size=args.batch_size,
            multiprocessing_context=args.multiprocessing_context,
        )

    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
