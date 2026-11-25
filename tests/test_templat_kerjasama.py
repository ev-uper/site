"""Templat impor kerja sama (pemilik 2026-11-24): judul kolom dan pilihan di site/Templat_Kerja_Sama.xlsx sama dengan
site/impor-kerjasama.js dan site/manfaat-kerjasama.js; templat tanpa data."""
import re
from pathlib import Path

from openpyxl import load_workbook

AKAR = Path(__file__).resolve().parents[1]
JS = (AKAR / "site" / "impor-kerjasama.js").read_text(encoding="utf-8")
JS_BUKTI = (AKAR / "site" / "manfaat-kerjasama.js").read_text(encoding="utf-8")
WB = load_workbook(AKAR / "site" / "Templat_Kerja_Sama.xlsx")


def label_js(teks, nama):
    blok = re.search(r"export const " + nama + r" = \[(.*?)\];", teks, re.S).group(1)
    return [m[1] for m in re.findall(r"\['([^']+)', '([^']+)'\]", blok)]


def test_judul_kolom_sama_dengan_impor():
    kolom = re.findall(r"\['(\w+)', '([^']+)', (true|false)\]", re.search(r"export const KOLOM_KS = \[(.*?)\n\];", JS, re.S).group(1))
    ws = WB["Kerja sama"]
    judul = [c.value for c in ws[1]]
    assert judul == [k[1] for k in kolom]
    # Sel tanggal sudah berformat (max_row > 1), tetapi tidak boleh ada nilai: contoh hanya di Petunjuk.
    assert not [c.coordinate for r in ws.iter_rows(min_row=2) for c in r if c.value not in (None, "")]


def test_pilihan_sama_dengan_situs():
    pl = WB["Pilihan"]
    kol = {pl.cell(row=1, column=j).value: [pl.cell(row=r, column=j).value for r in range(2, pl.max_row + 1)
                                             if pl.cell(row=r, column=j).value] for j in range(1, pl.max_column + 1)}
    assert kol["jenis"] == label_js(JS, "JENIS_KS")
    assert kol["tingkat"] == label_js(JS, "TINGKAT_KS")
    assert kol["jenis_bukti"] == label_js(JS_BUKTI, "JENIS_BUKTI_KS")
    assert kol["sembunyikan_publik"] == label_js(JS, "YA_TIDAK")
    assert pl.sheet_state == "hidden"


def test_daftar_tarik_turun_terpasang():
    ws = WB["Kerja sama"]
    rumus = {dv.formula1 for dv in ws.data_validations.dataValidation if dv.type == "list"}
    assert len(rumus) == 4 and all(r.startswith("=Pilihan!") for r in rumus)
