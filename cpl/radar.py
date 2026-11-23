"""Profil CPL per mahasiswa (pemilik 2026-11-13, diperluas 2026-11-14).

Halaman HTML mandiri (tanpa internet) di paths.output_dir:
  radar_mahasiswa.html         semua mahasiswa (admin)
  perwalian/<email wali>.html  hanya mahasiswa perwalian dosen itu (dari paths.advisors_csv)

Per mahasiswa: hal. 1 foto dan grafik (radar CPL kumulatif vs rata-rata angkatan vs ambang, IPS/IPK,
CPL tercapai per semester); hal. 2 daftar data seperti SKPI (identitas, program studi, ringkasan
akademik, CPL dan rumusannya, prestasi, karya, kegiatan, tanda tangan); hal. 3 dst. nilai dan CPL
per semester. Tiga versi cetak (pemilik 2026-11-14), dipilih di "Versi":
  rapor               judul semester ke-N, rencana pencapaian CPL, catatan dosen wali, tanda tangan
                      orang tua/wali dan dosen wali, ditambah hal. 3 dst.;
  resmi per semester  hal. 1-2, bagian program studi, tanda tangan dosen wali dan Kaprodi;
  resmi kelulusan     hal. 1-2 untuk lulusan: hanya SKS lulus, IPK, dan CPL (tanpa angka per semester),
                      tanda tangan Kaprodi.
MEMUAT NIM, nama, dan nilai: untuk perwalian, dibagikan lewat Drive privat, tidak diunggah ke situs.
"""
from collections import Counter
from datetime import datetime
from pathlib import Path
import html
import json
import logging
import re

import pandas as pd

from .archive import cohort_of
from .final_grades import load_reference
from .template import norm_cpl
from . import student_record as sr_

log = logging.getLogger("run_cpl")


def _ref_cpl(root, cfg):
    ref = Path(str((cfg.get("final_grades") or {}).get("reference_dir") or "cadangan"))
    p = (ref if ref.is_absolute() else Path(root) / ref) / "ref_cpl.csv"
    if not p.is_file() or p.stat().st_size < 3:
        return pd.DataFrame()
    return pd.read_csv(p, dtype=str, keep_default_na=False)


def load_cpl_text(root, cfg):
    """(kurikulum, kode) -> rumusan dari ref_cpl.csv di final_grades.reference_dir (bila ada)."""
    df = _ref_cpl(root, cfg)
    return {(r["kurikulum"], r["kode"]): r["rumusan"] for _, r in df.iterrows()} if not df.empty else {}


def load_cpl_text_en(root, cfg):
    """(kurikulum, kode) -> rumusan_en (kosong bila kolom tidak ada)."""
    df = _ref_cpl(root, cfg)
    if df.empty or "rumusan_en" not in df.columns:
        return {}
    return {(r["kurikulum"], r["kode"]): r["rumusan_en"] for _, r in df.iterrows() if r["rumusan_en"]}


def load_curriculum(root, cfg):
    """kurikulum -> [{kode, nama, sks, smt, sifat, cpl}] dari ref_mata_kuliah + ref_mk_cpl di
    final_grades.reference_dir; untuk rencana pencapaian CPL di rapor (pemilik 2026-11-14)."""
    ref = Path(str((cfg.get("final_grades") or {}).get("reference_dir") or "cadangan"))
    mk, peta = load_reference(ref if ref.is_absolute() else Path(root) / ref)
    cpl = {}
    for r in peta.itertuples(index=False):
        if str(r.cpl).strip():
            cpl.setdefault((r.kurikulum, r.kode_mk), set()).add(norm_cpl(str(r.cpl).strip()))
    out = {}
    for r in mk.itertuples(index=False):
        out.setdefault(r.kurikulum, []).append({
            "kode": r.kode, "nama": r.nama, "sks": float(r.sks), "smt": None if pd.isna(r.semester) else int(r.semester),
            "sifat": r.sifat, "cpl": sorted(cpl.get((r.kurikulum, r.kode), ()), key=lambda c: (len(c), c))})
    return out


def build_records(cfg, root, final_files=(), removed=None):
    """Masukan tambahan per mahasiswa (student_record.py). Kosong bila tidak ada yang diisi.
    removed: MK yang disetujui dihapus (student_record.removals), tidak masuk daftar nilai."""
    pres, kar = sr_.achievements(cfg, root)
    return {"transcript": sr_.transcript(final_files, removed), "info": sr_.student_info(cfg), "wali": sr_.advisors(cfg, root),
            "kegiatan": sr_.activities(cfg), "prestasi": pres, "karya": kar, "kurikulum_mk": load_curriculum(root, cfg)}


def _by_nim(df):
    """DataFrame (nim, term_order, cpl, score) -> nim -> term_order -> {cpl: skor}."""
    out = {}
    if df is None or df.empty:
        return out
    for r in df.itertuples(index=False):
        out.setdefault(str(r.nim), {}).setdefault(int(r.term_order), {"term": r.term})[r.cpl] = round(float(r.score), 1)
    return out


