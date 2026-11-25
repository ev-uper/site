"""supabase_archive.py against an in-memory fake Supabase (no network).

Data is fictitious. Rule under test (config.yaml, owner 2026-10-10):
karya_mahasiswa rows are pruned when karya.tahun < current year - 8;
karya itself is never pruned.
"""
import json
from datetime import date

import pytest

from pathlib import Path
import supabase_archive as sa
from cpl.config import load_config

TODAY = date(2035, 9, 1)          # cutoff year = 2035 - 8 = 2027


class FakeClient:
    def __init__(self, tables):
        self.tables = {t: [dict(r) for r in rows] for t, rows in tables.items()}
        self.deleted = []

    def rows(self, table, order):
        if table not in self.tables:
            raise RuntimeError(f"{table}: HTTP 404")
        return [dict(r) for r in self.tables[table]]

    def delete_in(self, table, column, values):
        values = set(values)
        before = len(self.tables[table])
        self.tables[table] = [r for r in self.tables[table] if str(r[column]) not in values]
        self.deleted.append((table, column, sorted(values)))
        return before - len(self.tables[table])


@pytest.fixture
def cfg():
    return load_config(sa.ROOT / "config.yaml")


def sample():
    return {
        "dosen": [{"id": "d1", "nama": "Dosen Uji", "aktif": True}],
        "karya": [{"id": "k-old", "judul": "Lama", "tahun": 2020},
                  {"id": "k-edge", "judul": "Batas", "tahun": 2027},
                  {"id": "k-new", "judul": "Baru", "tahun": 2033},
                  {"id": "k-noyear", "judul": "Tanpa tahun", "tahun": None}],
        "karya_penulis": [{"karya_id": "k-old", "dosen_id": "d1", "peran": "penulis"}],
        "karya_mahasiswa": [{"karya_id": "k-old", "nim": "9999000001", "nama": "Uji A"},
                            {"karya_id": "k-old", "nim": "9999000002", "nama": "Uji B"},
                            {"karya_id": "k-edge", "nim": "9999000003", "nama": "Uji C"},
                            {"karya_id": "k-new", "nim": "9999000004", "nama": "Uji D"},
                            {"karya_id": "k-noyear", "nim": "9999000005", "nama": "Uji E"}],
        "karya_mitra": [{"karya_id": "k-old", "institusi": "Mitra", "negara": "ID"}],
        # Sitasi per tahun (patch 42, pemilik 2026-11-10).
        "karya_sitasi": [{"karya_id": "k-old", "tahun": 2025, "jumlah": 3, "sumber": "manual"}],
        "pengaturan": [{"kunci": "x", "nilai": "1"}],
        "ref_kelompok_dana": [{"kode": "A", "nama": "Kelompok"}],
        "ref_skema_dana": [{"kode": "S", "nama": "Skema"}],
        # Tabel patch 13-17, 20, 21 (config.yaml): satu baris fiktif tiap tabel.
        **{t: [{"id": 1, "catatan": "uji"}] for t in (
            "dokumen", "karya_bukti", "butir_bukti", "ajuan_hapus", "ajuan_ubah",
            "lkps_mahasiswa_ta", "lkps_kohort_lulusan", "lkps_tracer_lulusan",
            "lkps_kerjasama", "lkps_bkd", "lkps_prestasi_mahasiswa", "ajuan_prestasi", "ajuan_bkd",
            "lkps_publikasi_mahasiswa", "lkps_luaran_mahasiswa",
            "lkps_kepuasan_pengguna", "lkps_bukti", "lkps_vmts", "lkps_prodi_upps",
            "lkps_penggunaan_dana", "lkps_tendik", "lkps_prasarana", "lkps_dokumen_k3l",
            "lkps_fasilitas_k3l", "lkps_spmi_ppepp", "lkps_target_kinerja", "lkps_peta_jalan",
            # Tabel patch 165, sarana menurut standar (LKPS LAMDEPILAR L.1, 2026-11-24).
            "lkps_sarana_standar",
            # Tabel patch 167, pembimbing utama TA (LKPS LAMDEPILAR P.1.2, 2026-11-24).
            "lkps_bimbingan_utama",
            # Tabel patch 169, keuangan A.5 (LKPS LAMDEPILAR, 2026-11-24).
            "lkps_keuangan",
            # Tabel patch 171, mahasiswa per angkatan (LKPS LAMDEPILAR E.1, 2026-11-24).
            "lkps_mahasiswa_angkatan",
            # Tabel patch 50-57 (pemilik 2026-11-11).
            "tautan_ami", "ami_temuan", "potret_skor", "survei", "survei_jawaban",
            "cpl_ringkasan", "cpl_kelas", "cpl_berkas",
            # Tabel patch 58, pelacak hibah (pemilik 2026-11-11).
            "hibah_panggilan", "hibah_ajuan",
            # Tabel patch 61, daftar keahlian baku (pemilik 2026-11-12).
            "ref_bidang_keahlian", "ref_topik_keahlian",
            # Tabel patch 62, rapat dan notulen (pemilik 2026-11-12).
            "rapat", "rapat_peserta", "rapat_tindak",
            # Tabel patch 64, kalender kegiatan (pemilik 2026-11-12).
            "kegiatan")},
        "templat_email": [{"kunci": "karya", "subjek": "s", "isi": "i"}],
        "hibah_tim": [{"ajuan_id": "a", "dosen_id": "d", "peran": "ketua"}],
        # Tabel patch 162, dosen yang ditugasi per kegiatan (Kalender saya, pemilik 2026-11-24).
        "kegiatan_dosen": [{"kegiatan_id": 1, "dosen_id": "d"}],
        # Tabel patch 163, klaim insentif publikasi (pemilik 2026-11-24).
        "insentif_pengajuan": [{"id": 1, "judul": "Pengajuan insentif uji", "tanggal": "2026-11-24"}],
        "insentif_publikasi": [{"id": 1, "karya_id": "k", "pengklaim_id": "d", "status": "diajukan", "pengajuan_id": 1}],
        # Tabel patch 66, target kinerja per dosen (pemilik 2026-11-12).
        "target_baku": [{"tahun": 2026, "jabatan": "lektor", "indikator": "publikasi", "target": 2}],
        "target_dosen": [{"tahun": 2026, "dosen_id": "d", "indikator": "publikasi", "target": 1}],
        "spmi_standar": [{"id": 1, "kode": "A.01.01", "pernyataan": "WRA memastikan kriteria CPL"}],
        "spmi_capaian": [{"standar_id": 1, "tahun_ts": 2027, "target": "Tersedia"}],
        "spmi_standar_revisi": [{"id": 1, "standar_id": 1, "tanggal": "2026-03-10", "perubahan": "target naik"}],
        "evaluasi_mk": [{"id": 1, "tahun_akademik": "2025/2026", "semester": "Ganjil", "kode_mk": "SI2101", "dosen_id": "d", "edom": 3.1}],
        "evaluasi_tindak": [{"id": 1, "evaluasi_id": 1, "masalah": "EDOM rendah", "rencana": "Revisi RPS"}],
        "ref_mata_kuliah": [{"id": 1, "kurikulum": "K26", "kode": "SI0001", "nama": "Mata kuliah uji"}],
        # Tabel patch 71, CPL per kurikulum (pemilik 2026-11-13).
        "ref_cpl": [{"id": 1, "kurikulum": "K26", "kode": "A", "rumusan": "uji"}],
        "ref_mk_cpl": [{"id": 1, "kurikulum": "K26", "kode_mk": "SI0001", "cpl": "A", "bobot": None}],
        "ref_cpl_korelasi": [{"id": 1, "kurikulum_asal": "K21", "cpl_asal": "a", "kurikulum_tujuan": "K26",
                              "cpl_tujuan": "A", "tingkat": "setara", "status": "usulan"}],
        # Tabel patch 77-78, wilayah mahasiswa (pemilik 2026-11-16).
        "pengumuman_mahasiswa": [{"id": 1, "judul": "Uji", "isi": "", "berlaku_sampai": None}],
        "masukan_mahasiswa": [{"id": 1, "jenis": "tanya", "isi": "Pertanyaan uji", "status": "baru"}],
        "tanya_jawab": [{"id": 1, "topik": "Umum", "pertanyaan": "Uji?", "jawaban": "Ya.", "urutan": 100, "tampil": True}],
        # Tabel patch 79, profil lulusan (pemilik 2026-11-16).
        "ref_profil_lulusan": [{"id": 1, "kurikulum": "K26", "kode": "PL1", "nama": "Perencana", "cpl": "A, B"}],
        # Tabel patch 81, kabar kegiatan (pemilik 2026-11-16).
        "kabar_kegiatan": [{"id": 1, "judul": "Kuliah tamu", "tanggal": "2030-01-01", "ringkasan": "x" * 20, "status": "terbit"}],
        # Tabel patch 82, laboratorium (pemilik 2026-11-16).
        "laboratorium": [{"id": 1, "nama": "Laboratorium Contoh", "ringkasan": "x" * 20}],
        # Tabel patch 84, profil prodi (pemilik 2026-11-16).
        "profil_prodi": [{"id": 1, "sejarah": "Berdiri 2016."}],
        "pengelola_prodi": [{"id": 1, "jabatan": "Ketua Program Studi", "nama": "Contoh"}],
        # Tabel patch 90, pengajuan KP/lomba mahasiswa (pemilik 2026-11-17); contoh tanpa tanggal.
        "pengajuan_mahasiswa": [{"id": 1, "jenis": "kp", "nim": "100000001", "nama": "Uji", "status": "draf"}],
        "pengajuan_berkas": [{"id": 1, "pengajuan_id": 1, "jenis": "surat_permohonan", "url": "https://drive.google.com/file/d/x"}],
        "pengajuan_riwayat": [{"id": 1, "pengajuan_id": 1, "status": "draf", "oleh": "mahasiswa"}],
        # Tabel patch 94, jadwal seminar/sidang TA (pemilik 2026-11-17).
        "jadwal_ta": [{"id": 1, "tahap": "sidang_akhir", "nama_mahasiswa": "Uji", "judul": "Uji", "tanggal": "2035-01-02"}],
        # Tabel patch 97, koordinator prodi (pemilik 2026-11-17).
        "koordinator": [{"id": 1, "dosen_id": "d1", "jabatan": "koordinator_ta", "mulai": "2035-01-01"}],
        # Patch 102 (OBE O2): struktur CPMK per MK dan riwayatnya.
        "mk_struktur": [{"kurikulum": "K26", "kode_mk": "SI101", "data": {"versi": "1", "cpmk": [], "sub": [], "asesmen": [], "bobot": {}}}],
        "mk_struktur_riwayat": [{"id": 1, "kurikulum": "K26", "kode_mk": "SI101", "data": {"versi": "1"}}],
        # Patch 103 (OBE O3): berkas portofolio MK.
        "portofolio_berkas": [{"id": 1, "tahun_akademik": "2034/2035", "semester": "Ganjil", "kurikulum": "K26", "kode_mk": "SI101",
                               "komponen": "soal", "asesmen": "UTS", "url": "https://drive.google.com/file/d/P/view"}],
        # Patch 104: email alternatif mahasiswa.
        "mhs_email_alt": [{"nim": "9999000001", "email": "alt@contoh.id", "oleh": "mahasiswa"}],
        "mhs_email_alt_riwayat": [{"id": 1, "nim": "9999000001", "email": "alt@contoh.id", "aksi": "aktif", "oleh": "mahasiswa"}],
        # Patch 105: keputusan instansi KP.
        "kp_instansi_keputusan": [{"kunci": "pt contoh", "nama": "PT Contoh", "keputusan": "usul"}],
        # Patch 106: surat pengantar KP ditolak instansi.
        "kp_tolak_instansi": [{"id": 1, "pengajuan_id": 1, "instansi": "PT Contoh", "alasan": "kuota penuh"}],
        "kp_kuota": [{"id": 1, "ts": 2027, "dosen_id": None, "kuota": 5}],
        "ta_kk_dekat": [{"kk_a": "GEO", "kk_b": "STR"}],
        "ta_kuota": [{"id": 1, "ts": 2027, "dosen_id": None, "kuota": 4, "semester": "Ganjil"}],   # 180: per semester
        # Patch 172: pengecualian urutan tahap TA (pemilik 2026-11-25).
        "ta_kecuali_urutan": [{"id": 1, "nim": "104199001", "tahap": "sidang_akhir", "alasan": "Seminar kemajuan sebelum situs"}],
        "ta_rubrik": [{"id": 1, "tahap": "seminar_proposal", "versi": 1, "komponen": [], "bobot_penguji": 60, "batas_lulus": 55}],
        "ta_nilai": [{"id": 1, "jadwal_id": 1, "rubrik_id": 1, "peran": "penguji", "penilai_nama": "Penguji Contoh", "total": 80}],
        "ta_berkas": [{"tahap": "sidang_akhir", "kode": "ta_transkrip", "label": "Transkrip atau KHS", "wajib": True, "urut": 3, "aktif": True}],
        "ta_bimbingan": [{"id": 1, "nim": "104199175", "nama": "Contoh", "tanggal": "2026-11-20", "cara": "daring", "topik": "Bab 3 metode", "status": "dikonfirmasi"}],
        "ta_syarat_bimbingan": [{"tahap": "sidang_akhir", "minimal": 4}],
        "ta_arsip": [{"nim": "104199178", "nama": "Contoh", "url": "https://drive.google.com/file/d/X/view"}],
        # Patch 122: daftar berkas yudisium.
        "yudisium_berkas": [{"kode": "yud_transkrip", "label": "Transkrip", "wajib": True, "urut": 3, "aktif": True}],
        # Patch 126: peringatan keamanan.
        "peringatan_keamanan": [{"id": 1, "jenis": "peran", "oleh": "admin@u.id", "rinci": "Peran berubah."}],
        # Patch 125: status pekerjaan otomatis.
        "status_sistem": [{"kunci": "cadangan", "waktu": "2026-11-20T01:40:00Z", "ok": True, "isi": {}}],
        "mk_rps": [{"kurikulum": "K26", "kode_mk": "13301", "data": {"versi": "1"}, "status": "draf"}],
        "mk_rps_riwayat": [{"id": 1, "kurikulum": "K26", "kode_mk": "13301", "data": {"versi": "1"}}],
        "mk_rps_pengesahan": [{"id": 1, "kurikulum": "K26", "kode_mk": "13301", "aksi": "ajukan"}],
        "mk_rps_ttd": [{"id": 1, "kurikulum": "K26", "kode_mk": "13301", "url": "https://drive.google.com/file/d/X/view"}],
        # Patch 115: tinjauan RPS dan padanan MK.
        "ref_mk_padanan": [{"id": 1, "kurikulum_lama": "K21", "kode_lama": "10001", "kurikulum_baru": "K26", "kode_baru": "13301"}],
        "mk_rps_tinjauan": [{"id": 1, "kurikulum": "K21", "kode_mk": "10001", "tahun_akademik": "2025/2026", "semester": "Genap", "data": {"versi": "1"}}],
        "mk_rps_tinjauan_log": [{"id": 1, "tinjauan_id": 1, "aksi": "ajukan"}],
        "mk_rps_review": [{"id": 1, "kurikulum": "K26", "kode_mk": "13301", "reviewer_id": "00000000-0000-0000-0000-000000000001"}],
        "mk_silabus": [{"kurikulum": "K26", "kode_mk": "13301", "data": {"versi": "1"}, "status": "draf"}],
        "mk_silabus_log": [{"id": 1, "kurikulum": "K26", "kode_mk": "13301", "aksi": "impor"}],
        "jadwal_slot": [{"id": 1, "urutan": 1, "label": "Jam 1", "mulai": "07:30", "selesai": "09:10"}],
        "jadwal_hari": [{"hari": 1}],
        "dosen_berhalangan": [{"id": 1, "dosen_id": "00000000-0000-0000-0000-000000000001", "tahun_akademik": "2026/2027",
                               "semester": "Ganjil", "hari": 1, "slot_id": 1}],
        "dosen_berhalangan_tgl": [{"id": 1, "dosen_id": "00000000-0000-0000-0000-000000000001", "tanggal": "2026-12-01"}],
        "dosen_berhalangan_rentang": [{"id": 1, "dosen_id": "00000000-0000-0000-0000-000000000001", "mulai": "2026-12-01",
                                       "selesai": "2027-01-15", "hari": [2, 4], "slot_ids": [1]}],
        "kelas_kuliah": [{"id": 1, "tahun_akademik": "2026/2027", "semester": "Ganjil", "kurikulum": "K26", "kode_mk": "A", "kelas": "A"}],
        "kelas_dosen": [{"kelas_id": 1, "dosen_id": "00000000-0000-0000-0000-000000000001", "peran": "koordinator"}],
        "hari_libur": [{"tanggal": "2026-12-25", "nama": "Hari Raya Natal", "jenis": "nasional"}],
        "berhalangan_konfirmasi": [{"dosen_id": "00000000-0000-0000-0000-000000000001", "tahun_akademik": "2026/2027", "semester": "Genap"}],
        "mk_padanan_sah": [{"kurikulum_lama": "K21", "kurikulum_baru": "K26", "status": "draf", "revisi": 0}],
        "mk_padanan_sah_log": [{"id": 1, "kurikulum_lama": "K21", "kurikulum_baru": "K26", "aksi": "sahkan"}],
        "kunjungan_publik": [{"tanggal": "2026-11-22", "halaman": "calon-mahasiswa.html", "rujukan": "instagram", "peristiwa": "lihat", "n": 3}],
        "testimoni": [{"id": 1, "nama": "Contoh Alumni", "peran": "alumni", "kutipan": "Kutipan contoh untuk uji cadangan.",
                       "persetujuan_tanggal": "2026-12-01", "tampil": True}],
        "kalender_akademik": [{"id": 1, "semester": "Ganjil 2026/2027", "kegiatan": "Ujian akhir semester", "kategori": "ujian",
                               "mulai": "2026-12-14", "selesai": "2026-12-22", "tampil": True}],
        "jadwal_kuliah": [{"kelas_id": 1, "hari": 1, "mulai": "07:00:00", "selesai": "09:30:00", "ruang": "R101", "kunci": False}],
        "jadwal_kuliah_sah": [{"tahun_akademik": "2026/2027", "semester": "Ganjil", "sah_oleh": "kaprodi@contoh.ac.id"}],
        "dosen_ampu_ts": [{"dosen_id": "00000000-0000-0000-0000-000000000001", "tahun_akademik": "2026/2027"}],
        "ref_kata_visi": [{"kata": "uji"}],
        "led_narasi": [{"kunci": "b1|tambahan", "nilai": "uji"}],
        "led_penugasan": [{"kelompok": "C1", "email": "a@contoh.ac.id"}],
        "led_tim": [{"id": 1, "urutan": 1, "jenis": "nondosen", "nama": "Uji"}],
        "ref_tema_peta_jalan": [{"id": 1, "nama": "Tema uji"}],
    }


