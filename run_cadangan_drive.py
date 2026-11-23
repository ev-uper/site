"""Cadangan berkas Google Drive prodi ke komputer atau hard disk prodi (pemilik 2026-11-20).

Mengunduh semua berkas di folder bukti prodi (FOLDER_ID Apps Script: bukti karya dan akreditasi, RPS, berkas mahasiswa,
berkas dan laporan CPL) ke paths.drive_backup_dir. Hanya berkas BARU atau BERUBAH yang diunduh; versi lama berkas yang
berubah dipindah ke _versi_lama/<tanggal>/; berkas yang hilang dari Drive TIDAK dihapus dari cadangan, hanya dicatat.
Hasil dilaporkan ke panel Kesehatan sistem (instal-lengkap.sql).

    python run_cadangan_drive.py                  # cadangkan (atau tombol Run di VS Code)
    python run_cadangan_drive.py --hanya-periksa  # tampilkan rencana saja, tanpa mengunduh

Config: config.yaml bagian drive_backup; folder tujuan di config.local.yaml paths.drive_backup_dir (di luar repo:
isinya memuat data pribadi mahasiswa dan dosen). Kunci CADANGAN_DRIVE_KUNCI dari env atau rahasia.env (sama dengan
Script Property CADANGAN_DRIVE_KUNCI di Apps Script); kunci tidak pernah dicetak. URL Apps Script dari site/config.js.
Isi folder tujuan:
    <jalur folder Drive>/<nama berkas>   salinan terbaru
    _versi_lama/<YYYY-MM-DD>/...          versi sebelum berkas itu berubah
    _manifest.json                        daftar berkas yang dicadangkan (id Drive -> jalur lokal, ukuran, waktu ubah)
    _log/cadangan_<waktu>.log             catatan tiap jalan
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path, PurePosixPath

AKAR = Path(__file__).resolve().parent
sys.path.insert(0, str(AKAR))
from cpl.config import load_config  # noqa: E402
from cpl.unduh import _aman, _post, baca_url  # noqa: E402

KUNCI_ENV = "CADANGAN_DRIVE_KUNCI"
COBA = (2, 5, 15)   # jeda (detik) sebelum mengulang panggilan Apps Script yang gagal


# ---------- config dan kunci ----------

def baca_kunci(repo_root: Path, env=os.environ) -> str:
    """CADANGAN_DRIVE_KUNCI dari env, bila kosong dari rahasia.env (baris CADANGAN_DRIVE_KUNCI=...)."""
    kunci = env.get(KUNCI_ENV, "").strip()
    path = Path(repo_root) / "rahasia.env"
    if not kunci and path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(KUNCI_ENV + "="):
                kunci = line.split("=", 1)[1].strip().strip('"').strip("'")
    if len(kunci) < 32:
        raise ValueError(f"{KUNCI_ENV} belum diisi (minimal 32 karakter) di env atau rahasia.env; "
                         f"nilainya sama dengan Script Property {KUNCI_ENV} di Apps Script.")
    return kunci


def periksa_config(cfg: dict, repo_root: Path) -> list[str]:
    """Galat config, tiap pesan menyebut kuncinya. Kosong = sah."""
    err = []
    db = cfg.get("drive_backup")
    if not isinstance(db, dict):
        return ["drive_backup: bagian belum ada di config.yaml"]
    mb = db.get("chunk_mb")
    if not isinstance(mb, int) or isinstance(mb, bool) or not 1 <= mb <= 20:
        err.append(f"drive_backup.chunk_mb: bilangan bulat 1-20, didapat {mb!r}")
    if not isinstance(db.get("keep_old_versions"), bool):
        err.append(f"drive_backup.keep_old_versions: true atau false, didapat {db.get('keep_old_versions')!r}")
    tujuan = (cfg.get("paths") or {}).get("drive_backup_dir")
    if not tujuan:
        err.append("paths.drive_backup_dir: belum diisi di config.local.yaml")
    else:
        p = Path(tujuan)
        try:
            p.resolve().relative_to(Path(repo_root).resolve())
            err.append(f"paths.drive_backup_dir: {p} berada di dalam repo; pakai folder di luar repo (berkas memuat data pribadi)")
        except ValueError:
            if not p.parent.is_dir():
                err.append(f"paths.drive_backup_dir: folder induk tidak ada: {p.parent} (hard disk belum terpasang?)")
    return err


def _os_path(p: Path) -> Path:
    """Jalur untuk operasi berkas. Windows: awalan \\\\?\\ supaya jalur di atas 260 karakter (folder dan nama
    berkas Drive yang panjang) tetap bisa ditulis tanpa mengubah setelan sistem. Sistem lain: apa adanya."""
    if os.name != "nt":
        return p
    s = str(Path(os.path.abspath(p)))
    if s.startswith("\\\\?\\"):
        return Path(s)
    return Path("\\\\?\\UNC\\" + s[2:]) if s.startswith("\\\\") else Path("\\\\?\\" + s)


# ---------- rencana ----------

def jalur_lokal(b: dict, terpakai: set[str]) -> str:
    """Jalur relatif (pakai /) untuk berkas Drive b; nama kembar di folder yang sama diberi akhiran [id8]."""
    segmen = [_aman(s) for s in str(b.get("jalur") or "").split("/") if s.strip()]
    nama = _aman(b.get("nama"))
    calon = str(PurePosixPath(*segmen, nama))
    if calon in terpakai:
        n = PurePosixPath(nama)
        calon = str(PurePosixPath(*segmen, f"{n.stem} [{str(b['id'])[:8]}]{n.suffix}"))
    return calon


def rencana(manifest: dict, daftar: list[dict], ada_lokal) -> dict:
    """Bandingkan manifest (id -> entri) dengan daftar Drive. ada_lokal(jalur, ukuran) -> bool.
    Hasil: baru, berubah (entri Drive), sama (id), hilang (id), lewat (berkas Google asli)."""
    out = {"baru": [], "berubah": [], "sama": [], "hilang": [], "lewat": []}
    di_drive = set()
    for b in daftar:
        if str(b.get("jenis", "")).startswith("application/vnd.google-apps."):
            out["lewat"].append(b)
            continue
        di_drive.add(b["id"])
        m = manifest.get(b["id"])
        if not m:
            out["baru"].append(b)
        elif m.get("diubah") != b.get("diubah") or m.get("ukuran") != b.get("ukuran") or not ada_lokal(m["lokal"], b.get("ukuran")):
            out["berubah"].append(b)
        else:
            out["sama"].append(b["id"])
    out["hilang"] = sorted(i for i, m in manifest.items() if i not in di_drive and not m.get("hilang_sejak"))
    return out


# ---------- unduh ----------

def panggil(post, url: str, isi: dict, tidur=time.sleep) -> dict:
    """post() dengan pengulangan (COBA); pesan galat tanpa isi berkas atau kunci."""
    sebab = ""
    for jeda in (*COBA, None):
        try:
            return post(url, isi)
        except Exception as e:  # noqa: BLE001 - jaringan/Apps Script: diulang
            sebab = str(e)
            if jeda is None:
                break
            tidur(jeda)
    raise RuntimeError(f"Apps Script ({isi.get('aksi')}): {sebab}")


def unduh(post, url: str, kunci: str, b: dict, tujuan: Path, potong_mb: int, tidur=time.sleep) -> int:
    """Unduh berkas b per potongan ke tujuan (lewat berkas .sebagian). Kembalikan jumlah byte."""
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    sementara = tujuan.with_name(tujuan.name + ".sebagian")
    panjang, mulai, total = potong_mb * 1024 * 1024, 0, None
    with open(sementara, "wb") as f:
        while total is None or mulai < total:
            a = panggil(post, url, {"kind": "cadangan_drive", "kunci": kunci, "aksi": "ambil", "id": b["id"],
                                    "mulai": mulai, "panjang": panjang}, tidur)
            data = base64.b64decode(a.get("data") or "")
            total = int(a["total"])
            if not data and mulai < total:
                raise RuntimeError("potongan kosong")
            f.write(data)
            mulai += len(data)
    if mulai != total or (b.get("ukuran") not in (None, 0) and total != b["ukuran"]):
        sementara.unlink(missing_ok=True)
        raise RuntimeError(f"ukuran tidak cocok ({mulai} dari {total}, Drive {b.get('ukuran')})")
    os.replace(sementara, tujuan)
    return total


def jalankan(cfg: dict, tujuan: Path, post, url: str, kunci: str, cetak=print, hanya_periksa=False,
             tidur=time.sleep, hari_ini=None) -> dict:
    """Satu kali cadangan. Kembalikan ringkasan {berkas, baru, berubah, hilang, gagal, lewat, megabita}."""
    db = cfg["drive_backup"]
    hari_ini = hari_ini or datetime.now().strftime("%Y-%m-%d")
    path_manifest = tujuan / "_manifest.json"
    manifest = json.loads(path_manifest.read_text(encoding="utf-8")) if path_manifest.is_file() else {}
    daftar = panggil(post, url, {"kind": "cadangan_drive", "kunci": kunci, "aksi": "daftar"}, tidur).get("berkas") or []
    ada_lokal = lambda j, u: _os_path(tujuan / j).is_file() and (u in (None, 0) or _os_path(tujuan / j).stat().st_size == u)  # noqa: E731
    r = rencana(manifest, daftar, ada_lokal)
    cetak(f"Drive: {len(daftar)} berkas; baru {len(r['baru'])}, berubah {len(r['berubah'])}, sama {len(r['sama'])}, "
          f"hilang dari Drive {len(r['hilang'])}, berkas Google asli dilewati {len(r['lewat'])}.")
    gagal = 0
    if not hanya_periksa:
        terpakai = {m["lokal"] for m in manifest.values()}
        for b in r["baru"] + r["berubah"]:
            lama = manifest.get(b["id"])
            lokal = lama["lokal"] if lama else jalur_lokal(b, terpakai)
            terpakai.add(lokal)
            path = _os_path(tujuan / lokal)
            try:
                if lama and db["keep_old_versions"] and path.is_file():
                    simpan = _os_path(tujuan / "_versi_lama" / hari_ini / lokal)
                    simpan.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, simpan)
                n = unduh(post, url, kunci, b, path, db["chunk_mb"], tidur)
                manifest[b["id"]] = {"lokal": lokal, "jalur": b.get("jalur", ""), "nama": b.get("nama"), "ukuran": n,
                                     "diubah": b.get("diubah"), "dicadangkan": hari_ini}
                cetak(f"  {'berubah' if lama else 'baru'}: {lokal} ({n:,} byte)")
            except Exception as e:  # noqa: BLE001 - satu berkas gagal tidak menghentikan yang lain
                gagal += 1
                cetak(f"  GAGAL: {lokal}: {e}")
        for i in r["sama"]:   # muncul lagi di Drive (mis. dipulihkan dari Sampah): tanda hilang dihapus
            manifest[i].pop("hilang_sejak", None)
        for i in r["hilang"]:
            manifest[i]["hilang_sejak"] = hari_ini
            cetak(f"  hilang dari Drive (salinan tetap disimpan): {manifest[i]['lokal']}")
        tujuan.mkdir(parents=True, exist_ok=True)
        baru = path_manifest.with_name("_manifest.json.baru")
        baru.write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(baru, path_manifest)
    ukuran = sum(m.get("ukuran") or 0 for m in manifest.values() if not m.get("hilang_sejak"))
    return {"berkas": len(daftar) - len(r["lewat"]), "baru": len(r["baru"]), "berubah": len(r["berubah"]),
            "hilang": len(r["hilang"]), "gagal": gagal, "lewat": len(r["lewat"]), "megabita": round(ukuran / 1048576, 1)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Cadangkan berkas Google Drive prodi ke komputer/hard disk prodi.")
    ap.add_argument("--hanya-periksa", action="store_true", help="tampilkan rencana saja, tanpa mengunduh")
    args = ap.parse_args(argv)
    cfg = load_config(AKAR / "config.yaml")
    err = periksa_config(cfg, AKAR)
    if err:
        print("Config belum sah:\n  " + "\n  ".join(err), file=sys.stderr)
        return 2
    tujuan = Path(cfg["paths"]["drive_backup_dir"])
    tujuan.mkdir(parents=True, exist_ok=True)
    (tujuan / "_log").mkdir(exist_ok=True)
    waktu = datetime.now().strftime("%Y%m%d-%H%M%S")
    log = open(tujuan / "_log" / f"cadangan_{waktu}.log", "w", encoding="utf-8")

    def cetak(s):
        print(s)
        log.write(s + "\n")
        log.flush()

    db = cfg["drive_backup"]
    cetak(f"Cadangan Drive {waktu}: tujuan {tujuan}; chunk_mb {db['chunk_mb']}; keep_old_versions {db['keep_old_versions']}"
          f"{'; HANYA PERIKSA' if args.hanya_periksa else ''}")
    try:
        url, kunci = baca_url(AKAR), baca_kunci(AKAR)
        hasil = jalankan(cfg, tujuan, _post, url, kunci, cetak, hanya_periksa=args.hanya_periksa)
    except Exception as e:  # noqa: BLE001
        cetak(f"GAGAL: {e}")
        log.close()
        return 1
    cetak(f"Selesai: {hasil}")
    if not args.hanya_periksa:
        try:
            panggil(_post, url, {"kind": "cadangan_drive", "kunci": kunci, "aksi": "selesai", "hasil": hasil})
        except Exception as e:  # noqa: BLE001 - cadangan tetap sah walau laporan gagal
            cetak(f"Laporan ke panel Kesehatan sistem gagal: {e}")
    log.close()
    return 1 if hasil["gagal"] else 0


if __name__ == "__main__":
    sys.exit(main())
