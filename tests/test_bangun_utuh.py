"""Uji build utuh (pemilik 2026-11-16): bangun.py yang asli dijalankan sampai selesai.

Build 6fa027e lolos semua uji per fungsi, tetapi bangun.py berhenti di main() (KeyError 'dosen')
dan situs tidak terbit berjam-jam. Uji ini menjalankan tools/coba_lokal.py bangun(): salinan repo
tanpa rahasia, Supabase tiruan berisi data fiktif, tanpa internet (luring), di folder sementara.
Butuh node + tools/node_modules (npm install --prefix tools); dilewati bila tidak ada.
"""
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

AKAR = Path(__file__).resolve().parents[1]
SKRIP = AKAR / "tools" / "coba_lokal.py"

pytestmark = pytest.mark.skipif(
    not (SKRIP.exists() and shutil.which("node") and (AKAR / "tools" / "node_modules").is_dir()),
    reason="butuh tools/coba_lokal.py, node, dan: npm install --prefix tools")


@pytest.fixture(scope="module")
def situs(tmp_path_factory):
    spec = importlib.util.spec_from_file_location("coba_lokal_uji", SKRIP)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    try:
        return m.bangun(None, keluar=tmp_path_factory.mktemp("bangun-utuh"), luring=True)
    except SystemExit as e:   # coba_lokal mencetak 3000 huruf terakhir keluaran bangun.py sebelum berhenti
        pytest.fail(str(e))


def test_build_writes_data_json_with_public_keys(situs):
    d = json.loads((situs / "data.json").read_text(encoding="utf-8"))
    for k in ("prodi", "dosen", "situs", "prestasi", "kabar", "akreditasi_prodi", "laboratorium", "kerja_sama", "profil"):
        assert k in d, f"data.json tanpa kunci {k}"
    assert d["dosen"], "data.json tanpa dosen"


def test_build_writes_public_pages(situs):
    for f in ("index.html", "prestasi.html", "kabar.html", "laboratorium.html", "kerja-sama.html", "alumni.html", "profil-prodi.html", "peta-situs.html", "sitemap.xml", "robots.txt"):
        assert (situs / f).is_file(), f"{f} tidak terbentuk"
    assert list((situs / "dosen").glob("*.html")), "halaman dosen/<slug>.html tidak terbentuk"
