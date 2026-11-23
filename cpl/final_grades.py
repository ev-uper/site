"""Estimated CPL attainment from final course grades (owner 2026-11-13).

Source: the campus per-class export, e.g. "Nilai_Detail_Kelas_2026_<course name>-<class>-2025.csv"
(columns No; NIM; Nama; one column per component "KUIS (KUIS) (20.00%)" ...; "Nilai Akhir").
The file has no course code and no semester, so the identity is derived from the name
"Nilai_Detail_Kelas_<A>_<course>[-<class>]<sep><B>[-<n>]":

  course       name matched to ref_mata_kuliah.nama of the curriculum (case, spacing,
               punctuation and roman numerals ignored);
  year         B = first year of the academic year ("2025" -> 2025/2026; owner 2026-11-13);
  semester     "-<n>" after B: 1 = first entry of semester_order, 2 = second ("2025-2" = Genap);
               otherwise from the folder name "<year>_<semester>" (e.g. 2025_genap, the owner's
               zip per semester, 2026-11-13). A is NOT the semester: Ganjil and Genap 2025/2026
               exports both carry A = 2026 (seen 2026-11-13);
  class        text after the last "-" before B; " UK" after the course name or class "UK" =
               ujian khusus. A course name with "-" (e.g. "Cipta Karsa-CO-CV") is matched by
               trying shorter prefixes;
  curriculum   final_grades.curriculum_by_year (owner 2026-11-13: up to 2025/2026 -> K21).

Override list (optional) daftar_berkas.csv in the same folder, separator ';':
  berkas;kode_mk;kurikulum;tahun_akademik;semester;kelas   (empty cell = derived value).

Rules (owner 2026-11-13):
  - a course's final grade counts for every CPL mapped to it (ref_mk_cpl), split by
    bobot (empty = 1, i.e. equal shares);
  - weight of a course for a CPL when combining courses = SKS x share;
  - students with 0 in every component are not counted (did not take part);
  - only students of the prodi count (NIM prefix, final_grades.student_id_prefixes);
  - ujian khusus (UK): grade capped at final_grades.uk_cap (45 = C) and merged into the
    regular class of the same course and term (the higher of regular and capped UK counts);
  - a class that also has a detailed template file is skipped (the template is exact).
Results are labelled "estimasi dari nilai akhir MK".
"""
from dataclasses import dataclass, field
from pathlib import Path
import csv
import io
import re

import pandas as pd

PREFIX = re.compile(r"^Nilai_Detail_Kelas_(?P<a>\d{4})_(?P<rest>.+)$", re.I)
TAIL = re.compile(r"[\s-]+(?P<b>\d{4})(?:[\s-]+(?P<n>[1-9]))?$")   # "-2025", "-2025-2", " 2022 2"
UK = re.compile(r"\s+UK$", re.I)
FOLDER = re.compile(r"^(?P<b>\d{4})[\s_-]+(?P<sem>[A-Za-z]+)$")
COMPONENT = re.compile(r"\(\s*\d+(?:[.,]\d+)?\s*%\s*\)")
ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4"}
OVERRIDE = "daftar_berkas.csv"
COPY = re.compile(r"\s*\(\d+\)$")   # browser copy suffix "name (1).csv"


def norm_name(s):
    s = re.sub(r"\b(iv|i{1,3})\b", lambda m: ROMAN[m.group(1)], str(s or "").lower())
    s = s.replace("pemrograman", "pemograman").replace("lalu lintas", "lalulintas")
    return re.sub(r"[^a-z0-9]", "", s)


def parse_name(stem):
    """File name -> dict(a, b, n, course, class_name, uk) or None."""
    m = PREFIX.match(stem)
    if not m:
        return None
    rest = m["rest"].strip()
    t = TAIL.search(rest)
    # Tanpa tahun di nama ("...-UK CV"): tahun dan semester dari nama folder.
    head = (rest[:t.start()] if t else rest).strip(" -")
    course, kelas = (head.rsplit("-", 1) + [""])[:2] if "-" in head else (head, "")
    course, kelas = course.strip(), kelas.strip()
    uk = bool(UK.search(course)) or bool(re.search(r"(?<![A-Za-z])UK(?![A-Za-z])", kelas, re.I))
    if uk:
        course = UK.sub("", course).strip()
        kelas = kelas or "UK"
    return {"a": int(m["a"]), "b": int(t["b"]) if t else None, "n": int(t["n"]) if t and t["n"] else None,
            "course": course, "class_name": kelas, "uk": uk}


def _num(v):
    v = str(v or "").strip().replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return None


