"""Many course files -> CPL archive: retakes, cumulative CPL, term progress.

One file = one class of one course in one term (owner decision 2026-10-09).
A CPL is identified by (curriculum, code), never by code alone
(Petunjuk rows 20-26).

Rules (all from config.yaml):
  - a file enters the archive only if it reads, its template version is
    known, its identity is valid and unique, and every check passes;
  - retake = best_total_co: per (curriculum, course, NIM) the whole attempt
    with the highest Total CO is used; on a tie the latest term wins;
  - course_weight = indicator: a course's weight for a CPL is the sum of its
    Bobot_Indikator weights on that CPL's indicators;
  - thresholds.student / thresholds.class_pct decide TERCAPAI / BELUM.

Estimated rows from final course grades (final_grades.py, owner 2026-11-13) can be
added: they carry estimate=True and go through the same retake/cumulative/progress
rules; tables mark a CPL as estimate when every contributing row is an estimate.
"""
from dataclasses import dataclass, field
from pathlib import Path
import json
import re

import numpy as np
import pandas as pd

from .checks import run_checks
from .compute import class_attainment, compute
from .template import read_template

# Info sheet label -> identity field.
INFO_FIELDS = {
    "Kode MK": "course_code", "Nama MK": "course_name", "SKS": "credits",
    "Semester": "semester", "Tahun Akademik": "academic_year", "Kurikulum": "curriculum",
    "Dosen Koordinator": "coordinator", "Kelas": "class_name", "Versi templat": "template_version",
}
ACADEMIC_YEAR = re.compile(r"^(\d{4})/(\d{4})$")


@dataclass
class CourseFile:
    path: Path
    identity: dict = field(default_factory=dict)
    term: str = ""
    term_order: int = 0          # start_year * 10 + semester order; sorts terms
    template: object = None
    result: object = None
    checks: list = field(default_factory=list)
    problems: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.problems

    @property
    def key(self):
        i = self.identity
        return tuple(str(i.get(k, "")).casefold() for k in
                     ("curriculum", "course_code", "academic_year", "semester", "class_name"))


