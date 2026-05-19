# Benchmarks

`ajpegli` should not claim to be faster than another JPEG loader without a
reproducible run. The benchmark runner emits JSON so results can be checked into
release notes without depending on optional packages at runtime.

Smoke and RAM-backed matrix numbers are published in
[Benchmark Results](benchmark-results.md). They are regression baselines and
should not be treated as broad production performance claims.

## Setup

Install only the comparison tools you want to measure:

```bash
uv sync --extra dev
uv pip install opencv-python-headless pillow
```

PyTorch is only needed for the DataLoader benchmark:

```bash
uv pip install torch
```

## Datasets

Use at least three groups before making project-level performance claims:

- `small`: thumbnails or web images under 256 px on the long edge.
- `medium`: ImageNet-like JPEGs around 224-512 px.
- `large`: camera or dataset photos above 2 MP.
- `mixed`: a shuffled path list containing all groups.

The vendored jpegli files are useful for smoke tests, but they are not a
representative speed dataset by themselves.

### Vendored libjxl testdata

The jpegli submodule vendors `libjxl/testdata` at commit
`ff8d743aaba05b3014f17e5475e576242fa979fc`. Use it for CI smoke tests,
regression fixtures, malformed JPEG coverage, and quick local sanity checks.
It is intentionally small and pinned, so it should not be used as the only
source for project-level speed claims.

### CID22

For release-grade decoder benchmarks, use the Cloudinary Image Dataset '22
validation set as an external manual dataset. CID22 is focused on image
compression quality from medium quality to near visually lossless, and the
validation set contains 49 reference images and 4292 distorted images. The
dataset is licensed under CC BY-SA 4.0, so do not vendor it into this
repository or ship it in wheels.

Download the CID22 validation set from <https://cloudinary.com/labs/cid22>,
extract it outside the repository or under an ignored local data directory, and
point the benchmark runner at the extracted root:

```bash
just bench-cid22 data/cid22-validation 1000 8 RGB ajpegli,cv2,pillow bytes
```

The lower-level command is:

```bash
uv run python benchmarks/bench_imread.py data/cid22-validation \
  --dataset cid22-validation \
  --mode RGB \
  --source bytes \
  --iterations 1000 \
  --thread-workers 8 \
  --codecs ajpegli,cv2,pillow
```

`--dataset cid22-validation` treats each positional argument as an extracted
dataset root or JPEG file, recursively discovers only `.jpg` / `.jpeg` files,
and records the CID22 URL, license, and discovered image count in the output
JSON. Prefer `--source bytes` for CID22 when comparing decoder throughput so
the benchmark measures preloaded JPEG buffers rather than disk speed.

## Single-Process And Threaded

Run each mode separately because RGB, BGR, and grayscale have different
conversion costs:

```bash
just bench-imread path/to/small/*.jpg 1000 8 RGB ajpegli,cv2,pillow
just bench-imread path/to/medium/*.jpg 1000 8 BGR ajpegli,cv2,pillow
just bench-imread path/to/large/*.jpg 200 8 L ajpegli,cv2,pillow
```

The lower-level runner uses explicit worker names:

```bash
uv run python benchmarks/bench_imread.py path/to/small/*.jpg \
  --mode RGB \
  --source path \
  --iterations 1000 \
  --thread-workers 8 \
  --codecs ajpegli,cv2,pillow
```

For native path investigation, `ajpegli-stdio` is an internal benchmark codec
that reads paths with `jpegli_stdio_src(FILE*)` instead of the public
`ajpegli.imread()` path, which reads into memory and decodes with
`jpegli_mem_src`.

Use `--source bytes` to benchmark preloaded JPEG bytes instead of path reads:

```bash
uv run python benchmarks/bench_imread.py path/to/small/*.jpg \
  --mode RGB \
  --source bytes \
  --iterations 1000 \
  --thread-workers 8 \
  --codecs ajpegli,cv2,pillow
```

In bytes mode, the runner reads each JPEG file into memory once before timing.
`ajpegli` uses the public `ajpegli.imdecode(data, mode=...)` API, OpenCV uses
`cv2.imdecode(np.frombuffer(data, np.uint8), ...)`, and Pillow decodes from a
`BytesIO` object. The `ajpegli-stdio` codec is path-only and is reported as
skipped for `--source bytes`.

For the release-grade RAM matrix, run every dataset group with every output
mode:

```bash
for mode in RGB BGR L; do
  uv run python benchmarks/bench_imread.py path/to/small/*.jpg \
    --mode "$mode" --source bytes --iterations 1000 \
    --thread-workers 8 --codecs ajpegli,cv2,pillow
  uv run python benchmarks/bench_imread.py path/to/medium/*.jpg \
    --mode "$mode" --source bytes --iterations 1000 \
    --thread-workers 8 --codecs ajpegli,cv2,pillow
  uv run python benchmarks/bench_imread.py path/to/large/*.jpg \
    --mode "$mode" --source bytes --iterations 200 \
    --thread-workers 8 --codecs ajpegli,cv2,pillow
done
```

The JSON output includes:

- `images_per_second`: decoded images per second.
- `megapixels_per_second`: decoded input pixels per second, based on the last
  decoded shape.
- `p50_seconds` and `p95_seconds`: per-image latency percentiles for the
  sequential reader.
- `source`: `path` for path reads or `bytes` for preloaded in-memory JPEG data.
- `threaded.workers`: the thread count used for threaded throughput.
- `skipped`: optional comparison packages that were not installed.

Keep the raw JSON output with the release artifacts when publishing benchmark
claims.

## Regression Guard

Use the benchmark guard to compare a current JSON run against a saved baseline
from the same machine and dataset:

```bash
just bench-guard artifacts/bench-baseline.json artifacts/bench-current.json 0.20
```

The guard only compares throughput metrics already emitted by
`benchmarks/bench_imread.py`: `images_per_second` and
`megapixels_per_second`. It intentionally does not compare against OpenCV or
Pillow thresholds. Use it to catch large local regressions, for example a
15-20% drop on the same runner, not to claim absolute performance superiority.

## Hot Path Follow-Up

If `ajpegli` trails OpenCV or Pillow on the target data, profile before changing
the native code. Start with:

- tiny JPEG overhead: Python wrapper + NumPy allocation + buffer acquisition.
- native decode time: jpegli header/read/finish time inside the GIL-released
  section.
- output mode cost: RGB vs BGR vs grayscale.
- scanline batch size: compare 16, 32, and 64 rows per `jpegli_read_scanlines`
  call.
- source path: compare `imread(path)` and `imdecode(path.read_bytes())` before
  blaming disk I/O.

## Interpreting Results

Prefer `megapixels_per_second` for large images and `images_per_second` for
small-image pipelines. For service latency, look at `p50_seconds` and
`p95_seconds`; for batch loading, compare threaded throughput and the DataLoader
report.

Do not compare RGB `ajpegli.imread()` against default OpenCV reads unless the
mode is intentional. OpenCV defaults to BGR, while `ajpegli` defaults to RGB.
Use `mode="BGR"` when measuring OpenCV-style pipelines.
