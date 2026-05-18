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

check:
    just lint
    just typecheck
    just test

