# DataLoader Benchmarking

`ajpegli.imread(path)` is designed for dataset code that maps a file path to a
NumPy array. The native read/decode path releases the GIL, but DataLoader
throughput still depends on storage, process startup, batch size, and image
sizes. Measure it on the target machine before making speed claims.

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
  --iterations 2000 \
  --workers 8 \
  --codecs ajpegli \
  --include-dataloader \
  --batch-size 64 \
  --multiprocessing-context fork
```

Use `--multiprocessing-context spawn` when checking Windows/macOS-like startup
behavior on Unix systems.

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
