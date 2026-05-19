# DataLoader Results

This page records an initial PyTorch `DataLoader` smoke run for
`ajpegli.imread()`. It is a regression baseline for the native path, not a
claim that this setup represents real training throughput.

## Run

- Date: 2026-05-19
- OS: macOS-26.4-arm64-arm-64bit-Mach-O
- CPU: arm
- Python: 3.13.7
- ajpegli: 0.1.2
- jpegli commit: 7cdf212790241868c77dca777dbee14e98128cba
- NumPy: 2.4.5
- PyTorch: 2.12.0
- Image: `third_party/jpegli/testdata/jxl/flower/flower_cropped.jpg`
- Shape: 1040 x 1040 RGB
- Iterations: 256
- Batch size: 32
- Warmup: 3

Each run used the same single vendored JPEG repeatedly. That intentionally keeps
the test easy to reproduce, but it also exaggerates process and batching
overhead compared with a real shuffled dataset.

Command template:

```bash
uv run python benchmarks/bench_imread.py \
  third_party/jpegli/testdata/jxl/flower/flower_cropped.jpg \
  --mode RGB \
  --iterations 256 \
  --thread-workers 4 \
  --dataloader-workers N \
  --warmup 3 \
  --codecs ajpegli \
  --include-dataloader \
  --batch-size 32
```

## Worker Scaling

| DataLoader workers | Images/s | MPix/s | Seconds |
| ---: | ---: | ---: | ---: |
| 0 | 201.1 | 217.6 | 1.273 |
| 2 | 129.5 | 140.1 | 1.977 |
| 4 | 104.2 | 112.7 | 2.458 |
| 8 | 94.8 | 102.5 | 2.702 |

For comparison, the same runner reported roughly 210 images/s sequential and
790 images/s with a 4-thread `ThreadPoolExecutor` for the same image and mode.

## Interpretation

For this synthetic one-file smoke workload, `num_workers=0` is fastest. Extra
DataLoader workers add multiprocessing overhead and do not improve throughput.
That does not mean DataLoader workers are bad for real datasets; it means the
project still needs a representative report across many files, storage modes,
batch sizes, and `fork` / `spawn` contexts before making DataLoader speed
claims.

Use [DataLoader Benchmarking](dataloader.md) for the full matrix to run before a
release-level performance claim.
