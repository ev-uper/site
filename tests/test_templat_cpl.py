"""Templat nilai CPL diisi situs (site/templat-cpl.js, JSZip) pulang-pergi (pemilik 2026-11-17, OBE O2).

Struktur contoh di templat resmi dibaca dengan cpl.template.read_template, diisikan lagi lewat pengisi situs,
lalu hasilnya dibaca ulang: semua sel isian dan hasil hitung CPL (dengan nilai mahasiswa yang sama) harus sama,
dan lembar selain lima lembar isian harus identik byte demi byte.
"""
import json
import shutil
import subprocess
import warnings
import zipfile
from pathlib import Path

import numpy as np
import openpyxl
import pytest

from cpl.compute import compute
from cpl.template import read_template, ROW_IND, ROW_CPMK, ROW_SUB, N_IND, N_CPMK, N_SUB

ROOT = Path(__file__).resolve().parent.parent
TEMPLAT = ROOT / "site" / "Template_Input_Data_CPL.xlsx"
ADA = shutil.which("node") and (ROOT / "tools" / "node_modules" / "jszip").is_dir()
pytestmark = pytest.mark.skipif(not ADA, reason="node atau tools/node_modules/jszip tidak ada (npm install --prefix tools)")


def struktur_contoh():
    """Struktur {d, info} dari isian contoh templat resmi."""
    t = read_template(TEMPLAT)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        rum = openpyxl.load_workbook(TEMPLAT)["Rumusan"]
    teks = lambda r, c: str(rum.cell(r, c).value or "").strip()
    ind = [{"kode": t.indicators[j], "cpl": t.indicator_cpl[j], "teks": teks(ROW_IND + j, 3)}
           for j in range(N_IND) if t.indicators[j]]
    cpmk = [{"kode": t.cpmk[i], "rumusan": teks(ROW_CPMK + i, 2),
             "indikator": {t.indicators[j]: float(t.w_cpmk_ind[i, j]) for j in range(N_IND) if t.indicators[j] and t.w_cpmk_ind[i, j]}}
            for i in range(N_CPMK) if t.cpmk[i]]
    # Isian contoh templat belum memetakan CPMK ke indikator (Bobot_Indikator kosong): uji memberi pemetaan buatan
    # (CPMK ke-i -> indikator ke-i dan ke-(i+1), bobot 1 dan 0,5), lalu membandingkan dengan pemetaan yang sama.
    kode_ind = [x["kode"] for x in ind]
    for i, c in enumerate(cpmk):
        if not c["indikator"]:
            c["indikator"] = {kode_ind[i % len(kode_ind)]: 1.0, kode_ind[(i + 1) % len(kode_ind)]: 0.5}
            for k, w in c["indikator"].items():
                t.w_cpmk_ind[t.cpmk.index(c["kode"]), t.indicators.index(k)] = w
    item = [x for x in t.items if x]
    sub = [{"kode": t.subs[i], "cpmk": t.sub_parent[i], "rumusan": teks(ROW_SUB + i, 2)} for i in range(N_SUB) if t.subs[i]]
    bobot = {t.subs[i]: {t.items[j]: float(t.w_sub_item[i, j]) for j in range(len(t.items)) if t.items[j] and t.w_sub_item[i, j]}
             for i in range(N_SUB) if t.subs[i]}
    d = {"cpl": [{"kode": c, "rumusan": x} for c, x in zip(t.cpl, t.cpl_text) if c],
         "indikator": ind, "cpmk": cpmk, "sub": sub, "asesmen": [{"nama": x} for x in item], "bobot": bobot}
    info = {"kode_mk": "SI101", "nama_mk": "Uji templat", "sks": 3, "semester": "Ganjil", "tahun_akademik": "2026/2027",
            "kurikulum": "K26", "dosen": "Dosen Uji", "kelas": "A"}
    return t, d, info


@pytest.fixture(scope="module")
def hasil(tmp_path_factory):
    t, d, info = struktur_contoh()
    p = tmp_path_factory.mktemp("templat")
    (p / "masuk.json").write_text(json.dumps({"d": d, "info": info}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run(["node", str(ROOT / "tools" / "isi_templat_cpl.mjs"), str(TEMPLAT), str(p / "masuk.json"), str(p / "keluar.xlsx")],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-2000:]
    return t, read_template(p / "keluar.xlsx"), p / "keluar.xlsx", info


def test_input_cells_round_trip(hasil):
    asli, baru, _, info = hasil
    for f in ("cpl", "cpl_text", "indicators", "indicator_cpl", "cpmk", "subs", "sub_parent", "items"):
        assert getattr(baru, f) == getattr(asli, f), f
    assert np.array_equal(baru.w_sub_item, asli.w_sub_item)
    assert np.array_equal(baru.w_cpmk_ind, asli.w_cpmk_ind)
    assert baru.nims == [""] * len(asli.nims) and np.isnan(baru.scores).all()        # contoh nilai dikosongkan
    assert baru.info["Kode MK"] == "SI101" and baru.info["Kelas"] == "A" and baru.info["SKS"] == 3
    assert baru.info["Tahun Akademik"] == "2026/2027" and baru.info["Tanggal pengisian"] is None


def test_cpl_computation_identical_with_same_scores(hasil):
    asli, baru, _, _ = hasil
    baru.nims, baru.scores = asli.nims, asli.scores
    a, b = compute(asli), compute(baru)
    for f in ("included", "sub", "cpmk", "indicator", "cpl", "total_co"):
        assert np.array_equal(getattr(a, f), getattr(b, f), equal_nan=True), f


def test_other_parts_of_workbook_unchanged(hasil):
    _, _, keluar, _ = hasil
    za, zb = zipfile.ZipFile(TEMPLAT), zipfile.ZipFile(keluar)
    assert sorted(za.namelist()) == sorted(zb.namelist())
    diubah = {f"xl/worksheets/sheet{i}.xml" for i in (2, 3, 4, 5, 6)}   # Info, Rumusan, Bobot_Butir, Bobot_Indikator, Nilai
    for n in za.namelist():
        if n not in diubah:
            assert za.read(n) == zb.read(n), n
    # Rumus di lembar isian tetap ada (mis. kolom A Bobot_Butir dan judul Bobot_Indikator).
    for n in diubah:
        assert za.read(n).count(b"<f>") == zb.read(n).count(b"<f>"), n
