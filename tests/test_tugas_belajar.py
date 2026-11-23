"""Dosen tugas belajar (instal-lengkap.sql, pemilik 2026-11-17): tampil di situs, tidak dihitung DTPS."""
import math

import pytest

import bangun as b


@pytest.mark.parametrize("d, dtps, tampil", [
    ({"dtps": "ya", "aktif": "ya"}, True, True),
    ({"dtps": "tidak", "aktif": "ya"}, False, False),
    ({"dtps": "tidak", "aktif": "ya", "tugas_belajar": "S3, Kyoto University"}, False, True),
    ({"dtps": "ya", "aktif": "ya", "tugas_belajar": "S3"}, False, True),        # pengaman bila dtps masih ya
    ({"dtps": "tidak", "aktif": "tidak", "tugas_belajar": "S3"}, False, False),
    ({"dtps": "tidak", "aktif": "ya", "tugas_belajar": math.nan}, False, False),  # kolom kosong dari pandas
    ({"dtps": "tidak", "aktif": "ya", "peran": "asesor", "tugas_belajar": "S3"}, False, False),
])
def test_study_leave_is_public_but_never_dtps(d, dtps, tampil):
    assert b.masuk_dtps(d) is dtps and b.tampil_publik(d) is tampil


def test_tugas_belajar_note_is_trimmed_text_or_empty():
    assert b.tugas_belajar({"tugas_belajar": "  S3, ITB "}) == "S3, ITB"
    assert b.tugas_belajar({"tugas_belajar": None}) == b.tugas_belajar({}) == ""


def test_public_lecturer_total_includes_study_leave_dtps_does_not():
    """Beranda dan halaman publik: dosen tetap termasuk yang tugas belajar (pemilik 2026-11-22); DTPS tetap tanpa mereka."""
    rows = [{"dtps": "ya", "aktif": "ya"}] * 10 + [{"dtps": "tidak", "aktif": "ya", "tugas_belajar": "S3, Kyoto University"},
                                                   {"dtps": "tidak", "aktif": "ya"}, {"dtps": "ya", "aktif": "ya", "peran": "asesor"}]
    assert b.dosen_tetap_publik(rows) == {"dosen_tetap": 11, "tugas_belajar": 1}
    assert sum(b.masuk_dtps(d) for d in rows) == 10


# 156 (pemilik 2026-11-22): periode tugas belajar, sama dengan sedangTB() di site/dosen-hitung.js.
def test_study_leave_period_overlaps_academic_year():
    d = {"tugas_belajar": "S3, Kyoto", "tugas_belajar_mulai": "2024-02-01", "tugas_belajar_selesai": "2027-02-15"}
    assert b.batas_ta("2026/2027") == ("2026-09-01", "2027-08-31") and b.batas_ta("2026") is None
    assert [b.sedang_tb(d, ta) for ta in ("2022/2023", "2023/2024", "2024/2025", "2026/2027", "2027/2028")] == \
        [False, True, True, True, False]
    assert b.sedang_tb(d, hari="2027-03-01") is False and b.sedang_tb(d, hari="2027-02-15") is True
    assert b.sedang_tb({**d, "tugas_belajar_selesai": None}, "2030/2031") is True
    assert b.sedang_tb({"tugas_belajar": "S3"}, "2010/2011") is True          # tanpa tanggal = perilaku lama
    assert b.sedang_tb({"tugas_belajar": None, "tugas_belajar_mulai": "2024-01-01"}, "2024/2025") is False


def test_homebase_back_from_study_leave_counts_as_dtps():
    """tb_ts "tidak" (di luar masa tugas belajar pada TS berjalan) = DTPS walau kolom dtps masih false (aturan patch 87)."""
    kembali = {"dtps": "tidak", "aktif": "ya", "tugas_belajar": "S3", "tb_ts": "tidak"}
    pergi = {"dtps": "tidak", "aktif": "ya", "tugas_belajar": "S3", "tb_ts": "ya"}
    assert b.masuk_dtps(kembali) is True and b.tampil_publik(kembali) is True
    assert b.masuk_dtps(pergi) is False and b.tampil_publik(pergi) is True
    assert b.masuk_dtps({**kembali, "aktif": "tidak"}) is False
    assert b.masuk_dtps({**kembali, "peran": "asesor"}) is False
