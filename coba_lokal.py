#!/usr/bin/env python3
"""Coba situs di komputer sendiri, tanpa Supabase, GitHub, atau Google (pemilik 2026-11-12).

    python coba_lokal.py                     # paket sesuai site/config.js
    python coba_lokal.py --paket akreditasi  # coba paket akreditasi
    python coba_lokal.py --port 8800         # bila port bawaan sudah dipakai

Yang dilakukan:
  1. menyalin site/ ke folder coba-lokal/situs (folder ini diabaikan git);
  2. membuat data fiktif "Contoh" (coba/seed.py) dan menjalankan bangun.py yang asli
     terhadap server REST tiruan, sehingga data.json dibangun persis seperti di GitHub;
  3. mengganti Supabase di halaman dengan tiruan (coba/mock-sb.js): login, isian, dan
     verifikasi berjalan, tetapi semua perubahan hanya tersimpan di peramban ini;
  4. membuka http://localhost:<port>/ruang-kerja.html. Bilah MODE COBA di bawah
     halaman untuk berganti peran (admin, dosen, tamu) dan mengembalikan data contoh.
Tekan Ctrl+C di jendela ini untuk berhenti.

Port: config.yaml, bagian coba_lokal. Tidak menyentuh site/, Supabase, atau GitHub.
Butuh Python dengan pyyaml, requests, numpy, openpyxl (sama dengan bangun.py).
"""
from __future__ import annotations

import argparse
import functools
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DI_SINI = Path(__file__).resolve().parent
# Di repo templat berkas ini ada di akar; di repo sumber (cv-data) di tools/.
AKAR = next(p for p in (DI_SINI, DI_SINI.parent) if (p / "bangun.py").exists())
COBA = DI_SINI / "coba"
KELUAR = AKAR / "coba-lokal"
# Versi dikunci di halaman sejak 2026-11-16 (mis. @2.119.0); pola menerima @2 maupun versi lengkap.
CDN = re.compile(r"https://cdn\.jsdelivr\.net/npm/@supabase/supabase-js@2(?:\.\d+\.\d+)?/\+esm")
# Paket situs: diambil dari install.py (satu sumber; site/fitur.js dibandingkan dengannya di tests/test_install.py).
_spek = importlib.util.spec_from_file_location("install_paket", Path(__file__).with_name("install.py"))
_install = importlib.util.module_from_spec(_spek)
_spek.loader.exec_module(_install)
PAKET = _install.PAKET
# Nama contoh bila install.py belum dijalankan (nama prodi tidak memengaruhi isi).
NAMA_CONTOH = {"nama_prodi": "Teknik Contoh", "nama_institusi": "Universitas Contoh"}


def baca_config(path: Path) -> dict:
    """Bagian coba_lokal dari config.yaml, divalidasi sebelum apa pun dikerjakan."""
    import yaml
    if not path.exists():
        sys.exit(f"config.yaml tidak ditemukan di {path.parent}")
    cfg = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("coba_lokal")
    if not isinstance(cfg, dict):
        sys.exit("config.yaml: bagian coba_lokal belum ada (lihat contoh di config.yaml repo templat).")
    port = cfg.get("port")
    if not isinstance(port, int) or not 1024 <= port <= 65535:
        sys.exit(f"config.yaml coba_lokal.port: harus bilangan bulat 1024-65535, tertulis {port!r}")
    return {"port": port}


def muat_seed():
    spec = importlib.util.spec_from_file_location("seed_coba", COBA / "seed.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def rest_tiruan(data: dict) -> ThreadingHTTPServer:
    """Server REST minimal untuk bangun.py: GET /rest/v1/<tabel> mengembalikan semua barisnya."""
    class Rest(BaseHTTPRequestHandler):
        def do_GET(self):
            tabel = self.path.split("/rest/v1/")[-1].split("?")[0]
            rows = data.get(tabel, [])
            if not isinstance(rows, list):
                rows = []
            if tabel == "karya_penulis":   # bangun.py meminta dosen(nama)
                nama = {d["id"]: d["nama"] for d in data["dosen"]}
                rows = [dict(x, dosen={"nama": nama.get(x["dosen_id"])}) for x in rows]
            body = json.dumps(rows).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Range", f"0-{max(len(rows) - 1, 0)}/{len(rows)}")
            self.end_headers()
            self.wfile.write(body)
        do_HEAD = do_GET

        def do_POST(self):   # RPC yang tidak ditiru: kosong
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"[]")

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Rest)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


