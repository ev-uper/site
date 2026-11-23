"""Run the JavaScript scoring tests (tests/js/) from pytest (owner 2026-11-04).

The butir formulas live in site/skor.html and run in the browser, so they
are tested with Node's built-in runner. This wrapper makes one `pytest`
command cover them too; it is skipped where Node is not installed.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

JS = Path(__file__).resolve().parent / "js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_score_formulas_js():
    r = subprocess.run(["node", "--test", str(JS)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
