from __future__ import annotations

import argparse
from collections.abc import Sequence

from ._version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ajpegli")
    parser.add_argument("--version", action="store_true", help="print ajpegli version and exit")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"ajpegli {__version__}")
        return 0
    parser.print_help()
    return 0