def read_csv_rows(path):
    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    first = text.splitlines()[0] if text else ""
    sep = ";" if first.count(";") >= first.count(",") else ","
    return list(csv.reader(io.StringIO(text), delimiter=sep))


def load_reference(folder):
    """ref_mata_kuliah, ref_mk_cpl from the backup CSVs (cadangan/). Returns (mk, peta) DataFrames."""
    folder = Path(folder)
    out = []
    for name, cols in (("ref_mata_kuliah", ["kurikulum", "kode", "nama", "sks", "semester", "sifat"]),
                       ("ref_mk_cpl", ["kurikulum", "kode_mk", "cpl", "bobot"])):
        p = folder / f"{name}.csv"
        df = pd.read_csv(p, dtype=str, keep_default_na=False) if p.is_file() and p.stat().st_size > 2 else pd.DataFrame()
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        out.append(df[cols].copy())
    mk, peta = out
    mk["sks"] = pd.to_numeric(mk["sks"], errors="coerce").fillna(0.0)
    mk["semester"] = pd.to_numeric(mk["semester"], errors="coerce")
    peta["bobot"] = pd.to_numeric(peta["bobot"], errors="coerce")
    return mk, peta


def shares(peta):
    """(kurikulum, kode_mk) -> [(cpl, share)]; empty bobot = 1 (owner 2026-11-13: equal split)."""
    out = {}
    for (kur, kode), g in peta.groupby(["kurikulum", "kode_mk"]):
        w = g["bobot"].where(g["bobot"] > 0, 1.0)
        out[(kur, kode)] = [(c, float(x) / float(w.sum())) for c, x in zip(g["cpl"], w)]
    return out


def curriculum_for(year_first, rules):
    """rules: [{'until': '2025/2026', 'curriculum': 'K21'}, ...] sorted by until."""
    for r in rules:
        if year_first <= int(str(r["until"])[:4]):
            return r["curriculum"]
    return None


@dataclass
class FinalGradeFile:
    path: Path
    identity: dict = field(default_factory=dict)
    term: str = ""
    term_order: int = 0
    uk: bool = False
    students: list = field(default_factory=list)   # (nim, final grade) counted
    names: dict = field(default_factory=dict)       # nim -> nama (radar lokal saja, tidak ke ringkasan)
    excluded_zero: int = 0
    excluded_other: int = 0                         # students of other prodi (NIM prefix)
    capped: int = 0                                 # UK grades lowered to uk_cap
    merged_into: str = ""                           # UK file merged into this regular file
    # Nilai akhir terbaca sah (identitas MK + nilai). Tetap True walau MK belum punya peta CPL atau kelas
    # punya templat rinci: daftar nilai per mahasiswa (student_record.py) tetap memuatnya.
    grades_ok: bool = False
    notes: list = field(default_factory=list)       # how the identity was derived
    problems: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.problems

    @property
    def counted(self):
        """Used for scores: ok and not merged into another class."""
        return self.ok and not self.merged_into


def _overrides(folder):
    """daftar_berkas.csv in the folder and every subfolder (one per semester folder)."""
    out = {}
    for p in sorted(Path(folder).rglob("*.csv")):
        if p.name.casefold() != OVERRIDE:
            continue
        rows = read_csv_rows(p)
        head = [h.strip().lower() for h in rows[0]] if rows else []
        for r in rows[1:]:
            d = {h: (r[i].strip() if i < len(r) else "") for i, h in enumerate(head)}
            if d.get("berkas"):
                out[Path(d["berkas"]).stem.casefold()] = d
    return out


