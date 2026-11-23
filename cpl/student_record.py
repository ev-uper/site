"""Data per mahasiswa untuk halaman profil CPL (radar.py): nilai per semester, IPS/IPK, identitas,
dosen wali, foto, prestasi, karya, kegiatan (pemilik 2026-11-14).

Semua masukan memuat NIM, jadi dibaca dari folder di luar repo (paths.* di config.local.yaml),
kecuali prestasi dan karya yang sudah ada di cadangan/ (salinan data situs). Hasilnya hanya
dipakai halaman lokal; tidak pernah masuk ringkasan situs.

Masukan (semua opsional; yang tidak diisi tidak ditampilkan):
  paths.student_info_csv        ekspor identitas (SIAKAD), kolom: nim, nama, tempat_lahir,
                                tanggal_lahir, tanggal_masuk, status (kolom lain diabaikan)
  paths.advisors_csv            perwalian, kolom: nim, email_wali (nama dicari di cadangan/dosen.csv;
                                kolom nama_wali opsional menimpa)
  paths.student_activities_csv  sertifikat/organisasi/magang, kolom: nim, jenis, nama, peran,
                                penyelenggara, tahun
  paths.photos_dir              foto <NIM>.jpg / .jpeg / .png
  paths.course_removals_csv     MK yang disetujui dihapus per mahasiswa, kolom: nim, kode_mk,
                                tahun_akademik (mis. 2023/2024; kosong = semua), semester (Ganjil/Genap/Pendek;
                                kosong = semua), keterangan (no. surat, opsional)
  final_grades.reference_dir    lkps_prestasi_mahasiswa.csv, karya_mahasiswa.csv, karya.csv, dosen.csv
"""
from base64 import b64encode
from io import BytesIO
from pathlib import Path
import logging

import pandas as pd

from .final_grades import read_csv_rows

log = logging.getLogger("run_cpl")

INFO_COLS = ["nama", "tempat_lahir", "tanggal_lahir", "tanggal_masuk", "status"]
ACTIVITY_COLS = ["jenis", "nama", "peran", "penyelenggara", "tahun"]
PHOTO_TYPES = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png"}


def _rows(path):
    """CSV -> list of dict (kolom huruf kecil, nilai dipangkas). [] bila path kosong/tidak ada."""
    if not path or not Path(path).is_file():
        return []
    rows = read_csv_rows(path)
    if not rows:
        return []
    head = [h.strip().lower() for h in rows[0]]
    return [{h: (r[i].strip() if i < len(r) else "") for i, h in enumerate(head)} for r in rows[1:] if any(c.strip() for c in r)]


def _ref(cfg, root):
    ref = Path(str((cfg.get("final_grades") or {}).get("reference_dir") or "cadangan"))
    return ref if ref.is_absolute() else Path(root) / ref


def _ref_df(folder, name):
    p = Path(folder) / f"{name}.csv"
    return pd.read_csv(p, dtype=str, keep_default_na=False) if p.is_file() and p.stat().st_size > 2 else pd.DataFrame()


# ---------------------------------------------------------------------------
# Nilai dan IPK

def letter_of(grade, scale):
    """(huruf, bobot) untuk nilai 0-100 menurut student_record.grade_scale; (None, None) bila skala kosong."""
    for s in sorted(scale or [], key=lambda s: -float(s["min"])):
        if grade >= float(s["min"]):
            return str(s["letter"]), float(s["point"])
    return None, None


def removals(cfg):
    """MK yang disetujui dihapus per mahasiswa (pemilik 2026-11-14): set (nim, kode_mk, semester casefold
    atau '' = semua semester). Keluar dari daftar nilai, IPS/IPK/SKS, dan skor CPL mahasiswa itu;
    capaian kelas dan angkatan tidak berubah (archive.build_report)."""
    p = (cfg.get("paths") or {}).get("course_removals_csv")
    out = set()
    for r in _rows(p):
        if not (r.get("nim") and r.get("kode_mk")):
            continue
        ta, sem = r.get("tahun_akademik", ""), r.get("semester", "")
        if bool(ta) != bool(sem):
            log.warning("penghapusan MK %s: isi tahun_akademik DAN semester, atau kosongkan keduanya; baris dilewati",
                        r["kode_mk"])
            continue
        out.add((r["nim"], r["kode_mk"], f"{ta} {sem}".casefold() if ta else ""))
    if p:
        log.info("hapus MK   : %s (%d baris)", p, len(out))
    return out


