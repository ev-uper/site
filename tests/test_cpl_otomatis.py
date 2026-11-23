"""Hitung CPL otomatis di GitHub Actions (tools/cpl_otomatis.py; pemilik 2026-11-17, OBE O4).

Hanya bagian yang tidak menjalankan run_cpl.py: keputusan hitung/lewati, peta masukan, daftar laporan, dan
penjagaan (tidak berjalan di luar Actions, tidak menulis config.local.yaml bila tidak ada yang baru).
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("cpl_otomatis", ROOT / "tools" / "cpl_otomatis.py")
co = importlib.util.module_from_spec(spec)
spec.loader.exec_module(co)


def test_compute_only_when_something_is_newer_than_last_summary():
    assert co.perlu_hitung(None, [], None)                                            # belum ada ringkasan
    assert not co.perlu_hitung("2026-11-17T10:00:00+00:00", [], "2026-11-17T11:00:00.5+00:00")
    assert co.perlu_hitung("2026-11-17T12:00:00+00:00", [], "2026-11-17T11:00:00+00:00")
    # Waktu Apps Script berakhiran Z dibandingkan dengan benar terhadap waktu Supabase.
    assert co.perlu_hitung(None, [{"diubah": "2026-11-17T11:30:00.000Z"}], "2026-11-17T18:00:00+07:00")
    assert not co.perlu_hitung(None, [{"diubah": "2026-11-17T10:30:00.000Z"}], "2026-11-17T18:00:00+07:00")
    # Unggahan peramban: tanggal ubah asli lama, tetapi baru masuk Drive -> dihitung (uji 2026-11-18: run tanpa
    # centang paksa menganggap 411 berkas nilai akhir yang baru diunggah "tidak baru").
    assert co.perlu_hitung(None, [{"diubah": "2022-02-01T00:00:00.000Z", "dibuat": "2026-11-18T02:00:00.000Z"}],
                           "2026-11-17T18:00:00+07:00")


def test_inputs_are_mapped_to_paths_and_unknown_or_unsafe_names_are_contained(tmp_path):
    daftar = [{"id": "1", "jalur": "nilai_akhir/2021_ganjil/Nilai_Detail_Kelas_2026_Gambar Teknik-CV3A-2021.csv"},
              {"id": "2", "jalur": "advisors.csv"}, {"id": "3", "jalur": "foto/104123002.jpg"},
              {"id": "4", "jalur": "catatan.docx"}, {"id": "5", "jalur": "nilai_akhir/../../rahasia.csv"},
              {"id": "6", "jalur": "lain/advisors.csv"}, {"id": "7", "jalur": "nilai_akhir/2021_ganjil.zip"},
              {"id": "8", "jalur": "nilai_akhir/2021_ganjil/Nilai_Detail_Kelas_2026_Gambar Teknik-CV3A-2021 (1).csv"}]
    paths, unduh, abai = co.petakan_masukan(daftar, tmp_path)
    assert paths == {"final_grades_dir": str(tmp_path / "nilai_akhir"), "advisors_csv": str(tmp_path / "advisors.csv"),
                     "photos_dir": str(tmp_path / "foto")}
    assert abai == 3                                                                  # docx di akar, folder lain, zip
    for _, p in unduh:                                                                # tidak ada yang keluar dari folder masukan
        assert tmp_path in p.resolve().parents
    d = tmp_path / "nilai_akhir" / "2021_ganjil"
    assert dict(unduh)["1"] == d / "Nilai_Detail_Kelas_2026_Gambar Teknik-CV3A-2021.csv"
    # "(1)" dipertahankan: final_grades.py mengenali unduhan ganda dari nama itu (tidak dihitung dua kali).
    assert dict(unduh)["8"] == d / "Nilai_Detail_Kelas_2026_Gambar Teknik-CV3A-2021 (1).csv"
    assert co.nama_aman("..") == "_" and co.nama_aman("a\\b:c") == "a_b_c"


def test_reports_saved_to_drive_include_advisor_pages(tmp_path):
    for n in ("laporan_cpl.xlsx", "ringkasan_cpl.json", "run_cpl.log"):
        (tmp_path / n).write_text("x")
    (tmp_path / "perwalian").mkdir()
    (tmp_path / "perwalian" / "Wali A.html").write_text("x")
    assert [j for j, _ in co.keluaran_laporan(tmp_path)] == ["laporan_cpl.xlsx", "run_cpl.log", "perwalian/Wali A.html"]


def test_apps_script_calls_retry_incomplete_or_failed_replies_and_report_only_keys():
    jawab = iter([{"ok": True, "folder": "x", "versi": "v"}, RuntimeError("Apps Script: Service invoked too many times"),
                  {"ok": True, "data": "QQ=="}])

    def post(url, isi):
        x = next(jawab)
        if isinstance(x, Exception):
            raise x
        return x
    jeda = []
    assert co.panggil(post, "u", {"aksi": "masukan_ambil"}, "data", tidur=jeda.append)["data"] == "QQ=="
    assert jeda == [2, 4]
    try:
        co.panggil(lambda u, i: {"ok": True, "versi": "v"}, "u", {"aksi": "masukan_ambil"}, "data", tidur=lambda s: None)
        raise AssertionError("harus gagal")
    except RuntimeError as e:
        assert "masukan_ambil gagal 5 kali" in str(e) and "kunci: ok, versi" in str(e)


def test_refuses_outside_actions_and_skips_without_writing_when_nothing_new(monkeypatch):
    assert co.main([], env={}) == 2
    monkeypatch.setattr(co, "baca_url", lambda akar: "https://contoh/exec")
    monkeypatch.setattr(co, "baca_kunci", lambda akar: "k" * 40)

    class SB:
        def terakhir(self, tabel, kolom):
            return {"cpl_berkas": "2026-11-17T10:00:00+00:00", "cpl_ringkasan": "2026-11-17T11:00:00+00:00"}[tabel]

    panggil = []
    post = lambda url, isi: panggil.append(isi["aksi"]) or {"ok": True, "berkas": []}
    tulis = []
    monkeypatch.setattr(Path, "write_text", lambda self, *a, **k: tulis.append(self))
    assert co.main([], env={"GITHUB_ACTIONS": "true"}, post=post, sb=SB()) == 0
    assert panggil == ["masukan_daftar"] and tulis == []                              # tidak mengunduh, tidak menulis config
    # Jalan manual (workflow_dispatch) selalu menghitung walau tidak ada yang baru: sampai ke tahap unduh/tulis.
    panggil.clear()
    monkeypatch.setattr(co.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("berhenti di run_cpl")))
    monkeypatch.setattr(Path, "mkdir", lambda self, *a, **k: None)
    monkeypatch.setattr(co, "open", lambda *a, **k: (_ for _ in ()).throw(AssertionError("berhenti di log")), raising=False)
    try:
        co.main([], env={"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch"}, post=post, sb=SB())
    except AssertionError as e:
        assert str(e).startswith("berhenti")
    assert tulis == [co.AKAR / "config.local.yaml"]