def read_final_grade_file(path, cfg, mk, override=None):
    fg = cfg["final_grades"]
    order = list(cfg["semester_order"])
    f = FinalGradeFile(path=Path(path))
    ov = override or {}
    nm = parse_name(COPY.sub("", f.path.stem))
    if not nm and not (ov.get("kode_mk") and ov.get("tahun_akademik") and ov.get("semester")):
        f.problems.append("nama berkas bukan Nilai_Detail_Kelas_<A>_<nama MK>-<kelas>-<tahun>; isi daftar_berkas.csv")
        return f
    nm = nm or {"a": None, "b": None, "n": None, "course": "", "class_name": "", "uk": False}
    f.uk = nm["uk"]
    fm = FOLDER.match(f.path.parent.name)
    yb = nm["b"] or (int(fm["b"]) if fm else None)
    if not nm["b"] and fm:
        f.notes.append(f"tahun dari nama folder {f.path.parent.name}")
    year = ov.get("tahun_akademik") or (f"{yb}/{yb + 1}" if yb else "")
    ym = re.match(r"^(\d{4})/(\d{4})$", year)
    if not ym or int(ym[2]) != int(ym[1]) + 1:
        f.problems.append(f"tahun akademik {year!r} harus berbentuk 2025/2026")
        return f
    sem = ov.get("semester")
    if sem:
        f.notes.append("semester dari daftar_berkas.csv")
    elif nm["n"] and nm["n"] <= len(order):
        sem = order[nm["n"] - 1]
        f.notes.append(f"semester dari akhiran -{nm['n']}")
    elif fm and any(str(k).casefold() == fm["sem"].casefold() for k in order):
        sem = fm["sem"]
        f.notes.append(f"semester dari nama folder {f.path.parent.name}")
    else:
        f.problems.append("semester tidak bisa dibaca: beri akhiran -1/-2, taruh di folder <tahun>_<semester> "
                          "(mis. 2025_genap), atau isi daftar_berkas.csv")
        return f
    if fm and not ov.get("tahun_akademik") and int(fm["b"]) != int(ym[1]):
        f.problems.append(f"tahun di nama berkas ({ym[1]}) beda dengan nama folder {f.path.parent.name}")
        return f
    so = {str(k).casefold(): v for k, v in cfg["semester_order"].items()}
    if sem.casefold() not in so:
        f.problems.append(f"semester {sem!r} tidak dikenal")
        return f
    sem = next(k for k in cfg["semester_order"] if str(k).casefold() == sem.casefold())
    kur = (ov.get("kurikulum") or curriculum_for(int(ym[1]), fg["curriculum_by_year"]) or "").upper()
    if not kur:
        f.problems.append(f"tidak ada aturan kurikulum untuk {year} (final_grades.curriculum_by_year)")
        return f
    kelas = ov.get("kelas") or nm["class_name"]
    cand = mk[mk["kurikulum"] == kur]
    if ov.get("kode_mk"):
        row = cand[cand["kode"] == ov["kode_mk"]]
        f.notes.append(f"MK dari daftar_berkas.csv (nama berkas {nm['course']!r})")
    else:
        parts = nm["course"].split("-")
        names = cand["nama"].map(norm_name)
        row = cand[names == norm_name(nm["course"])]
        alias = {norm_name(k): str(v) for k, v in ((fg.get("course_aliases") or {}).get(kur) or {}).items()}
        if row.empty and norm_name(nm["course"]) in alias:
            row = cand[cand["kode"] == alias[norm_name(nm["course"])]]
            f.notes.append(f"MK dari padanan nama (final_grades.course_aliases: {nm['course']!r})")
        for i in range(len(parts) - 1, 0, -1):
            if not row.empty:
                break
            row = cand[names == norm_name("-".join(parts[:i]))]
            if not row.empty:
                f.notes.append(f"MK dicocokkan dari {'-'.join(parts[:i])!r} (nama berkas {nm['course']!r})")
    if len(row) != 1:
        f.problems.append(f"MK {ov.get('kode_mk') or nm['course']!r} {'tidak ada' if row.empty else 'ganda'} di {kur}"
                          f"{'; isi kode_mk di daftar_berkas.csv' if row.empty else ''}")
        return f
    row = row.iloc[0]
    f.identity = {"curriculum": kur, "course_code": row["kode"], "course_name": row["nama"], "credits": float(row["sks"]),
                  "class_name": kelas, "academic_year": year, "semester": sem}
    f.term = f"{year} {sem}"
    f.term_order = int(ym[1]) * 10 + so[sem.casefold()]
    if not row["sks"] > 0:
        f.problems.append("SKS MK 0 atau kosong di Data prodi")

    rows = read_csv_rows(f.path)
    head = [h.strip() for h in rows[0]] if rows else []
    low = [h.casefold() for h in head]
    if "nim" not in low or "nilai akhir" not in low:
        f.problems.append("kolom NIM atau Nilai Akhir tidak ada")
        return f
    i_nim, i_na = low.index("nim"), low.index("nilai akhir")
    i_nama = low.index("nama") if "nama" in low else None
    comp = [i for i, h in enumerate(head) if COMPONENT.search(h)]
    prefixes = tuple(str(p) for p in fg.get("student_id_prefixes") or [])
    seen = set()
    for r in rows[1:]:
        if not any(c.strip() for c in r):
            continue
        nim = r[i_nim].strip() if i_nim < len(r) else ""
        na = _num(r[i_na]) if i_na < len(r) else None
        if not nim:
            continue
        if nim in seen:
            f.problems.append("NIM ganda di berkas")
            break
        seen.add(nim)
        if prefixes and not nim.startswith(prefixes):
            f.excluded_other += 1
            continue
        vals = [_num(r[i]) if i < len(r) else None for i in comp] or [na]
        # Nilai Akhir kosong dengan semua komponen 0/kosong = tidak ikut (ekspor Agama 2025/2026 Ganjil).
        if fg["exclude_all_zero"] and all((v or 0) == 0 for v in vals) and (na or 0) == 0:
            f.excluded_zero += 1
            continue
        if na is None or not 0 <= na <= 100:
            f.problems.append("Nilai Akhir kosong atau di luar 0-100 padahal komponen berisi nilai")
            break
        if f.uk and na > fg["uk_cap"]:
            na = float(fg["uk_cap"])
            f.capped += 1
        f.students.append((nim, na))
        if i_nama is not None and i_nama < len(r) and r[i_nama].strip():
            f.names[nim] = r[i_nama].strip()
    if not f.students and not f.problems:
        f.problems.append("tidak ada mahasiswa prodi yang dihitung")
    f.grades_ok = not f.problems
    return f


