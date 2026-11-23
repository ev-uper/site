"""Analisis ketercapaian CPL dari berkas nilai (Template_Input_Data_CPL.xlsx).

Jalankan tanpa argumen (VS Code: Run). Pilihan dibaca dari config.yaml,
path mesin dari config.local.yaml (contoh: config.local.yaml.contoh).

    python run_cpl.py
    python run_cpl.py --input-dir D:/CPL/berkas --output-dir D:/CPL/laporan   # penimpa sementara
    python run_cpl.py --source folder                                        # baca folder sendiri, tanpa unduh

source: site (bawaan, pemilik 2026-11-11): berkas terbaru tiap kelas diunduh dari Drive
privat prodi lewat Apps Script (kunci CPL_KUNCI di env atau rahasia.env) ke
paths.input_dir/_dari_situs, lalu dihitung. source: folder: berkas ditaruh sendiri.

Opsional (pemilik 2026-11-13): paths.final_grades_dir = folder nilai akhir per kelas dari
kampus; capaian CPL semester lama diestimasi dari nilai akhir MK (config.yaml final_grades,
cpl/final_grades.py) dan ditandai estimasi.

Keluaran di paths.output_dir: laporan_cpl.xlsx, ringkasan_cpl.json, radar_mahasiswa.html (profil CPL per mahasiswa),
perwalian/<wali>.html (bila paths.advisors_csv diisi), dan run_cpl.log.
Laporan MEMUAT NIM: simpan di luar repo, jangan diunggah ke situs.
ringkasan_cpl.json TANPA NIM (angka agregat): inilah yang diunggah admin di
situs, Monitoring > Capaian CPL (pemilik 2026-11-11).
"""
import argparse
from datetime import datetime
import logging
import sys
from pathlib import Path

from cpl.archive import build_report, load_folder, write_report, write_summary
from cpl.config import load_config, validate_config
from cpl.final_grades import prepare_final
from cpl.student_record import removals
from cpl.radar import build_records, load_cpl_text, load_cpl_text_en, write_student_radar
from cpl.unduh import SUBFOLDER, baca_kunci, baca_url, unduh_semua

ROOT = Path(__file__).resolve().parent
log = logging.getLogger("run_cpl")


def _close_logging():
    for h in list(log.handlers):
        log.removeHandler(h)
        h.close()