def is_removed(removed, nim, code, term):
    return bool(removed) and ((nim, code, "") in removed or (nim, code, str(term).casefold()) in removed)


def transcript(final_files, removed=None):
    """nim -> daftar MK yang ditempuh dari berkas nilai akhir (satu baris per MK per semester; nilai tertinggi
    bila ada dua kelas di semester yang sama). MK di removed tidak ikut."""
    best = {}
    used = set()
    for f in final_files or []:
        if not f.grades_ok or f.merged_into:
            continue
        i = f.identity
        for nim, na in f.students:
            if is_removed(removed, nim, i["course_code"], f.term):
                used.update({(nim, i["course_code"], ""), (nim, i["course_code"], f.term.casefold())})
                continue
            k = (nim, i["curriculum"], i["course_code"], f.term_order)
            if k not in best or na > best[k]["nilai"]:
                best[k] = {"term": f.term, "term_order": f.term_order, "kur": i["curriculum"], "kode": i["course_code"],
                           "nama": i["course_name"], "sks": float(i["credits"]), "nilai": float(na)}
    tak = sorted(f"{n} {c} {t or 'semua semester'}" for n, c, t in (removed or set()) if (n, c, t) not in used)
    if tak:
        log.warning("penghapusan MK tanpa nilai yang cocok (periksa NIM/kode/semester): %d baris", len(tak))
    out = {}
    for (nim, *_), r in best.items():
        out.setdefault(nim, []).append(r)
    for rows in out.values():
        rows.sort(key=lambda r: (r["term_order"], r["kode"]))
    return out


def semester_summary(rows, sr):
    """Per semester: IPS, IPK s.d. semester itu, SKS diambil, SKS lulus kumulatif. Tanpa skala nilai: hanya SKS."""
    scale = sr.get("grade_scale") or []
    for r in rows:
        r["huruf"], r["bobot"] = letter_of(r["nilai"], scale)
    out = []
    for t in sorted({r["term_order"] for r in rows}):
        now = [r for r in rows if r["term_order"] == t]
        s = {"term": now[0]["term"], "term_order": t, "sks": sum(r["sks"] for r in now)}
        if scale:
            s["ips"] = _gpa(now, sr)
            # Satu percobaan per MK s.d. semester ini: terbaik atau terakhir (student_record.gpa_retake).
            pick = {}
            for r in (x for x in rows if x["term_order"] <= t):
                k = (r["kur"], r["kode"])
                if k not in pick or (r["bobot"] > pick[k]["bobot"] if sr["gpa_retake"] == "best" else True):
                    pick[k] = r
            s["ipk"] = _gpa(pick.values(), sr)
            s["sks_lulus"] = sum(r["sks"] for r in pick.values() if r["bobot"] >= float(sr["pass_min_point"]))
        out.append(s)
    return out


def _gpa(rows, sr):
    rows = [r for r in rows if sr["gpa_include_failed"] or r["bobot"] >= float(sr["pass_min_point"])]
    sks = sum(r["sks"] for r in rows)
    return round(sum(r["bobot"] * r["sks"] for r in rows) / sks, 2) if sks else None


# ---------------------------------------------------------------------------
# Identitas, wali, foto, prestasi, karya, kegiatan

def student_info(cfg):
    p = (cfg.get("paths") or {}).get("student_info_csv")
    out = {}
    for r in _rows(p):
        if r.get("nim"):
            out[r["nim"]] = {k: r.get(k, "") for k in INFO_COLS}
    if p:
        log.info("identitas  : %s (%d mahasiswa)", p, len(out))
    return out


