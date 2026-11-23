"""Dosen dihitung untuk akreditasi hanya bila mengampu MK pada TS (instal-lengkap.sql, pemilik 2026-11-22)."""
from datetime import date

import bangun as b


def test_academic_year_in_progress_matches_skor_page():
    assert b.ta_berjalan(date(2026, 11, 22)) == "2026/2027"
    assert b.ta_berjalan(date(2027, 8, 31)) == "2026/2027"
    assert b.ta_berjalan(date(2027, 9, 1)) == "2027/2028"


def test_teaching_nidn_from_classes_and_manual_ticks_with_safeguard():
    kelas = [{"id": 1, "tahun_akademik": "2026/2027"}, {"id": 2, "tahun_akademik": "2025/2026"}]
    kd = [{"kelas_id": 1, "dosen_id": "a"}, {"kelas_id": 2, "dosen_id": "b"}]
    manual = [{"dosen_id": "c", "tahun_akademik": "2026/2027"}]
    dosen = [{"id": "a", "nidn": "0011"}, {"id": "b", "nidn": "0012"}, {"id": "c", "nidn": "0013"}]
    r = b.nidn_mengampu("2026/2027", kelas, kd, manual, dosen)
    assert r == {"ta": "2026/2027", "diterapkan": True, "nidn": {"0011", "0013"}}
    kosong = b.nidn_mengampu("2027/2028", kelas, kd, manual, dosen)
    assert kosong["diterapkan"] is False and kosong["nidn"] == set()   # tanpa data: aturan tidak diterapkan
