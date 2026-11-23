#!/usr/bin/env python3
"""
bangun.py — pengolah data kinerja prodi

    Supabase: karya dosen, daftar dosen    ┐
    (kelola-dosen.html), data prodi        ├─►  bangun.py  ─┬─►  situs/data.json       (publik)
    (data-prodi.html, tabel lkps_*)        ┘                ├─►  laporan-internal.html (privat)
                                                            └─►  arsip/prodi.sqlite    (arsip)

Semua data diisi di situs; data-prodi.xlsx tidak dibaca lagi (pemilik
2026-11-04). Perintah lama --template, --sinkron-dosen, --sinkron-pengaturan,
--tambah-lembar, --impor-lkps hanya mencetak di mana data kini diisi.

Perintah:
    python bangun.py --periksa         Hanya validasi, tidak menulis berkas apa pun
    python bangun.py                   Bangun seluruh keluaran

Ketergantungan:
    pip install requests pandas

Berkas rahasia.env (jangan pernah di-commit):
    SUPABASE_URL=https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY=eyJ...
    SITUS_DIR=../prodi-situs
    NAMA_PRODI=Nama Prodi
    NAMA_INSTITUSI=Universitas Contoh
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from cpl.config import load_config
from jadwal.aturan import baca_aturan
from halaman_publik import (akreditasi_publik, alumni_ringkas, drive_id, jadwal_ta_publik, kabar_publik, kerjasama_publik,
                            laboratorium_publik, lengkapi_mk_terbaru, tempat_kp_publik, berkas_bidang, kalender_publik, arsip_ta_publik,
                            kaprodi_aktif, riwayat_kaprodi, prestasi_publik, profil_publik, salin_foto_dosen, testimoni_publik,
                            salin_foto,
                            salin_foto_prestasi,
                            tulis_halaman_publik, lengkapi_beranda, alamat_situs, fitur_mati)
import requests

AKAR = Path(__file__).resolve().parent
BERKAS_ENV = AKAR / "rahasia.env"
# Kunci rahasia.env; nama yang sama dipakai sebagai variabel lingkungan
# di GitHub Actions.
KUNCI_ENV = ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "SITUS_DIR",
             "NAMA_PRODI", "NAMA_INSTITUSI")
DIR_ARSIP = AKAR / "arsip"

TINGKAT_SAH = {"internasional", "nasional", "wilayah_lokal"}
BIDANG_SAH = {"akademik", "non_akademik"}
STATUS_DTPS_SAH = {"dtps", "dosen_tetap", "dosen_tidak_tetap"}
KOLOM_SKS = ("sks_pendidikan", "sks_ps_lain_dalam", "sks_ps_lain_luar", "sks_penelitian", "sks_pkm",
             "sks_penunjang")

# Batas SKS wajar per semester. Di luar rentang ini hanya peringatan,
# tidak menghentikan proses — bisa saja benar untuk kasus tertentu.
SKS_MIN, SKS_MAKS = 12, 16


# =====================================================================
#  Konfigurasi
# =====================================================================
def slug(nama: str) -> str:
    """Pengenal dosen untuk URL halaman profil. Dibuat dari nama supaya
    tautannya terbaca manusia, dan tidak memakai NIDN di alamat publik."""
    return re.sub(r"[^a-z0-9]+", "-", str(nama).lower()).strip("-")


def id_saja(nilai) -> str:
    """Mengambil ID dari nilai yang mungkin ditempel sebagai URL lengkap.

    Dosen sering menyalin seluruh alamat profil dari peramban, bukan
    angkanya saja. Tanpa pembersihan ini, tautan di situs jadi bertumpuk
    seperti https://sinta.../profile/https://sinta.../profile/123456
    """
    v = str(nilai or "").strip()
    if not v or v.lower() in {"nan", "none", "-"}:
        return ""
    if "http" in v.lower():
        # Bila ada URL bersarang — akibat menempel alamat yang sudah
        # terlanjur bertumpuk — ambil yang paling belakang.
        v = v[v.lower().rfind("http"):]
        m = re.search(r"authorId=([0-9]+)", v, re.I)   # pola Scopus lama
        if m:
            return m.group(1)
        v = v.rstrip("/").split("?")[0].split("#")[0].rsplit("/", 1)[-1]
    return v.strip()


def keluar(pesan: str) -> None:
    print(f"\n  GAGAL — {pesan}\n", file=sys.stderr)
    sys.exit(1)


def baca_env() -> dict:
    """Membaca rahasia.env tanpa perlu pustaka tambahan.

    Tanpa rahasia.env (GitHub Actions, .github/workflows/bangun-situs.yml)
    kunci yang sama dibaca dari variabel lingkungan."""
    if not BERKAS_ENV.exists():
        if os.environ.get("GITHUB_ACTIONS") == "true":
            env = {k: os.environ.get(k, "") for k in KUNCI_ENV}
            for wajib in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "SITUS_DIR",
                          "NAMA_PRODI", "NAMA_INSTITUSI"):
                if not env[wajib]:
                    keluar(f"{wajib} kosong di lingkungan GitHub Actions "
                           f"(secrets/variables repositori).")
            return env
        keluar(
            f"Berkas {BERKAS_ENV.name} tidak ditemukan. Salin rahasia.env.contoh "
            f"menjadi rahasia.env, lalu isi nilainya."
        )
    env = {}
    for baris in BERKAS_ENV.read_text(encoding="utf-8").splitlines():
        baris = baris.strip()
        if not baris or baris.startswith("#") or "=" not in baris:
            continue
        k, v = baris.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    for wajib in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY"):
        if not env.get(wajib) or "xxxx" in env[wajib].lower():
            keluar(f"{wajib} belum diisi dengan benar di {BERKAS_ENV.name}.")
    return env


# =====================================================================
#  Pengambilan data dari Supabase
# =====================================================================
class Supabase:
    def __init__(self, env: dict):
        self.basis = env["SUPABASE_URL"].rstrip("/")
        kunci = env["SUPABASE_SERVICE_KEY"]
        self.kepala = {
            "apikey": kunci,
            "Authorization": f"Bearer {kunci}",
            "Content-Type": "application/json",
        }

    def ambil(self, tabel: str, pilih: str = "*") -> list[dict]:
        """Mengambil seluruh baris, 1000 per permintaan."""
        hasil, awal, langkah = [], 0, 1000
        while True:
            try:
                r = requests.get(
                    f"{self.basis}/rest/v1/{tabel}",
                    headers={**self.kepala, "Range": f"{awal}-{awal + langkah - 1}"},
                    params={"select": pilih},
                    timeout=60,
                )
            except requests.RequestException as e:
                keluar(f"Tidak bisa menghubungi Supabase: {e}")
            if r.status_code >= 300:
                keluar(f"Gagal membaca tabel {tabel}: {r.status_code} {r.text[:300]}")
            bagian = r.json()
            hasil.extend(bagian)
            if len(bagian) < langkah:
                return hasil
            awal += langkah

    def upsert(self, tabel: str, baris: list[dict], kunci_konflik: str,
               kering: bool = False) -> None:
        """Upsert in batches. `kering=True` performs no write at all.

        Batching matters here: one oversized POST that fails leaves no
        indication of how far it got, while a failed batch tells us exactly
        which slice to re-check.
        """
        if not baris:
            return
        if kering:
            print(f"  [KERING] {len(baris)} baris TIDAK dikirim ke {tabel}.")
            return
        UKURAN = 500
        for i in range(0, len(baris), UKURAN):
            potong = baris[i:i + UKURAN]
            r = requests.post(
                f"{self.basis}/rest/v1/{tabel}",
                headers={**self.kepala,
                         "Prefer": "resolution=merge-duplicates,return=minimal"},
                params={"on_conflict": kunci_konflik},
                data=json.dumps(potong),
                timeout=60,
            )
            if r.status_code >= 300:
                keluar(f"Gagal mengirim ke {tabel} (baris {i}-{i + len(potong) - 1}): "
                       f"{r.status_code} {r.text[:400]}")

    def ambil_opsional(self, tabel: str, pilih: str = "*") -> list[dict] | None:
        """Like ambil(), but None when the table or a selected column does not
        exist yet (patch not run), so a missing table never stops the build."""
        try:
            r = requests.get(f"{self.basis}/rest/v1/{tabel}",
                             headers={**self.kepala, "Range": "0-0"},
                             params={"select": pilih}, timeout=60)
        except requests.RequestException as e:
            keluar(f"Tidak bisa menghubungi Supabase: {e}")
        if r.status_code >= 400 and any(k in r.text for k in ("PGRST205", "42P01", "42703")):
            return None
        if r.status_code >= 300:
            keluar(f"Gagal membaca tabel {tabel}: {r.status_code} {r.text[:300]}")
        return self.ambil(tabel, pilih)

    def sisip(self, tabel: str, baris: list[dict], kering: bool = False) -> None:
        """Plain insert in batches (no conflict key); `kering=True` writes nothing."""
        if not baris:
            return
        if kering:
            print(f"  [KERING] {len(baris)} baris TIDAK dikirim ke {tabel}.")
            return
        UKURAN = 500
        for i in range(0, len(baris), UKURAN):
            potong = baris[i:i + UKURAN]
            r = requests.post(f"{self.basis}/rest/v1/{tabel}",
                              headers={**self.kepala, "Prefer": "return=minimal"},
                              data=json.dumps(potong), timeout=60)
            if r.status_code >= 300:
                keluar(f"Gagal mengirim ke {tabel} (baris {i}-{i + len(potong) - 1}): "
                       f"{r.status_code} {r.text[:400]}")


# =====================================================================
#  Validasi — bagian yang membuat pengolahan lokal sepadan
# =====================================================================
class Catatan:
    def __init__(self):
        self.galat: list[str] = []
        self.ingat: list[str] = []

    def g(self, p): self.galat.append(p)
    def i(self, p): self.ingat.append(p)

    def laporkan(self) -> bool:
        if self.ingat:
            print(f"\n  Peringatan ({len(self.ingat)}):")
            for p in self.ingat:
                print(f"    - {p}")
        if self.galat:
            print(f"\n  Kesalahan ({len(self.galat)}):")
            for p in self.galat:
                print(f"    ! {p}")
            return False
        if not self.ingat:
            print("\n  Validasi bersih. Tidak ada masalah ditemukan.")
        return True


def validasi(lembar, karya, penulis, skema, mitra, ctt: Catatan) -> None:
    dosen = lembar["dosen"]

    # ---- master dosen ----
    ganda = dosen.loc[dosen["nidn"].duplicated(), "nidn"].tolist()
    if ganda:
        ctt.g(f"NIDN ganda di lembar dosen: {', '.join(ganda)}")
    # Email boleh kosong untuk DT/DTT/industri (155, pemilik 2026-11-22); wajib untuk admin dan DTPS.
    tanpa_email = [d["nama"] for d in dosen.to_dict("records")
                   if not str(d.get("email") or "").strip() and (d.get("peran") == "admin" or masuk_dtps(d))]
    if tanpa_email:
        ctt.g(f"Admin/DTPS tanpa email: {', '.join(tanpa_email)}")
    if "admin" not in set(dosen["peran"]):
        ctt.g("Tidak ada dosen berperan 'admin'. Tidak akan ada yang bisa memverifikasi.")
    for _, d in dosen.iterrows():
        for kol, pola, ket in (
            ("sinta_id",  r"^[0-9]+$",                      "hanya angka"),
            ("scopus_id", r"^[0-9]+$",                      "hanya angka"),
            ("orcid",     r"^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$",
                                                            "format 0000-0000-0000-0000"),
        ):
            nilai = id_saja(d.get(kol))
            if nilai and not re.match(pola, nilai, re.I):
                ctt.i(f"{d['nama']}: {kol} '{nilai}' tidak sesuai pola "
                      f"({ket}). Tautan profilnya mungkin tidak berfungsi.")

    nidn_sah = set(dosen["nidn"])

    # ---- BKD ----
    bkd = lembar["bkd"]
    for i, b in bkd.iterrows():
        n = i + 2  # nomor baris di Excel
        if b["nidn"] not in nidn_sah:
            ctt.g(f"BKD baris {n}: NIDN {b['nidn']} tidak ada di lembar dosen.")
        if b.get("semester") not in {"ganjil", "genap"}:
            ctt.g(f"BKD baris {n}: semester '{b.get('semester')}' tidak sah.")
        if b.get("status") not in STATUS_DTPS_SAH:
            ctt.g(f"BKD baris {n}: status '{b.get('status')}' tidak sah.")
        total = 0.0
        for k in KOLOM_SKS:
            try:
                total += float(b.get(k) or 0)
            except ValueError:
                ctt.g(f"BKD baris {n}: nilai {k} bukan angka ('{b.get(k)}').")
        if total and not (SKS_MIN <= total <= SKS_MAKS):
            ctt.i(f"BKD baris {n} (NIDN {b['nidn']}): total {total:g} SKS, "
                  f"di luar rentang wajar {SKS_MIN}–{SKS_MAKS}. Periksa apakah benar.")

    if len(bkd):
        kunci = bkd[["nidn", "tahun_akademik", "semester"]].apply(tuple, axis=1)
        if kunci.duplicated().any():
            ctt.g("Ada baris BKD ganda untuk kombinasi NIDN + tahun akademik + semester.")

    # ---- prestasi mahasiswa ----
    for i, p in lembar["prestasi_mahasiswa"].iterrows():
        n = i + 2
        if p.get("tingkat") not in TINGKAT_SAH:
            ctt.g(f"Prestasi baris {n}: tingkat '{p.get('tingkat')}' tidak sah.")
        if p.get("bidang") not in BIDANG_SAH:
            ctt.g(f"Prestasi baris {n}: bidang '{p.get('bidang')}' tidak sah.")
        if not p.get("nim"):
            ctt.g(f"Prestasi baris {n}: NIM kosong.")
        for pem in pecah_pembimbing(p.get("pembimbing")):
            if pem not in nidn_sah:
                ctt.g(f"Prestasi baris {n}: NIDN pembimbing {pem} "
                      f"tidak ada di lembar dosen.")
        try:
            th = int(float(p.get("tahun") or 0))
            if not (2000 <= th <= datetime.now().year + 1):
                ctt.g(f"Prestasi baris {n}: tahun {th} di luar rentang wajar.")
        except ValueError:
            ctt.g(f"Prestasi baris {n}: tahun '{p.get('tahun')}' bukan angka.")

    # ---- karya dari Supabase ----
    ada_penulis = {p["karya_id"] for p in penulis}
    kode_skema = {s["kode"] for s in skema}
    for k in karya:
        if k["status"] == "terverifikasi" and k["id"] not in ada_penulis:
            ctt.g(f"Karya terverifikasi tanpa penulis terdaftar: {k['judul'][:60]}")
        # Skema pendanaan hanya wajib untuk penelitian dan PkM. Kategori
        # yang ditambahkan patch 05 — luaran, rekognisi, integrasi — sering
        # tidak berasal dari hibah sama sekali (HKI mandiri, buku, produk),
        # dan constraint karya_skema_wajib di basis data pun sudah
        # dipersempit ke dua kategori itu. Pemeriksaan di sini dulu lebih
        # ketat daripada basis datanya, sehingga baris yang sah ditolak.
        if k["kategori"] == "publikasi":
            if not (k.get("doi") or "").strip():
                ctt.i(f"Publikasi tanpa DOI, duplikat tidak terdeteksi: {k['judul'][:60]}")
        elif k["kategori"] in ("penelitian", "pkm"):
            if not k.get("skema_kode"):
                ctt.g(f"{k['kategori'].capitalize()} tanpa skema pendanaan: {k['judul'][:60]}")
            elif k["skema_kode"] not in kode_skema:
                ctt.g(f"Skema '{k['skema_kode']}' tidak ada di tabel acuan: {k['judul'][:60]}")
            elif "lainnya" in k["skema_kode"] and not (k.get("keterangan") or "").strip():
                ctt.i(f"Skema 'lainnya' tanpa keterangan nama skema: {k['judul'][:60]}")
        else:
            # Skema boleh kosong, tetapi bila diisi harus kode yang sah.
            if k.get("skema_kode") and k["skema_kode"] not in kode_skema:
                ctt.g(f"Skema '{k['skema_kode']}' tidak ada di tabel acuan: {k['judul'][:60]}")

    # Nama mitra diketik bebas, jadi ejaan yang sedikit berbeda akan
    # terhitung sebagai dua mitra. Peringatan ini membantu menyeragamkannya
    # sejak awal, sebelum daftarnya menumpuk.
    judul_karya = {k["id"]: k["judul"] for k in karya}
    mitra_per_karya: dict[str, list[dict]] = {}
    for m in mitra:
        mitra_per_karya.setdefault(m["karya_id"], []).append(m)

    ejaan: dict[str, set] = {}
    for m in mitra:
        nm = (m.get("institusi") or "").strip()
        if not nm:
            continue
        if not (m.get("tingkat") or "").strip():
            ctt.i(f"Mitra '{nm}' tanpa tingkat kerja sama: "
                  f"{judul_karya.get(m['karya_id'], '')[:50]}")
        ejaan.setdefault(nm.lower(), set()).add(nm)
    for kunci, bentuk in ejaan.items():
        if len(bentuk) > 1:
            ctt.i(f"Nama mitra dieja berbeda-beda: {' / '.join(sorted(bentuk))}. "
                  f"Seragamkan agar tidak terhitung sebagai mitra terpisah.")

    # Kolom mitra lama pada tabel karya tidak lagi dibaca sejak patch 06.
    # Bila masih ada yang terisi tanpa pasangan di karya_mitra, berarti ada
    # penyuntingan lewat Table Editor yang akan hilang dari rekap.
    tertinggal = [k for k in karya
                  if (k.get("mitra_institusi") or "").strip()
                  and not mitra_per_karya.get(k["id"])]
    if tertinggal:
        ctt.g(f"{len(tertinggal)} karya masih memakai kolom mitra lama tanpa baris "
              f"di karya_mitra, contoh: {tertinggal[0]['judul'][:50]}. "
              f"Jalankan ulang bagian migrasi pada instal-lengkap.sql.")

    # Bukti wajib ada sebelum masuk borang. Entri terverifikasi tanpa bukti
    # adalah temuan yang paling sering muncul saat asesmen lapangan.
    tanpa_bukti = [k for k in karya
                   if k["status"] == "terverifikasi"
                   and not (k.get("bukti_url") or "").strip()
                   and not (k.get("bukti_path") or "").strip()]
    if tanpa_bukti:
        ctt.i(f"{len(tanpa_bukti)} karya terverifikasi belum punya tautan bukti, "
              f"contoh: {tanpa_bukti[0]['judul'][:50]}")


    tanpa_bulan = sum(1 for k in karya if k["status"] == "terverifikasi"
                      and not k.get("bulan"))
    if tanpa_bulan:
        ctt.i(f"{tanpa_bulan} karya terverifikasi tanpa bulan — pada tampilan "
              f"per-TS, tahun kalendernya dipakai apa adanya.")

    diajukan = sum(1 for k in karya if k["status"] == "diajukan")
    if diajukan:
        ctt.i(f"{diajukan} karya masih menunggu verifikasi dan belum ikut dihitung.")


# =====================================================================
#  Pembangunan keluaran
# =====================================================================
KEGIATAN = ("penelitian", "pkm")
TURUNAN = ("publikasi", "luaran")


def sdgs_dari(k: dict) -> list[int]:
    """Nomor SDG (1-17) yang dipilih dosen untuk karya ini (instal-lengkap.sql,
    pemilik 2026-11-11). Kosong bila tidak terkait atau kolom belum ada."""
    v = k.get("sdgs") or []
    if isinstance(v, str):   # bentuk teks larik Postgres, mis. "{6,11}"
        v = [x for x in v.strip("{}").split(",") if x.strip()]
    hasil = set()
    for x in v:
        try:
            n = int(x)
        except (TypeError, ValueError):
            continue
        if 1 <= n <= 17:
            hasil.add(n)
    return sorted(hasil)


def _bulat(v) -> int:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return 0
    return 0 if x != x else int(x)


def kunci_id(v) -> str:
    """Id kerja sama induk sebagai teks ('' bila kosong); pandas memberi float."""
    if v is None or (isinstance(v, float) and v != v) or str(v).strip() in ("", "nan"):
        return ""
    s = str(v).strip()
    return str(_bulat(s)) if re.fullmatch(r"\d+(\.0+)?", s) else s


def ts_karya(k) -> int:
    """TS 1 Sep s.d. 31 Agu: bulan >= 9 masuk TS tahun berikutnya."""
    th = _bulat(k.get("tahun"))
    return th + 1 if _bulat(k.get("bulan")) >= 9 else th


def baris_kerjasama_karya(karya, mitra_per_karya, mitra_induk) -> list[tuple]:
    """Mitra kerja sama dari karya terverifikasi untuk skor butir 6.

    Aturan sama dengan site/kerjasama-karya.js (pemilik 2026-11-10), tanpa
    mitra MoU induk, yang dihitung dari lembar kerjasama:
      kegiatan (penelitian/PkM): satu baris per mitra, TS kegiatan;
      turunan (publikasi/luaran) berpayung: mitra yang sama dengan payung
        tidak dihitung lagi; mitra lain sekali per (payung, mitra), TS
        turunan paling awal;
      turunan tanpa payung terverifikasi: satu baris per mitra, TS turunan.
    karya: karya terverifikasi; mitra_per_karya: id -> [{nama, tingkat}];
    mitra_induk: kunci_id kerja sama -> nama mitra (huruf kecil).
    Hasil: [(ts, tingkat, kategori, nama mitra)].
    """
    def rapi(s):
        return str(s or "").strip().lower()
    per_id = {k["id"]: k for k in karya}

    def payung(t):
        K = per_id.get(t.get("induk_id")) if t.get("induk_id") else None
        return K if K and K.get("kategori") in KEGIATAN else None

    turunan_per: dict = {}
    for t in karya:
        K = payung(t) if t.get("kategori") in TURUNAN else None
        if K:
            turunan_per.setdefault(K["id"], []).append(t)
    hasil = []
    for K in karya:
        if K.get("kategori") not in KEGIATAN:
            continue
        induk = mitra_induk.get(kunci_id(K.get("kerjasama_id")))
        sudah = {induk} if induk else set()
        for m in mitra_per_karya.get(K["id"], []):
            n = rapi(m.get("nama"))
            if not n or n in sudah:
                continue
            sudah.add(n)
            hasil.append((ts_karya(K), m.get("tingkat") or "", K["kategori"], m["nama"]))
        baru: dict = {}
        for t in sorted(turunan_per.get(K["id"], []), key=ts_karya):
            for m in mitra_per_karya.get(t["id"], []):
                n = rapi(m.get("nama"))
                if n and n not in sudah and n not in baru:
                    baru[n] = (ts_karya(t), m.get("tingkat") or "", K["kategori"], m["nama"])
        hasil.extend(baru.values())
    for t in karya:
        if t.get("kategori") not in TURUNAN or payung(t):
            continue
        sudah = set()
        for m in mitra_per_karya.get(t["id"], []):
            n = rapi(m.get("nama"))
            if n and n not in sudah:
                sudah.add(n)
                hasil.append((ts_karya(t), m.get("tingkat") or "", "penelitian", m["nama"]))
    return hasil


def bangun(env, lembar, karya, penulis, skema, kelompok, mahasiswa, mitra,
           ctt: Catatan, hanya_periksa: bool) -> None:
    dosen = lembar["dosen"]
    nama_by_nidn = dict(zip(dosen["nidn"], dosen["nama"]))
    # Pimpinan bukan DTPS (mis. Dekan): nama tidak masuk keluaran publik (pemilik 2026-11-21).
    sembunyi = nama_tersembunyi(dosen.to_dict("records") if len(dosen) else [], lembar.get("nama_gelar"))
    peta_skema = {s["kode"]: s for s in skema}
    nama_kelompok = {k["kode"]: k["nama"] for k in kelompok}

    # Karya terverifikasi yang ditandai TIDAK relevan dengan visi keilmuan
    # tetap tampil di daftar publikasi/profil dosen (karya sah miliknya),
    # tetapi dikeluarkan dari SELURUH hitungan butir akreditasi prodi:
    # dtps, akreditasi, luaran, integrasi, dan agregat lainnya. Kolomnya
    # baru ada sejak patch 10; baris lama tanpa kolom dianggap relevan.
    semua_verif = [k for k in karya if k["status"] == "terverifikasi"]
    verif = [k for k in semua_verif if k.get("relevan_visi") is not False]
    n_luar = len(semua_verif) - len(verif)
    if n_luar:
        print(f"  Catatan: {n_luar} karya terverifikasi ditandai di luar visi "
              f"keilmuan — tampil di profil, tidak dihitung di butir prodi.")

    # Dua fungsi bantu yang dipakai hampir semua blok di bawah, jadi
    # didefinisikan paling awal (pernah diletakkan di tengah dan meledak
    # sebagai NameError saat blok agregat memakainya lebih dulu).
    def _angka(v, bawaan=0.0):
        try:
            x = float(str(v).replace(",", "."))
        except (ValueError, TypeError):
            return bawaan
        # Sel kosong dari pandas menjadi NaN, dan float("nan") TIDAK memicu
        # ValueError — tanpa pemeriksaan ini, int(_angka(sel_kosong)) meledak.
        return bawaan if x != x else x

    # Tahun akademik (TS) berjalan 1 Sep s.d. 31 Agu: bulan >= 9 masuk TS
    # tahun berikutnya. Karya lama tanpa bulan memakai tahun kalendernya.
    def _ts(k):
        th = int(_angka(k.get("tahun")))
        return th + 1 if int(_angka(k.get("bulan"))) >= 9 else th
    penulis_per_karya: dict[str, list[dict]] = {}
    for p in penulis:
        nm = p.get("_nama") or ""
        if not nm or nm.strip() in sembunyi:   # penulis pimpinan bukan DTPS tidak disebut (2026-11-21)
            continue
        penulis_per_karya.setdefault(p["karya_id"], []).append({
            "nama": nm,
            "slug": slug(nm),
            "peran": p.get("peran") or "anggota",
            "korespondensi": bool(p.get("korespondensi")),
        })

    mhs_per_karya: dict[str, list[dict]] = {}
    for m in mahasiswa:
        mhs_per_karya.setdefault(m["karya_id"], []).append(m)

    # Satu karya boleh punya banyak mitra sejak patch 06. Daftarnya diurutkan
    # menurut nama agar keluaran data.json stabil antar-pembangunan; tanpa itu
    # git akan mencatat perubahan palsu setiap kali urutan dari API bergeser.
    mitra_per_karya: dict[str, list[dict]] = {}
    for m in mitra:
        nm = (m.get("institusi") or "").strip()
        if not nm:
            continue
        mitra_per_karya.setdefault(m["karya_id"], []).append({
            "nama": nm,
            "tingkat": (m.get("tingkat") or "").strip(),
            "negara": (m.get("negara") or "").strip(),
        })
    for v in mitra_per_karya.values():
        v.sort(key=lambda x: x["nama"].lower())

    def daftar_mitra(kid):
        return mitra_per_karya.get(kid, [])

    def nama_penulis(kid):
        return sorted(penulis_per_karya.get(kid, []), key=lambda x: x["nama"])

    # Lembar Excel memakai kolom terpisah tahun + bulan (opsional).
    # Aturan TS sama dengan karya: bulan >= 9 masuk TS tahun berikutnya;
    # bulan kosong = TS mengikuti tahun kalendernya.
    def _ts_baris(th, bl):
        th = int(_angka(th))
        return th + 1 if int(_angka(bl)) >= 9 else th

    # ---------- agregat prestasi (tanpa nama dan NIM) ----------
    prestasi = lembar["prestasi_mahasiswa"]
    agg_prestasi = []
    if len(prestasi):
        pr = prestasi.copy()
        pr["tahun"] = pr["tahun"].astype(float).astype(int)
        pr["tahun_ts"] = [
            _ts_baris(t, b) for t, b in
            zip(pr["tahun"], pr.get("bulan", pd.Series([None] * len(pr))))]
        g = (pr.groupby(["tahun", "tahun_ts", "tingkat", "bidang"]).size()
             .reset_index(name="jumlah"))
        agg_prestasi = g.sort_values("tahun", ascending=False).to_dict("records")

    agg_pembimbing = agregat_pembimbing(prestasi, {n: v for n, v in nama_by_nidn.items() if v not in sembunyi})

    # Agregat keterlibatan mahasiswa untuk halaman monitoring.
    # Hanya angka: keterlibatan (jumlah baris) dan mahasiswa unik.
    # NIM dipakai sementara untuk menghitung keunikan, lalu dibuang.
    _mhs = {}
    for k in verif:
        for m in mhs_per_karya.get(k["id"], []):
            d = _mhs.setdefault((int(k["tahun"]), _ts(k), k["kategori"]),
                                {"keterlibatan": 0, "nim": set()})
            d["keterlibatan"] += 1
            d["nim"].add(str(m.get("nim", "")))
    agg_mahasiswa = [
        {"tahun": t, "tahun_ts": ts, "kategori": kat,
         "keterlibatan": v["keterlibatan"],
         "mahasiswa_unik": len(v["nim"])}
        for (t, ts, kat), v in sorted(_mhs.items(),
                                      key=lambda x: (-x[0][0], x[0][2]))
    ]

    # ---------- indikator LKPS ----------
    BAGIAN_LUARAN = {
        "paten": 1, "paten_sederhana": 1,
        "hak_cipta": 2, "desain_industri": 2, "desain_produk_industri": 2,
        "merek": 2, "rahasia_dagang": 2,
        "ttg": 3, "teknologi_tepat_guna": 3, "produk": 3, "karya_seni": 3,
        "buku_isbn": 4, "buku": 4, "book_chapter": 4, "bab_buku": 4,
    }
    NAMA_BAGIAN = {1: "HKI: Paten & Paten Sederhana",
                   2: "HKI: Hak Cipta, Desain, dll.",
                   3: "Teknologi Tepat Guna & Produk",
                   4: "Buku ber-ISBN & Book Chapter"}

    aktif = [d for d in dosen.to_dict("records") if masuk_dtps(d)]
    # 154 (pemilik 2026-11-22): untuk akreditasi DTPS dihitung hanya bila mengampu MK prodi pada TS berjalan
    # (Penyusunan kelas + centang manual); tanpa data mengampu sama sekali aturan tidak diterapkan (nidn_mengampu).
    ampu = lembar.get("ampu_ts") or {}
    n_homebase = len(aktif)
    if ampu.get("diterapkan"):
        aktif = [d for d in aktif if str(d.get("nidn") or "").strip() in ampu["nidn"]]
    n_dtps = len(aktif) or 1
    slug_dtps = {slug(d["nama"]) for d in aktif}

    doktor = sum(1 for d in aktif
                 if any(x in (d.get("pendidikan") or "").lower()
                        for x in ("s3", "doktor", "dr", "ph")))
    jabatan_hit: dict[str, int] = {}
    for d in aktif:
        j = (d.get("jabatan") or "").strip().lower().replace(" ", "_") \
            or "tanpa_jabatan"
        jabatan_hit[j] = jabatan_hit.get(j, 0) + 1

    # Luaran, rekognisi, dan integrasi kini diinput dosen lewat form web
    # dan tersimpan di tabel karya (kategori masing-masing). Hanya yang
    # sudah TERVERIFIKASI yang dihitung, sama seperti publikasi.
    def _dosen_karya(kid):
        return [a["nama"] for a in penulis_per_karya.get(kid, [])]

    luaran_pub = []
    for k in verif:
        if k["kategori"] != "luaran":
            continue
        jn = (k.get("sub_jenis") or "").strip().lower()
        bg = BAGIAN_LUARAN.get(jn)
        if bg is None:
            print(f"  Catatan: jenis luaran '{jn}' tidak dikenal — "
                  f"masuk bagian 3 (produk).")
            bg = 3
        luaran_pub.append({
            "tahun": int(_angka(k.get("tahun"))),
            "induk_id": k.get("induk_id"),
            "tahun_ts": _ts(k),
            "jenis": jn,
            "bagian": bg, "nama_bagian": NAMA_BAGIAN.get(bg, ""),
            "judul": k.get("judul") or "",
            "sdgs": sdgs_dari(k),
            "dosen": _dosen_karya(k["id"])})

    rekognisi_pub = [{
        "tahun": int(_angka(k.get("tahun"))),
        "tahun_ts": _ts(k),
        "dosen": ", ".join(_dosen_karya(k["id"])),
        "bentuk": (k.get("sub_jenis") or "").strip().lower(),
        "nama_kegiatan": k.get("judul") or "",
        "tingkat": (k.get("tingkat") or "").strip().lower()}
        for k in verif if k["kategori"] == "rekognisi"]

    # Tahun integrasi diisi sebagai TAHUN AJARAN MULAI, jadi TS-nya
    # selalu tahun berikutnya, tidak bergantung bulan.
    integrasi_pub = [{
        "tahun": int(_angka(k.get("tahun"))),
        "tahun_ts": int(_angka(k.get("tahun"))) + 1,
        "dosen": ", ".join(_dosen_karya(k["id"])),
        "mata_kuliah": k.get("mata_kuliah") or "",
        "judul_kegiatan": k.get("judul") or "",
        "bentuk": (k.get("sub_jenis") or "").strip().lower()}
        for k in verif if k["kategori"] == "integrasi"]

    # Indikator 3: DTPS dengan karya utama (penulis pertama/korespondensi)
    # pada jurnal internasional bereputasi / prosiding terindeks
    # Scopus, IEEE, SPIE / paten.
    # Butir syarat perlu ini dibatasi TIGA TAHUN TERAKHIR, jadi tahun tiap
    # karya ikut disimpan; penyaringan periodenya dikerjakan di halaman
    # monitoring supaya definisi "tiga tahun terakhir" tidak terkunci di sini.
    utama_pasang: set[tuple[str, int]] = set()
    for k in verif:
        if k["kategori"] != "publikasi":
            continue
        teks_k = f"{k.get('jenis','')} {k.get('tingkat','')} " \
                 f"{k.get('indeksasi','')}".lower()
        if not any(x in teks_k for x in
                   ("bereputasi", "scopus", "ieee", "spie", "wos")):
            continue
        th = _ts(k)
        for a in penulis_per_karya.get(k["id"], []):
            if a["peran"] == "penulis_pertama" or a["korespondensi"]:
                utama_pasang.add((a["slug"], th))
    for l in luaran_pub:
        if l["bagian"] == 1:
            for nm in l["dosen"]:
                utama_pasang.add((slug(nm), l.get("tahun_ts", l["tahun"])))
    utama_pasang = {(sg, th) for sg, th in utama_pasang if sg in slug_dtps}
    utama_int = {sg for sg, _ in utama_pasang}

    # Tampilan publik (pemilik 2026-11-22): "dosen tetap" termasuk yang sedang tugas belajar (tampil_publik), sedangkan
    # jumlah/doktor/jabatan tetap DTPS (masuk_dtps) untuk akreditasi.
    dtps_pub = {"jumlah": len(aktif), "doktor": doktor, **dosen_tetap_publik(dosen.to_dict("records")),
                "ampu": {"ta": ampu.get("ta"), "diterapkan": bool(ampu.get("diterapkan")),
                         "tidak_mengampu": n_homebase - len(aktif)},
                "jabatan": jabatan_hit,
                "karya_utama_internasional": len(utama_int),
                "karya_utama_rinci": sorted(
                    [{"slug": sg, "tahun": th} for sg, th in utama_pasang],
                    key=lambda x: (-x["tahun"], x["slug"]))}

    # Kolom opsional: kosong -> None (belum diisi), dibedakan dari 0 orang.
    def _bulat_atau_none(v):
        x = _angka(v, None)
        return None if x is None else int(x)

    tracer_pub = [{
        "tahun_lulus": int(_angka(r.get("tahun_lulus"))),
        "lulusan": int(_angka(r.get("jumlah_lulusan"))),
        "terlacak": int(_angka(r.get("jumlah_terlacak"))),
        "waktu_tunggu_bulan": _angka(r.get("rata_rata_waktu_tunggu_bulan")),
        "sesuai_bidang": int(_angka(r.get("bekerja_sesuai_bidang"))),
        # kolom opsional untuk butir 51 (tingkat tempat kerja)
        "kerja_internasional": int(_angka(r.get("kerja_internasional"))),
        "kerja_nasional": int(_angka(r.get("kerja_nasional"))),
        "kerja_wilayah": int(_angka(r.get("kerja_wilayah"))),
        # Butir 49: pita hanya untuk memeriksa rata-rata WT (pemilik 2026-11-05);
        # butir 50: KBK = (sedang + tinggi) / terlacak bila tingkat kesesuaian diisi.
        **{k: _bulat_atau_none(r.get(k)) for k in (
            "wt_kurang_3", "wt_3_18", "wt_lebih_18",
            "kesesuaian_rendah", "kesesuaian_sedang", "kesesuaian_tinggi")}}
        for r in lembar["tracer_lulusan"].to_dict("records")]

    # Karya mandiri mahasiswa — judul boleh publik, identitas TIDAK.
    mhs_publikasi_pub = [{
        "tahun": int(_angka(r.get("tahun"))),
        "tahun_ts": _ts_baris(r.get("tahun"), r.get("bulan")),
        "judul": r.get("judul") or "",
        "jenis": (r.get("jenis") or "").strip().lower(),
        "tingkat": (r.get("tingkat") or "").strip().lower()}
        for r in lembar["publikasi_mahasiswa"].to_dict("records")]
    mhs_luaran_pub = []
    for r in lembar["luaran_mahasiswa"].to_dict("records"):
        jn = (r.get("jenis") or "").strip().lower().replace(" ", "_")
        bg = BAGIAN_LUARAN.get(jn, 3)
        mhs_luaran_pub.append({
            "tahun": int(_angka(r.get("tahun"))),
            "tahun_ts": _ts_baris(r.get("tahun"), r.get("bulan")),
            "jenis": jn,
            "bagian": bg, "nama_bagian": NAMA_BAGIAN.get(bg, ""),
            "judul": r.get("judul") or ""})

    # ---------- agregat akreditasi (APS-AV 2025) ----------

    # Angka gabungan untuk kalkulator skor di skor.html. HANYA jumlah;
    # tidak ada nama, NIM, atau daftar per orang di blok ini.
    #
    # Pemetaan kategori publikasi NA1..NB3 (butir 33 dan 46):
    #   NA4 jurnal internasional bereputasi   NB3 prosiding terindeks
    #   NA3 jurnal internasional              NB2 prosiding internasional
    #   NA2 jurnal nasional terakreditasi     NB1 prosiding nasional/wilayah
    #   NA1 jurnal nasional
    # "Bereputasi/terindeks" dibaca dari indeksasi (scopus/wos) atau kata
    # "bereputasi" pada tingkat. Buku, bab buku, dan HKI tidak masuk
    # kategori mana pun pada kedua butir itu.
    def _kat_na(jenis, tingkat, indeksasi):
        jn = (jenis or "").strip().lower()
        tg = (tingkat or "").strip().lower()
        ix = (indeksasi or "").strip().lower()
        rep = any(x in ix for x in ("scopus", "wos", "bereputasi")) \
              or "bereputasi" in tg
        if jn == "jurnal":
            if "internasional" in tg:
                return "na4" if rep else "na3"
            return "na2" if "sinta" in ix else "na1"
        if jn == "prosiding":
            if rep:
                return "nb3"
            return "nb2" if "internasional" in tg else "nb1"
        return None

    KAT_NA = ("na1", "na2", "na3", "na4", "nb1", "nb2", "nb3")

    def _tambah(peta, tahun, kunci):
        if not kunci:
            return
        b = peta.setdefault(tahun, {k: 0 for k in KAT_NA})
        b[kunci] += 1

    # Publikasi DTPS (butir 33) dan publikasi mahasiswa (butir 46). Tabel
    # 6.e.1 LKPS hanya menghitung publikasi dengan mahasiswa sebagai PENULIS
    # PERTAMA (mandiri atau bersama DTPS). Jadi publikasi dosen dihitung untuk
    # butir 46 hanya bila ada mahasiswa berperan 'penulis_pertama' di form web;
    # lembar Excel publikasi_mahasiswa berisi publikasi mandiri mahasiswa.
    akr_pub_dtps: dict[int, dict] = {}
    akr_pub_mhs: dict[int, dict] = {}
    for k in verif:
        if k["kategori"] != "publikasi":
            continue
        th = _ts(k)
        kat = _kat_na(k.get("jenis"), k.get("tingkat"), k.get("indeksasi"))
        _tambah(akr_pub_dtps, th, kat)
        if any(m.get("peran") == "penulis_pertama" for m in mhs_per_karya.get(k["id"], [])):
            _tambah(akr_pub_mhs, th, kat)
    for r in lembar["publikasi_mahasiswa"].to_dict("records"):
        _tambah(akr_pub_mhs, _ts_baris(r.get("tahun"), r.get("bulan")),
                _kat_na(r.get("jenis"), r.get("tingkat"), r.get("indeksasi")))

    # Luaran (butir 34 dan 47). NHKI pada instrumen khusus Pencatatan
    # Ciptaan, jadi hanya hak_cipta yang dihitung; desain industri, merek,
    # dan rahasia dagang masuk "lainnya" dan tidak menyumbang skor.
    PETA_NLP = {"paten": "paten", "paten_sederhana": "paten",
                "ttg": "ttg", "teknologi_tepat_guna": "ttg", "produk": "ttg",
                "buku_isbn": "bc", "buku": "bc",
                "book_chapter": "bc", "bab_buku": "bc",
                "hak_cipta": "hki"}

    def _tambah_nlp(peta, tahun, jenis):
        b = peta.setdefault(tahun, {"paten": 0, "ttg": 0, "bc": 0,
                                    "hki": 0, "lainnya": 0})
        b[PETA_NLP.get(jenis, "lainnya")] += 1

    akr_luaran_dtps: dict[int, dict] = {}
    akr_luaran_mhs: dict[int, dict] = {}
    for l in luaran_pub:
        _tambah_nlp(akr_luaran_dtps, l.get("tahun_ts", l["tahun"]), l["jenis"])
    for l in mhs_luaran_pub:
        _tambah_nlp(akr_luaran_mhs, l.get("tahun_ts", l["tahun"]), l["jenis"])

    # Tahun akademik: '2025/2026' -> tahun_ts 2026 (tahun ujung TS).
    akr_ta = []
    for r in lembar["mahasiswa_ta"].to_dict("records"):
        ta = str(r.get("tahun_akademik") or "").strip()
        if not ta:
            continue
        try:
            ts = int(ta.replace("-", "/").split("/")[-1])
        except ValueError:
            print(f"  Catatan: tahun_akademik '{ta}' tidak terbaca — "
                  f"baris mahasiswa_ta dilewati.")
            continue
        akr_ta.append({
            "ta": ta, "tahun_ts": ts,
            "mahasiswa_aktif": int(_angka(r.get("jumlah_mahasiswa_aktif"))),
            "lulusan": int(_angka(r.get("jumlah_lulusan"))),
            "rerata_ipk": _angka(r.get("rerata_ipk_lulusan")),
            # kolom opsional; 0 berarti belum diisi
            "mahasiswa_asing": int(_angka(r.get("jumlah_mahasiswa_asing"))),
            "rerata_masa_studi": _angka(r.get("rerata_masa_studi_tahun")),
            "persen_tepat_waktu": _angka(r.get("persen_lulus_tepat_waktu")),
        })
    akr_ta.sort(key=lambda x: -x["tahun_ts"])

    # Butir 52: aggregate survey percentages per TS and aspect (no names).
    # The score itself is computed in the browser (butir-manual.js
    # tkKepuasan), which also checks that all seven aspects are present.
    akr_kepuasan = []
    for r in lembar.get("kepuasan_ts", pd.DataFrame()).to_dict("records"):
        ta = str(r.get("tahun_akademik") or "").strip()
        if not re.fullmatch(r"\d{4}/\d{4}", ta):
            continue
        akr_kepuasan.append({
            "tahun_ts": int(ta[5:]), "aspek": str(r.get("aspek") or "").strip(),
            **{k: _angka(r.get(k)) for k in ("sangat_baik", "baik", "cukup", "kurang")},
        })
    akr_kepuasan.sort(key=lambda x: (-x["tahun_ts"], x["aspek"]))

    def _rapikan(peta):
        return [{"tahun": t, **v} for t, v in sorted(peta.items(),
                                                     key=lambda x: -x[0])]

    # Kerja sama per tingkat (butir 6-II): satu baris mitra = satu kerja
    # sama. Tingkat kosong dihitung tersendiri agar kelihatan belum rapi.
    akr_kerjasama: dict[int, dict] = {}
    # Keterlibatan mahasiswa per judul (butir 23 dan 25): jumlah judul dan
    # judul yang melibatkan >= 1 mahasiswa.
    akr_keg_mhs: dict[tuple, dict] = {}
    # Sumber dana penelitian/PkM (butir 31 dan 32): luar negeri / dalam
    # negeri / PT+mandiri, dari kolom sumber_dana hasil trigger skema.
    akr_dana: dict[tuple, dict] = {}
    def _laci(ts):
        return akr_kerjasama.setdefault(ts, {
            "internasional": 0, "nasional": 0, "wilayah": 0,
            "tanpa_tingkat": 0, "pendidikan": 0})

    def ember_dana(k):
        """Map one record's sumber_dana to its LKPS bucket.

        Single definition on purpose: the butir 31/32 aggregate and the
        public per-butir breakdown both call this, so the two cannot drift.
        """
        sd = (k.get("sumber_dana") or "").lower()
        if "luar" in sd:
            return "luar_negeri"
        if "dalam" in sd:
            return "dalam_negeri"
        if sd.strip():
            return "pt_mandiri"          # mandiri + perguruan_tinggi
        return "tanpa_sumber"

    # Lembar kerjasama: satu baris berlaku pada SETIAP TS yang beririsan
    # dengan rentang tahun_mulai..tahun_selesai, karena instrumen
    # menghitung kerja sama yang aktif pada periode penilaian.
    for r in lembar["kerjasama"].to_dict("records"):
        mitra_nm = str(r.get("mitra") or "").strip()
        if not mitra_nm or mitra_nm.lower() == "nan":
            continue
        th0 = int(_angka(r.get("tahun_mulai")))
        if not th0:
            ctt.i(f"Kerja sama '{mitra_nm[:40]}' tanpa tahun_mulai — dilewati.")
            continue
        # tahun_selesai kosong = MoU tanpa tanggal berakhir, dianggap MASIH
        # BERLAKU sampai TS berjalan. Kalau kerja sama sudah usai, isi
        # tahun_selesai-nya agar tidak terus terhitung tiap tahun.
        th1 = int(_angka(r.get("tahun_selesai")))
        if not th1:
            th1 = max(th0, datetime.now().year + 1)
        if th1 < th0:
            ctt.g(f"Kerja sama '{mitra_nm[:40]}': tahun_selesai lebih awal "
                  f"daripada tahun_mulai.")
            continue
        tg = str(r.get("tingkat") or "").strip().lower()
        jn = str(r.get("jenis") or "").strip().lower()
        for ts in range(th0, max(th0, th1) + 1):
            b = _laci(ts)
            if "internasional" in tg:
                b["internasional"] += 1
            elif "nasional" in tg:
                b["nasional"] += 1
            elif tg:
                b["wilayah"] += 1
            else:
                b["tanpa_tingkat"] += 1
            if jn.startswith("pendidik"):
                b["pendidikan"] += 1

    # Mitra pada karya (baris_kerjasama_karya, aturan payung pemilik
    # 2026-11-10; sama dengan LKPS 2.a.2/2.a.3 di site/kerjasama-karya.js).
    # Mitra yang sama dengan kerja sama induk (karya.kerjasama_id, patch 24)
    # sudah terhitung lewat lembar kerjasama di atas.
    mitra_induk = {kunci_id(r.get("id")): str(r.get("mitra") or "").strip().lower()
                   for r in lembar["kerjasama"].to_dict("records") if kunci_id(r.get("id"))}
    for ts, tg, _kat, _nama in baris_kerjasama_karya(verif, mitra_per_karya, mitra_induk):
        b = _laci(ts)
        tg = tg.lower()
        if "internasional" in tg:
            b["internasional"] += 1
        elif "nasional" in tg:
            b["nasional"] += 1
        elif tg.strip():
            b["wilayah"] += 1
        else:
            b["tanpa_tingkat"] += 1
    for k in verif:
        ts = _ts(k)
        if k["kategori"] in ("penelitian", "pkm"):
            d = akr_keg_mhs.setdefault((ts, k["kategori"]),
                                       {"total": 0, "dengan_mahasiswa": 0})
            d["total"] += 1
            if mhs_per_karya.get(k["id"]):
                d["dengan_mahasiswa"] += 1
            e = akr_dana.setdefault((ts, k["kategori"]),
                {"luar_negeri": 0, "dalam_negeri": 0,
                 "pt_mandiri": 0, "tanpa_sumber": 0})
            e[ember_dana(k)] += 1

    # Rekognisi per dosen (butir 37): pasangan slug-tahun, tanpa rincian.
    akr_rekognisi = sorted(
        {(a["slug"], _ts(k)) for k in verif if k["kategori"] == "rekognisi"
         for a in penulis_per_karya.get(k["id"], []) if a["slug"] in slug_dtps},
        key=lambda x: (-x[1], x[0]))

    def _rapikan2(peta):
        return [{"tahun": t, "kategori": kat, **v}
                for (t, kat), v in sorted(peta.items(),
                                          key=lambda x: (-x[0][0], x[0][1]))]

    # Kohort lulusan (Tabel 6.d): titik tengah tiap pita masa studi
    # dipakai sebagai penaksir MS. Pita terakhir (6,5-8) memakai 7,25.
    # Instrumen tidak memberi angka tunggal per pita, jadi ini pendekatan
    # yang dinyatakan terbuka di halaman skor.
    PITA = (("lulus_3_5_sd_4_5", 4.0), ("lulus_4_5_sd_5_5", 5.0),
            ("lulus_5_5_sd_6_5", 6.0), ("lulus_6_5_sd_8", 7.25))
    akr_kohort = []
    for r in lembar["kohort_lulusan"].to_dict("records"):
        thm = int(_angka(r.get("tahun_masuk")))
        if not thm:
            continue
        pita = {k: int(_angka(r.get(k))) for k, _ in PITA}
        n_lulus = sum(pita.values())
        masuk = int(_angka(r.get("jumlah_masuk")))
        if n_lulus > masuk > 0:
            ctt.g(f"Kohort {thm}: lulusan ({n_lulus}) melebihi jumlah masuk "
                  f"({masuk}).")
        akr_kohort.append({
            "tahun_masuk": thm, "masuk": masuk, "lulus": n_lulus,
            **pita,
            "ms_tertimbang": (sum(pita[k] * m for k, m in PITA) / n_lulus)
                             if n_lulus else 0.0,
        })
    akr_kohort.sort(key=lambda x: -x["tahun_masuk"])

    akreditasi_pub = {
        "ta": akr_ta,
        "kepuasan": akr_kepuasan,
        "kohort": akr_kohort,
        "kerjasama": _rapikan(akr_kerjasama),
        "kegiatan_mhs": _rapikan2(akr_keg_mhs),
        "sumber_dana": _rapikan2(akr_dana),
        "rekognisi_dtps": [{"slug": sg, "tahun": th} for sg, th in akr_rekognisi],
        "publikasi_dtps": _rapikan(akr_pub_dtps),
        "publikasi_mhs": _rapikan(akr_pub_mhs),
        "luaran_dtps": _rapikan(akr_luaran_dtps),
        "luaran_mhs": _rapikan(akr_luaran_mhs),
    }

    # Peta induk_id -> judul kegiatan, untuk menampilkan asal karya tanpa
    # membocorkan id internal ke berkas publik.
    judul_induk = {k["id"]: k["judul"] for k in semua_verif
                   if k["kategori"] in ("penelitian", "pkm")}

    # data.json is pushed to a public repo, and a link that lands in git
    # history cannot be taken back. Evidence links (bukti_url, bukti_path, karya_bukti) are never published:
    # the public sees lists only; evidence is for logged-in users and
    # assessors via the workspace (owner 2026-11-04). The karya "Tautan"
    # field is meant for the journal page, but a Drive link typed there is
    # evidence too, so it is dropped as well.
    def url_publik(u):
        u = str(u or "").strip()
        if not u or re.search(r"(drive|docs|script)\.google\.", u, re.I):
            return None
        return u

    # ---------- KELUARAN PUBLIK ----------
    # Tanpa nama mahasiswa, tanpa NIM, tanpa nominal dana, tanpa BKD.
    publik = {
        "prodi": env.get("NAMA_PRODI", "Program Studi"),
        "institusi": env.get("NAMA_INSTITUSI", ""),
        "diperbarui": datetime.now(timezone.utc).astimezone().strftime("%d %B %Y"),
        "dosen": [
            {"nama": d["nama"], "slug": slug(d["nama"]),
             "sinta_id": id_saja(d.get("sinta_id")),
             "scopus_id": id_saja(d.get("scopus_id")),
             "orcid": id_saja(d.get("orcid")),
             **keahlian_publik(lembar.get("keahlian", {}).get(d["nama"])),
             **({"tugas_belajar": tugas_belajar(d)} if tugas_belajar(d) else {})}
            for d in dosen.to_dict("records")
            if tampil_publik(d)
        ],
        "publikasi": [
            {"judul": k["judul"], "tahun": k["tahun"], "tahun_ts": _ts(k),
             "dari_kegiatan": judul_induk.get(k.get("induk_id")),
             "jenis": k.get("jenis"),
             "terbitan": k.get("nama_terbitan"), "tingkat": k["tingkat"],
             # instal-lengkap.sql; None sebelum patch dijalankan.
             "volume": k.get("volume"), "nomor": k.get("nomor"), "halaman": k.get("halaman"),
             "indeksasi": k.get("indeksasi"), "doi": k.get("doi"), "url": url_publik(k.get("url")),
             "mitra": daftar_mitra(k["id"]),
             "mahasiswa": len(mhs_per_karya.get(k["id"], [])),
             "sdgs": sdgs_dari(k),
             "topik": topik_publik(k.get("topik")),
             "penulis": nama_penulis(k["id"])}
            for k in semua_verif if k["kategori"] == "publikasi"
        ],
        "kegiatan": [
            {"judul": k["judul"], "tahun": k["tahun"], "tahun_ts": _ts(k),
             "kategori": k["kategori"],
             "tingkat": k["tingkat"],
             "skema": nama_skema_publik(peta_skema.get(k.get("skema_kode"), {}).get("nama", "")),
             "kelompok": nama_kelompok.get(
                 peta_skema.get(k.get("skema_kode"), {}).get("kelompok"), ""),
             "mitra": daftar_mitra(k["id"]),
             "mahasiswa": len(mhs_per_karya.get(k["id"], [])),
             "penulis": nama_penulis(k["id"]),
             # Two fields below let the browser reproduce butir 23/25/31/32
             # exactly. The scores are computed from records where
             # relevan_visi is not False, while this list carries every
             # verified record - without the flag a per-butir breakdown
             # would list more items than the score's denominator.
             "relevan_visi": k.get("relevan_visi") is not False,
             "ember_dana": ember_dana(k),
             "sdgs": sdgs_dari(k)}
            for k in semua_verif if k["kategori"] in {"penelitian", "pkm"}
        ],
        **({"keahlian_baku": lembar["keahlian_baku"]} if lembar.get("keahlian_baku") else {}),
        "kurikulum": lembar.get("kurikulum", []),
        "ekuivalensi": lembar.get("ekuivalensi", []),
        "vmts": lembar.get("vmts", {}),
        "privasi": lembar.get("privasi", {}),
        "situs": lembar.get("situs", {}),
        # Aturan penyusunan jadwal kuliah (config.yaml schedule; pemilik 2026-11-22) untuk pemeriksaan bentrok di
        # jadwal-kuliah.html, sama dengan yang dipakai run_jadwal.py. Bukan data pribadi.
        "jadwal_aturan": lembar.get("jadwal_aturan", {}),
        # Prestasi mahasiswa terverifikasi untuk beranda dan prestasi.html (instal-lengkap.sql).
        "prestasi": lembar.get("prestasi_publik", []),
        # Kabar kegiatan terbit (instal-lengkap.sql) dan status akreditasi prodi (pemilik 2026-11-16).
        "kabar": lembar.get("kabar_publik", []),
        # Jadwal seminar/sidang TA (instal-lengkap.sql): tanpa NIM; nama hanya bila disetujui.
        "jadwal_ta": lembar.get("jadwal_ta_publik", []),
        # Tempat KP/magang dan ringkasan tracer alumni (pemilik 2026-11-17): agregat tanpa identitas.
        "tempat_kp": lembar.get("tempat_kp_publik", []),
        "alumni": lembar.get("alumni_publik", {}),
        "akreditasi_prodi": lembar.get("akreditasi_prodi", {}),
        # Kerja sama resmi untuk kerja-sama.html (instal-lengkap.sql), tanpa tautan bukti.
        "kerja_sama": lembar.get("kerja_sama_publik", []),
        # Profil prodi untuk profil-prodi.html (instal-lengkap.sql): sambutan, sejarah, pengelola.
        "profil": lembar.get("profil_publik", {}),
        # Testimoni alumni/mahasiswa yang sudah disetujui (patch 141).
        "testimoni": lembar.get("testimoni_publik", []),
        # Kalender akademik prodi (patch 148): yang tampil dan belum lewat lebih dari 60 hari.
        "kalender": lembar.get("kalender_publik", []),
        "prestasi_agregat": agg_prestasi,
        "prestasi_pembimbing": agg_pembimbing,
        "mahasiswa_agregat": agg_mahasiswa,
        "dtps": dtps_pub,
        "tracer": sorted(tracer_pub, key=lambda x: -x["tahun_lulus"]),
        # induk_id adalah UUID internal; yang keluar hanya judul kegiatannya.
        "luaran_dosen": sorted(
            [{**{k: v for k, v in l.items() if k != "induk_id"},
              "dari_kegiatan": judul_induk.get(l.get("induk_id"))}
             for l in luaran_pub], key=lambda x: -x["tahun"]),
        "rekognisi": sorted(rekognisi_pub, key=lambda x: -x["tahun"]),
        "integrasi": sorted(integrasi_pub, key=lambda x: -x["tahun"]),
        "akreditasi": akreditasi_pub,
        "mahasiswa_karya": {
            "publikasi": sorted(mhs_publikasi_pub, key=lambda x: -x["tahun"]),
            "luaran": sorted(mhs_luaran_pub, key=lambda x: -x["tahun"]),
        },
    }
    # Laboratorium (instal-lengkap.sql, pemilik 2026-11-16): alat dari LKPS 5.a, kepala dari NIDN,
    # penelitian terkait hanya dari karya penelitian/PkM yang terverifikasi.
    # Arsip judul tugas akhir (pemilik 2026-11-22): sidang akhir yang selesai, tanpa nama dan NIM mahasiswa; bidang dari
    # kolom bidang (patch 149) atau kelompok keahlian pembimbing pertama.
    publik["arsip_ta"] = arsip_ta_publik(lembar.get("jadwal_ta_baris") or [], lembar.get("dosen_per_nidn") or {}, publik["dosen"])
    publik["laboratorium"] = laboratorium_publik(
        lembar.get("laboratorium_baris") or [], lembar.get("prasarana_baris") or [], lembar.get("dosen_per_nidn") or {},
        publik["kurikulum"],
        {str(k["id"]): {"judul": k["judul"], "tahun": k["tahun"], "kategori": k["kategori"],
                        "skema": nama_skema_publik(peta_skema.get(k.get("skema_kode"), {}).get("nama", ""))}
         for k in semua_verif if k["kategori"] in {"penelitian", "pkm"}})
    # Foto dosen (pemilik 2026-11-16): unggahan dosen sendiri di Profil saya (instal-lengkap.sql,
    # disalin dari Drive sebelum data.json ditulis) didahulukan; selain itu berkas
    # site/foto-dosen/<slug>.(jpg|jpeg|webp|png) bila ada; tanpa keduanya, halaman menampilkan inisial.
    foto_profil = lembar.get("foto_profil") or {}
    for d in publik["dosen"]:
        for ext in ("webp", "jpg", "jpeg", "png"):
            if (AKAR / "site" / "foto-dosen" / f"{d['slug']}.{ext}").is_file():
                d["foto"] = f"foto-dosen/{d['slug']}.{ext}"
                break
        fid = drive_id(foto_profil.get(d["nama"]))
        if fid:
            d["_foto"] = [fid]
        # Kelompok keahlian (patch 86): hanya kode yang ada di config.yaml public_site.expertise_groups.
        kk = (lembar.get("kelompok_dosen") or {}).get(d["nama"])
        if kk in {x["kode"] for x in (lembar.get("situs") or {}).get("kelompok_keahlian", [])}:
            d["kelompok"] = kk
        nip = (lembar.get("nip_dosen") or {}).get(d["nama"])
        if nip:
            d["nip"] = nip
        tautan = (lembar.get("tautan_lain") or {}).get(d["nama"])
        if tautan:
            d["tautan"] = tautan
        ng = (lembar.get("nama_gelar") or {}).get(d["nama"])
        if ng and ng != d["nama"]:
            d["nama_gelar"] = ng
    publik["publikasi"].sort(key=lambda x: (-int(x["tahun"]), x["judul"]))
    publik["kegiatan"].sort(key=lambda x: (-int(x["tahun"]), x["judul"]))

    print("\n  Ringkasan")
    print(f"    Dosen aktif        : {len(publik['dosen'])}")
    print(f"    Publikasi verif.   : {len(publik['publikasi'])}")
    print(f"    Penelitian & PkM   : {len(publik['kegiatan'])}")
    # Evidence audit: no evidence link is published (owner 2026-11-04).
    _n_ada = sum(1 for k in semua_verif
                 if (k.get("bukti_url") or k.get("bukti_path") or ""))
    print(f"    Bukti ke data.json : 0 publik, {_n_ada} ditahan sebagai internal")
    print(f"    Prestasi mahasiswa : {len(prestasi)}")
    print(f"    Baris BKD          : {len(lembar['bkd'])}")
    print(f"    Luaran/rekognisi   : {len(luaran_pub)}/{len(rekognisi_pub)}, "
          f"integrasi {len(integrasi_pub)}, tracer {len(tracer_pub)} tahun")
    print(f"    Karya mhs mandiri  : {len(mhs_publikasi_pub)} publikasi, "
          f"{len(mhs_luaran_pub)} luaran")
    print(f"    Lembar mahasiswa_ta: {len(akr_ta)} tahun akademik")
    print(f"    Kurikulum publik   : " + (", ".join(
        f"{k['kode']} ({len(k['mk'])} MK, {len(k['cpl'])} CPL, {len(k['profil'])} profil)"
        for k in publik["kurikulum"]) or "kosong"))
    print(f"    Mitra tercatat     : {len(mitra)} baris "
          f"({len({(m.get('institusi') or '').strip().lower() for m in mitra})} institusi unik)")
    print(f"    Keterlibatan mhs   : {len(mahasiswa)} "
          f"({len({m['nim'] for m in mahasiswa})} mahasiswa unik)")

    # Catatan yang muncul saat menyusun agregat (kerja sama, kohort lulusan).
    # Galat di sini menghentikan penulisan, sama seperti galat validasi.
    if ctt.galat or ctt.ingat:
        if not ctt.laporkan():
            keluar("Perbaiki kesalahan di atas lebih dulu. Tidak ada berkas yang ditulis.")

    if hanya_periksa:
        print("\n  Mode periksa — tidak ada berkas yang ditulis.")
        return

    # penjaga terakhir: pastikan tidak ada data sensitif yang lolos
    try:
        teks = json.dumps(publik, ensure_ascii=False, allow_nan=False).lower()
    except ValueError:
        keluar("Keluaran memuat NaN — JSON tidak sah. Periksa isian angka di data-prodi.html.")
    nim_mhs = {str(m.get("nim", "")).strip().lower() for m in mahasiswa}
    nama_mhs = {str(m.get("nama", "")).strip().lower() for m in mahasiswa}
    for lb in ("publikasi_mahasiswa", "luaran_mahasiswa", "prestasi_mahasiswa"):
        df_ = lembar[lb] if lb in lembar else pd.DataFrame()
        for kol, kumpul in (("nim", nim_mhs), ("nama_mahasiswa", nama_mhs),
                            ("nama", nama_mhs)):
            if len(df_) and kol in df_.columns:
                for v in df_[kol]:
                    for bagian_v in str(v).replace(";", ",").split(","):
                        kumpul.add(bagian_v.strip().lower())
    # Nama yang disetujui mahasiswa untuk ditampilkan pada prestasinya (tampil_nama, pemilik
    # 2026-11-16) boleh ada di keluaran publik; nama lain dan semua NIM tetap dihentikan.
    # Jadwal TA (94): nama dan NIM di jadwal ikut dijaga; nama yang disetujui di jadwal publik boleh.
    for r in lembar.get("jadwal_ta_baris") or []:
        for kol, kumpul in (("nim", nim_mhs), ("nama_mahasiswa", nama_mhs)):
            for bagian_v in str(r.get(kol) or "").replace(";", ",").split(","):
                kumpul.add(bagian_v.strip().lower())
    boleh_nama = {n.strip().lower() for x in publik.get("prestasi", []) for n in x.get("mahasiswa") or []}
    boleh_nama |= {n.strip().lower() for x in publik.get("jadwal_ta", []) for n in x.get("mahasiswa") or []}
    for nilai in (nim_mhs | nama_mhs) - boleh_nama:
        if len(nilai) > 3 and nilai in teks:
            keluar(f"Keluaran publik memuat identitas mahasiswa ('{nilai}'). "
                   f"Dihentikan demi keamanan.")

    # Nama pimpinan bukan DTPS (mis. Dekan) tidak boleh ada di keluaran publik (pemilik 2026-11-21).
    for nilai in {n.strip().lower() for n in sembunyi}:
        if len(nilai) > 3 and nilai in teks:
            keluar(f"Keluaran publik memuat nama pimpinan yang tidak boleh tampil ('{nilai}'). "
                   f"Dihentikan demi keamanan.")

    for larangan in ("besaran_dana", "\"nim\"", "sks_"):
        if larangan in teks:
            keluar(f"Keluaran publik memuat '{larangan}'. Dihentikan demi keamanan.")

    situs = Path(env.get("SITUS_DIR", AKAR / "situs"))
    if not situs.is_absolute():
        situs = (AKAR / situs).resolve()
    situs.mkdir(parents=True, exist_ok=True)
    # Foto dokumentasi prestasi: disalin dari Drive sebelum data.json ditulis, supaya data.json
    # hanya menunjuk foto yang ada (pemilik 2026-11-16).
    hasil_foto = salin_foto_prestasi(situs, publik["prestasi"])
    foto_kabar = salin_foto(situs, publik["kabar"], "kabar")
    foto_dosen = salin_foto_dosen(situs, publik["dosen"])
    print(f"  Foto dosen (unggahan): {foto_dosen['dipakai']} dipakai, {foto_dosen['baru']} baru, {foto_dosen['gagal']} gagal diunduh")
    foto_lab = salin_foto(situs, publik["laboratorium"], "laboratorium")
    print(f"  Foto laboratorium: {foto_lab['dipakai']} dipakai, {foto_lab['baru']} baru, {foto_lab['gagal']} gagal diunduh")
    print(f"  Foto kabar: {foto_kabar['dipakai']} dipakai, {foto_kabar['baru']} baru, {foto_kabar['gagal']} gagal diunduh")
    print(f"  Foto prestasi: {hasil_foto['dipakai']} dipakai, {hasil_foto['baru']} baru, "
          f"{hasil_foto['gagal']} gagal diunduh, {hasil_foto['dibuang']} dibuang")
    (situs / "data.json").write_text(
        json.dumps(publik, ensure_ascii=False, indent=1, allow_nan=False),
        encoding="utf-8")
    print(f"\n  Ditulis: {situs / 'data.json'}")
    # Halaman statis untuk mesin pencari (pemilik 2026-11-16): dosen/<slug>.html, sitemap.xml, robots.txt.
    # Templat akreditasi (pemilik 2026-11-23): situs publik mati (config.js FITUR_MATI 'publik') = hanya ruang kerja,
    # tanpa halaman publik; robots.txt melarang pengindeksan.
    if "publik" in fitur_mati(AKAR / "site"):
        (situs / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
        print("  Situs publik dimatikan (config.js): tanpa halaman publik; robots.txt melarang pengindeksan")
    else:
        hasil = tulis_halaman_publik(situs, publik, lembar.get("_cfg") or {}, AKAR / "site")
        print(f"  Ditulis: {hasil['dosen']} halaman dosen di {situs / 'dosen'} (dibuang {hasil['dibuang']} lama)"
              + (f", sitemap.xml dan robots.txt" if hasil["sitemap"] else ", tanpa sitemap (public_site.base_url null)"))

    tulis_laporan_internal(env, lembar, semua_verif, peta_skema, nama_by_nidn,
                           nama_penulis, penulis, mhs_per_karya, mitra_per_karya)

    # ---------- arsip ----------
    DIR_ARSIP.mkdir(exist_ok=True)
    arsipkan(DIR_ARSIP / "prodi.sqlite", lembar, {
        "karya": karya, "karya_penulis": penulis, "ref_skema_dana": skema,
        "karya_mahasiswa": mahasiswa, "karya_mitra": mitra})


def arsipkan(db: Path, lembar: dict, tabel_lain: dict) -> None:
    """Every sheet (DataFrame) of `lembar` and the other tables -> SQLite archive.

    Entries of `lembar` that are not tables (e.g. lembar["keahlian"], a dict;
    owner 2026-11-11) are skipped: one such entry stopped the Actions build on
    2026-11-12. List/dict cells (karya.sdgs, karya.topik) are stored as JSON text,
    which SQLite can hold."""
    def simpan(df, nama, kon):
        """Melewati tabel kosong. pandas tidak bisa membuat tabel SQLite
        dari data tanpa kolom, dan itu terjadi bila seluruh baris dihapus."""
        if df is None or df.empty or not len(df.columns):
            print(f"    (lewati arsip '{nama}' — tidak ada baris)")
            return
        df = df.map(lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v)
        df.to_sql(nama, kon, if_exists="replace", index=False)

    with sqlite3.connect(db) as kon:
        for nama, df in lembar.items():
            if isinstance(df, pd.DataFrame):
                simpan(df, nama, kon)
        for nama, baris in tabel_lain.items():
            simpan(pd.DataFrame(baris), nama, kon)
    print(f"  Ditulis: {db}")


def sebut_penulis(daftar) -> list[str]:
    """Mengubah daftar objek penulis menjadi teks untuk laporan internal,
    lengkap dengan penanda peran. Objeknya sendiri dipakai apa adanya di
    data.json karena halaman web membutuhkan slug dan perannya terpisah."""
    hasil = []
    for a in daftar or []:
        tanda = []
        if a.get("peran") == "penulis_pertama":
            tanda.append("penulis pertama")
        elif a.get("peran") == "ketua":
            tanda.append("ketua")
        if a.get("korespondensi"):
            tanda.append("korespondensi")
        nama = a.get("nama", "")
        hasil.append(f"{nama} ({', '.join(tanda)})" if tanda else nama)
    return hasil


def tulis_laporan_internal(env, lembar, semua_verif, peta_skema, nama_by_nidn,
                           nama_penulis, penulis, mhs_per_karya,
                           mitra_per_karya) -> None:
    """Laporan lengkap berisi data sensitif. Tetap di repositori privat."""
    bkd = lembar["bkd"].copy()
    if len(bkd):
        for k in KOLOM_SKS:
            bkd[k] = pd.to_numeric(bkd[k], errors="coerce").fillna(0)
        bkd["total_sks"] = bkd[list(KOLOM_SKS)].sum(axis=1)
        bkd.insert(1, "nama", bkd["nidn"].map(nama_by_nidn))

    keg = [k for k in semua_verif if k["kategori"] in {"penelitian", "pkm"}]
    # Laporan internal sengaja memuat SEMUA karya terverifikasi, termasuk
    # yang di luar visi keilmuan — ini buku besar, bukan borang. Kolom
    # relevan_visi disertakan agar mudah dipilah saat menyalin ke LKPS.
    rinci = pd.DataFrame([{
        "tahun": k["tahun"], "jenis": k["kategori"], "judul": k["judul"],
        "relevan_visi": "ya" if k.get("relevan_visi") is not False else "TIDAK",
        "skema": peta_skema.get(k.get("skema_kode"), {}).get("nama", ""),
        "sumber_lkps": k.get("sumber_dana") or "",
        "pemberi_dana": k.get("nama_pemberi_dana") or "",
        "dana_rp": float(k.get("besaran_dana") or 0),
        "mitra": "; ".join(m["nama"] for m in mitra_per_karya.get(k["id"], [])),
        "negara": "; ".join(sorted({m["negara"] for m in
                                    mitra_per_karya.get(k["id"], []) if m["negara"]})),
        "bukti": k.get("bukti_url") or k.get("bukti_path") or "",
        "penulis": ", ".join(sebut_penulis(nama_penulis(k["id"]))),
    } for k in keg])

    per_skema = pd.DataFrame()
    if len(rinci):
        rinci = rinci.sort_values(["tahun", "jenis"], ascending=[False, True])
        per_skema = (rinci.groupby(["tahun", "jenis", "skema"])
                     .agg(jumlah=("judul", "count"), total_dana=("dana_rp", "sum"))
                     .reset_index().sort_values("tahun", ascending=False))

    # Rekap penulis utama: butir LKPS menghitung dosen yang menjadi penulis
    # pertama DAN/ATAU penulis korespondensi, jadi keduanya dijumlahkan
    # sebagai satu kategori "utama" tanpa menghitung ganda satu karya.
    id_pub = {k["id"] for k in semua_verif if k["kategori"] == "publikasi"}
    baris_utama = {}
    for p in penulis:
        if p["karya_id"] not in id_pub:
            continue
        pertama = p.get("peran") == "penulis_pertama"
        koresp = bool(p.get("korespondensi"))
        if not (pertama or koresp):
            continue
        r = baris_utama.setdefault(
            p["_nama"], {"nama": p["_nama"], "penulis_pertama": 0,
                         "korespondensi": 0, "utama": 0})
        r["penulis_pertama"] += int(pertama)
        r["korespondensi"] += int(koresp)
        r["utama"] += 1
    penulis_utama = pd.DataFrame(sorted(
        baris_utama.values(), key=lambda x: -x["utama"]))

    # Rincian keterlibatan mahasiswa. Hanya muncul di laporan internal;
    # nama dan NIM tidak pernah masuk keluaran publik.
    baris_mhs = []
    for k in semua_verif:
        for m in mhs_per_karya.get(k["id"], []):
            baris_mhs.append({
                "tahun": k["tahun"], "kategori": k["kategori"],
                "nim": m.get("nim", ""), "nama_mahasiswa": m.get("nama", ""),
                "peran": (m.get("peran") or "").replace("_", " "),
                "korespondensi": "ya" if m.get("korespondensi") else "",
                "judul": k["judul"],
            })
    mhs_tabel = pd.DataFrame(baris_mhs)
    if len(mhs_tabel):
        mhs_tabel = mhs_tabel.sort_values(["tahun", "nama_mahasiswa"],
                                          ascending=[False, True])

    total_dana = float(rinci["dana_rp"].sum()) if len(rinci) else 0.0

    def tabel(df: pd.DataFrame) -> str:
        if not len(df):
            return "<p class='kosong'>Belum ada data.</p>"
        return df.to_html(index=False, border=0, classes="t", na_rep="")

    html = f"""<!DOCTYPE html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Laporan internal — {env.get('NAMA_PRODI','Prodi')}</title>