def test_config_section_valid(cfg):
    assert sa.validate_config(cfg) == []


def test_backup_writes_every_table(tmp_path, cfg):
    counts = sa.backup(FakeClient(sample()), cfg, root=tmp_path)
    assert set(counts) == set(cfg["supabase"]["tables"])
    text = (tmp_path / "cadangan" / "karya_mahasiswa.csv").read_text(encoding="utf-8")
    assert text.splitlines()[0] == "karya_id,nim,nama" and len(text.splitlines()) == 6


def test_backup_reports_missing_table(tmp_path, cfg):
    data = sample()
    del data["pengaturan"]
    with pytest.raises(RuntimeError, match="pengaturan"):
        sa.backup(FakeClient(data), cfg, root=tmp_path)
    assert (tmp_path / "cadangan" / "karya.csv").is_file()   # other tables still written


def test_archive_manifest_and_plan(tmp_path, cfg):
    folder = sa.archive(FakeClient(sample()), cfg, root=tmp_path, today=TODAY)
    m = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert m["tables"]["karya"]["rows"] == 4
    assert m["retention"]["karya_mahasiswa"] == {"cutoff_year": 2027, "years": 8, "key": "karya_id",
                                                 "rows": 2, "key_count": 1}
    # Data pribadi patch 54/62/78 (pemilik 2026-11-16): 5 tahun; contoh baris tanpa tanggal, 0 baris.
    assert set(m["retention"]) == set(cfg["supabase"]["retention"])
    assert all(m["retention"][t]["cutoff_year"] == 2030 and m["retention"][t]["rows"] == 0
               for t in ("masukan_mahasiswa", "survei_jawaban", "rapat_peserta", "pengajuan_mahasiswa"))
    assert sa.verify_archive(folder)["created"] == "2035-09-01"
    with pytest.raises(RuntimeError, match="sudah ada"):
        sa.archive(FakeClient(sample()), cfg, root=tmp_path, today=TODAY)


