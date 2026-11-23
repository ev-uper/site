"""Checks that a filled template is usable, before its numbers enter the archive.

Checks 8-20 mirror the rows of the Periksa sheet (template CPL-2026.10.09),
same wording, so a lecturer recognises the message. Checks marked "extra"
are not in the workbook: Excel silently counts a text cell as 0 in
SUMPRODUCT, so a score typed as text would never show up there.
"""
import numpy as np

from .compute import Result
from .template import Template

TOL = 0.01  # same tolerance as the Periksa formulas (ABS(...)<0.01)

INFO_REQUIRED = ["Kode MK", "Nama MK", "SKS", "Semester", "Tahun Akademik",
                 "Kurikulum", "Dosen Koordinator", "Tanggal pengisian", "Kelas"]


def _same(a, b):
    return a.casefold() == b.casefold()


def run_checks(t: Template, r: Result):
    """Return a list of {id, label, value, ok}. All ok -> the file may be archived."""
    out = []

    def add(cid, label, value, ok):
        out.append({"id": cid, "label": label, "value": value, "ok": bool(ok)})

    sub_total = t.w_sub_item.sum(axis=1)
    item_total = t.w_sub_item.sum(axis=0)
    ind_total = t.w_cpmk_ind.sum(axis=0)

    total = float(t.w_sub_item.sum())
    add(8, "Total bobot butir asesmen = 100", total, abs(total - 100) < TOL)

    total_ind = float(t.w_cpmk_ind.sum())
    add(9, "Total bobot CPMK ke Indikator = 100", total_ind, abs(total_ind - 100) < TOL)

    mismatch = sum(1 for c, code in enumerate(t.cpmk) if code
                   and abs(t.w_cpmk_ind[c].sum() - r.w_cpmk_item[c].sum()) >= TOL)
    add(10, "Tiap baris Bobot_Indikator cocok dengan total Sub-CPMK CPMK itu", mismatch, mismatch == 0)

    n = sum(1 for s, code in enumerate(t.subs) if bool(code) != (sub_total[s] > 0))
    add(11, "Tiap Sub-CPMK berkode punya bobot, dan sebaliknya", n, n == 0)

    n = sum(1 for j, name in enumerate(t.items) if bool(name) != (item_total[j] > 0))
    add(12, "Tiap butir bernama punya bobot, dan sebaliknya", n, n == 0)

    n = sum(1 for s, code in enumerate(t.subs) if code and not t.sub_parent[s])
    add(13, "Tiap Sub-CPMK berkode punya Induk CPMK", n, n == 0)

    known = [c for c in t.cpmk if c]
    n = sum(1 for p in t.sub_parent if p and not any(_same(p, c) for c in known))
    add(14, "Induk CPMK yang dipakai terdaftar di Rumusan", n, n == 0)

    n = sum(1 for i, code in enumerate(t.indicators) if not code and ind_total[i] > 0)
    add(15, "Bobot indikator hanya pada kolom indikator yang terdaftar", n, n == 0)

    n = sum(1 for i, code in enumerate(t.indicators) if code and not t.indicator_cpl[i])
    add(16, "Tiap indikator berkode punya CPL induk", n, n == 0)

    s = t.scores[np.isfinite(t.scores)]
    n = int(((s > 100) | (s < 0)).sum())
    add(17, "Seluruh nilai berada di rentang 0-100", n, n == 0)

    counted = np.isfinite(t.scores).sum(axis=0)
    n = sum(1 for j, name in enumerate(t.items) if not name and counted[j] > 0)
    add(18, "Tidak ada nilai pada kolom butir yang tidak bernama", n, n == 0)

    nims = [x.casefold() for x in t.nims if x]
    n = len(nims) - len(set(nims))
    add(19, "Tidak ada NIM ganda", n, n == 0)

    blank = [k for k in INFO_REQUIRED if t.info.get(k) in (None, "")]
    add(20, "Identitas mata kuliah terisi lengkap (termasuk Kurikulum dan Kelas)",
        ", ".join(blank) or 0, not blank)

    add("extra-1", "Tidak ada nilai berupa teks (Excel menghitungnya 0 tanpa pesan)",
        len(t.score_text), not t.score_text)
    add("extra-2", "Tidak ada bobot berupa teks (Excel menghitungnya 0 tanpa pesan)",
        len(t.weight_text), not t.weight_text)
    return out


def all_ok(checks):
    return all(c["ok"] for c in checks)
