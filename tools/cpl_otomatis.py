"""Hitung CPL otomatis di GitHub Actions (pemilik 2026-11-17, OBE tahap O4).

Dijalankan .github/workflows/hitung-cpl.yml (harian, dan tombol "Hitung ulang sekarang" di Berkas nilai CPL).
Kode hitungnya run_cpl.py yang sama dengan di komputer admin, jadi hasilnya identik.

    python tools/cpl_otomatis.py           # hanya bila ada berkas nilai/masukan baru sejak ringkasan terakhir
    python tools/cpl_otomatis.py --paksa   # selalu (tombol admin/GKM)

Langkah:
  1. Bandingkan waktu berkas nilai terakhir (cpl_berkas) dan masukan tambahan (Drive berkas-privat/cpl-masukan/)
     dengan ringkasan terakhir (cpl_ringkasan).
  2. Unduh masukan tambahan ke folder sementara di luar repo (RUNNER_TEMP). Peta jalur Drive -> kunci paths:
       nilai_akhir/...           -> final_grades_dir      (nilai akhir kampus, estimasi semester lama)
       course_removals.csv       -> course_removals_csv
       student_info.csv          -> student_info_csv
       advisors.csv              -> advisors_csv
       student_activities.csv    -> student_activities_csv
       foto/...                  -> photos_dir
     Jalur lain diabaikan (dilaporkan jumlahnya saja).
  3. Tulis config.local.yaml sementara (paths) lalu jalankan run_cpl.py; keluarannya ke berkas log, BUKAN ke layar,
     supaya NIM tidak masuk log GitHub Actions.
  4. Unggah ringkasan_cpl.json (tanpa NIM; run_cpl.py sudah menolak bila memuat NIM) ke tabel cpl_ringkasan.
  5. Simpan laporan_cpl.xlsx, radar_mahasiswa.html, perwalian/*.html, dan log ke Drive privat
     berkas-privat/cpl-laporan/<waktu UTC>/ (Apps Script, kunci CPL_KUNCI). Tidak ada berkas ber-NIM di GitHub.

Env: SUPABASE_URL, SUPABASE_SERVICE_KEY, CPL_KUNCI (secret repo). URL Apps Script dari site/config.js.
Hanya berjalan di GitHub Actions (GITHUB_ACTIONS=true), karena menimpa config.local.yaml.
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

AKAR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AKAR))

from cpl.unduh import _post, baca_kunci, baca_url  # noqa: E402

UNDUH_PARALEL = 4   # panggilan Apps Script bersamaan (uji pertama 2026-11-18 dengan 8: sebagian jawaban tanpa data)
COBA = (2, 4, 8, 16)  # jeda (detik) sebelum mengulang panggilan Apps Script yang gagal atau jawabannya tidak lengkap


def panggil(post, url, isi, wajib, tidur=None):
    """post() dengan pemeriksaan: jawaban harus memuat kunci `wajib`; galat atau jawaban tidak lengkap diulang
    (jeda COBA). Pesan akhir hanya menyebut aksi, kunci jawaban, dan galat Apps Script (tanpa isi berkas)."""
    import time
    tidur = tidur or time.sleep
    sebab = ""
    for jeda in (*COBA, None):
        try:
            out = post(url, isi)
            if wajib in out:
                return out
            sebab = f"jawaban tanpa '{wajib}' (kunci: {', '.join(sorted(out)) or '-'})"
        except Exception as e:  # noqa: BLE001 - galat jaringan atau Apps Script ok:false; diulang
            sebab = f"{type(e).__name__}: {e}"
        if jeda is None:
            break
        tidur(jeda)
    raise RuntimeError(f"Apps Script {isi.get('aksi')} gagal {len(COBA) + 1} kali: {sebab}")

MASUKAN_FOLDER = {"nilai_akhir": "final_grades_dir", "foto": "photos_dir"}
MASUKAN_BERKAS = {"course_removals.csv": "course_removals_csv", "student_info.csv": "student_info_csv",
                  "advisors.csv": "advisors_csv", "student_activities.csv": "student_activities_csv"}
LAPORAN = ("laporan_cpl.xlsx", "radar_mahasiswa.html", "run_cpl.log")
CATATAN = "otomatis (GitHub Actions)"


def waktu(s):
    """ISO 8601 (Supabase '...+00:00' atau Apps Script '...Z') -> datetime UTC; None bila kosong."""
    if not s:
        return None
    return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(timezone.utc)


def perlu_hitung(berkas_terakhir, masukan, ringkasan_terakhir):
    """Ada berkas nilai atau masukan yang lebih baru dari ringkasan terakhir (atau belum ada ringkasan)."""
    r = waktu(ringkasan_terakhir)
    if r is None:
        return True
    # Masukan: tanggal ubah ATAU tanggal masuk Drive (unggahan peramban mempertahankan tanggal ubah asli yang lama).
    baru = [waktu(berkas_terakhir), *(waktu(m.get(k)) for m in masukan for k in ("diubah", "dibuat"))]
    return any(t is not None and t > r for t in baru)


def nama_aman(s):
    """Satu segmen jalur Drive -> nama lokal. Nama asli dipertahankan (termasuk "(1)", yang dipakai final_grades.py
    untuk mengenali unduhan ganda); hanya garis miring, karakter kontrol, dan '.'/'..' yang tidak boleh."""
    s = re.sub(r'[\x00-\x1f\\/:*?"<>|]+', "_", str(s or "")).strip(" ")
    return s if s.strip(".") else "_"


def petakan_masukan(daftar, dasar):
    """daftar [{id, jalur}] -> (paths {kunci: folder/berkas lokal}, unduh [(id, path lokal)], jumlah diabaikan).
    Di nilai_akhir/ hanya *.csv (final_grades.py hanya membaca itu; zip semester tidak perlu diunduh)."""
    dasar = Path(dasar)
    paths, unduh, abai = {}, [], 0
    for m in daftar:
        seg = [s for s in str(m.get("jalur") or "").split("/") if s]
        if not seg:
            abai += 1
            continue
        if seg[0] in MASUKAN_FOLDER and len(seg) > 1:
            if seg[0] == "nilai_akhir" and not seg[-1].casefold().endswith(".csv"):
                abai += 1
                continue
            akar = dasar / seg[0]
            paths[MASUKAN_FOLDER[seg[0]]] = str(akar)
            unduh.append((m["id"], akar.joinpath(*[nama_aman(s) for s in seg[1:]])))
        elif len(seg) == 1 and seg[0] in MASUKAN_BERKAS:
            p = dasar / seg[0]
            paths[MASUKAN_BERKAS[seg[0]]] = str(p)
            unduh.append((m["id"], p))
        else:
            abai += 1
    return paths, unduh, abai


def keluaran_laporan(output_dir):
    """Berkas ber-NIM yang disimpan ke Drive: (jalur relatif, path)."""
    out = Path(output_dir)
    xs = [(n, out / n) for n in LAPORAN if (out / n).is_file()]
    xs += [(f"perwalian/{p.name}", p) for p in sorted((out / "perwalian").glob("*.html"))]
    return xs


class Supabase:
    def __init__(self, url, kunci):
        import requests
        self.r, self.url = requests, url.rstrip("/")
        self.kepala = {"apikey": kunci, "Authorization": f"Bearer {kunci}"}

    def terakhir(self, tabel, kolom):
        r = self.r.get(f"{self.url}/rest/v1/{tabel}", headers=self.kepala,
                       params={"select": kolom, "order": f"{kolom}.desc", "limit": "1"}, timeout=60)
        r.raise_for_status()
        xs = r.json()
        return xs[0][kolom] if xs else None

    def simpan_ringkasan(self, data):
        r = self.r.post(f"{self.url}/rest/v1/cpl_ringkasan", headers={**self.kepala, "Content-Type": "application/json",
                        "Prefer": "return=minimal"}, timeout=120,
                        data=json.dumps({"dibuat": data.get("dibuat"), "data": data, "catatan": CATATAN, "oleh": "otomatis"}))
        r.raise_for_status()


def main(argv=None, env=None, post=None, sb=None):
    env = os.environ if env is None else env
    post = post or _post
    a = argparse.ArgumentParser(description="Hitung CPL otomatis (GitHub Actions).")
    a.add_argument("--paksa", action="store_true", help="hitung walau tidak ada berkas baru")
    args = a.parse_args(argv)
    if env.get("GITHUB_ACTIONS") != "true":
        print("Hanya untuk GitHub Actions (menimpa config.local.yaml). Di komputer sendiri jalankan run_cpl.py.")
        return 2
    url, kunci = baca_url(AKAR), baca_kunci(AKAR)
    sb = sb or Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
    masukan = post(url, {"kind": "cpl_unduh", "kunci": kunci, "aksi": "masukan_daftar"}).get("berkas") or []
    # Jalan manual (tab Actions atau tombol situs, event workflow_dispatch) selalu menghitung; jadwal malam hanya bila
    # ada yang baru. Dibaca di sini, bukan dari centang "paksa" (uji 2026-11-18: centang terlewat, tidak dihitung).
    paksa = args.paksa or env.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
    print(f"Pemicu: {env.get('GITHUB_EVENT_NAME') or '-'}; {'selalu hitung' if paksa else 'hitung bila ada yang baru'}.")
    if not paksa and not perlu_hitung(sb.terakhir("cpl_berkas", "diunggah"), masukan, sb.terakhir("cpl_ringkasan", "diunggah")):
        print("Tidak ada berkas nilai atau masukan baru sejak ringkasan terakhir; tidak dihitung.")
        return 0

    tmp = Path(env.get("RUNNER_TEMP") or tempfile.mkdtemp()) / "cpl-otomatis"
    masuk, keluar, tambahan = tmp / "berkas", tmp / "laporan", tmp / "masukan"
    for p in (masuk, keluar, tambahan):
        p.mkdir(parents=True, exist_ok=True)
    paths, unduh, abai = petakan_masukan(masukan, tambahan)
    def ambil(item):
        i, p = item
        p.parent.mkdir(parents=True, exist_ok=True)
        isi = {"kind": "cpl_unduh", "kunci": kunci, "aksi": "masukan_ambil", "id": i}
        p.write_bytes(base64.b64decode(panggil(post, url, isi, "data")["data"]))

    with ThreadPoolExecutor(max_workers=UNDUH_PARALEL) as ex:      # ratusan berkas nilai akhir: satu per satu terlalu lama
        list(ex.map(ambil, unduh))
    print(f"Masukan tambahan: {len(unduh)} berkas ({', '.join(sorted(paths)) or 'tidak ada'}); diabaikan {abai}.")

    import yaml
    (AKAR / "config.local.yaml").write_text(yaml.safe_dump({"source": "site", "paths": {
        "input_dir": str(masuk), "output_dir": str(keluar), **paths}}, allow_unicode=True), encoding="utf-8")
    with open(tmp / "keluaran_run_cpl.txt", "w", encoding="utf-8") as log:
        kode = subprocess.run([sys.executable, str(AKAR / "run_cpl.py")], cwd=AKAR, stdout=log, stderr=subprocess.STDOUT,
                              env={**env, "CPL_KUNCI": kunci}).returncode
    print(f"run_cpl.py selesai, kode {kode} (rincian di log Drive, tidak ditampilkan di sini karena bisa memuat NIM).")

    folder = datetime.now(timezone.utc).strftime("%Y-%m-%d %H%M UTC")
    simpan = keluaran_laporan(keluar) + [("keluaran_run_cpl.txt", tmp / "keluaran_run_cpl.txt")]
    for jalur, p in simpan:
        panggil(post, url, {"kind": "cpl_unduh", "kunci": kunci, "aksi": "laporan_simpan", "folder": folder, "jalur": jalur,
                            "data": base64.b64encode(p.read_bytes()).decode("ascii")}, "id")
    print(f"Laporan ber-NIM: {len(simpan)} berkas disimpan di Drive privat (cpl-laporan/{folder}).")

    ring = keluar / "ringkasan_cpl.json"
    if not ring.is_file():
        print("ringkasan_cpl.json tidak dibuat; periksa log di Drive.")
        return kode or 1
    sb.simpan_ringkasan(json.loads(ring.read_text(encoding="utf-8")))
    print("Ringkasan CPL diunggah ke situs (Monitoring > Capaian CPL).")
    return kode


if __name__ == "__main__":
    sys.exit(main())