def test_prune_dry_run_deletes_nothing(tmp_path, cfg):
    client = FakeClient(sample())
    folder = sa.archive(client, cfg, root=tmp_path, today=TODAY)
    assert sa.prune(client, cfg, folder, execute=False, today=TODAY) == {t: 0 for t in cfg["supabase"]["retention"]}
    assert client.deleted == [] and len(client.tables["karya_mahasiswa"]) == 5


def test_prune_deletes_only_old_rows(tmp_path, cfg):
    client = FakeClient(sample())
    folder = sa.archive(client, cfg, root=tmp_path, today=TODAY)
    done = sa.prune(client, cfg, folder, execute=True, today=TODAY)
    # Contoh baris tabel lain tanpa tanggal: tahun tak diketahui, tidak pernah dihapus.
    assert done == {t: 0 for t in cfg["supabase"]["retention"]} | {"karya_mahasiswa": 2}
    assert {r["karya_id"] for r in client.tables["karya_mahasiswa"]} == {"k-edge", "k-new", "k-noyear"}
    assert len(client.tables["karya"]) == 4                     # karya dosen never pruned
    assert (folder / "hapus_2035-09-01.json").is_file()


def test_prune_refuses_tampered_archive(tmp_path, cfg):
    client = FakeClient(sample())
    folder = sa.archive(client, cfg, root=tmp_path, today=TODAY)
    (folder / "karya_mahasiswa.csv").write_text("karya_id,nim,nama\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="tidak utuh"):
        sa.prune(client, cfg, folder, execute=True, today=TODAY)
    assert client.deleted == []


def test_prune_refuses_old_archive(tmp_path, cfg):
    client = FakeClient(sample())
    folder = sa.archive(client, cfg, root=tmp_path, today=TODAY)
    later = date(2035, 12, 1)
    with pytest.raises(RuntimeError, match="berumur"):
        sa.prune(client, cfg, folder, execute=True, today=later)
    assert client.deleted == []


def test_prune_refuses_rows_not_in_archive(tmp_path, cfg):
    client = FakeClient(sample())
    folder = sa.archive(client, cfg, root=tmp_path, today=TODAY)
    client.tables["karya_mahasiswa"].append({"karya_id": "k-old", "nim": "9999000009", "nama": "Baru masuk"})
    with pytest.raises(RuntimeError, match="belum ada di arsip"):
        sa.prune(client, cfg, folder, execute=True, today=TODAY)
    assert client.deleted == []


def test_rest_paging_and_duplicates(monkeypatch):
    rest = sa.Rest("https://example.supabase.co", "test-key")
    data = [{"id": i} for i in range(2500)]

    def fake_get(table, params, start, end):
        return data[start:end + 1], len(data)
    monkeypatch.setattr(rest, "_get", fake_get)
    assert len(rest.rows("karya", "id")) == 2500

    dup = [{"id": 1}, {"id": 1}]
    monkeypatch.setattr(rest, "_get", lambda t, p, s, e: (dup[s:e + 1], 2))
    with pytest.raises(RuntimeError, match="kembar"):
        rest.rows("karya", "id")


def test_rest_count_mismatch(monkeypatch):
    rest = sa.Rest("https://example.supabase.co", "test-key")
    monkeypatch.setattr(rest, "_get", lambda t, p, s, e: ([{"id": 1}], 5))
    with pytest.raises(RuntimeError, match="melaporkan 5"):
        rest.rows("karya", "id")


def test_secrets_from_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-key")
    assert sa.read_secrets(root=tmp_path)["SUPABASE_URL"] == "https://example.supabase.co"
    monkeypatch.delenv("SUPABASE_SERVICE_KEY")
    with pytest.raises(SystemExit, match="SUPABASE_SERVICE_KEY"):
        sa.read_secrets(root=tmp_path)


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


def _send_root(tmp_path, url="https://script.google.com/macros/s/x/exec"):
    (tmp_path / "site").mkdir()
    (tmp_path / "site" / "config.js").write_text(f"window.UPLOAD_URL    = '{url}';\n", encoding="utf-8")
    folder = tmp_path / "cadangan"
    folder.mkdir()
    (folder / "dosen.csv").write_text("id,email\n1,a@x.id\n", encoding="utf-8")
    return folder


def test_send_posts_one_zip_with_the_token(tmp_path, monkeypatch):
    import base64, io, zipfile
    folder = _send_root(tmp_path)
    monkeypatch.setenv("CADANGAN_TOKEN", "t" * 40)
    sent = {}

    def post(url, json, timeout):
        sent.update(json, url=url)
        return FakeResponse({"ok": True, "name": "x.zip"})

    sa.send(folder, root=tmp_path, post=post)
    assert sent["url"].endswith("/exec") and sent["kind"] == "cadangan"
    assert sent["cadangan_token"] == "t" * 40 and sent["name"] == "cadangan.zip"
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(sent["data"]))) as z:
        assert z.read("dosen.csv").startswith(b"id,email")


