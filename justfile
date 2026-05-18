set shell := ["zsh", "-cu"]

UV := "uv"

default:
    just --list

sync:
    {{ UV }} sync --extra dev

test:
    {{ UV }} run pytest

test-fast:
    {{ UV }} run pytest -q --no-cov

lint:
    {{ UV }} run ruff check .

format:
    {{ UV }} run ruff format .

typecheck:
    {{ UV }} run ty check python tests

build:
    {{ UV }} run python -m build

bench-imread file="third_party/jpegli/testdata/jxl/jpeg_reconstruction/1x1_exif_xmp.jpg" iterations="1000" workers="8":
    {{ UV }} run python benchmarks/bench_imread.py {{ file }} --iterations {{ iterations }} --workers {{ workers }}

check:
    just lint
    just typecheck
    just test
