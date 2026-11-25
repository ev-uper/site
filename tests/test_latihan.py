"""Mode latihan pengajuan mahasiswa (pemilik 2026-11-24, sosialisasi): site/latihan/ berisi tiruan yang identik dengan
mode coba dan data yang sepenuhnya fiktif; pengajuan.html hanya memakai tiruan bila ?latihan ada."""
import csv
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LATIHAN = ROOT / "site" / "latihan"


def test_mock_salinan_identik_dengan_mode_coba():
    # Repo sumber: tools/coba/mock-sb.js; paket templat (tools/make_package.py): coba/mock-sb.js di akar repo.
    sumber = next(p for p in (ROOT / "tools" / "coba" / "mock-sb.js", ROOT / "coba" / "mock-sb.js") if p.exists())
    assert (LATIHAN / "mock-sb.js").read_bytes() == sumber.read_bytes(), "Jalankan: python tools/buat_latihan.py"


def test_seed_fiktif_tanpa_data_asli():
    teks = (LATIHAN / "seed.json").read_text(encoding="utf-8")
    data = json.loads(teks)
    assert data["_versi"].startswith("latihan-")
    assert "universitaspertamina" not in teks.lower()
    cfg = (ROOT / "site" / "config.js").read_text(encoding="utf-8")
    sb = re.search(r"https://[a-z0-9]+\.supabase\.co", cfg)
    assert not sb or sb.group(0) not in teks
    daftar = ROOT / "cadangan" / "dosen.csv"
    if not daftar.exists():
        pytest.skip("cadangan/dosen.csv tidak ada (repo templat)")
    nama = {r["nama"].strip() for r in csv.DictReader(daftar.open(encoding="utf-8")) if len(r.get("nama", "").split()) >= 2}
    bocor = sorted(n for n in nama if n.lower() in teks.lower())
    assert not bocor, f"nama dosen asli di seed latihan: {bocor}"


def test_pengajuan_memakai_tiruan_hanya_dalam_mode_latihan():
    html = (ROOT / "site" / "pengajuan.html").read_text(encoding="utf-8")
    assert "LATIHAN ? await import('./latihan/mock-sb.js" in html
    assert "@supabase/supabase-js@" in html                    # tanpa ?latihan tetap Supabase sungguhan
    assert not re.search(r"^import \{ createClient \}", html, re.M), "createClient harus dimuat bersyarat"
    assert "window.UPLOAD_URL = 'https://script.google.com/macros/s/latihan/exec'" in html
