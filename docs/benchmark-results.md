# Benchmark Results

This page records reproducible smoke benchmark results for the current
`ajpegli.imread()` path. It is not a project-level speed claim. The vendored
jpegli image used here is useful for regression checks, but it is not a broad
dataset.

## Run

- Date: 2026-05-19
- OS: macOS-26.4-arm64-arm-64bit-Mach-O
- CPU: arm
- Python: 3.13.7
- ajpegli: 0.1.2
- jpegli commit: 7cdf212790241868c77dca777dbee14e98128cba
- NumPy: 2.4.5
- OpenCV: 4.13.0
- Pillow: 12.2.0
- Image: `third_party/jpegli/testdata/jxl/flower/flower_cropped.jpg`
- Shape: 1040 x 1040
- Iterations: 50
- Warmup: 3
- Threaded workers: 4

Commands:

```bash
uv run python benchmarks/bench_imread.py \
  third_party/jpegli/testdata/jxl/flower/flower_cropped.jpg \
  --mode RGB \
  --iterations 50 \
  --workers 4 \
  --warmup 3 \
  --codecs ajpegli,cv2,pillow

uv run python benchmarks/bench_imread.py \
  third_party/jpegli/testdata/jxl/flower/flower_cropped.jpg \
  --mode BGR \
  --iterations 50 \
  --workers 4 \
  --warmup 3 \
  --codecs ajpegli,cv2,pillow

uv run python benchmarks/bench_imread.py \
  third_party/jpegli/testdata/jxl/flower/flower_cropped.jpg \
  --mode L \
  --iterations 50 \
  --workers 4 \
  --warmup 3 \
  --codecs ajpegli,cv2,pillow
```

## RGB

| Codec | Sequential img/s | Sequential MPix/s | p50 ms | p95 ms | Threaded img/s | Threaded MPix/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ajpegli | 199.2 | 215.5 | 4.89 | 5.95 | 763.5 | 825.8 |
| cv2 | 308.4 | 333.6 | 3.26 | 3.47 | 1113.9 | 1204.8 |
| pillow | 277.0 | 299.6 | 3.64 | 3.81 | 810.0 | 876.1 |

## BGR

| Codec | Sequential img/s | Sequential MPix/s | p50 ms | p95 ms | Threaded img/s | Threaded MPix/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ajpegli | 205.4 | 222.2 | 4.87 | 5.08 | 750.5 | 811.8 |
| cv2 | 335.7 | 363.1 | 2.98 | 3.12 | 1188.1 | 1285.0 |
| pillow | 279.7 | 302.5 | 3.57 | 3.81 | 719.1 | 777.8 |

## Grayscale

| Codec | Sequential img/s | Sequential MPix/s | p50 ms | p95 ms | Threaded img/s | Threaded MPix/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ajpegli | 257.7 | 278.7 | 3.87 | 4.09 | 922.6 | 997.9 |
| cv2 | 410.0 | 443.5 | 2.45 | 2.59 | 1530.1 | 1654.9 |
| pillow | 303.2 | 327.9 | 3.34 | 3.55 | 1021.7 | 1105.0 |

## Interpretation

On this smoke corpus, OpenCV and Pillow are faster than `ajpegli` in the tested
RGB, BGR, and grayscale modes. That is useful negative evidence: the project
should not claim to be faster than OpenCV or Pillow without broader benchmark
data and hot-path work.

The current value proposition remains narrower and verifiable: `pip install
ajpegli`, pass a JPEG path, get a NumPy array, with native jpegli decode, RGB /
BGR / grayscale modes, GIL release around file I/O and decode, and no OpenCV or
Pillow runtime dependency.
