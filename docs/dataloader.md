# DataLoader Benchmarking

`ajpegli.imread(path)` maps a file path to a NumPy array, and
`ajpegli.imdecode(data)` maps preloaded JPEG bytes to a NumPy array. The native
decode path releases the GIL, but DataLoader throughput still depends on
storage, process startup, batch size, and image sizes. Measure it on the target
machine before making speed claims.

Smoke and RAM-backed matrix numbers are published in
[DataLoader Results](dataloader-results.md). They are regression baselines, not
claims about real training throughput.

## Dataset Pattern

```python
from pathlib import Path

import ajpegli


class JpegDataset:
    def __init__(self, paths: list[str | Path], mode: str = "RGB") -> None:
        self.paths = [Path(path) for path in paths]
        self.mode = mode

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, index: int):
        return ajpegli.imread(self.paths[index], mode=self.mode)
```

Keep transforms outside the benchmark first. Add them back only after the raw
decode path is understood.

For RAM-backed benchmarks, preload the JPEG bytes once and decode from memory in
`__getitem__`:

```python
from pathlib import Path

import ajpegli


class InMemoryJpegDataset:
    def __init__(self, paths: list[str | Path], mode: str = "RGB") -> None:
        self.samples = [Path(path).read_bytes() for path in paths]
        self.mode = mode

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int):
        return ajpegli.imdecode(self.samples[index], mode=self.mode)
```

## Worker Matrix

Run this matrix for each dataset group and mode:

- `num_workers`: `0`, `2`, `4`, `8`, `16`
- `batch_size`: `32`, `64`, `128`
- `persistent_workers`: enabled when `num_workers > 0`
- `multiprocessing_context`: `fork` on Linux, `spawn` on macOS/Windows

Example commands:

```bash
just bench-imread-dataloader path/to/small/*.jpg 1000 0 RGB 32
just bench-imread-dataloader path/to/small/*.jpg 1000 4 RGB 32
uv run python benchmarks/bench_imread.py path/to/medium/*.jpg \
  --mode RGB \
  --source bytes \
  --iterations 2000 \
  --thread-workers 8 \
  --dataloader-workers 8 \
  --codecs ajpegli \
  --include-dataloader \
  --batch-size 64 \
  --multiprocessing-context fork
```

Use `--multiprocessing-context spawn` when checking Windows/macOS-like startup
behavior on Unix systems.

For RAM-backed comparisons, keep `--source bytes` and run the full worker /
batch matrix:

```bash
for batch_size in 32 64 128; do
  for workers in 0 2 4 8 16; do
    uv run python benchmarks/bench_imread.py path/to/mixed/*.jpg \
      --mode RGB \
      --source bytes \
      --iterations 2000 \
      --thread-workers 8 \
      --dataloader-workers "$workers" \
      --codecs ajpegli \
      --include-dataloader \
      --batch-size "$batch_size"
  done
done
```

For CID22 validation-set runs, keep the same matrix and add the dataset preset:

```bash
for batch_size in 32 64 128; do
  for workers in 0 2 4 8 16; do
    uv run python benchmarks/bench_imread.py data/cid22-validation \
      --dataset cid22-validation \
      --mode RGB \
      --source bytes \
      --iterations 2000 \
      --thread-workers 8 \
      --dataloader-workers "$workers" \
      --codecs ajpegli \
      --include-dataloader \
      --batch-size "$batch_size"
  done
done
```

## Report Fields

The `torch_dataloader` JSON object reports:

- `images_per_second`: total examples yielded per second.
- `megapixels_per_second`: decoded input pixels per second.
- `workers`: DataLoader worker count.
- `batch_size`: DataLoader batch size.
- `multiprocessing_context`: set only when explicitly requested.
- `skipped`: present when PyTorch is not installed.

Compare `num_workers=0` against process workers. If throughput does not improve,
the bottleneck is likely storage, Python-side transforms, or process overhead
rather than jpegli decode itself.
