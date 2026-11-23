#!/usr/bin/env python3
"""Build site/lkps-outline.json from the LAM LKPS template (owner 2026-11-05).

    python tools/make_lkps_outline.py

site/lkps-tabel.js builds the programme's own LKPS workbook for copy-paste into
the LAM template. Values keep the template's cell addresses, so the workbook
only needs the template's frame:

    wajib   [{nama, judul}] tables ticked for Sarjana in sheet Daftar Tabel, in order
    lembar  per sheet:
      judul     sheet title (cell A1)
      label     {cell: text} constants of the table: headers, row names, column numbers
      rumus     cells holding a formula: copy blocks must never cover these
      gabung    merged ranges, "B7:C7", without those only partly open for input
      ketik     top-left cells of those partly open merges (Menu H7:X7): Excel refuses
                any paste there, so these values are typed
      boleh     the template's editable ranges (protected ranges); all else is locked
      grid      editable ranges of the Sarjana part, drawn as the table body
      batas     last column of the table; beyond it are INFO boxes and helper lists
      sembunyi  [[first, last]] rows hidden in the template (helper lists) and rows of
                other study levels (6d, 6f1)
      lebar     {column: width}, 0 = hidden
      tinggi    {row: height}

Run again only when LAM publishes a new template. Needs openpyxl.
"""
from __future__ import annotations

import json
import re
import warnings
import zipfile
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter, range_boundaries

AKAR = Path(__file__).resolve().parents[1]
TEMPLAT = AKAR / "site" / "lkps-template.xlsx"
KELUAR = AKAR / "site" / "lkps-outline.json"

# Index of tables and navigation links carry no data to copy.
LEMBAR_DILEWATI = {"Daftar Tabel"}
TEKS_DILEWATI = {"<<< Daftar Tabel"}
VERSI = 2                                     # shape of this file, checked by site/lkps-tabel.js
JENJANG = "S"                                 # column header in Daftar Tabel: Sarjana
BAGIAN_JENJANG = re.compile(r"Sarjana(?! Terapan)")


def lebar_kolom(ws) -> dict[str, float]:
    """Column widths; openpyxl stores a run of equal columns under its first letter."""
    hasil = {}
    for dim in ws.column_dimensions.values():
        if not dim.min or not (dim.width or dim.hidden):
            continue
        for i in range(dim.min, min(dim.max, 40) + 1):
            hasil[get_column_letter(i)] = 0 if dim.hidden else round(dim.width, 1)
    return hasil


def rentang_boleh(zf: zipfile.ZipFile) -> dict[str, list[str]]:
    """Editable ranges per sheet. openpyxl does not read <protectedRanges>."""
    wb = zf.read("xl/workbook.xml").decode("utf-8")
    rels = {}
    for m in re.findall(r"<Relationship [^>]*>", zf.read("xl/_rels/workbook.xml.rels").decode("utf-8")):
        rels[re.search(r' Id="([^"]+)"', m)[1]] = re.search(r' Target="([^"]+)"', m)[1]
    hasil = {}
    for m in re.findall(r"<sheet [^>]*>", wb):
        nama = re.search(r' name="([^"]+)"', m)[1].replace("&amp;", "&")
        target = rels[re.search(r' r:id="([^"]+)"', m)[1]].lstrip("/").removeprefix("xl/")
        xml = zf.read("xl/" + target).decode("utf-8")
        hasil[nama] = " ".join(re.findall(r'<protectedRange [^>]*?sqref="([^"]+)"', xml)).split()
    return hasil


def gabungan_utuh(ws, boleh: list[str]) -> tuple[list[str], list[str]]:
    """Merged ranges, and the top-left cells of merges only partly open for input."""
    kotak = [range_boundaries(r) for r in boleh]

    def terbuka(k, b):
        return any(k1 <= k <= k2 and b1 <= b <= b2 for k1, b1, k2, b2 in kotak)

    hasil, ketik = [], []
    for r in ws.merged_cells.ranges:
        sel = [(k, b) for k in range(r.min_col, r.max_col + 1) for b in range(r.min_row, r.max_row + 1)]
        if not terbuka(*sel[0]) or all(terbuka(k, b) for k, b in sel):
            hasil.append(str(r))
        else:
            ketik.append(str(r).split(":")[0])
    return sorted(hasil), sorted(ketik)


def bagian_lain(teks: dict[tuple[int, int], str], baris_akhir: int) -> list[list[int]]:
    """Row spans of the parts for other study levels, when a sheet has several parts."""
    awal = sorted(b for (k, b), t in teks.items() if k == 1 and t.startswith("Diisi oleh"))
    if len(awal) < 2:
        return []
    hasil = []
    for i, b in enumerate(awal):
        akhir = awal[i + 1] - 1 if i + 1 < len(awal) else baris_akhir
        if not BAGIAN_JENJANG.search(teks[(1, b)]):
            hasil.append([b, akhir])
    return hasil


