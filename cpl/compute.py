"""Recompute the template chain: item -> Sub-CPMK -> CPMK -> indicator -> CPL.

Mirrors the formulas of the Turunan and Hasil sheets (template
CPL-2026.10.09) exactly, so results match Excel to floating-point precision:

  Turunan B6:AY15   w(CPMK, item) = SUMIF over Sub-CPMK whose parent is that CPMK
  Turunan B62:K73   w(CPMK, CPL)  = SUMIF over indicators whose parent is that CPL
  Hasil B:AY        Sub-CPMK  = SUMPRODUCT(scores, w_sub)  / SUM(w_sub)
  Hasil AZ:BI       CPMK      = SUMPRODUCT(scores, w_cpmk) / SUM(w_cpmk)
  Hasil BJ:CW       indicator = SUMPRODUCT(CPMK, w_ind)    / SUM(w_ind)
  Hasil CX:DI       CPL       = SUMPRODUCT(CPMK, w_cpl)    / SUM(w_cpl)
  Hasil DJ          Total CO  = SUMPRODUCT(CPMK, total w_cpmk) / SUM(total w_cpmk)

Excel behaviour kept on purpose:
  - SUMIF matches case-insensitively, and an empty code matches blank cells;
  - SUMPRODUCT counts blank and text cells as 0;
  - a zero denominator gives "" (NaN here) through IFERROR;
  - a student row counts only with a NIM and at least one numeric score
    (Petunjuk rows 41-47); other rows are NaN throughout.
"""
from dataclasses import dataclass

import numpy as np

from .template import Template


@dataclass
class Result:
    """Per-student scores (0-100) by slot. NaN = not computed (excluded row or untouched slot)."""
    included: np.ndarray    # (N_STUDENT,) bool
    sub: np.ndarray         # (N_STUDENT, N_SUB)
    cpmk: np.ndarray        # (N_STUDENT, N_CPMK)
    indicator: np.ndarray   # (N_STUDENT, N_IND)
    cpl: np.ndarray         # (N_STUDENT, N_CPL)
    total_co: np.ndarray    # (N_STUDENT,)
    w_cpmk_item: np.ndarray  # (N_CPMK, N_ITEM)  Turunan B6:AY15
    w_cpmk_cpl: np.ndarray   # (N_CPMK, N_CPL)   Turunan B62:K73, transposed


def _same(a, b):
    """SUMIF criterion match: case-insensitive equality; '' matches blank."""
    return a.casefold() == b.casefold()


def _ratio(num, den):
    """num / den column-wise; NaN where den == 0 (IFERROR -> "")."""
    out = np.full(num.shape, np.nan)
    ok = den != 0
    out[..., ok] = num[..., ok] / den[ok]
    return out


def compute(t: Template) -> Result:
    n_cpmk, n_cpl = len(t.cpmk), len(t.cpl)

    w_cpmk_item = np.array([
        t.w_sub_item[[_same(p, t.cpmk[c]) for p in t.sub_parent]].sum(axis=0)
        for c in range(n_cpmk)
    ])
    w_cpmk_cpl = np.array([
        [t.w_cpmk_ind[c, [_same(p, t.cpl[k]) for p in t.indicator_cpl]].sum()
         for k in range(n_cpl)]
        for c in range(n_cpmk)
    ])
    total_w_cpmk = w_cpmk_item.sum(axis=1)

    has_score = np.isfinite(t.scores).any(axis=1)
    included = np.array([bool(n) for n in t.nims]) & has_score
    x = np.nan_to_num(t.scores, nan=0.0)

    sub = _ratio(x @ t.w_sub_item.T, t.w_sub_item.sum(axis=1))
    cpmk = _ratio(x @ w_cpmk_item.T, total_w_cpmk)
    c0 = np.nan_to_num(cpmk, nan=0.0)
    indicator = _ratio(c0 @ t.w_cpmk_ind, t.w_cpmk_ind.sum(axis=0))
    cpl = _ratio(c0 @ w_cpmk_cpl, w_cpmk_cpl.sum(axis=0))
    total_co = _ratio((c0 @ total_w_cpmk)[:, None], np.array([total_w_cpmk.sum()]))[:, 0]

    for arr in (sub, cpmk, indicator, cpl):
        arr[~included] = np.nan
    total_co[~included] = np.nan

    return Result(included, sub, cpmk, indicator, cpl, total_co, w_cpmk_item, w_cpmk_cpl)


def class_attainment(t: Template, r: Result, threshold_student, threshold_class_pct):
    """Per CPL: students counted, students >= threshold, share, and TERCAPAI/BELUM.

    Mirrors Periksa rows 31-42: COUNT, COUNTIF(">="&threshold), share >= class %/100.
    Only CPL slots with a code and at least one computed score are returned.
    """
    rows = []
    for k, code in enumerate(t.cpl):
        col = r.cpl[:, k]
        n = int(np.isfinite(col).sum())
        if not code or n == 0:
            continue
        above = int((col[np.isfinite(col)] >= threshold_student).sum())
        share = above / n
        rows.append({
            "cpl": code,
            "counted": n,
            "above_threshold": above,
            "share": share,
            "status": "TERCAPAI" if share >= threshold_class_pct / 100 else "BELUM",
        })
    return rows
