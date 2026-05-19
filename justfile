set shell := ["zsh", "-cu"]

UV := "uv"

default:
    just --list

sync:
    {{ UV }} sync --extra dev

test:
    {{ UV }} run pytest

test-coverage:
    {{ UV }} run pytest --cov-report=json:coverage.json

check-version:
    {{ UV }} run python -m tools.check_versions

coverage-badge:
    just test-coverage
    {{ UV }} run python -m tools.coverage_badge --coverage-json coverage.json --output badges/coverage.svg

test-fast:
    {{ UV }} run pytest -q --no-cov

lint:
    {{ UV }} run ruff check .

format:
    {{ UV }} run ruff format .

typecheck:
    {{ UV }} run ty check python tests tools

build:
    {{ UV }} run python -m build

bench-imread files="third_party/jpegli/testdata/jxl/jpeg_reconstruction/1x1_exif_xmp.jpg" iterations="1000" workers="8" mode="RGB" codecs="ajpegli,cv2,pillow" source="path":
    {{ UV }} run python benchmarks/bench_imread.py {{ files }} --mode {{ mode }} --source {{ source }} --iterations {{ iterations }} --thread-workers {{ workers }} --codecs {{ codecs }}

bench-imread-dataloader files="third_party/jpegli/testdata/jxl/jpeg_reconstruction/1x1_exif_xmp.jpg" iterations="1000" dataloader_workers="4" mode="RGB" batch_size="32" thread_workers="4" source="path":
    {{ UV }} run python benchmarks/bench_imread.py {{ files }} --mode {{ mode }} --source {{ source }} --iterations {{ iterations }} --thread-workers {{ thread_workers }} --dataloader-workers {{ dataloader_workers }} --codecs ajpegli --include-dataloader --batch-size {{ batch_size }}

check:
    just lint
    just typecheck
    just check-version
    just test

ci:
    just lint
    just typecheck
    just check-version
    just coverage-badge
