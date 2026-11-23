"""cpl package against Excel's own results.

tests/data/golden_example.xlsx is the master template filled with fictitious
data and recalculated by Excel (make_golden.py + recalc_excel.ps1). Its cached
Hasil and Periksa values are the reference: the Python recompute must match
them cell by cell.
"""
from pathlib import Path

import numpy as np
import openpyxl
import pytest

from cpl import class_attainment, compute, read_template, run_checks
from cpl.template import N_STUDENT, norm_cpl

GOLDEN = Path(__file__).parent / "data" / "golden_example.xlsx"

# Hasil column blocks (1-based column numbers): B:AY, AZ:BI, BJ:CW, CX:DI, DJ.
BLOCKS = {"sub": (2, 50), "cpmk": (52, 10), "indicator": (62, 40), "cpl": (102, 12)}
COL_TOTAL_CO = 114


@pytest.fixture(scope="module")
def golden():
    t = read_template(GOLDEN)
    r = compute(t)
    wb = openpyxl.load_workbook(GOLDEN, data_only=True)
    return t, r, wb


def _cached(v):
    """Cached Excel value -> float; '' or None (IFERROR / excluded row) -> NaN."""
    return np.nan if v in (None, "") else float(v)


def test_golden_file_has_cached_values(golden):
    _, _, wb = golden
    assert wb["Hasil"].cell(5, COL_TOTAL_CO).value not in (None, ""), \
        "golden file not recalculated by Excel; run tests/data/recalc_excel.ps1"


@pytest.mark.parametrize("block", list(BLOCKS))
def test_matches_excel_hasil(golden, block):
    _, r, wb = golden
    first, n = BLOCKS[block]
    hasil = wb["Hasil"]
    expected = np.array([[_cached(hasil.cell(5 + i, first + j).value) for j in range(n)]
                         for i in range(N_STUDENT)])
    got = getattr(r, block)
    assert np.array_equal(np.isnan(expected), np.isnan(got)), f"{block}: blank pattern differs"
    np.testing.assert_allclose(got[~np.isnan(got)], expected[~np.isnan(expected)], rtol=0, atol=1e-9)


def test_matches_excel_total_co(golden):
    _, r, wb = golden
    expected = np.array([_cached(wb["Hasil"].cell(5 + i, COL_TOTAL_CO).value) for i in range(N_STUDENT)])
    assert np.array_equal(np.isnan(expected), np.isnan(r.total_co))
    np.testing.assert_allclose(r.total_co[~np.isnan(r.total_co)], expected[~np.isnan(expected)], atol=1e-9)


def test_inclusion_rule(golden):
    t, r, _ = golden
    by_nim = dict(zip(t.nims, r.included))
    assert by_nim["9999000003"] is np.False_        # all blank -> excluded
    assert by_nim["TEST-0005"] is np.True_           # all zero -> counted
    assert r.total_co[t.nims.index("TEST-0005")] == 0


def test_checks_match_periksa(golden):
    t, r, wb = golden
    periksa = wb["Periksa"]
    excel = {row: periksa.cell(row, 3).value == "OK" for row in range(8, 21)}
    ours = {c["id"]: c["ok"] for c in run_checks(t, r)}
    assert {k: ours[k] for k in excel} == excel
    assert ours["extra-1"] and ours["extra-2"]


def test_class_attainment_matches_periksa(golden):
    t, r, wb = golden
    periksa = wb["Periksa"]
    # Excel menulis CPL-C; kode dibaca tanpa awalan, sama dengan Data prodi (pemilik 2026-11-14).
    expected = [{"cpl": norm_cpl(periksa.cell(row, 1).value), "counted": periksa.cell(row, 2).value,
                 "above_threshold": periksa.cell(row, 3).value, "status": periksa.cell(row, 5).value}
                for row in range(31, 43) if periksa.cell(row, 1).value]
    got = class_attainment(t, r, threshold_student=45, threshold_class_pct=60)
    assert [{k: g[k] for k in ("cpl", "counted", "above_threshold", "status")} for g in got] == expected


def _mutated(tmp_path, edit):
    wb = openpyxl.load_workbook(GOLDEN)
    edit(wb)
    p = tmp_path / "mutated.xlsx"
    wb.save(p)
    t = read_template(p)
    return t, {c["id"]: c for c in run_checks(t, compute(t))}


def test_text_score_is_flagged(tmp_path):
    _, checks = _mutated(tmp_path, lambda wb: wb["Nilai"].cell(5, 3).__setattr__("value", "85"))
    assert not checks["extra-1"]["ok"]


def test_duplicate_nim_is_flagged(tmp_path):
    _, checks = _mutated(tmp_path, lambda wb: wb["Nilai"].cell(8, 1).__setattr__("value", "9999000001"))
    assert not checks[19]["ok"]


def test_weight_total_not_100_is_flagged(tmp_path):
    _, checks = _mutated(tmp_path, lambda wb: wb["Bobot_Butir"].cell(5, 3).__setattr__("value", 5))
    assert not checks[8]["ok"]


def test_missing_class_is_flagged(tmp_path):
    _, checks = _mutated(tmp_path, lambda wb: wb["Info"].cell(12, 2).__setattr__("value", None))
    assert not checks[20]["ok"] and "Kelas" in checks[20]["value"]


def test_parent_code_case_insensitive(tmp_path, golden):
    _, r_ref, _ = golden

    def lower_parent(wb):
        ws = wb["Bobot_Butir"]
        ws.cell(5, 2).value = ws.cell(5, 2).value.lower()
    t, checks = _mutated(tmp_path, lower_parent)
    r = compute(t)
    np.testing.assert_allclose(np.nan_to_num(r.cpl), np.nan_to_num(r_ref.cpl), atol=1e-12)
    assert checks[14]["ok"]
