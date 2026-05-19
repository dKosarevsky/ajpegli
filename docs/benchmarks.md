# Benchmarks

`ajpegli` should not claim to be faster than another JPEG loader without a
reproducible run. The benchmark runner emits JSON so results can be checked into
release notes without depending on optional packages at runtime.

Initial smoke numbers are published in
[Benchmark Results](benchmark-results.md). They are intentionally narrow and
should not be treated as a full performance claim.

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

## Interpreting Results

Prefer `megapixels_per_second` for large images and `images_per_second` for
small-image pipelines. For service latency, look at `p50_seconds` and
`p95_seconds`; for batch loading, compare threaded throughput and the DataLoader
report.

Do not compare RGB `ajpegli.imread()` against default OpenCV reads unless the
mode is intentional. OpenCV defaults to BGR, while `ajpegli` defaults to RGB.
Use `mode="BGR"` when measuring OpenCV-style pipelines.
