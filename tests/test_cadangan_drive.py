"""Cadangan berkas Google Drive ke komputer prodi (run_cadangan_drive.py, pemilik 2026-11-20), dengan Apps Script tiruan."""
import base64
import json
from pathlib import Path

import pytest

import run_cadangan_drive as cd

AKAR = Path(cd.__file__).resolve().parent
CFG = {"drive_backup": {"chunk_mb": 1, "keep_old_versions": True}}
GDOC = "application/vnd.google-apps.document"


class Drive:
    """Apps Script tiruan: kind cadangan_drive, aksi daftar/ambil."""

    def __init__(self):
        self.berkas, self.gagal, self.ambil = {}, set(), 0

    def taruh(self, i, jalur, nama, isi, diubah="2026-11-20T01:00:00Z", jenis="application/pdf"):
        self.berkas[i] = {"id": i, "jalur": jalur, "nama": nama, "isi": isi, "diubah": diubah, "jenis": jenis}

    def __call__(self, url, isi):
        assert isi["kind"] == "cadangan_drive" and isi["kunci"] == "k" * 32
        if isi["aksi"] == "daftar":
            return {"ok": True, "berkas": [{k: v for k, v in b.items() if k != "isi"} | {"ukuran": len(b["isi"])}
                                           for b in self.berkas.values()]}
        self.ambil += 1
        if isi["id"] in self.gagal:
            raise RuntimeError("Apps Script: jaringan putus")
        data = self.berkas[isi["id"]]["isi"]
        m = isi["mulai"]
        return {"ok": True, "total": len(data), "data": base64.b64encode(data[m:m + isi["panjang"]]).decode()}


def jalan(drive, tujuan, hari="2026-11-20", **kw):
    log = []
    hasil = cd.jalankan(CFG, tujuan, drive, "https://contoh/exec", "k" * 32, log.append, tidur=lambda s: None,
                        hari_ini=hari, **kw)
    return hasil, log


def test_config_kunci_dan_nama_kembar(tmp_path, monkeypatch):
    assert cd.periksa_config({}, AKAR) == ["drive_backup: bagian belum ada di config.yaml"]
    err = cd.periksa_config({"drive_backup": {"chunk_mb": 30, "keep_old_versions": "ya"}, "paths": {"drive_backup_dir": str(AKAR / "x")}}, AKAR)
    assert any("drive_backup.chunk_mb" in e for e in err) and any("keep_old_versions" in e for e in err)
    assert any("berada di dalam repo" in e for e in err)
    assert cd.periksa_config({**CFG, "paths": {"drive_backup_dir": str(tmp_path / "cadangan")}}, AKAR) == []
    assert any("belum diisi" in e for e in cd.periksa_config(CFG, AKAR))
    monkeypatch.setenv("CADANGAN_DRIVE_KUNCI", "a" * 40)
    assert cd.baca_kunci(tmp_path) == "a" * 40
    monkeypatch.setenv("CADANGAN_DRIVE_KUNCI", "pendek")
    with pytest.raises(ValueError, match="minimal 32 karakter"):
        cd.baca_kunci(tmp_path)
    terpakai = {"bukti/laporan.pdf"}
    assert cd.jalur_lokal({"id": "abcdefghijk", "jalur": "bukti", "nama": "laporan.pdf"}, terpakai) == "bukti/laporan [abcdefgh].pdf"
    assert cd.jalur_lokal({"id": "z", "jalur": "a/b:c", "nama": "x?.pdf"}, set()) == "a/b_c/x_.pdf"


