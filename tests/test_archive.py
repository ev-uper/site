"""Archive rules on fictitious files derived from the golden example.

Rules under test (config.yaml, owner decisions 2026-10-09): retake uses the
attempt with the highest Total CO, cumulative CPL is weighted by the
course's indicator weight, files that fail checks or repeat an identity are
left out, and the report never lands inside the repo.
"""
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
import pytest

from cpl import compute, read_template
from cpl.archive import build_report, load_folder
from cpl.config import load_config, validate_config

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = Path(__file__).parent / "data" / "golden_example.xlsx"
N_ITEMS = 8   # assessment items in the golden example


@pytest.fixture(scope="module")
def cfg():
    c = load_config(ROOT / "config.yaml")
    c.pop("paths", None)   # tests never use the machine's config.local.yaml paths
    return c


def make(folder, name, info=None, students=None, edit=None):
    """Copy the golden file with Info edits and, if given, a new Nilai block.

    students: list of (nim, [score per item]) replacing Nilai rows 5..124.
    """
    wb = openpyxl.load_workbook(GOLDEN)
    ws_info = wb["Info"]
    rows = {ws_info.cell(r, 1).value: r for r in range(4, 14)}
    for label, value in (info or {}).items():
        ws_info.cell(rows[label], 2).value = value
    if students is not None:
        nl = wb["Nilai"]
        for r in range(5, 125):
            for c in range(1, 3 + N_ITEMS):
                nl.cell(r, c).value = None
        for i, (nim, scores) in enumerate(students):
            nl.cell(5 + i, 1).value = nim
            for j, v in enumerate(scores):
                nl.cell(5 + i, 3 + j).value = v
    if edit:
        edit(wb)
    folder.mkdir(parents=True, exist_ok=True)
    wb.save(folder / name)


@pytest.fixture(scope="module")
def archive(tmp_path_factory, cfg):
    d = tmp_path_factory.mktemp("berkas")
    make(d, "a_41214_2425genap_A.xlsx")
    make(d, "b_41214_2526ganjil_A.xlsx",
         info={"Tahun Akademik": "2025/2026", "Semester": "Ganjil"},
         students=[("9999000002", [100] * N_ITEMS), ("9999000001", [50] * N_ITEMS)])
    make(d, "c_41299_2425genap_A.xlsx", info={"Kode MK": "41299", "Nama MK": "MK Uji"},
         students=[("9999000001", [80] * N_ITEMS)])
    make(d, "d_rusak.xlsx", info={"Kelas": "C"},
         edit=lambda wb: wb["Bobot_Butir"].cell(5, 3).__setattr__("value", 9))
    files = load_folder(d, cfg)
    return files, build_report(files, cfg)


def test_broken_file_left_out(archive):
    files, report = archive
    status = {f.path.name: f.ok for f in files}
    assert status == {"a_41214_2425genap_A.xlsx": True, "b_41214_2526ganjil_A.xlsx": True,
                      "c_41299_2425genap_A.xlsx": True, "d_rusak.xlsx": False}
    bad = report["files"].set_index("file").loc["d_rusak.xlsx"]
    assert not bad["used"] and "Total bobot butir asesmen = 100" in bad["problems"]


def test_retake_uses_highest_total_co(archive):
    _, report = archive
    att = report["student_attempts"].set_index(["course_code", "nim"])
    assert att.loc[("41214", "9999000002"), "file"] == "b_41214_2526ganjil_A.xlsx"   # 100 > 62.9
    assert att.loc[("41214", "9999000001"), "file"] == "a_41214_2425genap_A.xlsx"    # 93.5 > 50
    assert att.loc[("41214", "9999000001"), "attempts"] == 2


def test_cumulative_weighted_by_indicator(archive):
    _, report = archive
    t = read_template(GOLDEN)
    r = compute(t)
    k = t.cpl.index("G")
    s_a = r.cpl[t.nims.index("9999000001"), k]        # attempt a, course 41214
    w = r.w_cpmk_cpl.sum(axis=0)[k]                   # same weights in both courses
    expected = (s_a * w + 80 * w) / (w + w)           # course 41299: every score 80
    got = report["student_cpl"].set_index(["cpl", "nim"]).loc[("G", "9999000001")]
    assert got["courses"] == 2
    assert got["score"] == pytest.approx(expected, abs=1e-9)


def test_term_progress_ordered_with_change(archive):
    _, report = archive
    g = report["term_progress"]
    g = g[g["cpl"] == "G"]
    assert list(g["term"]) == ["2024/2025 Genap", "2025/2026 Ganjil"]
    assert np.isnan(g["change_share"].iloc[0]) and np.isfinite(g["change_share"].iloc[1])