ABAIKAN_SALIN = (".git", "node_modules", "paket", "coba-lokal", "arsip", "pulih", "cadangan", "__pycache__", ".pytest_cache",
                 "*.env", ".env*", ".cdsapirc", "*.xlsx", "*.sqlite", "laporan-internal.html", "pasang-tercatat.json")


def salin_sumber(akar: Path, tujuan: Path) -> Path:
    """Salinan repo untuk bangun.py tanpa rahasia, arsip, data Excel, dan .git. Berhenti bila rahasia ikut tersalin."""
    shutil.copytree(akar, tujuan, ignore=shutil.ignore_patterns(*ABAIKAN_SALIN))
    rahasia = [str(p.relative_to(tujuan)) for p in tujuan.rglob("*")
               if p.suffix == ".env" or p.name.startswith(".env") or p.name == ".cdsapirc"]
    if rahasia:
        sys.exit(f"Berhenti: berkas rahasia ikut tersalin ke {tujuan} ({', '.join(rahasia)}).")
    return tujuan


def bangun(paket: str | None, keluar: Path = KELUAR, luring: bool = False) -> Path:
    """Build the sample site in <keluar>/situs with the real bangun.py and return that folder.
    luring=True (tests/test_bangun_utuh.py): every internet request fails at once through a dead
    proxy, so the build never waits on Drive photos; the fake REST server on 127.0.0.1 is exempt."""
    sql = AKAR / "supabase" / "instal-lengkap.sql"
    if keluar.exists():
        shutil.rmtree(keluar)
    if not sql.exists():
        # Repo sumber (cv-data): skema lengkap disusun dari patch NN-*.sql (supabase_archive.full_schema,
        # perlu npm install --prefix tools), pemilik 2026-11-12 untuk uji asap.
        try:
            sys.path.insert(0, str(AKAR))
            from supabase_archive import full_schema
            keluar.mkdir(parents=True)
            sql = keluar / "instal-lengkap.sql"
            sql.write_bytes(full_schema(AKAR))
        except Exception as e:
            sys.exit(f"supabase/instal-lengkap.sql tidak ada dan skema tidak bisa disusun dari patch ({e}).\n"
                     "Di repo templat berkas itu ada; di repo sumber jalankan dulu: npm install --prefix tools")
    situs = keluar / "situs"
    shutil.copytree(AKAR / "site", situs)

    data = muat_seed().buat(sql)
    data["_versi"] = str(time.time_ns())   # data peramban lama diganti bila situs coba dibangun ulang
    (situs / "seed.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    tercatat = AKAR / "pasang-tercatat.json"
    nama = json.loads(tercatat.read_text(encoding="utf-8")) if tercatat.exists() else NAMA_CONTOH
    srv = rest_tiruan(data)
    env = dict(os.environ, GITHUB_ACTIONS="true", SUPABASE_URL=f"http://127.0.0.1:{srv.server_address[1]}",
               SUPABASE_SERVICE_KEY="kunci-contoh", SITUS_DIR=str(situs), PYTHONIOENCODING="utf-8",
               NAMA_PRODI=nama.get("nama_prodi") or NAMA_CONTOH["nama_prodi"],
               NAMA_INSTITUSI=nama.get("nama_institusi") or NAMA_CONTOH["nama_institusi"])
    if luring:
        env.update(HTTP_PROXY="http://127.0.0.1:9", HTTPS_PROXY="http://127.0.0.1:9",
                   NO_PROXY="127.0.0.1,localhost")
    # bangun.py dijalankan di SALINAN repo tanpa berkas rahasia (2026-11-12): bila dijalankan di repo,
    # bangun.py membaca rahasia.env (Supabase sungguhan) dan menulis arsip/, laporan internal, dan
    # data.json ke tempat sungguhan. Salinan: coba-lokal/sumber, tanpa .git, arsip, data Excel, *.env.
    sumber = salin_sumber(AKAR, keluar / "sumber")
    print("Membangun data.json dengan bangun.py (salinan repo, Supabase tiruan) ...")
    r = subprocess.run([sys.executable, str(sumber / "bangun.py")], cwd=sumber, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, timeout=300)
    srv.shutdown()
    if r.returncode or not (situs / "data.json").exists():
        print((r.stdout + r.stderr)[-3000:])
        sys.exit(f"bangun.py gagal (kode {r.returncode}); pesan di atas.")

    # Halaman memakai Supabase tiruan, tidak pernah proyek sungguhan.
    shutil.copy(COBA / "mock-sb.js", situs / "mock-sb.js")
    for f in situs.iterdir():
        if f.suffix in (".html", ".js") and f.name != "mock-sb.js":
            t = f.read_text(encoding="utf-8")
            if CDN.search(t):
                f.write_text(CDN.sub("./mock-sb.js", t), encoding="utf-8", newline="")
    tambahan = ("\n/* coba_lokal.py: kunci contoh; unggah berkas ditiru di mock-sb.js */\n"
                "window.SB_URL = 'https://contoh.supabase.co'; window.SB_KEY = 'sb_publishable_contoh';\n"
                "window.UPLOAD_URL = 'https://script.google.com/macros/s/contoh/exec';\n")
    if paket:
        tambahan += "window.FITUR_MATI = [" + ", ".join(f"'{k}'" for k in PAKET[paket]) + "];\n"
    cfg = situs / "config.js"
    cfg.write_text(cfg.read_text(encoding="utf-8") + tambahan, encoding="utf-8", newline="")
    return situs


def sajikan(situs: Path, port: int, buka: bool) -> None:
    class TanpaCache(SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def log_message(self, *a):
            pass

    try:
        srv = ThreadingHTTPServer(("127.0.0.1", port), functools.partial(TanpaCache, directory=str(situs)))
    except OSError:
        sys.exit(f"Port {port} sedang dipakai program lain. Tutup program itu, atau jalankan: python coba_lokal.py --port {port + 1}")
    alamat = f"http://localhost:{port}/ruang-kerja.html"
    print(f"\nSitus coba berjalan di {alamat}")
    print("Bilah MODE COBA di bawah halaman: ganti peran (Admin, Dosen, Tamu) dan Atur ulang data.")
    print("Tekan Ctrl+C di jendela ini untuk berhenti.\n")
    if buka:
        webbrowser.open(alamat)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("Berhenti.")
    finally:
        srv.server_close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Coba situs di komputer sendiri dengan data contoh")
    ap.add_argument("--paket", choices=sorted(PAKET), help="timpa paket di site/config.js untuk percobaan ini")
    ap.add_argument("--port", type=int, help="timpa coba_lokal.port di config.yaml untuk percobaan ini")
    ap.add_argument("--tanpa-buka", action="store_true", help="jangan membuka peramban otomatis")
    a = ap.parse_args()
    try:   # pesan langsung tampil, juga bila keluaran dialihkan
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    cfg = baca_config(AKAR / "config.yaml")
    port = a.port or cfg["port"]
    if not 1024 <= port <= 65535:
        sys.exit(f"--port: harus 1024-65535, tertulis {port}")
    print(f"Folder repo : {AKAR}")
    print(f"Port        : {port}" + (" (dari --port)" if a.port else " (config.yaml coba_lokal.port)"))
    print(f"Paket       : {a.paket or 'sesuai site/config.js'}")
    situs = bangun(a.paket)
    sajikan(situs, port, not a.tanpa_buka)


if __name__ == "__main__":
    main()
