"""Unduh berkas nilai CPL dari Drive prodi lewat Apps Script (pemilik 2026-11-11, pilihan 2).

Dosen mengunggah berkas lewat situs (site/nilai-cpl.html) ke Drive privat
(berkas-privat/cpl/<TA semester>/<MK-kelas>/). run_cpl.py dengan source: site
mengunduh berkas terbaru tiap kelas ke paths.input_dir/_dari_situs, lalu
menghitung seperti biasa.

URL Apps Script dibaca dari site/config.js (window.UPLOAD_URL), satu sumber
dengan situs. Kunci CPL_KUNCI dibaca dari env atau rahasia.env di akar repo;
nilainya sama dengan Script Property CPL_KUNCI di Apps Script. Kunci tidak
pernah ditulis ke log.
"""
import base64
import json
import os
import re
import shutil
import urllib.request
from pathlib import Path

KUNCI_ENV = "CPL_KUNCI"
SUBFOLDER = "_dari_situs"


def baca_url(repo_root):
    """window.UPLOAD_URL dari site/config.js; galat bila kosong."""
    teks = (Path(repo_root) / "site" / "config.js").read_text(encoding="utf-8")
    for u in re.findall(r"window\.UPLOAD_URL\s*=\s*'([^']*)'", teks):
        if u.strip():
            return u.strip()
    raise ValueError("UPLOAD_URL di site/config.js kosong: Apps Script belum disiapkan.")


def baca_kunci(repo_root):
    """CPL_KUNCI dari env, bila kosong dari rahasia.env (baris CPL_KUNCI=...)."""
    kunci = os.environ.get(KUNCI_ENV, "").strip()
    path = Path(repo_root) / "rahasia.env"
    if not kunci and path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(KUNCI_ENV + "="):
                kunci = line.split("=", 1)[1].strip().strip('"').strip("'")
    if len(kunci) < 32:
        raise ValueError(f"{KUNCI_ENV} belum diisi (minimal 32 karakter) di env atau rahasia.env; "
                         "nilainya sama dengan Script Property CPL_KUNCI di Apps Script.")
    return kunci


def _post(url, isi, timeout=180):
    """POST JSON ke Apps Script (pengalihan 302 diikuti urllib sebagai GET, seperti curl -L)."""
    req = urllib.request.Request(url, data=json.dumps(isi).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "text/plain;charset=utf-8"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.loads(r.read().decode("utf-8"))
    if not out.get("ok"):
        raise RuntimeError(f"Apps Script: {out.get('error') or 'gagal'}")
    return out


def _aman(s):
    s = re.sub(r"[^\w.\- ]+", "_", str(s or "")).strip(" .")
    return s or "_"


def unduh_semua(url, kunci, tujuan, post=None):
    """Unduh berkas terbaru tiap kelas ke tujuan (dikosongkan dulu). Kembalikan daftar path."""
    post = post or _post
    tujuan = Path(tujuan)
    if tujuan.name != SUBFOLDER:
        raise ValueError(f"Folder unduhan harus bernama {SUBFOLDER}; tidak menghapus {tujuan}.")
    daftar = post(url, {"kind": "cpl_unduh", "kunci": kunci, "aksi": "daftar"}).get("berkas") or []
    if tujuan.exists():
        shutil.rmtree(tujuan)
    hasil = []
    for b in daftar:
        a = post(url, {"kind": "cpl_unduh", "kunci": kunci, "aksi": "ambil", "id": b["id"]})
        path = tujuan / _aman(b.get("semester")) / _aman(b.get("kelas")) / _aman(a.get("nama") or b.get("nama"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(a["data"]))
        hasil.append(path)
    return hasil
