"""Fill the master CPL template with fictitious data for the golden test.

Step 1 of 2. Writes tests/data/golden_example.xlsx with inputs only; the
formula sheets have no cached values yet. Step 2, recalc_excel.ps1, opens
the file in Excel, recalculates and saves it, so the Hasil sheet carries
Excel's own numbers. tests/test_cpl.py compares the Python recompute
against those numbers.

Run again only when the template version changes:
    python tests/data/make_golden.py
    powershell -File tests/data/recalc_excel.ps1

All names and NIMs are fictitious.
"""
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "templates" / "Template_Input_Data_CPL.xlsx"
GOLDEN = Path(__file__).resolve().parent / "golden_example.xlsx"

# How each CPMK's total weight is split over indicators (fractions sum to 1).
# CPL-I receives weight from two CPMK on purpose.
SPLIT = {
    "CPMK-1": {"G1": 0.75, "C1": 0.25},
    "CPMK-2": {"J1": 2 / 3, "I1": 1 / 3},
    "CPMK-3": {"I2": 0.6, "E1": 0.4},
}

# Extra fictitious students; None = blank cell. One value per assessment item
# in Bobot_Butir order (the template example has 8 items).
EXTRA = [
    ("TEST-0004", "Uji - satu sel kosong", [90, None, 70, 80, 75, 85, 60, 88]),
    ("TEST-0005", "Uji - semua nol", [0, 0, 0, 0, 0, 0, 0, 0]),
    ("TEST-0006", "Uji - hanya UTS", [None, None, None, None, None, None, None, 72]),
    ("TEST-0007", "Uji - desimal", [77.5, 66.25, 91.75, 58.5, 63.0, 70.4, 81.2, 69.9]),
]


def main():
    wb = openpyxl.load_workbook(TEMPLATE)
    info, rum = wb["Info"], wb["Rumusan"]
    bb, bi, nl = wb["Bobot_Butir"], wb["Bobot_Indikator"], wb["Nilai"]

    info["B6"] = 3
    info["B10"] = "Dosen Contoh (fiktif)"
    info["B11"] = "2026-10-09"
    info["B12"] = "A"

    items = [bb.cell(4, c).value for c in range(3, 53)]
    n_items = sum(1 for v in items if v not in (None, ""))

    # Expected Bobot_Indikator row total per CPMK = sum of its Sub-CPMK weights.
    totals = {}
    for r in range(5, 55):
        parent = bb.cell(r, 2).value
        if parent:
            row_sum = sum(bb.cell(r, c).value or 0 for c in range(3, 53))
            totals[parent] = totals.get(parent, 0) + row_sum

    indicator_col = {rum.cell(21 + k, 1).value: 2 + k for k in range(40)
                     if rum.cell(21 + k, 1).value}
    cpmk_row = {rum.cell(64 + k, 1).value: 5 + k for k in range(10)
                if rum.cell(64 + k, 1).value}
    for cpmk, parts in SPLIT.items():
        for ind, frac in parts.items():
            bi.cell(cpmk_row[cpmk], indicator_col[ind]).value = round(totals[cpmk] * frac, 10)

    for i, (nim, name, scores) in enumerate(EXTRA):
        r = 8 + i
        assert nl.cell(r, 1).value in (None, ""), f"Nilai row {r} not empty"
        assert len(scores) == n_items
        nl.cell(r, 1).value = nim
        nl.cell(r, 2).value = name
        for j, v in enumerate(scores):
            nl.cell(r, 3 + j).value = v

    wb.save(GOLDEN)
    print(f"written {GOLDEN} (items={n_items}, CPMK totals={totals})")


if __name__ == "__main__":
    main()
