"""Halaman statis dosen, sitemap.xml, robots.txt (halaman_publik.py, pemilik 2026-11-16)."""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import bangun
import halaman_publik as hp

ROOT = Path(__file__).resolve().parents[1]
D = {
    "prodi": "Teknik Contoh", "institusi": "Universitas Contoh", "diperbarui": "1 Januari 2030",
    "dosen": [{"nama": "Ani Lestari", "slug": "ani-lestari", "sinta_id": "123", "orcid": "0000-0001",
               "topik_keahlian": ["HYD01"]},
              {"nama": "Budi <Santoso>", "slug": "budi-santoso"}],
    "keahlian_baku": {"bidang": [{"kode": "HYD", "nama": "Hidrologi"}],
                      "topik": [{"kode": "HYD01", "bidang": "HYD", "nama": "Banjir"}]},
    "publikasi": [{"judul": "Banjir & curah hujan", "tahun": 2029, "tingkat": "internasional", "doi": "10.1/x",
                   "terbitan": "Jurnal A", "volume": "3", "nomor": "2", "penulis": [
                       {"nama": "Ani Lestari", "slug": "ani-lestari"}, {"nama": "Budi <Santoso>", "slug": "budi-santoso"}]},
                  {"judul": "Lain", "tahun": 2028, "penulis": [{"nama": "Budi <Santoso>", "slug": "budi-santoso"}]}],
    "kegiatan": [{"judul": "PkM desa", "tahun": 2029, "kategori": "pkm", "skema": "Hibah",
                  "penulis": [{"nama": "Ani Lestari", "slug": "ani-lestari", "peran": "ketua"}],
                  "mitra": [{"nama": "Desa A"}], "mahasiswa": 3}],
    "rekognisi": [{"dosen": "Ani Lestari", "bentuk": "invited_speaker", "nama_kegiatan": "Seminar X",
                   "tingkat": "internasional", "tahun": 2029}],
    "luaran_dosen": [],
}


def test_lecturer_page_has_text_links_and_metadata():
    h = hp.halaman_dosen(D, D["dosen"][0], "https://contoh.ac.id/situs", "v1", [])
    assert "<h1>Ani Lestari</h1>" in h and "Banjir &amp; curah hujan" in h
    assert '<link rel="canonical" href="https://contoh.ac.id/situs/dosen/ani-lestari.html">' in h
    assert '"@type": "Person"' in h and hp.GENERATOR in h
    assert "<b>Ani Lestari</b>" in h and 'href="budi-santoso.html">Budi &lt;Santoso&gt;</a>' in h
    assert "https://doi.org/10.1/x" in h and "Vol. 3 No. 2" in h
    assert "PkM desa" in h and "Ketua" in h and "Mitra: Desa A" in h and "Seminar X" in h
    assert "Lain" not in h.split("<main")[1]          # karya dosen lain tidak ikut
    assert "Banjir</span>" in h                       # topik keahlian baku
    assert "../tema.css?v=v1" in h


def test_lecturer_page_shows_nip_only_when_filled():
    """NIP (instal-lengkap.sql, pemilik 2026-11-17): mahasiswa memerlukannya; kosong = tidak tampil."""
    h = hp.halaman_dosen(D, {**D["dosen"][0], "nip": "116<0>21"}, "", "v1", [])
    assert '<div class="bidang nip">NIP 116&lt;0&gt;21</div>' in h
    assert "NIP" not in hp.halaman_dosen(D, D["dosen"][0], "", "v1", []).split("<main")[0]


def test_lecturer_page_shows_name_with_titles_when_filled():
    """Nama dengan gelar (pemilik 2026-11-19): tampil di judul, h1, dan jejak; karya tetap dicocokkan
    dengan nama biasa. Judul tab: "<nama> — Dosen Program Studi <prodi> <institusi>" tanpa koma."""
    h = hp.halaman_dosen(D, {**D["dosen"][0], "nama_gelar": "Dr. Ani Lestari, S.T., M.T."}, "", "v1", [])
    assert "<h1>Dr. Ani Lestari, S.T., M.T.</h1>" in h
    assert "<title>Dr. Ani Lestari, S.T., M.T. — Dosen Program Studi Teknik Contoh Universitas Contoh</title>" in h
    assert "› Dr. Ani Lestari, S.T., M.T.</nav>" in h and "Seminar X" in h
    assert "<title>Ani Lestari — Dosen Program Studi" in hp.halaman_dosen(D, D["dosen"][0], "", "v1", [])


def test_nip_check_matches_patch_89():
    sql = (ROOT / "supabase" / "instal-lengkap.sql").read_text(encoding="utf-8")
    pola = re.search(r"nip ~ '([^']+)'", sql).group(1)
    js = (ROOT / "site" / "kelola-dosen.html").read_text(encoding="utf-8")
    assert pola in js                                  # pemeriksaan formulir sama dengan aturan basis data
    for nip, sah in [("116021090", True), ("1990 0101 2020", True), ("UP-123/A", True), ("1", False), ("-12", False)]:
        assert bool(re.fullmatch(pola, nip)) is sah


def test_name_is_escaped_and_no_canonical_without_base_url():
    h = hp.halaman_dosen(D, D["dosen"][1], "", "", [])
    assert "<h1>Budi &lt;Santoso&gt;</h1>" in h and "canonical" not in h