def advisors(cfg, root):
    """nim -> {email, nama}. Nama dari cadangan/dosen.csv (email atau email_alternatif), atau kolom nama_wali."""
    p = (cfg.get("paths") or {}).get("advisors_csv")
    rows = _rows(p)
    if not rows:
        return {}
    dosen = _ref_df(_ref(cfg, root), "dosen")
    nama = {}
    for _, d in dosen.iterrows():
        for e in (d.get("email", ""), d.get("email_alternatif", "")):
            if str(e).strip():
                nama[str(e).strip().lower()] = d.get("nama", "")
    out = {}
    for r in rows:
        e = r.get("email_wali", "").lower()
        if r.get("nim") and e:
            out[r["nim"]] = {"email": e, "nama": r.get("nama_wali") or nama.get(e, "")}
    tanpa = sorted({v["email"] for v in out.values() if not v["nama"]})
    log.info("perwalian  : %s (%d mahasiswa, %d dosen wali)", p, len(out), len({v["email"] for v in out.values()}))
    if tanpa:
        log.warning("email wali tidak ada di cadangan/dosen.csv (isi kolom nama_wali): %s", ", ".join(tanpa))
    return out


def activities(cfg):
    p = (cfg.get("paths") or {}).get("student_activities_csv")
    out = {}
    for r in _rows(p):
        if r.get("nim") and r.get("nama"):
            out.setdefault(r["nim"], []).append({k: r.get(k, "") for k in ACTIVITY_COLS})
    if p:
        log.info("kegiatan   : %s (%d mahasiswa)", p, len(out))
    return out


def achievements(cfg, root):
    """nim -> prestasi (lkps_prestasi_mahasiswa) dan karya (karya_mahasiswa + karya), status sesuai config."""
    ref = _ref(cfg, root)
    ok = set((cfg.get("student_record") or {}).get("record_statuses") or [])
    pres, kar = {}, {}
    p = _ref_df(ref, "lkps_prestasi_mahasiswa")
    for _, r in p.iterrows():
        if r.get("nim") and r.get("status", "") in ok:
            pres.setdefault(r["nim"].strip(), []).append({k: r.get(k, "") for k in
                                                          ("nama_kegiatan", "penyelenggara", "tingkat", "capaian", "tahun")})
    km, k = _ref_df(ref, "karya_mahasiswa"), _ref_df(ref, "karya")
    if not km.empty and not k.empty:
        k = k[k["status"].isin(ok)].set_index("id")
        for _, r in km.iterrows():
            if r["karya_id"] in k.index:
                x = k.loc[r["karya_id"]]
                kar.setdefault(r["nim"].strip(), []).append({"judul": x.get("judul", ""), "tahun": x.get("tahun", ""),
                                                             "jenis": x.get("jenis", "") or x.get("kategori", ""),
                                                             "terbitan": x.get("nama_terbitan", ""), "peran": r.get("peran", "")})
    for d in (pres, kar):
        for v in d.values():
            v.sort(key=lambda x: str(x.get("tahun", "")), reverse=True)
    return pres, kar


def photo(cfg, nim):
    """data: URI foto <NIM>.jpg/.png (diperkecil ke student_record.photo_max_px bila Pillow ada), '' bila tidak ada."""
    d = (cfg.get("paths") or {}).get("photos_dir")
    if not d:
        return ""
    for ext, typ in PHOTO_TYPES.items():
        for p in (Path(d) / f"{nim}{ext}", Path(d) / f"{nim}{ext.upper()}"):
            if p.is_file():
                return _photo_uri(p, typ, int((cfg.get("student_record") or {}).get("photo_max_px") or 400))
    return ""


def _photo_uri(p, typ, max_px):
    raw = p.read_bytes()
    try:
        from PIL import Image, ImageOps
        im = ImageOps.exif_transpose(Image.open(BytesIO(raw))).convert("RGB")
        im.thumbnail((max_px, max_px))
        buf = BytesIO()
        im.save(buf, "JPEG", quality=85)
        raw, typ = buf.getvalue(), "jpeg"
    except ImportError:
        if len(raw) > 300_000:
            log.warning("foto %s %d kB disisipkan utuh (pasang Pillow agar diperkecil)", p.name, len(raw) // 1000)
    except Exception as e:  # noqa: BLE001 - foto rusak tidak menghentikan laporan
        log.warning("foto %s tidak terbaca (%s); dilewati", p.name, e)
        return ""
    return f"data:image/{typ};base64,{b64encode(raw).decode()}"
