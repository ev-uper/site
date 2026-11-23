"""Jadwal seminar/sidang TA di situs publik (instal-lengkap.sql, pemilik 2026-11-17; halaman_publik.jadwal_ta_publik)."""
import halaman_publik as hp

DOSEN = {"001": {"nama": "Ani", "slug": "ani"}, "002": {"nama": "Budi"}}
BARIS = [
    {"id": 1, "tahap": "sidang_akhir", "nama_mahasiswa": "Cici", "nim": "104123001", "judul": "Banjir", "pembimbing": ["001"],
     "penguji": ["002", "999"], "tanggal": "2030-01-10", "jam": "09.00", "ruang": "R1", "status": "terjadwal", "tampil_nama": True},
    {"id": 2, "tahap": "seminar_proposal", "nama_mahasiswa": "Dodi", "nim": "104123002", "judul": "Jalan", "pembimbing": ["002"],
     "penguji": [], "tanggal": "2030-01-05", "status": "terjadwal", "tampil_nama": False, "tautan_daring": "https://meet/x"},
    {"id": 3, "tahap": "seminar_kemajuan", "nama_mahasiswa": "Eka", "judul": "Batal", "tanggal": "2030-01-06", "status": "batal"},
    {"id": 4, "tahap": "seminar_kemajuan", "nama_mahasiswa": "Fani", "judul": "Sembunyi", "tanggal": "2030-01-06",
     "status": "terjadwal", "sembunyikan_publik": True},
    {"id": 5, "tahap": "seminar_kemajuan", "nama_mahasiswa": "Gina", "judul": "Lama", "tanggal": "2029-11-01", "status": "selesai"},
    {"id": 6, "tahap": "seminar_kemajuan", "nama_mahasiswa": "Hadi", "judul": "Jauh", "tanggal": "2030-09-01", "status": "terjadwal"},
]


def test_window_order_and_hidden_rows():
    xs = hp.jadwal_ta_publik(BARIS, DOSEN, "2030-01-01")
    assert [x["id"] for x in xs] == [2, 1]          # batal, disembunyikan, lewat > 14 hari, > 90 hari ke depan: tidak ikut


def test_no_nim_and_name_only_with_consent():
    a, b = hp.jadwal_ta_publik(BARIS, DOSEN, "2030-01-01")
    assert "nim" not in a and "nim" not in b
    assert a["mahasiswa"] == [] and b["mahasiswa"] == ["Cici"]
    assert b["pembimbing"] == [{"nama": "Ani", "slug": "ani"}] and b["penguji"] == [{"nama": "Budi"}]   # NIDN tak dikenal dilewati
    assert a["daring"] is True and "meet" not in str(a)                                              # tautan daring tidak dipublikasikan
    assert b["tahap_label"] == "Sidang akhir"