def test_write_pages_sitemap_and_remove_only_own_stale_pages(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text('<link href="tema.css?v=2030-01-01-abc">', encoding="utf-8")
    (site / "config.js").write_text("window.FITUR_MATI = ['sdgs'];", encoding="utf-8")
    situs = tmp_path / "situs"
    (situs / "dosen").mkdir(parents=True)
    (situs / "dosen" / "lama.html").write_text(f'<meta name="generator" content="{hp.GENERATOR}">', encoding="utf-8")
    (situs / "dosen" / "tangan.html").write_text("<p>dibuat tangan</p>", encoding="utf-8")
    hasil = hp.tulis_halaman_publik(situs, D, {"public_site": {"base_url": "https://contoh.ac.id"}}, site)
    assert hasil == {"dosen": 2, "dibuang": 1, "sitemap": True, "alamat": "https://contoh.ac.id"}
    assert not (situs / "dosen" / "lama.html").exists() and (situs / "dosen" / "tangan.html").exists()
    assert "tema.css?v=2030-01-01-abc" in (situs / "dosen" / "ani-lestari.html").read_text(encoding="utf-8")
    loc = [el.text for u in ET.parse(situs / "sitemap.xml").getroot() for el in u]
    assert "https://contoh.ac.id/dosen/ani-lestari.html" in loc and "https://contoh.ac.id/" in loc
    assert "https://contoh.ac.id/sdgs.html" not in loc       # modul dimatikan
    assert "Sitemap: https://contoh.ac.id/sitemap.xml" in (situs / "robots.txt").read_text(encoding="utf-8")


def test_no_sitemap_without_base_url(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("", encoding="utf-8")
    hasil = hp.tulis_halaman_publik(tmp_path / "situs", D, {"public_site": {"base_url": None}}, site)
    assert hasil["sitemap"] is False and not (tmp_path / "situs" / "sitemap.xml").exists()


def test_public_site_config_is_valid_and_validated():
    from cpl.config import load_config
    cfg = load_config(ROOT / "config.yaml")
    assert bangun.validasi_situs_publik(cfg) == []
    salah = {"public_site": {"base_url": "http://x/", "tagline": "", "contact": {"email": "bukan"},
                             "social": {"instagram": "instagram.com/x"}, "admission_url": "ftp://x"}}
    galat = " ".join(bangun.validasi_situs_publik(salah))
    for k in ("base_url", "tagline", "contact.email", "social.instagram", "admission_url"):
        assert f"public_site.{k}" in galat


def test_homepage_content_only_filled_keys():
    assert bangun.situs_publik({"public_site": {"tagline": None, "contact": {"email": None}}}) == {}
    s = bangun.situs_publik({"public_site": {"tagline": " Unggul ", "contact": {"phone": "021", "email": None},
                                             "social": {"instagram": "https://instagram.com/x"}}})
    assert s == {"tagline": "Unggul", "kontak": {"phone": "021"}, "sosial": {"instagram": "https://instagram.com/x"}}


def test_cname_overrides_base_url_and_site_map_page(tmp_path):
    """Domain change through GitHub Pages custom domain (CNAME) is followed by itself (owner 2026-11-16)."""
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("", encoding="utf-8")
    situs = tmp_path / "situs"
    situs.mkdir()
    (situs / "CNAME").write_text("sipil.contoh.ac.id\n", encoding="utf-8")
    hasil = hp.tulis_halaman_publik(situs, D, {"public_site": {"base_url": "https://lama.github.io/x"}}, site)
    assert hasil["alamat"] == "https://sipil.contoh.ac.id"
    peta = (situs / "sitemap.xml").read_text(encoding="utf-8")
    assert "https://sipil.contoh.ac.id/dosen/ani-lestari.html" in peta and "lama.github.io" not in peta
    assert "https://sipil.contoh.ac.id/peta-situs.html" in peta
    halaman = (situs / "peta-situs.html").read_text(encoding="utf-8")
    assert 'href="dosen/ani-lestari.html"' in halaman and "Budi &lt;Santoso&gt;" in halaman
    assert 'canonical" href="https://sipil.contoh.ac.id/dosen/ani-lestari.html"' in (situs / "dosen" / "ani-lestari.html").read_text(encoding="utf-8")


def test_lecturer_photo_used_when_present():
    d = dict(D["dosen"][0], foto="foto-dosen/ani-lestari.jpg")
    h = hp.halaman_dosen(D, d, "", "v1", [])
    assert 'src="../foto-dosen/ani-lestari.jpg?v=v1"' in h and 'class="avatar"' not in h.replace('class="avatar foto"', "")


def test_homepage_lists_and_links_are_validated():
    salah = {"public_site": {"careers": ["", "y"], "laboratories": "Lab A",
                             "admission_whatsapp": "wa.me/62", "news_url": "http://x"}}
    galat = " ".join(bangun.validasi_situs_publik(salah))
    for k in ("careers", "laboratories", "admission_whatsapp", "news_url"):
        assert f"public_site.{k}" in galat


# ---------- Prestasi mahasiswa di situs publik (pemilik 2026-11-16, patch 80) ----------
FID1, FID2, FID3 = "A" * 25, "B" * 25, "C" * 25
BARIS = [
    {"id": 1, "nama_mahasiswa": "Sari Dewi; Rudi Hartono", "nim": "105", "nama_kegiatan": "Lomba Jembatan", "tingkat": "nasional",
     "capaian": "Juara 1", "tahun": 2030, "bulan": 5, "pembimbing": ["0011"], "status": "terverifikasi",
     "tampil_nama": True, "cerita": "Jembatan rangka ringan."},
    {"id": 2, "nama_mahasiswa": "Rahasia Orang", "nama_kegiatan": "Lomba Beton", "tingkat": "internasional", "capaian": "Juara 2",
     "tahun": 2031, "pembimbing": ["0011", "0099"], "status": "terverifikasi", "tampil_nama": False},
    {"id": 3, "nama_mahasiswa": "X", "nama_kegiatan": "Belum diverifikasi", "tingkat": "nasional", "tahun": 2031, "status": "diajukan"},
    {"id": 4, "nama_mahasiswa": "Y", "nama_kegiatan": "Disembunyikan", "tingkat": "nasional", "tahun": 2031,
     "status": "terverifikasi", "sembunyikan_publik": True},
]
BUKTI = [{"tabel": "lkps_prestasi_mahasiswa", "baris_id": 1, "jenis": "foto", "url": f"https://drive.google.com/file/d/{FID1}/view"},
         {"tabel": "lkps_prestasi_mahasiswa", "baris_id": 1, "jenis": "sertifikat", "url": f"https://drive.google.com/file/d/{FID2}/view"},
         {"tabel": "lkps_prestasi_mahasiswa", "baris_id": 2, "jenis": "foto", "url": f"https://drive.google.com/open?id={FID3}"},
         {"tabel": "lkps_kerjasama", "baris_id": 1, "jenis": "foto", "url": f"https://drive.google.com/file/d/{FID2}/view"}]
DOSEN = [{"nidn": "0011", "nama": "Ani Lestari", "slug": "ani-lestari"}, {"nidn": "0099", "nama": "Dosen Luar", "slug": None}]


def test_prestasi_publik_names_only_with_consent_and_photos_only_of_kind_foto():
    xs = hp.prestasi_publik(BARIS, BUKTI, DOSEN)
    assert [x["id"] for x in xs] == [2, 1]                        # terbaru dulu; 3 diajukan, 4 disembunyikan
    jembatan, beton = xs[1], xs[0]
    assert jembatan["mahasiswa"] == ["Sari Dewi", "Rudi Hartono"] and beton["mahasiswa"] == []
    assert jembatan["_foto"] == [FID1] and beton["_foto"] == [FID3]   # sertifikat tidak pernah dipakai
    assert beton["pembimbing"] == [{"nama": "Ani Lestari", "slug": "ani-lestari"}, {"nama": "Dosen Luar"}]
    assert "105" not in str(xs) and "Rahasia" not in str(xs)


def test_salin_foto_copies_once_skips_failures_and_removes_unused(tmp_path):
    xs = hp.prestasi_publik(BARIS, BUKTI, DOSEN)
    (tmp_path / "prestasi").mkdir()
    (tmp_path / "prestasi" / "lama.jpg").write_bytes(b"x")
    diminta = []

    def ambil(url):
        diminta.append(url)
        return ("image/jpeg", b"\xff" * 2000) if FID1 in url else ("text/html", b"<html>")
    hasil = hp.salin_foto_prestasi(tmp_path, xs, ambil)
    assert hasil == {"baru": 1, "gagal": 1, "dibuang": 1, "dipakai": 1}
    assert xs[1]["foto"] == [f"prestasi/{FID1}.jpg"] and "foto" not in xs[0] and "_foto" not in xs[0]
    assert all("thumbnail?id=" in u for u in diminta)
    # berkas yang sudah ada tidak diunduh ulang
    xs2 = hp.prestasi_publik(BARIS, BUKTI, DOSEN)
    diminta.clear()
    hp.salin_foto_prestasi(tmp_path, xs2, ambil)
    assert diminta == [f"https://drive.google.com/thumbnail?id={FID3}&sz=w1200"]


def test_prestasi_page_and_lecturer_section():
    xs = hp.prestasi_publik(BARIS, BUKTI, DOSEN)
    for x in xs:
        x.pop("_foto")
    xs[1]["foto"] = [f"prestasi/{FID1}.jpg"]
    d = dict(D, prestasi=xs)
    h = hp.halaman_prestasi(d, "v1")
    assert "Juara 1" in h and "Sari Dewi dan Rudi Hartono" in h and "Jembatan rangka ringan." in h
    assert "Tim mahasiswa" in h and f"prestasi/{FID1}.jpg?v=v1" in h and 'href="dosen/ani-lestari.html"' in h
    assert h.index("<h2>2031</h2>") < h.index("<h2>2030</h2>")
    dosen = hp.halaman_dosen(d, D["dosen"][0], "", "v1", [])
    assert "Prestasi mahasiswa bimbingan" in dosen and "Lomba Beton" in dosen


# ---------- Kabar kegiatan (patch 81) dan status akreditasi (pemilik 2026-11-16) ----------
def test_kabar_publik_only_published_newest_first_with_photo_ids():
    rows = [{"id": 1, "judul": "Kuliah tamu beton", "tanggal": "2030-03-01", "jenis": "kuliah_tamu", "ringkasan": "r" * 30,
             "status": "terbit", "foto": [f"https://drive.google.com/file/d/{FID1}/view", "bukan-drive"]},
            {"id": 2, "judul": "Draf", "tanggal": "2030-04-01", "ringkasan": "r" * 30, "status": "diajukan"},
            {"id": 3, "judul": "Kunjungan proyek", "tanggal": "2030-05-01", "jenis": "kunjungan_lapangan", "ringkasan": "r" * 30,
             "status": "terbit", "foto": []}]
    xs = hp.kabar_publik(rows)
    assert [x["id"] for x in xs] == [3, 1] and xs[1]["_foto"] == [FID1]


def test_akreditasi_publik_valid_only():
    baris = [{"diakreditasi": False, "status_akreditasi": "unggul"},
             {"diakreditasi": True, "status_akreditasi": "baik_sekali", "nomor_sk": " 123/SK ", "tanggal_kedaluwarsa": "2031-01-01"}]
    assert hp.akreditasi_publik(baris, "2030-06-01", "LAM Teknik") == {
        "peringkat": "Baik Sekali", "kode": "baik_sekali", "nomor_sk": "123/SK", "berlaku_sampai": "2031-01-01", "lembaga": "LAM Teknik"}
    assert hp.akreditasi_publik(baris, "2031-01-02") == {}                       # kedaluwarsa: tidak ditampilkan
    assert hp.akreditasi_publik([{"diakreditasi": True, "status_akreditasi": "tidak_terakreditasi"}], "2030-01-01") == {}


def test_kabar_page_and_photo_folder(tmp_path):
    xs = hp.kabar_publik([{"id": 7, "judul": "Seminar <K3>", "tanggal": "2030-02-03", "jenis": "seminar", "ringkasan": "r" * 30,
                           "status": "terbit", "foto": [f"https://drive.google.com/file/d/{FID2}/view"]}])
    hasil = hp.salin_foto(tmp_path, xs, "kabar", lambda u: ("image/jpeg", b"\xff" * 2000))
    assert hasil["baru"] == 1 and xs[0]["foto"] == [f"kabar/{FID2}.jpg"] and (tmp_path / "kabar" / f"{FID2}.jpg").is_file()
    h = hp.halaman_kabar(dict(D, kabar=xs, situs={"berita": "https://univ.ac.id/berita"}), "v1")
    assert "Seminar &lt;K3&gt;" in h and "3 Februari 2030" in h and 'id="kabar-7"' in h and "univ.ac.id/berita" in h


def test_main_reads_lecturers_before_using_them():
    """Build 6fa027e berhenti dengan KeyError 'dosen': lembar["dosen"] dipakai sebelum diisi."""
    teks = (ROOT / "bangun.py").read_text(encoding="utf-8")
    awal = teks.index("def main(")
    isi = teks.index('lembar["dosen"] = dosen_dari_supabase(sb)', awal)
    pakai = teks.index('lembar["dosen"].', awal)
    assert isi < pakai


def test_laboratorium_publik_matches_tools_lecturer_courses_and_verified_research():
    rows = [{"id": 2, "nama": "Lab Tanah", "ringkasan": "r" * 30, "prasarana": "Ruang Tanah ", "kepala_nidn": "001",
             "mata_kuliah": ["SI201", "XX999"], "layanan": ["Uji sondir", " "], "kontak_layanan": "lab@contoh.ac.id",
             "foto": [f"https://drive.google.com/file/d/{FID1}/view"], "penelitian": ["a", "b"], "urutan": 1},
            {"id": 3, "nama": "Lab Lama", "ringkasan": "r" * 30, "tampil": False}]
    alat = [{"prasarana": "ruang tanah", "alat": "Sondir", "jumlah_dimiliki": 2, "jumlah_standar": 5, "kondisi": "terawat"},
            {"prasarana": "Ruang Lain", "alat": "Mesin"}]
    dosen = {"001": {"nama": "Ani Lestari", "slug": "ani-lestari"}}
    kur = [{"mk": [{"kode": "SI201", "nama": "Mekanika Tanah"}]}]
    keg = {"a": {"judul": "Riset lereng", "tahun": 2029, "kategori": "penelitian", "skema": "Hibah"}}
    xs = hp.laboratorium_publik(rows, alat, dosen, kur, keg)
    assert [x["nama"] for x in xs] == ["Lab Tanah"]
    x = xs[0]
    assert x["alat"] == [{"nama": "Sondir", "jumlah": 2}]          # standar dan kondisi tidak publik
    assert x["kepala"] == {"nama": "Ani Lestari", "slug": "ani-lestari"}
    assert x["mk"] == [{"kode": "SI201", "nama": "Mekanika Tanah"}]
    assert x["layanan"] == ["Uji sondir"] and x["_foto"] == [FID1]
    assert x["penelitian"] == [{"judul": "Riset lereng", "tahun": 2029, "jenis": "Penelitian", "skema": "Hibah"}]


def test_laboratorium_page_links_lecturer_and_escapes_text():
    lab = {"id": 2, "nama": "Lab <Tanah>", "ringkasan": "r" * 30, "kepala": {"nama": "Ani Lestari", "slug": "ani-lestari"},
           "mk": [{"kode": "SI201", "nama": "Mekanika Tanah"}], "alat": [{"nama": "Sondir", "jumlah": 2}],
           "layanan": ["Uji sondir"], "kontak": "lab@contoh.ac.id", "penelitian": [], "foto": ["laboratorium/x.jpg"]}
    h = hp.halaman_laboratorium(dict(D, laboratorium=[lab]), "v1")
    assert 'id="lab-2"' in h and "Lab &lt;Tanah&gt;" in h and 'href="dosen/ani-lestari.html"' in h
    assert 'href="mailto:lab@contoh.ac.id"' in h and "Sondir" in h and "laboratorium/x.jpg?v=v1" in h
    kosong = hp.halaman_laboratorium(dict(D, laboratorium=[], situs={"laboratorium": ["Lab Struktur"]}), "v1")
    assert "Lab Struktur" in kosong


def test_kerjasama_publik_hides_marked_rows_and_orders_in_force_first():
    rows = [{"id": 1, "mitra": "Univ Lama", "jenis": "penelitian", "tingkat": "nasional", "tahun_mulai": 2020, "tahun_selesai": 2022,
             "tautan_bukti": "https://drive.google.com/x"},
            {"id": 2, "mitra": "PT Baru", "jenis": "pendidikan", "tingkat": "nasional", "tanggal_mulai": "2029-03-01",
             "tanggal_selesai": "2031-02-28", "manfaat": "Magang"},
            {"id": 3, "mitra": "Rahasia", "jenis": "pkm", "tingkat": "wilayah", "tahun_mulai": 2029, "sembunyikan_publik": True},
            {"id": 4, "mitra": "Pemda", "jenis": "pkm", "tingkat": "wilayah", "tahun_mulai": 2028}]
    xs = hp.kerjasama_publik(rows, "2030-01-01")
    assert [x["mitra"] for x in xs] == ["PT Baru", "Pemda", "Univ Lama"]
    assert [x["aktif"] for x in xs] == [True, True, False]
    assert "tautan_bukti" not in xs[2] and xs[0]["selesai"] == "2031-02-28"


def test_kerjasama_page_lists_agreements_and_partners_by_level():
    d = dict(D, kerja_sama=hp.kerjasama_publik([{"id": 2, "mitra": "PT <Baru>", "jenis": "pendidikan", "tingkat": "nasional",
                                                 "tahun_mulai": 2029, "manfaat": "Magang"}], "2030-01-01"),
             publikasi=[{"judul": "Banjir", "tahun": 2029, "penulis": [], "mitra": [{"nama": "Kyoto Univ", "tingkat": "internasional",
                                                                                   "negara": "Jepang"}]}],
             kegiatan=[{"judul": "PkM", "tahun": 2028, "kategori": "pkm", "penulis": [],
                        "mitra": [{"nama": "kyoto univ", "tingkat": "internasional"}]}])
    g = hp.mitra_karya(d)
    assert len(g) == 1 and g[0]["nama"] == "Kyoto Univ" and [k["tahun"] for k in g[0]["karya"]] == [2029, 2028]
    h = hp.halaman_kerjasama(d, "v1")
    assert "PT &lt;Baru&gt;" in h and "Berlaku" in h and "Magang" in h and "Internasional" in h and "Jepang" in h
    assert "2 karya bersama" in h


def test_kerjasama_country_count_excludes_indonesia():
    d = dict(D, kerja_sama=[], kegiatan=[],
             publikasi=[{"judul": "A", "tahun": 2029, "penulis": [], "mitra": [
                 {"nama": "Kyoto Univ", "tingkat": "internasional", "negara": "Jepang"},
                 {"nama": "Tohoku Univ", "tingkat": "internasional", "negara": "jepang"},
                 {"nama": "UTP", "tingkat": "internasional", "negara": "Malaysia"},
                 {"nama": "ITB", "tingkat": "nasional", "negara": "Indonesia"}]}])
    h = hp.halaman_kerjasama(d, "v1")
    assert "<div><b>2</b><span>Negara</span></div>" in h


def test_profil_publik_names_lecturers_from_roster_and_orders_management():
    dosen = {"001": {"nama": "Ani Lestari", "slug": "ani-lestari"}, "002": {"nama": "Budi", "slug": None}}
    p = hp.profil_publik([{"sejarah": "Berdiri 2016.", "sambutan": "Selamat datang.", "penyambut_nidn": "001"}],
                         [{"id": 2, "jabatan": "Sekretaris Program Studi", "nidn": "002", "urutan": 2},
                          {"id": 1, "jabatan": "Ketua Program Studi", "nidn": "001", "urutan": 1},
                          {"id": 3, "jabatan": "Tenaga Kependidikan", "nama": "Citra", "urutan": 9},
                          {"id": 4, "jabatan": "Koordinator", "nidn": "999"}], dosen)
    assert p["penyambut"] == {"nama": "Ani Lestari", "slug": "ani-lestari"}
    assert p["pengelola"] == [{"jabatan": "Ketua Program Studi", "nama": "Ani Lestari", "slug": "ani-lestari"},
                              {"jabatan": "Sekretaris Program Studi", "nama": "Budi"},
                              {"jabatan": "Tenaga Kependidikan", "nama": "Citra"}]
    assert hp.profil_publik([], [], dosen) == {}


def test_profil_page_strategy_is_collapsible_below_mission_cards():
    d = dict(D, profil={}, vmts={"ps": {"visi": "V", "misi": "1. M", "tujuan": "1. T",
                                       "strategi": "1. Kurikulum OBE: satu.\n\n2. Pembelajaran: dua."}},
             kurikulum=[], akreditasi_prodi={}, dosen=[])
    h = hp.halaman_profil(d, "v1")
    kartu = h[h.index('class="vm-grid"'):h.index('<details class="strategi">')]
    assert "<h3>Misi</h3>" in kartu and "<h3>Tujuan</h3>" in kartu and "Strategi" not in kartu
    assert "Strategi pencapaian (2 butir)" in h and "<p>2. Pembelajaran: dua.</p>" in h
    assert '<details class="strategi" open' not in h          # tertutup pada awalnya


def test_inisial_skips_front_and_back_titles():
    assert hp.inisial("Dr. Antoni, ST., MT") == "A"
    assert hp.inisial("Prof. Dr. Ir. Ani Lestari, M.T.") == "AL"
    assert hp.inisial("Budi Santoso") == "BS"


def test_kaprodi_aktif_follows_assignment_dates():
    nidn = {"a": "001", "b": "002", "c": None}
    rows = [{"jabatan": "kaprodi", "dosen_id": "b", "mulai": "2026-07-01", "selesai": "2026-11-30"},
            {"jabatan": "kaprodi", "dosen_id": "a", "mulai": "2026-12-01", "selesai": "2029-11-30"},
            {"jabatan": "dekan", "dosen_id": "a", "mulai": "2026-01-01", "selesai": None}]
    assert hp.kaprodi_aktif(rows, nidn, "2026-11-30") == "002"
    assert hp.kaprodi_aktif(rows, nidn, "2026-12-01") == "001"
    assert hp.kaprodi_aktif(rows, nidn, "2026-06-30") is None          # dekan is not kaprodi
    assert hp.kaprodi_aktif(rows, nidn, "2030-01-01") is None
    # open-ended assignment; overlap -> latest start; lecturer without NIDN is skipped
    rows2 = [{"jabatan": "kaprodi", "dosen_id": "b", "mulai": "2025-01-01", "selesai": None},
             {"jabatan": "kaprodi", "dosen_id": "c", "mulai": "2026-01-01", "selesai": None}]
    assert hp.kaprodi_aktif(rows2, nidn, "2026-05-05") == "002"
    assert hp.kaprodi_aktif([], nidn, "2026-05-05") is None


def test_profil_publik_kaprodi_from_assignment_heads_list_and_signs_welcome():
    dosen = {"001": {"nama": "Ani Lestari", "slug": "ani-lestari"}, "002": {"nama": "Budi", "slug": None}}
    profil = [{"sambutan": "Selamat datang.", "penyambut_nidn": "002"}]
    kelola = [{"id": 1, "jabatan": "ketua program studi", "nidn": "002", "urutan": 1},
              {"id": 2, "jabatan": "Sekretaris Program Studi", "nidn": "002", "urutan": 2}]
    p = hp.profil_publik(profil, kelola, dosen, "001")
    assert p["penyambut"] == {"nama": "Ani Lestari", "slug": "ani-lestari"}
    assert p["pengelola"] == [{"jabatan": "Ketua Program Studi", "nama": "Ani Lestari", "slug": "ani-lestari"},
                              {"jabatan": "Sekretaris Program Studi", "nama": "Budi"}]
    # Kaprodi not on the public roster (e.g. hidden leader): typed rows and penyambut_nidn stay in force.
    p = hp.profil_publik(profil, kelola, dosen, "999")
    assert p["penyambut"] == {"nama": "Budi"} and p["pengelola"][0]["jabatan"] == "ketua program studi"
    # No welcome text -> no signatory even with a Kaprodi.
    assert "penyambut" not in hp.profil_publik([{"sejarah": "Berdiri 2016."}], [], dosen, "001")


def test_profil_page_shows_filled_parts_only():
    d = dict(D, profil={"sambutan": "Selamat datang <di> prodi.\n\nParagraf dua.", "penyambut": {"nama": "Ani Lestari", "slug": "ani-lestari"},
                        "pengelola": [{"jabatan": "Ketua Program Studi", "nama": "Ani Lestari", "slug": "ani-lestari"}]},
             vmts={"ps": {"visi": "Unggul dalam rekayasa", "misi": "Mendidik", "tujuan": "", "strategi": ""}},
             kurikulum=[{"kode": "K26", "profil": [{"kode": "PL1", "nama": "Perencana", "deskripsi": "Merancang"}]}],
             akreditasi_prodi={}, dosen=[{"nama": "Ani Lestari", "slug": "ani-lestari", "foto": "foto-dosen/ani-lestari.webp"}])
    h = hp.halaman_profil(d, "v1")
    assert "Selamat datang &lt;di&gt; prodi." in h and h.count("<p>Paragraf dua.</p>") == 1
    assert 'id="visi"' in h and "Unggul dalam rekayasa" in h and "<h3>Misi</h3>" in h and "<h3>Tujuan</h3>" not in h
    assert "Perencana" in h and 'id="akreditasi"' not in h and 'id="sejarah"' not in h
    assert 'href="dosen/ani-lestari.html"' in h and "foto-dosen/ani-lestari.webp?v=v1" in h


def test_generated_pages_do_not_share_a_name_with_site_files():
    """Actions copies site/ over the build output (cp -r site/. situs/), so a generated page named like a
    file in site/ is silently replaced: profil.html (workspace "Profil saya") hid the public profile on 2026-11-16."""
    teks = (ROOT / "halaman_publik.py").read_text(encoding="utf-8")
    # Ditulis langsung, atau lewat kamus `halaman = {"x.html": ...}` (pratinjau tautan, 2026-11-21).
    dibangun = set(re.findall(r'\(situs / "([\w.-]+\.html)"\)\.write_text', teks))
    kamus = re.search(r"\n    halaman = \{\n(.*?)\n    \}\n", teks, re.S)
    dibangun |= set(re.findall(r'^\s+"([\w.-]+\.html)": ', kamus.group(1), re.M)) if kamus else set()
    assert {"prestasi.html", "kabar.html", "profil-prodi.html"} <= dibangun
    assert sorted(f for f in dibangun if (ROOT / "site" / f).exists()) == []


def test_nama_tim_one_two_or_first_dkk():
    assert hp.nama_tim(None) == hp.nama_tim([]) == "Tim mahasiswa"
    assert hp.nama_tim(["Ani"]) == "Ani"
    assert hp.nama_tim(["Ani", "Budi"]) == "Ani dan Budi"
    assert hp.nama_tim(["Ani", "Budi", "Cici"]) == "Ani dkk."


def test_salin_foto_dosen_uploaded_photo_first_then_site_file(tmp_path):
    dipanggil = []
    def ambil(url):
        dipanggil.append(url)
        return ("image/jpeg", b"\xff" * 2000) if FID1 in url else ("", b"")
    dosen = [{"nama": "Ani", "slug": "ani", "_foto": [FID1]},
             {"nama": "Budi", "slug": "budi", "foto": "foto-dosen/budi.webp", "_foto": [FID2]},   # unduhan gagal
             {"nama": "Cici", "slug": "cici"}]
    hasil = hp.salin_foto_dosen(tmp_path, dosen, ambil)
    assert dosen[0]["foto"] == f"foto-profil/{FID1}.jpg" and (tmp_path / "foto-profil" / f"{FID1}.jpg").is_file()
    assert dosen[1]["foto"] == "foto-dosen/budi.webp" and "foto" not in dosen[2]
    assert all("_foto" not in d for d in dosen) and hasil["baru"] == 1 and hasil["gagal"] == 1
    assert all("sz=w400" in u for u in dipanggil)


def test_expertise_groups_validated_and_published_in_order():
    ps = {"expertise_groups": [{"code": "STR", "name": "Rekayasa Struktur"}, {"code": "AIR", "name": "Rekayasa Sumber Daya Air"}]}
    assert bangun.validasi_situs_publik({"public_site": ps}) == []
    assert bangun.situs_publik({"public_site": ps})["kelompok_keahlian"] == [
        {"kode": "STR", "nama": "Rekayasa Struktur", "berkas": "bidang-rekayasa-struktur.html"},
        {"kode": "AIR", "nama": "Rekayasa Sumber Daya Air", "berkas": "bidang-rekayasa-sumber-daya-air.html"}]
    for salah in ([{"code": "str", "name": "x"}], [{"code": "STR", "name": "a"}, {"code": "STR", "name": "b"}],
                  [{"code": "STR", "name": ""}], "STR"):
        assert "public_site.expertise_groups" in " ".join(bangun.validasi_situs_publik({"public_site": {"expertise_groups": salah}}))
    assert "kelompok_keahlian" not in bangun.situs_publik({"public_site": {"expertise_groups": None}})


def test_kabar_publik_skips_evidence_only_rows_and_keeps_fields_public():
    rows = [{"id": 1, "judul": "Kuliah tamu", "tanggal": "2030-01-02", "status": "terbit", "ringkasan": "r" * 30, "tampil_publik": True,
             "bukti": ["https://drive.google.com/file/d/xx/view"], "narasumber": "Ir. A"},
            {"id": 2, "judul": "Rapat internal", "tanggal": "2030-01-03", "status": "terbit", "ringkasan": "r" * 30, "tampil_publik": False}]
    xs = hp.kabar_publik(rows)
    assert [x["id"] for x in xs] == [1] and "bukti" not in xs[0] and "narasumber" not in xs[0]


def test_tempat_kp_groups_approved_kp_and_magang_without_identity():
    rows = [{"jenis": "kp", "status": "disetujui", "tahap": "pengajuan", "nim": "104123002", "nama": "Ani",
             "data": {"instansi": "PT  Wika", "bidang_kerja": "Struktur", "rencana_mulai": "2026-01-05"}},
            {"jenis": "kp", "status": "admin", "tahap": "selesai", "data": {"instansi": "pt wika", "program": "magang"},
             "data_selesai": {"tanggal_mulai": "2027-02-01"}},
            {"jenis": "kp", "status": "disetujui", "tahap": "pengajuan", "data": {"instansi": "PT. Wika,", "rencana_mulai": "2026-03-01"}},
            {"jenis": "kp", "status": "admin", "tahap": "pengajuan", "data": {"instansi": "PT Belum"}},   # belum disetujui
            {"jenis": "kp", "status": "ditolak", "data": {"instansi": "PT Tolak"}},
            {"jenis": "lomba", "status": "disetujui", "data": {"instansi": "X"}}]
    xs = hp.tempat_kp_publik(rows)
    assert xs == [{"instansi": "PT Wika", "kp": 2, "magang": 1, "bidang": ["Struktur"], "tahun_awal": 2026, "tahun_akhir": 2027}]   # "PT. Wika," ikut (105)
    h = hp.halaman_kerjasama(dict(D, kerja_sama=[], publikasi=[], kegiatan=[], tempat_kp=xs), "v1")
    assert 'id="tempat-kp"' in h and "PT Wika" in h and "2 KP · 1 magang" in h and "2026–2027" in h
    assert "104123002" not in h and "Ani" not in h


def test_alumni_summary_waits_for_minimum_and_counts_answers_as_written():
    sv = [{"id": 5, "kelompok": "alumni", "judul": "Tracer alumni 2026/2027", "publik": True, "dicabut": False, "token": "abc",
           "mulai": "2026-11-01", "selesai": None, "pertanyaan": [{"id": "f17_etika_a", "teks": "Saat lulus, ...: etika"}]},
          {"id": 4, "kelompok": "pengguna", "token": "zzz"}]
    j = [{"survei_id": 5, "jawaban": {"tahun_lulus": 2024, "status": "Bekerja (full time / part time)", "kerja_6bulan": "Ya",
                                      "bulan": 2, "provinsi": "DKI Jakarta", "f17_etika_a": "4", "f17_etika_b": "5", "pendapatan": 9000000}},
         {"survei_id": 5, "jawaban": {"tahun_lulus": 2024, "status": "Melanjutkan pendidikan", "kerja_6bulan": "Tidak", "bulan": 7,
                                      "provinsi": "dki  jakarta", "f17_etika_a": 3}},
         {"survei_id": 4, "jawaban": {"status": "x"}}]
    kecil = hp.alumni_ringkas(sv, j, 3, "2026-11-17")
    assert kecil == {"responden": 2, "min": 3, "isi": {"judul": "Tracer alumni 2026/2027", "token": "abc"}}
    a = hp.alumni_ringkas(sv, j, 2, "2026-11-17")
    assert a["provinsi"] == [["DKI Jakarta", 2]] and a["waktu_tunggu_rerata"] == 4.5 and a["per_tahun"] == [[2024, 2]]
    assert a["kompetensi"] == [{"nama": "Etika", "lulus": 3.5, "kerja": 5.0}]
    assert "pendapatan" not in json.dumps(a)
    h = hp.halaman_alumni(dict(D, alumni=a, tracer=[{"tahun_lulus": 2024, "lulusan": 30, "terlacak": 2, "waktu_tunggu_bulan": 4.5,
                                                     "sesuai_bidang": 1, "kerja_wilayah": 0, "kerja_nasional": 1, "kerja_internasional": 0}]), "v1")
    assert "50%" in h and "Bekerja ≤ 6 bulan" in h and "Etika" in h and "survei.html?t=abc" in h and "4,5" in h
    assert "9000000" not in h
    h0 = hp.halaman_alumni(dict(D, alumni=kecil, tracer=[]), "v1")
    assert "minimal 3 alumni" in h0 and "sekarang 2" in h0
    assert hp.alumni_ringkas(sv, j, 2, "2026-10-01").get("isi") is None   # survei belum dibuka


def test_alumni_distribution_follows_survey_option_order():
    sv = [{"id": 1, "kelompok": "alumni", "pertanyaan": [{"id": "kesesuaian", "opsi": ["Sangat erat", "Erat", "Kurang erat"]}]}]
    j = [{"survei_id": 1, "jawaban": {"status": "B", "kesesuaian": k}} for k in ("Kurang erat", "Kurang erat", "Sangat erat", "Lain")]
    assert hp.alumni_ringkas(sv, j, 1)["kesesuaian"] == [["Sangat erat", 1], ["Kurang erat", 2], ["Lain", 1]]


def test_calon_mahasiswa_page_uses_available_data_and_hides_empty_sections():
    """calon-mahasiswa.html (pemilik 2026-11-20): bagian tanpa data tidak tampil; FAQ dan tautan PMB dari config."""
    d = {**D, "situs": {"tagline": "Unggul <di> energi", "pendaftaran": "https://pmb.contoh.ac.id/admisi?src=1",
                        "kelompok_keahlian": [{"kode": "HYD", "nama": "Sumber Daya Air"}], "karier": ["Konsultan"]},
         "kurikulum": [{"kode": "K21", "mk": []}, {"kode": "K26", "mk": [
             {"kode": "01X01", "nama": "Kalkulus 1", "semester": 1, "sks": 4, "sifat": "wajib", "unit": "universitas", "bagian": {}},
             {"kode": "41334", "nama": "Perancangan Bangunan", "semester": 7, "sks": 4, "sifat": "wajib", "unit": "prodi",
              "capstone": True, "bagian": {}},
             {"kode": "41333", "nama": "Kerja Praktik", "semester": 7, "sks": 2, "sifat": "wajib", "unit": "prodi", "bagian": {}},
             {"kode": "41309", "nama": "Praktikum Bahan", "semester": 3, "sks": 1, "sifat": "wajib", "unit": "prodi",
              "bagian": {"praktikum": 1}},
             {"kode": "41401", "nama": "Dinamika Struktur", "sks": 3, "sifat": "pilihan", "unit": "prodi"}]}],
         "prestasi": [{"capaian": "Juara 1", "kegiatan": "Lomba Beton", "tingkat": "nasional", "tahun": 2029}],
         "dtps": {"jumlah": 10, "doktor": 7}, "alumni": {"responden": 0, "min": 5}}
    h = hp.halaman_calon(d, "v1")
    assert "Untuk calon mahasiswa" in h and "Unggul &lt;di&gt; energi" in h
    assert 'href="https://pmb.contoh.ac.id/admisi?src=1"' in h and "Daftar di PMB Universitas Contoh" in h
    assert "11 sks" not in h and ">11<" in h                     # sks wajib K26 (4+4+2+1), bukan K21
    # Perjalanan bertonggak (2026-11-21): tonggak dari data, bukan teks tetap.
    smt = lambda n: h[h.index(f"<b>Semester {n}</b>"):h.index("</li>", h.index(f"<b>Semester {n}</b>"))]
    assert "Dasar sains dan umum" in smt(1) and "Kalkulus 1" in smt(1)
    assert 'class="tg">Praktikum' not in h                      # lencana praktikum dihapus (pemilik 2026-11-22); nama MK boleh
    assert "Kerja praktik" in smt(7) and "Proyek rancangan (capstone)" in smt(7) and "Perancangan Bangunan" in smt(7)
    assert "Perjalanan 7 semester" in h
    # Terbaru dari program studi: prestasi 2029 dulu, maks. 2 per jenis; tanpa nama mahasiswa.
    baru = h[h.index("Terbaru dari program studi"):h.index("</section>", h.index("Terbaru dari program studi"))]
    assert baru.index("Prestasi · 2029") < baru.index("Pengabdian · 2029") and 'href="prestasi.html"' in baru
    # Mahasiswa ikut riset: angka dan kartu dari kegiatan.mahasiswa.
    riset = h[h.index("Mahasiswa ikut riset"):h.index("</section>", h.index("Mahasiswa ikut riset"))]
    assert "<b>1</b><span>penelitian dan pengabdian melibatkan mahasiswa</span>" in riset and "3 mahasiswa" in riset
    assert "publikasi ditulis bersama mahasiswa" not in riset   # tidak ada publikasi bermahasiswa di data uji
    assert "Sumber Daya Air" in h and "Hidrologi" not in h        # cakupan hanya dari bidang baku berkode sama (tidak ada cakupan)
    assert "Juara 1 — Lomba Beton" in h and "PkM desa" in h and "Konsultan" in h
    assert "Pertanyaan umum" not in h and "alumni sudah mengisi" not in h   # FAQ kosong, alumni di bawah minimum
    assert "Pertanyaan umum" in hp.halaman_calon({**d, "situs": {**d["situs"], "faq": [{"tanya": "Ada beasiswa?", "jawab": "Lihat PMB."}]}}, "")
    kosong = hp.halaman_calon({"prodi": "X", "institusi": "", "situs": {}}, "")
    assert "Tertarik bergabung?" in kosong and "Bidang yang Anda pelajari" not in kosong and "Daftar di PMB" not in kosong


def test_testimoni_only_with_consent_and_without_consent_fields():
    rows = [{"id": 2, "nama": "Budi", "peran": "alumni", "tahun_lulus": 2024, "pekerjaan": "Engineer, PT A",
             "kutipan": "Kuliah  di sini\nmembuka jalan karier saya.", "persetujuan_tanggal": "2026-12-01",
             "persetujuan_cara": "surel", "tampil": True, "urutan": 2},
            {"id": 1, "nama": "Ani", "peran": "mahasiswa", "angkatan": 2023, "kutipan": "Praktikumnya seru sekali.",
             "persetujuan_tanggal": "2026-12-02", "tampil": True, "urutan": 1},
            {"id": 3, "nama": "Tanpa izin", "kutipan": "Belum setuju dimuat di situs.", "persetujuan_tanggal": None, "tampil": True},
            {"id": 4, "nama": "Ditarik", "kutipan": "Sudah menarik persetujuannya.", "persetujuan_tanggal": "2026-01-01", "tampil": False}]
    t = hp.testimoni_publik(rows)
    assert [x["nama"] for x in t] == ["Ani", "Budi"]
    assert t[1] == {"nama": "Budi", "peran": "alumni", "kutipan": "Kuliah di sini membuka jalan karier saya.",
                    "tahun_lulus": 2024, "pekerjaan": "Engineer, PT A"}
    assert not any("persetujuan" in k for x in t for k in x)


def test_calon_page_quiz_scope_research_parents_and_testimonials():
    d = {**D, "situs": {"pendaftaran": "https://pmb.contoh.ac.id",
                        "kelompok_keahlian": [{"kode": "AIR", "nama": "Sumber Daya Air", "cakupan": "Hidrologi, tenaga air"},
                                              {"kode": "GEO", "nama": "Geoteknik"}],
                        "karier": ["Konsultan konstruksi"],
                        "kuis": [{"tanya": "Suka apa?", "pilihan": [{"teks": "Air", "kk": ["AIR"]}, {"teks": "Tanah", "kk": ["GEO", "XXX"]}]}]},
         "keahlian_baku": {"bidang": [{"kode": "AIR", "cakupan": "air bersih"}, {"kode": "GEO", "cakupan": "Tanah, fondasi"}],
                           "topik": [{"kode": "AIR01", "nama": "Hidrologi"}, {"kode": "AIR02", "nama": "Banjir"}]},
         "dosen": [{"nama": "Ani", "slug": "ani", "kelompok": "AIR", "topik_keahlian": ["AIR02", "AIR01"]},
                   {"nama": "Budi", "kelompok": "AIR", "topik_keahlian": ["AIR02"]}],
         "kurikulum": [{"kode": "K26", "mk": [{"nama": "Metode Pelaksanaan Konstruksi dan K3", "semester": 6, "sks": 2,
                                               "sifat": "wajib", "unit": "prodi", "bagian": {}}]}],
         "dtps": {"jumlah": 10, "doktor": 7}, "akreditasi_prodi": {"peringkat": "Baik Sekali", "lembaga": "LAM Teknik"},
         "testimoni": [{"nama": "Citra Dewi", "peran": "alumni", "tahun_lulus": 2024, "kutipan": "Dosennya sangat membantu."}]}
    h = hp.halaman_calon(d, "v1")
    # Cakupan prodi menang atas bidang baku; riset dosen dari topik, urut jumlah dosen.
    assert "<b>Diajarkan:</b> Hidrologi, tenaga air" in h and "air bersih" not in h
    assert "<b>Riset dosen:</b> Banjir, Hidrologi" in h
    assert "<b>Diajarkan:</b> Tanah, fondasi" in h            # GEO tanpa scope: bidang baku
    # Kuis: kode tak dikenal dibuang dari nilai pilihan; data kelompok tertanam untuk hasil.
    assert 'id="kuisForm"' in h and 'value="GEO"' in h and "XXX" not in h and '"riset": "Banjir, Hidrologi"' in h
    # Orang tua: dari data saja; biaya ke PMB.
    ortu = h[h.index('id="orang-tua"'):h.index("</section>", h.index('id="orang-tua"'))]
    assert "Terakreditasi Baik Sekali oleh LAM Teknik" in ortu and "10 dosen tetap, 7 di antaranya bergelar doktor" in ortu
    assert "Metode Pelaksanaan Konstruksi dan K3" in ortu and 'href="https://pmb.contoh.ac.id"' in ortu
    # Testimoni.
    assert "Kata alumni dan mahasiswa" in h and "Dosennya sangat membantu." in h and "Alumni 2024" in h
    assert "Kata alumni" not in hp.halaman_calon({**d, "testimoni": []}, "v1")


def test_english_page_from_english_data_with_fallbacks():
    d = {**D, "institusi": "Universitas Contoh",
         "situs": {"prodi_en": "Civil Engineering", "gelar": "Sarjana Teknik (S.T.)", "tagline_en": "Innovative <civil>",
                   "pendaftaran": "https://pmb.contoh.ac.id",
                   "kelompok_keahlian": [{"kode": "AIR", "nama": "Sumber Daya Air", "nama_en": "Water Resources",
                                          "cakupan_en": "Hydrology and hydropower"}, {"kode": "GEO", "nama": "Geoteknik"}]},
         "akreditasi_prodi": {"peringkat": "Baik Sekali", "lembaga": "LAM Teknik"},
         "dosen": [{"nama": "Ani", "slug": "ani", "kelompok": "AIR"}],
         "kurikulum": [{"kode": "K26", "profil": [{"kode": "PL-1", "nama": "Civil Engineer Pemula", "nama_en": "Junior Civil Engineer"},
                                                    {"kode": "PL-2", "nama": "Analis"}],
                        "cpl": [{"kode": "A", "rumusan_en": "Able to act ethically."}, {"kode": "B", "rumusan_en": ""}],
                        "mk": [{"nama": "Kalkulus 1", "nama_en": "Calculus 1", "semester": 1, "sks": 4, "sifat": "wajib"},
                               {"nama": "Pancasila", "semester": 8, "sks": 2, "sifat": "wajib"},
                               {"nama": "Dinamika Struktur", "nama_en": "Structural Dynamics", "sks": 3, "sifat": "pilihan"}]}]}
    h = hp.halaman_english(d, "v1")
    assert '<html lang="en">' in h and "<h1>Civil Engineering Study Program</h1>" in h and "Innovative &lt;civil&gt;" in h
    assert "accredited <b>Very Good</b> (Baik Sekali) by LAM Teknik" in h and "degree Sarjana Teknik (S.T.)" in h
    assert "Junior Civil Engineer" in h and "<b>Analis</b>" in h                      # PL tanpa nama_en: nama Indonesia
    assert "PLO A</span>Able to act ethically." in h and "PLO B" not in h
    assert "Calculus 1" in h and "Pancasila" in h and "Structural Dynamics" in h and "Kalkulus 1" not in h
    assert "Water Resources" in h and "Hydrology and hydropower" in h and 'href="dosen/ani.html"' in h and "<b>Geoteknik</b>" in h
    assert 'href="https://pmb.contoh.ac.id"' in h
    # Tanpa nama Inggris prodi: halaman tidak dibuat dan tidak masuk peta situs.
    assert "english.html" in hp.peta_situs("https://x.id", d, set())
    assert "english.html" not in hp.peta_situs("https://x.id", {**d, "situs": {}}, set())


def test_interest_quiz_config_validated():
    ps = {"expertise_groups": [{"code": "AIR", "name": "Air"}],
          "interest_quiz": [{"question": "Q", "options": [{"text": "a", "groups": ["AIR"]}, {"text": "b", "groups": ["TRN"]}]}]}
    assert any("interest_quiz" in g for g in bangun.validasi_situs_publik({"public_site": ps}))
    ps["interest_quiz"][0]["options"][1]["groups"] = ["AIR"]
    assert not any("interest_quiz" in g for g in bangun.validasi_situs_publik({"public_site": ps}))
    assert bangun.situs_publik({"public_site": ps})["kuis"][0]["pilihan"][1] == {"teks": "b", "kk": ["AIR"]}


def test_public_faq_config_validated_and_exported():
    s = bangun.situs_publik({"public_site": {"faq": [{"question": " Ada beasiswa? ", "answer": " Lihat PMB. "}, {"question": "x"}]}})
    assert s["faq"] == [{"tanya": "Ada beasiswa?", "jawab": "Lihat PMB."}]
    galat = " ".join(bangun.validasi_situs_publik({"public_site": {"faq": [{"question": "x"}]}}))
    assert "public_site.faq" in galat


# ---- Pratinjau tautan dan data terstruktur (pemilik 2026-11-21) ----
KEPALA = ('<html><head>\n<title>T</title>\n<meta name="description" content="Desk &amp; isi">\n'
          '<meta property="og:title" content="Judul">\n{og}</head><body></body></html>')


def test_lengkapi_bagikan_menambah_tag_yang_belum_ada():
    t = hp.lengkapi_bagikan(KEPALA.format(og=""), "https://contoh.id/situs", "kabar.html", "Program Studi X — Univ Y")
    assert '<link rel="canonical" href="https://contoh.id/situs/kabar.html">' in t
    assert '<meta property="og:description" content="Desk &amp; isi">' in t          # tidak di-escape dua kali
    assert '<meta property="og:url" content="https://contoh.id/situs/kabar.html">' in t
    assert '<meta property="og:image" content="https://contoh.id/situs/bagikan.png">' in t
    assert '<meta property="og:image:width" content="1200">' in t and 'summary_large_image' in t
    assert '<meta property="og:site_name" content="Program Studi X — Univ Y">' in t
    assert t.count("</head>") == 1 and t.index("og:locale") < t.index("</head>")


def test_lengkapi_bagikan_foto_relatif_jadi_mutlak_dan_tidak_menggandakan():
    og = '<meta property="og:image" content="prestasi/a b.jpg">\n<meta property="og:type" content="profile">\n'
    t = hp.lengkapi_bagikan(KEPALA.format(og=og), "https://contoh.id/situs/", "prestasi.html", "")
    assert '<meta property="og:image" content="https://contoh.id/situs/prestasi/a b.jpg">' in t
    assert t.count('property="og:image"') == 1 and t.count('property="og:type"') == 1
    assert "og:image:width" not in t and "og:site_name" not in t
    d = hp.lengkapi_bagikan(KEPALA.format(og='<meta property="og:image" content="../foto/x.jpg">\n'), "https://c.id", "dosen/a.html", "")
    assert 'content="https://c.id/foto/x.jpg"' in d and '<meta property="og:url" content="https://c.id/dosen/a.html">' in d
    sekali = hp.lengkapi_bagikan(t, "https://contoh.id/situs", "prestasi.html", "")
    assert sekali == t                                                                   # dijalankan ulang = tetap
    assert hp.lengkapi_bagikan(KEPALA.format(og=""), "", "x.html", "") == KEPALA.format(og="")
    tanpa = hp.lengkapi_bagikan(KEPALA.format(og=""), "https://c.id", "x.html", "", None)
    assert "og:image" not in tanpa and 'content="summary"' in tanpa


def test_ld_program_hanya_fakta_dari_data():
    D = {"prodi": "Teknik Sipil", "institusi": "Universitas Contoh",
         "situs": {"tagline": "Tagline.", "pendaftaran": "https://pmb.contoh/daftar",
                   "sosial": {"instagram": "https://www.instagram.com/prodi/", "instagram_himpunan": "https://www.instagram.com/hima/"}},
         "kurikulum": [{"kode": "K21", "mk": [{"semester": 10}]}, {"kode": "K26", "mk": [{"semester": 1}, {"semester": 8}, {"semester": None}]}]}
    ld = hp.ld_program(D, "https://contoh.id/situs/")
    assert ld["@type"] == "EducationalOccupationalProgram" and ld["name"] == "Program Studi Teknik Sipil"
    assert ld["url"] == "https://contoh.id/situs/calon-mahasiswa.html" and ld["description"] == "Tagline."
    assert ld["provider"] == {"@type": "CollegeOrUniversity", "name": "Universitas Contoh"}
    assert ld["timeToComplete"] == "P4Y"                                                # kurikulum terbaru (K26), 8 semester
    assert ld["sameAs"] == ["https://www.instagram.com/prodi/"]                         # akun himpunan bukan akun prodi
    assert ld["potentialAction"]["target"] == "https://pmb.contoh/daftar"
    kosong = hp.ld_program({"prodi": "X"}, "")
    assert set(kosong) == {"@context", "@type", "name", "inLanguage"}


def test_beranda_sumber_tanpa_alamat_situs():
    """Domain akan pindah (domain kampus, 2026-11-21): site/index.html tidak memuat alamat situs; --beranda mengisinya."""
    idx = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    kepala = re.sub(r"<!--.*?-->", "", idx[:idx.index("</head>")], flags=re.S)
    assert '<meta property="og:image" content="bagikan.png">' in kepala and (ROOT / "site" / "bagikan.png").is_file()
    assert "github.io" not in kepala and "og:url" not in kepala and 'rel="canonical"' not in kepala


def test_lengkapi_beranda_alamat_dan_akun_dari_data():
    idx = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    D = {"prodi": "Teknik Sipil", "institusi": "Universitas Contoh",
         "situs": {"sosial": {"instagram": "https://www.instagram.com/prodi/", "instagram_himpunan": "https://www.instagram.com/hima/"}}}
    t = hp.lengkapi_beranda(idx, D, "https://sipil.contoh.ac.id")
    assert '<meta property="og:image" content="https://sipil.contoh.ac.id/bagikan.png">' in t
    assert '<link rel="canonical" href="https://sipil.contoh.ac.id/">' in t
    assert '<meta property="og:url" content="https://sipil.contoh.ac.id/">' in t
    assert '"url":"https://sipil.contoh.ac.id/","sameAs":["https://www.instagram.com/prodi/"]' in t
    assert hp.lengkapi_beranda(t, D, "https://sipil.contoh.ac.id") == t                  # dijalankan ulang = tetap
    assert hp.lengkapi_beranda(idx, D, "") == idx


def test_beranda_dilengkapi_sesudah_salin_site():
    """cp -r site/. situs/ menimpa index.html terbit; --beranda harus SESUDAH langkah salin."""
    wf = (ROOT / ".github" / "workflows" / "bangun-situs.yml").read_text(encoding="utf-8")
    assert wf.index("cp -r site/. situs/") < wf.index("python bangun.py --beranda situs")
    bat = ROOT / "bangun-dan-push.bat"   # hanya di repo sumber (repo prodi membangun di GitHub Actions)
    if bat.is_file():
        bat = bat.read_text(encoding="utf-8")
        assert bat.index(r'robocopy "%DATA%\site"') < bat.index("bangun.py --beranda")


def test_bangun_beranda_tanpa_supabase(tmp_path, monkeypatch):
    import shutil
    (tmp_path / "data.json").write_text('{"prodi": "Teknik Sipil", "institusi": "U", "situs": {"sosial": {}}}', encoding="utf-8")
    shutil.copyfile(ROOT / "site" / "index.html", tmp_path / "index.html")
    (tmp_path / "CNAME").write_text("sipil.kampus.ac.id\n", encoding="utf-8")                 # CNAME menang atas config
    for k in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY"):
        monkeypatch.delenv(k, raising=False)
    bangun.lengkapi_beranda_terbit(tmp_path)
    t = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert '<meta property="og:image" content="https://sipil.kampus.ac.id/bagikan.png">' in t and '"url":"https://sipil.kampus.ac.id/"' in t


def test_semester_stages_from_config():
    """Tahap belajar per semester (pemilik 2026-11-22): lencana dari config, menggantikan tebakan 'Dasar sains dan umum'."""
    mk = [{"kode": "01X01", "nama": "Kalkulus 1", "semester": 1, "sks": 4, "sifat": "wajib", "unit": "universitas", "bagian": {}},
          {"kode": "41301", "nama": "Statika", "semester": 3, "sks": 3, "sifat": "wajib", "unit": "prodi", "bagian": {}}]
    d = {**D, "situs": {"tahap": {"1": "Sains dasar", "2": "Sains dasar", "3": "Dasar teknik"}},
         "kurikulum": [{"kode": "K26", "mk": mk}]}
    h = hp.halaman_calon(d, "v1")
    smt = lambda n: h[h.index(f"<b>Semester {n}</b>"):h.index("</li>", h.index(f"<b>Semester {n}</b>"))]
    assert '<span class="tg tahap">Sains dasar</span>' in smt(1) and "Dasar sains dan umum" not in h
    assert '<span class="tg tahap">Dasar teknik</span>' in smt(3)
    assert bangun.situs_publik({"public_site": {"semester_stages": [{"semesters": [1, 2], "label": " Sains dasar "}]}})["tahap"] \
        == {"1": "Sains dasar", "2": "Sains dasar"}
    galat = lambda t: [g for g in bangun.validasi_situs_publik({"public_site": {"semester_stages": t}}) if "semester_stages" in g]
    assert not galat([{"semesters": [1, 2], "label": "A"}, {"semesters": [3], "label": "B"}]) and not galat(None)
    assert galat([{"semesters": [1, 2], "label": "A"}, {"semesters": [2], "label": "B"}])   # semester 2 dua kali
    assert galat([{"semesters": ["1"], "label": "A"}]) and galat([{"semesters": [1], "label": ""}])


def test_electives_grouped_by_peminatan():
    """MK pilihan per bidang (instal-lengkap.sql, pemilik 2026-11-22): kartu di calon-mahasiswa.html, isi kuis."""
    mk = [{"kode": "41301", "nama": "Statika", "semester": 3, "sks": 3, "sifat": "wajib", "unit": "prodi", "bagian": {}},
          {"kode": "41401", "nama": "Dinamika Struktur", "sks": 3, "sifat": "pilihan", "unit": "prodi", "peminatan": "STR"},
          {"kode": "41413", "nama": "Hidrologi Lanjut", "sks": 3, "sifat": "pilihan", "unit": "prodi", "peminatan": "AIR"},
          {"kode": "41419", "nama": "Aspek Kebencanaan", "sks": 3, "sifat": "pilihan", "unit": "prodi", "peminatan": "UMUM"},
          {"kode": "41499", "nama": "Tanpa Peminatan", "sks": 2, "sifat": "pilihan", "unit": "prodi"}]
    situs = {"kelompok_keahlian": [{"kode": "STR", "nama": "Rekayasa Struktur"}, {"kode": "AIR", "nama": "Sumber Daya Air"}],
             "peminatan_lain": [{"kode": "UMUM", "nama": "Sipil umum"}],
             "kuis": [{"tanya": "Q", "pilihan": [{"teks": "a", "kk": ["STR"]}, {"teks": "b", "kk": ["AIR"]}]}]}
    h = hp.halaman_calon({**D, "situs": situs, "kurikulum": [{"kode": "K26", "mk": mk}]}, "v1")
    pil = h[h.index("Mata kuliah pilihan per bidang"):h.index("</section>", h.index("Mata kuliah pilihan per bidang"))]
    assert pil.index("Rekayasa Struktur") < pil.index("Sumber Daya Air") < pil.index("Sipil umum")   # urutan config
    assert "<li>Dinamika Struktur</li>" in pil and "tersedia 4 mata kuliah pilihan" in pil and "Tanpa Peminatan" not in pil
    data = json.loads(h[h.index('id="kuisData">') + 14:h.index("</script>", h.index('id="kuisData">'))])
    assert [x["pilihan"] for x in data] == [["Dinamika Struktur"], ["Hidrologi Lanjut"]]
    # Tanpa peminatan sama sekali: kalimat lama.
    polos = [{k: v for k, v in m.items() if k != "peminatan"} for m in mk]
    h2 = hp.halaman_calon({**D, "situs": situs, "kurikulum": [{"kode": "K26", "mk": polos}]}, "v1")
    assert "Mata kuliah pilihan per bidang" not in h2 and "tersedia 4 mata kuliah pilihan untuk mendalami minat Anda" in h2


def test_peminatan_build_and_config():
    rows = [{"kurikulum": "K26", "kode": "41401", "nama": "Dinamika Struktur", "sifat": "pilihan", "peminatan": " STR "},
            {"kurikulum": "K26", "kode": "41499", "nama": "Lain", "sifat": "pilihan", "peminatan": None}]
    mk = bangun.kurikulum_publik(rows, [], [], [])[0]["mk"]
    assert mk[0]["peminatan"] == "STR" and "peminatan" not in mk[1]
    ps = {"expertise_groups": [{"code": "STR", "name": "Struktur"}]}
    galat = lambda lain: [g for g in bangun.validasi_situs_publik({"public_site": {**ps, "elective_other_groups": lain}})
                          if "elective_other_groups" in g]
    assert not galat([{"code": "UMUM", "name": "Sipil umum"}]) and not galat(None)
    assert galat([{"code": "STR", "name": "x"}]) and galat([{"code": "umum", "name": "x"}]) and galat([{"code": "UMUM", "name": ""}])
    assert bangun.situs_publik({"public_site": {"elective_other_groups": [{"code": "UMUM", "name": " Sipil umum "}]}})["peminatan_lain"] \
        == [{"kode": "UMUM", "nama": "Sipil umum"}]


def test_galeri_from_published_photos():
    """Galeri foto (pemilik 2026-11-22): dari kabar, prestasi, laboratorium; terbaru dulu; tanpa nama mahasiswa."""
    d = {**D, "kabar": [{"id": 3, "judul": "Kuliah tamu", "tanggal": "2026-10-05", "foto": ["kabar/a.jpg", "kabar/b.jpg"]}],
         "prestasi": [{"id": 7, "capaian": "Juara 1", "kegiatan": "Lomba Beton", "tahun": 2026, "bulan": 11,
                       "mahasiswa": ["Rahasia Nama"], "foto": ["prestasi/p.jpg"]},
                      {"id": 8, "capaian": "Juara 2", "kegiatan": "Lomba Jembatan", "tahun": 2025, "bulan": 3}],
         "laboratorium": [{"id": 2, "nama": "Lab Hidraulika", "foto": ["laboratorium/l.jpg"]}]}
    fs = hp.foto_galeri(d)
    assert [f["src"] for f in fs] == ["prestasi/p.jpg", "kabar/a.jpg", "kabar/b.jpg", "laboratorium/l.jpg"]
    assert fs[0]["href"] == "prestasi.html#prestasi-7" and fs[1]["href"] == "kabar.html#kabar-3"
    h = hp.halaman_galeri(d, "v1")
    assert h.index("<h2>2026</h2>") < h.index("<h2>Fasilitas</h2>") and "Rahasia Nama" not in h
    assert "November 2026" in h and 'href="laboratorium.html#lab-2"' in h
    assert 'id="prestasi-7"' in hp.halaman_prestasi(d, "v1")              # anchor tujuan tautan galeri
    kosong = hp.halaman_galeri({**D, "kabar": [], "prestasi": [], "laboratorium": []}, "v1")
    assert "akan tampil di sini" in kosong
    # Cuplikan di calon-mahasiswa.html mulai 3 foto.
    assert "Suasana kegiatan" in hp.halaman_calon(d, "v1")
    sedikit = {**d, "kabar": [], "laboratorium": []}
    assert "Suasana kegiatan" not in hp.halaman_calon(sedikit, "v1")
    # Sitemap: galeri baru didaftarkan mulai GALERI_MIN_SITEMAP foto; peta situs mulai 1 foto.
    assert "galeri.html" not in hp.peta_situs("https://x.id", d, set())
    banyak = {**d, "kabar": [{"id": 3, "judul": "K", "tanggal": "2026-10-05", "foto": [f"kabar/{i}.jpg" for i in range(6)]}]}
    assert "galeri.html" in hp.peta_situs("https://x.id", banyak, set())
    assert 'href="galeri.html"' in hp.halaman_peta(d, set(), "v1")
    assert 'href="galeri.html"' not in hp.halaman_peta({**D, "kabar": [], "prestasi": [], "laboratorium": []}, set(), "v1")


def test_calon_tracer_figures_aggregate_only():
    """Setelah lulus (pemilik 2026-11-22): angka tracer agregat bila responden cukup; tanpa nama instansi."""
    a = {"responden": 6, "min": 5, "status": [["Bekerja", 5], ["Melanjutkan studi", 1]],
         "kerja_6bulan": [["Ya", 4], ["Tidak", 1]], "waktu_tunggu_rerata": 3.5,
         "jenis_instansi": [["BUMN/BUMD", 3], ["Swasta", 2], ["Lainnya", 1]]}
    h = hp.halaman_calon({**D, "alumni": a}, "v1")
    lulus = h[h.index("Setelah lulus"):h.index("</section>", h.index("Setelah lulus"))]
    assert "<b>80%</b>" in lulus and "<b>3,5</b>" in lulus and "BUMN/BUMD 50%, Swasta 33%" in lulus
    assert "Lainnya 17%" not in lulus and "Dari 6 alumni" in lulus
    sedikit = hp.halaman_calon({**D, "alumni": {**a, "responden": 3}}, "v1")
    assert "bekerja dalam 6 bulan" not in sedikit
    assert hp.persen_jawaban([["Ya", 1], ["tidak", 3]], {"ya"}) == 25 and hp.persen_jawaban([], {"ya"}) is None


def test_lecturer_page_extra_links_escaped():
    """Tautan lain (patch 146) tampil di dosen/<slug>.html di samping SINTA; label di-escape; hanya https; sameAs."""
    dosen = {**D["dosen"][0], "tautan": [{"label": "HESLab <lab>", "url": "https://heslab.contoh.id"},
                                         {"label": "Jahat", "url": "javascript:alert(1)"}]}
    h = hp.halaman_dosen(D, dosen, "https://x.id", "v1")
    assert 'href="https://heslab.contoh.id" rel="noopener">HESLab &lt;lab&gt; ↗</a>' in h
    assert "javascript:" not in h and '"https://heslab.contoh.id"' in h[h.index("application/ld+json"):]


def test_expertise_group_pages():
    """Halaman per bidang (pemilik 2026-11-22): MK pilihan, dosen, topik riset, kegiatan dan publikasi dosen bidang itu."""
    d = {**D, "situs": {"kelompok_keahlian": [{"kode": "AIR", "nama": "Rekayasa Sumber Daya Air", "cakupan": "Hidrologi, drainase"},
                                              {"kode": "STR", "nama": "Rekayasa Struktur"}],
                        "aturan_pilihan": "Wajib 2 MK pilihan sesuai peminatan TA."},
         "dosen": [{"nama": "Ani", "slug": "ani", "kelompok": "AIR", "topik_keahlian": ["T1"]},
                   {"nama": "Budi", "slug": "budi", "kelompok": "STR"}],
         "keahlian_baku": {"bidang": [], "topik": [{"kode": "T1", "nama": "Hidrologi", "bidang": "AIR"}]},
         "kurikulum": [{"kode": "K26", "mk": [{"kode": "41413", "nama": "Hidrologi Lanjut", "sks": 3, "sifat": "pilihan", "peminatan": "AIR"},
                                             {"kode": "41401", "nama": "Dinamika Struktur", "sks": 3, "sifat": "pilihan", "peminatan": "STR"}]}],
         "kegiatan": [{"judul": "Riset banjir", "tahun": 2026, "kategori": "penelitian", "mahasiswa": 2, "penulis": [{"slug": "ani"}]},
                      {"judul": "Riset beton", "tahun": 2026, "kategori": "penelitian", "penulis": [{"slug": "budi"}]},
                      # Ketua dosen STR, dosen AIR hanya anggota: tidak tampil di halaman AIR.
                      {"judul": "Riset jembatan", "tahun": 2026, "kategori": "penelitian",
                       "penulis": [{"slug": "budi", "peran": "ketua"}, {"slug": "ani", "peran": "anggota"}]}],
         "publikasi": [{"judul": "Banjir <kota>", "tahun": 2025, "url": "https://doi.org/x", "penulis": [{"slug": "ani"}]},
                       {"judul": "Jahat", "tahun": 2024, "url": "javascript:x", "penulis": [{"slug": "ani"}]}]}
    bs = hp.info_bidang(d)
    assert [b["berkas"] for b in bs] == ["bidang-rekayasa-sumber-daya-air.html", "bidang-rekayasa-struktur.html"]
    h = hp.halaman_bidang(d, bs[0], bs, "v1")
    assert "<h1>Rekayasa Sumber Daya Air</h1>" in h and "Hidrologi Lanjut" in h and "Dinamika Struktur" not in h
    assert 'href="dosen/ani.html"' in h and "Budi" not in h and "Topik riset dosen:</b> Hidrologi" in h
    assert "Riset banjir" in h and "melibatkan 2 mahasiswa" in h and "Riset beton" not in h and "Riset jembatan" not in h
    assert "Riset jembatan" in hp.halaman_bidang(d, bs[1], bs, "v1")
    assert "Banjir &lt;kota&gt;" in h and "javascript:" not in h and "Wajib 2 MK pilihan sesuai peminatan TA." in h
    assert 'href="bidang-rekayasa-struktur.html">Rekayasa Struktur</a>' in h and 'aria-current="page">Rekayasa Sumber Daya Air' in h
    # Ditaut dari halaman calon, profil prodi, peta situs, sitemap, dan halaman dosen.
    assert 'href="bidang-rekayasa-sumber-daya-air.html"' in hp.halaman_calon(d, "v1")
    assert 'href="bidang-rekayasa-sumber-daya-air.html"' in hp.halaman_peta(d, set(), "v1")
    assert "https://x.id/bidang-rekayasa-struktur.html" in hp.peta_situs("https://x.id", d, set())
    assert 'href="../bidang-rekayasa-sumber-daya-air.html"' in hp.halaman_dosen(d, d["dosen"][0], "https://x.id", "v1")


def test_elective_rule_config():
    ps = {"elective_rule": " Wajib 2 MK. "}
    assert bangun.situs_publik({"public_site": ps})["aturan_pilihan"] == "Wajib 2 MK."
    assert not [g for g in bangun.validasi_situs_publik({"public_site": ps}) if "elective_rule" in g]
    assert [g for g in bangun.validasi_situs_publik({"public_site": {"elective_rule": "x" * 301}}) if "elective_rule" in g]


def test_public_pages_show_name_with_titles():
    """Nama dengan gelar di halaman publik (pemilik 2026-11-19, 2026-11-22); tanpa nama_gelar: nama biasa."""
    d = {**D, "dosen": [{"nama": "Ani", "slug": "ani", "nama_gelar": "Dr. Ani, S.T., M.T.", "kelompok": "AIR"},
                        {"nama": "Budi", "slug": "budi", "kelompok": "AIR"}],
         "situs": {"kelompok_keahlian": [{"kode": "AIR", "nama": "Sumber Daya Air"}]},
         "prestasi": [{"id": 1, "capaian": "Juara 1", "kegiatan": "Lomba", "tahun": 2026, "pembimbing": [{"nama": "Ani", "slug": "ani"}]}]}
    assert hp.nama_dosen(d, {"slug": "ani"}) == "Dr. Ani, S.T., M.T." and hp.nama_dosen(d, {"nama": "Budi"}) == "Budi"
    bs = hp.info_bidang(d)
    h = hp.halaman_bidang(d, bs[0], bs, "v1")
    assert ">Dr. Ani, S.T., M.T.</a>" in h and ">Budi</a>" in h
    assert ">Dr. Ani, S.T., M.T.</a>" in hp.halaman_prestasi(d, "v1")
    assert ">Dr. Ani, S.T., M.T.</a>" in hp.halaman_peta(d, set(), "v1")


def test_kaprodi_history():
    """Ketua program studi dari masa ke masa (pemilik 2026-11-22): dari penugasan Kaprodi; periode berurutan digabung."""
    k = [{"jabatan": "kaprodi", "dosen_id": "a", "mulai": "2016-08-01", "selesai": "2021-07-31"},
         {"jabatan": "kaprodi", "dosen_id": "a", "mulai": "2021-08-01", "selesai": "2026-11-30"},
         {"jabatan": "kaprodi", "dosen_id": "b", "mulai": "2026-12-01", "selesai": None},
         {"jabatan": "koordinator_ta", "dosen_id": "c", "mulai": "2020-01-01"},
         {"jabatan": "kaprodi", "dosen_id": "x", "mulai": "2010-01-01"}]   # tidak ada di daftar dosen: dilewati
    orang = {"a": {"nama": "Dr. Antoni, ST., MT", "slug": "antoni"}, "b": {"nama": "Dr. Budi"}}
    assert hp.riwayat_kaprodi(k, orang, "2026-11-22") == [{"nama": "Dr. Antoni, ST., MT", "slug": "antoni", "mulai": "2016-08-01",
                                                          "selesai": "2026-11-30", "kini": True}]
    r = hp.riwayat_kaprodi(k, orang, "2026-12-05")
    assert [(x["nama"], x["mulai"], x["selesai"], x["kini"]) for x in r] == [
        ("Dr. Antoni, ST., MT", "2016-08-01", "2026-11-30", False), ("Dr. Budi", "2026-12-01", None, True)]
    P = hp.profil_publik([{}], [], {}, None, r)
    h = hp.halaman_profil({**D, "profil": P}, "v1")
    seg = h[h.index("Ketua program studi dari masa ke masa"):]
    assert "2016–2026</small>" in seg and "2026–sekarang · menjabat" in seg and seg.index("Antoni") < seg.index("Budi")
    assert 'href="dosen/antoni.html"' in seg


def _d_mk():
    kur = [{"kode": "K26",
            "cpl": [{"kode": "B", "rumusan": "Mampu menerapkan <sains> dasar."}],
            "mk": [{"kode": "41413", "nama": "Hidrologi Lanjut", "sks": 3, "sifat": "pilihan", "peminatan": "AIR", "cpl": ["B"],
                    "bagian": {"kuliah": 2, "praktikum": 1}},
                   {"kode": "41414", "nama": "Drainase Kota", "sks": 2, "sifat": "pilihan", "peminatan": "AIR", "cpl": []},
                   {"kode": "41301", "nama": "Geologi Dasar", "sks": 2, "semester": 2, "sifat": "wajib", "cpl": [],
                    "unit": "universitas"},
                   {"kode": "41302", "nama": "Fisika Dasar", "sks": 3, "semester": 2, "sifat": "wajib", "cpl": []}]},
           {"kode": "K21", "cpl": [], "mk": [{"kode": "41413", "nama": "Hidrologi", "sks": 3, "sifat": "wajib", "cpl": []}]}]
    sil = [{"kurikulum": "K26", "kode_mk": "41413", "sah_pada": "2026-11-20T03:00:00+00:00",
            "sah": {"versi": "1", "deskripsi": "Analisis banjir.\n\nPokok bahasan kedua.", "deskripsi_en": "Flood analysis.",
                    "pustaka": "Chow (1988)\n\nLinsley (1982)", "prasyarat": "41302 Hidrologi Dasar",
                    "catatan_impor": "RAHASIA impor"}},
           # Draf belum pernah disahkan: tidak keluar.
           {"kurikulum": "K26", "kode_mk": "41301", "sah": None},
           # Silabus kurikulum lama: bukan kurikulum terbaru, tidak dipakai.
           {"kurikulum": "K21", "kode_mk": "41413", "sah": {"versi": "1", "deskripsi": "Lama"}}]
    hp.lengkapi_mk_terbaru(kur, sil)
    return {**D, "kurikulum": kur,
            "situs": {"kelompok_keahlian": [{"kode": "AIR", "nama": "Rekayasa Sumber Daya Air"}], "tahap": {"2": "Sains dasar"}},
            "laboratorium": [{"id": 7, "nama": "Lab Hidraulika", "mk": [{"kode": "41413", "nama": "Hidrologi Lanjut"}],
                              "bidang": ["AIR", "XYZ"], "alat": [], "layanan": [], "penelitian": [], "ringkasan": "Lab air."}]}


def test_course_pages():
    """Halaman per mata kuliah (pemilik 2026-11-22): kurikulum terbaru saja, silabus hanya yang disahkan, tanpa pengampu."""
    d = _d_mk()
    ms = hp.info_mk(d)
    assert [m["berkas"] for m in ms] == ["mk-41413-hidrologi-lanjut.html", "mk-41414-drainase-kota.html",
                                         "mk-41301-geologi-dasar.html", "mk-41302-fisika-dasar.html"]
    assert "berkas" not in d["kurikulum"][1]["mk"][0]          # K21 tidak mendapat halaman
    assert set(ms[0]["silabus"]) == {"deskripsi", "deskripsi_en", "pustaka", "prasyarat", "disahkan"}
    assert "silabus" not in ms[2]                               # draf tidak pernah keluar
    h = hp.halaman_mk(d, ms[0], "v1")
    assert "<h1>Hidrologi Lanjut</h1>" in h and "RAHASIA" not in h and "Lama" not in h
    assert "<p>Analisis banjir.</p><p>Pokok bahasan kedua.</p>" in h and "<li>Chow (1988)</li><li>Linsley (1982)</li>" in h
    assert "Mampu menerapkan &lt;sains&gt; dasar." in h and "41302 Hidrologi Dasar" in h and "Flood analysis." in h
    assert "3 sks (kuliah 2, praktikum 1)" in h and "Pilihan" in h and "disahkan Ketua Program Studi pada 20 November 2026" in h
    assert 'href="bidang-rekayasa-sumber-daya-air.html">Rekayasa Sumber Daya Air</a>' in h
    assert 'href="laboratorium.html#lab-7">Lab Hidraulika</a>' in h and 'href="mk-41414-drainase-kota.html"' in h
    assert '"@type": "Course"' in h and '"courseCode": "41413"' in h
    g = hp.halaman_mk(d, ms[2], "v1")
    assert "2 · Sains dasar" in g and "Universitas (mata kuliah bersama)" in g and "setelah disahkan Ketua Program Studi" in g
    assert 'href="mk-41302-fisika-dasar.html"' in g and "Hidrologi Lanjut" not in g
    # Tautan dari sitemap, halaman bidang, dan peta situs mesin pencari.
    assert "https://x.id/mk-41413-hidrologi-lanjut.html" in hp.peta_situs("https://x.id", d, set())
    bs = hp.info_bidang(d)
    assert 'href="mk-41413-hidrologi-lanjut.html">Hidrologi Lanjut</a>' in hp.halaman_bidang(d, bs[0], bs, "v1")


def test_course_pages_written_and_stale_removed(tmp_path):
    d = _d_mk()
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("", encoding="utf-8")
    situs = tmp_path / "terbit"
    situs.mkdir()
    (situs / "mk-1-lama.html").write_text(f'<meta name="generator" content="{hp.GENERATOR}">', encoding="utf-8")
    (situs / "mk-catatan.html").write_text("buatan tangan", encoding="utf-8")
    hp.tulis_halaman_publik(situs, d, {"public_site": {"base_url": None}}, site)
    assert (situs / "mk-41413-hidrologi-lanjut.html").is_file() and not (situs / "mk-1-lama.html").exists()
    assert (situs / "mk-catatan.html").exists()


def test_laboratory_expertise_groups():
    """Laboratorium ke bidang keahlian (patch 147, pemilik 2026-11-22): halaman bidang dan halaman lab saling bertaut."""
    rows = [{"id": 7, "nama": "Lab Hidraulika", "ringkasan": "Laboratorium hidraulika.", "bidang": ["AIR", " ", "XYZ"]},
            {"id": 8, "nama": "Lab Beton", "ringkasan": "Laboratorium beton."}]
    xs = {x["id"]: x for x in hp.laboratorium_publik(rows, [], {}, [], {})}
    assert xs[7]["bidang"] == ["AIR", "XYZ"] and xs[8]["bidang"] == []
    d = _d_mk()
    bs = hp.info_bidang(d)
    assert 'href="laboratorium.html#lab-7">Lab Hidraulika</a>' in hp.halaman_bidang(d, bs[0], bs, "v1")
    h = hp.halaman_laboratorium(d, "v1")
    assert '<dt>Bidang keahlian</dt><dd><a href="bidang-rekayasa-sumber-daya-air.html">Rekayasa Sumber Daya Air</a></dd>' in h
    assert "XYZ" not in h and 'class="chip" href="mk-41413-hidrologi-lanjut.html"' in h


def test_academic_calendar_public():
    """Kalender akademik (patch 148, pemilik 2026-11-22): tampil saja, belum lewat > 60 hari, urut tanggal, kunci terbatas."""
    rows = [{"semester": "Ganjil 2026/2027", "kegiatan": "UAS", "kategori": "ujian", "mulai": "2026-12-14", "selesai": "2026-12-22",
             "catatan": " Jadwal per kelas di SIAKAD ", "tampil": True, "oleh": "admin@x.id"},
            {"semester": "Ganjil 2026/2027", "kegiatan": "KRS", "kategori": "registrasi", "mulai": "2026-08-01", "selesai": "2026-08-10"},
            {"semester": "Ganjil 2026/2027", "kegiatan": "Lama sekali", "mulai": "2026-07-01"},
            {"semester": "Ganjil 2026/2027", "kegiatan": "Disembunyikan", "mulai": "2026-12-01", "tampil": False},
            {"semester": "Genap 2026/2027", "kegiatan": "Yudisium", "kategori": "aneh", "mulai": "2027-02-01", "selesai": "2027-02-01"}]
    xs = hp.kalender_publik(rows, "2026-09-15")
    assert [x["kegiatan"] for x in xs] == ["KRS", "UAS", "Yudisium"]
    assert xs[1] == {"semester": "Ganjil 2026/2027", "kegiatan": "UAS", "kategori": "ujian", "mulai": "2026-12-14",
                     "selesai": "2026-12-22", "catatan": "Jadwal per kelas di SIAKAD"}
    assert xs[2]["kategori"] == "lainnya" and "selesai" not in xs[2]


def test_costs_scholarships_and_calendar_config():
    ps = {"costs_scholarships": [{"title": "PMB", "url": "https://pmb.contoh.ac.id", "note": "Jalur masuk."},
                                 {"title": "Beasiswa", "url": "https://contoh.ac.id/beasiswa"}],
          "academic_calendar_url": "https://contoh.ac.id/kalender"}
    assert not [g for g in bangun.validasi_situs_publik({"public_site": ps}) if "costs" in g or "calendar" in g]
    s = bangun.situs_publik({"public_site": ps})
    assert s["biaya"] == [{"judul": "PMB", "url": "https://pmb.contoh.ac.id", "ket": "Jalur masuk."},
                          {"judul": "Beasiswa", "url": "https://contoh.ac.id/beasiswa"}]
    assert s["kalender_resmi"] == "https://contoh.ac.id/kalender"
    salah = {"costs_scholarships": [{"title": "PMB", "url": "http://tidak-aman"}], "academic_calendar_url": "kalender"}
    g = bangun.validasi_situs_publik({"public_site": salah})
    assert [x for x in g if "costs_scholarships" in x] and [x for x in g if "academic_calendar_url" in x]


def test_costs_scholarships_page(tmp_path):
    """Biaya dan beasiswa (pemilik 2026-11-22): hanya tautan resmi, tanpa angka; dibuat hanya bila config diisi."""
    d = {**D, "situs": {"biaya": [{"judul": "PMB <resmi>", "url": "https://pmb.contoh.ac.id/admisi", "ket": "Jalur masuk."}],
                        "pendaftaran": "https://pmb.contoh.ac.id"}}
    h = hp.halaman_biaya(d, "v1")
    assert "<h1>Biaya dan beasiswa</h1>" in h and "PMB &lt;resmi&gt;" in h and 'href="https://pmb.contoh.ac.id/admisi"' in h
    assert "pmb.contoh.ac.id ↗" in h and "Daftar sekarang" in h and 'href="layanan-mahasiswa.html#kirim"' in h
    # Kotak di "Untuk orang tua dan wali" (bagian itu tampil mulai 3 kotak: akreditasi, dosen, biaya, ...).
    assert 'href="biaya-beasiswa.html"' in hp.halaman_calon({**d, "akreditasi_prodi": {"peringkat": "Unggul"}, "dtps": {"jumlah": 11}}, "v1")
    assert "https://x.id/biaya-beasiswa.html" in hp.peta_situs("https://x.id", d, set())
    assert "https://x.id/biaya-beasiswa.html" not in hp.peta_situs("https://x.id", D, set())
    assert 'href="biaya-beasiswa.html"' in hp.halaman_peta(d, set(), "v1")
    assert 'href="biaya-beasiswa.html"' not in hp.halaman_peta(D, set(), "v1")
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("", encoding="utf-8")
    situs = tmp_path / "terbit"
    hp.tulis_halaman_publik(situs, d, {"public_site": {"base_url": None}}, site)
    assert (situs / "biaya-beasiswa.html").is_file()
    hp.tulis_halaman_publik(situs, D, {"public_site": {"base_url": None}}, site)   # tautan dihapus dari config
    assert not (situs / "biaya-beasiswa.html").exists()


def test_english_course_pages():
    """Halaman mata kuliah berbahasa Inggris (pemilik 2026-11-22): hanya bila english.html dibuat; silabus disahkan saja."""
    d = _d_mk()
    d["situs"] = {**d["situs"], "prodi_en": "Civil Engineering"}
    d["situs"]["kelompok_keahlian"][0]["nama_en"] = "Water Resources Engineering"
    d["kurikulum"][0]["cpl"][0]["rumusan_en"] = "Able to apply <basic> science."
    d["kurikulum"][0]["mk"][0]["nama_en"] = "Advanced Hydrology"
    hp.lengkapi_mk_terbaru(d["kurikulum"], [])
    ms = hp.info_mk(d)
    assert ms[0]["berkas_en"] == "course-41413-advanced-hydrology.html" and ms[2]["berkas_en"] == "course-41301-geologi-dasar.html"
    ms[0]["silabus"] = {"deskripsi_en": "Flood analysis.", "pustaka": "Chow (1988)", "disahkan": "2026-11-20"}
    h = hp.halaman_mk_en(d, ms[0], "v1")
    assert '<html lang="en">' in h and "<h1>Advanced Hydrology</h1>" in h and "Hidrologi Lanjut" in h
    assert "Able to apply &lt;basic&gt; science." in h and "Flood analysis." in h and "<li>Chow (1988)</li>" in h
    assert "3 credits (lecture 2, practicum 1)" in h and "Elective" in h and "Water Resources Engineering" in h
    assert "approved by the Head of Study Program on 20 November 2026" in h
    assert 'href="mk-41413-hidrologi-lanjut.html" lang="id" hreflang="id">Bahasa Indonesia' in h
    assert 'href="course-41414-drainase-kota.html"' in h and '"inLanguage": "en"' in h
    g = hp.halaman_mk_en(d, ms[2], "v1")
    assert "once approved by the Head of Study Program" in g and "University (shared course)" in g
    # Halaman Indonesia menaut ke kembarannya; english.html menaut ke halaman mata kuliah.
    assert 'href="course-41413-advanced-hydrology.html" lang="en" hreflang="en">English' in hp.halaman_mk(d, ms[0], "v1")
    assert 'href="course-41301-geologi-dasar.html">Geologi Dasar</a>' in hp.halaman_english(d, "v1")
    assert "https://x.id/course-41413-advanced-hydrology.html" in hp.peta_situs("https://x.id", d, set())
    # Tanpa nama prodi Inggris: tidak ada tautan English dan tidak masuk sitemap.
    d2 = _d_mk()
    assert "English</a>" not in hp.halaman_mk(d2, hp.info_mk(d2)[0], "v1")
    assert "course-" not in hp.peta_situs("https://x.id", d2, set())


def _baris_ta():
    return [{"id": 1, "tahap": "sidang_akhir", "status": "selesai", "hasil": "lulus", "judul": "Analisis banjir Ciliwung",
             "nama_mahasiswa": "RAHASIA Mahasiswa", "nim": "105999", "pembimbing": ["001"], "tanggal": "2026-08-20", "bidang": None},
            {"id": 2, "tahap": "sidang_akhir", "status": "selesai", "hasil": "lulus_revisi", "judul": "Beton <mutu> tinggi",
             "nama_mahasiswa": "X", "pembimbing": ["002", "001"], "tanggal": "2025-02-10", "bidang": "STR"},
            {"id": 3, "tahap": "sidang_akhir", "status": "selesai", "hasil": "mengulang", "judul": "Mengulang", "pembimbing": ["001"],
             "tanggal": "2026-01-01"},
            {"id": 4, "tahap": "seminar_proposal", "status": "selesai", "judul": "Baru proposal", "pembimbing": ["001"], "tanggal": "2026-01-01"},
            {"id": 5, "tahap": "sidang_akhir", "status": "terjadwal", "judul": "Belum sidang", "pembimbing": ["001"], "tanggal": "2026-12-01"},
            {"id": 6, "tahap": "sidang_akhir", "status": "selesai", "judul": "Disembunyikan", "pembimbing": ["001"], "tanggal": "2026-01-01",
             "sembunyikan_publik": True},
            {"id": 7, "tahap": "sidang_akhir", "status": "selesai", "judul": "Tanpa pembimbing prodi", "pembimbing": ["999"], "tanggal": "2024-05-01"}]


def _d_ta():
    dn = {"001": {"nama": "Dr. Ani", "slug": "ani"}, "002": {"nama": "Budi", "slug": None}}
    dosen = [{"nama": "Ani", "slug": "ani", "kelompok": "AIR"}]
    xs = hp.arsip_ta_publik(_baris_ta(), dn, dosen)
    return {**D, "arsip_ta": xs, "dosen": dosen,
            "situs": {"kelompok_keahlian": [{"kode": "AIR", "nama": "Rekayasa Sumber Daya Air"}, {"kode": "STR", "nama": "Rekayasa Struktur"}]}}


def test_thesis_archive_public():
    """Arsip judul TA (pemilik 2026-11-22): sidang akhir selesai dan tidak mengulang; tanpa nama/NIM; bidang kolom atau pembimbing."""
    xs = _d_ta()["arsip_ta"]
    assert [x["id"] for x in xs] == [1, 2, 7]
    assert xs[0] == {"id": 1, "judul": "Analisis banjir Ciliwung", "tahun": 2026, "bulan": 8, "bidang": "AIR",
                     "pembimbing": [{"nama": "Dr. Ani", "slug": "ani"}]}           # bidang dari pembimbing pertama
    assert xs[1]["bidang"] == "STR" and xs[1]["pembimbing"] == [{"nama": "Budi"}, {"nama": "Dr. Ani", "slug": "ani"}]
    assert "bidang" not in xs[2] and xs[2]["pembimbing"] == []
    teks = json.dumps(xs, ensure_ascii=False)
    assert "RAHASIA" not in teks and "105999" not in teks and "nim" not in teks


def test_thesis_archive_page_and_links():
    d = _d_ta()
    h = hp.halaman_arsip_ta(d, "v1")
    assert "<h1>Arsip tugas akhir</h1>" in h and "Nama mahasiswa tidak dicantumkan" in h and "2024–2026" in h
    assert 'id="bidang-air"' in h and 'href="bidang-rekayasa-sumber-daya-air.html">Rekayasa Sumber Daya Air</a>' in h
    assert 'id="bidang-lain"' in h and "Tanpa pembimbing prodi" in h and "Beton &lt;mutu&gt; tinggi" in h
    assert 'href="dosen/ani.html">Dr. Ani</a>' in h and 'id="ta-1"' in h and "RAHASIA" not in h
    assert "Arsip judul tugas akhir akan tampil" in hp.halaman_arsip_ta({**D, "arsip_ta": []}, "v1")
    bs = hp.info_bidang(d)
    hb = hp.halaman_bidang(d, bs[0], bs, "v1")
    assert "Tugas akhir terbaru" in hb and "Analisis banjir Ciliwung" in hb and 'href="tugas-akhir.html#bidang-air"' in hb
    # Sitemap mulai 5 judul; peta situs mulai 1.
    assert "https://x.id/tugas-akhir.html" not in hp.peta_situs("https://x.id", d, set())
    assert "https://x.id/tugas-akhir.html" in hp.peta_situs("https://x.id", {**d, "arsip_ta": d["arsip_ta"] * 2}, set())
    assert 'href="tugas-akhir.html"' in hp.halaman_peta(d, set(), "v1")
    assert 'href="tugas-akhir.html"' not in hp.halaman_peta(D, set(), "v1")


def test_contact_page():
    """Halaman Kontak (pemilik 2026-11-22): dari config contact; peta lewat tautan; tanpa kontak: tidak dibuat."""
    d = {**D, "situs": {"kontak": {"address": "Jl. Contoh 1, Jakarta", "phone": "+62 812-1 (Pusat Informasi)", "email": "info@contoh.ac.id"},
                        "sosial": {"instagram": "https://instagram.com/contoh"}, "pendaftaran": "https://pmb.contoh.ac.id"}}
    h = hp.halaman_kontak(d, "v1")
    assert "<h1>Kontak</h1>" in h and "Jl. Contoh 1, Jakarta" in h
    assert 'href="https://www.google.com/maps/search/?api=1&amp;query=Jl.%20Contoh%201%2C%20Jakarta"' in h
    assert 'href="tel:+628121"' in h and 'href="mailto:info@contoh.ac.id"' in h and "Jam layanan" not in h
    assert 'href="layanan-mahasiswa.html#kirim"' in h and "https://instagram.com/contoh" in h and "Pendaftaran mahasiswa baru" in h
    assert "https://x.id/kontak.html" in hp.peta_situs("https://x.id", d, set())
    assert "https://x.id/kontak.html" not in hp.peta_situs("https://x.id", D, set())


def test_rss_feed(tmp_path):
    """Umpan RSS kabar dan prestasi (pemilik 2026-11-22): terbaru dulu, alamat lengkap; hanya bila alamat situs diketahui."""
    d = {**D, "kabar": [{"id": 9, "judul": "Kunjungan <bendungan>", "tanggal": "2026-11-01", "ringkasan": "Ke bendungan.",
                         "jenis": "kunjungan", "tempat": "", "tautan": "", "_foto": []}],
         "prestasi": [{"id": 3, "capaian": "Juara 1", "kegiatan": "Lomba Jembatan", "tahun": 2026, "bulan": 5, "tingkat": "nasional"}]}
    x = hp.umpan_rss(d, "https://x.id")
    root = ET.fromstring(x)
    items = root.findall("./channel/item")
    assert [i.findtext("title") for i in items] == ["Kunjungan <bendungan>", "Juara 1 — Lomba Jembatan"]
    assert items[0].findtext("link") == "https://x.id/kabar.html#kabar-9" and items[1].findtext("category") == "Prestasi mahasiswa"
    assert items[0].findtext("pubDate").startswith("Sun, 01 Nov 2026")
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("", encoding="utf-8")
    situs = tmp_path / "terbit"
    hp.tulis_halaman_publik(situs, d, {"public_site": {"base_url": "https://x.id"}}, site)
    assert (situs / "feed.xml").is_file() and 'href="feed.xml"' in (situs / "kabar.html").read_text(encoding="utf-8")
    situs2 = tmp_path / "tanpa-alamat"
    hp.tulis_halaman_publik(situs2, d, {"public_site": {"base_url": None}}, site)
    assert not (situs2 / "feed.xml").exists() and 'href="feed.xml"' not in (situs2 / "kabar.html").read_text(encoding="utf-8")


def test_tab_icon_on_every_page(tmp_path):
    """Ikon tab = lambang Universitas Pertamina (pemilik 2026-11-22): semua halaman statis dan yang dibangkitkan."""
    root = Path(__file__).resolve().parents[1]
    assert (root / "site" / "favicon.png").is_file() and (root / "site" / "apple-touch-icon.png").is_file()
    tanpa = [f.name for f in (root / "site").glob("*.html") if 'rel="icon"' not in f.read_text(encoding="utf-8")]
    assert tanpa == []
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("", encoding="utf-8")
    situs = tmp_path / "terbit"
    hp.tulis_halaman_publik(situs, D, {"public_site": {"base_url": None}}, site)
    assert 'href="favicon.png"' in (situs / "peta-situs.html").read_text(encoding="utf-8")
    dosen = next((situs / "dosen").glob("*.html")).read_text(encoding="utf-8")
    assert 'href="../favicon.png"' in dosen and dosen.count('rel="icon"') == 1
    assert hp.pasang_ikon(hp.pasang_ikon("<head></head>")).count('rel="icon"') == 1


def test_light_header_data_manifest_and_404(tmp_path):
    """Situs lebih ringan, manifest, halaman 404 (pemilik 2026-11-22)."""
    d = {**D, "situs": {"kontak": {"email": "info@contoh.ac.id"}, "pendaftaran": "https://pmb.contoh.ac.id", "karier": ["x"] * 50},
         "kabar": [{"id": 1, "foto": ["a.jpg", "b.jpg"]}], "prestasi": [{"id": 2, "foto": ["c.jpg"]}], "arsip_ta": [{"id": 3}],
         "akreditasi_prodi": {"peringkat": "Unggul"}}
    k = hp.data_kerangka(d)
    assert k["jumlah"] == {"kabar": 1, "foto": 3, "arsip_ta": 1}
    assert k["situs"] == {"kontak": {"email": "info@contoh.ac.id"}, "pendaftaran": "https://pmb.contoh.ac.id"}   # tanpa karier dsb.
    assert "dosen" not in k and "publikasi" not in k and k["akreditasi_prodi"] == {"peringkat": "Unggul"}
    m = hp.manifes(d, "#084999")
    assert m["short_name"] == "Teknik Contoh" and m["name"] == "Program Studi Teknik Contoh Universitas Contoh"
    assert m["theme_color"] == "#084999" and [i["sizes"] for i in m["icons"]] == ["192x192", "512x512", "180x180"]
    assert "theme_color" not in hp.manifes(d, "")
    h = hp.halaman_404(d, "v1", "https://x.id/cv-site")
    assert '<base href="https://x.id/cv-site/">' in h and '<meta name="robots" content="noindex">' in h
    assert "<h1>Halaman tidak ditemukan</h1>" in h and 'href="kontak.html">Kontak' in h
    assert r"replace(/\.html?$/i, '')" in h and r"replace(/\b\d{3,}\b/g, '')" in h
    assert "<base" not in hp.halaman_404(D, "v1", "")
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("", encoding="utf-8")
    (site / "tema.css").write_text(":root{\n  --biru:#084999;   --biru-rgb:8,73,153;\n}", encoding="utf-8")
    situs = tmp_path / "terbit"
    d2 = {**d, "kabar": [], "prestasi": [], "arsip_ta": []}   # daftar contoh di atas tidak lengkap untuk membangun halaman
    hp.tulis_halaman_publik(situs, d2, {"public_site": {"base_url": "https://x.id/cv-site"}}, site)
    kj = json.loads((situs / "kerangka.json").read_text(encoding="utf-8"))
    assert kj["jumlah"] == {"kabar": 0, "foto": 0, "arsip_ta": 0} and kj["situs"]["pendaftaran"] == "https://pmb.contoh.ac.id"
    assert json.loads((situs / "manifest.webmanifest").read_text(encoding="utf-8"))["theme_color"] == "#084999"
    t404 = (situs / "404.html").read_text(encoding="utf-8")
    assert 'rel="canonical"' not in t404 and 'href="favicon.png"' in t404
    prof = (situs / "profil-prodi.html").read_text(encoding="utf-8")
    assert "fetch('kerangka.json', {cache: 'no-cache'})" in prof and "fetch('data.json" not in prof and 'href="manifest.webmanifest"' in prof
    assert 'href="../manifest.webmanifest"' in next((situs / "dosen").glob("*.html")).read_text(encoding="utf-8")
    root = Path(__file__).resolve().parents[1]
    assert [f.name for f in (root / "site").glob("*.html") if 'rel="manifest"' not in f.read_text(encoding="utf-8")] == []
    assert (root / "site" / "icon-512.png").is_file()


def test_json_fetched_with_revalidation_not_cache_busting(tmp_path):
    """Data situs memakai cache peramban + ETag (304 bila tidak berubah), bukan ?v=Date.now() (pemilik 2026-11-22)."""
    root = Path(__file__).resolve().parents[1]
    lama = re.compile(r"fetch\('[^']+\?v=' \+ Date\.now\(\)")   # ambang.js <script> di monitoring.html bukan fetch
    sumber = [*(root / "site").glob("*.html"), *(root / "site").glob("*.js"), root / "halaman_publik.py"]
    assert [f.name for f in sumber if lama.search(f.read_text(encoding="utf-8"))] == []
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("", encoding="utf-8")
    situs = tmp_path / "terbit"
    hp.tulis_halaman_publik(situs, D, {"public_site": {"base_url": "https://x.id/cv-site"}}, site)
    terbit = list(situs.rglob("*.html"))
    assert terbit and [f.name for f in terbit if lama.search(f.read_text(encoding="utf-8"))] == []
    assert any("{cache: 'no-cache'}" in f.read_text(encoding="utf-8") for f in terbit)


def _kontras(a, b):
    """Rasio kontras WCAG 2.x dua warna #RRGGBB."""
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    x, y = sorted((lum(a), lum(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


def test_accessibility_audit_fixes(tmp_path):
    """Temuan audit axe-core 2026-11-22: kontras teks samar, satu landmark banner, footer 404, halaman dosen."""
    root = Path(__file__).resolve().parents[1]
    tema = (root / "site" / "tema.css").read_text(encoding="utf-8")
    warna = dict(re.findall(r"--(muted|bg):(#[0-9A-Fa-f]{6})", tema))
    assert _kontras(warna["muted"], warna["bg"]) >= 4.5 and _kontras(warna["muted"], "#FFFFFF") >= 4.5
    # Satu landmark banner: hanya kepala situs dari kerangka.js yang <header>.
    assert [f.name for f in (root / "site").glob("*.html") if "<header" in f.read_text(encoding="utf-8")] == []
    assert (root / "site" / "kerangka.js").read_text(encoding="utf-8").count("<header") == 1
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("", encoding="utf-8")
    situs = tmp_path / "terbit"
    hp.tulis_halaman_publik(situs, D, {"public_site": {"base_url": "https://x.id/cv-site"}}, site)
    terbit = list(situs.rglob("*.html"))
    assert [f.name for f in terbit if "<header" in f.read_text(encoding="utf-8")] == []
    # 404: gaya daftar saran tidak boleh mengenai daftar di footer (kotak putih di kaki biru).
    t404 = (situs / "404.html").read_text(encoding="utf-8")
    assert "main ul{" in t404 and "main li a{" in t404 and "main button{" in t404
    assert not re.search(r"(?m)^(ul|li a|form|input|button)\{", t404)
    # Halaman dosen: tautan bidang terbaca di hero biru; pita angka berada di wilayah berlabel.
    dosen = next((situs / "dosen").glob("*.html")).read_text(encoding="utf-8")
    assert ".bidang a{color:#fff" in dosen and '<section class="angka" aria-label="Ringkasan karya">' in dosen
    # Hero bekas <header> tetap di dalam landmark (aturan axe "region").
    assert 'class="hero" role="region" aria-label="Pembuka halaman"' in dosen
    assert 'class="hero" role="region" aria-label="Pembuka halaman"' in (root / "site" / "kurikulum.html").read_text(encoding="utf-8")


def test_no_layout_shift_while_data_loads():
    """Audit kecepatan 2026-11-22: CLS 0,2-0,8 di halaman yang menggambar isi dari data.json. Kaki halaman menunggu isi
    tenang; teks "Memuat…" berada di kotak yang nanti terisi, bukan di bawahnya (yang lalu terdorong)."""
    root = Path(__file__).resolve().parents[1] / "site"
    kerangka = (root / "kerangka.js").read_text(encoding="utf-8")
    assert "tampilkanKakiSetelahTenang(kaki, document.getElementById('krKepala'))" in kerangka
    assert "fetchBerjalan" in kerangka and "KAKI_MAKS_MS" in kerangka
    tempat = {"kurikulum.html": 'id="angka"><div><span>Memuat…', "keahlian.html": 'id="angka"><div><span>Memuat…',
              "sdgs.html": 'id="angka">Memuat…', "kinerja.html": 'id="ringkas" aria-label="Angka utama"><p class="kosong">Memuat…',
              "daftar.html": '<p id="hKet">Memuat…</p>'}
    for nama, cari in tempat.items():
        t = (root / nama).read_text(encoding="utf-8")
        assert cari in t, nama
        assert not re.search(r'id="isi"><p class="kosong">Memuat…', t), nama   # tidak ada "Memuat…" di bawah kepala
    for nama in ("kurikulum.html", "keahlian.html", "sdgs.html"):
        t = (root / nama).read_text(encoding="utf-8")
        assert 'id="hProdi">&nbsp;</div>' in t and "('angka').textContent = ''" in t, nama   # galat: teks muat dihapus
    assert 'id="hProdi">&nbsp;</div>' in (root / "layanan-mahasiswa.html").read_text(encoding="utf-8")
