"""Aturan payung kerja sama untuk skor butir 6 (bangun.baris_kerjasama_karya).

Kasus bersama dengan tests/js/kerjasama_karya.test.mjs, sehingga tabel LKPS
2.a (site/kerjasama-karya.js) dan skor tidak bisa menyimpang (pemilik 2026-11-10).
"""
import json
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AKAR))
import bangun  # noqa: E402

KASUS = json.loads((AKAR / "tests" / "data" / "kerjasama_karya.json").read_text(encoding="utf-8"))


def _hitung():
    # Bentuk data seperti di bangun.bangun: nama mitra dirapikan, yang kosong dibuang.
    mitra_per_karya = {
        k["id"]: [{"nama": m["institusi"].strip(), "tingkat": m["tingkat"]}
                  for m in k.get("karya_mitra", []) if m["institusi"].strip()]
        for k in KASUS["karya"]}
    mitra_induk = {bangun.kunci_id(r["id"]): r["mitra"].strip().lower() for r in KASUS["kerjasama"]}
    return bangun.baris_kerjasama_karya(KASUS["karya"], mitra_per_karya, mitra_induk)


def test_same_rows_as_the_lkps_table():
    dapat = sorted([ts, kat, nama.lower()] for ts, _tg, kat, nama in _hitung())
    assert dapat == sorted(h[:3] for h in KASUS["harapan"])


def test_mou_partner_left_to_the_kerjasama_sheet():
    nama = [n.lower() for _ts, _tg, _k, n in _hitung()]
    assert "mitra mou" not in nama and "pemda contoh" not in nama


def test_kunci_id_reads_pandas_floats():
    assert bangun.kunci_id(1.0) == "1" and bangun.kunci_id("2") == "2"
    assert bangun.kunci_id(float("nan")) == "" and bangun.kunci_id(None) == ""
