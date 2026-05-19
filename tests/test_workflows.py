from __future__ import annotations

from pathlib import Path


def test_wheels_workflow_runs_published_sdist_install_smoke_after_pypi_publish() -> None:
    workflow = Path(".github/workflows/wheels.yml").read_text(encoding="utf-8")

    assert "pypi-sdist-install-smoke:" in workflow
    assert "needs: publish-pypi" in workflow
    assert "--no-binary ajpegli" in workflow
    assert '"ajpegli==${{ steps.version.outputs.version }}"' in workflow
    assert "for attempt in {1..12}" in workflow
    assert "ajpegli.imdecode" in workflow