<style>
 body{{font-family:'IBM Plex Sans',system-ui,sans-serif;max-width:1150px;margin:0 auto;
   padding:40px 24px 80px;color:#161E26;background:#EEF0ED;font-size:15px}}
 h1{{font-size:22px;font-weight:600;margin:0}}
 h2{{font-size:17px;font-weight:600;margin:36px 0 10px}}
 .rahasia{{background:#F7E7E7;border-left:3px solid #8C2F2F;padding:12px 16px;
   margin:18px 0;font-size:13.5px}}
 .meta{{color:#616C76;font-size:13px;margin-top:4px}}
 table.t{{width:100%;border-collapse:collapse;font-size:12.5px;background:#fff}}
 table.t th{{text-align:left;font-weight:500;font-size:10px;letter-spacing:.09em;
   text-transform:uppercase;color:#616C76;border-bottom:1px solid #D8DDD8;padding:7px 9px}}
 table.t td{{padding:7px 9px;border-bottom:1px solid #E8EBE7;vertical-align:top}}
 .kosong{{color:#616C76;font-size:13.5px}}
</style></head><body>
<h1>Laporan internal — {env.get('NAMA_PRODI','Prodi')}</h1>
<div class="meta">{env.get('NAMA_INSTITUSI','')} · dibangun {datetime.now().strftime('%d %B %Y %H:%M')}</div>
<div class="rahasia"><strong>Dokumen internal.</strong> Berisi beban kerja dosen,
nama dan NIM mahasiswa, serta nominal pendanaan. Jangan diunggah ke repositori
publik atau dikirim ke luar prodi.</div>

<h2>Beban kerja dosen</h2>
{tabel(bkd)}

<h2>Prestasi mahasiswa</h2>
{tabel(lembar['prestasi_mahasiswa'])}

<h2>Keterlibatan mahasiswa dalam karya dosen</h2>
<p>Dipakai untuk butir LKPS tentang keterlibatan mahasiswa dalam penelitian
dan PkM DTPS. Identitas mahasiswa hanya ada di dokumen ini.</p>
{tabel(mhs_tabel)}

<h2>Publikasi sebagai penulis pertama dan/atau korespondensi</h2>
<p>Dipakai untuk butir LKPS tentang persentase DTPS dengan karya sebagai
penulis pertama dan/atau penulis korespondensi.</p>
{tabel(penulis_utama)}

<h2>Rekap per skema pendanaan</h2>
{tabel(per_skema)}

<h2>Rincian penelitian dan PkM terverifikasi</h2>
<p>Total pendanaan: <strong>Rp {total_dana:,.0f}</strong> dari {len(rinci)} kegiatan.</p>
{tabel(rinci)}
</body></html>"""

    berkas = AKAR / "laporan-internal.html"
    berkas.write_text(html, encoding="utf-8")
    print(f"  Ditulis: {berkas}")


# =====================================================================
#  Data kuantitatif LKPS dari situs (tabel lkps_*, supabase/instal-lengkap.sql)
# =====================================================================
# Keputusan pemilik 2026-11-03: data kuantitatif diisi admin di
# data-prodi.html. Tabelnya memakai kolom yang sama dengan lembar Excel lama,
# jadi bangun() tidak berubah; sejak 2026-11-04 Excel tidak dibaca lagi.
# lembar -> (tabel, {kolom: jenis}); jenis 'int' | 'num' | 'teks'.
TABEL_LKPS = {
    "mahasiswa_ta": ("lkps_mahasiswa_ta", {
        "tahun_akademik": "teks", "jumlah_mahasiswa_aktif": "int", "jumlah_lulusan": "int",
        "rerata_ipk_lulusan": "num", "jumlah_mahasiswa_asing": "int",
        "rerata_masa_studi_tahun": "num", "persen_lulus_tepat_waktu": "num"}),
    "kohort_lulusan": ("lkps_kohort_lulusan", {
        "tahun_masuk": "int", "jumlah_masuk": "int", "lulus_3_5_sd_4_5": "int",
        "lulus_4_5_sd_5_5": "int", "lulus_5_5_sd_6_5": "int", "lulus_6_5_sd_8": "int"}),
    "tracer_lulusan": ("lkps_tracer_lulusan", {
        "tahun_lulus": "int", "jumlah_lulusan": "int", "jumlah_terlacak": "int",
        "rata_rata_waktu_tunggu_bulan": "num", "bekerja_sesuai_bidang": "int",
        "kerja_internasional": "int", "kerja_nasional": "int", "kerja_wilayah": "int",
        # Pita Tabel 6.f.1 Sarjana dan tingkat kesesuaian Tabel 6.f.2 (instal-lengkap.sql)
        "wt_kurang_3": "int", "wt_3_18": "int", "wt_lebih_18": "int",
        "kesesuaian_rendah": "int", "kesesuaian_sedang": "int", "kesesuaian_tinggi": "int"}),
    "kerjasama": ("lkps_kerjasama", {
        "id": "int", "mitra": "teks", "jenis": "teks", "tingkat": "teks", "kegiatan": "teks",
        "tahun_mulai": "int", "tahun_selesai": "int", "tautan_bukti": "teks"}),
    "bkd": ("lkps_bkd", {
        "nidn": "teks", "tahun_akademik": "teks", "semester": "teks", "status": "teks",
        "jabatan_akademik": "teks", "pendidikan_tertinggi": "teks",
        "sks_pendidikan": "num", "sks_ps_lain_dalam": "num", "sks_ps_lain_luar": "num",
        "sks_penelitian": "num", "sks_pkm": "num", "sks_penunjang": "num"}),
    "prestasi_mahasiswa": ("lkps_prestasi_mahasiswa", {
        "nama_mahasiswa": "teks", "nim": "teks", "nama_kegiatan": "teks", "penyelenggara": "teks",
        "bidang": "teks", "bulan": "int", "tingkat": "teks", "capaian": "teks", "tahun": "int",
        "pembimbing": "teks", "tautan_bukti": "teks"}),
    "publikasi_mahasiswa": ("lkps_publikasi_mahasiswa", {
        "tahun": "int", "judul": "teks", "nama_mahasiswa": "teks", "nim": "teks",
        "jenis": "teks", "tingkat": "teks", "indeksasi": "teks", "bulan": "int"}),
    "luaran_mahasiswa": ("lkps_luaran_mahasiswa", {
        "tahun": "int", "bulan": "int", "jenis": "teks", "judul": "teks",
        "nama_mahasiswa": "teks", "nim": "teks"}),
    # Butir 52 per TS (patch 21). Not 'kepuasan_pengguna', the name of the
    # retired Excel sheet that had no year.
    "kepuasan_ts": ("lkps_kepuasan_pengguna", {
        "tahun_akademik": "teks", "aspek": "teks", "sangat_baik": "num",
        "baik": "num", "cukup": "num", "kurang": "num"}),
}


def _teks_nilai(v) -> str:
    """Supabase value -> the string form the Excel sheets used ('' for null)."""
    if v is None:
        return ""
    if isinstance(v, list):
        return "; ".join(str(x).strip() for x in v)
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def pecah_pembimbing(v) -> list[str]:
    """NIDN list from a sheet cell ('a; b'), without blanks."""
    return [x.strip() for x in str(v or "").split(";") if x.strip()]


def agregat_pembimbing(prestasi: pd.DataFrame, nama_by_nidn: dict) -> list[dict]:
    """Achievements per supervisor: counts only, no student identity. A team
    with two supervisors counts once for each (owner 2026-11-06); butir 43
    still counts the achievement once."""
    baris = [{"nama": nama_by_nidn[n], "tahun": int(float(p["tahun"])), "tingkat": p["tingkat"]}
             for _, p in prestasi.iterrows()
             for n in dict.fromkeys(pecah_pembimbing(p.get("pembimbing")))
             if n in nama_by_nidn]
    if not baris:
        return []
    gp = pd.DataFrame(baris).groupby(["nama", "tahun", "tingkat"]).size().reset_index(name="jumlah")
    return [{"slug": slug(r["nama"]), "nama": r["nama"], "tahun": int(r["tahun"]),
             "tingkat": r["tingkat"], "jumlah": int(r["jumlah"])}
            for r in gp.sort_values("tahun", ascending=False).to_dict("records")]


def lembar_dari_supabase(sb: Supabase) -> dict:
    """Quantitative data from the lkps_* tables (data-prodi.html).

    Since 2026-11-04 (owner) the Excel file is no longer read at all. A table
    that does not exist yet (its patch not run) gives an empty sheet WITH its
    columns, so validasi() and bangun() can still read the expected columns.
    """
    lembar = {}
    for nama, (tabel, kolom) in TABEL_LKPS.items():
        rows = sb.ambil_opsional(tabel)
        if rows is None:
            print(f"  Catatan: tabel {tabel} belum ada (jalankan patch di supabase/); "
                  f"data '{nama}' kosong.")
            rows = []
        # Lecturer entries count once verified (patches 38, 39). In lkps_bkd
        # `status` means something else, so verification has its own column.
        if nama == "prestasi_mahasiswa":
            rows = [r for r in rows if r.get("status", "terverifikasi") == "terverifikasi"]
        if nama == "bkd":
            rows = [r for r in rows if r.get("verifikasi", "terverifikasi") == "terverifikasi"]
        lembar[nama] = pd.DataFrame([{k: _teks_nilai(r.get(k)) for k in kolom} for r in rows],
                                    columns=list(kolom))
    return lembar


# Roles that are never DTPS: assessors must be aktif=tidak. `pimpinan` (the
# dean) is NOT listed: the dean may or may not be DTPS of this prodi, so like
# any lecturer `aktif` decides (owner 2026-11-02). The role only grants reading.
PERAN_BUKAN_DTPS = {"asesor"}


YA = {"ya", "y", "true", "1"}


# Columns of the dosen roster, in the order the old Excel sheet used.
KOLOM_DOSEN = ("nidn", "nama", "email", "peran", "pendidikan", "jabatan",
               "sinta_id", "scopus_id", "orcid", "aktif", "dtps")


def dosen_dari_supabase(sb: Supabase) -> pd.DataFrame:
    """Dosen roster from the `dosen` table (kelola-dosen.html), sorted by name.

    The only source since Excel was retired (owner 2026-11-04). A missing
    patch-18 column or an empty table stops the build: publishing a site
    without its lecturers would be worse than not publishing.
    """
    rows = sb.ambil_opsional("dosen", ",".join(KOLOM_DOSEN))
    if rows is None:
        keluar("Kolom dosen.pendidikan/jabatan belum ada. Jalankan "
               "supabase/instal-lengkap.sql di Supabase.")
    if not rows:
        keluar("Tabel dosen kosong. Tambahkan dosen di kelola-dosen.html "
               "(admin pertama: lihat supabase/README.md).")

    def teks(r, k):
        v = r.get(k)
        if k in ("aktif", "dtps"):
            return "ya" if v else "tidak"
        return "" if v is None else str(v).strip()

    d = pd.DataFrame([{k: teks(r, k) for k in KOLOM_DOSEN} for r in rows], columns=list(KOLOM_DOSEN))
    return d.sort_values("nama", kind="stable").reset_index(drop=True)


def nama_skema_publik(nama: str | None) -> str:
    """Nama skema dana untuk situs publik (pemilik 2026-11-20): petunjuk isian formulir ("Lainnya — sebutkan di
    keterangan") tidak ikut terbit. Bagian setelah " — sebutkan" dibuang; sisa "Lainnya" saja = kosong. Keterangan karya
    tidak dipakai sebagai pengganti karena bisa memuat catatan internal."""
    teks = (nama or "").split(" — sebutkan")[0].split(" - sebutkan")[0].strip()
    return "" if teks.lower() in ("lainnya", "lain-lain", "lainnya:") else teks


def keahlian_publik(r: dict | None) -> dict:
    """Public expertise of one lecturer for data.json (owner 2026-11-11, patch 60):
    keywords (approved via the profile request) and the LKPS field of expertise.
    Empty dict when the patch has not run or nothing is filled, so the key is absent."""
    if not r:
        return {}
    out = {}
    kata = [str(k).strip() for k in (r.get("kata_kunci") or []) if str(k).strip()]
    if kata:
        out["kata_kunci"] = kata
    bidang = str(r.get("bidang_keahlian") or "").strip()
    if bidang:
        out["bidang_keahlian"] = bidang
    topik = [str(k).strip() for k in (r.get("topik_keahlian") or []) if str(k).strip()]
    if topik:
        out["topik_keahlian"] = topik
    return out


def keahlian_baku_publik(bidang: list[dict], topik: list[dict]) -> dict | None:
    """Active fields and topics of the standard expertise list for data.json (patch 61).
    sinonim/padanan ('; '-separated text) become lists. None when the tables are empty
    or absent, so data.json has no key until the patch has run."""
    pecah = lambda s: [x.strip() for x in str(s or "").split(";") if x.strip()]
    urut = lambda r: (int(r.get("urutan") or 100), str(r.get("kode")))
    b = [{"kode": r["kode"], "nama": r["nama"], "nama_en": r["nama_en"], "cakupan": r.get("cakupan") or ""}
         for r in sorted(bidang, key=urut) if r.get("aktif", True)]
    ada = {x["kode"] for x in b}
    t = [{"kode": r["kode"], "bidang": r["bidang"], "nama": r["nama"], "nama_en": r["nama_en"],
          "sinonim": pecah(r.get("sinonim")), "padanan": pecah(r.get("padanan"))}
         for r in sorted(topik, key=lambda r: (r.get("bidang") or "", *urut(r)))
         if r.get("aktif", True) and r.get("bidang") in ada]
    return {"bidang": b, "topik": t} if b and t else None


def _urut_baris(r: dict) -> tuple:
    return (int(r.get("urutan") or 100), str(r.get("kode") or ""))


def kurikulum_publik(mk: list[dict], cpl: list[dict], profil: list[dict],
                     peta: list[dict]) -> list[dict]:
    """Curricula for the public page kurikulum.html (owner 2026-11-16): graduate profiles
    (patch 79), CPL (patch 71) and courses per semester, newest curriculum first.

    Per curriculum, only active courses when any is active; a curriculum whose courses
    are all inactive (an old one, patch 70) shows all its courses, so older cohorts can
    still read theirs. Internal columns (pengampu, rps_url, sks_* breakdown names) stay
    out: the build's last guard refuses 'sks_' in public output."""
    def kur(r):
        return str(r.get("kurikulum") or "").strip().upper()
    nama = sorted({kur(r) for r in [*mk, *cpl, *profil]} - {""},
                  key=lambda k: -int(k[1:]) if k[1:].isdigit() else 0)
    cpl_mk: dict[tuple, list] = {}
    for p in peta:
        cpl_mk.setdefault((kur(p), str(p.get("kode_mk") or "").strip()), []).append(str(p.get("cpl") or ""))
    angka = lambda v: float(v) if v not in (None, "") else None
    out = []
    for k in nama:
        mk_k = [r for r in mk if kur(r) == k]
        if any(r.get("aktif", True) for r in mk_k):
            mk_k = [r for r in mk_k if r.get("aktif", True)]
        mk_k.sort(key=lambda r: (int(r.get("semester") or 99), *_urut_baris(r)))
        out.append({
            "kode": k,
            "profil": [{"kode": r["kode"], "nama": r["nama"], "nama_en": r.get("nama_en") or "",
                        "deskripsi": r.get("deskripsi") or "",
                        "cpl": [c.strip() for c in str(r.get("cpl") or "").split(",") if c.strip()]}
                       for r in sorted((r for r in profil if kur(r) == k), key=_urut_baris)],
            "cpl": [{"kode": r["kode"], "ranah": r.get("ranah") or "", "rumusan": r["rumusan"],
                     "rumusan_en": r.get("rumusan_en") or ""}
                    for r in sorted((r for r in cpl if kur(r) == k), key=_urut_baris)],
            "mk": [{"kode": r["kode"], "nama": r["nama"], "semester": r.get("semester"),
                    # Nama Inggris (patch 143) hanya bila terisi, untuk english.html.
                    **({"nama_en": str(r["nama_en"]).strip()} if str(r.get("nama_en") or "").strip() else {}),
                    # Peminatan MK pilihan (patch 145): kode kelompok keahlian atau peminatan lain, hanya bila terisi.
                    **({"peminatan": str(r["peminatan"]).strip()} if str(r.get("peminatan") or "").strip() else {}),
                    "sks": angka(r.get("sks")),
                    "bagian": {"kuliah": angka(r.get("sks_kuliah")), "seminar": angka(r.get("sks_seminar")),
                               "praktikum": angka(r.get("sks_praktikum"))},
                    "sifat": r.get("sifat") or "", "unit": r.get("unit_penyelenggara") or "",
                    "capstone": bool(r.get("capstone")),
                    "cpl": sorted(set(cpl_mk.get((k, str(r["kode"]).strip()), [])))}
                   for r in mk_k],
        })
    return [x for x in out if x["mk"] or x["cpl"] or x["profil"]]


def ekuivalensi_publik(rows: list[dict]) -> list[dict]:
    """Published course-equivalence tables for ekuivalensi-kurikulum.html (patch 134, owner 2026-11-21).

    Only the version approved by the Kaprodi and set by the Dekan (mk_padanan_sah.terbit) goes public;
    a draft never does. Allow-listed keys only, so columns added to the snapshot later stay internal.
    The Dekan's name never goes public, only the date (owner 2026-11-21). Newest target curriculum first."""
    mk = lambda xs: [{k: m.get(k) for k in ("kode", "nama", "sks", "semester", "sifat")} for m in xs or []]
    pejabat = lambda x: {"nama": (x or {}).get("nama") or "", "pada": (x or {}).get("pada") or ""}
    tanggal = lambda x: {"pada": (x or {}).get("pada") or ""}
    out = []
    for r in rows:
        t = r.get("terbit")
        if not isinstance(t, dict):
            continue
        out.append({
            "kurikulum_lama": t.get("kurikulum_lama") or r.get("kurikulum_lama"),
            "kurikulum_baru": t.get("kurikulum_baru") or r.get("kurikulum_baru"),
            "revisi": t.get("revisi") or r.get("revisi"),
            "disahkan": pejabat(t.get("disahkan")), "ditetapkan": tanggal(t.get("ditetapkan")),
            "mk_lama": mk(t.get("mk_lama")), "mk_baru": mk(t.get("mk_baru")),
            "padanan": [{k: p.get(k) for k in ("kode_lama", "kode_baru", "model", "tidak_berlanjut", "catatan")}
                        for p in t.get("padanan") or []],
        })
    return sorted(out, key=lambda x: str(x["kurikulum_baru"] or ""), reverse=True)


def vmts_publik(rows: list[dict]) -> dict:
    """Vision/mission statements (lkps_vmts, patch 27) for the public curriculum page:
    statement text only, per jenis (pt, upps, ps); SK numbers and links stay internal."""
    kolom = ("visi", "misi", "tujuan", "strategi")
    return {r["jenis"]: {k: r.get(k) or "" for k in kolom}
            for r in rows if r.get("jenis") and any(r.get(k) for k in kolom)}


def jadwal_aturan_publik(cfg: dict) -> dict:
    """config.yaml schedule (sudah divalidasi) -> aturan untuk halaman Jadwal kuliah; kosong bila bagian itu tidak ada."""
    s = cfg.get("schedule")
    if not isinstance(s, dict):
        return {}
    return {k: s.get(k) for k in ("minutes_per_sks", "same_label_break_minutes", "electives_no_overlap", "blocked", "avoid",
                                  "lecturer_daily_max_hours")}


def privasi_publik(cfg: dict) -> dict:
    """Facts for the public privacy page privasi.html (owner 2026-11-16), from config.yaml:
    contact address (public_site.privacy_contact_email) and the retention years of the
    personal-data tables (supabase.retention), so the page states what pruning does."""
    ret = (cfg.get("supabase") or {}).get("retention") or {}
    return {"kontak": (cfg.get("public_site") or {}).get("privacy_contact_email") or "",
            "masa_simpan": {t: r["years"] for t, r in ret.items()}}


def validasi_situs_publik(cfg: dict) -> list[str]:
    """Errors in config.yaml public_site, each naming its key. Empty = valid."""
    ps = cfg.get("public_site")
    if not isinstance(ps, dict):
        return ["public_site: bagian wajib ada di config.yaml"]
    galat = []
    email = lambda v: isinstance(v, str) and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v)
    https = lambda v: isinstance(v, str) and re.fullmatch(r"https://\S+", v)
    teks = lambda n: (lambda v: isinstance(v, str) and 0 < len(v.strip()) <= n)

    def cek(kunci, nilai, sah, arti):
        if nilai is not None and not sah(nilai):
            galat.append(f"public_site.{kunci}: harus {arti} atau null, didapat {nilai!r}")

    cek("privacy_contact_email", ps.get("privacy_contact_email"), email, "alamat email")
    cek("base_url", ps.get("base_url"), lambda v: https(v) and not v.endswith("/"), "URL https tanpa / di akhir")
    cek("tagline", ps.get("tagline"), teks(200), "teks 1-200 huruf")
    cek("tagline_en", ps.get("tagline_en"), teks(200), "teks 1-200 huruf")
    cek("programme_name_en", ps.get("programme_name_en"), teks(120), "teks 1-120 huruf")
    cek("degree", ps.get("degree"), teks(120), "teks 1-120 huruf")
    cek("admission_url", ps.get("admission_url"), https, "URL https")
    cek("admission_whatsapp", ps.get("admission_whatsapp"), https, "URL https")
    cek("news_url", ps.get("news_url"), https, "URL https")
    cek("academic_calendar_url", ps.get("academic_calendar_url"), https, "URL https")
    biaya = ps.get("costs_scholarships")
    if biaya is not None and not (isinstance(biaya, list) and all(
            isinstance(x, dict) and teks(120)(x.get("title")) and https(x.get("url"))
            and (x.get("note") is None or teks(300)(x.get("note"))) for x in biaya)):
        galat.append("public_site.costs_scholarships: harus daftar {title: teks 1-120 huruf, url: URL https, "
                     f"note: teks 1-300 huruf atau null}} atau null, didapat {biaya!r}")
    cek("accreditation_body", ps.get("accreditation_body"), teks(120), "teks 1-120 huruf")
    cek("alumni_min_respondents", ps.get("alumni_min_respondents"),
        lambda v: isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 100, "bilangan bulat 1-100")
    for kunci, n in (("careers", 120), ("laboratories", 120)):
        xs = ps.get(kunci)
        if xs is not None and not (isinstance(xs, list) and all(teks(n)(x) for x in xs)):
            galat.append(f"public_site.{kunci}: harus daftar teks 1-{n} huruf atau null, didapat {xs!r}")
    faq = ps.get("faq")
    if faq is not None and not (isinstance(faq, list) and all(isinstance(x, dict) and teks(200)(x.get("question"))
                                                             and teks(1500)(x.get("answer")) for x in faq)):
        galat.append("public_site.faq: harus daftar {question: teks 1-200 huruf, answer: teks 1-1500 huruf} atau null, "
                     f"didapat {faq!r}")
    kuis = ps.get("interest_quiz")
    if kuis is not None:
        kode_kk = {x.get("code") for x in ps.get("expertise_groups") or [] if isinstance(x, dict)}
        sah = isinstance(kuis, list) and all(
            isinstance(q, dict) and teks(200)(q.get("question")) and isinstance(q.get("options"), list)
            and 2 <= len(q["options"]) <= 8
            and all(isinstance(o, dict) and teks(160)(o.get("text")) and isinstance(o.get("groups"), list) and o["groups"]
                    and all(g in kode_kk for g in o["groups"]) for o in q["options"])
            for q in kuis)
        if not sah:
            galat.append("public_site.interest_quiz: harus daftar {question: teks 1-200, options: 2-8 x {text: teks 1-160, "
                         "groups: [kode di public_site.expertise_groups]}} atau null")
    cek("elective_rule", ps.get("elective_rule"), teks(300), "teks 1-300 huruf")
    lain = ps.get("elective_other_groups")
    if lain is not None:
        kode_kk = {x.get("code") for x in ps.get("expertise_groups") or [] if isinstance(x, dict)}
        sah = isinstance(lain, list) and all(
            isinstance(x, dict) and isinstance(x.get("code"), str) and re.fullmatch(r"[A-Z0-9]{2,12}", x["code"])
            and x["code"] not in kode_kk and teks(120)(x.get("name")) for x in lain)             and len({x["code"] for x in lain}) == len(lain)
        if not sah:
            galat.append("public_site.elective_other_groups: harus daftar {code: KODE (A-Z/0-9, 2-12, unik, bukan kode "
                         f"expertise_groups), name: teks 1-120 huruf}} atau null, didapat {lain!r}")
    tahap = ps.get("semester_stages")
    if tahap is not None:
        smt = [n for x in tahap if isinstance(x, dict) for n in (x.get("semesters") or [])] if isinstance(tahap, list) else []
        sah = isinstance(tahap, list) and all(
            isinstance(x, dict) and teks(60)(x.get("label")) and isinstance(x.get("semesters"), list) and x["semesters"]
            and all(type(n) is int and 1 <= n <= 14 for n in x["semesters"]) for x in tahap) and len(smt) == len(set(smt))
        if not sah:
            galat.append("public_site.semester_stages: harus daftar {semesters: [bilangan 1-14, tiap semester sekali], "
                         f"label: teks 1-60 huruf}} atau null, didapat {tahap!r}")
    kk = ps.get("expertise_groups")
    if kk is not None:
        sah = isinstance(kk, list) and all(isinstance(x, dict) and isinstance(x.get("code"), str)
                                           and re.fullmatch(r"[A-Z0-9]{2,12}", x["code"]) and teks(120)(x.get("name"))
                                           and (x.get("scope") is None or teks(200)(x.get("scope")))
                                           and (x.get("name_en") is None or teks(120)(x.get("name_en")))
                                           and (x.get("scope_en") is None or teks(200)(x.get("scope_en")))
                                           for x in kk)
        if not sah or len({x["code"] for x in kk}) != len(kk):
            galat.append("public_site.expertise_groups: harus daftar {code: KODE (A-Z/0-9, 2-12, unik), "
                         f"name: teks 1-120 huruf}} atau null, didapat {kk!r}")
    kontak = ps.get("contact") or {}
    if not isinstance(kontak, dict):
        galat.append("public_site.contact: harus pemetaan address/phone/email/hours")
        kontak = {}
    for k in ("address", "phone", "hours"):
        cek(f"contact.{k}", kontak.get(k), teks(300), "teks 1-300 huruf")
    cek("contact.email", kontak.get("email"), email, "alamat email")
    sosial = ps.get("social") or {}
    if not isinstance(sosial, dict):
        galat.append("public_site.social: harus pemetaan nama -> URL")
        sosial = {}
    for k, v in sosial.items():
        cek(f"social.{k}", v, https, "URL https")
    return galat


def situs_publik(cfg: dict) -> dict:
    """Homepage content from config.yaml public_site (owner 2026-11-16): only filled keys, so
    index.html shows a block only when its content exists."""
    ps = cfg.get("public_site") or {}
    isi = lambda d: {k: v.strip() for k, v in (d or {}).items() if isinstance(v, str) and v.strip()}
    daftar = lambda xs: [x.strip() for x in xs or [] if isinstance(x, str) and x.strip()]
    teks = lambda k: (ps.get(k) or "").strip()
    return {k: v for k, v in {
        "tagline": teks("tagline"), "kontak": isi(ps.get("contact")),
        "sosial": isi(ps.get("social")), "pendaftaran": teks("admission_url"),
        "konsultasi": teks("admission_whatsapp"), "berita": teks("news_url"),
        # Kalender akademik resmi universitas dan tautan biaya/beasiswa (pemilik 2026-11-22).
        "kalender_resmi": teks("academic_calendar_url"),
        "biaya": [{"judul": x["title"].strip(), "url": x["url"].strip(), **({"ket": x["note"].strip()} if x.get("note") else {})}
                  for x in ps.get("costs_scholarships") or [] if isinstance(x, dict) and x.get("title") and x.get("url")],
        "karier": daftar(ps.get("careers")),
        # Pertanyaan umum calon mahasiswa (pemilik 2026-11-20); hanya pasangan yang lengkap.
        "faq": [{"tanya": x["question"].strip(), "jawab": x["answer"].strip()} for x in ps.get("faq") or []
                if isinstance(x, dict) and str(x.get("question") or "").strip() and str(x.get("answer") or "").strip()],
        "laboratorium": daftar(ps.get("laboratories")),
        # Kuis minat calon mahasiswa (pemilik 2026-11-21): soal yang punya >= 2 pilihan lengkap.
        "kuis": [q for q in ({"tanya": str(x.get("question") or "").strip(),
                              "pilihan": [{"teks": str(o.get("text") or "").strip(), "kk": [str(g) for g in o.get("groups") or []]}
                                          for o in x.get("options") or [] if isinstance(o, dict) and str(o.get("text") or "").strip()]}
                             for x in ps.get("interest_quiz") or [] if isinstance(x, dict))
                 if q["tanya"] and len(q["pilihan"]) >= 2],
        # Aturan MK pilihan (pemilik 2026-11-22).
        "aturan_pilihan": teks("elective_rule"),
        # Peminatan MK pilihan di luar kelompok keahlian (pemilik 2026-11-22), mis. Sipil umum.
        "peminatan_lain": [{"kode": x["code"], "nama": str(x["name"]).strip()} for x in ps.get("elective_other_groups") or []
                           if isinstance(x, dict) and x.get("code") and str(x.get("name") or "").strip()],
        # Tahap belajar per semester (pemilik 2026-11-22): {nomor semester: label}.
        "tahap": {str(n): str(x["label"]).strip() for x in ps.get("semester_stages") or []
                  if isinstance(x, dict) and str(x.get("label") or "").strip() for n in x.get("semesters") or []},
        # Kelompok keahlian dosen, urutan tampil (instal-lengkap.sql, pemilik 2026-11-17).
        # berkas = halaman bidang (halaman_publik.berkas_bidang), dipakai pencarian situs (cari.js) tanpa menyalin aturannya.
        "kelompok_keahlian": [{"kode": x["code"], "nama": x["name"].strip(), "berkas": berkas_bidang(x["name"].strip()),
                               **{k2: str(x[k1]).strip() for k1, k2 in (("scope", "cakupan"), ("name_en", "nama_en"),
                                                                       ("scope_en", "cakupan_en")) if str(x.get(k1) or "").strip()}}
                              for x in ps.get("expertise_groups") or []],
        # Tagline, nama prodi, dan gelar untuk english.html (pemilik 2026-11-21).
        "tagline_en": teks("tagline_en"), "prodi_en": teks("programme_name_en"), "gelar": teks("degree"),
    }.items() if v}


def topik_publik(topik) -> list[dict]:
    """OpenAlex topics of a publication for data.json: topic and subfield only, at most 3
    (karya.topik, written by the admin's citation refresh; owner 2026-11-11)."""
    out = []
    for x in topik if isinstance(topik, list) else []:
        if isinstance(x, dict) and str(x.get("t") or "").strip():
            out.append({"t": str(x["t"]).strip(), **({"s": str(x["s"]).strip()} if x.get("s") else {})})
    return out[:3]


def masuk_dtps(d: dict) -> bool:
    """True if this `dosen` row counts as DTPS (divisor, public roster).

    Since 2026-11-03 (owner) the `dtps` column decides and `aktif` only
    grants login, so a non-DTPS admin or dean can still log in. Without a
    `dtps` value the old rule applies (aktif=ya). Never for roles in
    PERAN_BUKAN_DTPS."""
    peran = str(d.get("peran") or "dosen").strip().lower()
    if peran in PERAN_BUKAN_DTPS:
        return False
    # Tugas belajar berperiode (156, pemilik 2026-11-22): tb_ts = "ya"/"tidak" untuk TS berjalan (lihat main); "tidak" =
    # dosen homebase di luar masa tugas belajarnya = DTPS. Tanpa tb_ts: keterangan terisi = tugas belajar (perilaku lama).
    tb_ts = str(d.get("tb_ts") or "")
    if tb_ts == "ya" or (tb_ts != "tidak" and tugas_belajar(d)):
        return False
    if tb_ts == "tidak":
        return str(d.get("aktif", "ya")).strip().lower() in YA
    dtps = str(d.get("dtps") or "").strip().lower()
    if dtps:
        return dtps in YA
    return str(d.get("aktif", "ya")).strip().lower() in YA


def tugas_belajar(d: dict) -> str:
    """Study-leave note (instal-lengkap.sql, owner 2026-11-17), or '' when not on study leave."""
    v = d.get("tugas_belajar")
    return v.strip() if isinstance(v, str) and v.strip() else ""


def batas_ta(ta: str) -> tuple[str, str] | None:
    """'2026/2027' -> ('2026-09-01', '2027-08-31'), as batasTA() in site/dosen-hitung.js; None for another format."""
    m = re.fullmatch(r"(\d{4})/(\d{4})", str(ta or ""))
    return (f"{m[1]}-09-01", f"{m[2]}-08-31") if m else None


def sedang_tb(d: dict, ta: str | None = None, hari: str | None = None) -> bool:
    """On study leave in academic year ta (period overlaps it, owner 2026-11-22, patch 156) or, without ta, on day hari
    (ISO date). The note (tugas_belajar) marks a homebase lecturer on study leave; without a start date: always (the
    behaviour before patch 156). Same rule as sedangTB() in site/dosen-hitung.js."""
    if not tugas_belajar(d):
        return False
    mulai = str(d.get("tugas_belajar_mulai") or "")[:10]
    selesai = str(d.get("tugas_belajar_selesai") or "")[:10]
    if not mulai:
        return True
    b = batas_ta(ta) if ta else None
    kini = hari or datetime.now().date().isoformat()
    awal, akhir = b or (kini, kini)
    return mulai <= akhir and (not selesai or selesai >= awal)


def pimpinan_tersembunyi(d: dict) -> bool:
    """True for a leader (peran 'pimpinan', e.g. the Dekan) who is not on the public roster: the
    owner (2026-11-21) does not want such a name anywhere on the public site, also not as a
    co-author, supervisor or approver. A pimpinan who is also DTPS of this prodi stays public."""
    return str(d.get("peran") or "").strip().lower() == "pimpinan" and not tampil_publik(d)


def nama_tersembunyi(dosen: list[dict], nama_gelar: dict | None = None) -> set[str]:
    """Names (plain and with titles) of pimpinan_tersembunyi lecturers."""
    out = set()
    for d in dosen:
        if d.get("nama") and pimpinan_tersembunyi(d):
            out.add(str(d["nama"]).strip())
            if (nama_gelar or {}).get(d["nama"]):
                out.add(str(nama_gelar[d["nama"]]).strip())
    return out


def ta_berjalan(hari: date) -> str:
    """Academic year in progress, as skor.html tsBerjalan(): 1 September - 31 August, e.g. 2026-11-22 -> '2026/2027'."""
    ts = hari.year + 1 if hari.month >= 9 else hari.year
    return f"{ts - 1}/{ts}"


def nidn_mengampu(ta: str, kelas: list[dict], kelas_dosen: list[dict], manual: list[dict], dosen: list[dict]) -> dict:
    """Lecturers teaching a course of the prodi in academic year ta (owner 2026-11-22, patch 154): classes in Penyusunan
    kelas (both semesters, team teaching included) plus the admin's manual ticks (dosen_ampu_ts). diterapkan = False when
    there is no teaching data at all for ta, so the rule is not applied (safeguard: counts must not drop to zero only
    because the data has not been entered)."""
    ids = {k.get("id") for k in kelas if k.get("tahun_akademik") == ta}
    dari = {r.get("dosen_id") for r in kelas_dosen if r.get("kelas_id") in ids}
    dari |= {r.get("dosen_id") for r in manual if r.get("tahun_akademik") == ta}
    peta = {d.get("id"): str(d.get("nidn")).strip() for d in dosen if d.get("id") and d.get("nidn")}
    nidn = {peta[i] for i in dari if i in peta}
    return {"ta": ta, "diterapkan": bool(nidn), "nidn": nidn}


def ampu_ts_dari(sb, ta: str) -> dict:
    """nidn_mengampu from Supabase; tables that do not exist yet (patches 136/154) read as empty."""
    return nidn_mengampu(ta, sb.ambil_opsional("kelas_kuliah", "id,tahun_akademik") or [],
                         sb.ambil_opsional("kelas_dosen", "kelas_id,dosen_id") or [],
                         sb.ambil_opsional("dosen_ampu_ts", "dosen_id,tahun_akademik") or [],
                         sb.ambil_opsional("dosen", "id,nidn") or [])


def dosen_tetap_publik(rows: list[dict]) -> dict:
    """Public lecturer total (owner 2026-11-22): everyone on the public roster (tampil_publik), so permanent lecturers on
    study leave are included; the DTPS figures for accreditation stay separate (masuk_dtps)."""
    tetap = [d for d in rows if tampil_publik(d)]
    return {"dosen_tetap": len(tetap), "tugas_belajar": sum(1 for d in tetap if tugas_belajar(d))}


def tampil_publik(d: dict) -> bool:
    """True if this lecturer appears on the public site (roster, own page, links): DTPS, or an
    active lecturer on study leave who is not counted as DTPS (owner 2026-11-17). Accreditation
    counts keep using masuk_dtps."""
    if str(d.get("peran") or "dosen").strip().lower() in PERAN_BUKAN_DTPS:
        return False
    sedang = bool(tugas_belajar(d)) or str(d.get("tb_ts") or "") == "ya"
    return masuk_dtps(d) or (sedang and str(d.get("aktif", "ya")).strip().lower() in YA)


# Commands retired with the Excel file (owner 2026-11-03/04): each now only
# says where the data is entered, so an old habit cannot overwrite site data.
PENSIUN = {
    "template": "data-prodi.xlsx tidak dipakai lagi.",
    "sinkron_dosen": "Daftar dosen diisi admin di kelola-dosen.html.",
    "sinkron_pengaturan": "Nilai butir manual diisi di input-butir.html; kepuasan "
                          "pengguna (butir 52) di data-prodi.html, tab Kepuasan pengguna.",
    "tambah_lembar": "Isian butir diisi di input-butir.html.",
    "impor_lkps": "Data kuantitatif sudah di tabel lkps_* dan diisi di data-prodi.html.",
}


def lengkapi_beranda_terbit(situs: Path) -> None:
    """`--beranda`: index.html terbit dilengkapi tag pratinjau beralamat lengkap dan url + sameAs JSON-LD (pemilik
    2026-11-21). index.html tulisan tangan disalin dari site/ SESUDAH bangun.py, jadi langkah ini dijalankan sesudah
    salin (GitHub Actions, bangun-dan-push.bat). Alamat dari alamat_situs(): CNAME di folder situs menang atas
    config.yaml public_site.base_url, jadi ikut bila domain pindah. Tanpa kunci Supabase."""
    idx, dj = situs / "index.html", situs / "data.json"
    if not idx.is_file() or not dj.is_file():
        keluar(f"--beranda: {idx} atau {dj} tidak ada (jalankan bangun.py dan salin site/ dulu).")
    cfg = load_config(AKAR / "config.yaml")
    base = alamat_situs(situs, cfg)
    D = json.loads(dj.read_text(encoding="utf-8"))
    lama = idx.read_text(encoding="utf-8")
    baru = lengkapi_beranda(lama, D, base)
    if baru != lama:
        idx.write_text(baru, encoding="utf-8")
    print(f"  Beranda: pratinjau tautan dan JSON-LD {'dilengkapi' if baru != lama else 'tidak berubah'} ({base or 'tanpa alamat situs'})")


def main() -> None:
    p = argparse.ArgumentParser(description="Pengolah data kinerja prodi")
    for k in PENSIUN:
        p.add_argument("--" + k.replace("_", "-"), action="store_true",
                       help="(dipensiunkan 2026-11-04)")
    p.add_argument("--periksa", action="store_true", help="hanya validasi, tanpa menulis berkas")
    p.add_argument("--beranda", metavar="FOLDER_SITUS",
                   help="hanya melengkapi index.html terbit (pratinjau tautan, JSON-LD) dari data.json dan alamat situs; "
                        "dijalankan sesudah site/ disalin, tanpa kunci Supabase")
    a = p.parse_args()
    if a.beranda:
        lengkapi_beranda_terbit(Path(a.beranda))
        return

    for k, pesan in PENSIUN.items():
        if getattr(a, k):
            keluar(f"--{k.replace('_', '-')} dipensiunkan (2026-11-04). {pesan}")

    env = baca_env()
    # Pilihan situs publik (config.yaml public_site, pemilik 2026-11-16), divalidasi sebelum
    # membaca Supabase.
    cfg = load_config(AKAR / "config.yaml")
    galat_cfg = validasi_situs_publik(cfg)
    if cfg.get("schedule") is not None:   # aturan jadwal kuliah (run_jadwal.py), dipakai juga jadwal-kuliah.html
        galat_cfg += baca_aturan(cfg)[1]
    if galat_cfg:
        keluar("config.yaml tidak sah:\n  " + "\n  ".join(galat_cfg))
    print(f"  public_site.privacy_contact_email = {cfg['public_site'].get('privacy_contact_email')!r}")
    print(f"  public_site.alumni_min_respondents = {cfg['public_site'].get('alumni_min_respondents')!r}")
    sb = Supabase(env)
    lembar = lembar_dari_supabase(sb)
    # Halaman publik Kurikulum dan Kebijakan privasi (pemilik 2026-11-16). Opsional: tabel
    # yang belum ada (patch 71/79 belum dijalankan) memberi daftar kosong.
    lembar["kurikulum"] = kurikulum_publik(
        sb.ambil_opsional("ref_mata_kuliah") or [], sb.ambil_opsional("ref_cpl") or [],
        sb.ambil_opsional("ref_profil_lulusan") or [], sb.ambil_opsional("ref_mk_cpl") or [])
    # Halaman per mata kuliah kurikulum terbaru (pemilik 2026-11-22): berkas halaman + silabus yang DISAHKAN Kaprodi
    # (mk_silabus.sah, patch 129, opsional); draf dan catatan impor tidak dibaca.
    lengkapi_mk_terbaru(lembar["kurikulum"], sb.ambil_opsional("mk_silabus", "kurikulum,kode_mk,sah,sah_pada") or [])
    # Ekuivalensi MK yang sudah ditetapkan Dekan (patch 134, opsional; pemilik 2026-11-21).
    lembar["ekuivalensi"] = ekuivalensi_publik(
        sb.ambil_opsional("mk_padanan_sah", "kurikulum_lama,kurikulum_baru,revisi,terbit") or [])
    lembar["vmts"] = vmts_publik(sb.ambil_opsional("lkps_vmts", "jenis,visi,misi,tujuan,strategi") or [])
    lembar["privasi"] = privasi_publik(cfg)
    lembar["jadwal_aturan"] = jadwal_aturan_publik(cfg)
    lembar["situs"] = situs_publik(cfg)
    lembar["_cfg"] = cfg   # untuk halaman_publik setelah data.json ditulis (bukan tabel; arsipkan melewatinya)
    # Dosen dibaca sebelum prestasi: prestasi_publik memakai daftar dosen untuk pembimbing.
    lembar["dosen"] = dosen_dari_supabase(sb)
    # Dosen mengampu MK pada TS berjalan (154, pemilik 2026-11-22), untuk hitungan DTPS akreditasi.
    lembar["ampu_ts"] = ampu_ts_dari(sb, ta_berjalan(datetime.now().date()))
    print(f"  mengampu {lembar['ampu_ts']['ta']}: {len(lembar['ampu_ts']['nidn'])} dosen"
          + ("" if lembar["ampu_ts"]["diterapkan"] else " (belum ada data: aturan mengampu belum diterapkan)"))
    # Tugas belajar (patch 87, opsional): kueri terpisah supaya daftar dosen tetap terbaca sebelum patch. Periode (156,
    # pemilik 2026-11-22): keterangan publik hanya selama masa tugas belajar (hari ini); tb_ts = beririsan dengan TS
    # berjalan ("ya"/"tidak"), dipakai masuk_dtps. Tanpa kolom periode: keterangan terisi = tugas belajar (perilaku lama).
    tb = {r["nama"]: r for r in (sb.ambil_opsional("dosen", "nama,tugas_belajar,tugas_belajar_mulai,tugas_belajar_selesai")
                                 or sb.ambil_opsional("dosen", "nama,tugas_belajar") or [])
          if r.get("nama") and tugas_belajar(r)}
    if not lembar["dosen"].empty:
        ta_kini = ta_berjalan(datetime.now().date())
        lembar["dosen"]["tugas_belajar"] = lembar["dosen"]["nama"].map(
            lambda n: tugas_belajar(tb[n]) if n in tb and sedang_tb(tb[n]) else None)
        lembar["dosen"]["tb_ts"] = lembar["dosen"]["nama"].map(
            lambda n: ("ya" if sedang_tb(tb[n], ta_kini) else "tidak") if n in tb else None)
    # Prestasi mahasiswa untuk situs publik (pemilik 2026-11-16). Kolom patch 80 opsional: sebelum
    # patch dijalankan, prestasi tetap tampil tanpa nama dan cerita.
    kolom = "id,nama_mahasiswa,nama_kegiatan,penyelenggara,bidang,tingkat,capaian,tahun,bulan,pembimbing,status"
    baris_prestasi = (sb.ambil_opsional("lkps_prestasi_mahasiswa", kolom + ",tampil_nama,cerita,sembunyikan_publik")
                      or sb.ambil_opsional("lkps_prestasi_mahasiswa", kolom) or [])
    # Nama dengan gelar (patch 111, opsional; pemilik 2026-11-19): nama -> nama_gelar, hanya untuk tampilan publik.
    # Kunci tetap nama biasa (slug, penulis, pencarian).
    lembar["nama_gelar"] = {r["nama"]: str(r["nama_gelar"]).strip() for r in (sb.ambil_opsional("dosen", "nama,nama_gelar") or [])
                            if r.get("nama") and str(r.get("nama_gelar") or "").strip()}
    dosen_publik = [{"nidn": d.get("nidn"), "nama": lembar["nama_gelar"].get(d.get("nama")) or d.get("nama"),
                     "slug": slug(d["nama"]) if tampil_publik(d) else None}
                    for d in lembar["dosen"].to_dict("records") if d.get("nama") and not pimpinan_tersembunyi(d)]
    lembar["prestasi_publik"] = prestasi_publik(
        baris_prestasi, sb.ambil_opsional("lkps_bukti", "tabel,baris_id,jenis,url") or [], dosen_publik)
    # Tempat KP/magang (90/91/99) dan ringkasan tracer alumni (55) untuk kerja-sama.html dan alumni.html
    # (pemilik 2026-11-17): hanya agregat; NIM, nama, email, dan isian pribadi tidak keluar dari fungsi.
    lembar["tempat_kp_publik"] = tempat_kp_publik(
        sb.ambil_opsional("pengajuan_mahasiswa", "jenis,status,tahap,data,data_selesai,dibuat") or [])
    lembar["alumni_publik"] = alumni_ringkas(
        sb.ambil_opsional("survei", "id,kelompok,judul,pertanyaan,publik,dicabut,token,mulai,selesai,dibuat") or [],
        sb.ambil_opsional("survei_jawaban", "survei_id,jawaban") or [],
        cfg["public_site"].get("alumni_min_respondents"), datetime.now().date().isoformat())
    # Kabar kegiatan terbit (patch 81, opsional) dan status akreditasi prodi (Data prodi > Prodi di UPPS).
    # Laboratorium (patch 82, opsional) dan alat per prasarana (LKPS 5.a, patch 28); NIDN -> dosen untuk koordinator.
    # Bidang keahlian lab (patch 147, opsional): tanpa kolom itu dibaca seperti sebelumnya.
    kolom_lab = "id,nama,ringkasan,prasarana,kepala_nidn,mata_kuliah,layanan,kontak_layanan,foto,penelitian,urutan,tampil"
    lembar["laboratorium_baris"] = (sb.ambil_opsional("laboratorium", kolom_lab + ",bidang")
                                    or sb.ambil_opsional("laboratorium", kolom_lab) or [])
    lembar["prasarana_baris"] = sb.ambil_opsional("lkps_prasarana", "prasarana,alat,jumlah_dimiliki,urutan") or []
    lembar["dosen_per_nidn"] = {str(d["nidn"]).strip(): d for d in dosen_publik if d.get("nidn")}
    # Kerja sama resmi untuk situs publik (patch 83: sembunyikan_publik; patch 24: manfaat dan tanggal), opsional.
    kolom_ks = "id,mitra,jenis,tingkat,kegiatan,tahun_mulai,tahun_selesai"
    lembar["kerja_sama_publik"] = kerjasama_publik(
        sb.ambil_opsional("lkps_kerjasama", kolom_ks + ",manfaat,tanggal_mulai,tanggal_selesai,sembunyikan_publik")
        or sb.ambil_opsional("lkps_kerjasama", kolom_ks + ",manfaat,tanggal_mulai,tanggal_selesai")
        or sb.ambil_opsional("lkps_kerjasama", kolom_ks) or [],
        datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d"))
    # Profil prodi (patch 84, opsional): sambutan, sejarah, pengelola; NIDN -> dosen seperti koordinator lab.
    # Ketua Program Studi dan penanda tangan sambutan = Kaprodi yang berlaku hari ini (penugasan koordinator,
    # patch 97; pemilik 2026-11-21). Tanggal menurut WIB (UTC+7, tanpa musim): runner Actions berjalan dalam UTC.
    hari_wib = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d")
    nidn_per_id = {str(r["id"]): r.get("nidn") for r in (sb.ambil_opsional("dosen", "id,nidn") or []) if r.get("id")}
    penugasan = sb.ambil_opsional("koordinator", "jabatan,dosen_id,mulai,selesai") or []
    # Riwayat Kaprodi (pemilik 2026-11-22): id dosen -> nama bergelar; tautan hanya bila dosen punya halaman publik.
    # dosen_per_nidn menyimpan nama yang sudah bergelar (baris 2027), jadi slug dicari dengan nama yang ditampilkan.
    slug_publik = {d["nama"]: d.get("slug") for d in lembar["dosen_per_nidn"].values() if d.get("nama")}
    orang_per_id = {}
    for r in sb.ambil_opsional("dosen", "id,nama") or []:
        if r.get("id") and r.get("nama"):
            nm = (lembar.get("nama_gelar") or {}).get(r["nama"]) or r["nama"]
            orang_per_id[str(r["id"])] = {"nama": nm, **({"slug": slug_publik[nm]} if slug_publik.get(nm) else {})}
    lembar["profil_publik"] = profil_publik(
        sb.ambil_opsional("profil_prodi", "sejarah,sambutan,penyambut_nidn") or [],
        sb.ambil_opsional("pengelola_prodi", "id,jabatan,nidn,nama,urutan") or [], lembar["dosen_per_nidn"],
        kaprodi_aktif(penugasan, nidn_per_id, hari_wib), riwayat_kaprodi(penugasan, orang_per_id, hari_wib))
    # Testimoni (patch 141, opsional): hanya yang persetujuannya dicatat dan tampil; kolom persetujuan tidak ikut keluar.
    # Kalender akademik (patch 148, opsional; pemilik 2026-11-22), menurut tanggal WIB.
    lembar["kalender_publik"] = kalender_publik(sb.ambil_opsional(
        "kalender_akademik", "semester,kegiatan,kategori,mulai,selesai,catatan,tampil") or [], hari_wib)
    lembar["testimoni_publik"] = testimoni_publik(sb.ambil_opsional(
        "testimoni", "id,nama,peran,angkatan,tahun_lulus,pekerjaan,kutipan,persetujuan_tanggal,tampil,urutan") or [])
    # Foto profil dosen (patch 85, opsional): nama -> tautan Drive; kueri terpisah supaya daftar dosen tetap
    # terbaca sebelum patch dijalankan.
    lembar["foto_profil"] = {r["nama"]: r.get("foto_url") for r in (sb.ambil_opsional("dosen", "nama,foto_url") or [])
                             if r.get("nama") and r.get("foto_url")}
    # Kelompok keahlian dosen (patch 86, opsional): nama -> kode KK.
    lembar["kelompok_dosen"] = {r["nama"]: r.get("kelompok_keahlian") for r in (sb.ambil_opsional("dosen", "nama,kelompok_keahlian") or [])
                                if r.get("nama") and r.get("kelompok_keahlian")}
    # NIP dosen (patch 89, opsional, pemilik 2026-11-17): nama -> NIP, tampil di situs untuk mahasiswa.
    lembar["nip_dosen"] = {r["nama"]: str(r["nip"]).strip() for r in (sb.ambil_opsional("dosen", "nama,nip") or [])
                           if r.get("nama") and str(r.get("nip") or "").strip()}
    # Tautan lain di profil dosen (patch 146, opsional, pemilik 2026-11-22): nama -> [{label, url https}].
    lembar["tautan_lain"] = {r["nama"]: [{"label": str(t["label"]).strip()[:60], "url": str(t["url"]).strip()}
                                         for t in r["tautan_lain"] if isinstance(t, dict) and str(t.get("label") or "").strip()
                                         and re.fullmatch(r"https://\S{1,492}", str(t.get("url") or "").strip())][:5]
                             for r in (sb.ambil_opsional("dosen", "nama,tautan_lain") or [])
                             if r.get("nama") and isinstance(r.get("tautan_lain"), list)}
    lembar["kabar_publik"] = kabar_publik(
        sb.ambil_opsional("kabar_kegiatan", "id,judul,tanggal,jenis,tempat,ringkasan,tautan,foto,status,tampil_publik")
        or sb.ambil_opsional("kabar_kegiatan", "id,judul,tanggal,jenis,tempat,ringkasan,tautan,foto,status") or [])
    # Jadwal seminar/sidang TA (94, opsional, pemilik 2026-11-17); baris mentah ikut penjaga identitas mahasiswa.
    # hasil: arsip judul TA hanya yang tidak "mengulang"; bidang (patch 149, opsional): bidang keahlian TA.
    kolom_ta = ("id,tahap,nama_mahasiswa,nim,judul,pembimbing,penguji,tanggal,jam,ruang,tautan_daring,status,"
                "tampil_nama,sembunyikan_publik,hasil")
    lembar["jadwal_ta_baris"] = (sb.ambil_opsional("jadwal_ta", kolom_ta + ",bidang")
                                 or sb.ambil_opsional("jadwal_ta", kolom_ta) or [])
    lembar["jadwal_ta_publik"] = jadwal_ta_publik(lembar["jadwal_ta_baris"], lembar["dosen_per_nidn"],
                                                  datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d"))
    lembar["akreditasi_prodi"] = akreditasi_publik(
        sb.ambil_opsional("lkps_prodi_upps", "diakreditasi,status_akreditasi,nomor_sk,tanggal_sk,tanggal_kedaluwarsa") or [],
        datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d"),
        (cfg.get("public_site") or {}).get("accreditation_body") or "")
    # Peta keahlian (instal-lengkap.sql, owner 2026-11-11): public keywords and
    # field of expertise per lecturer. Optional so the build runs before the patch.
    lembar["keahlian"] = {r["nama"]: r for r in (sb.ambil_opsional(
        "dosen", "nama,kata_kunci,bidang_keahlian") or [])}
    # Daftar keahlian baku (instal-lengkap.sql, owner 2026-11-12): topics chosen
    # by each lecturer, and the active fields/topics. Separate optional reads, so the
    # keywords above still arrive before patch 61 has run.
    for r in sb.ambil_opsional("dosen", "nama,topik_keahlian") or []:
        lembar["keahlian"].setdefault(r["nama"], {})["topik_keahlian"] = r.get("topik_keahlian")
    lembar["keahlian_baku"] = keahlian_baku_publik(
        sb.ambil_opsional("ref_bidang_keahlian") or [], sb.ambil_opsional("ref_topik_keahlian") or [])

    print("  Mengambil data dari Supabase…")
    karya = sb.ambil("karya")
    skema = sb.ambil("ref_skema_dana")
    kelompok = sb.ambil("ref_kelompok_dana")
    penulis = [{
        "karya_id": x["karya_id"], "dosen_id": x["dosen_id"], "peran": x["peran"],
        "korespondensi": bool(x.get("korespondensi")),
        "ditambahkan_sendiri": x.get("ditambahkan_sendiri"),
        "_nama": (x.get("dosen") or {}).get("nama", ""),
    } for x in sb.ambil(
        "karya_penulis", "karya_id,dosen_id,peran,korespondensi,ditambahkan_sendiri,dosen(nama)")]

    mahasiswa = sb.ambil("karya_mahasiswa",
                         "karya_id,nim,nama,peran,korespondensi")
    mitra = sb.ambil("karya_mitra", "karya_id,institusi,negara,tingkat")

    ctt = Catatan()
    validasi(lembar, karya, penulis, skema, mitra, ctt)
    if not ctt.laporkan():
        keluar("Perbaiki kesalahan di atas lebih dulu. Tidak ada berkas yang ditulis.")

    # Catatan terpisah: peringatan validasi di atas sudah dicetak.
    bangun(env, lembar, karya, penulis, skema, kelompok, mahasiswa, mitra,
           Catatan(), a.periksa)

    if not a.periksa:
        print("\n  Selesai. Langkah berikutnya:")
        print("    cd ../prodi-situs")
        print("    grep -ci 'nim\\|sks_\\|besaran_dana' data.json     # harus 0")
        print("    git add -A && git commit -m 'Perbarui data' && git push\n")


if __name__ == "__main__":
    main()
