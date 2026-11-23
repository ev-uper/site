#!/usr/bin/env python3
"""Pemasang situs kinerja program studi: dijalankan sekali, di komputer pengelola.

Jalankan di folder repo hasil clone:

    python install.py                 tanya satu per satu
    python install.py --ini isian.ini isi dari berkas (lihat isian.contoh.ini)

Hanya pustaka standar Python 3.9+; tidak menyentuh internet. Yang diisi:
site/config.js, config.yaml, judul beranda, logo, warna. Boleh dijalankan ulang
dengan nilai baru, misalnya setelah Apps Script terpasang.

Nama repo boleh bebas (bawaan cv-site, pemilik 2026-11-09); alamat situs dan
alamat yang diisikan di Supabase dihitung dari organisasi dan nama repo.

Repo ini publik: data admin dan token cadangan hanya tampil di layar, tidak
ditulis ke berkas yang di-commit. pasang-tercatat.json diabaikan git.
"""
from __future__ import annotations

import argparse
import configparser
import json
import re
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent
CATATAN = AKAR / "pasang-tercatat.json"
WARNA_AWAL = {"warna_utama": "#0C2A4D", "warna_aksen": "#C8102E"}
# Nilai bawaan saat pertanyaan dijawab Enter atau kunci tidak ada di isian.ini.
BAWAAN = {**WARNA_AWAL, "nama_repo": "cv-site", "paket": "lengkap"}
# Paket situs (pemilik 2026-11-12): modul yang dimatikan, ditulis ke site/config.js
# (window.FITUR_MATI). Samakan dengan PAKET di site/fitur.js (diuji tests/test_install.py).
PAKET = {
    "lengkap": [],
    # Khusus akreditasi (pemilik 2026-11-23): ruang kerja akreditasi + kurikulum/CPL/RPS, tanpa situs publik.
    "akreditasi": ["rapat", "hibah", "kalender", "pengingat", "kepakaran", "sdgs",
                   "kemahasiswaan", "jadwal", "kabar", "profil_prodi", "publik"],
}
POLA_FITUR = r"window\.FITUR_MATI *= *\[[^\]]*\];"

# key: (pertanyaan, wajib, pemeriksa -> pesan galat atau '')
def _tidak_kosong(v): return "" if v.strip() else "wajib diisi"
def _org(v): return "" if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", v) else "hanya huruf, angka, tanda minus"
def _repo(v):
    # Huruf kecil saja: nama repo menjadi bagian alamat situs dan alamat login
    # di Supabase, yang harus ditulis persis sama.
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,99}", v) or v.endswith(".git"):
        return "huruf kecil, angka, titik, tanda minus atau garis bawah (mis. cv-site)"
    return ""
def _sb_url(v): return "" if re.fullmatch(r"https://[a-z0-9]{10,40}\.supabase\.co/?", v) else "bentuknya https://<kode>.supabase.co"
def _sb_key(v):
    if v.startswith("sb_secret_"):
        return "itu SECRET key: jangan pernah dipakai di sini, gunakan publishable key"
    return "" if v.startswith("sb_publishable_") else "publishable key diawali sb_publishable_"
def _upload(v): return "" if not v or re.fullmatch(r"https://script\.google\.com/macros/s/[\w-]+/exec", v) else "kosongkan, atau URL Web App berakhiran /exec"
def _email(v): return "" if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v) else "bukan alamat email"
def _logo(v):
    if not v:
        return ""
    p = Path(v).expanduser()
    return "" if p.is_file() and p.suffix.lower() == ".png" else "berkas .png yang ada"
def _warna(v): return "" if re.fullmatch(r"#[0-9A-Fa-f]{6}", v) else "bentuknya #RRGGBB"
def _paket(v): return "" if v in PAKET else "pilih: " + " atau ".join(PAKET)