def test_send_fails_loudly_when_refused(tmp_path, monkeypatch):
    folder = _send_root(tmp_path)
    monkeypatch.setenv("CADANGAN_TOKEN", "salah")
    with pytest.raises(RuntimeError, match="Token cadangan salah"):
        sa.send(folder, root=tmp_path,
                post=lambda *a, **k: FakeResponse({"ok": False, "error": "Token cadangan salah."}))


def test_send_needs_url_and_token(tmp_path, monkeypatch):
    folder = _send_root(tmp_path, url="")
    monkeypatch.setenv("CADANGAN_TOKEN", "t")
    with pytest.raises(RuntimeError, match="UPLOAD_URL"):
        sa.send(folder, root=tmp_path, post=None)
    (tmp_path / "site" / "config.js").write_text("window.UPLOAD_URL = 'https://a/exec';", encoding="utf-8")
    monkeypatch.delenv("CADANGAN_TOKEN")
    with pytest.raises(RuntimeError, match="CADANGAN_TOKEN"):
        sa.send(folder, root=tmp_path, post=None)


def test_rehearsal_backup_needs_test_project_keys(tmp_path, monkeypatch, capsys):
    """Gladi pemulihan (2026-11-12): backup --folder must not fall back to rahasia.env (the main project),
    otherwise 'bandingkan' compares the main project with its own backup and proves nothing."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    dipanggil = []
    monkeypatch.setattr(sa, "read_secrets", lambda *a, **k: dipanggil.append(1) or {})
    assert sa.main(["backup", "--folder", str(tmp_path / "uji-balik")]) == 2
    assert not dipanggil and "proyek uji" in capsys.readouterr().err

    monkeypatch.setenv("SUPABASE_URL", "https://proyekuji.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "kunci-uji")
    monkeypatch.setattr(sa, "read_secrets", lambda *a, **k: {"SUPABASE_URL": "https://proyekuji.supabase.co", "SUPABASE_SERVICE_KEY": "kunci-uji"})
    monkeypatch.setattr(sa, "backup", lambda client, cfg, folder=None: None)
    assert sa.main(["backup", "--folder", str(tmp_path / "uji-balik")]) == 0
    keluar = capsys.readouterr().out
    assert "proyek: proyekuji.supabase.co (variabel lingkungan)" in keluar and "kunci-uji" not in keluar


def test_retention_personal_data_by_date_and_filter(cfg):
    """Patch 54/62/78 personal data, 5 years by calendar year of a timestamp column
    (owner 2026-11-16): cutoff 2035 - 5 = 2030. Anonymous survey answers and lecturer
    attendance are kept; a row without a date is never deleted."""
    data = sample()
    data["masukan_mahasiswa"] = [{"id": 1, "dikirim": "2029-12-31T23:00:00+00:00"},
                                 {"id": 2, "dikirim": "2030-01-01T00:00:00+00:00"},
                                 {"id": 3, "dikirim": None}]
    data["survei_jawaban"] = [{"id": 1, "diisi": "2028-05-01T00:00:00+00:00", "nama": "Uji", "nim": None, "email": None},
                              {"id": 2, "diisi": "2028-05-01T00:00:00+00:00", "nama": None, "nim": "", "email": None},
                              {"id": 3, "diisi": "2033-05-01T00:00:00+00:00", "nama": None, "nim": None, "email": "a@b.id"}]
    data["rapat_peserta"] = [{"id": 1, "waktu": "2027-01-01T00:00:00+00:00", "dosen_id": None, "nama": "Tamu"},
                             {"id": 2, "waktu": "2027-01-01T00:00:00+00:00", "dosen_id": "d1", "nama": "Dosen Uji"}]
    # Pengajuan KP/lomba (patch 90, pemilik 2026-11-17): 5 tahun sejak dibuat.
    data["pengajuan_mahasiswa"] = [{"id": 1, "dibuat": "2029-06-01T00:00:00+00:00"},
                                   {"id": 2, "dibuat": "2031-06-01T00:00:00+00:00"}]
    plan = sa.retention_plan(cfg, data, TODAY)
    assert plan["pengajuan_mahasiswa"]["key_values"] == ["1"]
    assert plan["masukan_mahasiswa"]["key_values"] == ["1"]
    assert plan["survei_jawaban"]["key_values"] == ["1"]
    assert plan["rapat_peserta"]["key_values"] == ["1"]
    assert plan["karya_mahasiswa"]["cutoff_year"] == 2027 and plan["masukan_mahasiswa"]["cutoff_year"] == 2030


def test_retention_filter_must_be_column_list(cfg):
    bad = json.loads(json.dumps(cfg))
    bad["supabase"]["retention"]["survei_jawaban"]["only_if_any"] = "nama"
    assert any("only_if_any" in e for e in sa.validate_config(bad))


def test_patches_run_in_numeric_order():
    # 2026-11-17: 100-*.sql jalan sebelum 11-*.sql karena urutan abjad.
    xs = ["supabase/11-b.sql", "supabase/100-a.sql", "supabase/09-c.sql", "supabase/99-d.sql", "supabase/101-e.sql"]
    assert [Path(p).name for p in sa.urut_patch(xs)] == ["09-c.sql", "11-b.sql", "99-d.sql", "100-a.sql", "101-e.sql"]
