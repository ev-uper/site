"""Fictional sample data for "python coba_lokal.py": one JSON read by bangun.py (through a
fake REST server) and by the mock client in the pages (coba/mock-sb.js).

Started as the data for the promotional video (2026-11-07); owner 2026-11-12: ship it with
the template so other programmes can try the site on their own computer first. Everything
is invented ("Contoh"); nothing here may come from a real programme.
"""
from __future__ import annotations

import json
import random
import re
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

R = random.Random(7)


def uid(s):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "contoh/" + s))


DRV = "https://drive.google.com/file/d/contohberkas{:012d}abcdef/view"
n_url = [0]


def url():
    n_url[0] += 1
    return DRV.format(n_url[0])


NAMA = [("Adi", "lektor_kepala", "S3"), ("Budi", "lektor", "S3"), ("Cici", "lektor", "S3"), ("Dewi", "lektor", "S2"),
        ("Eko", "asisten_ahli", "S3"), ("Fitri", "lektor", "S3"), ("Gani", "asisten_ahli", "S2"), ("Hana", "lektor", "S3"),
        ("Indra", "guru_besar", "S3"), ("Joko", "asisten_ahli", "S2"), ("Kartika", "lektor", "S2"), ("Lina", "tenaga_pengajar", "S2")]
KEAHLIAN = ["Struktur", "Geoteknik", "Hidrologi", "Transportasi", "Manajemen konstruksi", "Lingkungan"]
# Kode kelompok keahlian (dosen.kelompok_keahlian, 110/149) sejajar KEAHLIAN; kode = config.yaml public_site expertise_groups
# dan pasangan ta_kk_dekat di mock-sb.js. Tanpa ini daftar Pembimbing 1 TA kosong di mode coba/latihan (2026-11-24).
KK_KODE = ["STR", "GEO", "AIR", "TRN", "MRK", "AIR"]


def dosen():
    xs = [dict(id=uid("admin"), nidn="0000000099", nama="Admin Contoh", email="admin@contoh.ac.id", peran="admin", aktif=True,
               dtps=False, kategori="tetap", tim_penyusun=True, jabatan="lektor", pendidikan="S3", bidang_keahlian="Struktur", sesuai_kompetensi_inti=True, sesuai_keahlian_mk=True, sertifikat=[],
               riwayat_pendidikan=[dict(jenjang="S1", bidang="Teknik Contoh", institusi="Universitas Contoh"),
                                   dict(jenjang="S3", bidang="Struktur", institusi="Institut Contoh")])]
    for i, (n, j, p) in enumerate(NAMA):
        xs.append(dict(id=uid(n), nidn=f"00000000{i + 10}", nama=f"{n} Contoh", email=f"{n.lower()}@contoh.ac.id", peran="dosen", aktif=True,
                       dtps=i < 10, kategori="tetap" if i < 11 else "tidak_tetap", jabatan=j, pendidikan=p, tim_penyusun=i < 4,
                       bidang_keahlian=KEAHLIAN[i % 6], kelompok_keahlian=KK_KODE[i % 6], sesuai_kompetensi_inti=True, sesuai_keahlian_mk=True,
                       nomor_serdos=f"1{i:04d}" if i < 8 else None, sinta_id=f"60{i:04d}", scopus_id=None, orcid=None,
                       riwayat_pendidikan=[dict(jenjang="S1", bidang="Teknik Contoh", institusi="Universitas Contoh"),
                                           dict(jenjang=p, bidang=KEAHLIAN[i % 6], institusi="Institut Contoh")],
                       sertifikat=[], mk_ps_lain=None))
    # Peran pimpinan dan asesor (uji asap dan bilah MODE COBA, 2026-11-12): bukan DTPS, supaya hitungan dosen tetap sama.
    for n, peran, nidn in (("Pimpinan", "pimpinan", "0000000097"), ("Asesor", "asesor", "0000000098")):
        xs.append(dict(id=uid(n.lower()), nidn=nidn, nama=f"{n} Contoh", email=f"{n.lower()}@contoh.ac.id", peran=peran, aktif=True,
                       dtps=False, kategori="tidak_tetap", tim_penyusun=False, jabatan=None, pendidikan="S3", sertifikat=[],
                       riwayat_pendidikan=[]))
    return xs


TOPIK = ["Perkuatan balok beton dengan serat alami", "Model banjir sungai perkotaan", "Stabilisasi tanah lunak dengan kapur",
         "Analisis kemacetan simpang bersinyal", "Keterlambatan proyek gedung bertingkat", "Kualitas air sungai di kawasan industri",
         "Ketahanan gempa rumah sederhana", "Prakiraan hujan untuk irigasi", "Daur ulang aspal jalan", "Pemodelan keruntuhan lereng",
         "Efisiensi rantai pasok beton", "Pengelolaan sampah konstruksi"]


