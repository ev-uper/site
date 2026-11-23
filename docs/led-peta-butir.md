# Ringkasan LED per no urut butir (APS-AV 2025, Sarjana)

Sumber: template LEDPS LAM Teknik "untuk pasca akreditasi pertama dan
unggul", instrumen LAM Teknik 2025 ver. 2 (berkas `.docx` dari pemilik,
2026-11-03). Template tidak mencantumkan nomor butir; nomor di sini adalah
no urut 1–60 matriks APS-AV 2025 yang dipakai situs (`site/butir-manual.js`,
`site/butir-data.js`). Pemetaan bagian LED ke butir disusun Claude
2026-11-03 dari kesamaan judul dan isi; periksa sebelum dipakai.

Kolom "Sumber" menunjukkan dari mana angka atau bukti bisa diambil:
**data** = dihitung situs dari data.json/Supabase, **manual** = skor diisi
tangan di `input-butir.html`, **narasi** = harus ditulis prodi.

## Draf Word otomatis

Tombol **Unduh draf LED (.docx)** di halaman skor (bilah "Buka semua /
Tutup semua") mengisi `site/led-template.docx` di browser lewat
`site/led.js` (pemilik 2026-11-03). Isinya: sampul dan identitas yang
diketahui dari data.json, logo `site/logo.png`, lalu di bawah kalimat
petunjuk tiap subbagian: skor butir, tabel data dari kartu skor, dasar
perhitungan, syarat perlu, tautan bukti, draf narasi, dan kotak gambar.
Ringkasan eksekutif dan Bab IV memuat NA dan status; analisis dan SWOT
tiap kriteria memuat daftar butir kuat dan lemah; Bab III memuat 10 butir
prioritas; lampiran memuat tautan bukti 60 butir.

Sorot kuning = draf mesin yang harus diperiksa; `[isi: …]` merah = wajib
diisi; tabel dan tautan tanpa sorot = diambil dari sistem. Bila template
LAM berganti, perbarui `SLOT` di `led.js`: tiap titik sisip mencari awal
judul subbagian. Subbagian yang tidak ketemu dicantumkan pada catatan di
halaman pertama draf.

## Bagian tanpa butir

| Bagian LED | Isi yang diminta |
|---|---|
| Halaman muka, identitas pengusul | identitas PT, UPPS, SK pendirian PT dan pembukaan PS, akreditasi terakhir, tabel PS di UPPS dengan jumlah mahasiswa saat TS |
| Identitas tim penyusun | nama, NIDN/NUPTK, jabatan, tanggal, tanda tangan |
| Kata pengantar, ringkasan eksekutif | narasi |
| Bab I Pendahuluan | narasi |
| Bab II.A Struktur tim penyusun | SK tim, keterlibatan pemangku internal dan eksternal, mekanisme pengumpulan, verifikasi, validasi, analisis data, jadwal; Tabel 2.1 tim dosen, Tabel 2.2 tim nondosen |
| Tiap kriteria C.1–C.7: Latar belakang | latar belakang, tujuan, rasional kriteria itu |
| Tiap kriteria C.1–C.7: Kebijakan | dokumen formal kebijakan yang diacu |
| Tiap kriteria C.1–C.7: Analisis faktor keberhasilan dan penghambat | evaluasi IKU, faktor pendukung, akar masalah |
| Tiap kriteria C.1–C.7: Strategi perbaikan (SWOT) | kekuatan, kelemahan, peluang, ancaman, strategi |
| Bab IV Penutup | kesimpulan, kekuatan, kelemahan, peluang, ancaman |
| Lampiran | tautan bukti sahih LED dan LKPS di penyimpanan awan |

## Butir 1–60

| No | Butir | Bagian LED | Isi yang diminta | Sumber |
|---|---|---|---|---|
| 1 | Kekhasan VMTS | C.1 IKU: Kekhasan VMTS | linearitas VMTS PT–UPPS–visi keilmuan prodi, keunggulan kompetitif, didukung renstra dan kurikulum | manual, narasi |
| 2 | Mekanisme penyusunan VMTS | C.1 IKU: Mekanisme penyusunan | keterlibatan dosen, mahasiswa, tendik, alumni, pengguna, pakar | manual, narasi |
| 3 | Pemahaman dan pencapaian VMTS | C.1 IKU: Tingkat pemahaman dan pencapaian | sosialisasi, tingkat pemahaman, capaian jangka pendek/menengah, dampak | manual, narasi |
| 4 | Sistem tata pamong (I, II) | C.2 IKU: Sistem tata pamong | I struktur organisasi dan kebijakan operasional sesuai statuta; II Good University Governance | manual, narasi |
| 5 | Komitmen dan manajerial pimpinan (I, II) | C.2 IKU: Komitmen pimpinan dan kemampuan manajerial | I visi, integritas, kode etik, pengembangan SDM; II kepemimpinan, keputusan, manajemen konflik | manual, narasi |
| 6 | Kerja sama (Tabel 2.a) | C.2 IKU: Relevansi dan tingkat kerja sama | kerja sama pendidikan, penelitian, PkM tingkat internasional/nasional/lokal, 3 tahun terakhir | data |
| 7 | Pelaksanaan kerja sama | C.2 IKU: Pelaksanaan kerja sama | bukti sahih 3 aspek: manfaat bagi prodi, peningkatan kinerja tridharma, kepuasan mitra | manual, narasi |
| 8 | Pengelolaan keuangan | C.2 IKU: Pengelolaan keuangan | akuntabel, transparan, efektif, efisien | manual, narasi |
| 9 | Biaya operasional pendidikan | C.2 IKU: Biaya operasional pendidikan | rerata BOP/mahasiswa/tahun | data |
| 10 | Dana penelitian DTPS | C.2 IKU: Dana penelitian | rerata dana penelitian DTPS/tahun | data |
| 11 | Dana PkM DTPS | C.2 IKU: Dana PkM | rerata dana PkM DTPS/tahun | data |
| 12 | Pemutakhiran kurikulum | C.3 IKU Pendidikan: Pemutakhiran kurikulum | evaluasi dan pemutakhiran melibatkan pemangku internal/eksternal, direview pakar, sesuai iptek | manual, narasi |
| 13 | Profil lulusan dan CPL (I, II) | C.3: Profil lulusan; Kesesuaian CPL dengan profil lulusan | I profil lulusan dari visi, kebutuhan pengguna, sumber daya; II CPL sesuai kebutuhan pengguna, iptek, daya saing global, diukur dan ditinjau rutin | manual, narasi; laporan `run_cpl.py` |
| 14 | Kesesuaian dan tinjauan CPL (I, II) | C.3: Kesesuaian CPL dengan standar kompetensi; Proses tinjauan rutin CPL | I konsep rekayasa, kemampuan teknis, komunikasi dan tim, etika profesi; II tinjauan berkala melibatkan pemangku | manual, narasi; laporan CPL |
| 15 | RPS (I, II) | C.3: Ketersediaan RPS; Proses tinjauan rutin RPS | I 9 komponen RPS, mudah diakses; II tinjauan berkala | manual, narasi |
| 16 | Proses pembelajaran (I, II) | C.3: Proses pembelajaran; Tinjauan rutin proses pembelajaran | I metode, media, interaksi, daya analisis kritis; II pemantauan kesesuaian RPS sampai tindakan perbaikan | manual, narasi |
| 17 | Integrasi penelitian/PkM dalam pembelajaran | C.3: Integrasi penelitian dan PkM | relevansi CPL, keunggulan kompetitif, kebaruan ilmiah, dampak sosial (Tabel 3.a.3) | manual; data pendukung di situs |
| 18 | Pembelajaran penugasan/praktikum/lapangan | C.3: Pembelajaran penugasan, praktikum, praktik lapangan | rasio jam penugasan/praktikum terhadap jam total | manual (JP, JB) |
| 19 | Basic sciences dan matematika | C.3: Basic sciences dan matematika | MK basic sciences dan matematika (Tabel 3.a.4); syarat perlu ≥ 25 SKS untuk Unggul | data |
| 20 | Capstone design | C.3: Proyek rekayasa penciri bidang prodi | MK capstone dan penunjangnya, panduan, CPMK, standar keteknikan, bukti pelaksanaan (Tabel 3.a.5) | manual, narasi |
| 21 | Suasana akademik (I, II) | C.3: Pengelolaan suasana akademik; Integritas dan kebebasan ilmiah | I kebijakan, program, fasilitas, evaluasi; II kebebasan akademik, mimbar akademik, otonomi keilmuan terjadwal | manual, narasi |
| 22 | Penelitian: peta jalan | C.3 Penelitian: Kesesuaian dengan VMTS | peta jalan mendukung VMTS, memayungi tema dosen dan mahasiswa, dievaluasi, berdampak | manual, narasi |
| 23 | Penelitian DTPS melibatkan mahasiswa | C.3 Penelitian: Penelitian DTPS sesuai peta jalan | penelitian DTPS sesuai peta jalan dengan mahasiswa, 3 tahun (Tabel 6.h.1) | data |
| 24 | PkM: peta jalan | C.3 PkM: Kesesuaian dengan VMTS | sama dengan butir 22 untuk PkM | manual, narasi |
| 25 | PkM DTPS melibatkan mahasiswa | C.3 PkM: PkM DTPS sesuai peta jalan | PkM DTPS dengan mahasiswa, 3 tahun (Tabel 6.i) | data |
| 26 | Kecukupan DTPS | C.4 IKU: Kecukupan jumlah DTPS | jumlah DTPS sesuai kompetensi inti prodi (Tabel 4.a) | data |
| 27 | Kualifikasi akademik DTPS | C.4 IKU: Kualifikasi akademik DTPS | persentase DTPS doktor; syarat perlu Unggul | data |
| 28 | Jabatan akademik DTPS | C.4 IKU: Jabatan akademik DTPS | persentase GB/LK/Lektor; syarat perlu Unggul | data |
| 29 | Tenaga kependidikan | C.4 IKU: Tenaga kependidikan | kualifikasi dan kecukupan laboran/teknisi (Tabel 4.b) | manual, narasi |
| 30 | Beban kerja DTPS | C.4 IKU: Beban kerja DTPS | rerata beban kerja pendidikan, penelitian, PkM, tugas tambahan (Tabel 4.c) | manual (RBK) |
| 31 | Penelitian DTPS per sumber dana | C.4 Kinerja: Kegiatan penelitian | jumlah penelitian DTPS mendukung visi, 3 tahun (Tabel 3.b) | data |
| 32 | PkM DTPS per sumber dana | C.4 Kinerja: Kegiatan PkM | jumlah PkM DTPS mendukung visi, 3 tahun (Tabel 3.c) | data |
| 33 | Publikasi ilmiah DTPS | C.4 Kinerja: Publikasi ilmiah DTPS | publikasi DTPS bertema visi keilmuan, 3 tahun | data |
| 34 | Luaran penelitian/PkM DTPS | C.4 Kinerja: Luaran penelitian dan PkM | HKI, TTG, produk, buku ber-ISBN, book chapter, 3 tahun | data |
| 35 | Karya utama internasional | C.4 Kinerja: Kinerja DTPS dan keunggulan kompetitif | persentase DTPS penulis utama/korespondensi di jurnal internasional bereputasi atau paten; syarat perlu Unggul | data |
| 36 | Karya ilmiah disitasi | C.4 Kinerja: Karya ilmiah DTPS yang disitasi | sitasi di pengindeks internasional, 3 tahun (Tabel 4.i) | manual (angka) |
| 37 | Rekognisi DTPS | C.4 Kinerja: Pengakuan/rekognisi DTPS | persentase DTPS berekognisi, 3 tahun (Tabel 4.j) | data |
| 38 | Sarana dan prasarana (I, II) | C.5 IKU: Sarana dan prasarana | I akademik: media, ruang, laboratorium, perpustakaan; II nonakademik: kesehatan, konseling, karier, ibadah | manual, narasi |
| 39 | K3L | C.5 IKU: K3L | kebijakan dan tata kelola K3L, sarana, bukti pelaksanaan, tinjauan berkala | manual, narasi |
| 40 | Rasio mahasiswa/DTPS | C.6 IKU: Rasio mahasiswa terhadap DTPS | rasio (Tabel 6.a) | data |
| 41 | Mahasiswa asing | C.6 IKU: Persentase mahasiswa asing | mahasiswa asing paruh/penuh waktu | data |
| 42 | IPK lulusan | C.6 IKU: IPK lulusan | rerata IPK | data |
| 43 | Prestasi mahasiswa | C.6 IKU: Prestasi mahasiswa | prestasi akademik dan nonakademik, 5 tahun | data |
| 44 | Masa studi | C.6 IKU: Masa studi | rerata masa studi (Tabel 6.d) | data |
| 45 | Lulusan tepat waktu | C.6 IKU: Lulusan tepat waktu | persentase lulus tepat waktu (Tabel 6.d) | data |
| 46 | Publikasi ilmiah mahasiswa | C.6 IKU: Publikasi ilmiah mahasiswa | publikasi mahasiswa, mandiri/bersama DTPS, 3 tahun | data |
| 47 | Luaran mahasiswa | C.6 IKU: Luaran penelitian dan PkM mahasiswa | HKI, TTG, produk, buku, 3 tahun | data |
| 48 | Tracer study | C.6 IKU: Tracer study | 5 aspek: terkoordinasi PT, reguler, pertanyaan inti DIKTI, seluruh populasi TS-2..TS-1, hasil dipakai | manual, narasi |
| 49 | Waktu tunggu | C.6 IKU: Waktu tunggu | waktu tunggu kerja pertama, lulusan TS-2..TS-1 (Tabel 6.f.1); syarat perlu Unggul | data |
| 50 | Kesesuaian bidang kerja | C.6 IKU: Kesesuaian bidang kerja | kesesuaian bidang kerja (Tabel 6.f.2); syarat perlu Unggul | data |
| 51 | Tingkat tempat kerja | C.6 IKU: Tingkat dan ukuran tempat kerja | internasional, nasional, lokal (Tabel 6.g.1) | data |
| 52 | Kepuasan pengguna lulusan | C.6 IKU: Tingkat kepuasan pengguna | 7 aspek (Tabel 6.g.2) | manual (ΣTKi) |
| 53 | Unit penjaminan mutu dan perangkat SPMI (I, II) | C.7 IKU: Keberadaan unit dan komitmen; Perangkat SPMI dan pengakuan eksternal | I SK unit, auditor independen, AMI, RTM; II kebijakan, pedoman PPEPP, standar, dokumentasi, pengakuan eksternal | manual, narasi |
| 54 | IKT | C.7: Indikator Kinerja Tambahan | 4 unsur: tujuan strategis, dampak terukur, daya saing internasional, diukur dan dianalisis | manual, narasi |
| 55 | Keterlaksanaan PM dan AMI | C.7: Keterlaksanaan penjaminan mutu dan AMI | dokumen IKU/IKT, siklus PPEPP, bukti efektivitas, peningkatan standar | manual, narasi |
| 56 | Evaluasi capaian kinerja | C.7: Evaluasi capaian kinerja | metode pengukuran, akar masalah, tinjauan rutin, penyebarluasan | manual, narasi |
| 57 | Kepuasan pemangku kepentingan | C.7: Kepuasan pemangku kepentingan | kepuasan mahasiswa, dosen, tendik, lulusan, pengguna, mitra | manual, narasi |
| 58 | Lingkungan eksternal dan SWOT (I, II) | Bab II.B Analisis lingkungan eksternal; Bab III Analisis SWOT semua kriteria | I lingkungan makro dan mikro; II ketepatan SWOT dan posisi UPPS/PS | manual, narasi |
| 59 | Tujuan strategis pengembangan | Bab III: Tujuan strategis pengembangan | tujuan strategis dari SWOT, jangka pendek dan menengah | manual, narasi |
| 60 | Program pengembangan berkelanjutan | Bab III: Program pengembangan keberlanjutan | program rasional, terukur, sesuai sumber daya | manual, narasi |

## Bagian template yang bukan untuk Sarjana

Template berlaku untuk semua jenjang. Subbagian berikut ditandai untuk
jenjang lain dan dilewati untuk Sarjana:

- Magister/Doktor: metode rekrutmen dan seleksi, kriteria penerimaan, proses
  seleksi, penelitian DTPS rujukan tesis/disertasi.
- Program Profesi Insinyur: DTPSPPI dan dosen industri, kualifikasi
  keinsinyuran, kegiatan dan luaran kolaboratif industri, pengembangan dosen,
  pembimbing lapangan, keberhasilan studi moda reguler.
- Vokasi/terapan: sertifikat kompetensi DTPS, MK kompetensi diampu praktisi,
  pagelaran/pameran DTPS dan mahasiswa, produk/jasa diadopsi industri.
- Khusus doktor dalam subbagian kualifikasi DTPS (C.4) diberi keterangan
  "Program Profesi Insinyur" di template, padahal butir 27 berlaku untuk
  Sarjana. Tetap diisi.