def test_class_attainment_uses_config_thresholds(archive, cfg):
    _, report = archive
    ca = report["class_attainment"]
    assert set(ca["status"]) <= {"TERCAPAI", "BELUM"}
    na = report["not_achieved"]
    assert (na["status"] == "BELUM").all()
    assert (na["share"] < cfg["thresholds"]["class_pct"] / 100).all()


def test_duplicate_identity_rejected(tmp_path, cfg):
    make(tmp_path, "x1.xlsx")
    make(tmp_path, "x2.xlsx")
    files = load_folder(tmp_path, cfg)
    assert not any(f.ok for f in files)
    assert all("ganda" in "; ".join(f.problems) for f in files)


def test_unknown_semester_rejected(tmp_path, cfg):
    make(tmp_path, "p.xlsx", info={"Semester": "Antara"})
    (f,) = load_folder(tmp_path, cfg)
    assert not f.ok and any("Semester 'Antara' tidak dikenal" in p for p in f.problems)


def test_short_semester_accepted_after_even(tmp_path, cfg):
    # Semester pendek (pemilik 2026-11-14): sesudah Genap tahun akademik yang sama.
    make(tmp_path, "sp.xlsx", info={"Semester": "Pendek", "Tahun Akademik": "2025/2026"})
    (f,) = load_folder(tmp_path, cfg)
    assert f.ok and f.term_order == 20253


def test_unknown_template_version_rejected(tmp_path, cfg):
    make(tmp_path, "v.xlsx", info={"Versi templat": None})
    (f,) = load_folder(tmp_path, cfg)
    assert not f.ok and any("versi templat" in p for p in f.problems)


def test_output_inside_repo_refused(cfg):
    c = dict(cfg, paths={"input_dir": str(GOLDEN.parent), "output_dir": str(ROOT / "laporan")})
    errors = validate_config(c, ROOT)
    assert any(e.startswith("paths.output_dir") for e in errors)
    assert any(e.startswith("paths.input_dir") for e in errors)


def test_run_cpl_end_to_end(tmp_path):
    import run_cpl
    src, out = tmp_path / "in", tmp_path / "out"
    make(src, "a.xlsx")
    rc = run_cpl.main(["--input-dir", str(src), "--output-dir", str(out), "--source", "folder"])
    assert rc == 0
    sheets = pd.ExcelFile(out / "laporan_cpl.xlsx").sheet_names
    assert sheets[0] == "README" and "term_progress" in sheets and "not_achieved" in sheets
    assert "laporan" in (out / "run_cpl.log").read_text(encoding="utf-8")


# Ringkasan untuk situs (owner 2026-11-11, option 1): aggregate only, no NIM.
def test_summary_has_no_nim_and_keeps_aggregates(archive, cfg):
    import json
    from cpl.archive import summary
    files, report = archive
    s = summary(report, files, cfg, "2026-11-11T15:00:00+07:00")
    text = json.dumps(s)
    assert "9999000001" not in text and "9999000002" not in text and '"nim"' not in text
    assert s["versi"] == 1 and s["ambang"] == {"individu": 45, "kelas_persen": 60}
    assert {r["cpl"] for r in s["kumulatif"]} == set(report["cpl_cumulative"]["cpl"])
    assert len(s["kelas"]) == len(report["class_attainment"])
    assert all(set(r) <= {"curriculum", "course_code", "course_name", "class_name", "term", "term_order",
                          "cpl", "counted", "above_threshold", "share", "status", "estimate"} for r in s["kelas"])
    assert any(not b["used"] for b in s["berkas"]) and all("problems" not in b for b in s["berkas"])
    assert s["cpl"] and all(r["text"] for r in s["cpl"])            # descriptions read from Rumusan


def test_summary_refuses_to_leak_nim(archive, cfg):
    from cpl.archive import summary
    files, report = archive
    bad = dict(report)
    bad["cpl_cumulative"] = report["cpl_cumulative"].assign(curriculum="9999000001")
    with pytest.raises(ValueError):
        summary(bad, files, cfg, "x")


def test_run_cpl_writes_summary(tmp_path):
    import json
    import run_cpl
    src, out = tmp_path / "in", tmp_path / "out"
    make(src, "a.xlsx")
    assert run_cpl.main(["--input-dir", str(src), "--output-dir", str(out), "--source", "folder"]) == 0
    s = json.loads((out / "ringkasan_cpl.json").read_text(encoding="utf-8"))
    assert s["kumulatif"] and s["kelas"]
    assert "ringkasan" in (out / "run_cpl.log").read_text(encoding="utf-8")