def karya(ds):
    dt = [d for d in ds if d["dtps"]]
    xs, pen = [], []
    n = 0

    def tambah(kat, judul, tahun, **k):
        nonlocal n
        n += 1
        i = uid(f"karya{n}")
        pel = dt[n % len(dt)]
        r = dict(id=i, kategori=kat, judul=judul, judul_norm=judul.lower(), tahun=tahun, status="terverifikasi", tingkat="nasional",
                 dilaporkan_oleh=pel["id"], dibuat_pada=f"{tahun}-06-01T00:00:00Z", bulan=R.randint(1, 12), relevan_visi=True,
                 sumber_dana=None, bukti_url=url(), url=None, keterangan="Skema contoh")
        r.update(k)
        xs.append(r)
        pen.append(dict(karya_id=i, dosen_id=pel["id"], peran="ketua" if kat in ("penelitian", "pkm") else "penulis_pertama",
                        korespondensi=True, ditambahkan_sendiri=False))
        ang = dt[(n + 3) % len(dt)]
        pen.append(dict(karya_id=i, dosen_id=ang["id"], peran="anggota", korespondensi=False, ditambahkan_sendiri=False))

    idx = ["scopus_q1", "scopus_q2", "scopus_q3", "sinta_1_2", "sinta_3_4", "sinta_3_4"]
    for t in (2023, 2024, 2025, 2026):
        for j in range(9):
            ix = idx[j % 6]
            tambah("publikasi", f"{TOPIK[(j + t) % 12]}: studi kasus {t}-{j + 1}", t, jenis="jurnal" if j % 4 else "prosiding",
                   nama_terbitan="Jurnal Teknik Contoh" if "sinta" in ix else "Journal of Example Engineering", indeksasi=ix,
                   tingkat="internasional" if "scopus" in ix else "nasional", doi=f"10.5555/contoh.{t}.{j + 1}", jumlah_sitasi=R.randint(0, 14),
                   tema_id=j % 3 + 1)
        for j in range(4):
            tambah("penelitian", f"Penelitian {TOPIK[(j * 2 + t) % 12].lower()} tahun {t}", t,
                   skema_kode=["int_reguler", "pf", "int_kolab_dn", "mandiri"][j],
                   sumber_dana=["perguruan_tinggi", "dalam_negeri", "perguruan_tinggi", "mandiri"][j], besaran_dana=[25, 120, 40, 5][j] * 1000000,
                   nama_pemberi_dana="Universitas Contoh", tkt=3 + j, tema_id=j % 3 + 1, keterlibatan_mhs="tugas_akhir")
        for j in range(3):
            tambah("pkm", f"Pendampingan warga: {TOPIK[(j * 3 + t) % 12].lower()} {t}", t, skema_kode=["int_lainnya", "mandiri", "pemda"][j],
                   sumber_dana=["perguruan_tinggi", "mandiri", "dalam_negeri"][j], besaran_dana=[15, 3, 50][j] * 1000000,
                   nama_pemberi_dana="Universitas Contoh", tema_id=j % 3 + 1, keterlibatan_mhs="lainnya")
        tambah("luaran", f"Hak cipta perangkat lunak {TOPIK[t % 12].lower()}", t, sub_jenis="hak_cipta", jenis="haki_paten")
        tambah("rekognisi", f"Narasumber kuliah tamu {t}", t, sub_jenis="narasumber")
    xs[-5]["status"] = "diajukan"
    xs[-9]["status"] = "diajukan"
    return xs, pen


def id_(rows):
    return [dict(id=i + 1, **r) for i, r in enumerate(rows)]


