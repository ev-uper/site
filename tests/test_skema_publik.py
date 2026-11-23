"""Nama skema dana di situs publik tanpa petunjuk isian formulir (bangun.nama_skema_publik, pemilik 2026-11-20)."""
import bangun


def test_nama_skema_publik():
    assert bangun.nama_skema_publik("Lainnya — sebutkan di keterangan") == ""
    assert bangun.nama_skema_publik("Swasta lainnya — sebutkan di keterangan") == "Swasta lainnya"
    assert bangun.nama_skema_publik("Penelitian Fundamental") == "Penelitian Fundamental"
    assert bangun.nama_skema_publik("UPERESEARCH — Hibah Selektif Tahunan") == "UPERESEARCH — Hibah Selektif Tahunan"
    assert bangun.nama_skema_publik(None) == ""