def tabel_tampil(ws, boleh, sembunyi, teks):
    """Editable ranges outside hidden rows, and the last column of the table:
    the widest range, extended by headers that continue right of it (formula columns)."""
    tersembunyi = lambda b: any(a <= b <= z for a, z in sembunyi)
    grid = [r for r in boleh if not tersembunyi(range_boundaries(r)[1])]
    if not grid:
        return grid, ws.max_column
    kotak = [range_boundaries(r) for r in grid]
    batas, baris1 = max(k[2] for k in kotak), min(k[1] for k in kotak)
    info = min((k for (k, b), t in teks.items() if t.upper() == "INFO"), default=10 ** 6)
    while batas + 1 < info and any(b < baris1 and k == batas + 1 for (k, b) in teks):
        batas += 1
    return grid, batas


def rentang_baris(baris: set[int]) -> list[list[int]]:
    """Sorted row numbers as [[first, last]] runs."""
    hasil = []
    for b in sorted(baris):
        if hasil and hasil[-1][1] == b - 1:
            hasil[-1][1] = b
        else:
            hasil.append([b, b])
    return hasil


def kerangka(ws, boleh: list[str]) -> dict:
    teks, angka, rumus = {}, {}, []
    gabung, ketik = gabungan_utuh(ws, boleh)
    for baris in ws.iter_rows():
        for sel in baris:
            v = sel.value
            if sel.data_type == "f":         # array formulas are objects, not "=..." text
                rumus.append(sel.coordinate)
            elif isinstance(v, str) and v.strip() and v.strip() not in TEKS_DILEWATI:
                teks[(sel.column, sel.row)] = v.strip()
            elif isinstance(v, int) and not isinstance(v, bool):
                angka[(sel.column, sel.row)] = str(v)        # column numbers under a header
    akhir = max((b for _, b in teks), default=1)
    tutup = {b for b, d in ws.row_dimensions.items() if d.hidden and b <= akhir}
    for a, z in bagian_lain(teks, akhir):
        tutup |= set(range(a, z + 1))
    sembunyi = rentang_baris(tutup)
    teks = {kb: t for kb, t in teks.items() if kb[1] not in tutup}
    grid, batas = tabel_tampil(ws, boleh, sembunyi, teks)
    tersembunyi = lambda b: b in tutup
    kotak = [range_boundaries(r) for r in boleh]
    isian = lambda k, b: any(k1 <= k <= k2 and b1 <= b <= b2 for k1, b1, k2, b2 in kotak)
    teks |= {kb: t for kb, t in angka.items() if kb[1] not in tutup and not isian(*kb)}
    label = {f"{get_column_letter(k)}{b}": t for (k, b), t in teks.items() if k <= batas}
    tinggi = {b: round(d.height, 1) for b, d in ws.row_dimensions.items()
              if d.height and b <= 200 and not tersembunyi(b)}
    return {"judul": str(ws["A1"].value or ws.title).strip(), "label": label, "rumus": rumus,
            "gabung": gabung, "ketik": ketik, "boleh": boleh, "grid": grid, "batas": batas,
            "sembunyi": sembunyi, "lebar": lebar_kolom(ws), "tinggi": tinggi}


def daftar_wajib(ws) -> list[dict]:
    """Tables ticked for the study level in sheet Daftar Tabel, in order."""
    kolom = next(c.column for c in ws[3] if c.value == JENJANG)
    hasil = []
    for b in range(4, ws.max_row + 1):
        if ws.cell(b, kolom).value == "√":
            hasil.append({"nama": str(ws.cell(b, 3).value).strip(), "judul": str(ws.cell(b, 2).value).strip()})
    return hasil


def main() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")      # x14 validations: not needed here
        wb = openpyxl.load_workbook(TEMPLAT)
    with zipfile.ZipFile(TEMPLAT) as zf:
        boleh = rentang_boleh(zf)
    hasil = {"versi": VERSI, "wajib": daftar_wajib(wb["Daftar Tabel"]),
             "lembar": {ws.title: kerangka(ws, boleh.get(ws.title, [])) for ws in wb
                        if ws.title not in LEMBAR_DILEWATI}}
    teks = json.dumps(hasil, ensure_ascii=False, separators=(",", ":"))
    KELUAR.write_text(teks + "\n", encoding="utf-8", newline="\n")
    print(f"{KELUAR.name}: {len(hasil['wajib'])} tabel wajib, {len(hasil['lembar'])} lembar, "
          f"{len(teks) // 1024} KiB, {sum(len(x['rumus']) for x in hasil['lembar'].values())} rumus")


if __name__ == "__main__":
    main()
