"""Pengajuan mahasiswa KP dan lomba (instal-lengkap.sql, pemilik 2026-11-17).

Skema lengkap dari semua patch dipasang di PGlite (tools/uji_pengajuan.mjs) lalu fungsi-fungsinya
dijalankan sebagai anon dan authenticated. Butuh node + tools/node_modules; dilewati bila tidak ada.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

import supabase_archive as sa

ROOT = Path(sa.__file__).resolve().parent
ADA = shutil.which("node") and (ROOT / "tools" / "node_modules").is_dir() and (ROOT / "tools" / "uji_pengajuan.mjs").is_file()
pytestmark = pytest.mark.skipif(not ADA, reason="node, tools/node_modules, atau tools/uji_pengajuan.mjs tidak ada")


@pytest.fixture(scope="module")
def h(tmp_path_factory):
    t = tmp_path_factory.mktemp("pengajuan")
    (t / "skema.sql").write_bytes(sa.full_schema(ROOT))
    r = subprocess.run(["node", str(ROOT / "tools" / "uji_pengajuan.mjs"), str(t / "skema.sql"), str(t / "hasil.json")],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-2000:]
    return {x["langkah"]: x for x in json.loads((t / "hasil.json").read_text(encoding="utf-8"))}


def gagal(h, langkah, kata):
    assert not h[langkah]["ok"] and kata in h[langkah]["galat"], h[langkah]


def nilai(h, langkah):
    assert h[langkah]["ok"], h[langkah]
    return h[langkah]["nilai"]


def test_key_and_tables_are_closed(h):
    for l in ("anon_baca_kunci", "admin_baca_kunci", "anon_baca_pengajuan", "anon_putuskan"):
        gagal(h, l, "permission denied")
    gagal(h, "buat_kunci_salah", "Kunci layanan salah")
    gagal(h, "catat_berkas_tanpa_kunci", "Kunci layanan salah")


def test_only_lecturers_can_be_chosen_as_advisor(h):
    assert [r["nama"] for r in nilai(h, "pilihan")] == ["Admin Prodi", "Dosen Lain", "Pembimbing Satu"]
    gagal(h, "buat_pembimbing_staf", "Pilih dosen pembimbing")


def test_kp_needs_letter_and_locks_after_sending(h):
    v = nilai(h, "lihat_kp")[0]["v"]
    assert v["data"] == {"instansi": "PT Contoh", "rencana_mulai": "2027-01-05"}     # kunci asing dibuang, spasi dirapikan
    gagal(h, "lihat_token_salah", "Tautan tidak berlaku")
    gagal(h, "kirim_tanpa_berkas", "surat permohonan")
    gagal(h, "catat_surat_pengantar_mhs", "diunggah admin")
    assert nilai(h, "kirim_kp")[0]["s"] == "admin"          # 107: KP tahap 1 langsung ke koordinator KP/admin
    gagal(h, "ubah_setelah_kirim", "sedang diperiksa")


def test_two_level_review(h):
    assert nilai(h, "dosen_lain_baca") == []
    assert nilai(h, "pembimbing_baca") == [{"id": 1, "status": "pembimbing"}]
    assert nilai(h, "pembimbing_baca_berkas") == [{"jenis": "surat_permohonan"}]
    gagal(h, "dosen_lain_putuskan", "Hanya dosen pembimbing")
    gagal(h, "pembimbing_tolak", "Menolak khusus")
    gagal(h, "pembimbing_kembalikan_tanpa_catatan", "Tulis catatan")
    assert nilai(h, "pembimbing_setujui")[0]["s"] == "admin"
    gagal(h, "pembimbing_tahap_admin", "diputuskan koordinator")
    gagal(h, "pembimbing_surat_pengantar", "Surat dari prodi diunggah")
    assert nilai(h, "admin_setujui")[0]["s"] == "disetujui"
    v = nilai(h, "lihat_kp_akhir")[0]["v"]
    assert [b["jenis"] for b in v["berkas"]] == ["surat_permohonan", "surat_pengantar"]
    assert [b["oleh"] for b in v["berkas"]] == ["mahasiswa", "prodi"]                 # email admin tidak bocor
    assert [r["status"] for r in v["riwayat"]] == ["draf", "pembimbing", "admin", "disetujui", "disetujui"]


def test_new_link_replaces_old_and_is_rate_limited(h):
    assert nilai(h, "tautan_ulang")[0]["v"][0]["judul"] == "PT Contoh"
    gagal(h, "tautan_ulang_lagi", "baru saja dikirim")
    gagal(h, "token_lama", "Tautan tidak berlaku")
    assert nilai(h, "token_baru") == [{"s": "disetujui"}]


def test_approved_competition_becomes_verified_achievement_with_evidence(h):
    gagal(h, "lomba_tingkat_salah", "Tingkat lomba")
    assert nilai(h, "lomba_kembalikan")[0]["s"] == "dikembalikan"
    assert nilai(h, "lomba_admin_tahap_pembimbing")[0]["s"] == "disetujui"    # 108: satu persetujuan (admin menggantikan pembimbing)
    gagal(h, "lomba_admin_setujui", "tidak sedang menunggu")
    p = nilai(h, "prestasi")
    assert p == [{"nama_mahasiswa": "Budi; Cici", "nim": "104123010; 104123011", "nama_kegiatan": "Lomba Jembatan",
                  "penyelenggara": "Kementerian", "bidang": "akademik", "bulan": 10, "tingkat": "nasional",
                  "capaian": "Juara 1", "tahun": 2026, "pembimbing": ["002"], "status": "terverifikasi", "tampil_nama": True}]
    assert [b["jenis"] for b in nilai(h, "prestasi_bukti")] == ["lainnya", "foto", "sertifikat"]
    r = nilai(h, "riwayat_lomba")[0]["r"]
    assert [x["status"] for x in r] == ["draf", "pembimbing", "dikembalikan", "pembimbing", "disetujui"]
    assert r[2]["catatan"] == "Lengkapi penyelenggara" and r[4]["oleh"] == "Admin Prodi (pembina kemahasiswaan/admin)"


def test_kp_completion_report_two_level_and_student_overview(h):
    """instal-lengkap.sql: laporan selesai KP setelah pengajuan disetujui; daftar pengajuan satu NIM."""
    gagal(h, "s_ubah_pengajuan", "sudah disetujui")
    gagal(h, "s_catat_permohonan", "sudah diperiksa")
    gagal(h, "s_buang_permohonan", "tidak bisa dibuang")
    gagal(h, "s_kirim_kosong", "pembimbing lapangan")
    gagal(h, "s_tanggal_terbalik", "sebelum tanggal mulai")
    gagal(h, "s_kirim_tanpa_surat", "laporan KP")
    assert nilai(h, "s_kirim")[0]["s"] == "pembimbing"
    gagal(h, "s_ubah_setelah_kirim", "tidak bisa diubah")
    assert [nilai(h, l)[0]["s"] for l in ("s_kembalikan", "s_lagi", "s_pembimbing", "s_admin")] == \
        ["dikembalikan", "pembimbing", "admin", "disetujui"]
    v = nilai(h, "s_lihat")[0]["v"]
    assert v["tahap"] == "selesai" and v["status"] == "disetujui" and not v["boleh_ubah"] and not v["jendela_selesai"]
    assert v["data_selesai"]["pembimbing_lapangan"] == "Ir. Budi" and "asing" not in v["data_selesai"]
    assert [(r["tahap"], r["status"]) for r in v["riwayat"] if r["tahap"] == "selesai"] == \
        [("selesai", "pembimbing"), ("selesai", "dikembalikan"), ("selesai", "pembimbing"), ("selesai", "admin"), ("selesai", "disetujui")]
    assert [(x["judul"], x["status"]) for x in v["lain"]] == [("PT Dua", "draf")]
    gagal(h, "s_lomba_selesai", "belum bisa dikirim")


def test_letter_request_goes_to_admin_and_needs_signed_letter(h):
    """instal-lengkap.sql: surat ditandatangani Kaprodi; tanpa pembimbing, langsung admin."""
    gagal(h, "surat_jenis_salah", "Jenis surat tidak dikenal")
    gagal(h, "surat_kirim_kurang", "keperluannya")
    gagal(h, "surat_jadi_mhs", "diunggah admin")
    assert nilai(h, "surat_kirim")[0]["s"] == "admin"
    assert nilai(h, "surat_pembimbing_baca") == []
    gagal(h, "surat_pembimbing_putus", "diputuskan koordinator")
    gagal(h, "surat_sah_tanpa_surat", "sudah ditandatangani")
    assert nilai(h, "surat_sah")[0]["s"] == "disetujui"
    v = nilai(h, "surat_lihat")[0]
    assert v["pb"] is None and "asing" not in v["d"] and v["d"]["jenis_surat"] == "izin_penelitian"


def test_ta_registration_screened_then_scheduled_by_admin(h):
    """instal-lengkap.sql: penyaringan TA di sistem prodi (pemilik 2026-11-17); jadwal lalu input ke SIUP."""
    gagal(h, "ta_tahap_salah", "Tahap TA")
    gagal(h, "ta_kirim_tanpa_naskah", "naskah TA")
    assert nilai(h, "ta_kirim")[0]["s"] == "pembimbing" and nilai(h, "ta_pembimbing")[0]["s"] == "admin"
    gagal(h, "ta_sahkan_biasa", "Jadwalkan")
    gagal(h, "ta_jadwal_dosen", "khusus koordinator TA atau admin")
    gagal(h, "ta_jadwal_tanpa_penguji", "minimal satu penguji")
    assert nilai(h, "ta_jadwal")[0]["j"] >= 1
    gagal(h, "ta_jadwal_lagi", "sudah dijadwalkan")
    b = nilai(h, "ta_baris")[0]
    assert (b["pembimbing"], b["penguji"], b["tanggal"], b["status"], b["tampil_nama"]) == (["002", "003"], ["003"], "2026-12-03", "terjadwal", True)
    assert nilai(h, "ta_dosen_baca_jadwal")[0]["n"] == 1
    gagal(h, "ta_anon_jadwal", "permission denied")
    v = nilai(h, "ta_lihat")[0]
    assert v["s"] == "disetujui" and v["p2"] == "Dosen Lain" and v["j"]["penguji"] == ["Dosen Lain"] and v["j"]["ruang"] == "R 2.1"


def test_revision_after_defence_marked_by_advisor_or_admin(h):
    """instal-lengkap.sql: batas dan catatan revisi; pembimbing (1 atau 2) atau admin menandai selesai."""
    gagal(h, "rv_bukan_revisi", "bukan lulus dengan revisi")
    assert nilai(h, "rv_bukan_pembimbing")[0]["ta_revisi_selesai"]       # pembimbing 2 boleh
    assert nilai(h, "rv_batal") == [{"d": None}]
    gagal(h, "rv_orang_lain", "Hanya pembimbing")
    assert nilai(h, "rv_pembimbing") == [{"ok": True}]
    j = nilai(h, "rv_lihat")[0]["j"]
    assert (j["hasil"], j["batas_revisi"], j["catatan_revisi"]) == ("lulus_revisi", "2026-12-20", "Perbaiki bab 3") and j["revisi_selesai"]


def test_student_output_mandiri_goes_to_lkps_but_not_when_with_lecturer(h):
    """instal-lengkap.sql: publikasi/luaran mandiri -> 6.e.1 / 6.e.3; bersama dosen lewat karya dosen."""
    gagal(h, "lu_indeks_salah", "Indeksasi")
    gagal(h, "lu_kirim_tanpa_bukti", "bukti publikasi/luaran")
    assert nilai(h, "lu_admin")[0]["s"] == "disetujui"
    assert nilai(h, "lu_tabel_pub") == [{"tahun": 2026, "judul": "Simulasi banjir", "nama_mahasiswa": "Lia; Rudi", "nim": "104123055; 104123056",
                                          "jenis": "jurnal", "tingkat": "nasional", "indeksasi": "sinta", "bulan": 10,
                                          "bukti_url": "https://doi.org/10.1/x"}]
    assert nilai(h, "lu_bukti_pub") == [{"n": 1}]
    assert nilai(h, "lu_tabel_hki") == [{"jenis": "hak_cipta", "judul": "Aplikasi debit", "nomor": "EC00202612345", "nim": "104123057"}]
    b = nilai(h, "lu_bersama")[0]
    assert b["n_pub"] == 1 and b["lid"] is None and "bersama dosen" in b["cat"]


def test_coordinators_act_only_in_their_field_and_period(h):
    """instal-lengkap.sql: koordinator menggantikan admin di bidangnya; periode lewat = tanpa wewenang."""
    assert {r["jenis"] for r in nilai(h, "ko_ta_baca")} == {"ta"}
    gagal(h, "ko_lama_jadwal", "khusus koordinator TA")
    assert nilai(h, "ko_ta_jadwal") == [{"ok": True}]
    assert nilai(h, "ko_ta_ubah_jadwal") == [{"ruang": "R2"}]
    assert nilai(h, "ko_pembina_ubah_jadwal") == []                       # bukan bidangnya: tidak ada baris berubah
    assert {r["jenis"] for r in nilai(h, "ko_pembina_baca")} == {"lomba", "luaran"}
    assert nilai(h, "ko_pembina_prestasi") == [{"nama_kegiatan": "Uji pembina"}]
    gagal(h, "ko_ta_prestasi", "row-level security")
    gagal(h, "ko_ta_tulis_koordinator", "row-level security")


def test_gkm_quality_modules_and_lab_head_own_lab(h):
    """instal-lengkap.sql: GKM menulis modul mutu saja; kepala lab mengubah lab miliknya saja."""
    assert nilai(h, "mu_gkm_temuan") == [{"kode": "A-1"}]
    assert nilai(h, "mu_gkm_narasi") == [{"b": True}]
    gagal(h, "mu_gkm_jadwal", "row-level security")
    gagal(h, "mu_ta_temuan", "row-level security")
    assert nilai(h, "mu_lab_ubah_miliknya") == [{"nama": "Lab Hidro"}]
    assert nilai(h, "mu_lab_ubah_lain") == []
    gagal(h, "mu_lab_buat", "row-level security")


def test_kp_program_magang_and_field_grade_uploaded_by_staff(h):
    # instal-lengkap.sql (pemilik 2026-11-17)
    assert nilai(h, "kp_lihat_magang")[0]["v"]["data"] == {"instansi": "PT Magang", "program": "magang"}
    gagal(h, "kp_program_asing", "Program KP tidak dikenal")
    gagal(h, "kp_mhs_nilai_lapangan", "Nilai pembimbing lapangan diunggah")
    assert nilai(h, "kp_pembimbing_nilai_lapangan")[0]["id"]


def test_learning_evaluation_follow_up_flags_and_gkm_access(h):
    # instal-lengkap.sql (pemilik 2026-11-17, OBE O1)
    assert nilai(h, "ev_perlu_awal") == [{"kode_mk": "SI101", "alasan": ["CPL belum tercapai: CPL1 kelas A"]},
                                         {"kode_mk": "SI103", "alasan": ["EDOM 2,50 di bawah 3,00"]}]
    assert nilai(h, "ev_tambah_tl")[0]["id"]
    assert [r["kode_mk"] for r in nilai(h, "ev_perlu_sesudah")] == ["SI103"]      # sudah ada tindak lanjut = tidak muncul lagi
    assert nilai(h, "ev_tanpa_baris_dosen") == []                                 # dosen biasa tidak melihat rekap prodi
    assert nilai(h, "ev_tanpa_baris_gkm") == [{"kode_mk": "SI102", "belum": ["CPL3 kelas B"]}]
    assert [r["kode_mk"] for r in nilai(h, "ev_gkm_perlu")] == ["SI103"]
    assert nilai(h, "ev_gkm_ubah_tl")[0]["status"] == "proses"
    assert float(nilai(h, "ev_gkm_edom")[0]["edom"]) == 3.9
    gagal(h, "ev_dosen_edom", "Hanya admin atau GKM")


def test_cpmk_structure_and_rps_by_course_coordinator(h):
    # instal-lengkap.sql (pemilik 2026-11-17, OBE O2)
    assert nilai(h, "mk_p1_tulis")[0]["oleh"] == "p1@u.id"                       # koordinator MK (pengampu NIDN)
    gagal(h, "mk_p1_tulis_lain", "row-level security")                           # kelasnya di semester lama, bukan terakhir
    assert nilai(h, "mk_kelas_terakhir_tulis")[0]["kode_mk"] == "SI202"          # pengampu kelas semester terakhir
    assert [r["kode_mk"] for r in nilai(h, "mk_boleh_saya_p1")] == ["SI201"]
    assert [(r["kode_mk"], r["oleh"]) for r in nilai(h, "mk_riwayat")] == [("SI201", "p1@u.id"), ("SI202", "p2@u.id")]
    # 113 (pemilik 2026-11-19): jalur lama mk_simpan_rps ditutup; bukti RPS hanya RPS bertanda tangan Dekan (rps_unggah_ttd).
    for k in ("mk_rps_p1", "mk_rps_bukan_https", "mk_rps_bukan_haknya"):
        gagal(h, k, "permission denied")
    assert nilai(h, "mk_rps_baca") == [{"rps_ada": None, "rps_9_komponen": None, "rps_url": None}]
    gagal(h, "mk_pengampu_dosen", "ditetapkan admin prodi atau GKM")
    assert h["mk_pengampu_gkm"]["ok"], h["mk_pengampu_gkm"]
    gagal(h, "mk_pengampu_asing", "bukan dosen terdaftar")
    gagal(h, "mk_data_salah", "mk_struktur_data_check")


def test_course_portfolio_access_and_ami_link(h):
    # instal-lengkap.sql (pemilik 2026-11-17, OBE O3)
    assert nilai(h, "po_koor_mk")[0]["oleh"] == "p1@u.id"                       # koordinator MK: tingkat MK
    assert nilai(h, "po_koor_kelas")[0]["id"]                                    # koordinator MK: kelas mana pun
    assert nilai(h, "po_pengampu_kelasnya")[0]["oleh"] == "p2@u.id"             # pengampu: kelasnya sendiri
    gagal(h, "po_pengampu_kelas_lain", "row-level security")                    # walau p2 boleh mengisi CPMK MK itu (O2)
    assert nilai(h, "po_pengampu_materi")[0]["id"]                               # pengampu kelas boleh melengkapi tingkat MK
    gagal(h, "po_soal_di_kelas", "portofolio_berkas_check")                       # soal hanya di tingkat MK
    assert nilai(h, "po_lain_baca") == [{"n": 0}]
    assert nilai(h, "po_url_pengampu")[0]["u"].startswith("https://drive.google.com/")
    gagal(h, "po_url_lain", "tidak berhak")
    assert sorted(k["kelas"] for k in nilai(h, "po_ringkas_koor")[0]["k"] if k["kode_mk"] == "SI201") == ["A", "B"]
    assert nilai(h, "po_ami_isi") == [{"n": 4, "k": 4}]          # 4 berkas; kelas SI201 A, B + SI202 A (2025/2026 Genap, 2026/2027 Ganjil)
    assert nilai(h, "po_ami_url")[0]["u"].startswith("https://")
    gagal(h, "po_ami_periode_lain", "tidak termasuk tautan AMI")
    gagal(h, "po_ami_dicabut", "tidak berlaku")
    gagal(h, "po_ami_cakup_langsung", "permission denied")                       # pembantu periode tertutup


def test_student_alternative_email_needs_campus_confirmation_or_staff(h):
    """104 (pemilik 2026-11-18): jalur A lewat email kampus, jalur B oleh admin/koordinator aktif; riwayat tercatat."""
    gagal(h, "ea_baca_tabel", "permission denied")                                     # anon tidak membaca
    gagal(h, "ea_minta_kunci_salah", "Kunci layanan salah")
    gagal(h, "ea_minta_email_salah", "tidak sah")
    assert nilai(h, "ea_tujuan_kosong") == [{"v": None}]
    assert len(nilai(h, "ea_minta")[0]["t"]) == 48
    gagal(h, "ea_minta_lagi", "10 menit")
    assert nilai(h, "ea_tujuan_belum") == [{"v": None}]                                # calon belum menerima apa pun
    gagal(h, "ea_konfirmasi_salah", "tidak berlaku")
    assert nilai(h, "ea_konfirmasi")[0]["v"] == {"nim": "104123009", "email": "ani.alt@gmail.com"}
    gagal(h, "ea_konfirmasi_ulang", "tidak berlaku")
    assert nilai(h, "ea_tujuan_aktif") == [{"v": "ani.alt@gmail.com"}]
    gagal(h, "ea_konfirmasi_basi", "kedaluwarsa")
    assert nilai(h, "ea_tujuan_tetap") == [{"v": "ani.alt@gmail.com"}]
    # Jalur B: dosen biasa dan koordinator yang masa tugasnya habis ditolak; koordinator aktif dan admin boleh.
    gagal(h, "ea_dosen_isi", "row-level security")
    assert nilai(h, "ea_dosen_baca") == []
    gagal(h, "ea_koor_lama_isi", "row-level security")
    assert nilai(h, "ea_koor_isi") == [{"nim": "104123010", "email": "b.alt@gmail.com", "oleh": "kta@u.id"}]
    assert nilai(h, "ea_admin_ganti") == [{"email": "ganti@gmail.com", "calon": None, "oleh": "admin@u.id"}]
    assert nilai(h, "ea_admin_cabut") == [{"nim": "104123010"}]
    # Riwayat hanya ditulis pemicu: tulis langsung ditolak (RLS tanpa policy insert, atau hak tabel).
    assert not h["ea_riwayat_tulis"]["ok"] and any(k in h["ea_riwayat_tulis"]["galat"]
                                                   for k in ("row-level security", "permission denied"))
    assert [(r["nim"], r["email"], r["aksi"], r["oleh"]) for r in nilai(h, "ea_riwayat")] == [
        ("104123009", "ani.alt@gmail.com", "diminta", "mahasiswa"),
        ("104123009", "ani.alt@gmail.com", "aktif", "mahasiswa (konfirmasi email kampus)"),
        ("104123009", "baru@gmail.com", "diminta", "mahasiswa"),
        ("104123010", "b.alt@gmail.com", "aktif", "kta@u.id"),
        ("104123009", "ganti@gmail.com", "aktif", "admin@u.id"),
        ("104123010", "b.alt@gmail.com", "dicabut", "admin@u.id"),
    ]
    assert nilai(h, "ea_riwayat_dosen") == []


def test_kp_room_institution_names_partner_evidence_and_assessor_access(h):
    """105 (pemilik 2026-11-18): nama instansi baku, KP selesai di mitra = bukti kegiatan, asesor hanya laporan/surat selesai."""
    assert nilai(h, "kp_kunci") == [{"v": "pt wijaya karya"}]
    gagal(h, "kp_bakukan_dosen", "koordinator KP")
    assert nilai(h, "kp_bakukan_satu") == [{"n": 1}]
    assert nilai(h, "kp_bakukan_semua") == [{"n": 2}]                                   # A dan C (beda tulis, nama sama)
    assert nilai(h, "kp_bakukan_hasil") == [
        {"token_hash": "h105a", "instansi": "PT Wijaya Karya", "asli": "PT. Wijaya  karya"},
        {"token_hash": "h105b", "instansi": "CV Lain Jaya", "asli": "CV Lain"},
        {"token_hash": "h105c", "instansi": "PT Wijaya Karya", "asli": "pt wijaya karya"}]
    p = nilai(h, "kp_pelaksanaan")                                                      # hanya KP selesai di mitra
    assert [(r["tahun"], r["kp"], r["magang"]) for r in p] == [(2026, 1, 0)]
    gagal(h, "kp_pelaksanaan_anon", "permission denied")
    assert nilai(h, "kp_asesor_pengajuan") == [{"semua": True, "n": 2}]
    assert [r["jenis"] for r in nilai(h, "kp_asesor_berkas")] == ["laporan_kp", "surat_selesai"]
    assert nilai(h, "kp_asesor_riwayat") == []
    assert nilai(h, "kp_asesor_lama") == [{"n": 0}]
    assert nilai(h, "kp_putus") == [{"kunci": "cv lain jaya", "nama": "CV. Lain Jaya", "keputusan": "tidak", "oleh": "kkp@u.id"}]
    gagal(h, "kp_putus_dosen", "row-level security")
    assert nilai(h, "kp_putus_baca") == [{"kunci": "cv lain jaya", "keputusan": "tidak"}]
    # Rekap untuk semua staf: tanpa NIM/nama mahasiswa; pengunjung tanpa login ditolak.
    r = nilai(h, "kp_rekap_dosen")
    assert [(x["instansi"], x["program"], x["status"], x["tahap"], x["mulai"]) for x in r] == [
        ("CV Lain Jaya", "magang", "disetujui", "selesai", "2026-08-01"),
        ("PT Wijaya Karya", "kp", "disetujui", "selesai", "2026-07-01"),
        ("PT Wijaya Karya", "kp", "pembimbing", "pengajuan", None)]
    assert set(r[0]) == {"id", "instansi", "program", "status", "tahap", "mulai", "dibuat", "pembimbing_id", "jawaban"}
    gagal(h, "kp_rekap_anon", "permission denied")


def test_kp_reported_late_after_finishing(h):
    """106 (pemilik 2026-11-18): formulir lapor selesai KP terpisah; diperiksa dosen pembimbing; wajib laporan + surat selesai."""
    assert nilai(h, "sus_lihat_awal") == [{"j": True, "s": "selesai"}]
    gagal(h, "sus_kirim_biasa", "Kirim laporan selesai")
    nilai(h, "sus_ubah_selesai")
    gagal(h, "sus_kirim_tanpa_berkas", "laporan KP")
    assert nilai(h, "sus_kirim_selesai") == [{"s": "pembimbing"}]
    gagal(h, "sus_ubah_lagi", "sedang diperiksa")
    nilai(h, "sus_pembimbing_setuju")
    nilai(h, "sus_admin_setuju")
    assert nilai(h, "sus_akhir") == [{"tahap": "selesai", "status": "disetujui", "s": "selesai"}]


def test_kp_goes_to_coordinator_who_assigns_advisor(h):
    """107 (pemilik 2026-11-18): tidak ada "KP berjalan"; pengajuan KP diperiksa koordinator saja, yang menetapkan pembimbing."""
    assert nilai(h, "k7_susulan_dibuang") == [{"ada": False}]
    gagal(h, "k7_kirim_selesai", "belum bisa")
    gagal(h, "k7_tanpa_berkas", "surat permohonan")
    assert nilai(h, "k7_kirim") == [{"s": "admin"}]                 # surat balasan menggantikan surat permohonan
    gagal(h, "k7_tidak_dikenal", "Keadaan KP")
    gagal(h, "k7_pembimbing_putuskan", "diputuskan koordinator")
    gagal(h, "k7_tetapkan_dosen", "koordinator KP atau admin")
    gagal(h, "k7_tetapkan_staf", "Pilih dosen")
    assert nilai(h, "k7_tetapkan") == [{"s": "diganti"}]
    assert nilai(h, "k7_tetapkan_sama") == [{"s": "tetap"}]
    assert nilai(h, "k7_riwayat") == [{"catatan": "Dosen pembimbing ditetapkan: Dosen Lain (sebelumnya Pembimbing Satu)"}]
    assert len(nilai(h, "k7_p2_baca")) == 1                        # pembimbing yang ditetapkan melihat pengajuannya
    gagal(h, "k7_tetapkan_anon", "permission denied")
    assert nilai(h, "tolak_admin_setuju") == [{"s": "disetujui"}]


def test_one_active_kp_and_company_answer(h):
    """106/107: satu KP aktif per mahasiswa; ditolak instansi = pengajuan ditutup, lalu pengajuan baru; diterima = surat balasan + mulai."""
    gagal(h, "aktif_kedua", "satu KP aktif")
    assert nilai(h, "aktif_setelah_selesai") == [{"ok": True}]
    gagal(h, "tolak_alasan_pendek", "alasan")
    assert nilai(h, "tolak") == [{"s": "ditolak"}]
    v = nilai(h, "tolak_hasil")[0]
    assert v["status"] == "ditolak" and v["jawab"] == "ditolak"
    assert v["berkas"] == "surat_balasan,surat_pengantar"           # berkas tetap di pengajuan yang ditutup
    gagal(h, "tolak_lagi", "sudah terbit")
    gagal(h, "tolak_ubah", "tidak bisa diubah")
    assert nilai(h, "tolak_baca_p1") == []                                                      # bukan pembimbingnya lagi
    assert nilai(h, "tolak_baca_p2") == [{"instansi": "PT Jalan", "alasan": "Kuota KP penuh"}]   # pembimbing yang ditetapkan
    assert nilai(h, "tolak_rekap_staf") == [{"instansi": "PT Jalan", "n": 1}]
    gagal(h, "tolak_rekap_anon", "permission denied")
    # Pengajuan baru diperiksa penuh, lalu diterima instansi.
    assert nilai(h, "k7_baru_kirim") == [{"s": "admin"}]
    gagal(h, "k7_terima_belum", "sudah terbit")
    gagal(h, "k7_terima_tanpa_balasan", "surat balasan")
    gagal(h, "k7_terima_tanpa_tanggal", "tanggal mulai")
    assert nilai(h, "k7_terima") == [{"s": "diterima"}]
    assert nilai(h, "k7_terima_hasil") == [{"status": "disetujui", "jawab": "diterima", "mulai": "2026-12-01", "j": True}]
    assert nilai(h, "k7_rekap") == [
        {"instansi": "PT Jalan", "status": "ditolak", "mulai": None, "jawaban": "ditolak"},
        {"instansi": "PT Terima", "status": "disetujui", "mulai": "2026-12-01", "jawaban": "diterima"}]


def test_advisor_quota_per_academic_year(h):
    """107: kuota pembimbing KP per TS (1 Sep - 31 Agu, tahun ujung); bawaan + per dosen; beban tanpa draf/ditolak."""
    gagal(h, "k7_kuota_dosen", "koordinator KP atau admin")
    for l in ("k7_kuota_bawaan", "k7_kuota_p2", "k7_kuota_p2_ulang", "k7_kuota_hapus"):
        nilai(h, l)
    gagal(h, "k7_kuota_salah", "Kuota 0 sampai 100")
    assert nilai(h, "k7_beban") == [
        {"nama": "Admin Prodi", "kuota": 3, "kuota_sendiri": False, "beban": 0},
        {"nama": "Dosen Lain", "kuota": 2, "kuota_sendiri": True, "beban": 1}]   # PT Terima; PT Jalan ditolak tidak dihitung
    assert nilai(h, "k7_beban_hapus") == [{"kuota": 3, "kuota_sendiri": False}]
    gagal(h, "k7_kuota_tulis_langsung", "permission denied")
    gagal(h, "k7_beban_anon", "permission denied")
    gagal(h, "k7_kuota_anon", "permission denied")
    assert nilai(h, "k7_ts") == [{"a": 2027, "b": 2026}]


def test_competition_report_needs_one_approval(h):
    """108 (pemilik 2026-11-18): lomba disahkan pembimbing ATAU pembina kemahasiswaan ATAU admin, siapa pun lebih dulu."""
    gagal(h, "l8_dosen_lain", "Hanya dosen pembimbing")
    assert nilai(h, "l8_pembimbing_setuju") == [{"s": "disetujui"}]
    gagal(h, "l8_setuju_kedua", "tidak sedang menunggu")
    assert nilai(h, "l8_pembina_setuju") == [{"s": "disetujui"}]
    assert nilai(h, "l8_riwayat_pembina") == [{"oleh": "Pembina (pembina kemahasiswaan/admin)"}]
    assert nilai(h, "l8_prestasi") == [{"nama_kegiatan": "Lomba pembimbing", "status": "terverifikasi"},
                                       {"nama_kegiatan": "Lomba pembina", "status": "terverifikasi"}]
    # Laporan lama yang sudah di tahap admin: tetap pembina/admin.
    gagal(h, "l8_lama_pembimbing", "diputuskan koordinator")
    assert nilai(h, "l8_lama_pembina") == [{"s": "disetujui"}]


def test_supervision_load_per_lecturer(h):
    """109 (pemilik 2026-11-18): beban bimbingan per dosen per TS, hanya angka, untuk staf yang login."""
    gagal(h, "b9_anon", "permission denied")
    assert nilai(h, "b9_asing") == [{"n": 0}]
    assert nilai(h, "b9_dosen") == [
        # Dosen Lain: pembimbing 2 mahasiswa A, penguji sidang B (jadwal batal tidak dihitung).
        {"nama": "Dosen Lain", "kk": None, "kp": 0, "kp_selesai": 0, "kp_kuota": 2, "ta": 1, "ta_lulus": 0, "uji": 1, "lomba": 0},
        # Pembimbing Satu: KP 2 (ditolak/draf tidak), TA A (dua pengajuan = satu mahasiswa) + B (jadwal manual) = 2,
        # lomba Okt 2030 + bulan kosong 2031 = 2 (Sep 2031 = TS 2032, ditolak tidak).
        {"nama": "Pembimbing Satu", "kk": "AIR", "kp": 2, "kp_selesai": 1, "kp_kuota": 2, "ta": 2, "ta_lulus": 1, "uji": 0, "lomba": 2}]


def test_ta_advisor_by_expertise_group_and_quota(h):
    """110 (pemilik 2026-11-18): pengajuan pembimbing TA; pembimbing 1 KK sama atau berdekatan (STR-GEO, STR-MRK,
    AIR-GEO, TRN-GEO); koordinator TA boleh di luar aturan dengan alasan; kuota TA per TS; seminar ikut penetapan."""
    assert nilai(h, "t0_pilihan") == [{"nama": "Dosen Lain", "kk": "GEO", "kk_cocok": ["AIR", "GEO", "STR", "TRN"]},
                                      {"nama": "Pembimbing Satu", "kk": "AIR", "kk_cocok": ["AIR", "GEO"]}]
    gagal(h, "t1_tanpa_kk", "kelompok keahlian TA")
    gagal(h, "t1_luar_kk", "Pembimbing 1 harus dari kelompok keahlian")
    assert nilai(h, "t1_kirim") == [{"s": "admin"}]                      # langsung ke koordinator TA
    gagal(h, "t1_kedua", "Masih ada pengajuan pembimbing TA")
    gagal(h, "t2_bukan_koor", "koordinator TA atau admin")
    gagal(h, "t2_koor_lama", "koordinator TA atau admin")                # masa tugas berakhir
    gagal(h, "t2_tanpa_alasan", "tulis alasannya")
    gagal(h, "t2_sama", "harus berbeda")
    assert nilai(h, "t2_alasan") == [{"s": "diganti"}]
    r = nilai(h, "t2_riwayat")[0]
    assert r["oleh"] == "Koor TA (koordinator TA/admin)"
    assert r["catatan"].startswith("Pembimbing 1 ditetapkan: Pembimbing Satu (sebelumnya Dosen Lain); pembimbing 2: Dosen Lain.")
    assert "Di luar kelompok keahlian TA: Topik drainase" in r["catatan"]
    assert nilai(h, "t2_setujui") == [{"s": "disetujui"}]
    gagal(h, "t3_anon_beban", "permission denied")
    gagal(h, "t3_atur_bukan_koor", "koordinator TA atau admin")
    assert nilai(h, "t3_atur") == [{"s": "ok"}]
    assert nilai(h, "t3_beban") == [{"nama": "Dosen Lain", "kk": "GEO", "kuota": 3, "kuota_sendiri": False, "beban": 0},
                                    {"nama": "Pembimbing Satu", "kk": "AIR", "kuota": 3, "kuota_sendiri": False, "beban": 1}]
    # Seminar sesudah penetapan: pembimbing 1 dan 2 mengikuti penetapan, bukan pilihan mahasiswa.
    assert nilai(h, "t4_kirim") == [{"s": "pembimbing"}]
    assert nilai(h, "t4_pembimbing") == [{"p1": True, "p2": True}]
    assert nilai(h, "t4_lihat") == [{"pb": "Pembimbing Satu", "kk": "TRN"}]
    # Pembimbing 1 di luar KK tanpa alasan tidak bisa disahkan; penetapan tidak dijadwalkan.
    gagal(h, "t5_setujui_luar", "tetapkan pembimbing dengan alasan")
    gagal(h, "t5_jadwalkan", "jadwal_ta_tahap_check")


def test_rps_k26_storage_and_rights(h):
    """111 (pemilik 2026-11-18): RPS di situs (mk_rps), hak tulis sama dengan CPMK (boleh_mk), status draf saja di tahap 1,
    riwayat simpan, nama dengan gelar, jabatan Kaprodi."""
    assert nilai(h, "r1_pengampu") == [{"status": "draf", "oleh": "p1@u.id"}]
    assert nilai(h, "r1_ubah") == [{"t": "Menganalisis"}]
    gagal(h, "r1_bukan_pengampu", "row-level security")
    assert nilai(h, "r1_kelas_terakhir") == [{"kode_mk": "SI202"}]
    gagal(h, "r1_sahkan_sendiri", "row-level security")             # pengesahan lewat Kaprodi (tahap 2)
    gagal(h, "r1_versi_salah", "check constraint")
    gagal(h, "r1_struktur_versi_salah", "check constraint")         # galat cpmk.js 2026-11-17: versi harus '1'
    assert nilai(h, "r1_baca") == [{"kode_mk": "SI201"}, {"kode_mk": "SI202"}]
    gagal(h, "r1_anon", "permission denied")
    assert nilai(h, "r1_riwayat") == [{"kode_mk": "SI201", "t": "Memahami"}, {"kode_mk": "SI201", "t": "Menganalisis"}]
    assert nilai(h, "r1_riwayat_lain") == [{"n": 0}]
    assert nilai(h, "r1_gelar_baca") == [{"nama_gelar": "Dr. Pembimbing Satu, S.T., M.T."}]
    gagal(h, "r1_gelar_pendek", "3 sampai 200")
    gagal(h, "r1_gelar_anon", "permission denied")
    assert nilai(h, "r1_kaprodi") == [{"jabatan": "kaprodi"}]


def test_rps_k26_approval_by_head_of_programme(h):
    """112 (pemilik 2026-11-18): RPS disusun koordinator MK/pengampu (GKM/admin melihat), diajukan ke Kaprodi aktif,
    disahkan atau dikembalikan; salinan sah + data MK; revisi berikutnya wajib ringkasan perubahan."""
    assert nilai(h, "r2_admin_tulis") == [] and nilai(h, "r2_admin_boleh") == [{"n": 0}]
    assert nilai(h, "r2_p1_boleh") == [{"kode_mk": "SI201"}]
    gagal(h, "r2_anon", "permission denied")
    assert nilai(h, "r2_ajukan") == [{"s": "diajukan"}]
    assert nilai(h, "r2_ubah_saat_diajukan") == []                   # terkunci selama diajukan
    gagal(h, "r2_ajukan_lagi", "sudah diajukan")
    gagal(h, "r2_bukan_kaprodi", "Kaprodi aktif")
    gagal(h, "r2_kembalikan_tanpa", "catatan")
    assert nilai(h, "r2_kembalikan") == [{"s": "dikembalikan"}]
    assert nilai(h, "r2_perbaiki") == [{"status": "draf"}]
    assert nilai(h, "r2_palsu") == [{"revisi": 0, "sah": None}]      # kolom pengesahan dijaga trigger
    gagal(h, "r2_url_salah", "https://")
    assert nilai(h, "r2_sahkan") == [{"s": "disahkan"}]
    assert nilai(h, "r2_sah") == [{"status": "disahkan", "revisi": 1, "tujuan": "Menganalisis tanah", "ada_b": True, "oleh": "p1@u.id",
                                   "oleh_kaprodi": True}]
    # 113: pengesahan = sinkron penilaian (RPS ada, 9 komponen); bukti (rps_url) hanya dari RPS bertanda tangan Dekan.
    assert nilai(h, "r2_mk") == [{"rps_url": None, "rps_ada": True, "rps_9_komponen": True}]
    gagal(h, "r2_ajukan_sudah_sah", "sudah disahkan")
    assert nilai(h, "r2_ubah_setelah_sah") == [{"status": "draf"}]
    gagal(h, "r2_ajukan_tanpa_ringkasan", "ringkasan perubahan")
    assert nilai(h, "r2_sahkan2") == [{"s": "disahkan"}]
    assert [(r["aksi"], r["revisi"]) for r in nilai(h, "r2_log")] == [("ajukan", 0), ("kembalikan", 0), ("ajukan", 0), ("sahkan", 1),
                                                                     ("ajukan", 1), ("sahkan", 2)]
    assert nilai(h, "r2_akhir") == [{"status": "disahkan", "revisi": 2, "tujuan": "Revisi pustaka"}]


def test_rps_evidence_only_dean_signed_upload(h):
    """113 (pemilik 2026-11-19): RPS disahkan Kaprodi = terhitung di penilaian; bukti asesor = hanya RPS bertanda tangan Dekan
    yang diunggah penyusun MK atau admin; RPS situs harus sudah disahkan; RPS di luar situs boleh langsung."""
    gagal(h, "t13_anon", "permission denied")
    gagal(h, "t13_bukan_penyusun", "koordinator MK, dosen pengampu")
    gagal(h, "t13_bukan_https", "https://")
    gagal(h, "t13_belum_sah", "belum disahkan Kaprodi")
    for k in ("t13_sah", "t13_luar_situs", "t13_admin"):
        assert nilai(h, k) == [{"s": "ok"}], k
    assert nilai(h, "t13_mk") == [{"kode": "SI201", "rps_url": "https://drive.google.com/file/d/TTD4/view", "rps_ada": True},
                                  {"kode": "SI202", "rps_url": None, "rps_ada": None},
                                  {"kode": "SI203", "rps_url": "https://drive.google.com/file/d/TTD3/view", "rps_ada": True}]
    assert nilai(h, "t13_riwayat") == [{"kode_mk": "SI201", "revisi": 2, "oleh": "p1@u.id"}, {"kode_mk": "SI203", "revisi": None, "oleh": "p1@u.id"},
                                       {"kode_mk": "SI201", "revisi": 2, "oleh": "admin@u.id"}]
    gagal(h, "t13_jalur_lama", "permission denied")


def test_rps_kaprodi_author_flag_and_part_b_change(h):
    """114 (pemilik 2026-11-19): Kaprodi sekaligus penyusun boleh mengesahkan, ditandai; bagian B yang diubah setelah
    disahkan menjadikan RPS draf (salinan sah, revisi, RPS ada tetap)."""
    assert nilai(h, "t14_si201") == [{"tanda": "true", "log": True}]
    assert nilai(h, "t14_sahkan") == [{"s": "disahkan"}]
    assert nilai(h, "t14_si203") == [{"tanda": "false", "log": False}]
    assert nilai(h, "t14_b_sama") == [{"kode_mk": "SI201"}]
    assert nilai(h, "t14_b_sama_st") == [{"status": "disahkan"}]
    assert nilai(h, "t14_b_hasil") == [{"status": "draf", "revisi": 2, "ada_sah": True, "rps_ada": True}]
    assert nilai(h, "t14_ajukan_ulang") == [{"s": "diajukan"}]


def test_rps_review_after_final_grades(h):
    """115 (pemilik 2026-11-19): tinjauan RPS setelah nilai akhir keluar, diisi koordinator MK padanan, disetujui Kaprodi;
    revisi menjadikan RPS sasaran draf dan mencatat revisi dasarnya."""
    gagal(h, "t15_padanan_bukan_admin", "row-level security")
    assert nilai(h, "t15_padanan") == [{"model": "1:1"}]
    gagal(h, "t15_padanan_salah", "check")
    gagal(h, "t15_anon", "permission denied")
    gagal(h, "t15_sebelum_mulai", "dimulai dari semester")
    gagal(h, "t15_tanpa_nilai", "Nilai akhir MK ini")
    gagal(h, "t15_bukan_pengisi", "row-level security")
    assert nilai(h, "t15_buat") == [{"status": "draf", "term_order": 20252}]
    gagal(h, "t15_ajukan_kurang", "Isi keempat bagian")
    gagal(h, "t15_ajukan_tanpa_rencana", "rencana perubahan")
    assert nilai(h, "t15_palsu") == [{"status": "draf", "disetujui_pada": None}]
    assert nilai(h, "t15_ajukan") == [{"s": "diajukan"}]
    assert nilai(h, "t15_ubah_saat_diajukan") == []
    gagal(h, "t15_bukan_kaprodi", "Kaprodi aktif")
    gagal(h, "t15_kembalikan_tanpa", "catatan")
    assert nilai(h, "t15_kembalikan") == [{"s": "dikembalikan"}]
    assert nilai(h, "t15_ajukan2") == [{"s": "diajukan"}]
    assert nilai(h, "t15_sahkan_rps") == [{"s": "disahkan"}]
    assert nilai(h, "t15_setujui") == [{"s": "disetujui"}]
    assert nilai(h, "t15_hasil") == [{"status": "disetujui", "rps_dasar": {"K26|SI201": 3}, "ada_pengesah": True, "rps_status": "draf"}]
    assert [r["aksi"] for r in nilai(h, "t15_log")] == ["ajukan", "kembalikan", "ajukan", "setujui"]
    assert nilai(h, "t15_ubah_disetujui") == []
    assert nilai(h, "t15_sasaran") == [{"kurikulum": "K26", "kode": "SI201"}]


def test_rps_esign_116(h):
    """116 (pemilik 2026-11-19): kode verifikasi, admin selalu boleh a.n. Kaprodi/Dekan, Dekan menetapkan, verifikasi publik."""
    assert nilai(h, "t16_kaprodi_sahkan") == [{"s": "disahkan"}]
    assert nilai(h, "t16_baris_kaprodi") == [{"ada_kode": True, "an_kaprodi": True, "oleh_kaprodi": True, "belum_tetap": True}]
    assert nilai(h, "t16_verif_anon") == [{"ada": "true", "berlaku": "true", "wakil": "false", "tetap": None}]
    assert nilai(h, "t16_verif_salah") == [{"ada": "false"}]
    gagal(h, "t16_anon_tabel", "permission denied")
    gagal(h, "t16_tetap_tanpa_dekan", "Dekan aktif belum ditetapkan")
    gagal(h, "t16_tetap_dosen", "Dekan aktif atau admin")
    assert nilai(h, "t16_tetap_admin") == [{"s": "ditetapkan"}]
    gagal(h, "t16_tetap_ulang", "sudah ditetapkan")
    assert nilai(h, "t16_verif_tetap") == [{"wakil": "true", "ada_dekan": True}]
    gagal(h, "t16_ubah_kode", "row-level security")   # penyusun tidak bisa mengubah kode/penetapan
    assert nilai(h, "t16_admin_sahkan") == [{"s": "disahkan"}]
    assert nilai(h, "t16_baris_admin") == [{"ada_kode": True, "an_kaprodi": True, "oleh_kaprodi": False, "belum_tetap": True}]
    assert nilai(h, "t16_verif_lama") == [{"ada": "false"}]   # pengesahan baru = kode baru
    assert nilai(h, "t16_log") == [{"aksi": "sahkan", "oleh_admin": True, "ada_an": True}, {"aksi": "tetapkan", "oleh_admin": True, "ada_an": True}]


def test_rps_tanggal_sebutan_117(h):
    """117 (pemilik 2026-11-19): sebutan pejabat (Pjs. Dekan) di verifikasi; kunci tanggal dokumen RPS per semester."""
    assert nilai(h, "t17_sebutan") == [{"sebutan": "Pjs. Dekan Fakultas Perencanaan Infrastruktur"}]
    assert nilai(h, "t17_tetapkan") == [{"s": "ditetapkan"}]
    assert nilai(h, "t17_verif") == [{"sebutan": "Pjs. Dekan Fakultas Perencanaan Infrastruktur", "ada_kunci": True}]
    assert nilai(h, "t17_tanggal") == [{"kunci": "rps_tanggal_ganjil"}, {"kunci": "rps_tanggal_genap"}]


def test_rps_review_118(h):
    """118 (pemilik 2026-11-19): review sejawat RPS; Kaprodi/admin menunjuk, pengembang tidak boleh, draf tersembunyi."""
    gagal(h, "t18_tunjuk_dosen", "Kaprodi aktif atau admin")
    assert nilai(h, "t18_tunjuk_kaprodi") == [{"s": "ditunjuk"}]
    assert nilai(h, "t18_tunjuk_admin") == [{"s": "ditunjuk"}]
    gagal(h, "t18_tunjuk_pengembang", "pengembang RPS ini")
    gagal(h, "t18_simpan_bukan", "tidak ditunjuk")
    gagal(h, "t18_skor_salah", "1, 2, 3, atau 4")
    assert nilai(h, "t18_draf") == [{"s": "disimpan"}]
    # GKM (reviewer lain) melihat dua reviewer; isi draf Kalab tersembunyi (null), miliknya sendiri terlihat.
    assert nilai(h, "t18_lihat_draf") == [
        {"nama": "GKM", "skor": "object", "kes": None, "sama": False, "saya": True},
        {"nama": "Kalab", "skor": "null", "kes": None, "sama": False, "saya": False}]
    gagal(h, "t18_kirim_tanpa_kesimpulan", "kesimpulan")
    assert nilai(h, "t18_kirim") == [{"s": "dikirim"}]
    assert {"nama": "Kalab", "skor": "object", "kes": "perbaikan_kecil", "sama": True, "saya": False} in nilai(h, "t18_lihat_kirim")
    assert nilai(h, "t18_tabel_p1") == [{"n": 0}]          # dosen biasa tidak membaca tabel langsung
    assert nilai(h, "t18_tabel_kaprodi") == [{"n": 2}]
    gagal(h, "t18_tulis_langsung", "permission denied")
    gagal(h, "t18_batal_terkirim", "sudah dikirim")
    assert nilai(h, "t18_batal") == [{"s": "dibatalkan"}]
    assert nilai(h, "t18_lihat_berubah") == [{"nama": "Kalab", "skor": "object", "kes": "perbaikan_kecil", "sama": False, "saya": False}]
    gagal(h, "t18_anon", "permission denied")


def test_rps_review_tanggapan_119(h):
    """119 (pemilik 2026-11-19): tanggapan penyusun (bukan reviewer/admin), rekap review per MK."""
    gagal(h, "t19_bukan_penyusun", "dosen penyusun RPS")
    gagal(h, "t19_admin", "dosen penyusun RPS")          # admin tidak menanggapi atas nama penyusun
    gagal(h, "t19_status_salah", "diperbaiki, sebagian, atau tidak_diubah")
    gagal(h, "t19_belum_kirim", "belum dikirim")
    assert nilai(h, "t19_tanggapi") == [{"s": "ditanggapi"}]
    assert nilai(h, "t19_lihat") == [{"status": "diperbaiki", "umum": "Terima kasih", "ada_oleh": True}]
    assert nilai(h, "t19_rekap") == [{"ditunjuk": 1, "terkirim": 1, "ditanggapi": 1, "rerata": 3.5, "kes": ["perbaikan_kecil"]}]
    assert nilai(h, "t19_kirim_ulang") == [{"s": "dikirim"}]
    assert nilai(h, "t19_rekap_ulang") == [{"ditunjuk": 1, "terkirim": 1, "ditanggapi": 0, "rerata": 4, "kes": ["layak"]}]
    gagal(h, "t19_anon", "permission denied")


def test_rps_tenggat_undangan_120(h):
    """120 (pemilik 2026-11-19): tenggat review N hari (bawaan 14, diubah admin); undangan reviewer hanya Kaprodi/admin."""
    assert nilai(h, "t20_hari") == [{"h": 14}]
    assert nilai(h, "t20_tunjuk") == [{"s": "ditunjuk"}]
    gagal(h, "t20_undangan_dosen", "Kaprodi aktif atau admin")
    assert nilai(h, "t20_undangan") == [{"email": "gkm@u.id", "kode": "SI201", "hari": 14, "ada_penunjuk": True}]
    gagal(h, "t20_undangan_terkirim", "sudah dikirim")
    assert nilai(h, "t20_dikabari") == [{"nama": "GKM", "dikabari": True, "ada_tenggat": True},
                                        {"nama": "Kalab", "dikabari": False, "ada_tenggat": True}]
    assert nilai(h, "t20_hari_ubah") == [{"n": 7}]
    assert nilai(h, "t20_hari_7") == [{"h": 7}]
    gagal(h, "t20_anon", "permission denied")


def test_rps_dokumen_elektronik_121(h):
    """121 (pemilik 2026-11-19): bahan Word lewat kode QR tanpa login (tanpa catatan kembalikan); tautan dokumen otomatis."""
    d = nilai(h, "t21_dokumen")[0]
    assert d["kode"] == "SI201" and d["ada_rps"] and d["ada_dosen"] and d["dekan_aktif"]
    assert "kembalikan" not in d["aksi"] and "sahkan" in d["aksi"]
    assert nilai(h, "t21_dokumen_salah") == [{"d": None}]
    gagal(h, "t21_pasang_dosen", "Kaprodi, Dekan, atau admin")
    gagal(h, "t21_pasang_situs_salah", "Alamat situs tidak sah")
    assert nilai(h, "t21_pasang") == [{"s": "terpasang"}]
    assert nilai(h, "t21_tautan") == [{"cocok": True, "rps_ada": True}]
    gagal(h, "t21_pasang_anon", "permission denied")


def test_yudisium_documents_122(h):
    """122 (pemilik 2026-11-19/20): berkas yudisium diperiksa admin prodi saja; 14 wajib + bukti tambahan opsional;
    berkas besar boleh tautan Google Drive (dibuang = barisnya saja); satu yudisium aktif per NIM."""
    assert nilai(h, "y_daftar") == [{"n": 15, "pertama": "Form pendaftaran yudisium", "wajib": 14}]
    gagal(h, "y_anon_tabel", "permission denied")
    assert nilai(h, "y_buat")[0]["t"]
    gagal(h, "y_buat_lagi", "sudah punya pengajuan berkas yudisium")
    assert nilai(h, "y_ubah")
    gagal(h, "y_kirim_kurang", "Berkas wajib belum lengkap: Form pendaftaran yudisium")
    gagal(h, "y_berkas_jenis_lain", "Jenis berkas tidak dikenal")
    gagal(h, "y_berkas_kode_asing", "Jenis berkas tidak dikenal")
    assert all(x["ok"] for k, x in h.items() if k.startswith("y_unggah_")), [x for k, x in h.items() if k.startswith("y_unggah_") and not x["ok"]]
    gagal(h, "y_kirim_tanpa_plagiasi", "Bebas plagiasi")
    gagal(h, "y_tautan_bukan_drive", "Google Drive")
    gagal(h, "y_tautan_http", "Google Drive")
    gagal(h, "y_buka_tautan", "buka tautannya langsung")
    assert nilai(h, "y_buang_tautan") == [{"u": ""}]
    assert nilai(h, "y_tautan_lagi")[0]["id"]
    v = nilai(h, "y_lihat")[0]
    assert v["n"] == 15 and v["tautan_url"] == 1 and v["unggah_url"] == 0
    assert v["d"] == {"judul": "Analisis bendung tetap", "catatan": "Foto menyusul"}   # kunci lain dibuang, pembimbing diabaikan
    assert nilai(h, "y_kirim") == [{"s": "admin"}]
    gagal(h, "y_tautan_setelah_kirim", "sedang diperiksa")
    gagal(h, "y_dosen_putus", "koordinator bidangnya atau admin")
    assert nilai(h, "y_admin_sah") == [{"s": "disetujui"}]
    gagal(h, "y_tautan_kp", "hanya untuk berkas yudisium")
    assert nilai(h, "y_dosen_ubah_daftar") == []
    assert nilai(h, "y_admin_ubah_daftar") == [{"kode": "yud_pem"}]


def test_reviewer_email_1h_and_24h_123_124(h):
    """123/124 (pemilik 2026-11-20): kabar 1 jam ke pemeriksa yang belum membuka ruang kerja; pengingat 24 jam ke semua;
    sekali per tingkat; koordinator bidang aktif, admin bila kosong atau surat; jam kerja diatur Apps Script."""
    assert nilai(h, "k_draf")[0]["perlu"] == "false"
    assert nilai(h, "k_antre") == [{"belum1jam": False, "lewat1jam": True}]
    kp = nilai(h, "k_kp_1")[0]
    assert kp["tingkat"] == 1 and "p2@u.id" in kp["ke"] and "admin@u.id" not in kp["ke"]   # koordinator KP aktif, bukan admin
    assert "p2@u.id" not in (nilai(h, "k_kp_1_aktif")[0]["ke"] or [])                      # sudah membuka ruang kerja
    gagal(h, "k_kunci_salah", "Kunci layanan salah")
    assert nilai(h, "k_tandai_lama") == [{"s": "diabaikan"}]
    assert nilai(h, "k_tandai_1") == [{"s": "tercatat"}]
    assert nilai(h, "k_antre_setelah_1") == [{"jam1": False, "jam24": True}]
    k24 = nilai(h, "k_kp_24")[0]
    assert k24["tingkat"] == 24 and "p2@u.id" in k24["ke"]                         # pengingat: juga yang sudah aktif
    assert nilai(h, "k_tandai_24") == [{"s": "tercatat"}] and nilai(h, "k_tandai_24_lagi") == [{"s": "sudah"}]
    assert nilai(h, "k_antre_setelah_24") == [{"ada": False}]
    assert "p1@u.id" in nilai(h, "k_lomba")[0]["ke"]
    surat = nilai(h, "k_surat")[0]["ke"]
    assert "admin@u.id" in surat and "staf@u.id" in surat and "p2@u.id" not in surat
    assert nilai(h, "k_penanda_lama") == [{"ada": False}]
    assert nilai(h, "k_aktif_baris") == [{"n": 1}]
    gagal(h, "k_catat_aktif_anon", "permission denied")
    assert nilai(h, "k_dikembalikan") == [{"ada": False}] and nilai(h, "k_dikirim_lagi") == [{"ada": True}]


def test_system_health_125(h):
    """125 (pemilik 2026-11-20): status pekerjaan otomatis dinilai satu aturan; admin/pimpinan saja; Apps Script berkunci."""
    gagal(h, "s_anon_tabel", "permission denied")
    gagal(h, "s_dosen", "Khusus admin dan pimpinan")
    assert nilai(h, "s_dosen_tabel") == [{"n": 0}]
    assert nilai(h, "s_kosong") == [{"perlu": 6, "n": 7, "ada_ukuran": True}]          # 6 belum pernah melapor + 1 info (127: +Drive)
    assert nilai(h, "s_lapor") == [{"s": "ok"}]
    gagal(h, "s_lapor_status_salah", "Status tidak dikenal")
    gagal(h, "s_lapor_kunci_salah", "Kunci layanan salah")
    assert nilai(h, "s_lapor_drive") == [{"s": "ok"}]
    st = {k: nilai(h, "s_" + k)[0] for k in ["bangun_situs", "cadangan", "jaga_hidup", "hitung_cpl", "apps_script", "situs_terbit", "cadangan_drive"]}
    assert st["cadangan_drive"]["status"] == "baik" and st["cadangan_drive"]["rinci"] == "12 berkas · 3.4 MB · baru/berubah 3"
    assert st["bangun_situs"]["status"] == "baik" and st["bangun_situs"]["rinci"] == "terbit pada jalan terakhir"
    assert st["cadangan"]["status"] == "terlambat"                                        # 30 jam > 26 jam
    assert st["jaga_hidup"]["status"] == "baik"
    assert st["hitung_cpl"]["status"] == "gagal"
    assert st["apps_script"]["status"] == "perlu_dicek" and "sisa kuota email hari ini 10" in st["apps_script"]["rinci"]
    assert "Drive 33%" in st["apps_script"]["rinci"]
    assert st["situs_terbit"]["status"] == "info"
    k = nilai(h, "s_kunci")[0]
    assert k["perlu"] == 3 and "admin@u.id" in k["admin"] and "p1@u.id" not in k["admin"]
    gagal(h, "s_kunci_salah", "Kunci layanan salah")


def test_security_alerts_126(h):
    """126 (pemilik 2026-11-20): akun berperan khusus, peran/email berubah, akun dihapus, koordinator, hapus massal -> antrean
    peringatan; dosen biasa tidak; Apps Script membaca dan menandai dengan kunci layanan."""
    gagal(h, "k6_anon_tabel", "permission denied")
    for k in ["k6_akun_baru", "k6_dosen_biasa", "k6_ubah_peran", "k6_ubah_email", "k6_koordinator", "k6_hapus_akun"]:
        assert nilai(h, k), k
    for k in ["k6_a_akun_baru", "k6_a_peran", "k6_a_email", "k6_a_koordinator", "k6_a_hapus", "k6_a_massal"]:
        assert nilai(h, k) == [{"n": 1}], (k, nilai(h, k))
    assert nilai(h, "k6_a_biasa") == [{"n": 0}]                     # dosen biasa baru: tidak diperingatkan
    assert nilai(h, "k6_massal_sekali") == [{"n": 1}]               # 21 hapus, satu peringatan per jam
    a = nilai(h, "k6_admin")[0]
    assert a["admin"] and a["n"] >= 6
    assert nilai(h, "k6_tandai")[0]["n"] == a["n"]
    assert nilai(h, "k6_sisa") == [{"n": 0}]
    gagal(h, "k6_kunci_salah", "Kunci layanan salah")


def test_nip_nuptk_by_lecturer_128(h):
    """instal-lengkap.sql: dosen mengisi NIP dan NUPTK sendiri, tanpa ajuan admin (pemilik 2026-11-20)."""
    assert nilai(h, "n8_lihat") == [{"nip": "19800101 200501 1 001", "nuptk": "1234567890123456"}]
    gagal(h, "n8_nip_salah", "NIP: 3–40 karakter")
    gagal(h, "n8_nuptk_salah", "NUPTK: 3–40 karakter")
    assert nilai(h, "n8_lihat_kosong") == [{"nip": None, "nuptk": None}]
    assert nilai(h, "n8_lain_tetap") == [{"nip": None}]
    gagal(h, "n8_anon", "permission denied")
    gagal(h, "n8_tak_terdaftar", "Belum masuk")


def test_silabus_129(h):
    """instal-lengkap.sql: koordinator MK menyusun, hanya Kaprodi aktif mengesahkan, impor admin tanpa menimpa (pemilik 2026-11-20)."""
    gagal(h, "s9_bukan_pengampu", "dosen aktif")   # 131
    gagal(h, "s9_ajukan_kurang", "Lengkapi dulu: pustaka")
    gagal(h, "s9_ajukan_catatan_impor", "hapus catatan impor")
    assert nilai(h, "s9_bersih") == [{"asing": False, "p": "1. Buku"}]
    gagal(h, "s9_tulis_langsung", "permission denied")   # hak tulis dicabut; hanya lewat fungsi
    assert nilai(h, "s9_ajukan") == [{"s": "diajukan"}]
    gagal(h, "s9_simpan_saat_diajukan", "sedang diajukan")
    gagal(h, "s9_bukan_kaprodi", "Kaprodi aktif")
    gagal(h, "s9_admin_an", "Kaprodi aktif")             # admin a.n. Kaprodi hanya untuk RPS (2026-11-19)
    gagal(h, "s9_kembali_tanpa_catatan", "Tulis catatan")
    assert nilai(h, "s9_kembalikan") == [{"s": "dikembalikan"}]
    assert nilai(h, "s9_sahkan") == [{"s": "disahkan"}]
    assert nilai(h, "s9_sah") == [{"status": "disahkan", "revisi": 1, "t": "Tujuan", "kaprodi": True}]
    assert nilai(h, "s9_draf_baru") == [{"status": "draf", "sah": "Tujuan", "kini": "Tujuan baru"}]
    gagal(h, "s9_revisi_tanpa_ringkasan", "ringkasan perubahan")
    assert nilai(h, "s9_revisi") == [{"s": "diajukan"}]
    assert [r["aksi"] for r in nilai(h, "s9_log")] == ["ajukan", "kembalikan", "ajukan", "sahkan", "ajukan"]
    gagal(h, "s9_impor_bukan_admin", "hanya oleh admin")
    assert nilai(h, "s9_impor") == [{"r": {"masuk": 1, "sudah_ada": 1, "tidak_ada": ["TIDAKADA"]}}]
    assert nilai(h, "s9_impor_hasil") == [{"kode_mk": "SI202", "status": "draf", "c": "Dari SIAKUP", "log": 1}]
    gagal(h, "s9_anon_baca", "permission denied")
    gagal(h, "s9_anon_simpan", "permission denied")
    assert nilai(h, "s9_dosen_lain") == [{"s": "draf"}]   # 131: dosen aktif bukan pengampu boleh mengisi


def test_survei_terbit_130(h):
    """instal-lengkap.sql: rekap publik hanya salinan yang diterbitkan admin; hapus jawaban oleh admin (pemilik 2026-11-20)."""
    assert nilai(h, "v0_sebelum_terbit") == [{"ada": 0, "n": None, "h": None}]
    gagal(h, "v0_terbit_bukan_admin", "admin atau GKM")
    gagal(h, "v0_terbit_anon", "permission denied")
    gagal(h, "v0_hitung_anon", "permission denied")
    assert nilai(h, "v0_terbit") == [{"n": 3}]
    assert nilai(h, "v0_sesudah_terbit") == [{"ada": 1, "n": 3, "h": [0, 0, 0, 3]}]
    assert nilai(h, "v0_jawaban_baru_belum_terbit") == [{"ada": 1, "n": 3, "h": [0, 0, 0, 3]}]   # 5 jawaban, publik tetap 3
    assert len(nilai(h, "v0_hapus")) == 2
    assert nilai(h, "v0_hapus_bukan_admin") == []                                                # RLS: dosen biasa tidak menghapus apa pun
    assert nilai(h, "v0_terbit_ulang") == [{"n": 3}]
    assert nilai(h, "v0_sesudah_terbit_ulang") == [{"ada": 1, "n": 3, "h": [0, 0, 0, 3]}]
    assert nilai(h, "v0_sesudah_tarik") == [{"ada": 0, "n": None, "h": None}]


def test_jadwal_berhalangan_132(h):
    """instal-lengkap.sql: dosen mengisi miliknya; pengatur jadwal melihat semua; rekap tanpa nama (pemilik 2026-11-20)."""
    assert len(nilai(h, "j2_slot_admin")) == 1
    gagal(h, "j2_slot_dosen", "row-level security")
    assert nilai(h, "j2_isi_sendiri") == [{"jenis": "prodi_lain"}]
    gagal(h, "j2_isi_orang_lain", "row-level security")
    assert nilai(h, "j2_lihat_dosen_lain") == [{"n": 0}]
    assert nilai(h, "j2_lihat_kaprodi") == [{"alasan": "Mengajar Teknik Lingkungan"}]
    m = nilai(h, "j2_rekap")[0]["m"]
    assert len(m) == 1 and m[0]["n"] == 1 and m[0]["hari"] == 1
    gagal(h, "j2_rekap_anon", "permission denied")
    assert nilai(h, "j2_tgl") == [{"slot_id": None}]
    gagal(h, "j2_tgl_ganda", "duplicate key")
    assert nilai(h, "j2_rekap_tgl") == [{"n": 1}]
    assert nilai(h, "j2_hapus_milik_orang") == []
    assert len(nilai(h, "j2_hapus_sendiri")) == 1


def test_pemakaian_halaman_133(h):
    """instal-lengkap.sql: catat per hari/halaman/pengguna; hanya rekap untuk admin (pemilik 2026-11-20)."""
    gagal(h, "m3_anon_catat", "permission denied")
    gagal(h, "m3_baca_mentah", "permission denied")
    gagal(h, "m3_rekap_dosen", "hanya untuk admin")
    r = nilai(h, "m3_rekap")[0]["r"]
    hal = {x["halaman"]: x for x in r["halaman"]}
    assert set(hal) == {"rps.html", "silabus.html"}                     # '../rahasia.env' diabaikan
    assert hal["rps.html"]["kunjungan"] == 3 and hal["rps.html"]["pengguna"] == 2 and hal["rps.html"]["hari"] == 1
    assert hal["rps.html"]["peran"] == {"dosen": 2}
    assert hal["rps.html"]["jabatan"].get("kaprodi") == 1                # jabatan lain dari blok uji sebelumnya boleh ada
    assert hal["silabus.html"]["jabatan"].get("kaprodi") == 1
    assert r["pengguna_aktif"] == 2


def test_berhalangan_rentang_135(h):
    """instal-lengkap.sql: rentang tanggal + hari + slot; hak seperti 132; rekap menguraikan rentang;
    slot dihapus tidak mengubah rentang menjadi sepanjang hari (pemilik 2026-11-21)."""
    r = nilai(h, "r5_isi")[0]
    assert r["hari"] == [2, 4] and len(r["slot_ids"]) == 1                 # hari dirapikan: unik dan urut
    gagal(h, "r5_orang_lain", "row-level security")
    gagal(h, "r5_terbalik", "check constraint")
    gagal(h, "r5_terlalu_panjang", "check constraint")
    gagal(h, "r5_slot_asing", "Slot jam tidak dikenal")
    gagal(h, "r5_hari_salah", "check constraint")
    assert nilai(h, "r5_lihat_dosen_lain") == [{"n": 0}]
    assert nilai(h, "r5_lihat_kaprodi") == [{"n": 1}]
    rk = nilai(h, "r5_rekap")[0]
    assert rk["harap"] > 0 and rk["n"] == rk["harap"]                    # satu baris per Selasa/Kamis dalam rentang
    gagal(h, "r5_anon", "permission denied")
    assert len(nilai(h, "r5_hapus_slot")) == 1
    sisa = nilai(h, "r5_sesudah_hapus")
    assert [x["hari_ke"] for x in sisa] == [32]                          # rentang yang hanya berisi slot terhapus ikut hilang
    assert len(sisa[0]["slot_ids"]) == 1


def test_penyusunan_kelas_136(h):
    """instal-lengkap.sql: admin/Kaprodi menyusun kelas; team teaching dengan tepat satu koordinator; impor dengan
    NIDN/email; ganti = hapus yang tidak di berkas; salin ke cpl_kelas, kode sama dua kurikulum dilewati (pemilik 2026-11-21)."""
    gagal(h, "k6_bukan_pengatur", "admin atau Kaprodi")
    gagal(h, "k6_tanpa_dosen", "minimal satu dosen")
    gagal(h, "k6_dua_koor", "tepat satu koordinator")
    assert nilai(h, "k6_simpan")[0]["id"] and nilai(h, "k6_simpan_b")[0]["id"]
    assert nilai(h, "k6_baca") == [{"kelas": 2, "dosen": 3}]
    gagal(h, "k6_tulis_langsung", "row-level security")
    gagal(h, "k6_anon", "permission denied")
    r = nilai(h, "k6_impor")[0]["r"]
    assert r["masuk"] == 1 and r["dihapus"] == 0 and len(r["galat"]) == 2
    assert any("tidak@ada.id" in g for g in r["galat"]) and any("TIDAKADA" in g for g in r["galat"])
    r = nilai(h, "k6_impor_ganti")[0]["r"]
    assert r["masuk"] == 1 and r["dihapus"] == 2 and r["galat"] == []
    assert nilai(h, "k6_sesudah_ganti") == [{"kode_mk": "SI201", "kelas": "A", "dosen": "lab@u.id:koordinator,p1@u.id:anggota"}]
    gagal(h, "k6_cpl_bukan_pengatur", "admin atau Kaprodi")
    assert nilai(h, "k6_cpl")[0]["r"] == {"disalin": 1, "bentrok_kurikulum": [], "tanpa_koordinator": []}
    assert nilai(h, "k6_cpl_baris") == [{"dosen_email": "lab@u.id"}]
    assert nilai(h, "k6_cpl_bentrok")[0]["r"] == {"disalin": 0, "bentrok_kurikulum": ["SI201 A"], "tanpa_koordinator": []}


def test_hak_team_teaching_137(h):
    """instal-lengkap.sql: anggota team teaching (kelas_dosen) mendapat hak MK semester berjalan/sesudahnya,
    dan hak tinjauan/portofolio per periode kelasnya; kelas lampau tidak memberi hak MK (pemilik 2026-11-21)."""
    assert nilai(h, "t7_sebelum") == [{"mk": False, "rps": False, "saya": False}]
    assert nilai(h, "t7_kelas_depan")[0]["id"] and nilai(h, "t7_kelas_lampau")[0]["id"]
    assert nilai(h, "t7_sesudah") == [{"mk": True, "rps": True, "saya": True}]
    assert nilai(h, "t7_lampau") == [{"mk": False, "rps": False, "tinjau": True, "tinjau_lain": False}]
    assert nilai(h, "t7_kelas") == [{"a": True, "b": False, "semua": True}]
    assert nilai(h, "t7_dosen_lain") == [{"m": False}]
    gagal(h, "t7_anon", "permission denied")
    assert len(nilai(h, "t7_bersih")) == 2


def test_cari_waktu_rapat_138(h):
    """instal-lengkap.sql: jumlah peserta yang tidak bisa per tanggal/slot dari berhalangan mingguan, rentang,
    dan rapat lain; nama hanya untuk pengatur jadwal; alasan tidak pernah dikirim (pemilik 2026-11-20/21)."""
    k = nilai(h, "w8_kunci")[0]
    slot, sen, sel = int(k["slot"]), k["sen"], k["sel"]
    d = nilai(h, "w8_dosen")[0]["r"]
    assert d["nama"] is False
    per = {(x["tanggal"], x["slot_id"]): x for x in d["sibuk"]}
    assert per[(sen, slot)]["n"] == 2 and "dosen" not in per[(sen, slot)]       # dosen biasa: jumlah saja
    assert per[(sel, slot)]["n"] == 1
    assert "Rahasia" not in str(d)                                                # alasan tidak pernah dikirim
    p = nilai(h, "w8_pengatur")[0]["r"]
    assert p["nama"] is True
    per = {(x["tanggal"], x["slot_id"]): x for x in p["sibuk"]}
    assert sorted(per[(sen, slot)]["dosen"]) == sorted([k["p2"], k["lab"]]) and per[(sel, slot)]["dosen"] == [k["p1"]]
    assert not any(x["tanggal"] == sel for x in nilai(h, "w8_kecuali")[0]["r"]["sibuk"])   # rapat yang sedang diubah
    gagal(h, "w8_terlalu_panjang", "1-32 hari")
    gagal(h, "w8_tanpa_peserta", "1-60 peserta")
    gagal(h, "w8_anon", "permission denied")
    assert nilai(h, "w8_semester") == [{"ta": "2026/2027", "sm": "Ganjil"}, {"ta": "2026/2027", "sm": "Ganjil"},
                                       {"ta": "2026/2027", "sm": "Genap"}]


def test_berhalangan_konfirmasi_140(h):
    """instal-lengkap.sql: dosen menandai isiannya lengkap; dosen lain tidak bisa menandai atau melihat;
    pengatur jadwal melihat semua (pemilik 2026-11-21)."""
    assert nilai(h, "k0_sendiri") == [{"semester": "Genap"}]
    gagal(h, "k0_orang_lain", "row-level security")
    gagal(h, "k0_semester_salah", "check constraint")
    assert nilai(h, "k0_lihat_lain") == [{"n": 0}]
    assert nilai(h, "k0_lihat_pengatur") == [{"n": 1}]
    gagal(h, "k0_anon", "permission denied")
    assert nilai(h, "k0_batal") == [{"semester": "Genap"}]


def test_hari_libur_139(h):
    """instal-lengkap.sql: admin mengisi, dosen membaca, anon hanya lewat hari_libur_antara (pemilik 2026-11-21)."""
    assert len(nilai(h, "l9_admin_isi")) == 2
    assert nilai(h, "l9_dosen_baca") == [{"tanggal": "2099-12-25", "jenis": "nasional"}, {"tanggal": "2099-12-26", "jenis": "cuti_bersama"}]
    gagal(h, "l9_dosen_isi", "row-level security")
    gagal(h, "l9_jenis_salah", "check constraint")
    gagal(h, "l9_anon_tabel", "permission denied")
    r = nilai(h, "l9_anon_fungsi")[0]["r"]
    assert [(x["tanggal"], x["nama"], x["jenis"]) for x in r] == [("2099-12-25", "Hari Raya Natal", "nasional"),
                                                                  ("2099-12-26", "Cuti bersama Natal", "cuti_bersama")]
    gagal(h, "l9_terlalu_panjang", "1-400 hari")
    assert len(nilai(h, "l9_bersih")) == 2


def test_ekuivalensi_sah_134(h):
    """instal-lengkap.sql: Kaprodi aktif mengesahkan, Dekan aktif menetapkan (Pedoman K26 4.1.1 butir 4);
    tanpa a.n. admin; semua MK lama wajib berbaris; suntingan padanan -> draf, versi terbit tetap (pemilik 2026-11-21)."""
    gagal(h, "e4_bukan_kaprodi", "Kaprodi aktif")
    gagal(h, "e4_admin_an", "Kaprodi aktif")
    gagal(h, "e4_belum_lengkap", "SI204")
    assert nilai(h, "e4_tidak_berlanjut") == [{"tidak_berlanjut": True}]
    gagal(h, "e4_tetap_sebelum_sah", "Belum disahkan")
    assert nilai(h, "e4_sahkan") == [{"s": "disahkan"}]
    gagal(h, "e4_sahkan_lagi", "menunggu penetapan Dekan")
    gagal(h, "e4_tetap_bukan_dekan", "Dekan aktif")
    gagal(h, "e4_tetap_admin", "Dekan aktif")
    assert nilai(h, "e4_tetapkan") == [{"s": "ditetapkan"}]
    t = nilai(h, "e4_terbit")
    assert len(t) == 1 and t[0]["status"] == "ditetapkan" and t[0]["revisi"] == 1 and t[0]["terbit"]
    assert t[0]["n"] == 2 and t[0]["dekan"] and t[0]["kaprodi"]          # SI203 -> SI201 dan SI204 tidak berlanjut
    gagal(h, "e4_tulis_langsung", "permission denied")
    gagal(h, "e4_catat_langsung", "permission denied")
    gagal(h, "e4_anon_baca", "permission denied")
    gagal(h, "e4_anon_salinan", "permission denied")
    assert nilai(h, "e4_sunting") == [{"catatan": "Bab 7 Tabel 7-2"}]
    d = nilai(h, "e4_draf_terbit_tetap")[0]
    assert d["status"] == "draf" and d["revisi"] == 1 and d["terbit"] and d["n"] == 2
    assert nilai(h, "e4_sahkan_ulang") == [{"s": "disahkan"}]
    gagal(h, "e4_kembali_tanpa_catatan", "Tulis catatan")
    gagal(h, "e4_kembali_bukan_pejabat", "Kaprodi atau Dekan")
    assert nilai(h, "e4_kembalikan") == [{"s": "draf"}]
    assert nilai(h, "e4_catatan") == [{"status": "draf", "catatan": "Periksa baris SI204", "kosong": True}]
    assert [r["aksi"] for r in nilai(h, "e4_log")] == ["sahkan", "tetapkan", "berubah", "sahkan", "kembalikan"]


def test_kabar_mahasiswa_144(h):
    """instal-lengkap.sql: kabar kegiatan dari mahasiswa; dosen pendamping opsional; satu persetujuan
    (pendamping, pembina kemahasiswaan, atau admin); disahkan -> kabar_kegiatan 'terbit' sekali (pemilik 2026-11-21)."""
    gagal(h, "kb_buat_staf", "Pilih dosen pembimbing")
    gagal(h, "kb_jenis_salah", "Jenis kegiatan tidak dikenal")
    gagal(h, "kb_tautan_salah", "https://")
    gagal(h, "kb_tanggal_salah", "YYYY-MM-DD")
    gagal(h, "kb_ubah_staf", "Pilih dosen pembimbing")
    v = nilai(h, "kb_lihat")[0]
    assert v["jenis"] == "kabar" and v["pb"] is None
    assert v["d"] == {"judul": "Kunjungan lapangan ke bendungan", "tanggal": "2026-11-10", "jenis_kegiatan": "kunjungan_lapangan",
                      "tempat": "Bendungan Contoh", "tautan": "https://contoh.id/p/1",
                      "ringkasan": "Mahasiswa mengunjungi proyek bendungan dan mempelajari bangunan pelimpah."}   # 'asing' dibuang
    gagal(h, "kb_kirim_ringkas_pendek", "minimal 20 huruf")
    gagal(h, "kb_kirim_tanpa_foto", "foto kegiatan")
    assert nilai(h, "kb_kirim") == [{"s": "pembimbing"}]
    p = nilai(h, "kb_pemeriksa")[0]
    assert p["ke"] == ["pmb@u.id"] and p["judul"] == "Kunjungan lapangan ke bendungan"
    assert len(nilai(h, "kb_pembina_baca")) == 1
    gagal(h, "kb_dosen_lain", "Hanya dosen pembimbing")
    gagal(h, "kb_dosen_lain_berkas", "koordinator bidangnya atau admin")   # pembimbing_id null tidak meloloskan dosen lain
    assert nilai(h, "kb_pembina_berkas") == [{"ok": True}]
    gagal(h, "kb_p1_bukan_pendamping", "Hanya dosen pembimbing")
    assert nilai(h, "kb_pembina_setuju") == [{"s": "disetujui"}]
    k = nilai(h, "kb_kabar")
    assert len(k) == 1
    k = k[0]
    assert (k["judul"], k["tanggal"], k["jenis"], k["tempat"], k["status"]) == (
        "Kunjungan lapangan ke bendungan", "2026-11-10", "kunjungan_lapangan", "Bendungan Contoh", "terbit")
    assert k["tautan"] == "https://contoh.id/p/1" and k["tanpa_pelapor"]
    assert k["n_foto"] == 6                                             # 7 foto diunggah; 'lainnya' tidak ikut
    assert k["foto1"] == "https://drive.google.com/file/d/KBF1xxxxxxxx/view"
    assert k["foto6"] == "https://drive.google.com/file/d/KBF6xxxxxxxx/view"
    assert nilai(h, "kb_kabar_id") == [{"cocok": True}]
    assert nilai(h, "kb_riwayat") == [{"oleh": "Pembina (pembina kemahasiswaan/admin)"}]
    gagal(h, "kb_setuju_lagi", "tidak sedang menunggu")
    assert nilai(h, "kb_admin_ulang") == [{"s": "disetujui"}]
    assert nilai(h, "kb_jumlah") == [{"n": 1}]                         # kabar_id: tidak terbit dua kali
    # Dengan dosen pendamping: pendamping sendiri mengesahkan; jenis kosong -> lainnya, tempat/tautan kosong -> null.
    assert nilai(h, "kb2_kirim") == [{"s": "pembimbing"}]
    assert nilai(h, "kb2_pendamping_setuju") == [{"s": "disetujui"}]
    k2 = nilai(h, "kb2_kabar")[0]
    assert (k2["jenis"], k2["tempat"], k2["tautan"], k2["status"], k2["n_foto"]) == ("lainnya", None, None, "terbit", 1)
    assert nilai(h, "kb2_riwayat") == [{"oleh": "Pembimbing Satu"}]


def test_lecturer_extra_links_146(h):
    """Tautan lain di profil dosen (pemilik 2026-11-22): lewat ajuan; hanya admin menyetujui; disimpan rapi."""
    if "tl_ajukan" not in h:
        pytest.skip("146 belum ada")
    nilai(h, "tl_ajukan")
    gagal(h, "tl_setujui_sendiri", "Hanya admin")
    nilai(h, "tl_setujui")
    assert nilai(h, "tl_hasil")[0]["tautan_lain"] == [{"url": "https://heslab.contoh.id", "label": "HESLab"},
                                                      {"url": "https://scholar.contoh.id/u", "label": "Scholar"}]


def test_laboratory_expertise_groups_147(h):
    """Bidang keahlian laboratorium (pemilik 2026-11-22): kode kelompok huruf besar, paling banyak 5; default kosong."""
    if "lb_isi" not in h:
        pytest.skip("147 belum ada")
    assert nilai(h, "lb_isi")[0]["bidang"] == ["AIR", "STR"]
    assert all(r["bidang"] == [] for r in nilai(h, "lb_kosong"))
    gagal(h, "lb_huruf_kecil", "laboratorium_bidang_cek")
    gagal(h, "lb_terlalu_banyak", "laboratorium_bidang_cek")


def test_academic_calendar_148(h):
    """Kalender akademik (pemilik 2026-11-22): diisi admin; tanggal dan kategori diperiksa; dosen membaca; anon tidak."""
    if "kal_isi" not in h:
        pytest.skip("148 belum ada")
    assert nilai(h, "kal_isi") == [{"kategori": "ujian", "tampil": True}]
    gagal(h, "kal_tanggal_terbalik", "check")
    gagal(h, "kal_kategori_salah", "check")
    gagal(h, "kal_dosen_tulis", "row-level security")
    assert nilai(h, "kal_dosen_baca")[0]["n"] == 1
    gagal(h, "kal_anon_baca", "permission denied")


def test_thesis_expertise_group_149(h):
    """Bidang keahlian TA (pemilik 2026-11-22): kode kelompok huruf besar atau kosong."""
    if "bta_isi" not in h:
        pytest.skip("149 belum ada")
    assert nilai(h, "bta_isi") == [{"bidang": "AIR"}]
    assert nilai(h, "bta_kosong") == [{"bidang": None}]
    gagal(h, "bta_salah", "jadwal_ta_bidang_cek")


def test_course_timetable_draft_import_and_kaprodi_approval(h):
    """instal-lengkap.sql (pemilik 2026-11-22): draf hanya untuk penyusun, impor melewati baris salah, hanya Kaprodi
    mengesahkan, dosen bentrok menolak pengesahan, setelah sah jam terkunci tetapi ruang boleh diisi, kelas berkunci tetap."""
    if "j0_ids" not in h:
        pytest.skip("patch 150 tidak ada di skema")
    ids = nilai(h, "j0_ids")[0]
    A, B, C = ids["A"], ids["B"], ids["C"]
    gagal(h, "j0_bukan_pengatur", "disusun admin atau Kaprodi")
    gagal(h, "j0_jam_terbalik", "jam selesai harus sesudah")
    assert nilai(h, "j0_simpan")[0]["r"] == {"kelas_id": A, "hapus": False}
    assert nilai(h, "j0_dosen_draf")[0]["n"] == 0            # draf tidak terlihat dosen biasa
    assert nilai(h, "j0_pengatur_draf")[0]["n"] == 1
    r = nilai(h, "j0_impor")[0]["r"]
    assert (r["masuk"], r["berkunci"], r["dihapus"]) == (2, 0, 0) and len(r["galat"]) == 2
    assert "tidak ada di Genap 2097/2098" in r["galat"][0] and "hari 1-7" in r["galat"][1]
    gagal(h, "j0_sah_admin", "disahkan Kaprodi aktif")
    gagal(h, "j0_sah_bentrok", "Dosen bentrok: Pembimbing Satu (SI201 A dan SI201 B)")
    assert nilai(h, "j0_sah")[0]["r"] == {"sah": True, "kelas": 3}
    assert nilai(h, "j0_dosen_sah")[0]["n"] == 3              # setelah sah semua dosen melihat
    gagal(h, "j0_ubah_jam_sah", "hari dan jam terkunci")
    assert nilai(h, "j0_ubah_ruang_sah")[0]["r"]["hapus"] is False
    assert nilai(h, "j0_ruang")[0]["ruang"] == "R202"
    gagal(h, "j0_impor_sah", "sudah disahkan Kaprodi")
    assert nilai(h, "j0_buka")[0]["r"] == {"sah": False}
    assert nilai(h, "j0_dosen_buka")[0]["n"] == 0
    r = nilai(h, "j0_impor_kunci")[0]["r"]
    assert (r["masuk"], r["berkunci"], r["dihapus"]) == (1, 1, 1)   # C berkunci tetap; B tidak ada di berkas -> dihapus
    assert nilai(h, "j0_sesudah_ganti") == [{"kelas_id": A, "hari": 5, "ruang": "R202"}, {"kelas_id": C, "hari": 2, "ruang": None}]
    assert nilai(h, "j0_hapus")[0]["r"] == {"kelas_id": A, "hapus": True}
    gagal(h, "j0_sah_tanpa_jadwal", "belum berjadwal")
    gagal(h, "j0_anon", "permission denied")
    gagal(h, "j0_anon_sah", "permission denied")
    assert len(nilai(h, "j0_bersih")) == 3


def test_mku_and_faculty_classes_may_have_no_prodi_lecturer(h):
    """instal-lengkap.sql (pemilik 2026-11-22): MKU (universitas) dan MK fakultas boleh tanpa dosen prodi; MK prodi tidak."""
    if "m1_mku_tanpa_dosen" not in h:
        pytest.skip("patch 151 tidak ada di skema")
    assert nilai(h, "m1_mku_tanpa_dosen")[0]["id"]
    assert nilai(h, "m1_fakultas_tanpa_dosen")[0]["id"]
    gagal(h, "m1_prodi_tanpa_dosen", "pilih minimal satu dosen")
    r = nilai(h, "m1_impor_mku")[0]["r"]
    assert r["masuk"] == 1 and len(r["galat"]) == 1 and "pilih minimal satu dosen" in r["galat"][0]
    assert sorted(x["kode_mk"] for x in nilai(h, "m1_bersih")) == ["FAK01", "MKU01", "MKU01"]


def test_meeting_finder_counts_approved_teaching(h):
    """instal-lengkap.sql (pemilik 2026-11-22): mengajar = tidak bisa, hanya jadwal sah, di masa kuliah, bukan libur."""
    if "w2_draf" not in h:
        pytest.skip("patch 152 tidak ada di skema")
    slot = nilai(h, "w2_kunci")[0]["slot"]
    sibuk = lambda l: [(x["slot_id"], x["n"]) for x in nilai(h, l)[0]["r"]["sibuk"]]
    assert sibuk("w2_draf") == []                       # draf belum dihitung
    assert nilai(h, "w2_sahkan")[0]["r"]["sah"] is True
    assert sibuk("w2_sah") == [(slot, 1)]               # setelah sah: Senin slot pertama sibuk
    assert sibuk("w2_libur") == []                      # hari libur
    assert sibuk("w2_luar_masa") == []                  # Kalender akademik punya masa kuliah; Senin pertama di luarnya
    assert sibuk("w2_dalam_masa") == [(slot, 1)]
    assert nilai(h, "w2_masa_fungsi") == [{"dalam": True, "luar": False}]
    gagal(h, "w2_anon", "permission denied")


def test_karya_index_accepts_scopus_without_quartile(h):
    """instal-lengkap.sql (pemilik 2026-11-22): 'scopus' sah, Q1-Q4 tetap sah."""
    d = nilai(h, "ix_scopus")[0]["d"]
    assert "'scopus'::text" in d and "'scopus_q4'::text" in d and "'tidak_terindeks'::text" in d


def test_teaching_per_academic_year_and_dtps_needs_permanent(h):
    """instal-lengkap.sql (pemilik 2026-11-22): centang manual hanya admin; dosen_mengampu = kelas + centang;
    DTPS hanya untuk dosen berkategori tetap (constraint untuk suntingan baru)."""
    if "a4_mengampu" not in h:
        pytest.skip("patch 154 tidak ada di skema")
    gagal(h, "a4_dosen_centang", "row-level security")
    assert nilai(h, "a4_admin_centang") == [{"tahun_akademik": "2095/2096"}]
    gagal(h, "a4_ta_salah", "check constraint")
    assert nilai(h, "a4_mengampu") == [{"sumber": "kelas", "p1": True}, {"sumber": "manual", "p1": False}]
    gagal(h, "a4_anon", "permission denied")
    gagal(h, "a4_dtps_tanpa_tetap", "dosen_dtps_tetap_check")


def test_lecturer_email_optional_and_login_switch(h):
    """instal-lengkap.sql (pemilik 2026-11-22): email boleh kosong kecuali DTPS/admin; boleh_masuk = false
    menutup semua gerbang (me, is_admin, id_dosen_login, email_saya); admin tidak bisa ditutup; email luar tidak berubah."""
    if "m5_p2_ditutup" not in h:
        pytest.skip("patch 155 tidak ada di skema")
    assert nilai(h, "m5_dtt_tanpa_email") == [{"email": None}]
    gagal(h, "m5_dtps_tanpa_email", "dosen_email_wajib_check")
    gagal(h, "m5_email_kosong", "dosen_email_isi_check")
    gagal(h, "m5_admin_ditutup", "dosen_admin_boleh_masuk_check")
    assert nilai(h, "m5_tutup_p2") == [{"boleh_masuk": False}]
    assert nilai(h, "m5_p2_ditutup") == [{"tanpa_me": True, "admin": False, "ditutup": True, "email": None, "tanpa_id": True}]
    assert nilai(h, "m5_p2_baca_dosen") == [{"n": 0}]
    assert nilai(h, "m5_p1_biasa") == [{"tanpa_me": False, "admin": False, "ditutup": False, "email": "p1@u.id", "tanpa_id": False}]
    assert nilai(h, "m5_luar") == [{"tanpa_me": True, "admin": False, "ditutup": False, "email": "luar@x.id", "tanpa_id": True}]
    assert nilai(h, "m5_p2_dibuka") == [{"ada_me": True, "ditutup": False}]


def test_study_leave_period_columns(h):
    """instal-lengkap.sql: tanggal hanya bersama keterangan; selesai tidak sebelum mulai."""
    if "p6_sah" not in h:
        pytest.skip("patch 156 tidak ada di skema")
    gagal(h, "p6_tanggal_tanpa_ket", "dosen_tugas_belajar_tanggal_check")
    gagal(h, "p6_selesai_sebelum_mulai", "dosen_tugas_belajar_periode_check")
    assert nilai(h, "p6_sah") == [{"s": "2027-02-15"}]


def test_leader_is_read_only_everywhere(h):
    """instal-lengkap.sql (pemilik 2026-11-22): pimpinan bukan DTPS membaca tetapi tidak menulis (juga lewat
    RPC); catat_aktif dan catat_kunjungan tetap jalan; pimpinan DTPS dan dosen biasa menulis; semua tabel berpenjaga."""
    if "hb7_status" not in h:
        pytest.skip("patch 157 tidak ada di skema")
    assert nilai(h, "hb7_status") == [{"hb": True, "ada_me": True}]
    assert nilai(h, "hb7_baca") == [{"ada": True}]
    gagal(h, "hb7_karya", "hanya-baca")
    assert nilai(h, "hb7_catat_aktif") is not None
    assert nilai(h, "hb7_kunjungan") is not None
    assert nilai(h, "hb7_dosen_biasa") == [{"judul": "Uji hanya baca"}]
    assert nilai(h, "hb7_admin_ubah") == [{"nama": "Dekan Uji 2"}]
    assert nilai(h, "hb7_pimpinan_dtps") == [{"judul": "Uji hanya baca"}]
    assert nilai(h, "hb7_semua_berpenjaga") == [{"n": 0}]
    # Dekan aktif (Penugasan koordinator): tabel penetapan RPS/ekuivalensi boleh, karya tetap tidak.
    gagal(h, "hb7_padanan_bukan_dekan", "hanya-baca")
    assert "hanya-baca" not in str(h["hb7_padanan_dekan"].get("galat", ""))
    gagal(h, "hb7_dekan_karya", "hanya-baca")
