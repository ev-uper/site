"""Penyusunan jadwal kuliah: hari dan jam tiap kelas (rencana pemilik 2026-11-21, aturan pemilik 2026-11-22).

Alur:
  1. Situs: Jadwal kuliah > Unduh masukan penjadwalan -> jadwal_masukan_<TA>_<semester>.json, simpan ke
     config.local.yaml paths.schedule_dir.
  2. Jalankan tanpa argumen (VS Code ▶):  python run_jadwal.py
     Berkas masukan terbaru di folder itu dipakai. Aturan dibaca dari config.yaml bagian schedule.
  3. Hasil di subfolder hasil_<TA>_<semester>_<waktu>: hasil_jadwal_*.csv (impor di situs: Jadwal kuliah > Impor hasil),
     jadwal_*.xlsx (Jadwal, Per hari, Per dosen, Catatan), laporan_jadwal.txt, run_jadwal.log.
Ruang tidak ditempatkan: ruang dari universitas diisi prodi di situs (pemilik 2026-11-22).

Argumen opsional, hanya menimpa sementara:  --masukan <berkas.json>  --keluar <folder>  --batas-waktu <detik>
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

AKAR = Path(__file__).resolve().parent
sys.path.insert(0, str(AKAR))
from cpl.config import load_config  # noqa: E402
from jadwal.aturan import baca_aturan, ringkas  # noqa: E402
from jadwal.keluaran import baris_jadwal, laporan, tulis_csv, tulis_excel  # noqa: E402
from jadwal.masukan import baca_masukan  # noqa: E402
from jadwal.model import periksa, saran_tidak_layak, susun  # noqa: E402

log = logging.getLogger("run_jadwal")


def periksa_config(cfg: dict) -> list[str]:
    """Config errors, each naming its key. Empty = valid."""
    _, err = baca_aturan(cfg)
    if not (cfg.get("paths") or {}).get("schedule_dir"):
        err.append("paths.schedule_dir: belum diisi di config.local.yaml (folder berkas masukan dan hasil jadwal, di luar repo)")
    return err


def masukan_terbaru(folder: Path) -> Path | None:
    xs = sorted(folder.glob("jadwal_masukan_*.json"), key=lambda p: p.stat().st_mtime)
    return xs[-1] if xs else None


def _log(folder: Path) -> None:
    for h in list(log.handlers):
        log.removeHandler(h)
        h.close()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    for h in (logging.StreamHandler(sys.stdout), logging.FileHandler(folder / "run_jadwal.log", mode="w", encoding="utf-8")):
        h.setFormatter(fmt)
        log.addHandler(h)
    log.setLevel(logging.INFO)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--config", type=Path, default=AKAR / "config.yaml", help="bawaan: config.yaml di sebelah skrip")
    p.add_argument("--masukan", type=Path, help="berkas masukan tertentu (bawaan: terbaru di paths.schedule_dir)")
    p.add_argument("--keluar", type=Path, help="folder hasil (bawaan: subfolder baru di paths.schedule_dir)")
    p.add_argument("--batas-waktu", type=int, help="menimpa schedule.time_limit_seconds sementara")
    arg = p.parse_args(argv)

    cfg = load_config(arg.config)
    if arg.batas_waktu is not None:
        cfg.setdefault("schedule", {})["time_limit_seconds"] = arg.batas_waktu
    if arg.masukan or arg.keluar:
        cfg.setdefault("paths", {}).setdefault("schedule_dir", str((arg.keluar or arg.masukan).parent))
    err = periksa_config(cfg)
    if err:
        print("Config tidak sah, tidak ada yang dihitung:", file=sys.stderr)
        for e in err:
            print(f"  - {e}", file=sys.stderr)
        return 2
    aturan, _ = baca_aturan(cfg)
    folder = Path(cfg["paths"]["schedule_dir"])
    berkas = arg.masukan or (masukan_terbaru(folder) if folder.is_dir() else None)
    if not berkas or not berkas.is_file():
        print(f"Berkas masukan tidak ditemukan di {folder}. Unduh dari situs: Jadwal kuliah > Unduh masukan penjadwalan, "
              "lalu simpan di folder itu.", file=sys.stderr)
        return 2
    m, pesan = baca_masukan(berkas)
    if m is None:
        print(f"Berkas masukan tidak sah ({berkas}):", file=sys.stderr)
        for e in pesan:
            print(f"  - {e}", file=sys.stderr)
        return 2

    nama = f"{m.tahun_akademik.replace('/', '-')}_{m.semester}"
    keluar = arg.keluar or folder / f"hasil_{nama}_{datetime.now():%Y%m%d-%H%M}"
    keluar.mkdir(parents=True, exist_ok=True)
    _log(keluar)
    try:
        log.info("config  : %s", arg.config)
        log.info("masukan : %s", berkas)
        log.info("keluar  : %s", keluar)
        log.info("periode : %s %s, %d kelas, %d dosen", m.semester, m.tahun_akademik, len(m.kelas), len(m.dosen))
        for baris in ringkas(aturan):
            log.info("%s", baris)
        for x in pesan:
            log.warning("%s", x)
        h = susun(m, aturan)
        log.info("hasil   : %s — %s", h.status, h.pesan)
        cek, saran = None, []
        if h.jadwal:
            cek = periksa(m, aturan, h.jadwal)
            rows = baris_jadwal(m, h.jadwal)
            tulis_csv(keluar / f"hasil_jadwal_{nama}.csv", rows)
            tulis_excel(keluar / f"jadwal_{nama}.xlsx", m, rows, cek)
            log.info("wajib   : %d pelanggaran (hanya mungkin dari kelas yang dikunci di situs)", len(cek["wajib"]))
            log.info("anjuran : %d catatan", len(cek["anjuran"]))
            log.info("impor   : %s", keluar / f"hasil_jadwal_{nama}.csv")
        elif h.status == "tidak_layak" and not h.tanpa_pilihan:
            saran = saran_tidak_layak(m, aturan)
        (keluar / "laporan_jadwal.txt").write_text(laporan(m, aturan, h, cek, pesan, saran), encoding="utf-8")
        log.info("laporan : %s", keluar / "laporan_jadwal.txt")
        return 0 if h.jadwal else 1
    finally:
        for hd in list(log.handlers):
            log.removeHandler(hd)
            hd.close()


if __name__ == "__main__":
    raise SystemExit(main())