def test_cadangan_bertahap_versi_lama_hilang_dan_gagal(tmp_path):
    d, t = Drive(), tmp_path / "cadangan"
    besar = bytes(range(256)) * 10000                       # 2,56 MB: tiga potongan 1 MB
    d.taruh("A1", "berkas-privat/cpl", "nilai.xlsx", besar)
    d.taruh("B1", "bukti", "sertifikat.pdf", b"%PDF-1 isi")
    d.taruh("B2", "bukti", "sertifikat.pdf", b"%PDF-2 kembar nama")
    d.taruh("G1", "", "Catatan rapat", b"", jenis=GDOC)
    h, log = jalan(d, t)
    assert h == {"berkas": 3, "baru": 3, "berubah": 0, "hilang": 0, "gagal": 0, "lewat": 1, "megabita": 2.4}
    assert (t / "berkas-privat/cpl/nilai.xlsx").read_bytes() == besar
    assert (t / "bukti/sertifikat.pdf").read_bytes() == b"%PDF-1 isi"
    assert (t / "bukti/sertifikat [B2].pdf").read_bytes() == b"%PDF-2 kembar nama"
    assert not list(t.rglob("*.sebagian"))
    m = json.loads((t / "_manifest.json").read_text(encoding="utf-8"))
    assert set(m) == {"A1", "B1", "B2"}

    d.ambil = 0
    h, _ = jalan(d, t, "2026-11-27")                        # tidak ada yang berubah: tidak ada unduhan
    assert (h["baru"], h["berubah"], d.ambil) == (0, 0, 0)

    d.taruh("B1", "bukti", "sertifikat.pdf", b"%PDF-1 diganti", diubah="2026-11-28T00:00:00Z")
    del d.berkas["B2"]
    d.taruh("C1", "mahasiswa", "laporan.pdf", b"%PDF baru")
    d.gagal.add("C1")
    h, log = jalan(d, t, "2026-11-28")
    assert (h["berubah"], h["hilang"], h["gagal"], h["baru"]) == (1, 1, 1, 1)
    assert (t / "bukti/sertifikat.pdf").read_bytes() == b"%PDF-1 diganti"
    assert (t / "_versi_lama/2026-11-28/bukti/sertifikat.pdf").read_bytes() == b"%PDF-1 isi"
    assert (t / "bukti/sertifikat [B2].pdf").is_file()       # hilang dari Drive: salinan tetap
    m = json.loads((t / "_manifest.json").read_text(encoding="utf-8"))
    assert m["B2"]["hilang_sejak"] == "2026-11-28" and "C1" not in m
    assert any("GAGAL: mahasiswa/laporan.pdf" in s for s in log)

    d.gagal.clear()
    h, _ = jalan(d, t, "2026-11-29")                         # yang gagal dicoba lagi; yang hilang tidak dihitung ulang
    assert (h["baru"], h["hilang"], h["gagal"]) == (1, 0, 0)
    assert (t / "mahasiswa/laporan.pdf").read_bytes() == b"%PDF baru"

    d.taruh("B2", "bukti", "sertifikat.pdf", b"%PDF-2 kembar nama")   # dipulihkan dari Sampah Drive
    h, _ = jalan(d, t, "2026-11-30")
    assert (h["baru"], h["berubah"]) == (0, 0)
    assert "hilang_sejak" not in json.loads((t / "_manifest.json").read_text(encoding="utf-8"))["B2"]


def test_berkas_lokal_rusak_diunduh_ulang_dan_hanya_periksa(tmp_path):
    d, t = Drive(), tmp_path / "c"
    d.taruh("A", "x", "a.pdf", b"%PDF isi asli")
    jalan(d, t)
    (t / "x/a.pdf").write_bytes(b"terpotong")                # salinan lokal rusak (ukuran beda)
    h, _ = jalan(d, t, "2026-11-21")
    assert h["berubah"] == 1 and (t / "x/a.pdf").read_bytes() == b"%PDF isi asli"
    d.taruh("B", "x", "b.pdf", b"%PDF baru")
    h, _ = jalan(d, t, "2026-11-22", hanya_periksa=True)
    assert h["baru"] == 1 and not (t / "x/b.pdf").exists()
    assert "B" not in json.loads((t / "_manifest.json").read_text(encoding="utf-8"))


def test_ukuran_tidak_cocok_ditolak(tmp_path):
    def post(url, isi):
        if isi["aksi"] == "daftar":
            return {"ok": True, "berkas": [{"id": "A", "jalur": "", "nama": "a.pdf", "ukuran": 99, "diubah": "x", "jenis": "application/pdf"}]}
        return {"ok": True, "total": 5, "data": base64.b64encode(b"12345").decode()}
    h, log = jalan(post, tmp_path / "c")
    assert h["gagal"] == 1 and any("ukuran tidak cocok" in s for s in log)
    assert not (tmp_path / "c" / "a.pdf").exists() and not list((tmp_path / "c").rglob("*.sebagian"))


def test_jalur_lebih_dari_260_karakter(tmp_path):
    """Folder + nama berkas Drive yang panjang (cadangan pertama 2026-11-20 gagal di satu berkas: Errno 2)."""
    d, t = Drive(), tmp_path / "cadangan"
    folder = "2025/Nama Dosen/" + "Toward Sustainable Flood Resilience Assessing Efficacy " * 2
    nama = "20261115-065221_" + "Rizaldi et al. 2025 Toward Sustainable Flood Resilience " * 3 + ".pdf"
    d.taruh("P1", folder.strip(), nama, b"%PDF panjang")
    assert len(str(t / folder / nama)) > 260
    h, log = jalan(d, t)
    assert h["gagal"] == 0 and h["baru"] == 1, log
    lokal = json.loads((t / "_manifest.json").read_text(encoding="utf-8"))["P1"]["lokal"]
    assert cd._os_path(t / lokal).read_bytes() == b"%PDF panjang"
    h, _ = jalan(d, t, "2026-11-27")                        # dikenali sebagai sama, tidak diunduh ulang
    assert (h["baru"], h["berubah"]) == (0, 0)