def tabel_lain(ds, ks):
    ts = 2026
    ta = [f"{y}/{y + 1}" for y in (2023, 2024, 2025)]
    dt = [d for d in ds if d["dtps"]]
    t = {}
    t["pengaturan"] = [dict(kunci="bop", nilai=21000000, keterangan="Butir 9"), dict(kunci="kerjasama_pendidikan_3th", nilai=5, keterangan="Butir 6-I"),
                       dict(kunci="ndtt", nilai=2, keterangan="Butir 26"), dict(kunci="sks_basic_sciences", nilai=30, keterangan="Butir 19"),
                       dict(kunci="kib_3th", nilai=12, keterangan="Butir 36")]
    t["ref_kata_visi"] = [dict(kata=k) for k in ("banjir", "beton", "tanah", "jalan", "konstruksi")]
    t["ref_tema_peta_jalan"] = id_([dict(nama=n, jenis="keduanya", aktif=True, urutan=i, keterangan="")
                                    for i, n in enumerate(["Infrastruktur tangguh", "Air dan lingkungan", "Konstruksi berkelanjutan"])])
    mk = ["Matematika Teknik", "Fisika Dasar", "Mekanika Bahan", "Hidrologi", "Beton Bertulang", "Mekanika Tanah", "Rekayasa Lalu Lintas",
          "Manajemen Proyek", "Struktur Baja", "Perancangan Terpadu"]
    t["ref_mata_kuliah"] = id_([dict(kode=f"TC{i + 101}", nama=n, sks=3, sks_kuliah=3, sks_seminar=0, sks_praktikum=0, semester=i % 8 + 1, inti=i > 1,
                                     aktif=True, urutan=i, rps_ada=True, rps_url=url(), unit_penyelenggara="prodi", basic_science=i < 2, capstone=i == 9,
                                     pengampu=[dt[i % 10]["nidn"], dt[(i + 1) % 10]["nidn"]],
                                     # 158: koordinator = dosen pertama, tim = dosen kedua (pemilik 2026-11-23)
                                     koordinator_nidn=dt[i % 10]["nidn"], kurikulum="K26") for i, n in enumerate(mk)])
    # Penyusunan kelas (136) dan jadwal kuliah (150, pemilik 2026-11-22): kelas Genap 2026/2027 contoh; satu sudah berjadwal
    # dengan ruang, sisanya untuk dicoba (unduh masukan, isi manual, sahkan sebagai Admin Contoh = Kaprodi).
    t["kelas_kuliah"] = [dict(id=i + 1, tahun_akademik="2026/2027", semester="Genap", kurikulum="K26", kode_mk=kode, kelas=kls, kapasitas=40,
                              angkatan=None, catatan=None, oleh=None) for i, (kode, kls) in enumerate(
                             [("TC102", "A"), ("TC110", "A"), ("TC104", "A"), ("TC104", "B")])]
    t["kelas_dosen"] = [dict(kelas_id=i + 1, dosen_id=dt[d]["id"], peran="koordinator", pertemuan=None, urutan=0)
                        for i, d in enumerate([1, 9, 3, 3])]
    t["jadwal_kuliah"] = [dict(kelas_id=1, hari=1, mulai="07:30:00", selesai="09:10:00", ruang="Ruang contoh 1.01", kunci=False, oleh=None)]
    t["jadwal_kuliah_sah"] = []
    # Ekuivalensi K21 -> K26 (134, pemilik 2026-11-21): MK lama contoh dengan pola 1:1, 1:2, 2:1, tidak berlanjut, dan satu MK
    # tanpa baris (peringatan). Admin Contoh = Kaprodi, Pimpinan Contoh (bukan DTPS) = Dekan, supaya alur sahkan -> tetapkan bisa dicoba.
    lama = [("LA101", "Matematika Teknik I", 3, 1, "wajib"), ("LA102", "Fisika Dasar", 3, 1, "wajib"), ("LA103", "Mekanika Tanah", 3, 4, "wajib"),
            ("LA104", "Struktur Baja I", 2, 5, "wajib"), ("LA105", "Struktur Baja II", 2, 6, "wajib"), ("LA106", "Hidrologi dan Drainase", 3, 4, "wajib"),
            ("LA107", "Beton Prategang", 3, None, "pilihan"), ("LA108", "Ilmu Lingkungan", 2, 2, "wajib")]
    t["ref_mata_kuliah"] += [dict(id=len(t["ref_mata_kuliah"]) + i + 1, kode=k, nama=n, sks=s, semester=smt, sifat=sf, aktif=False, urutan=i,
                                  unit_penyelenggara="prodi", kurikulum="K21") for i, (k, n, s, smt, sf) in enumerate(lama)]
    # MK universitas (pemilik 2026-11-24): PIC prodi di koordinator_nidn tanpa tim; satu dengan sisa pengampu lama, satu tanpa PIC.
    mku = [("01X01", "Kalkulus 1", 1, [dt[2]["nidn"], dt[3]["nidn"]], dt[2]["nidn"]), ("01102", "Pancasila", 2, [dt[4]["nidn"]], dt[4]["nidn"]),
           ("01104", "Bahasa Indonesia", 1, [], None)]
    t["ref_mata_kuliah"] += [dict(id=len(t["ref_mata_kuliah"]) + i + 1, kode=k, nama=n, sks=2, semester=smt, sifat="wajib", aktif=True, urutan=20 + i,
                                  unit_penyelenggara="universitas", pengampu=pg, koordinator_nidn=pic, kurikulum="K26")
                             for i, (k, n, smt, pg, pic) in enumerate(mku)]
    pad = [("LA101", "TC101", "1:1", "Bab 7 Tabel 7-2 no 1"), ("LA102", "TC102", "nama sama", "Nama sama di K21 dan K26"),
           ("LA103", "TC106", "1:2", "Bab 7 Tabel 7-3 no 1"), ("LA103", "TC103", "1:2", "Bab 7 Tabel 7-3 no 1"),
           ("LA104", "TC109", "2:1", "Bab 7 Tabel 7-4 no 1"), ("LA105", "TC109", "2:1", "Bab 7 Tabel 7-4 no 2"),
           ("LA106", "TC104", "1:1", "Bab 7 Tabel 7-2 no 2"), ("LA107", None, None, "MK pilihan tidak diselenggarakan di K26")]
    t["ref_mk_padanan"] = id_([dict(kurikulum_lama="K21", kode_lama=a, kurikulum_baru="K26" if b else None, kode_baru=b, model=m,
                                    tidak_berlanjut=not b, catatan=c) for a, b, m, c in pad])
    # Keadaan contoh: revisi 1 sudah ditetapkan (tampil di ekuivalensi-kurikulum.html), lalu padanan disunting -> draf lagi.
    ringkas = lambda m: {k: m.get(k) for k in ("kode", "nama", "sks", "semester", "sifat")}
    terbit = dict(kurikulum_lama="K21", kurikulum_baru="K26", revisi=1,
                  mk_lama=[ringkas(m) for m in t["ref_mata_kuliah"] if m["kurikulum"] == "K21"],
                  mk_baru=[ringkas(m) for m in t["ref_mata_kuliah"] if m["kurikulum"] == "K26"],
                  padanan=[{k: p[k] for k in ("kode_lama", "kode_baru", "model", "tidak_berlanjut", "catatan")} for p in t["ref_mk_padanan"]]
                          + [dict(kode_lama="LA108", kode_baru=None, model=None, tidak_berlanjut=True, catatan="Contoh revisi 1")],
                  disahkan=dict(nama="Admin Contoh", pada="2026-11-01T09:00:00+07:00"),
                  ditetapkan=dict(nama="Pimpinan Contoh", pada="2026-11-02T10:00:00+07:00"))
    t["mk_padanan_sah"] = [dict(kurikulum_lama="K21", kurikulum_baru="K26", status="draf", revisi=1, terbit=terbit,
                                terbit_pada="2026-11-02T10:00:00+07:00", sah_nama="Admin Contoh", sah_pada="2026-11-01T09:00:00+07:00")]
    t["mk_padanan_sah_log"] = id_([dict(kurikulum_lama="K21", kurikulum_baru="K26", aksi=a, oleh_nama=n, revisi=r, pada=w, catatan=c)
                                   for a, n, r, w, c in [("sahkan", "Admin Contoh", 0, "2026-11-01T09:00:00+07:00", None),
                                                         ("tetapkan", "Pimpinan Contoh", 1, "2026-11-02T10:00:00+07:00", None),
                                                         ("berubah", "Admin Contoh", 1, "2026-11-10T08:00:00+07:00",
                                                          "Padanan disunting; perlu disahkan dan ditetapkan lagi.")]])
    t["koordinator"] = id_([dict(dosen_id=uid("admin"), jabatan="kaprodi", mulai="2026-01-01", selesai=None),
                            dict(dosen_id=uid("pimpinan"), jabatan="dekan", mulai="2026-01-01", selesai=None)])
    # Jadwal berhalangan (132/135): slot jam dan hari contoh (fiktif; jam kuliah sebenarnya diatur admin di halaman).
    t["jadwal_slot"] = id_([dict(urutan=i + 1, label=f"Jam {i + 1}", mulai=m, selesai=s, aktif=True)
                            for i, (m, s) in enumerate([("07:30", "09:10"), ("09:20", "11:00"), ("13:00", "14:40"), ("15:00", "16:40")])])
    t["jadwal_hari"] = [dict(hari=h) for h in range(1, 6)]
    # OBE (cpmk.html, pemilik 2026-11-17): CPL contoh berindikator bernomor dan peta MK-CPL, supaya CPMK/templat bisa dicoba.
    t["ref_cpl"] = id_([dict(kurikulum="K26", kode=k, ranah=r, rumusan=n, indikator=ind, urutan=i) for i, (k, r, n, ind) in enumerate([
        ("A", "Sikap", "Mampu bertindak etis dan bertanggung jawab dalam praktik keteknikan.",
         "1. Mengidentifikasi isu etika profesi 2. Menentukan tindakan yang sesuai etika"),
        ("B", "Pengetahuan", "Mampu menerapkan matematika, sains, dan prinsip rekayasa.",
         "1. Menerapkan matematika teknik 2. Menerapkan mekanika 3. Menganalisis data hasil uji"),
        ("C", "Keterampilan", "Mampu merancang sistem atau komponen infrastruktur.",
         "1. Merumuskan kebutuhan desain 2. Menyusun alternatif desain")])])
    # Ruang KP contoh (105, pemilik 2026-11-18): KP selesai di mitra (nama ditulis berbeda), magang, berjalan, diperiksa.
    kp = [("9999000101", "Mahasiswa Satu", "PT Konstruksi Contoh", "kp", "disetujui", "selesai", "2026-02-02", "Adi"),
          ("9999000102", "Mahasiswa Dua", "PT. Konstruksi  contoh", "kp", "disetujui", "selesai", "2025-07-01", "Adi"),
          ("9999000103", "Mahasiswa Tiga", "Dinas PU Contoh", "magang", "disetujui", "selesai", "2026-03-01", "Budi"),
          ("9999000104", "Mahasiswa Empat", "CV Rancang Contoh", "kp", "disetujui", "pengajuan", "2026-12-01", "Adi"),
          ("9999000105", "Mahasiswa Lima", "PT Beton Contoh", "kp", "pembimbing", "pengajuan", "2027-01-05", "Adi")]
    t["pengajuan_mahasiswa"] = id_([dict(jenis="kp", nim=n, nama=nm, email=f"{n}@mhs.contoh.ac.id", pembimbing_id=uid(dsn),
                                         data=dict(instansi=ins, program=pr, rencana_mulai=mulai), status=st, tahap=th,
                                         data_selesai=dict(tanggal_mulai=mulai) if th == "selesai" else {}, token=f"kp{n}",
                                         dibuat=mulai + "T08:00:00Z")
                                    for n, nm, ins, pr, st, th, mulai, dsn in kp])
    # Seminar/sidang TA (94) dan pemeriksaan jadwal dosen saat menjadwalkan (pemilik 2026-11-22): satu sidang akhir siap
    # dijadwalkan (pembimbing Adi) dan satu seminar lain Adi + Budi minggu depan 09.00-10.30, supaya bentrok terlihat.
    pekan = date.today() + timedelta(days=7)
    pekan += timedelta(days=(7 - pekan.weekday()) % 7 if pekan.weekday() >= 5 else 0)   # Sabtu/Minggu -> Senin berikutnya
    t["pengajuan_mahasiswa"].append(dict(id=len(t["pengajuan_mahasiswa"]) + 1, jenis="ta", nim="9999000106", nama="Mahasiswa Enam",
                                         email="9999000106@mhs.contoh.ac.id", pembimbing_id=uid("Adi"),
                                         data=dict(judul="Analisis debit banjir rancangan DAS Contoh", tahap_ta="sidang_akhir"),
                                         status="admin", tahap="pengajuan", data_selesai={}, token="ta9999000106",
                                         dibuat=date.today().isoformat() + "T08:00:00Z"))
    t["jadwal_ta"] = [dict(id=1, pengajuan_id=None, tahap="seminar_proposal", nama_mahasiswa="Mahasiswa Tujuh", nim=None,
                           judul="Kajian drainase kampus contoh", pembimbing=["0000000010"], penguji=["0000000011"], penguji_luar=None,
                           tanggal=pekan.isoformat(), jam="09.00–10.30", ruang="Ruang contoh 2.01", tautan_daring=None,
                           status="terjadwal", hasil=None, tampil_nama=False, sembunyikan_publik=False, oleh=None)]
    # Penilaian sidang (173, pemilik 2026-11-25): sidang akhir kemarin, Budi (penguji) sudah menilai; Adi (peran "Dosen (Adi)",
    # pembimbing: nilai sidang + proses bimbingan) dan penguji luar belum, jadi alur isi nilai -> tetapkan berita acara bisa dicoba.
    kemarin = date.today() - timedelta(days=1)
    t["jadwal_ta"].append(dict(id=2, pengajuan_id=None, tahap="sidang_akhir", nama_mahasiswa="Mahasiswa Delapan", nim="9999000108",
                               judul="Evaluasi kapasitas saluran drainase perumahan contoh", pembimbing=["0000000010"],
                               penguji=["0000000011"], penguji_luar="Ir. Penguji Luar, M.T. (PT Contoh)", tanggal=kemarin.isoformat(),
                               jam="13.00–14.30", ruang="Ruang contoh 2.02", tautan_daring=None, status="terjadwal", hasil=None,
                               tampil_nama=False, sembunyikan_publik=False, oleh=None))
    # Catatan bimbingan TA (175, pemilik 2026-11-25): Mahasiswa Enam (pembimbing Adi) punya 3 bimbingan terkonfirmasi dan 1 yang
    # menunggu, jadi Tugas saya Adi berisi konfirmasi dan sidangnya belum memenuhi minimal 4.
    hari = lambda n: (date.today() - timedelta(days=n)).isoformat()
    t["ta_bimbingan"] = id_([dict(nim="9999000106", nama="Mahasiswa Enam", tanggal=hari(h), cara=c, pembimbing_id=uid("Adi"), topik=tp, arahan=ar,
                                  status=st, catatan_pembimbing=None, konfirmasi_oleh="Adi Contoh" if st == "dikonfirmasi" else None,
                                  konfirmasi_pada=hari(h - 1) + "T09:00:00Z" if st == "dikonfirmasi" else None,
                                  diajukan=(hari(h) if st == "dikonfirmasi" else date.today().isoformat()) + "T08:00:00Z", dibuat=hari(h) + "T08:00:00Z")
                             for h, c, tp, ar, st in [
                                 (60, "tatap_muka", "Bab 4 hasil analisis debit banjir", "Lengkapi kalibrasi model", "dikonfirmasi"),
                                 (40, "daring", "Bab 4 pembahasan dan perbandingan metode", "Tambahkan grafik hidrograf", "dikonfirmasi"),
                                 (20, "tatap_muka", "Bab 5 kesimpulan dan saran", "Kaitkan kesimpulan dengan tujuan", "dikonfirmasi"),
                                 (2, "daring", "Persiapan sidang akhir: slide presentasi", "", "menunggu")]])
    t["pengajuan_berkas"] = id_([dict(pengajuan_id=i, jenis=j, nama=f"{j}.pdf", url=url(), oleh="mahasiswa")
                                 for i in (1, 2, 3) for j in ("laporan_kp", "surat_selesai")])
    # Daftar kelas CPL contoh (portofolio MK, templat terisi per kelas).
    t["cpl_kelas"] = id_([dict(tahun_akademik="2026/2027", semester="Ganjil", kode_mk=f"TC{i + 101}", nama_mk=mk[i], kelas=k,
                               dosen_email=dt[i]["email"]) for i in (0, 1) for k in "AB"])
    t["ref_mk_cpl"] = id_([dict(kurikulum="K26", kode_mk=f"TC{i + 101}", cpl=c, indikator=None, bobot=None)
                           for i in range(len(mk)) for c in (["B", "A"] if i < 4 else ["B", "C"])])
    t["lkps_mahasiswa_ta"] = id_([dict(tahun_akademik=a, jumlah_mahasiswa_aktif=210 + 12 * i, jumlah_lulusan=38 + 4 * i, rerata_ipk_lulusan=3.31 + .04 * i,
                                       jumlah_mahasiswa_asing=0, jumlah_mahasiswa_asing_penuh=0, jumlah_mahasiswa_asing_paruh=0, rerata_masa_studi_tahun=4.4,
                                       persen_lulus_tepat_waktu=62 + 5 * i, ipk_min=2.8, ipk_maks=3.92) for i, a in enumerate(ta)])
    t["lkps_kohort_lulusan"] = id_([dict(tahun_masuk=y, jumlah_masuk=60, lulus_3_5_sd_4_5=33, lulus_4_5_sd_5_5=14, lulus_5_5_sd_6_5=4, lulus_6_5_sd_8=1)
                                    for y in range(2019, 2023)])
    t["lkps_tracer_lulusan"] = id_([dict(tahun_lulus=y, jumlah_lulusan=38 + 4 * i, jumlah_terlacak=30 + 3 * i, rata_rata_waktu_tunggu_bulan=4.2 - .3 * i,
                                         bekerja_sesuai_bidang=24 + 3 * i, kerja_internasional=1, kerja_nasional=12 + i, kerja_wilayah=15, wt_kurang_3=10,
                                         wt_3_18=18 + 3 * i, wt_lebih_18=2, kesesuaian_rendah=4, kesesuaian_sedang=10, kesesuaian_tinggi=16 + 3 * i,
                                         pengguna_tanggapan=18) for i, y in enumerate((2023, 2024, 2025))])
    asp = ["etika", "keahlian_bidang_ilmu", "bahasa_asing", "teknologi_informasi", "komunikasi", "kerja_sama_tim", "pengembangan_diri"]
    t["lkps_kepuasan_pengguna"] = id_([dict(tahun_akademik="2025/2026", aspek=a, sangat_baik=45, baik=40, cukup=12, kurang=3,
                                            rencana_tindak_lanjut="Dibahas dalam rapat kurikulum.", bukti_url=url()) for a in asp])
    t["lkps_kerjasama"] = id_([dict(mitra=m, jenis=j, tingkat=g, kegiatan=k, tahun_mulai=2024, tahun_selesai=2027, tautan_bukti=url(),
                                    manfaat="Magang mahasiswa dan riset bersama.", tanggal_mulai="2024-02-01", tanggal_selesai="2027-01-31",
                                    jenis_bukti="bukti_pelaksanaan")
                               for m, j, g, k in [("PT Konstruksi Contoh", "pendidikan", "nasional", "Magang dan kuliah tamu"),
                                                  ("Balai Sungai Contoh", "penelitian", "wilayah", "Pemantauan banjir"),
                                                  ("Example Institute of Technology", "penelitian", "internasional", "Riset bersama"),
                                                  ("Pemerintah Kota Contoh", "pkm", "wilayah", "Pendampingan drainase"),
                                                  ("PT Beton Contoh", "pendidikan", "nasional", "Kerja praktik")]])
    prestasi = [("Lomba Jembatan Baja Contoh", "Rina Mahasiswa; Dimas Mahasiswa", "akademik", "nasional", "Juara 2", 2025),
                ("Kompetisi Beton Contoh", "Sari Mahasiswa", "akademik", "nasional", "Juara 1", 2026),
                ("Lomba Karya Tulis Contoh", "Yoga Mahasiswa", "akademik", "wilayah_lokal", "Juara 3", 2024),
                ("Kejuaraan Bulu Tangkis Contoh", "Tia Mahasiswa", "non_akademik", "wilayah_lokal", "Juara 1", 2025)]
    t["lkps_prestasi_mahasiswa"] = id_([dict(nama_kegiatan=n, nama_mahasiswa=m, nim=f"219977{i}", penyelenggara="Asosiasi Contoh", bidang=b, tingkat=g, capaian=c,
                                             tahun=y, bulan=i + 3, pembimbing=[dt[i]["nidn"]], status="terverifikasi", dilaporkan_oleh=dt[i]["id"])
                                        for i, (n, m, b, g, c, y) in enumerate(prestasi)])
    t["lkps_publikasi_mahasiswa"] = id_([dict(tahun=y, judul=f"Kajian mahasiswa {i + 1}: {TOPIK[i].lower()}", nama_mahasiswa="Rina Mahasiswa", nim="2199770",
                                              jenis="jurnal", tingkat="nasional", indeksasi="sinta", bulan=5) for i, y in enumerate((2024, 2025, 2025, 2026))])
    t["lkps_luaran_mahasiswa"] = id_([dict(tahun=2025, bulan=7, jenis="hak_cipta", judul="Aplikasi perhitungan drainase", nama_mahasiswa="Dimas Mahasiswa",
                                           nim="2199771", status_hki="granted", nomor="EC-CONTOH-001")])
    t["lkps_vmts"] = id_([dict(jenis=j, visi=f"Menjadi {n} yang unggul dalam rekayasa berkelanjutan.", misi="Menyelenggarakan pendidikan, penelitian, dan pengabdian yang bermutu.",
                               tujuan="Menghasilkan lulusan yang kompeten.", strategi="Penguatan kurikulum dan kerja sama.", nomor_sk="SK/CONTOH/001", tautan=url())
                          for j, n in [("pt", "perguruan tinggi"), ("upps", "fakultas"), ("ps", "program studi")]])
    t["lkps_prodi_upps"] = id_([dict(jenis_program="Sarjana", nama_prodi="Teknik Contoh", diakreditasi=True, status_akreditasi="baik_sekali", nomor_sk="SK/LAM/CONTOH",
                                     tanggal_sk="2022-03-01", tanggal_kedaluwarsa="2027-03-01", mahasiswa_ts2=210, mahasiswa_ts1=222, mahasiswa_ts=234, urutan=1)])
    jd = ["biaya_dosen", "biaya_tendik", "operasional_pembelajaran", "operasional_tidak_langsung", "investasi", "kemahasiswaan"]
    t["lkps_penggunaan_dana"] = id_([dict(tahun_akademik=a, jenis=j, dana_upps=(k + 2) * 40000000, dana_ps=(k + 2) * 25000000) for a in ta for k, j in enumerate(jd)])
    # 164: peran, status kerja, boleh tampil; magang tampil di situs tetapi tidak masuk LKPS 4.b.
    t["lkps_tendik"] = id_([dict(nama=n, jabatan=j, pendidikan=p, sertifikat="", unit_kerja="prodi", aktif=True, status_kerja=s,
                                 laboratorium_id=None, boleh_tampil=b)
                            for n, j, p, s, b in [("Rudi Tendik", "laboran", "d3", "tetap", True), ("Sinta Tendik", "admin_prodi", "s1", "kontrak", True),
                                                  ("Tono Tendik", "teknisi", "d3", "tetap", False), ("Dewi Aslab", "asisten_lab", "sma_smk", "magang", True)]])
    t["lkps_prasarana"] = id_([dict(prasarana=n, jumlah_prasarana=1, alat=a, jumlah_standar=4, jumlah_dimiliki=4, kepemilikan="sendiri", kondisi="terawat", urutan=i)
                               for i, (n, a) in enumerate([("Laboratorium Beton", "Mesin uji tekan"), ("Laboratorium Tanah", "Alat geser langsung"),
                                                           ("Laboratorium Hidraulika", "Saluran terbuka")])])
    t["lkps_dokumen_k3l"] = id_([dict(jenis_dokumen="Pedoman K3 laboratorium", jumlah=1, riwayat_pengesahan="Disahkan 2024", urutan=1)])
    t["lkps_fasilitas_k3l"] = id_([dict(nama_sarana="Alat pemadam api", fungsi="Keselamatan", jumlah_unit=6, kondisi="terawat", urutan=1)])
    t["lkps_target_kinerja"] = id_([
        dict(jenis="iku", bidang="pendidikan", nama="Lulusan tepat waktu", butir=54, satuan="%", arah="minimal", target=70, capaian=72, tahun_ts=ts, urutan=1,
             tujuan_strategis="Mutu lulusan", dampak="Masa studi lebih pendek", daya_saing="Di atas rata-rata prodi sejenis", analisis="Pendampingan tugas akhir berjalan baik."),
        dict(jenis="iku", bidang="penelitian", nama="Publikasi bereputasi per dosen", butir=54, satuan="karya", arah="minimal", target=1, capaian=1.2, tahun_ts=ts, urutan=2,
             tujuan_strategis="Mutu riset", dampak="Sitasi naik", daya_saing="Setara prodi sejenis", analisis="Hibah internal mendorong publikasi.")])
    dok = []
    jenis = [("statuta", 2023, ""), ("renstra", 2024, ""), ("kurikulum", 2024, ""), ("kebijakan_spmi", 2024, ""), ("standar_spmi", 2024, ""),
             ("laporan_ami", 2025, ""), ("notulen", 2025, "Rapat tinjauan manajemen")]
    for i, (j, y, jud) in enumerate(jenis):
        dok.append(dict(id=i + 1, jenis=j, tahun=y, judul=jud, url=url(), folder_url=None, nama_berkas=f"{j}-{y}.pdf", butir=[],
                        diunggah_oleh="admin@contoh.ac.id", diperbarui=f"{y}-08-01T00:00:00Z", sha256=None))
    t["dokumen"] = dok
    t["lkps_spmi_ppepp"] = id_([dict(tahap=h, dokumen_id=4, keterangan="Dilaksanakan setiap tahun.") for h in ("penetapan", "pelaksanaan", "evaluasi", "pengendalian", "peningkatan")])
    bk = []
    for d in dt:
        for a in ta:
            for s in ("ganjil", "genap"):
                bk.append(dict(nidn=d["nidn"], tahun_akademik=a, semester=s, status="dtps", jabatan_akademik=d["jabatan"], pendidikan_tertinggi=d["pendidikan"].lower(),
                               sks_pendidikan=R.choice([8, 9, 10]), sks_penelitian=3, sks_pkm=1, sks_penunjang=1.5, sks_ps_lain_dalam=0, sks_ps_lain_luar=0,
                               sks_lebih_pendidikan=R.choice([0, 0, 2]), sks_lebih_penelitian=0, sks_lebih_pkm=0, sks_lebih_penunjang=0, verifikasi="terverifikasi",
                               bukti_url=url(), dilaporkan_oleh=d["id"]))
    t["lkps_bkd"] = id_(bk)
    t["led_tim"] = id_([dict(urutan=i, jenis="dosen", dosen_id=dt[i]["id"], jabatan=j, deskripsi="Menyusun LED dan LKPS")
                        for i, j in enumerate(["Ketua", "Anggota", "Anggota", "Anggota"])])
    for x in ("lkps_bukti", "butir_bukti", "karya_bukti", "karya_mahasiswa", "karya_mitra", "ajuan_ubah", "ajuan_hapus", "ajuan_prestasi", "ajuan_bkd",
              "led_narasi", "led_penugasan", "ref_kategori_publikasi"):
        t.setdefault(x, [])
    for k in ks:
        if k["kategori"] == "pkm":
            t["karya_mitra"].append(dict(id=uid("mitra" + k["id"]), karya_id=k["id"], institusi=["Desa Contoh", "Kelurahan Contoh", "Dinas PU Contoh", "Koperasi Contoh"][len(t["karya_mitra"]) % 4], negara="Indonesia", tingkat="wilayah_lokal"))
        if k["kategori"] in ("publikasi", "penelitian", "pkm"):
            t["karya_bukti"].append(dict(id=len(t["karya_bukti"]) + 1, karya_id=k["id"], jenis="naskah", judul="Naskah", url=url(),
                                         oleh=k["dilaporkan_oleh"], dibuat=k["dibuat_pada"]))
    return t


