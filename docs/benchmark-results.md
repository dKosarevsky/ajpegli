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
  --thread-workers 4 \
  --warmup 3 \
  --codecs ajpegli,cv2,pillow

uv run python benchmarks/bench_imread.py \
  third_party/jpegli/testdata/jxl/flower/flower_cropped.jpg \
  --mode BGR \
  --iterations 50 \
  --thread-workers 4 \
  --warmup 3 \
  --codecs ajpegli,cv2,pillow

uv run python benchmarks/bench_imread.py \
  third_party/jpegli/testdata/jxl/flower/flower_cropped.jpg \
  --mode L \
  --iterations 50 \
  --thread-workers 4 \
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

## Vendored Mixed Corpus

This run uses 20 vendored JPEGs from `third_party/jpegli/testdata/jxl/flower`
and `third_party/jpegli/testdata/jxl/jpeg_reconstruction`, excluding
`flower_small.cmyk.jpg` for RGB/BGR/L throughput. That CMYK input currently
fails when forced to RGB with `Unsupported color transform 5 -> 2`; keep that as
a compatibility gap instead of hiding it inside throughput numbers.

- Date: 2026-05-19
- ajpegli: 0.1.4
- Python: 3.13.7
- NumPy: 2.4.5
- OpenCV: 4.13.0
- Pillow: 12.2.0
- Images: 20
- Iterations: 200
- Warmup: 3
- Threaded workers: 4

| Mode | Codec | Sequential img/s | Sequential MPix/s | p50 ms | p95 ms | Threaded img/s | Threaded MPix/s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| RGB | ajpegli | 68.4 | 44.2 | 16.25 | 33.33 | 175.2 | 113.2 |
| RGB | cv2 | 85.1 | 55.0 | 12.13 | 28.93 | 243.9 | 157.6 |
| RGB | pillow | 86.3 | 55.7 | 12.64 | 27.21 | 162.8 | 105.2 |
| BGR | ajpegli | 73.6 | 47.6 | 15.01 | 30.48 | 281.4 | 181.8 |
| BGR | cv2 | 122.2 | 78.9 | 9.02 | 20.87 | 396.6 | 256.2 |
| BGR | pillow | 95.8 | 61.9 | 11.45 | 24.41 | 281.9 | 182.1 |
| L | ajpegli | 101.6 | 65.6 | 11.13 | 23.73 | 385.8 | 249.3 |
| L | cv2 | 153.2 | 99.0 | 6.66 | 19.83 | 572.7 | 370.0 |
| L | pillow | 125.2 | 80.9 | 9.39 | 18.71 | 451.5 | 291.7 |

The mixed vendored corpus tells the same story as the one-file smoke result:
OpenCV is still faster in every measured mode. `ajpegli` threaded BGR is roughly
at Pillow parity on this corpus, but that is not enough for a project-level
performance claim.

## Native Source Path Check

This run compares the public `ajpegli.imread()` path against an internal
benchmark-only `ajpegli-stdio` codec. The public path reads the whole file into
a native buffer and uses `jpegli_mem_src`; the stdio path opens the file with
`FILE*` and uses `jpegli_stdio_src`.

| Dataset | Codec | Sequential img/s | Sequential MPix/s | p50 ms | p95 ms | Threaded img/s | Threaded MPix/s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| flower_cropped | ajpegli | 216.2 | 233.9 | 4.64 | 4.77 | 803.5 | 869.1 |
| flower_cropped | ajpegli-stdio | 215.7 | 233.3 | 4.64 | 4.78 | 821.9 | 889.0 |
| vendored mixed | ajpegli | 86.2 | 55.7 | 14.41 | 26.63 | 330.4 | 213.5 |
| vendored mixed | ajpegli-stdio | 86.3 | 55.8 | 14.55 | 25.44 | 330.9 | 213.8 |

`jpegli_stdio_src` is effectively at parity with the current path in these
smoke runs. There is no measured reason yet to change the public default away
from `jpegli_mem_src`; keep `ajpegli-stdio` as an investigation tool for broader
datasets.
