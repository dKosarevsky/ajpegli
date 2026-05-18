# Benchmarks

`ajpegli` should not claim to be faster than another JPEG loader without a
reproducible run. The benchmark runner emits JSON so results can be checked into
release notes without depending on optional packages at runtime.

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

The JSON output includes:

- `images_per_second`: decoded images per second.
- `megapixels_per_second`: decoded input pixels per second, based on the last
  decoded shape.
- `p50_seconds` and `p95_seconds`: per-image latency percentiles for the
  sequential reader.
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
