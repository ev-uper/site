"""Load and validate config.yaml (+ config.local.yaml) for run_cpl.py.

Same behaviour as heslab_core.load_config (config.yaml overridden by
config.local.yaml next to it), kept local so the prodi can run cv-data
without the lab libraries (owner decision 2026-10-09).
"""
from pathlib import Path

import yaml

RETAKE_RULES = {"best_total_co"}
COURSE_WEIGHTS = {"indicator"}
SOURCES = {"site", "folder"}
FINAL_WEIGHTS = {"sks_share"}
GPA_RETAKE = {"best", "latest"}


def _merge(base, over):
    out = dict(base)
    for k, v in over.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_config(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"config tidak ditemukan: {path}")
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    local = path.with_name("config.local.yaml")
    if local.is_file():
        cfg = _merge(cfg, yaml.safe_load(local.read_text(encoding="utf-8")) or {})
    return cfg


def _inside(child: Path, parent: Path):
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def validate_config(cfg, repo_root):
    """Return a list of error messages, each naming its key. Empty = valid."""
    err = []

    def number(key, value, lo, hi):
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not lo <= value <= hi:
            err.append(f"{key}: harus angka {lo}-{hi}, didapat {value!r}")

    th = cfg.get("thresholds") or {}
    number("thresholds.student", th.get("student"), 0, 100)
    number("thresholds.class_pct", th.get("class_pct"), 0, 100)

    order = cfg.get("semester_order")
    if not isinstance(order, dict) or not order:
        err.append("semester_order: harus pemetaan nama semester -> urutan, mis. Ganjil: 1")
    else:
        vals = list(order.values())
        if not all(isinstance(v, int) and not isinstance(v, bool) and v >= 1 for v in vals):
            err.append(f"semester_order: urutan harus bilangan bulat >= 1, didapat {vals}")
        elif len(set(vals)) != len(vals):
            err.append(f"semester_order: urutan kembar {vals}")
        if len({str(k).casefold() for k in order}) != len(order):
            err.append("semester_order: nama semester kembar (huruf besar/kecil diabaikan)")

    co = cfg.get("cohort") or {}
    dg = co.get("digits")
    if not (isinstance(dg, list) and len(dg) == 2 and all(isinstance(x, int) and not isinstance(x, bool) and x >= 1 for x in dg)
            and dg[0] <= dg[1]):
        err.append(f"cohort.digits: dua bilangan bulat >= 1, mis. [5, 6], didapat {dg!r}")
    ms = co.get("min_students")
    if not isinstance(ms, int) or isinstance(ms, bool) or ms < 1:
        err.append(f"cohort.min_students: bilangan bulat >= 1, didapat {ms!r}")

    versions = cfg.get("template_versions")
    if not isinstance(versions, list) or not versions or not all(isinstance(v, str) for v in versions):
        err.append("template_versions: harus daftar teks, mis. [CPL-2026.10.09]")

    if cfg.get("retake") not in RETAKE_RULES:
        err.append(f"retake: nilai sah {sorted(RETAKE_RULES)}, didapat {cfg.get('retake')!r}")
    if cfg.get("course_weight") not in COURSE_WEIGHTS:
        err.append(f"course_weight: nilai sah {sorted(COURSE_WEIGHTS)}, didapat {cfg.get('course_weight')!r}")
    if cfg.get("source", "folder") not in SOURCES:
        err.append(f"source: nilai sah {sorted(SOURCES)}, didapat {cfg.get('source')!r}")

    paths = cfg.get("paths") or {}
    for key in ("input_dir", "output_dir"):
        value = paths.get(key)
        if not value:
            err.append(f"paths.{key}: belum diisi di config.local.yaml")
            continue
        p = Path(value)
        if _inside(p, repo_root):
            err.append(f"paths.{key}: {p} berada di dalam repo; pakai folder di luar repo (berkas memuat NIM)")
        elif key == "input_dir" and not p.is_dir():
            err.append(f"paths.input_dir: folder tidak ada: {p}")

    # Estimasi dari nilai akhir (pemilik 2026-11-13): hanya diperiksa bila folder diisi.
    fdir = paths.get("final_grades_dir")
    if fdir:
        p = Path(fdir)
        if _inside(p, repo_root):
            err.append(f"paths.final_grades_dir: {p} berada di dalam repo; pakai folder di luar repo (berkas memuat NIM)")
        elif not p.is_dir():
            err.append(f"paths.final_grades_dir: folder tidak ada: {p}")
        fg = cfg.get("final_grades") or {}
        rules = fg.get("curriculum_by_year")
        if not isinstance(rules, list) or not rules:
            err.append("final_grades.curriculum_by_year: daftar {until: 2025/2026, curriculum: K21}")
        else:
            prev = 0
            for i, r in enumerate(rules):
                u = str((r or {}).get("until", ""))
                k = str((r or {}).get("curriculum", ""))
                ok = len(u) == 9 and u[4] == "/" and u[:4].isdigit() and u[5:].isdigit() and int(u[5:]) == int(u[:4]) + 1
                if not ok or not (len(k) == 3 and k[0] == "K" and k[1:].isdigit()):
                    err.append(f"final_grades.curriculum_by_year[{i}]: until 'YYYY/YYYY' dan curriculum K + 2 angka, didapat {r!r}")
                elif int(u[:4]) <= prev:
                    err.append(f"final_grades.curriculum_by_year[{i}]: until harus urut naik")
                else:
                    prev = int(u[:4])
        pre = fg.get("student_id_prefixes")
        # Daftar kosong = semua NIM dihitung (paket templat untuk prodi lain).
        if not isinstance(pre, list) or not all(isinstance(x, str) and x.isdigit() for x in pre):
            err.append(f"final_grades.student_id_prefixes: daftar teks angka, mis. [\"1041\"] atau [], didapat {pre!r}")
        number("final_grades.uk_cap", fg.get("uk_cap"), 0, 100)
        al = fg.get("course_aliases", {})
        if not isinstance(al, dict) or not all(isinstance(v, dict) and all(isinstance(x, str) for x in v.values())
                                               for v in al.values()):
            err.append("final_grades.course_aliases: {K21: {\"nama di berkas\": \"kode MK\"}}")
        if not isinstance(fg.get("exclude_all_zero"), bool):
            err.append(f"final_grades.exclude_all_zero: true atau false, didapat {fg.get('exclude_all_zero')!r}")
        if fg.get("course_weight") not in FINAL_WEIGHTS:
            err.append(f"final_grades.course_weight: nilai sah {sorted(FINAL_WEIGHTS)}, didapat {fg.get('course_weight')!r}")
        ref = Path(str(fg.get("reference_dir") or ""))
        ref = ref if ref.is_absolute() else Path(repo_root) / ref
        if not fg.get("reference_dir") or not (ref / "ref_mata_kuliah.csv").is_file():
            err.append(f"final_grades.reference_dir: {ref} tidak memuat ref_mata_kuliah.csv")
    err += _student_record(cfg, repo_root)
    return err