def ref(sql):
    lit = re.compile(r"'((?:[^']|'')*)'|(NULL|true|false)|(-?\d+(?:\.\d+)?)")
    out = {}
    for m in re.finditer(r"INSERT INTO public\.(ref_skema_dana|ref_kelompok_dana|ta_berkas|ta_syarat_bimbingan) \(([^)]*)\) VALUES \((.*)\);", sql):
        cols = [c.strip() for c in m.group(2).split(",")]
        vals = []
        for v in lit.finditer(m.group(3)):
            if v.group(1) is not None:
                vals.append(v.group(1).replace("''", "'"))
            elif v.group(2):
                vals.append({"NULL": None, "true": True, "false": False}[v.group(2)])
            else:
                vals.append(float(v.group(3)) if "." in v.group(3) else int(v.group(3)))
        assert len(vals) == len(cols), m.group(0)[:100]
        out.setdefault(m.group(1), []).append(dict(zip(cols, vals)))
    return out


def tabel_baru(ds, kini: date) -> dict:
    """Contoh untuk modul 2026-11 (rapat, kalender, hibah, temuan AMI); tanggal relatif terhadap hari ini,
    supaya Kalender dan Tugas saya ikut berisi. Kolom mengikuti patch 51, 58, 62, 64."""
    h = lambda n: (kini + timedelta(days=n)).isoformat()
    admin, adi = ds[0], ds[1]
    t = {}
    t["rapat"] = [dict(id=1, judul="Rapat tinjauan kurikulum", jenis="kurikulum", tanggal=h(-20), mulai="13:00:00", selesai="15:00:00",
                       tempat="Ruang rapat prodi", pimpinan="Admin Contoh", notulis="Budi Contoh", agenda="1. Evaluasi CPL\n2. Revisi RPS",
                       pembahasan="CPL 3 belum tercapai di dua mata kuliah.", terbatas=False, status="final", dokumen_id=None,
                       token_hadir=None, hadir_sampai=None, dibuat_oleh=admin["id"], oleh=admin["email"],
                       dibuat=h(-20) + "T08:00:00Z", diperbarui=h(-20) + "T08:00:00Z"),
                  # 166: draf yang tidak diikuti Adi -> Adi hanya melihat jadwal dan agenda.
                  dict(id=2, judul="Rapat persiapan akreditasi", jenis="rapat_prodi", tanggal=h(-2), mulai="09:00:00", selesai="11:00:00",
                       tempat="Ruang rapat prodi", pimpinan="Admin Contoh", notulis="Budi Contoh", agenda="1. Pembagian tugas borang",
                       pembahasan="Pembagian penyusun kriteria (draf).", terbatas=False, status="draf", dokumen_id=None,
                       token_hadir=None, hadir_sampai=None, dibuat_oleh=admin["id"], oleh=admin["email"],
                       dibuat=h(-2) + "T08:00:00Z", diperbarui=h(-2) + "T08:00:00Z")]
    t["rapat_peserta"] = [dict(id=i + 1, rapat_id=1, dosen_id=d["id"], nama=d["nama"], instansi=None, peran=p, hadir=True,
                               cara="dicatat", klien=None, waktu=h(-20) + "T06:00:00Z")
                          for i, (d, p) in enumerate([(admin, "pimpinan"), (ds[2], "notulis"), (adi, "peserta"), (ds[3], "peserta")])]
    t["rapat_peserta"].append(dict(id=99, rapat_id=2, dosen_id=ds[2]["id"], nama=ds[2]["nama"], instansi=None, peran="notulis", hadir=True,
                                   cara="dicatat", klien=None, waktu=h(-2) + "T02:00:00Z"))
    t["rapat_tindak"] = [dict(id=1, rapat_id=1, urutan=1, keputusan="Revisi RPS Hidrologi sesuai CPL 3", pj_dosen_id=adi["id"], pj_nama=None,
                              tenggat=h(-3), status="terbuka", tanggal_selesai=None, catatan=None, diperbarui=h(-20) + "T08:00:00Z"),
                         dict(id=2, rapat_id=1, urutan=2, keputusan="Usulkan pelatihan asesmen berbasis OBE", pj_dosen_id=admin["id"], pj_nama=None,
                              tenggat=h(25), status="proses", tanggal_selesai=None, catatan=None, diperbarui=h(-20) + "T08:00:00Z")]
    # 139: hari libur contoh (tanggal relatif, bukan daftar libur sungguhan).
    t["hari_libur"] = [dict(tanggal=h(n), nama=nm, jenis=j, oleh=admin["email"], dibuat_pada=h(-5) + "T00:00:00Z")
                       for n, nm, j in ((3, "Hari libur nasional (contoh)", "nasional"), (4, "Cuti bersama (contoh)", "cuti_bersama"),
                                        (40, "Libur kampus (contoh)", "kampus"))]
    # 140: admin sudah menandai isian Genap 2026/2027 lengkap; Adi sudah mengisi satu slot tetapi belum menandai.
    t["berhalangan_konfirmasi"] = [dict(dosen_id=admin["id"], tahun_akademik="2026/2027", semester="Genap",
                                        dikonfirmasi_pada="2026-11-20T09:00:00+07:00")]
    t["dosen_berhalangan"] = [dict(id=1, dosen_id=adi["id"], tahun_akademik="2026/2027", semester="Genap", hari=2, slot_id=1,
                                   jenis="prodi_lain", alasan="Mengajar Teknik Lingkungan (contoh)")]
    t["kegiatan"] = [dict(id=1, judul="Ujian akhir semester ganjil", jenis="akademik", mulai=h(24), selesai=h(35), jam_mulai=None, jam_selesai=None,
                          tempat="Gedung kuliah", keterangan=None, tautan=None, oleh=admin["email"], dibuat=h(-5) + "T00:00:00Z", diperbarui=h(-5) + "T00:00:00Z"),
                     dict(id=2, judul="Kuliah tamu: rekayasa banjir perkotaan", jenis="seminar", mulai=h(9), selesai=None, jam_mulai="09:00:00",
                          jam_selesai="11:00:00", tempat="Aula", keterangan="Terbuka untuk mahasiswa semester 5 ke atas.", tautan=None,
                          oleh=admin["email"], dibuat=h(-5) + "T00:00:00Z", diperbarui=h(-5) + "T00:00:00Z")]
    t["hibah_panggilan"] = [dict(id=1, judul="Hibah penelitian dasar contoh", penyelenggara="Kementerian Contoh", kategori="penelitian",
                                 skema_kode=None, tenggat=h(12), tautan="https://contoh.go.id/hibah", keterangan=None, diumumkan=None,
                                 oleh=admin["email"], dibuat=h(-10) + "T00:00:00Z")]
    t["ami_temuan"] = [dict(id=1, siklus="2026", tahun_ts=kini.year, tanggal_audit=h(-40), kode="T1", standar="Standar pembelajaran", butir=15,
                            kategori="kts_minor", uraian="Monitoring RPS belum terdokumentasi.", akar_masalah=None, rencana="Buat format monev RPS.",
                            pihak="P", pj_nama=adi["nama"], pj_email=adi["email"], tenggat=h(30), status="terbuka", tanggal_selesai=None, verifikasi=None)]
    return t