ISIAN = [
    ("nama_prodi", "Nama program studi (tanpa 'Program Studi', mis. Teknik Lingkungan)", _tidak_kosong),
    ("nama_institusi", "Nama institusi (mis. Universitas Contoh)", _tidak_kosong),
    ("github_org", "Nama organisasi/akun GitHub pemilik repo situs", _org),
    ("nama_repo", "Nama repo situs di GitHub", _repo),
    ("supabase_url", "Supabase Project URL (https://<kode>.supabase.co)", _sb_url),
    ("supabase_key", "Supabase PUBLISHABLE key (sb_publishable_...)", _sb_key),
    ("upload_url", "URL Web App Apps Script (boleh kosong, diisi nanti)", _upload),
    ("admin_email", "Email admin pertama (untuk masuk situs)", _email),
    ("admin_nidn", "NIDN admin pertama (staf tanpa NIDN: nomor pegawai)", _tidak_kosong),
    ("admin_nama", "Nama lengkap admin pertama", _tidak_kosong),
    ("logo", "Berkas logo .png (boleh kosong, diganti nanti)", _logo),
    ("warna_utama", "Warna utama #RRGGBB", _warna),
    ("warna_aksen", "Warna aksen #RRGGBB", _warna),
    ("paket", "Paket situs: lengkap atau akreditasi", _paket),
]
# Tempat mencari nilainya; dicetak di atas pertanyaan (docs/panduan-pemasangan.md).
PETUNJUK = {
    "github_org": "bagian alamat github.com/<org>/<repo>",
    "nama_repo": "nama yang dipilih saat Use this template; Enter bila cv-site",
    "supabase_url": "Supabase: tombol Connect di atas halaman proyek",
    "supabase_key": "Supabase: Project Settings > API Keys, baris Publishable key."
                    " JANGAN secret key (sb_secret_...)",
    "upload_url": "Apps Script: Deploy > Manage deployments > Web app URL (berakhiran /exec)",
    "admin_email": "alamat yang dipakai admin untuk masuk situs",
    "paket": "lengkap = semua modul dan situs publik; akreditasi = hanya ruang kerja akreditasi (skor, LKPS, LED,"
             " bukti, Data prodi, dosen, kurikulum/CPL/RPS), tanpa situs publik, layanan mahasiswa, jadwal, rapat,"
             " hibah, kalender, pengingat, kepakaran, SDGs (bisa dinyalakan lagi dengan memasang ulang)",
}


# site_check.url di config.yaml, apa pun nama repo sebelumnya.
POLA_URL = r"url: https://[^/\s]+\.github\.io(?:/[^\s#]*)?"


def alamat_situs(org: str, repo: str) -> str:
    """Alamat GitHub Pages: repo <org>.github.io tayang di akar, repo lain di /<repo>."""
    org = org.lower()
    return f"https://{org}.github.io" + ("" if repo == f"{org}.github.io" else f"/{repo}")


def tanya(lama: dict) -> dict:
    isi = {}
    print("Isi data prodi. Tekan Enter untuk memakai nilai dalam [kurung].\n")
    for kunci, teks, cek in ISIAN:
        bawaan = lama.get(kunci, BAWAAN.get(kunci, ""))
        if kunci in PETUNJUK:
            print(f"  ({PETUNJUK[kunci]})")
        while True:
            v = input(f"  {teks}{f' [{bawaan}]' if bawaan else ''}: ").strip() or bawaan
            galat = cek(v)
            if not galat:
                isi[kunci] = v
                break
            print(f"    -> {galat}")
    return isi


def dari_ini(berkas: Path) -> dict:
    cp = configparser.ConfigParser(interpolation=None)
    cp.read(berkas, encoding="utf-8")
    sek = cp["prodi"] if cp.has_section("prodi") else {}
    isi, galat = {}, []
    for kunci, _, cek in ISIAN:
        v = str(sek.get(kunci, "")).strip() or BAWAAN.get(kunci, "")
        g = cek(v)
        if g:
            galat.append(f"{kunci}: {g}")
        isi[kunci] = v
    if galat:
        sys.exit("Isian tidak sah:\n  " + "\n  ".join(galat))
    return isi


def ganti(path: Path, pola: str, baru: str, wajib: bool = True) -> None:
    t = path.read_text(encoding="utf-8")
    t2, n = re.subn(pola, lambda m: baru, t)
    if wajib and n == 0:
        sys.exit(f"Tidak menemukan bagian yang diganti di {path.relative_to(AKAR)}: {pola}")
    path.write_text(t2, encoding="utf-8", newline="\n")


def sql_teks(v: str) -> str:
    return "'" + v.replace("'", "''") + "'"