def _merge_uk(files):
    """UK files: merge into the regular class(es) of the same course and term (higher grade counts)."""
    for u in files:
        if not (u.ok and u.uk):
            continue
        i = u.identity
        reg = [f for f in files if f.ok and not f.uk and f.term == u.term
               and (f.identity["curriculum"], f.identity["course_code"]) == (i["curriculum"], i["course_code"])]
        if not reg:
            u.notes.append("UK tanpa kelas reguler: dihitung sebagai kelas sendiri")
            continue
        added = 0
        for nim, na in u.students:
            home = next((f for f in reg if any(n == nim for n, _ in f.students)), None)
            if home:
                home.students = [(n, max(v, na) if n == nim else v) for n, v in home.students]
            else:
                reg[0].students.append((nim, na))
                added += 1
        u.merged_into = ", ".join(f.path.name for f in reg)
        u.notes.append(f"UK digabung ke kelas reguler (nilai tertinggi dipakai; {added} mahasiswa baru)")


def load_final_folder(folder, cfg, mk, template_keys=()):
    """Every *.csv under folder (except daftar_berkas.csv); template_keys = identities of detailed template files."""
    ov = _overrides(folder)
    paths = sorted(p for p in Path(folder).rglob("*.csv") if p.name.casefold() != OVERRIDE)
    files = []
    for p in paths:
        base = p.with_name(COPY.sub("", p.stem) + p.suffix)
        if base != p and base.is_file() and base.read_bytes() == p.read_bytes():
            # Unduhan ganda browser ("... (1).csv") berisi sama persis: dilewati, tidak dihitung dua kali.
            files.append(FinalGradeFile(path=p, problems=[f"salinan unduhan ganda dari {base.name} (isi sama); tidak dipakai"]))
            continue
        files.append(read_final_grade_file(p, cfg, mk, ov.get(p.stem.casefold()) or ov.get(base.stem.casefold())))
    taken = {tuple(str(x).casefold() for x in k) for k in template_keys}
    by_key = {}
    for f in files:
        if not f.ok:
            continue
        i = f.identity
        key = tuple(str(i[k]).casefold() for k in ("curriculum", "course_code", "academic_year", "semester", "class_name"))
        if key in taken:
            f.problems.append("kelas ini punya berkas templat CPL rinci; nilai akhir tidak dipakai")
        by_key.setdefault(key, []).append(f)
    for group in by_key.values():
        if len(group) > 1:
            names = ", ".join(g.path.name for g in group)
            for g in group:
                g.problems.append(f"identitas kelas ganda: {names}")
                g.grades_ok = False
    _merge_uk(files)
    return files


def final_scores(files, peta):
    """Rows like archive.score_table: one per (file, student, CPL); weight = SKS x share; estimate = True."""
    sh = shares(peta)
    rows = []
    for f in files:
        if not f.counted:
            continue
        i = f.identity
        for cpl, share in sh.get((i["curriculum"], i["course_code"]), []):
            for nim, na in f.students:
                rows.append({"file": f.path.name, "curriculum": i["curriculum"], "course_code": i["course_code"],
                             "course_name": i["course_name"], "class_name": i["class_name"], "term": f.term,
                             "term_order": f.term_order, "nim": nim, "total_co": na, "cpl": cpl, "score": na,
                             "weight": i["credits"] * share, "estimate": True})
    return pd.DataFrame(rows, columns=["file", "curriculum", "course_code", "course_name", "class_name", "term",
                                       "term_order", "nim", "total_co", "cpl", "score", "weight", "estimate"])