def _setup_logging(output_dir):
    _close_logging()
    output_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    handlers = [logging.StreamHandler(sys.stdout),
                logging.FileHandler(output_dir / "run_cpl.log", mode="w", encoding="utf-8")]
    for h in handlers:
        h.setFormatter(fmt)
        log.addHandler(h)
    log.setLevel(logging.INFO)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--config", default=ROOT / "config.yaml", type=Path, help="bawaan: config.yaml di sebelah skrip")
    p.add_argument("--input-dir", type=Path, help="menimpa paths.input_dir sementara")
    p.add_argument("--output-dir", type=Path, help="menimpa paths.output_dir sementara")
    p.add_argument("--source", choices=["site", "folder"], help="menimpa source sementara (site = unduh dari situs)")
    a = p.parse_args(argv)

    cfg = load_config(a.config)
    cfg.setdefault("paths", {})
    if a.input_dir:
        cfg["paths"]["input_dir"] = str(a.input_dir)
    if a.output_dir:
        cfg["paths"]["output_dir"] = str(a.output_dir)
    if a.source:
        cfg["source"] = a.source

    errors = validate_config(cfg, ROOT)
    if errors:
        print("Config tidak sah, tidak ada berkas yang dibaca:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 2

    input_dir, output_dir = Path(cfg["paths"]["input_dir"]), Path(cfg["paths"]["output_dir"])
    _setup_logging(output_dir)
    try:
        return _run(cfg, a.config, input_dir, output_dir)
    finally:
        _close_logging()


def _run(cfg, config_path, input_dir, output_dir):
    th = cfg["thresholds"]
    log.info("config     : %s", config_path)
    log.info("input_dir  : %s", input_dir)
    log.info("output_dir : %s", output_dir)
    log.info("ambang     : individu %s, kelas %s%%", th["student"], th["class_pct"])
    log.info("semester   : %s", cfg["semester_order"])
    log.info("templat    : %s", ", ".join(cfg["template_versions"]))
    log.info("aturan     : retake=%s, course_weight=%s", cfg["retake"], cfg["course_weight"])
    log.info("sumber     : %s", cfg.get("source", "folder"))
    if cfg.get("source", "folder") == "site":
        # Pilihan 2 (pemilik 2026-11-11): berkas dari Drive privat lewat Apps Script; kunci tidak dicatat.
        try:
            url, kunci = baca_url(ROOT), baca_kunci(ROOT)
            input_dir = input_dir / SUBFOLDER
            got = unduh_semua(url, kunci, input_dir)
        except Exception as e:  # noqa: BLE001 - pesan jelas ke admin, lalu berhenti
            log.error("unduh dari situs gagal: %s", e)
            return 3
        log.info("unduhan   : %d berkas ke %s", len(got), input_dir)

    files = load_folder(input_dir, cfg)
    used = [f for f in files if f.ok]
    log.info("berkas     : %d dibaca, %d dipakai, %d ditolak", len(files), len(used), len(files) - len(used))
    for f in files:
        if not f.ok:
            log.warning("DITOLAK %s: %s", f.path.name, "; ".join(f.problems))

    final = prepare_final(cfg, ROOT, files)
    if final is not None:
        fg = cfg["final_grades"]
        log.info("nilai akhir: %s (estimasi; kurikulum %s; bobot %s; nol semua komponen %s)",
                 cfg["paths"]["final_grades_dir"], fg["curriculum_by_year"], fg["course_weight"],
                 "tidak dihitung" if fg["exclude_all_zero"] else "dihitung")
        log.info("rujukan    : %s (%d MK, %d pasangan MK-CPL)", fg["reference_dir"],
                 final["reference"]["mk"], final["reference"]["peta"])
        if not final["reference"]["peta"]:
            log.warning("peta MK-CPL kosong di %s: jalankan workflow Pemeliharaan (cadangkan) lalu git pull",
                        fg["reference_dir"])
        ff = final["files"]
        log.info("berkas NA  : %d dibaca, %d dipakai, %d ditolak", len(ff), sum(f.ok for f in ff),
                 sum(not f.ok for f in ff))
        for f in ff:
            if f.ok:
                i = f.identity
                log.info("  %s -> %s %s %s kelas %s, %s; %d dihitung, %d nol (%s)", f.path.name, i["curriculum"],
                         i["course_code"], i["course_name"], i["class_name"], f.term, len(f.students),
                         f.excluded_zero, "; ".join(f.notes))
            else:
                log.warning("DITOLAK %s: %s", f.path.name, "; ".join(f.problems))
    # MK yang disetujui dihapus per mahasiswa (pemilik 2026-11-14): keluar dari tabel student_* dan profil.
    removed = removals(cfg)
    report = build_report(files, cfg, final, removed)
    path = write_report(report, output_dir, cfg)
    ringkasan = write_summary(report, files, cfg, output_dir, datetime.now().astimezone().isoformat(timespec="seconds"),
                              final["files"] if final else ())
    # Radar per mahasiswa (pemilik 2026-11-13): lokal, MEMUAT NIM, untuk perwalian; tidak diunggah.
    names = {n: m for f in (final["files"] if final else []) for n, m in f.names.items()}
    teks = load_cpl_text(ROOT, cfg)
    for f in files:
        if f.ok and f.template is not None:
            for code, t in zip(f.template.cpl, f.template.cpl_text or []):
                if code and t:
                    teks.setdefault((f.identity["curriculum"], code), t)
    # Profil per mahasiswa (pemilik 2026-11-14): nilai per semester, identitas, wali, foto, prestasi.
    sr = cfg["student_record"]
    log.info("profil     : skala nilai %s; status prestasi/karya %s; foto maks %s px",
             f"{len(sr['grade_scale'])} huruf, lulus >= {sr['pass_min_point']}, ulang={sr['gpa_retake']}, "
             f"tidak lulus ikut IPK={sr['gpa_include_failed']}" if sr["grade_scale"]
             else "belum diisi (IPS/IPK/huruf tidak ditampilkan)", sr["record_statuses"], sr["photo_max_px"])
    record = build_records(cfg, ROOT, final["files"] if final else (), removed)
    radar = write_student_radar(report, cfg, output_dir, names, teks, record, load_cpl_text_en(ROOT, cfg))

    na = report["not_achieved"]
    log.info("CPL belum tercapai per kelas: %d baris", len(na))
    cum = report["cpl_cumulative"]
    for _, row in cum.iterrows():
        log.info("kumulatif %s %s: %d mahasiswa, rata-rata %.1f, %.0f%% >= %s -> %s%s",
                 row["curriculum"], row["cpl"], row["students"], row["mean_score"],
                 100 * row["share_achieved"], th["student"], row["status"],
                 " (estimasi)" if row.get("estimate") == True else "")  # noqa: E712 (numpy bool)
    log.info("laporan    : %s (memuat NIM, jangan diunggah)", path)
    log.info("ringkasan  : %s (tanpa NIM; unggah di situs, Monitoring > Capaian CPL)", ringkasan)
    if radar:
        log.info("radar      : %s (memuat NIM; untuk perwalian, jangan diunggah)", radar)
    return 0 if used or (final and any(f.ok for f in final["files"])) else 1


if __name__ == "__main__":
    sys.exit(main())
