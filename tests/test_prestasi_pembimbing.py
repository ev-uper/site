"""Supervisors and verification status of student achievements (patch 38)."""
import pandas as pd

import bangun


class SbPalsu:
    def __init__(self, tabel):
        self.tabel = tabel

    def ambil_opsional(self, tabel, pilih="*"):
        return self.tabel.get(tabel, [])


def baris(**k):
    return {"nama_kegiatan": "Lomba", "tahun": 2026, "tingkat": "nasional", "bidang": "akademik",
            "status": "terverifikasi", "pembimbing": ["1"], **k}


def test_only_verified_rows_count():
    lembar = bangun.lembar_dari_supabase(SbPalsu({"lkps_prestasi_mahasiswa": [
        baris(nama_kegiatan="A"), baris(nama_kegiatan="B", status="diajukan"),
        baris(nama_kegiatan="C", status="ditolak")]}))
    assert list(lembar["prestasi_mahasiswa"]["nama_kegiatan"]) == ["A"]


def test_status_filter_leaves_bkd_alone():
    lembar = bangun.lembar_dari_supabase(SbPalsu({"lkps_bkd": [
        {"nidn": "1", "tahun_akademik": "2025/2026", "semester": "ganjil", "status": "dtps"}]}))
    assert len(lembar["bkd"]) == 1


def test_rows_before_patch_38_still_count():
    r = baris()
    del r["status"]
    assert len(bangun.lembar_dari_supabase(SbPalsu({"lkps_prestasi_mahasiswa": [r]}))["prestasi_mahasiswa"]) == 1


def test_supervisor_list_becomes_cell_and_back():
    assert bangun._teks_nilai(["1", "2"]) == "1; 2"
    assert bangun._teks_nilai([]) == ""
    assert bangun.pecah_pembimbing("1; 2;") == ["1", "2"]
    assert bangun.pecah_pembimbing("") == []
    assert bangun.pecah_pembimbing(None) == []


def test_team_counts_once_for_each_supervisor():
    df = pd.DataFrame([{"tahun": "2026", "tingkat": "nasional", "pembimbing": "1; 2"},
                       {"tahun": "2026", "tingkat": "nasional", "pembimbing": "1"},
                       {"tahun": "2025", "tingkat": "nasional", "pembimbing": "9"},
                       {"tahun": "2025", "tingkat": "nasional", "pembimbing": ""}])
    hasil = bangun.agregat_pembimbing(df, {"1": "Adi", "2": "Budi"})
    assert {(r["nama"], r["jumlah"]) for r in hasil} == {("Adi", 2), ("Budi", 1)}
    assert all(set(r) == {"slug", "nama", "tahun", "tingkat", "jumlah"} for r in hasil)


def test_no_supervisors_gives_empty_list():
    assert bangun.agregat_pembimbing(pd.DataFrame(columns=["tahun", "tingkat", "pembimbing"]), {}) == []


def test_only_verified_bkd_rows_count():
    b = {"nidn": "1", "tahun_akademik": "2025/2026", "status": "dtps", "sks_ps_lain_dalam": 2.5}
    lembar = bangun.lembar_dari_supabase(SbPalsu({"lkps_bkd": [
        {**b, "semester": "ganjil", "verifikasi": "terverifikasi"},
        {**b, "semester": "genap", "verifikasi": "diajukan"}]}))
    assert list(lembar["bkd"]["semester"]) == ["ganjil"]
    assert list(lembar["bkd"]["sks_ps_lain_dalam"]) == ["2.5"]
