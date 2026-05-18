from __future__ import annotations

import json
from pathlib import Path

from tools.coverage_badge import read_coverage_percent, write_coverage_badge


def test_read_coverage_percent_rounds_coverage_json_total(tmp_path: Path) -> None:
    coverage_json = tmp_path / "coverage.json"
    coverage_json.write_text(
        json.dumps({"totals": {"percent_covered": 98.27431}}),
        encoding="utf-8",
    )

    assert read_coverage_percent(coverage_json) == 98.27


def test_write_coverage_badge_creates_stable_svg(tmp_path: Path) -> None:
    badge_path = tmp_path / "coverage.svg"

    write_coverage_badge(98.27, badge_path)

    svg = badge_path.read_text(encoding="utf-8")
    assert "<svg" in svg
    assert "coverage" in svg
    assert "98.27%" in svg
    assert "#4c1" in svg
