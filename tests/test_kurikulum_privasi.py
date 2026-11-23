"""Halaman publik Kurikulum dan Kebijakan privasi di data.json (bangun.py, pemilik 2026-11-16, patch 79)."""
import json

import bangun
from cpl.config import load_config

MK = [
    {"kurikulum": "K26", "kode": "SI201", "nama": "Mekanika", "semester": 2, "sks": 3, "sks_kuliah": 2,
     "sks_praktikum": 1, "aktif": True, "sifat": "wajib", "pengampu": ["0011"], "rps_url": "https://drive/x"},
    {"kurikulum": "K26", "kode": "SI101", "nama": "Kalkulus", "semester": 1, "sks": 3, "aktif": True, "urutan": 5},
    {"kurikulum": "K26", "kode": "SI999", "nama": "Dihapus", "semester": 1, "sks": 2, "aktif": False},
    {"kurikulum": "K21", "kode": "41101", "nama": "Kalkulus 1", "semester": 1, "sks": 3, "aktif": False},
    {"kurikulum": "K21", "kode": "41201", "nama": "Statika", "semester": 2, "sks": 3, "aktif": False},
]
CPL = [{"kurikulum": "K26", "kode": "B", "rumusan": "Merancang", "urutan": 2},
       {"kurikulum": "K26", "kode": "A", "rumusan": "Menerapkan", "urutan": 1},
       {"kurikulum": "K21", "kode": "a", "rumusan": "lama"}]
PROFIL = [{"kurikulum": "K26", "kode": "PL1", "nama": "Perencana", "cpl": "A, B", "deskripsi": "d"}]
PETA = [{"kurikulum": "K26", "kode_mk": "SI201", "cpl": "B"}, {"kurikulum": "K26", "kode_mk": "SI201", "cpl": "A"}]


def test_kurikulum_newest_first_active_courses_only():
    k = bangun.kurikulum_publik(MK, CPL, PROFIL, PETA)
    assert [x["kode"] for x in k] == ["K26", "K21"]
    k26, k21 = k
    assert [m["kode"] for m in k26["mk"]] == ["SI101", "SI201"]        # SI999 nonaktif, urut semester
    assert [c["kode"] for c in k26["cpl"]] == ["A", "B"]
    assert k26["profil"][0]["cpl"] == ["A", "B"]
    assert k26["mk"][1]["cpl"] == ["A", "B"] and k26["mk"][1]["bagian"]["praktikum"] == 1.0
    # K21: semua MK nonaktif (kurikulum lama, patch 70) -> semua tampil.
    assert [m["kode"] for m in k21["mk"]] == ["41101", "41201"] and k21["profil"] == []


def test_kurikulum_keeps_internal_columns_out():
    teks = json.dumps(bangun.kurikulum_publik(MK, CPL, PROFIL, PETA)).lower()
    for larangan in ("sks_", "pengampu", "rps_url", "drive", "0011"):
        assert larangan not in teks


def test_kurikulum_empty_without_tables():
    assert bangun.kurikulum_publik([], [], [], []) == []


def test_vmts_statements_only():
    v = bangun.vmts_publik([{"jenis": "ps", "visi": "Unggul", "nomor_sk": "SK/1", "tautan": "https://x"},
                            {"jenis": "pt", "visi": None, "misi": None}])
    assert v == {"ps": {"visi": "Unggul", "misi": "", "tujuan": "", "strategi": ""}}


def test_privasi_from_config():
    cfg = load_config(bangun.AKAR / "config.yaml")
    assert bangun.validasi_situs_publik(cfg) == []
    p = bangun.privasi_publik(cfg)
    assert p["masa_simpan"]["masukan_mahasiswa"] == 5 and p["masa_simpan"]["karya_mahasiswa"] == 8
    assert p["kontak"] == (cfg["public_site"]["privacy_contact_email"] or "")


def test_validasi_situs_publik_names_key():
    assert bangun.validasi_situs_publik({}) == ["public_site: bagian wajib ada di config.yaml"]
    galat = bangun.validasi_situs_publik({"public_site": {"privacy_contact_email": "bukan email"}})
    assert galat and "public_site.privacy_contact_email" in galat[0]
    assert bangun.validasi_situs_publik({"public_site": {"privacy_contact_email": "prodi@contoh.ac.id"}}) == []
