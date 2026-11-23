"""Read the input cells of one filled CPL template (one class, one semester).

Only cells a lecturer types are read. Header cells in Bobot_Butir,
Bobot_Indikator and Nilai are formulas pointing at Rumusan, so every code is
read from Rumusan itself. The formula sheets (Turunan, Hasil, Periksa) are
never trusted here: a workbook saved by a tool other than Excel carries no
cached values, and an inserted column breaks the formulas silently
(Petunjuk rows 17-18). compute.py recomputes the whole chain instead.

Cell layout below is the fixed slot layout of the template
(Petunjuk rows 15-16), checked against template version CPL-2026.10.09.
"""
from dataclasses import dataclass, field
from pathlib import Path
import re
import warnings

import numpy as np
import openpyxl

N_ITEM, N_SUB, N_CPMK, N_IND, N_CPL, N_STUDENT = 50, 50, 10, 40, 12, 120

# Rumusan: first row of each code block, column A = code, column B = text.
ROW_CPL, ROW_IND, ROW_CPMK, ROW_SUB = 6, 21, 64, 77
# Bobot_Butir: item names row 4 from column C; Sub-CPMK rows 5.. (column B = parent CPMK).
BB_HEADER_ROW, BB_FIRST_ROW, BB_FIRST_COL = 4, 5, 3
# Bobot_Indikator: CPMK rows 5.., indicator columns from B.
BI_FIRST_ROW, BI_FIRST_COL = 5, 2
# Nilai: student rows 5.., NIM in A, scores from C.
NL_FIRST_ROW, NL_FIRST_COL = 5, 3
# Periksa: per-file thresholds (informative only; analysis thresholds live in config).
PR_THRESHOLD_STUDENT, PR_THRESHOLD_CLASS = "B4", "B5"


@dataclass
class Template:
    """Raw inputs of one workbook. Empty slots keep their position as ''."""
    path: Path
    info: dict             # Info sheet: label -> value
    cpl: list              # CPL codes (N_CPL)
    indicators: list       # indicator codes (N_IND)
    indicator_cpl: list    # parent CPL code of each indicator (N_IND)
    cpmk: list             # CPMK codes (N_CPMK)
    subs: list             # Sub-CPMK codes (N_SUB)
    sub_parent: list       # parent CPMK typed in Bobot_Butir column B (N_SUB)
    items: list            # assessment item names (N_ITEM)
    w_sub_item: np.ndarray   # (N_SUB, N_ITEM) weights, blank = 0
    w_cpmk_ind: np.ndarray   # (N_CPMK, N_IND) weights, blank = 0
    nims: list             # NIM per student row as text, '' when blank (N_STUDENT)
    scores: np.ndarray     # (N_STUDENT, N_ITEM) numbers, NaN when blank or not a number
    score_text: list       # (row, col, value) of score cells holding text, which Excel counts as 0
    weight_text: list      # (sheet, cell, value) of weight cells holding text
    file_thresholds: tuple  # (individual %, class %) as typed in Periksa
    cpl_text: list = field(default_factory=list)  # CPL description, Rumusan column B (N_CPL)


def _text(v):
    """Cell value as stripped text; None -> ''. Whole floats lose '.0' (NIM typed as number)."""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def norm_cpl(code):
    """Kode CPL tanpa awalan "CPL": "CPL-A", "CPL A" -> "A" (huruf asli tetap), sama dengan normCpl di
    site/kurikulum-cpl.js; templat menulis CPL-A, Data prodi (ref_cpl, ref_mk_cpl) menulis A (pemilik 2026-11-14)."""
    return re.sub(r"^cpl[\s_.-]*", "", code, flags=re.I)


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _weights(ws, sheet, first_row, first_col, n_rows, n_cols, text_cells):
    out = np.zeros((n_rows, n_cols))
    for i in range(n_rows):
        for j in range(n_cols):
            cell = ws.cell(first_row + i, first_col + j)
            v = cell.value
            if _is_number(v):
                out[i, j] = v
            elif v not in (None, ""):
                text_cells.append((sheet, cell.coordinate, v))
    return out


def read_template(path) -> Template:
    path = Path(path)
    with warnings.catch_warnings():
        # Excel stores cross-sheet list validation as an extension openpyxl skips; harmless for reading.
        warnings.filterwarnings("ignore", message="Data Validation extension")
        wb = openpyxl.load_workbook(path, data_only=False)

    info_ws, rum = wb["Info"], wb["Rumusan"]
    info = {}
    for r in range(4, info_ws.max_row + 1):
        label = _text(info_ws.cell(r, 1).value)
        if label:
            info[label] = info_ws.cell(r, 2).value

    def codes(first_row, n, col=1):
        return [_text(rum.cell(first_row + k, col).value) for k in range(n)]

    bb, bi, nl, pr = wb["Bobot_Butir"], wb["Bobot_Indikator"], wb["Nilai"], wb["Periksa"]
    weight_text = []
    w_sub_item = _weights(bb, "Bobot_Butir", BB_FIRST_ROW, BB_FIRST_COL, N_SUB, N_ITEM, weight_text)
    w_cpmk_ind = _weights(bi, "Bobot_Indikator", BI_FIRST_ROW, BI_FIRST_COL, N_CPMK, N_IND, weight_text)

    scores = np.full((N_STUDENT, N_ITEM), np.nan)
    score_text = []
    nims = []
    for i in range(N_STUDENT):
        r = NL_FIRST_ROW + i
        nims.append(_text(nl.cell(r, 1).value))
        for j in range(N_ITEM):
            v = nl.cell(r, NL_FIRST_COL + j).value
            if _is_number(v):
                scores[i, j] = v
            elif v not in (None, ""):
                score_text.append((r, NL_FIRST_COL + j, v))

    return Template(
        path=path,
        info=info,
        cpl=[norm_cpl(c) for c in codes(ROW_CPL, N_CPL)],
        cpl_text=codes(ROW_CPL, N_CPL, col=2),
        indicators=codes(ROW_IND, N_IND),
        indicator_cpl=[norm_cpl(c) for c in codes(ROW_IND, N_IND, col=2)],
        cpmk=codes(ROW_CPMK, N_CPMK),
        subs=codes(ROW_SUB, N_SUB),
        sub_parent=[_text(bb.cell(BB_FIRST_ROW + k, 2).value) for k in range(N_SUB)],
        items=[_text(bb.cell(BB_HEADER_ROW, BB_FIRST_COL + j).value) for j in range(N_ITEM)],
        w_sub_item=w_sub_item,
        w_cpmk_ind=w_cpmk_ind,
        nims=nims,
        scores=scores,
        score_text=score_text,
        weight_text=weight_text,
        file_thresholds=(pr[PR_THRESHOLD_STUDENT].value, pr[PR_THRESHOLD_CLASS].value),
    )