def no_cpl_problem(files, peta):
    """Files whose course has no CPL in the map get a problem (nothing to count)."""
    sh = shares(peta)
    for f in files:
        if f.ok and not sh.get((f.identity["curriculum"], f.identity["course_code"])):
            f.problems.append(f"MK {f.identity['course_code']} belum punya CPL di peta MK-CPL {f.identity['curriculum']}")


def final_class_rows(files, peta, th_student, th_class_pct):
    """Per file per CPL: counted, >= threshold, share, status (same shape as class_attainment rows)."""
    sh = shares(peta)
    out = []
    for f in files:
        if not f.counted:
            continue
        i = f.identity
        n = len(f.students)
        above = sum(1 for _, na in f.students if na >= th_student)
        for cpl, _ in sh.get((i["curriculum"], i["course_code"]), []):
            out.append({"file": f.path.name, "curriculum": i["curriculum"], "course_code": i["course_code"],
                        "course_name": i["course_name"], "class_name": i["class_name"], "term": f.term,
                        "term_order": f.term_order, "cpl": cpl, "counted": n, "above_threshold": above,
                        "share": above / n, "status": "TERCAPAI" if above / n >= th_class_pct / 100 else "BELUM",
                        "estimate": True})
    return out


def coverage(files, mk, peta):
    """Spread check (no NIM): per CPL per term which classes/courses contribute, and courses without files."""
    sh = shares(peta)
    rows = []
    for f in files:
        if not f.counted:
            continue
        i = f.identity
        for cpl, share in sh.get((i["curriculum"], i["course_code"]), []):
            rows.append({"curriculum": i["curriculum"], "cpl": cpl, "term": f.term, "term_order": f.term_order,
                         "course_code": i["course_code"], "class_name": i["class_name"],
                         "sks_equivalent": i["credits"] * share, "students": len(f.students)})
    df = pd.DataFrame(rows, columns=["curriculum", "cpl", "term", "term_order", "course_code", "class_name",
                                     "sks_equivalent", "students"])
    if df.empty:
        cpl_tab = df
    else:
        cpl_tab = (df.groupby(["curriculum", "cpl", "term_order", "term"])
                   .agg(classes=("class_name", "size"), courses=("course_code", "nunique"),
                        sks_equivalent=("sks_equivalent", "sum"), student_rows=("students", "sum"))
                   .reset_index().sort_values(["curriculum", "cpl", "term_order"]))
    kurs = sorted({f.identity["curriculum"] for f in files if f.ok}) or sorted(peta["kurikulum"].unique())
    n_files = {}
    for f in files:
        if f.counted:
            k = (f.identity["curriculum"], f.identity["course_code"])
            n_files[k] = n_files.get(k, 0) + 1
    crs = []
    for _, m in mk[mk["kurikulum"].isin(kurs)].iterrows():
        cpls = [c for c, _ in sh.get((m["kurikulum"], m["kode"]), [])]
        crs.append({"curriculum": m["kurikulum"], "course_code": m["kode"], "course_name": m["nama"],
                    "semester": m["semester"], "sks": m["sks"], "sifat": m["sifat"], "cpl": ", ".join(cpls),
                    "files": n_files.get((m["kurikulum"], m["kode"]), 0)})
    course_tab = pd.DataFrame(crs)
    if not course_tab.empty:
        course_tab = course_tab.sort_values(["curriculum", "files", "semester", "course_code"])
    return cpl_tab, course_tab


def prepare_final(cfg, root, template_files=()):
    """Read the final-grade folder (paths.final_grades_dir) for build_report. None when not configured."""
    folder = (cfg.get("paths") or {}).get("final_grades_dir")
    if not folder:
        return None
    fg = cfg["final_grades"]
    ref = Path(fg["reference_dir"])
    mk, peta = load_reference(ref if ref.is_absolute() else Path(root) / ref)
    keys = [tuple(f.identity.get(k, "") for k in ("curriculum", "course_code", "academic_year", "semester", "class_name"))
            for f in template_files if f.ok]
    files = load_final_folder(folder, cfg, mk, keys)
    no_cpl_problem(files, peta)
    cpl_tab, course_tab = coverage(files, mk, peta)
    th = cfg["thresholds"]
    return {"files": files, "scores": final_scores(files, peta),
            "class_rows": final_class_rows(files, peta, th["student"], th["class_pct"]),
            "coverage_cpl": cpl_tab, "coverage_courses": course_tab,
            "reference": {"mk": len(mk), "peta": len(peta)}}