def _student_record(cfg, repo_root):
    """Halaman profil CPL per mahasiswa (pemilik 2026-11-14): student_record.* dan paths masukannya."""
    err = []
    paths = cfg.get("paths") or {}
    for key, want in (("student_info_csv", "file"), ("advisors_csv", "file"), ("student_activities_csv", "file"),
                      ("course_removals_csv", "file"), ("photos_dir", "dir")):
        v = paths.get(key)
        if not v:
            continue
        p = Path(v)
        if _inside(p, repo_root):
            err.append(f"paths.{key}: {p} berada di dalam repo; pakai folder di luar repo (memuat NIM)")
        elif not (p.is_file() if want == "file" else p.is_dir()):
            err.append(f"paths.{key}: {'berkas' if want == 'file' else 'folder'} tidak ada: {p}")
    sr = cfg.get("student_record")
    if not isinstance(sr, dict):
        return err + ["student_record: bagian belum ada di config.yaml"]
    ss = sr.get("short_semesters", [])
    known = {str(k).casefold() for k in (cfg.get("semester_order") or {})}
    if not isinstance(ss, list) or not all(isinstance(x, str) and x.casefold() in known for x in ss):
        err.append(f"student_record.short_semesters: daftar kunci semester_order, mis. [Pendek], didapat {ss!r}")
    st = sr.get("record_statuses")
    if not isinstance(st, list) or not all(isinstance(x, str) for x in st):
        err.append(f"student_record.record_statuses: daftar teks, mis. [terverifikasi], didapat {st!r}")
    px = sr.get("photo_max_px")
    if not isinstance(px, int) or isinstance(px, bool) or not 100 <= px <= 2000:
        err.append(f"student_record.photo_max_px: bilangan bulat 100-2000, didapat {px!r}")
    hd = sr.get("header")
    if not isinstance(hd, dict) or not all(isinstance(v, str) for v in hd.values()):
        err.append("student_record.header: pemetaan teks (university, faculty, programme, degree, city, head_title, head_name)")
    dc = sr.get("degree_credits", {})
    if not isinstance(dc, dict) or not all(isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 300 for v in dc.values()):
        err.append(f"student_record.degree_credits: pemetaan kurikulum -> SKS bulat 1-300, mis. {{K21: 144}}, didapat {dc!r}")
    for key, lo, hi in (("plan_max_courses", 1, 10), ("plan_lowest", 0, 12)):
        v = sr.get(key)
        if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
            err.append(f"student_record.{key}: bilangan bulat {lo}-{hi}, didapat {v!r}")
    sc = sr.get("grade_scale")
    if not isinstance(sc, list):
        return err + [f"student_record.grade_scale: daftar {{min, letter, point}} atau [], didapat {sc!r}"]
    for i, s in enumerate(sc):
        ok = isinstance(s, dict) and all(isinstance(s.get(k), (int, float)) and not isinstance(s.get(k), bool) for k in ("min", "point"))
        if not ok or not 0 <= s["min"] <= 100 or not 0 <= s["point"] <= 4 or not str(s.get("letter") or "").strip():
            err.append(f"student_record.grade_scale[{i}]: {{min: 0-100, letter: teks, point: 0-4}}, didapat {s!r}")
    if sc:
        if len({s.get("min") for s in sc if isinstance(s, dict)}) != len(sc):
            err.append("student_record.grade_scale: nilai min kembar")
        pm = sr.get("pass_min_point")
        if not isinstance(pm, (int, float)) or isinstance(pm, bool) or not 0 <= pm <= 4:
            err.append(f"student_record.pass_min_point: angka 0-4 (wajib bila grade_scale diisi), didapat {pm!r}")
        if sr.get("gpa_retake") not in GPA_RETAKE:
            err.append(f"student_record.gpa_retake: nilai sah {sorted(GPA_RETAKE)} (wajib bila grade_scale diisi), "
                       f"didapat {sr.get('gpa_retake')!r}")
        if not isinstance(sr.get("gpa_include_failed"), bool):
            err.append(f"student_record.gpa_include_failed: true atau false (wajib bila grade_scale diisi), "
                       f"didapat {sr.get('gpa_include_failed')!r}")
    return err