def _text(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def read_course_file(path, cfg) -> CourseFile:
    f = CourseFile(path=Path(path))
    try:
        t = read_template(f.path)
    except Exception as e:  # unreadable or not this template at all
        f.problems.append(f"tidak bisa dibaca sebagai templat CPL: {e}")
        return f
    f.template = t
    f.identity = {name: _text(t.info.get(label)) for label, name in INFO_FIELDS.items()}
    ident = f.identity

    if ident["template_version"] not in cfg["template_versions"]:
        f.problems.append(f"versi templat {ident['template_version'] or '(kosong)'!r} tidak dikenal; "
                          f"yang diterima: {', '.join(cfg['template_versions'])}")
    m = ACADEMIC_YEAR.match(ident["academic_year"])
    if not m or int(m.group(2)) != int(m.group(1)) + 1:
        f.problems.append(f"Tahun Akademik {ident['academic_year']!r} harus berbentuk 2024/2025")
    order = {str(k).casefold(): v for k, v in cfg["semester_order"].items()}
    sem = order.get(ident["semester"].casefold())
    if sem is None:
        f.problems.append(f"Semester {ident['semester']!r} tidak dikenal; "
                          f"yang dikenal: {', '.join(cfg['semester_order'])}")
    if m and sem is not None:
        f.term = f"{ident['academic_year']} {ident['semester']}"
        f.term_order = int(m.group(1)) * 10 + sem

    f.result = compute(t)
    f.checks = run_checks(t, f.result)
    f.problems += [f"pemeriksaan gagal: {c['label']} ({c['value']})" for c in f.checks if not c["ok"]]
    return f


def load_folder(folder, cfg):
    """Read every .xlsx under folder (Excel lock files ~$* skipped); flag duplicate identities."""
    paths = sorted(p for p in Path(folder).rglob("*.xlsx") if not p.name.startswith("~$"))
    files = [read_course_file(p, cfg) for p in paths]
    by_key = {}
    for f in files:
        if f.ok:
            by_key.setdefault(f.key, []).append(f)
    for group in by_key.values():
        if len(group) > 1:
            names = ", ".join(g.path.name for g in group)
            for g in group:
                g.problems.append(f"identitas (kurikulum, MK, tahun, semester, kelas) ganda: {names}")
    return files


def score_table(files):
    """Long table: one row per (file, student, CPL) with a score and the course weight for that CPL."""
    rows = []
    for f in files:
        if not f.ok:
            continue
        t, r, i = f.template, f.result, f.identity
        course_weight = r.w_cpmk_cpl.sum(axis=0)  # per CPL slot, from Bobot_Indikator
        for s in np.flatnonzero(r.included):
            for k, code in enumerate(t.cpl):
                if code and course_weight[k] > 0 and np.isfinite(r.cpl[s, k]):
                    rows.append({
                        "file": f.path.name, "curriculum": i["curriculum"],
                        "course_code": i["course_code"], "course_name": i["course_name"],
                        "class_name": i["class_name"], "term": f.term, "term_order": f.term_order,
                        "nim": t.nims[s], "total_co": float(r.total_co[s]),
                        "cpl": code, "score": float(r.cpl[s, k]), "weight": float(course_weight[k]),
                        "estimate": False,
                    })
    cols = ["file", "curriculum", "course_code", "course_name", "class_name", "term", "term_order",
            "nim", "total_co", "cpl", "score", "weight", "estimate"]
    return pd.DataFrame(rows, columns=cols)


def best_attempts(scores):
    """Per (curriculum, course, NIM): the attempt (file) with highest Total CO; tie -> latest term."""
    att = scores.drop_duplicates(["file", "nim"])[
        ["curriculum", "course_code", "nim", "file", "term", "term_order", "total_co"]]
    att = att.sort_values(["total_co", "term_order", "file"], ascending=[False, False, True])
    chosen = att.groupby(["curriculum", "course_code", "nim"], sort=False).head(1)
    n_attempts = att.groupby(["curriculum", "course_code", "nim"]).size().rename("attempts")
    return chosen.join(n_attempts, on=["curriculum", "course_code", "nim"]).reset_index(drop=True)


def _weighted(df, by):
    g = df.assign(sw=df["score"] * df["weight"]).groupby(by)
    out = (g["sw"].sum() / g["weight"].sum()).rename("score").to_frame()
    out["courses"] = g["course_code"].nunique()
    return out.reset_index()


def _summary(per_student, by, cfg):
    th = cfg["thresholds"]
    g = per_student.assign(achieved=per_student["score"] >= th["student"]).groupby(by)
    out = pd.DataFrame({"students": g["nim"].nunique(), "mean_score": g["score"].mean(),
                        "share_achieved": g["achieved"].mean()}).reset_index()
    out["status"] = np.where(out["share_achieved"] >= th["class_pct"] / 100, "TERCAPAI", "BELUM")
    return out


def _estimate_flag(df, scores, by):
    """Add column estimate = every contributing score row of the group is an estimate."""
    if df.empty:
        return df
    flag = scores.groupby(by)["estimate"].all().rename("estimate").reset_index()
    return df.merge(flag, on=by, how="left")


def cohort_of(nim, cfg):
    """Angkatan dari NIM (config cohort.digits, 1-based inklusif): '104122023' -> 2022. None bila tidak terbaca."""
    a, b = (cfg.get("cohort") or {}).get("digits") or [5, 6]
    d = str(nim or "")[a - 1:b]
    return 2000 + int(d) if len(d) == b - a + 1 and d.isdigit() else None


def _cohorts(student_cpl, cfg):
    """Per kurikulum, angkatan, CPL: mahasiswa, rerata skor, share >= ambang (agregat, tanpa NIM)."""
    if student_cpl.empty:
        return pd.DataFrame()
    df = student_cpl.assign(cohort=student_cpl["nim"].map(lambda n: cohort_of(n, cfg))).dropna(subset=["cohort"])
    out = _summary(df, ["curriculum", "cohort", "cpl"], cfg)
    out["cohort"] = out["cohort"].astype(int)
    return out.sort_values(["curriculum", "cohort", "cpl"]).reset_index(drop=True)


def removed_mask(df, removed):
    """True untuk baris (nim, course_code, term) yang MK-nya disetujui dihapus untuk mahasiswa itu.
    removed: set (nim, kode MK, semester casefold atau '' = semua semester); student_record.removals."""
    if df is None or df.empty or not removed:
        return pd.Series(False, index=df.index if df is not None else [])
    return pd.Series([(n, c, "") in removed or (n, c, str(t).casefold()) in removed
                      for n, c, t in zip(df["nim"].astype(str), df["course_code"].astype(str), df["term"])], index=df.index)


def build_report(files, cfg, final=None, removed=None):
    """All report tables as DataFrames. Tables with NIM are marked by name (student_*).

    final: optional dict from final_grades (files, scores, class_rows, coverage tables).
    removed: MK yang disetujui dihapus per mahasiswa (pemilik 2026-11-14): keluar dari tabel student_*
    (radar/profil), tetapi capaian kelas, progres, kumulatif, dan angkatan tetap memakai semua data."""
    th = cfg["thresholds"]
    scores = score_table(files)
    if final is not None and not final["scores"].empty:
        scores = pd.concat([scores, final["scores"]], ignore_index=True) if not scores.empty else final["scores"].copy()
    scores["estimate"] = scores["estimate"].astype(bool)

    file_rows = []
    for f in files:
        i = f.identity
        file_rows.append({
            "file": f.path.name, "used": f.ok, "curriculum": i.get("curriculum", ""),
            "course_code": i.get("course_code", ""), "course_name": i.get("course_name", ""),
            "class_name": i.get("class_name", ""), "term": f.term,
            "students_counted": int(f.result.included.sum()) if f.result is not None else 0,
            "file_thresholds": f"{f.template.file_thresholds}" if f.template else "",
            "problems": "; ".join(f.problems),
        })
    for f in (final or {}).get("files", []):
        i = f.identity
        file_rows.append({
            "file": f.path.name, "used": f.ok, "curriculum": i.get("curriculum", ""),
            "course_code": i.get("course_code", ""), "course_name": i.get("course_name", ""),
            "class_name": i.get("class_name", ""), "term": f.term, "students_counted": len(f.students),
            "file_thresholds": "nilai akhir (estimasi)",
            "problems": "; ".join(f.problems
                                  + ([f"{f.excluded_other} mahasiswa prodi lain tidak dihitung"] if f.excluded_other else [])
                                  + ([f"{f.excluded_zero} mahasiswa nilai 0 semua komponen tidak dihitung"] if f.excluded_zero else [])
                                  + ([f"{f.capped} nilai UK dibatasi"] if f.capped else []) + f.notes),
        })
    files_df = pd.DataFrame(file_rows)

    class_rows = []
    for f in files:
        if f.ok:
            for row in class_attainment(f.template, f.result, th["student"], th["class_pct"]):
                class_rows.append({"file": f.path.name, "curriculum": f.identity["curriculum"],
                                   "course_code": f.identity["course_code"],
                                   "course_name": f.identity["course_name"],
                                   "class_name": f.identity["class_name"], "term": f.term,
                                   "term_order": f.term_order, **row, "estimate": False})
    class_rows += (final or {}).get("class_rows", [])
    class_df = pd.DataFrame(class_rows)
    if not class_df.empty:
        class_df = class_df.sort_values(["term_order", "course_code", "class_name", "cpl"])
    not_achieved = class_df[class_df["status"] == "BELUM"] if not class_df.empty else class_df

    extra = {k: v for k, v in (final or {}).items() if k.startswith("coverage_")}
    if scores.empty:
        empty = pd.DataFrame()
        return {"files": files_df, "class_attainment": class_df, "not_achieved": not_achieved,
                "term_progress": empty, "cpl_cumulative": empty,
                "student_cpl": empty, "student_attempts": empty, **extra}

    chosen = best_attempts(scores)
    best = scores.merge(chosen[["file", "nim"]], on=["file", "nim"])
    all_cpl = _weighted(best, ["curriculum", "cpl", "nim"])
    cumulative = _estimate_flag(_summary(all_cpl, ["curriculum", "cpl"], cfg), best, ["curriculum", "cpl"])
    # Per mahasiswa: tanpa MK yang disetujui dihapus.
    own = scores[~removed_mask(scores, removed)] if removed else scores
    if own.empty:
        chosen, student_cpl = chosen.iloc[0:0], all_cpl.iloc[0:0].assign(achieved=False)
    elif removed:
        chosen = best_attempts(own)
        student_cpl = _weighted(own.merge(chosen[["file", "nim"]], on=["file", "nim"]), ["curriculum", "cpl", "nim"])
    else:
        student_cpl = all_cpl.copy()
    student_cpl["achieved"] = student_cpl["score"] >= th["student"]

    per_term_student = _weighted(scores, ["curriculum", "cpl", "term_order", "term", "nim"])
    progress = _estimate_flag(_summary(per_term_student, ["curriculum", "cpl", "term_order", "term"], cfg),
                              scores, ["curriculum", "cpl", "term_order", "term"])
    progress = progress.sort_values(["curriculum", "cpl", "term_order"])
    progress["change_share"] = progress.groupby(["curriculum", "cpl"])["share_achieved"].diff()
    progress["change_mean"] = progress.groupby(["curriculum", "cpl"])["mean_score"].diff()

    return {"files": files_df, "class_attainment": class_df, "not_achieved": not_achieved,
            "term_progress": progress.reset_index(drop=True), "cpl_cumulative": cumulative,
            "cohort_cpl": _cohorts(all_cpl, cfg),
            "student_cpl": student_cpl, "student_attempts": chosen,
            "student_term_cpl": _weighted(own, ["curriculum", "cpl", "term_order", "term", "nim"]) if not own.empty else own,
            "student_cum_cpl": _cumulative_by_term(own) if not own.empty else own, **extra}


def _cumulative_by_term(scores):
    """Per mahasiswa per CPL per semester: skor kumulatif s.d. semester itu (percobaan terbaik
    tiap MK di antara semester <= semester itu, bobot sama dengan student_cpl). Untuk halaman
    perkembangan per mahasiswa (radar.py, lokal; pemilik 2026-11-14)."""
    parts = []
    terms = scores[["term_order", "term"]].drop_duplicates().sort_values("term_order")
    for _, t in terms.iterrows():
        upto = scores[scores["term_order"] <= t["term_order"]]
        best = upto.merge(best_attempts(upto)[["file", "nim"]], on=["file", "nim"])
        w = _weighted(best, ["curriculum", "cpl", "nim"])
        parts.append(w.assign(term_order=t["term_order"], term=t["term"]))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


README_ROWS = [
    ("Laporan CPL", "Dibuat run_cpl.py. MEMUAT NIM (data pribadi): jangan diunggah ke situs publik."),
    ("files", "Semua berkas yang dibaca. used=False: tidak dihitung, alasannya di kolom problems."),
    ("class_attainment", "Per berkas (MK, kelas, semester) per CPL: dihitung, >= ambang, share, status."),
    ("not_achieved", "Baris class_attainment berstatus BELUM: bahan evaluasi semester/tahun berikutnya."),
    ("term_progress", "Per semester per CPL: skor CPL mahasiswa dari MK semester itu (bobot indikator), "
                      "rata-rata, share >= ambang, status, dan perubahan dari semester sebelumnya."),
    ("cpl_cumulative", "Per CPL: skor kumulatif mahasiswa (percobaan terbaik tiap MK, bobot indikator)."),
    ("student_cpl", "Per mahasiswa per CPL: skor kumulatif, jumlah MK, tercapai atau tidak. Berisi NIM."),
    ("student_attempts", "Percobaan yang dipakai per mahasiswa per MK (Total CO tertinggi). Berisi NIM."),
    ("student_term_cpl", "Per mahasiswa per CPL per semester: skor dari MK semester itu saja. Berisi NIM."),
    ("student_cum_cpl", "Per mahasiswa per CPL per semester: skor kumulatif s.d. semester itu (percobaan terbaik). Berisi NIM."),
    ("cohort_cpl", "Per angkatan (dari NIM, config cohort) per CPL: mahasiswa, rerata skor kumulatif, share >= ambang."),
    ("estimate", "Kolom estimate=True: dihitung dari nilai akhir MK (estimasi), bukan templat rinci."),
    ("coverage_cpl", "Estimasi: per kurikulum, CPL, semester: kelas, MK, SKS setara yang menyumbang (cek sebaran)."),
    ("coverage_courses", "Estimasi: MK di peta MK-CPL dan banyak kelas berkas nilai akhirnya (0 = belum ada berkas)."),
]


def write_report(report, output_dir, cfg):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "laporan_cpl.xlsx"
    th = cfg["thresholds"]
    readme = pd.DataFrame(README_ROWS + [
        ("ambang", f"individu {th['student']}, kelas {th['class_pct']}% (config.yaml)"),
        ("aturan", f"retake={cfg['retake']}, course_weight={cfg['course_weight']}"),
    ], columns=["lembar", "isi"])
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        readme.to_excel(xw, sheet_name="README", index=False)
        for name, df in report.items():
            df.to_excel(xw, sheet_name=name, index=False)
    return path


# ---------------------------------------------------------------------------
# Ringkasan untuk situs (pemilik 2026-11-11, pilihan 1): hanya angka agregat,
# TANPA NIM. Admin mengunggah ringkasan_cpl.json di Monitoring; berkas nilai
# dan laporan_cpl.xlsx tidak pernah keluar dari komputer admin.
# Kolom diambil dengan daftar putih, jadi kolom berisi NIM tidak ikut.
SUMMARY_VERSION = 1
_KELAS = ["curriculum", "course_code", "course_name", "class_name", "term", "term_order",
          "cpl", "counted", "above_threshold", "share", "status", "estimate"]
_PROGRES = ["curriculum", "cpl", "term", "term_order", "students", "mean_score", "share_achieved",
            "status", "change_share", "change_mean", "estimate"]
_KUMULATIF = ["curriculum", "cpl", "students", "mean_score", "share_achieved", "status", "estimate"]
_ANGKATAN = ["curriculum", "cohort", "cpl", "students", "mean_score", "share_achieved", "status"]


def _records(df, cols):
    if df is None or df.empty:
        return []
    out = df[[c for c in cols if c in df.columns]].copy()
    out = out.astype(object).where(pd.notna(out), None)
    rows = out.to_dict("records")
    for r in rows:
        for k, v in r.items():
            if isinstance(v, (bool, np.bool_)):
                r[k] = bool(v)
            elif isinstance(v, (np.integer,)):
                r[k] = int(v)
            elif isinstance(v, (np.floating, float)):
                r[k] = round(float(v), 4)
    return rows


def summary(report, files, cfg, created, final_files=()):
    """Dict ringkasan tanpa NIM. created: teks ISO waktu pembuatan. final_files: berkas nilai akhir (estimasi)."""
    th = cfg["thresholds"]
    cpl_text = {}
    for f in files:
        if f.ok and f.template is not None:
            for code, text in zip(f.template.cpl, f.template.cpl_text or []):
                if code:
                    cpl_text.setdefault((f.identity["curriculum"], code), text)
    out = {
        "versi": SUMMARY_VERSION, "dibuat": created,
        "ambang": {"individu": th["student"], "kelas_persen": th["class_pct"]},
        "aturan": {"retake": cfg["retake"], "course_weight": cfg["course_weight"],
                   **({"estimasi": "nilai akhir MK; bobot SKS x porsi CPL (porsi rata bila bobot kosong); "
                                   "nilai 0 semua komponen tidak dihitung"} if final_files else {})},
        "cpl": [{"curriculum": k, "cpl": c, "text": t} for (k, c), t in sorted(cpl_text.items())],
        "berkas": [{"curriculum": f.identity.get("curriculum", ""), "course_code": f.identity.get("course_code", ""),
                    "course_name": f.identity.get("course_name", ""), "class_name": f.identity.get("class_name", ""),
                    "term": f.term, "used": bool(f.ok),
                    "students_counted": int(f.result.included.sum()) if f.ok and f.result is not None else 0}
                   for f in files] + [
            {"curriculum": f.identity.get("curriculum", ""), "course_code": f.identity.get("course_code", ""),
             "course_name": f.identity.get("course_name", ""), "class_name": f.identity.get("class_name", ""),
             "term": f.term, "used": bool(f.ok), "students_counted": len(f.students) if f.ok else 0,
             "jenis": "nilai_akhir"} for f in final_files],
        "kelas": _records(report.get("class_attainment"), _KELAS),
        "progres": _records(report.get("term_progress"), _PROGRES),
        "kumulatif": _records(report.get("cpl_cumulative"), _KUMULATIF),
        # Per angkatan: hanya kelompok >= cohort.min_students mahasiswa (privasi kelompok kecil).
        "angkatan": [r for r in _records(report.get("cohort_cpl"), _ANGKATAN)
                     if r["students"] >= (cfg.get("cohort") or {}).get("min_students", 5)],
    }
    # Penjaga terakhir: tidak satu pun NIM dari berkas boleh muncul di ringkasan.
    nims = {n for f in files if f.template is not None for n in f.template.nims if n}
    nims |= {n for f in final_files for n, _ in f.students}
    text = json.dumps(out, ensure_ascii=False)
    bocor = [n for n in nims if n in text]
    if bocor:
        raise ValueError(f"Ringkasan memuat {len(bocor)} NIM; tidak ditulis.")
    return out


def write_summary(report, files, cfg, output_dir, created, final_files=()):
    path = Path(output_dir) / "ringkasan_cpl.json"
    path.write_text(json.dumps(summary(report, files, cfg, created, final_files), ensure_ascii=False, indent=1),
                    encoding="utf-8")
    return path