def radar_data(report, cfg, names=None, cpl_text=None, record=None, cpl_text_en=None):
    """Data halaman (memuat NIM). None bila belum ada skor CPL maupun nilai mahasiswa."""
    sc = report.get("student_cpl")
    sc = sc if sc is not None else pd.DataFrame()
    rec = record or {}
    tr = rec.get("transcript") or {}
    if sc.empty and not tr:
        return None
    names, cpl_text, cpl_en = names or {}, cpl_text or {}, cpl_text_en or {}
    srcfg = cfg.get("student_record") or {}
    kur = {}
    if not sc.empty:
        for k, g in sc.groupby("curriculum"):
            codes = sorted(g["cpl"].unique(), key=lambda c: (len(c), c))
            kur[k] = {"cpl": codes, "teks": {c: cpl_text.get((k, c), "") for c in codes},
                      "teks_en": {c: cpl_en.get((k, c), "") for c in codes}}
    kmk = rec.get("kurikulum_mk") or {}
    pass_min = srcfg.get("pass_min_point")
    coh = report.get("cohort_cpl")
    rata = {}
    if coh is not None and not coh.empty:
        for _, r in coh.iterrows():
            rata.setdefault(f"{r['curriculum']}|{int(r['cohort'])}", {})[r["cpl"]] = round(float(r["mean_score"]), 1)
    per_term, cum = _by_nim(report.get("student_term_cpl")), _by_nim(report.get("student_cum_cpl"))
    skor = {}
    if not sc.empty:
        for r in sc.itertuples(index=False):
            d = skor.setdefault((r.curriculum, str(r.nim)), {"skor": {}, "mk": {}})
            d["skor"][r.cpl], d["mk"][r.cpl] = round(float(r.score), 1), int(r.courses)
    nims = {n for _, n in skor} | set(tr)
    info, wali = rec.get("info") or {}, rec.get("wali") or {}
    mhs = []
    for nim in nims:
        rows = tr.get(nim, [])
        ks = [k for k, n in skor if n == nim] or [Counter(r["kur"] for r in rows).most_common(1)[0][0]]
        k = ks[0]
        kur.setdefault(k, {"cpl": [], "teks": {}, "teks_en": {}})
        kur[k]["mk"] = kmk.get(k, [])
        smt = {s["term_order"]: s for s in sr_.semester_summary(rows, srcfg)} if rows else {}
        for t, v in {**per_term.get(nim, {}), **cum.get(nim, {})}.items():
            smt.setdefault(t, {"term": v["term"], "term_order": t, "sks": 0})
        pendek = {str(x).casefold() for x in srcfg.get("short_semesters") or []}
        for t, s in smt.items():
            s["pendek"] = str(s["term"]).rsplit(" ", 1)[-1].casefold() in pendek
            # lulus: bobot >= pass_min_point; tanpa skala nilai semua MK yang ditempuh dianggap selesai.
            s["mk"] = [{**{x: r[x] for x in ("kode", "nama", "sks", "nilai", "huruf")},
                        "lulus": r.get("bobot") is None or pass_min is None or r["bobot"] >= float(pass_min)}
                       for r in rows if r["term_order"] == t]
            s["cpl"] = {c: v for c, v in per_term.get(nim, {}).get(t, {}).items() if c != "term"}
            s["kum"] = {c: v for c, v in cum.get(nim, {}).get(t, {}).items() if c != "term"}
        i = info.get(nim, {})
        d = skor.get((k, nim), {"skor": {}, "mk": {}})
        mhs.append({"nim": nim, "nama": names.get(nim) or i.get("nama", ""), "kur": k, "angkatan": cohort_of(nim, cfg),
                    "skor": d["skor"], "mk": d["mk"], "info": i, "wali": wali.get(nim),
                    "foto": sr_.photo(cfg, nim), "smt": [smt[t] for t in sorted(smt)],
                    "prestasi": (rec.get("prestasi") or {}).get(nim, []), "karya": (rec.get("karya") or {}).get(nim, []),
                    "kegiatan": (rec.get("kegiatan") or {}).get(nim, [])})
    mhs.sort(key=lambda m: (m["kur"], m["nim"]))
    # Rata-rata IPS angkatan per semester (pembanding grafik rapor, pemilik 2026-11-14): rata-rata IPS
    # mahasiswa kurikulum dan angkatan yang sama yang punya nilai di semester itu.
    ips = {}
    for m in mhs:
        for s in m["smt"]:
            if s.get("ips") is not None:
                ips.setdefault(f"{m['kur']}|{m['angkatan']}", {}).setdefault(s["term_order"], []).append(s["ips"])
    rata_ips = {g: {t: round(sum(v) / len(v), 2) for t, v in d.items()} for g, d in ips.items()}
    return {"dibuat": datetime.now().astimezone().isoformat(timespec="minutes"),
            "ambang": cfg["thresholds"]["student"], "kurikulum": kur, "rata": rata, "rata_ips": rata_ips, "mahasiswa": mhs,
            "sks_sarjana": srcfg.get("degree_credits") or {},
            "rencana": {"maks": srcfg.get("plan_max_courses", 4), "terendah": srcfg.get("plan_lowest", 3)},
            "kop": srcfg.get("header") or {}, "skala": bool(srcfg.get("grade_scale")), "judul": "Semua mahasiswa"}


def _write(path, data):
    teks = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".html.new")
    tmp.write_text(HALAMAN.replace("__DATA__", teks).replace("__DIBUAT__", html.escape(data["dibuat"]))
                   .replace("__JUDUL__", html.escape(data["judul"])), encoding="utf-8")
    tmp.replace(path)


def advisor_file_name(email):
    return re.sub(r"[^a-z0-9._-]", "_", email.split("@")[0].lower()) + ".html"


def write_student_radar(report, cfg, output_dir, names=None, cpl_text=None, record=None, cpl_text_en=None):
    """radar_mahasiswa.html (semua) dan perwalian/<wali>.html. Path berkas utama, None bila tidak ada data."""
    data = radar_data(report, cfg, names, cpl_text, record, cpl_text_en)
    if data is None:
        return None
    path = Path(output_dir) / "radar_mahasiswa.html"
    _write(path, data)
    per = {}
    for m in data["mahasiswa"]:
        if m["wali"]:
            per.setdefault(m["wali"]["email"], []).append(m)
    for email, xs in sorted(per.items()):
        nama = xs[0]["wali"]["nama"] or email
        _write(Path(output_dir) / "perwalian" / advisor_file_name(email),
               {**data, "mahasiswa": xs, "judul": f"Perwalian {nama}"})
        log.info("perwalian  : %s, %d mahasiswa -> perwalian/%s", nama, len(xs), advisor_file_name(email))
    tanpa = sum(1 for m in data["mahasiswa"] if not m["wali"])
    if per and tanpa:
        log.warning("perwalian  : %d mahasiswa tanpa dosen wali di advisors_csv (hanya di radar_mahasiswa.html)", tanpa)
    return path


