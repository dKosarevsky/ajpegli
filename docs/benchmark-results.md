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
- Source: path
- Iterations: 50
- Warmup: 3
- Threaded workers: 4

Commands:

```bash
uv run python benchmarks/bench_imread.py \
  third_party/jpegli/testdata/jxl/flower/flower_cropped.jpg \
  --mode RGB \
  --source path \
  --iterations 50 \
  --thread-workers 4 \
  --warmup 3 \
  --codecs ajpegli,cv2,pillow

uv run python benchmarks/bench_imread.py \
  third_party/jpegli/testdata/jxl/flower/flower_cropped.jpg \
  --mode BGR \
  --source path \
  --iterations 50 \
  --thread-workers 4 \
  --warmup 3 \
  --codecs ajpegli,cv2,pillow

uv run python benchmarks/bench_imread.py \
  third_party/jpegli/testdata/jxl/flower/flower_cropped.jpg \
  --mode L \
  --source path \
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
- Source: path
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

## Vendored Mixed Corpus, Bytes Source

This run uses the same vendored mixed corpus as above, but with
`--source bytes`. Each JPEG is read into memory before timing starts. `ajpegli`
uses `ajpegli.imdecode(data, mode=...)`, OpenCV uses
`cv2.imdecode(np.frombuffer(data, np.uint8), ...)`, and Pillow decodes from
`BytesIO`.

- Date: 2026-05-19
- ajpegli: 0.1.5
- Python: 3.13.7
- NumPy: 2.4.5
- OpenCV: 4.13.0
- Pillow: 12.2.0
- Images: 20
- Source: bytes
- Iterations: 200
- Warmup: 3
- Threaded workers: 4

| Mode | Codec | Sequential img/s | Sequential MPix/s | p50 ms | p95 ms | Threaded img/s | Threaded MPix/s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| RGB | ajpegli | 77.1 | 20.9 | 14.74 | 29.85 | 325.2 | 88.2 |
| RGB | cv2 | 140.6 | 38.1 | 8.21 | 17.51 | 529.9 | 143.8 |
| RGB | pillow | 115.8 | 31.4 | 10.57 | 21.47 | 370.2 | 100.5 |
| BGR | ajpegli | 85.6 | 23.2 | 14.44 | 26.80 | 312.4 | 84.8 |
| BGR | cv2 | 130.6 | 35.4 | 8.36 | 20.25 | 537.4 | 145.8 |
| BGR | pillow | 116.3 | 31.5 | 10.60 | 21.61 | 374.8 | 101.7 |
| L | ajpegli | 103.8 | 28.2 | 11.03 | 23.28 | 405.7 | 110.1 |
| L | cv2 | 148.0 | 40.2 | 6.54 | 19.94 | 591.1 | 160.4 |
| L | pillow | 112.1 | 30.4 | 9.92 | 21.92 | 456.4 | 123.8 |

These bytes-source smoke numbers still do not support a claim that `ajpegli` is
faster than OpenCV or Pillow. They are useful as a RAM-backed regression
baseline and avoid mixing codec throughput with storage differences.

## RAM Dataset Matrix

This run expands the RAM-backed `--source bytes` comparison beyond one mixed
corpus. Files are still vendored smoke fixtures, not a representative production
dataset, but the split makes size sensitivity visible.

- Date: 2026-05-19
- ajpegli: 0.1.5
- Python: 3.13.7
- NumPy: 2.4.5
- OpenCV: 4.13.0
- Pillow: 12.2.0
- Source: bytes
- Threaded workers: 4

Datasets:

| Dataset | Files | Examples | Iterations |
| --- | ---: | --- | ---: |
| small fixtures | 3 | `sideways_bench.jpg`, `flower_small.q85_*` | 600 |
| medium | 2 | `bicycles_restarts.jpg`, `flower_cropped.jpg` | 240 |
| large | 4 | full-size `flower.png.im_q85_*` JPEGs | 80 |
| mixed | 9 | small fixtures + medium + large | 240 |

Throughput is reported as sequential images/s followed by 4-thread images/s.

| Dataset | Mode | ajpegli | cv2 | pillow |
| --- | --- | ---: | ---: | ---: |
| small fixtures | RGB | 867.8 / 3165.6 | 1482.8 / 5691.7 | 1230.6 / 4085.3 |
| small fixtures | BGR | 891.9 / 3365.2 | 1526.2 / 5718.9 | 1243.5 / 4052.2 |
| small fixtures | L | 1063.1 / 3923.8 | 1904.7 / 7164.9 | 1330.1 / 4619.4 |
| medium | RGB | 274.7 / 1031.3 | 461.9 / 1771.3 | 370.9 / 1215.2 |
| medium | BGR | 277.0 / 1034.8 | 466.2 / 1776.1 | 372.9 / 1256.0 |
| medium | L | 343.0 / 1224.8 | 558.1 / 2152.7 | 404.5 / 1496.1 |
| large | RGB | 46.3 / 174.5 | 69.6 / 260.7 | 59.5 / 191.9 |
| large | BGR | 45.6 / 171.5 | 69.3 / 260.3 | 57.3 / 184.3 |
| large | L | 52.5 / 197.5 | 75.6 / 282.7 | 64.4 / 238.3 |
| mixed | RGB | 93.7 / 358.3 | 143.4 / 545.9 | 119.0 / 399.9 |
| mixed | BGR | 92.3 / 353.2 | 142.7 / 543.1 | 120.7 / 405.9 |
| mixed | L | 107.7 / 406.8 | 157.5 / 596.0 | 131.6 / 491.4 |

Latency checks tell the same story. For small RGB JPEGs, `ajpegli` p50 is
1.26 ms versus OpenCV 0.73 ms and Pillow 0.90 ms. For large RGB JPEGs,
`ajpegli` p50 is 22.72 ms versus OpenCV 14.32 ms and Pillow 16.62 ms. On the
mixed RGB set, `ajpegli` p50 is 4.61 ms versus OpenCV 2.80 ms and Pillow
3.47 ms.

The actionable conclusion is that RAM preload alone does not make `ajpegli`
competitive with OpenCV/Pillow on these corpora. Future speed work should focus
on the native decode/output path, not disk I/O.

## CID22 Validation Set, Bytes Source

This run uses the Cloudinary Image Dataset '22 validation set as an external
manual benchmark. The full validation archive contains multiple codecs and file
formats; this decoder run extracts only the `mozjpeg/*.jpg` files and benchmarks
preloaded JPEG bytes.

- Date: 2026-05-19
- ajpegli: 0.1.5
- Python: 3.13.7
- NumPy: 2.4.5
- OpenCV: 4.13.0
- Pillow: 12.2.0
- Dataset: CID22 validation set
- Dataset URL: <https://cloudinary.com/labs/cid22>
- Dataset license: CC BY-SA 4.0
- JPEG files: 536
- Source: bytes
- Iterations: 1000
- Warmup: 3
- Threaded workers: 8

Command template:

```bash
uv run python benchmarks/bench_imread.py data/cid22-validation \
  --dataset cid22-validation \
  --mode RGB \
  --source bytes \
  --iterations 1000 \
  --warmup 3 \
  --thread-workers 8 \
  --codecs ajpegli,cv2,pillow
```

| Mode | Codec | Sequential img/s | Sequential MPix/s | p50 ms | p95 ms | Threaded img/s | Threaded MPix/s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| RGB | ajpegli | 582.8 | 152.8 | 1.270 | 4.030 | 3913.8 | 1026.0 |
| RGB | cv2 | 876.9 | 229.9 | 0.714 | 3.488 | 5082.9 | 1332.5 |
| RGB | pillow | 748.5 | 196.2 | 0.900 | 3.700 | 3053.6 | 800.5 |
| BGR | ajpegli | 577.0 | 151.2 | 1.271 | 4.056 | 4002.0 | 1049.1 |
| BGR | cv2 | 882.1 | 231.2 | 0.710 | 3.485 | 6096.9 | 1598.3 |
| BGR | pillow | 759.8 | 199.2 | 0.886 | 3.616 | 3593.4 | 942.0 |
| L | ajpegli | 668.2 | 175.2 | 1.060 | 3.825 | 4383.1 | 1149.0 |
| L | cv2 | 1016.6 | 266.5 | 0.573 | 3.114 | 7004.4 | 1836.2 |
| L | pillow | 794.1 | 208.2 | 0.830 | 3.609 | 3923.0 | 1028.4 |

CID22 confirms the vendored-corpus result: OpenCV is faster than `ajpegli` in
every measured mode. Pillow is faster sequentially, while `ajpegli` is faster
than Pillow in the 8-thread RGB/BGR runs on this machine. That is still not a
project-level speed claim; it is a dataset-specific baseline for future hot-path
work.

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