def pasang(isi: dict, lama: dict) -> None:
    site = AKAR / "site"
    # 1. config.js
    cfg = site / "config.js"
    ganti(cfg, r"window\.SB_URL = '[^']*';", f"window.SB_URL = '{isi['supabase_url'].rstrip('/')}';")
    ganti(cfg, r"window\.SB_KEY = '[^']*';", f"window.SB_KEY = '{isi['supabase_key']}';")
    ganti(cfg, r"window\.UPLOAD_URL *= '[^']*';", f"window.UPLOAD_URL    = '{isi['upload_url']}';")
    mati = ", ".join(f"'{k}'" for k in PAKET[isi["paket"]])
    ganti(cfg, POLA_FITUR, f"window.FITUR_MATI = [{mati}];")
    # 2. alamat situs untuk pemeriksa situs
    ganti(AKAR / "config.yaml", POLA_URL, "url: " + alamat_situs(isi["github_org"], isi["nama_repo"]))
    # 3. judul dan deskripsi beranda dan dasbor kinerja (diganti juga oleh skrip halaman dari data.json).
    #    Beranda program studi = index.html, dasbor kinerja = kinerja.html (2026-11-16).
    idx = site / "index.html"
    ganti(idx, r"<title>[^<]*</title>",
          f"<title>Program Studi {isi['nama_prodi']} — {isi['nama_institusi']}</title>")
    ganti(idx, r'<meta name="description" content="[^"]*">',
          f'<meta name="description" content="Program Studi {isi["nama_prodi"]}, {isi["nama_institusi"]}: '
          f'kurikulum, dosen dan kepakaran, penelitian, pengabdian kepada masyarakat, dan layanan mahasiswa.">')
    kin = site / "kinerja.html"
    if kin.exists():
        ganti(kin, r"<title>[^<]*</title>", f"<title>Kinerja Program Studi {isi['nama_prodi']}</title>")
        ganti(kin, r'<meta name="description" content="[^"]*">',
              f'<meta name="description" content="Publikasi, penelitian, pengabdian kepada masyarakat, '
              f'dan prestasi mahasiswa Program Studi {isi["nama_prodi"]}, {isi["nama_institusi"]}.">')
    # 4. logo
    if isi["logo"]:
        shutil.copyfile(Path(isi["logo"]).expanduser(), site / "logo.png")
        # Ikon tab dari logo (2026-11-23): bagian berwarna logo. Butuh Pillow; tanpa itu ikon pengganti tetap dipakai.
        ikon = AKAR / "tools" / "make_favicon.py"
        if ikon.exists():
            r = subprocess.run([sys.executable, str(ikon), str(site / "logo.png")], cwd=AKAR,
                               capture_output=True, text=True)
            if r.returncode:
                print("Ikon tab belum dibuat dari logo (ikon pengganti tetap dipakai). Jalankan nanti:\n"
                      "   pip install pillow\n   python tools/make_favicon.py site/logo.png")
    # 5. warna (dari nilai terakhir yang terpasang)
    for kunci in ("warna_utama", "warna_aksen"):
        dari = lama.get(kunci, WARNA_AWAL[kunci])
        if dari.lower() != isi[kunci].lower():
            for p in list(site.glob("*.html")) + list(site.glob("*.css")) + list(site.glob("*.js")):
                ganti(p, "(?i)" + re.escape(dari), isi[kunci].upper(), wajib=False)
    CATATAN.write_text(json.dumps(isi, ensure_ascii=False, indent=2), encoding="utf-8")
    # 6. new version stamps, so browsers drop the cached old colours/config
    if (AKAR / "stamp_versions.py").exists():
        subprocess.run([sys.executable, str(AKAR / "stamp_versions.py")], cwd=AKAR,
                       stdout=subprocess.DEVNULL, check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Pemasang situs kinerja program studi")
    ap.add_argument("--ini", type=Path, help="isi dari berkas .ini (bagian [prodi])")
    a = ap.parse_args()
    lama = json.loads(CATATAN.read_text(encoding="utf-8")) if CATATAN.exists() else {}
    isi = dari_ini(a.ini) if a.ini else tanya(lama)
    pasang(isi, lama)
    mati = PAKET[isi["paket"]]
    print(f"\nPaket: {isi['paket']}" + (f" (dimatikan: {', '.join(mati)})" if mati else ""))
    print("\nSelesai. Diisi: site/config.js, config.yaml, site/index.html, site/kinerja.html"
          + (", site/logo.png" if isi["logo"] else ""))
    situs = alamat_situs(isi["github_org"], isi["nama_repo"])
    print(f"\nAlamat situs: {situs}/")
    print("Isi di Supabase, Authentication > URL Configuration (panduan tahap 4):")
    print(f"   Site URL      : {situs}/")
    print(f"   Redirect URLs : {situs}/**")
    print("\n--- Salin sekarang; dua hal ini tidak disimpan di berkas mana pun ---")
    print("\n1. SQL admin pertama (README langkah 5, sekali saja):\n")
    print("   insert into public.dosen (nidn, nama, email, peran)")
    print(f"   values ({sql_teks(isi['admin_nidn'])}, {sql_teks(isi['admin_nama'])}, "
          f"{sql_teks(isi['admin_email'].lower())}, 'admin')")
    print("   on conflict (email) do update set peran = 'admin', aktif = true;")
    print("\n2. Token cadangan baru (README langkah 6 dan 7). Kalau sudah terpasang,")
    print("   abaikan yang ini dan tetap pakai yang lama:\n")
    print(f"   {secrets.token_urlsafe(32)}")


if __name__ == "__main__":
    main()