def penilaian_ta(sql: str) -> dict:
    """Form penilaian TA versi 1 (173) dari skema + satu nilai sidang contoh Budi untuk jadwal 2. Skema gabungan (full_schema /
    instal-lengkap.sql) memuat barisnya sebagai INSERT; patch sumber memuat blok rubrik_awal. Tanpa patch 173: kosong."""
    lit = re.compile(r"'((?:[^']|'')*)'|(NULL)|(-?\d+(?:\.\d+)?)")
    rubrik = []
    for m in re.finditer(r"INSERT INTO public\.ta_rubrik \(([^)]*)\) OVERRIDING SYSTEM VALUE VALUES \((.*)\);", sql):
        cols = [c.strip() for c in m.group(1).split(",")]
        vals = [v.group(1).replace("''", "'") if v.group(1) is not None else None if v.group(2) else float(v.group(3))
                for v in lit.finditer(m.group(2))]
        r = dict(zip(cols, vals))
        r.update(id=int(r["id"]), versi=int(r["versi"]), komponen=json.loads(r["komponen"]),
                 komponen_bimbingan=json.loads(r.get("komponen_bimbingan") or "[]"),
                 tingkat=[float(x) for x in r["tingkat"].strip("{}").split(",")], bobot_penguji=float(r["bobot_penguji"]),
                 bobot_bimbingan=float(r.get("bobot_bimbingan") or 0), batas_lulus=float(r["batas_lulus"]))
        rubrik.append(r)
    if not rubrik:
        m = re.search(r"\$rubrik_awal\$(.*?)\$rubrik_awal\$", sql, re.S)
        if not m:
            return {}
        rubrik = [dict(id=i + 1, tahap=tahap, versi=1, komponen=x["komponen"], komponen_bimbingan=x["komponen_bimbingan"],
                       bobot_penguji=x["bobot_penguji"], bobot_bimbingan=x["bobot_bimbingan"], batas_lulus=55, tingkat=[85, 70, 55, 0],
                       catatan="Draf awal (pemilik 2026-11-25).", oleh="pemasangan", dibuat="2026-11-25T00:00:00Z")
                  for i, (tahap, x) in enumerate(json.loads(m.group(1)).items())]
    sidang = next(r for r in rubrik if r["tahap"] == "sidang_akhir")
    nilai = {k["kode"]: 80 for k in sidang["komponen"]}
    return {"ta_rubrik": rubrik,
            "ta_nilai": [dict(id=1, jadwal_id=2, rubrik_id=sidang["id"], bagian="seminar", peran="penguji", penilai_nidn="0000000011",
                              penilai_nama="Budi Contoh", nilai=nilai, total=80, catatan="Kesimpulan perlu dikaitkan dengan tujuan.", diisi_oleh="Budi Contoh",
                              diwakilkan=False, diperbarui="2026-11-25T08:00:00Z")]}


def buat(sql_path: Path, kini: date | None = None) -> dict:
    ds = dosen()
    ks, pen = karya(ds)
    t = tabel_lain(ds, ks)
    sql = sql_path.read_text(encoding="utf-8")
    t.update(ref(sql))
    t.update(penilaian_ta(sql))
    t.update(tabel_baru(ds, kini or date.today()))
    # Dekan bukan DTPS ikut menulis (pemilik 2026-11-21: nama pimpinan tidak boleh tampil di situs umum).
    pen += [dict(karya_id=k["id"], dosen_id=uid("pimpinan"), peran="anggota", korespondensi=False, ditambahkan_sendiri=False) for k in ks[:3]]
    t["dosen"], t["karya"], t["karya_penulis"] = ds, ks, pen
    return t


if __name__ == "__main__":
    d = buat(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    print({k: len(v) for k, v in d.items()})
