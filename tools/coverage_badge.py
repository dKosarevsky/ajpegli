from __future__ import annotations

import argparse
import json
from pathlib import Path

BRIGHTGREEN_MINIMUM = 98
GREEN_MINIMUM = 90
YELLOW_MINIMUM = 80
ORANGE_MINIMUM = 70
CHARACTER_WIDTH = 7
TEXT_PADDING = 10
BADGE_HEIGHT = 20
FONT_FAMILY = "Verdana,Geneva,DejaVu Sans,sans-serif"


def read_coverage_percent(path: Path) -> float:
    report = json.loads(path.read_text(encoding="utf-8"))
    percent = float(report["totals"]["percent_covered"])
    return round(percent, 2)


def write_coverage_badge(percent: float, path: Path) -> None:
    label = "coverage"
    message = f"{percent:.2f}%"
    color = _coverage_color(percent)
    svg = _render_badge(label=label, message=message, color=color)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")


def _coverage_color(percent: float) -> str:
    if percent >= BRIGHTGREEN_MINIMUM:
        return "#4c1"
    if percent >= GREEN_MINIMUM:
        return "#97ca00"
    if percent >= YELLOW_MINIMUM:
        return "#dfb317"
    if percent >= ORANGE_MINIMUM:
        return "#fe7d37"
    return "#e05d44"


def _text_width(text: str) -> int:
    return TEXT_PADDING + len(text) * CHARACTER_WIDTH


def _render_badge(*, label: str, message: str, color: str) -> str:
    label_width = _text_width(label)
    message_width = _text_width(message)
    total_width = label_width + message_width
    label_center = label_width / 2
    message_center = label_width + message_width / 2
    label_text_length = (label_width - TEXT_PADDING) * 10
    message_text_length = (message_width - TEXT_PADDING) * 10
    lines = [
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{total_width}" height="{BADGE_HEIGHT}" role="img" '
            f'aria-label="{label}: {message}">'
        ),
        f"  <title>{label}: {message}</title>",
        '  <linearGradient id="s" x2="0" y2="100%">',
        '    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>',
        '    <stop offset="1" stop-opacity=".1"/>',
        "  </linearGradient>",
        '  <clipPath id="r">',
        f'    <rect width="{total_width}" height="{BADGE_HEIGHT}" rx="3" fill="#fff"/>',
        "  </clipPath>",
        '  <g clip-path="url(#r)">',
        f'    <rect width="{label_width}" height="{BADGE_HEIGHT}" fill="#555"/>',
        (
            f'    <rect x="{label_width}" width="{message_width}" '
            f'height="{BADGE_HEIGHT}" fill="{color}"/>'
        ),
        f'    <rect width="{total_width}" height="{BADGE_HEIGHT}" fill="url(#s)"/>',
        "  </g>",
        (
            '  <g fill="#fff" text-anchor="middle" '
            f'font-family="{FONT_FAMILY}" text-rendering="geometricPrecision" '
            'font-size="110">'
        ),
        _svg_text(label, label_center, 150, label_text_length, shadow=True),
        _svg_text(label, label_center, 140, label_text_length),
        _svg_text(message, message_center, 150, message_text_length, shadow=True),
        _svg_text(message, message_center, 140, message_text_length),
        "  </g>",
        "</svg>",
    ]
    return "\n".join(lines) + "\n"


def _svg_text(
    text: str,
    center: float,
    y: int,
    text_length: int,
    *,
    shadow: bool = False,
) -> str:
    attributes = [
        f'x="{center * 10:.0f}"',
        f'y="{y}"',
    ]
    if shadow:
        attributes.extend(
            [
                'aria-hidden="true"',
                'fill="#010101"',
                'fill-opacity=".3"',
            ],
        )
    attributes.extend(
        [
            'transform="scale(.1)"',
            f'textLength="{text_length}"',
        ],
    )
    return f'    <text {" ".join(attributes)}>{text}</text>'


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the repository coverage badge.")
    parser.add_argument("--coverage-json", type=Path, default=Path("coverage.json"))
    parser.add_argument("--output", type=Path, default=Path("badges/coverage.svg"))
    args = parser.parse_args()

    write_coverage_badge(read_coverage_percent(args.coverage_json), args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