HALAMAN = r"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Profil CPL Mahasiswa</title>
<style>
:root{--biru:#0C2A4D;--biru-3:#5C86B0;--biru-m10:#EEF3F8;--emas:#B8860B;--merah:#C8102E;--hijau:#00954E;
  --ink:#14212E;--muted:#5D6B78;--line:#D9DFDA;--bg:#E9ECEA;--panel:#fff;--ok-bg:#E3F3EA;--no-bg:#FBE5E8}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 system-ui,'Segoe UI',sans-serif}
.kepala{background:var(--biru);color:#fff;padding:12px 20px}.kepala h1{margin:0;font-size:19px}.kepala p{margin:2px 0 0;font-size:13px;opacity:.85}
.awas{background:var(--no-bg);color:var(--merah);border:1px solid #F0C8CE;padding:8px 12px;margin:12px auto;border-radius:6px;font-size:13px;max-width:210mm}
.alat{position:sticky;top:0;z-index:2;background:var(--bg);display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:10px 16px;
  max-width:calc(210mm + 32px);margin:0 auto}
input,select,button{font:inherit;padding:6px 9px;border:1px solid var(--line);border-radius:6px;background:#fff}
input[type=search]{min-width:220px;flex:1}button{background:var(--biru);color:#fff;border-color:var(--biru);cursor:pointer}
button.kedua{background:#fff;color:var(--biru)}label.cek{font-size:13px;color:var(--muted);display:flex;gap:4px;align-items:center}
.ket{color:var(--muted);font-size:12.5px}
.lembar{background:var(--panel);width:210mm;max-width:calc(100% - 32px);min-height:297mm;margin:0 auto 18px;padding:14mm 14mm 10mm;
  box-shadow:0 1px 4px rgba(0,0,0,.12);display:flex;flex-direction:column}
.lembar>.isi{flex:1}
@media (max-width:820px){.lembar{min-height:0;padding:16px}}
.kop{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:2px solid var(--biru);padding-bottom:6px;margin-bottom:12px;gap:10px}
.kop .pt{font-size:11.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
.kop h2{margin:2px 0 0;font-size:18px;color:var(--biru)}.kop .en{font-style:italic;color:var(--muted);font-size:12px}
.kop .posisi{text-align:right;font-size:12px;color:var(--muted);white-space:nowrap}
.profil{display:grid;grid-template-columns:32mm 1fr;gap:14px;align-items:start}.profil.tanpa-foto{grid-template-columns:1fr}
body.resmi .profil.tanpa-foto{grid-template-columns:32mm 1fr}
.foto.slot{width:30mm;height:40mm;border:1px dashed var(--muted);background:#fff;text-align:center;line-height:1.3}
body.resmi .r-rapor,body:not(.resmi) .r-resmi,body:not(.lulus) .r-lulus,body.lulus .r-smt{display:none}
body.lulus .angka{grid-template-columns:repeat(3,1fr)}body.lulus .hal1 .dua{grid-template-columns:1fr}
body.lulus .hal1 .dua>div:first-child{max-width:125mm;margin:0 auto;width:100%}
.catatan{border:1px solid var(--line);border-radius:6px;height:40mm;margin-top:4px;
  background:repeating-linear-gradient(transparent 0 8mm,var(--line) 8mm calc(8mm + 1px));-webkit-print-color-adjust:exact;print-color-adjust:exact}
table.rencana td:nth-child(2){white-space:nowrap}table.rencana .tag{font-size:10.5px;color:var(--muted)}
.foto{width:32mm;height:42mm;border:1px solid var(--line);background:var(--biru-m10);display:flex;align-items:center;justify-content:center;
  color:var(--muted);font-size:12px;overflow:hidden}.foto img{width:100%;height:100%;object-fit:cover}
.nama{font-size:20px;font-weight:700;color:var(--biru);margin:0}.sub{color:var(--muted);font-size:13px;margin:0 0 6px}
.angka{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:6px}
.angka div{border:1px solid var(--line);border-radius:6px;padding:6px 8px}.angka b{display:block;font-size:19px;color:var(--biru)}
.angka span{font-size:11.5px;color:var(--muted)}
h3{font-size:14px;color:var(--biru);margin:14px 0 4px;border-bottom:1px solid var(--line);padding-bottom:2px}
h3 i{font-weight:400;color:var(--muted);font-size:12px}
.dua{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media (max-width:620px){.dua,.profil{grid-template-columns:1fr}.angka{grid-template-columns:repeat(2,1fr)}
  .kop{flex-direction:column;align-items:flex-start}.kop .posisi{text-align:left;white-space:normal}
  table.jalur,table.jalur tbody,table.jalur tr{display:flex;flex-wrap:wrap;width:100%}table.jalur td{flex:1 1 30%}}
table{border-collapse:collapse;width:100%;font-size:12.5px}th,td{border-bottom:1px solid var(--line);padding:3px 5px;text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.03em}td.n,th.n{text-align:right;white-space:nowrap}
table.data td:first-child{width:38%;color:var(--muted)}table.data td i{font-size:11px}
.ok{color:var(--hijau);font-weight:600}.no{color:var(--merah);font-weight:600}.en{font-style:italic;color:var(--muted);font-size:11.5px}
.leg{display:flex;gap:12px;flex-wrap:wrap;font-size:11.5px;color:var(--muted);margin-top:2px}.leg i{display:inline-block;width:16px;height:3px;vertical-align:middle;margin-right:4px}
svg text{font:11px system-ui,sans-serif;fill:var(--ink)}
ul.daftar{margin:2px 0 0;padding-left:18px;font-size:12.5px}ul.daftar li{margin:1px 0}
table.jalur td{border:1px solid var(--line);padding:3px 6px;vertical-align:top}table.jalur span{display:block;color:var(--muted);font-size:11px}
table.jalur b{font-size:13.5px;color:var(--biru)}
.ttd{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:18px;font-size:12.5px;break-inside:avoid}.ttd .ruang{height:20mm}
.kaki{border-top:1px solid var(--line);margin-top:10px;padding-top:4px;font-size:10.5px;color:var(--muted);display:flex;justify-content:space-between;gap:8px}
.peta td,.peta th{text-align:center;font-size:11.5px;padding:3px 2px}.peta td:first-child,.peta th:first-child{text-align:left}
.peta td.ok{background:var(--ok-bg)}.peta td.no{background:var(--no-bg)}
.smt-blok{break-inside:avoid;margin-top:10px}.smt-blok h4{margin:0 0 2px;font-size:13px;color:var(--biru)}
.chip{display:inline-block;border:1px solid var(--line);border-radius:10px;padding:0 7px;margin:2px 3px 0 0;font-size:11.5px}
.kosong{color:var(--muted);font-size:12.5px;margin:2px 0}
body:not(.cpl-en) .cpl-en{display:none}
@media print{
  @page{size:A4;margin:11mm}
  body{background:#fff;font-size:12px}.alat,.awas,.kepala{display:none}
  .lembar{width:auto;max-width:none;min-height:268mm;margin:0;padding:0;box-shadow:none;break-after:page}
  .lembar:last-child{break-after:auto}
  body.resmi .lembar.smt{display:none}
  body.resmi .lembar.hal2{break-after:page}
  /* Hal. 2 muat satu lembar A4 (12 CPL K21 dengan rumusan panjang, pemeriksaan 2026-11-14). */
  .hal2 table,.hal2 ul.daftar,.hal2 .kosong{font-size:10.5px}.hal2 th,.hal2 td{padding:1.5px 4px}
  .hal2 h3{margin:7px 0 2px;font-size:12.5px}.hal2 .en,.hal2 table.data td i{font-size:9.5px}.hal2 .ttd .ruang{height:15mm}
  .hal2 .dua{gap:10px}.hal2 table.data td:first-child{width:47%}.hal2 .ttd{margin-top:10px}.hal2 .ttd .ruang{height:12mm}.hal2{line-height:1.35}
  .peta td.ok,.peta td.no,.foto{-webkit-print-color-adjust:exact;print-color-adjust:exact}
}
</style></head><body>
<div class="kepala"><h1>Profil capaian pembelajaran mahasiswa</h1><p>__JUDUL__ · dibuat run_cpl.py, __DIBUAT__</p></div>
<div class="awas"><b>Memuat NIM dan nilai mahasiswa.</b> Untuk perwalian dan evaluasi internal prodi. Jangan diunggah ke situs atau dibagikan
  selain kepada mahasiswa yang bersangkutan dan dosen walinya.</div>
<div class="alat"><input type="search" id="cari" list="daftar" placeholder="Ketik NIM atau nama mahasiswa…" autocomplete="off">
  <datalist id="daftar"></datalist><select id="angkatan"><option value="">semua angkatan</option></select>
  <button type="button" class="kedua" id="sebelum" aria-label="Mahasiswa sebelumnya">‹</button>
  <button type="button" class="kedua" id="sesudah" aria-label="Mahasiswa berikutnya">›</button><span class="ket" id="jumlah"></span>
  <label class="cek">Versi <select id="versi" title="Juga mengubah tampilan di layar">
    <option value="rapor">Rapor semester (hal. 1-2 + nilai per semester; ttd orang tua dan dosen wali)</option>
    <option value="resmi">Resmi per semester (hal. 1-2; ttd dosen wali dan Kaprodi)</option>
    <option value="lulus">Resmi kelulusan (hal. 1-2; SKS lulus dan IPK; ttd Kaprodi)</option></select></label>
  <button type="button" id="cetak">Cetak</button>
  <label class="cek"><input type="checkbox" id="semua"> semua di daftar</label>
  <label class="cek" title="Rumusan CPL berbahasa Inggris di hal. 2; untuk K26 hal. 2 menjadi dua lembar"><input type="checkbox" id="cplEn"> rumusan CPL + English</label></div>
<div id="tampil"></div>
<script>
const D = __DATA__;
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const $ = id => document.getElementById(id);
const f1 = v => v == null ? '—' : (+v).toFixed(1), f2 = v => v == null ? '—' : (+v).toFixed(2);
const sks = v => v == null ? '—' : (Number.isInteger(+v) ? String(+v) : (+v).toFixed(1));
const KOP = D.kop || {}, A = D.ambang;
const HARI = new Date().toLocaleDateString('id-ID', { day: 'numeric', month: 'long', year: 'numeric' });
const pendek = t => { const m = /^(\d{4})\/(\d{4}) (.+)$/.exec(t || ''); return m ? `${m[1].slice(2)}/${m[2].slice(2)} ${m[3]}` : String(t || ''); };
const TINGKAT = { internasional: 'Internasional', nasional: 'Nasional', wilayah_lokal: 'Wilayah/lokal' };
let daftar = D.mahasiswa, pos = 0;

function radar(axes, seri, ambang){
  const W = 440, H = 400, cx = W / 2, cy = H / 2, R = 145, n = axes.length;
  const pt = (i, v) => { const a = -Math.PI / 2 + 2 * Math.PI * i / n, r = R * Math.max(0, Math.min(100, v)) / 100;
    return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; };
  const poly = vals => axes.map((c, i) => pt(i, vals[c] ?? 0).map(x => x.toFixed(1)).join(',')).join(' ');
  let g = '';
  for (const lv of [20, 40, 60, 80, 100]) g += `<polygon points="${poly(Object.fromEntries(axes.map(c => [c, lv])))}" fill="none" stroke="#D9DFDA"/>`;
  axes.forEach((c, i) => { const [x, y] = pt(i, 100), [lx, ly] = pt(i, 111);
    g += `<line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="#D9DFDA"/><text x="${lx}" y="${ly}" text-anchor="middle" dominant-baseline="middle" font-weight="600">${esc(c)}</text>`; });
  for (const lv of [20, 40, 60, 80]) { const [x, y] = pt(0, lv); g += `<text x="${x + 4}" y="${y}" fill="#5D6B78" font-size="9.5">${lv}</text>`; }
  g += `<polygon points="${poly(Object.fromEntries(axes.map(c => [c, ambang])))}" fill="none" stroke="var(--merah)" stroke-dasharray="5 4" stroke-width="1.5"/>`;
  for (const s of seri) {
    g += `<polygon points="${poly(s.v)}" fill="${s.isi || 'none'}" fill-opacity=".18" stroke="${s.warna}" stroke-width="${s.tebal || 2}"${s.putus ? ' stroke-dasharray="6 4"' : ''}/>`;
    if (s.titik) axes.forEach((c, i) => { if (s.v[c] == null) return; const [x, y] = pt(i, s.v[c]);
      g += `<circle cx="${x}" cy="${y}" r="3.5" fill="${s.v[c] >= ambang ? 'var(--hijau)' : 'var(--merah)'}"><title>${esc(c)}: ${s.v[c]}</title></circle>`; });
  }
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Radar CPL">${g}</svg>`;
}
// Grafik per semester: garis (seri.jenis 'garis') atau batang, sumbu y 0..maks.
function grafik(terms, seri, maks, langkah){
  // Lebih dari 6 semester: label miring agar tidak bertumpuk (10 semester data K21, pemilik 2026-11-14).
  const miring = terms.length > 6;
  const W = 420, H = miring ? 214 : 190, L = 30, Rr = 8, T = 12, B = miring ? 54 : 30, w = W - L - Rr, h = H - T - B, n = Math.max(1, terms.length);
  const x = i => L + w * (i + .5) / n, y = v => T + h * (1 - Math.max(0, Math.min(maks, v)) / maks);
  let g = '';
  for (let v = 0; v <= maks + 1e-9; v += langkah) g += `<line x1="${L}" x2="${W - Rr}" y1="${y(v)}" y2="${y(v)}" stroke="#E4E8E5"/>`
    + `<text x="${L - 4}" y="${y(v) + 3.5}" text-anchor="end" fill="#5D6B78" font-size="9.5">${+v.toFixed(2)}</text>`;
  terms.forEach((t, i) => { g += miring
    ? `<text x="${x(i) + 3}" y="${T + h + 12}" text-anchor="end" font-size="9.5" fill="#5D6B78" transform="rotate(-35 ${x(i) + 3} ${T + h + 12})">${esc(pendek(t))}</text>`
    : `<text x="${x(i)}" y="${H - 12}" text-anchor="middle" font-size="9.5" fill="#5D6B78">${esc(pendek(t))}</text>`; });
  for (const s of seri) {
    if (s.jenis === 'batang') {
      const bw = Math.min(34, w / n * .55);
      s.v.forEach((v, i) => { if (v == null) return;
        g += `<rect x="${x(i) - bw / 2}" y="${y(v)}" width="${bw}" height="${y(0) - y(v)}" fill="${s.warna}" rx="2"/>`
          + `<text x="${x(i)}" y="${y(v) - 3}" text-anchor="middle" font-size="10" font-weight="600">${esc(s.label ? s.label(v) : v)}</text>`; });
    } else {
      const p = s.v.map((v, i) => v == null ? null : `${x(i).toFixed(1)},${y(v).toFixed(1)}`).filter(Boolean);
      if (p.length > 1) g += `<polyline points="${p.join(' ')}" fill="none" stroke="${s.warna}" stroke-width="2"${s.putus ? ' stroke-dasharray="5 4"' : ''}/>`;
      s.v.forEach((v, i) => { if (v != null) g += `<circle cx="${x(i)}" cy="${y(v)}" r="3" fill="${s.warna}"><title>${esc(terms[i])}: ${v}</title></circle>`; });
      const iAkhir = s.v.map(v => v != null).lastIndexOf(true);
      if (iAkhir >= 0) g += `<text x="${x(iAkhir) + 5}" y="${y(s.v[iAkhir]) - 5}" font-size="10" font-weight="600" fill="${s.warna}">${esc(s.label ? s.label(s.v[iAkhir]) : s.v[iAkhir])}</text>`;
    }
  }
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img">${g}</svg>`;
}
// versi: [[kelas, judul, en], ...] bila judul berbeda per versi (r-rapor, r-resmi r-smt, r-lulus).
function kop(judul, en, m, versi){
  const akhir = m.smt.length ? m.smt[m.smt.length - 1].term : '';
  const pt = [KOP.university, KOP.faculty, KOP.programme && `Program Studi ${KOP.programme}`].filter(Boolean).map(esc).join(' · ');
  return `<div class="kop"><div><div class="pt">${pt}</div>${versi ? `<h2>${versi.map(([c, j]) => `<span class="${c}">${esc(j)}</span>`).join('')}</h2>
    <div class="en">${versi.map(([c, , e]) => `<span class="${c}">${esc(e)}</span>`).join('')}</div>` : `<h2>${esc(judul)}</h2><div class="en">${esc(en)}</div>`}</div>
    <div class="posisi">${akhir ? `Data s.d. ${esc(akhir)}` : ''}<br>Dicetak ${esc(HARI)}</div></div>`;
}
const kaki = (m, hal) => `<div class="kaki"><span>${esc(m.nama || '')} · NIM ${esc(m.nim)}</span><span>${esc(hal)}</span></div>`;
function ringkas(m, k){
  const akhir = m.smt[m.smt.length - 1] || {};
  const capai = k.cpl.filter(c => (m.skor[c] ?? -1) >= A).length, ada = k.cpl.filter(c => m.skor[c] != null).length;
  return { akhir, capai, ada, sksAmbil: m.smt.reduce((a, s) => a + (s.sks || 0), 0), nSmt: m.smt.filter(s => s.mk.length && !s.pendek).length };
}
// Semester ke-N dari angkatan dan semester reguler terakhir (term_order = tahun x 10 + urutan semester_order:
// Ganjil 1, Genap 2). Semester pendek tidak menambah N.
function smtKe(m){
  const reg = m.smt.filter(s => !s.pendek && s.term_order), t = reg.length ? reg[reg.length - 1].term_order : null;
  if (!t || !m.angkatan) return null;
  const n = (Math.floor(t / 10) - +m.angkatan) * 2 + t % 10;
  return n > 0 ? n : null;
}
function hal1(m, k, r){
  const rata = D.rata[`${m.kur}|${m.angkatan}`] || {};
  const terms = m.smt.map(s => s.term);
  const tercapai = m.smt.map(s => Object.keys(s.kum).length ? k.cpl.filter(c => (s.kum[c] ?? -1) >= A).length : null);
  const g1 = k.cpl.length ? `${radar(k.cpl, [{ v: rata, warna: 'var(--emas)', putus: true }, { v: m.skor, warna: 'var(--biru)', isi: 'var(--biru-3)', tebal: 2.5, titik: true }], A)}
      <div class="leg"><span><i style="background:var(--biru)"></i>skor mahasiswa</span><span><i style="background:var(--emas)"></i>rata-rata angkatan ${esc(m.angkatan || '?')}</span>
      <span><i style="background:var(--merah)"></i>ambang ${A}</span></div>` : '<p class="kosong">Belum ada skor CPL.</p>';
  // IPS mahasiswa dibanding rata-rata IPS angkatan (pemilik 2026-11-14); IPK ada di tile.
  const ri = (D.rata_ips || {})[`${m.kur}|${m.angkatan}`] || {};
  const ipk = D.skala && m.smt.some(s => s.ips != null) ? `<h3>IPS per semester <i>Semester GPA</i></h3>
      ${grafik(terms, [{ v: m.smt.map(s => ri[s.term_order] ?? null), warna: 'var(--emas)', putus: true, label: f2 }, { v: m.smt.map(s => s.ips ?? null), warna: 'var(--biru)', label: f2 }], 4, 1)}
      <div class="leg"><span><i style="background:var(--biru)"></i>IPS mahasiswa</span><span><i style="background:var(--emas)"></i>rata-rata IPS angkatan ${esc(m.angkatan || '?')}</span></div>` : '';
  const cplSmt = k.cpl.length && tercapai.some(v => v != null) ? `<h3>CPL tercapai, kumulatif <i>Outcomes attained, cumulative</i></h3>
      ${grafik(terms, [{ jenis: 'batang', v: tercapai, warna: 'var(--biru-3)', label: v => `${v}/${k.cpl.length}` }], k.cpl.length, Math.max(1, Math.ceil(k.cpl.length / 4)))}
      <p class="ket">Jumlah CPL dengan skor kumulatif ≥ ${A} sampai akhir tiap semester.</p>` : '';
  const n = smtKe(m), sarjana = (D.sks_sarjana || {})[m.kur];
  const ips = [...m.smt].reverse().find(s => s.ips != null) || {};
  return `<section class="lembar hal1"><div class="isi">${kop('', '', m, [
      ['r-rapor', n ? `Rapor Capaian Pembelajaran · Semester ${n}` : 'Rapor Capaian Pembelajaran', n ? `Learning Outcomes Report · Semester ${n}` : 'Learning Outcomes Report'],
      ['r-resmi r-smt', 'Profil Capaian Pembelajaran Mahasiswa', 'Student Learning Outcomes Profile'],
      ['r-lulus', 'Profil Capaian Pembelajaran Lulusan', 'Graduate Learning Outcomes Profile']])}
    <div class="profil${m.foto ? '' : ' tanpa-foto'}">${m.foto ? `<div class="foto"><img src="${m.foto}" alt="Foto ${esc(m.nama)}"></div>`
      // Versi resmi tanpa foto digital: slot pas foto 3x4 untuk ditempel (pemilik 2026-11-14).
      : '<div class="foto slot r-resmi">Pas foto<br>3 × 4</div>'}
      <div><p class="nama">${esc(m.nama || m.nim)}</p><p class="sub">NIM ${esc(m.nim)} · angkatan ${esc(m.angkatan || '?')} · kurikulum ${esc(m.kur)}${
        m.wali ? `<span class="r-smt"> · dosen wali ${esc(m.wali.nama || m.wali.email)}</span>` : ''}</p>
        <div class="angka"><div><b>${r.capai}/${k.cpl.length || '—'}</b><span>CPL tercapai (≥ ${A})</span></div>
          <div class="r-smt"><b>${D.skala ? `${f2(ips.ips)} / ${f2(r.akhir.ipk)}` : '—'}</b><span>${D.skala ? `IPS ${esc(pendek(ips.term || ''))} / IPK` : 'IPK (skala nilai belum diatur)'}</span></div>
          <div class="r-smt"><b>${sks(r.sksAmbil)}${D.skala ? ` / ${sks(r.akhir.sks_lulus)}` : ''}</b><span>${
            D.skala ? 'SKS ditempuh / lulus' : 'SKS ditempuh'}${sarjana ? `<br>dari ${sarjana} SKS sarjana` : ''}</span></div>
          <div class="r-smt"><b>${n ? `Semester ${n}` : r.nSmt}</b><span>${n ? `tahun ke-${Math.ceil(n / 2)}` : 'semester reguler berdata nilai'}</span></div>
          <div class="r-lulus"><b>${D.skala ? f2(r.akhir.ipk) : '—'}</b><span>IPK <i class="en">GPA</i></span></div>
          <div class="r-lulus"><b>${D.skala ? sks(r.akhir.sks_lulus) : '—'}</b><span>SKS lulus <i class="en">Credits earned</i></span></div></div></div></div>
    <h3>Capaian CPL kumulatif <i>Cumulative learning outcomes</i></h3>
    <div class="dua"><div>${g1}</div><div class="r-smt">${ipk}${cplSmt}</div></div></div>${kaki(m, 'Halaman 1')}</section>`;
}
// Rencana pencapaian CPL (rapor; pemilik 2026-11-14): CPL di bawah ambang, atau bila semua tercapai
// D.rencana.terendah CPL dengan skor terendah; MK pendukung dari ref_mk_cpl: ulang (pernah, belum lulus),
// wajib belum ditempuh (urut semester kurikulum), lalu pilihan; paling banyak D.rencana.maks per CPL.
function rencana(m, k){
  const mk = k.mk || [];
  if (!k.cpl.length || !mk.length) return '';
  const lulus = new Set(), gagal = {};
  for (const s of m.smt) for (const x of s.mk) { if (x.lulus) lulus.add(x.kode); else gagal[x.kode] = x; }
  for (const kd of lulus) delete gagal[kd];
  let target = k.cpl.filter(c => m.skor[c] == null || m.skor[c] < A);
  const semua = !target.length;
  if (semua) target = k.cpl.filter(c => m.skor[c] != null).sort((a, b) => m.skor[a] - m.skor[b]).slice(0, D.rencana.terendah);
  if (!target.length) return '';
  const n = smtKe(m) || 0;
  const baris = target.map(c => {
    const dukung = mk.filter(x => x.cpl.includes(c) && !lulus.has(x.kode));
    const ulang = dukung.filter(x => gagal[x.kode]).map(x => `${esc(x.nama)} <span class="tag">ulang, ${esc(gagal[x.kode].huruf || 'belum lulus')}</span>`);
    const wajib = dukung.filter(x => !gagal[x.kode] && x.sifat === 'wajib').sort((a, b) => (a.smt ?? 99) - (b.smt ?? 99))
      .map(x => `${esc(x.nama)} <span class="tag">smt ${x.smt ?? '?'}${x.smt != null && x.smt <= n ? ', tertinggal' : ''}</span>`);
    const pilih = dukung.filter(x => !gagal[x.kode] && x.sifat !== 'wajib').map(x => `${esc(x.nama)} <span class="tag">pilihan</span>`);
    const xs = [...ulang, ...wajib, ...pilih].slice(0, D.rencana.maks), s = m.skor[c];
    return `<tr><td><b>${esc(c)}</b></td><td class="${s == null ? '' : s >= A ? 'ok' : 'no'}">${f1(s)}${s != null && s < A ? ` <span class="tag">kurang ${f1(A - s)}</span>` : ''}</td>
      <td>${xs.length ? xs.join('; ') : '<span class="ket">Semua MK yang memetakan CPL ini sudah lulus; bahas di perwalian.</span>'}</td></tr>`;
  }).join('');
  return `<div class="r-rapor"><h3>Rencana pencapaian CPL <i>Plan for the next semesters</i></h3>
    <p class="ket" style="margin:0 0 3px">${semua ? `Semua CPL sudah ≥ ${A}. CPL dengan skor terendah dan MK yang masih bisa menguatkannya:`
      : `CPL di bawah ambang ${A} (atau belum ada skor) dan MK yang bisa memperbaikinya: ulang MK yang belum lulus, lalu MK wajib yang belum ditempuh.`}</p>
    <table class="rencana"><thead><tr><th>CPL</th><th>Skor</th><th>MK pendukung <i>Supporting courses</i></th></tr></thead><tbody>${baris}</tbody></table></div>`;
}
function hal2(m, k, r){
  const i = m.info || {}, baris = xs => xs.filter(x => x[2] !== '' && x[2] != null)
    .map(([a, en, v, kelas]) => `<tr${kelas ? ` class="${kelas}"` : ''}><td>${esc(a)} <i class="en">${esc(en)}</i></td><td>${esc(v)}</td></tr>`).join('');
  const ttl = [i.tempat_lahir, i.tanggal_lahir].filter(Boolean).join(', ');
  // Bagian 3 sebagai satu jalur angka selebar halaman (hal. 2 muat satu lembar A4).
  const jalur = xs => `<table class="jalur"><tr>${xs.filter(x => x[2] !== '' && x[2] != null).map(([a, en, v]) =>
    `<td><span>${esc(a)} <i class="en">${esc(en)}</i></span><b>${esc(v)}</b></td>`).join('')}</tr></table>`;
  const daftar = (xs, f) => xs.length ? `<ul class="daftar">${xs.map(x => `<li>${f(x)}</li>`).join('')}</ul>` : '<p class="kosong">Belum ada data.</p>';
  // Tanda tangan (pemilik 2026-11-14): rapor = orang tua/wali dan dosen wali; resmi = dosen wali dan Kaprodi.
  const wali = ['Dosen Wali', 'Academic Advisor', m.wali ? m.wali.nama || '' : ''];
  const ttd = (xs, kelas) => `<div class="ttd ${kelas}">${xs.map(([a, en, nm], j) => `<div>${j === xs.length - 1 ? `${esc([KOP.city, HARI].filter(Boolean).join(', '))}<br>` : '<br>'}${esc(a)}<br><span class="en">${esc(en)}</span><div class="ruang"></div>
        <b>${nm ? esc(nm) : '……………………………'}</b></div>`).join('')}</div>`;
  // Kelulusan: hanya Kaprodi (lulusan tidak lagi berdosen wali; usulan Claude 2026-11-14).
  const kaprodi = KOP.head_title ? [KOP.head_title, 'Head of Study Programme', KOP.head_name || ''] : null;
  const resmi = [m.wali ? wali : null, kaprodi].filter(Boolean);
  return `<section class="lembar hal2"><div class="isi">${kop('', '', m, [
      ['r-rapor', 'Keterangan dan Rencana Capaian Pembelajaran', 'Learning Outcomes Statement and Plan'],
      ['r-resmi r-smt', 'Keterangan Capaian Pembelajaran', 'Learning Outcomes Statement'],
      ['r-lulus', 'Keterangan Capaian Pembelajaran Lulusan', 'Graduate Learning Outcomes Statement']])}
    <div class="dua"><div><h3>Identitas <i>Personal information</i></h3><table class="data">${baris([
      ['Nama', 'Name', m.nama], ['NIM', 'Student ID', m.nim], ['Tempat, tanggal lahir', 'Place, date of birth', ttl, 'r-resmi'],
      ['Tanggal masuk', 'Date of entry', i.tanggal_masuk, 'r-resmi'], ['Angkatan', 'Cohort', m.angkatan], ['Status', 'Status', i.status],
      ['Dosen wali', 'Academic advisor', m.wali ? (m.wali.nama || m.wali.email) : '', 'r-smt']])}</table></div>
    <div class="r-rapor"><h3>Catatan dosen wali <i>Advisor's notes</i></h3><div class="catatan"></div></div>
    <div class="r-resmi"><h3>Program studi <i>Study programme</i></h3><table class="data">${baris([
      ['Perguruan tinggi', 'University', KOP.university || ''], ['Fakultas', 'Faculty', KOP.faculty || ''],
      ['Program studi', 'Study programme', KOP.programme || ''], ['Jenjang', 'Level', KOP.degree || ''], ['Kurikulum', 'Curriculum', m.kur]])}</table></div></div>
    <div class="r-resmi r-smt"><h3>Ringkasan akademik <i>Academic summary</i></h3>${jalur([
      ['Data s.d.', 'Up to', r.akhir.term || ''], ['Semester reguler', 'Regular semesters', r.nSmt],
      ['SKS ditempuh', 'Credits taken', sks(r.sksAmbil)], ['SKS lulus', 'Credits passed', D.skala ? sks(r.akhir.sks_lulus) : ''],
      ['IPK', 'GPA', D.skala ? f2(r.akhir.ipk) : ''], ['CPL tercapai', 'Outcomes met', k.cpl.length ? `${r.capai} dari ${k.cpl.length}` : '']])}</div>
    <div class="r-lulus"><h3>Ringkasan akademik <i>Academic summary</i></h3>${jalur([
      ['SKS lulus', 'Credits earned', D.skala ? sks(r.akhir.sks_lulus) : ''], ['IPK', 'GPA', D.skala ? f2(r.akhir.ipk) : ''],
      ['CPL tercapai', 'Outcomes met', k.cpl.length ? `${r.capai} dari ${k.cpl.length}` : '']])}</div>
    <h3>Capaian pembelajaran lulusan <i>Programme learning outcomes</i></h3>
    ${k.cpl.length ? `<table><thead><tr><th>CPL</th><th>Rumusan <i>Statement</i></th><th class="n">Skor <i>Score</i></th></tr></thead><tbody>
      ${k.cpl.map(c => { const s = m.skor[c]; return `<tr><td><b>${esc(c)}</b></td><td>${esc(k.teks[c] || '')}${k.teks_en[c] ? `<span class="en cpl-en"><br>${esc(k.teks_en[c])}</span>` : ''}</td>
        <td class="n ${s == null ? '' : s >= A ? 'ok' : 'no'}">${f1(s)}${s == null ? '' : s >= A ? ' Tercapai' : ' Belum'}</td></tr>`; }).join('')}
      </tbody></table>` : '<p class="kosong">Belum ada skor CPL.</p>'}
    ${rencana(m, k)}
    <h3>Prestasi dan penghargaan <i>Achievements and awards</i></h3>
    ${daftar(m.prestasi, p => `${esc(p.nama_kegiatan)}${p.capaian ? ` — <b>${esc(p.capaian)}</b>` : ''} <span class="ket">(${[TINGKAT[p.tingkat] || p.tingkat, p.penyelenggara, p.tahun].filter(Boolean).map(esc).join(', ')})</span>`)}
    <h3>Karya dan publikasi <i>Works and publications</i></h3>
    ${daftar(m.karya, p => `${esc(p.judul)} <span class="ket">(${[p.jenis, p.terbitan, p.tahun, p.peran].filter(Boolean).map(esc).join(', ')})</span>`)}
    <h3>Sertifikat, organisasi, magang <i>Certificates, organisations, internships</i></h3>
    ${daftar(m.kegiatan, p => `${esc(p.nama)}${p.peran ? ` — ${esc(p.peran)}` : ''} <span class="ket">(${[p.jenis, p.penyelenggara, p.tahun].filter(Boolean).map(esc).join(', ')})</span>`)}
    ${ttd([['Orang Tua/Wali', 'Parent/Guardian', ''], wali], 'r-rapor')}${resmi.length ? ttd(resmi, 'r-resmi r-smt') : ''}${kaprodi ? ttd([kaprodi], 'r-lulus') : ''}
    </div>${kaki(m, 'Halaman 2')}</section>`;
}
function hal3(m, k){
  if (!m.smt.length) return '';
  const peta = k.cpl.length ? `<h3>CPL kumulatif per semester <i>Cumulative outcomes by semester</i></h3>
    <table class="peta"><thead><tr><th>CPL</th>${m.smt.map(s => `<th>${esc(pendek(s.term))}</th>`).join('')}</tr></thead><tbody>
    ${k.cpl.map(c => `<tr><td><b>${esc(c)}</b></td>${m.smt.map(s => { const v = s.kum[c];
      return `<td class="${v == null ? '' : v >= A ? 'ok' : 'no'}">${f1(v)}</td>`; }).join('')}</tr>`).join('')}</tbody></table>
    <p class="ket">Hijau: skor kumulatif ≥ ${A} sampai akhir semester itu; merah: di bawah ambang; — belum ada MK yang memetakan CPL itu.</p>` : '';
  const blok = m.smt.map(s => `<div class="smt-blok"><h4>${esc(s.term)}${s.pendek ? ' <span class="ket">(semester pendek)</span>' : ''}</h4><p class="ket" style="margin:0 0 3px">SKS ${sks(s.sks)}${
      D.skala ? ` · IPS ${f2(s.ips)} · IPK ${f2(s.ipk)} · SKS lulus kumulatif ${sks(s.sks_lulus)}` : ''}</p>
    ${s.mk.length ? `<table><thead><tr><th>Kode</th><th>Mata kuliah</th><th class="n">SKS</th><th class="n">Nilai</th>${D.skala ? '<th>Huruf</th>' : ''}</tr></thead><tbody>
      ${s.mk.map(x => `<tr><td>${esc(x.kode)}</td><td>${esc(x.nama)}</td><td class="n">${sks(x.sks)}</td><td class="n">${f1(x.nilai)}</td>${D.skala ? `<td>${esc(x.huruf || '—')}</td>` : ''}</tr>`).join('')}
      </tbody></table>` : '<p class="kosong">Nilai akhir MK semester ini tidak ada di berkas nilai akhir (hanya templat CPL rinci).</p>'}
    ${Object.keys(s.cpl).length ? `<div class="ket" style="margin-top:3px">CPL dari MK semester ini: ${Object.entries(s.cpl).sort()
      .map(([c, v]) => `<span class="chip ${v >= A ? 'ok' : 'no'}">${esc(c)} ${f1(v)}</span>`).join('')}</div>` : ''}</div>`).join('');
  return `<section class="lembar smt"><div class="isi">${kop('Perkembangan per Semester', 'Progress by Semester', m)}${peta}
    <h3>Nilai per semester <i>Grades by semester</i></h3>${blok}
    <p class="ket">Skor CPL kumulatif memakai percobaan terbaik tiap MK sampai semester itu. Untuk semester sebelum templat CPL rinci,
      skor adalah estimasi dari nilai akhir MK.</p></div>${kaki(m, 'Halaman 3 dst. (perkembangan)')}</section>`;
}
function halaman(m){
  const k = D.kurikulum[m.kur] || { cpl: [], teks: {}, teks_en: {} }, r = ringkas(m, k);
  return hal1(m, k, r) + hal2(m, k, r) + hal3(m, k);
}
function gambar(){
  $('jumlah').textContent = daftar.length ? `${pos + 1} dari ${daftar.length}` : 'tidak ada yang cocok';
  $('tampil').innerHTML = daftar[pos] ? halaman(daftar[pos]) : '<p class="ket" style="text-align:center">Tidak ada mahasiswa yang cocok.</p>';
}
function versi(){
  const v = $('versi').value;
  document.body.classList.toggle('resmi', v !== 'rapor');
  document.body.classList.toggle('lulus', v === 'lulus');
}
function cetak(){
  versi();
  if ($('semua').checked) $('tampil').innerHTML = daftar.map(halaman).join('');
  print();
}
addEventListener('afterprint', () => { if ($('semua').checked) gambar(); });
$('versi').onchange = versi;
function saring(){
  const q = $('cari').value.trim().toLowerCase(), a = $('angkatan').value;
  daftar = D.mahasiswa.filter(m => (!a || String(m.angkatan) === a) && (!q || m.nim.includes(q) || (m.nama || '').toLowerCase().includes(q)));
  pos = 0; gambar();
}
$('daftar').innerHTML = D.mahasiswa.map(m => `<option value="${esc(m.nim)}">${esc(m.nama)}</option>`).join('');
$('angkatan').innerHTML += [...new Set(D.mahasiswa.map(m => m.angkatan).filter(Boolean))].sort().map(a => `<option>${a}</option>`).join('');
$('cari').oninput = saring; $('angkatan').onchange = saring;
$('sebelum').onclick = () => { if (pos > 0) { pos--; gambar(); } };
$('sesudah').onclick = () => { if (pos < daftar.length - 1) { pos++; gambar(); } };
$('cplEn').onchange = e => document.body.classList.toggle('cpl-en', e.target.checked);
$('cetak').onclick = cetak;
gambar();
</script></body></html>
"""
