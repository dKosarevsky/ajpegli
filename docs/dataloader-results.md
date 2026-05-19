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
- Source: path
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
  --source path \
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

## Vendored Mixed Corpus

This run uses the same 20-file vendored corpus described in
[Benchmark Results](benchmark-results.md), excluding the CMYK JPEG for RGB
throughput.

- Date: 2026-05-19
- ajpegli: 0.1.4
- Python: 3.13.7
- NumPy: 2.4.5
- PyTorch: 2.12.0
- Images: 20
- Mode: RGB
- Source: path
- Iterations: 512
- Batch size: 32
- Warmup: 3

| DataLoader workers | Images/s | MPix/s | Seconds |
| ---: | ---: | ---: | ---: |
| 0 | 85.0 | 291.3 | 6.027 |
| 2 | 87.8 | 301.2 | 5.829 |
| 4 | 88.8 | 304.5 | 5.766 |
| 8 | 72.7 | 249.3 | 7.043 |

For this vendored mixed corpus, `num_workers=4` is slightly faster than
`num_workers=0`, while `num_workers=8` is slower. The improvement is small, so
the practical takeaway is still to measure worker count on the target dataset
and storage stack instead of assuming more workers are faster.

## Vendored Mixed Corpus, Bytes Source

This run uses the same 20-file vendored corpus, but with `--source bytes`.
JPEG files are preloaded into memory before timing starts, and each dataset
item calls `ajpegli.imdecode(data, mode="RGB")`.

- Date: 2026-05-19
- ajpegli: 0.1.5
- Python: 3.13.7
- NumPy: 2.4.5
- PyTorch: 2.12.0
- Images: 20
- Mode: RGB
- Source: bytes
- Iterations: 512
- Batch size: 32
- Warmup: 3

| DataLoader workers | Images/s | MPix/s | Seconds |
| ---: | ---: | ---: | ---: |
| 0 | 86.1 | 295.1 | 5.950 |
| 2 | 86.4 | 296.4 | 5.924 |
| 4 | 65.9 | 226.1 | 7.767 |
| 8 | 41.4 | 142.1 | 12.355 |

For this RAM-backed smoke workload, extra DataLoader workers do not improve
throughput. The fastest measurements are `num_workers=0` and `num_workers=2`,
while higher worker counts are slower from multiprocessing overhead.

## RAM Matrix, Mixed Size Corpus

This run uses a 9-file vendored corpus split across small, medium, and large
JPEGs. Every sample is preloaded into memory before timing starts, so each
`Dataset.__getitem__` calls `ajpegli.imdecode(data, mode="RGB")`.

- Date: 2026-05-19
- ajpegli: 0.1.5
- Python: 3.13.7
- NumPy: 2.4.5
- PyTorch: 2.12.0
- Images: 9
- Mode: RGB
- Source: bytes
- Iterations: 512
- Warmup: 3

Images/s:

| Batch size | workers=0 | workers=2 | workers=4 | workers=8 | workers=16 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 32 | 91.0 | 95.1 | 83.0 | 40.6 | 29.3 |
| 64 | 89.9 | 101.9 | 82.5 | 48.9 | 32.6 |
| 128 | 90.8 | 93.6 | 67.6 | 51.0 | 32.6 |

MPix/s:

| Batch size | workers=0 | workers=2 | workers=4 | workers=8 | workers=16 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 32 | 311.9 | 326.0 | 284.6 | 139.2 | 100.3 |
| 64 | 308.2 | 349.3 | 282.8 | 167.8 | 111.7 |
| 128 | 311.3 | 320.8 | 231.8 | 174.8 | 111.9 |

`num_workers=2` with `batch_size=64` is the best point in this smoke run, but
the margin over `num_workers=0` is small. `num_workers=8` and `16` are worse;
PyTorch also warned that 16 workers exceeds the suggested worker count for this
machine. This supports a conservative recommendation: tune worker count on the
target training host instead of assuming more workers help.

Context sanity, `batch_size=64`, `iterations=256`:

| Multiprocessing context | workers=2 img/s | workers=4 img/s |
| --- | ---: | ---: |
| fork | 133.5 | 165.3 |
| spawn | 77.0 | 60.5 |

These rows are a sanity check, not a cross-platform claim. They show that start
method can dominate RAM-backed DataLoader throughput; Linux `fork` and
macOS/Windows `spawn` should be reported separately in any release-grade
benchmark.
