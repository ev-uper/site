# Analisis kesenjangan: situs akreditasi vs instrumen LAM Teknik 2025 (Sarjana)

Disusun 2026-10-12. Dasar: tujuh dokumen instrumen yang diunggah pemilik
(matriks penilaian, pedoman penilaian, panduan LED, templat LED, panduan LKPS,
LKPS Excel, naskah akademik) dibandingkan dengan kode `site/` dan `bangun.py`.
Ekstraksi rinci per dokumen ada di scratchpad sesi (di luar repo); dokumen ini
hanya memuat kesimpulan dan rujukan halaman.

Tanda: ✅ sesuai · ⚠️ berbeda atau tafsiran · ❌ belum ada · 📝 diisi manual.

---

## 1. Ringkasan

1. **Versi instrumen sama dengan yang dipakai situs**: matriks berkode
   **APS-AV 2025 1.0, Program Sarjana**, 60 butir, Σ bobot 100,01 (pedoman
   penilaian hlm. 223–227), sama dengan `site/bobot.js`. Berkas "pasca akreditasi
   pertama dan unggul" tidak memuat butir atau aturan yang berbeda; frasa itu
   hanya ada di nama berkas.
2. **Rumus 28 butir otomatis sudah sesuai matriks** (faktor a/b/c, ambang, lantai
   skor). Kesenjangan terbesar bukan rumus, melainkan:
   - **data kosong** (tracer, kohort lulusan, kerja sama, publikasi/luaran
     mahasiswa, BKD), sehingga 9 butir (6, 30, 44–47, 49–51) berbobot 15,68
     belum terisi;
   - **status akreditasi belum dihitung**: situs menampilkan persen skor dan
     memeriksa syarat Unggul, tetapi tidak menghitung Nilai Akreditasi (NA, skala
     400), tidak menentukan status, dan **tidak memeriksa syarat perlu
     Terakreditasi**. Gagal satu syarat itu berarti Tidak Terakreditasi, berapa
     pun NA-nya;
   - **tiga syarat perlu berupa rerata skor** (tata pamong, kurikulum, penjaminan
     mutu) belum dihitung, padahal butir pembentuknya kini sudah diketahui (§3).
3. **60,7 dari 100 bobot dinilai kualitatif** (29 butir 📝). Enam butir berbobot
   ±13,9 menyangkut pengukuran dan tinjauan CPL serta tindakan perbaikan. Sistem
   CPL dan form rapat tindak lanjut yang sedang dibangun langsung menjadi bukti
   untuk butir-butir ini (§6).
4. **SAKTI menghitung skor kuantitatif otomatis dari LKPS Excel** (naskah akademik
   hlm. 18). Supaya skor di situs sama dengan skor resmi, situs sebaiknya bisa
   **mengisi templat LKPS resmi** dari datanya sendiri (§5, P3).
5. Ada **galat yang menunggu terpicu** di `bangun.py` (§5, P1-g).

## 2. Aturan yang sudah diverifikasi dari PDF

### 2.1 Status akreditasi (pedoman penilaian hlm. 12, Tabel 3; diverifikasi dengan `pdftotext -enc UTF-8`)

NA = Σ (bobot butir × skor butir 0–4), Σ bobot = 100, maksimum 400.

| NA | Syarat perlu Terakreditasi | Unggul 3 th | Unggul 5 th | Status |
|---|---|---|---|---|
| ≥ 361 | ✓ | ✓ | ✓ | Unggul, 5 tahun |
| ≥ 361 | ✓ | ✓ | x | Unggul, 3 tahun |
| 331 ≤ NA < 361 | ✓ | ✓ | ✓/x | Unggul, 3 tahun |
| 331 ≤ NA < 361 | ✓ | x | x | Terakreditasi, 5 tahun |
| 200 ≤ NA < 331 | ✓ | ✓/x | ✓/x | Terakreditasi, 5 tahun |
| berapa pun | x | | | Tidak Terakreditasi |
| < 200 | | | | Tidak Terakreditasi |

Celah di tabel: NA ≥ 361 dengan syarat Unggul 3 tahun tidak terpenuhi tidak
tercantum (paling wajar: Terakreditasi 5 tahun, seperti baris 4).

### 2.2 Syarat perlu Program Sarjana (pedoman penilaian hlm. 25–26, Tabel 4.3.1; diverifikasi)

| No | Syarat | Terakreditasi | Unggul 3 th | Unggul 5 th | Dari butir |
|---|---|---|---|---|---|
| 1 | Tata pamong (rerata, Tabel 5.1) | ≥ 2,00 | ≥ 3,00 | ≥ 3,50 | 4-I, 4-II, 5-I, 5-II |
| 2 | Kurikulum (rerata, Tabel 5.2) | ≥ 2,00 | ≥ 3,00 | ≥ 3,50 | 12, 13-I, 13-II, 16-I, 16-II |
| 3 | Basic sciences dan matematika | 15–24 SKS* | ≥ 25 SKS | ≥ 25 SKS | 19 |
| 4 | DTPS doktor | – | ≥ 30 % | ≥ 40 % | 27 |
| 5 | GB/LK/Lektor | – | ≥ 40 % | ≥ 50 % | 28 |
| 6 | DTPS penulis pertama/korespondensi bereputasi, 3 th | – | ≥ 25 % | ≥ 50 % | 35 |
| 7 | Waktu tunggu, 2 th | – | ≤ 6 bulan | ≤ 6 bulan | 49 |
| 8 | Kesesuaian bidang kerja | – | ≥ 50 % | ≥ 50 % | 50 |
| 9 | Penjaminan mutu (rerata, Tabel 5.3) | ≥ 2,00 | ≥ 3,00 | ≥ 3,50 | 53, 54, 55, 56, 57 |

\* Tercetak "15 ≤ SKS ≤ 24"; untuk Terakreditasi ditafsirkan sebagai minimal 15.

Pemetaan indikator a–e ke butir mengikuti bunyi indikator di Tabel 4.3.1 dan
rubrik matriks. "Rerata" tidak dijelaskan instrumen. **Keputusan pemilik
2026-10-12:** rata-rata biasa skor indikator, dengan pemetaan butir seperti
kolom terakhir tabel; butir 53 dihitung sebagai satu indikator (skor
gabungannya).

`site/ambang.js` memakai penomoran tabel lintas jenjang (1–15) dan menandai
syarat 9–11 "belum dibaca". Di tabel lintas jenjang, nomor-nomor itu adalah
syarat publikasi mahasiswa yang hanya berlaku untuk Magister/Doktor. Untuk
Sarjana, kesembilan syarat di atas sudah lengkap.

### 2.3 Definisi TS

TS berlangsung 1 September s.d. 31 Agustus tahun berikutnya. Definisi ini hanya
tercantum di petunjuk sel `Menu!S73` LKPS Excel (panduan tidak mendefinisikan
TS). Ini sudah sesuai dengan `bangun.py:690-692` (bulan ≥ 9 masuk TS berikutnya).

## 3. Status per butir

### 3.1 Butir kuantitatif (31)

| Butir | Bobot | Status | Catatan |
|---|---|---|---|
| 6 Kerja sama | 1,53 | ✅ rumus, ❌ data | lembar `kerjasama` 0 baris. LKPS Excel menghitung keberlakuan dalam 4 TA, matriks "3 tahun terakhir"; situs mengikuti matriks |
| 9 BOP | 0,49 | ✅ 📝 angka | dari `pengaturan.bop`; Tabel 2.b memberi rata-rata per PS, perlu dibagi jumlah mahasiswa |
| 10 Dana penelitian | 0,49 | ⚠️ | situs: Σ dana karya / 3 / NDTPS. Tabel 2.b berisi total biaya penelitian PS dari laporan keuangan, bukan per karya. Pembagian per DTPS adalah tafsiran (lihat §4) |
| 11 Dana PkM | 0,24 | ⚠️ | sama dengan 10 |
| 18 PJP | 0,79 | 📝 | bisa otomatis: LKPS Excel menghitung JP = sks praktikum × 50 dan JB = Σ sks × 50 dari Tabel 3.a.1 |
| 19 Basic sciences | 1,05 | ✅ 📝 angka | angka SKS tercatat dua kali (`ambang.js` capaian 29 dan `pengaturan`). Bisa otomatis dari daftar MK K26 (Tabel 3.a.4) |
| 23, 25 Penelitian/PkM melibatkan mahasiswa | 1,11 / 0,74 | ✅ | |
| 26 Kecukupan DTPS | 1,06 | ⚠️ | situs menganggap NDT = NDTPS. Matriks memakai NDT (semua dosen tetap pengampu) untuk PDTT |
| 27, 28 Doktor, jabatan | 1,76 / 0,85 | ✅ | |
| 30 Beban kerja | 0,28 | ✅ rumus, ❌ data | `bkd` 1 baris untuk 10 dosen |
| 31, 32 Sumber dana | 0,39 / 0,22 | ✅ | |
| 33 Publikasi DTPS | 0,39 | ✅ | NDTPS = semua dosen aktif (sedikit lebih luas dari definisi) |
| 34 Luaran DTPS | 0,22 | ✅ | |
| 35 Karya utama internasional | 1,88 | ✅ | |
| 36 KIB disitasi | 2,17 | ✅ 📝 angka | dihitung manual dari Scopus/GS. Tabel 4.i sendiri tidak konsisten soal sumber sitasi |
| 37 Rekognisi | 2,17 | ✅ | pilihan form tidak memuat "konsultan" (khusus vokasi), sudah benar untuk Sarjana. Tabel 4.j: satu DTPS hanya diakui satu rekognisi; situs menghitung dosen unik |
| 40, 41 Rasio mahasiswa, asing | 0,85 / 0,60 | ✅ | |
| 42 IPK | 1,22 | ✅ | |
| 43 Prestasi | 2,47 | ⚠️ | jendela 5 tahun memakai tahun kalender (`r.tahun`), padahal `tahun_ts` sudah tersedia |
| 44 Masa studi | 1,22 | ⚠️ | situs memakai kohort dengan tahun_masuk + 8 ≤ TS. Tabel 6.d memuat kohort **TS-7 s.d. TS**, jadi kedua jendela tidak beririsan. MS ditaksir dari titik tengah pita |
| 45 Tepat waktu | 1,22 | ⚠️ | rumus PTW = b/a, dengan a dan b tidak didefinisikan. Tabel 6.d menandai (a) jumlah masuk dan (b) lulus 3,5–4,5 th pada **baris kohort TS-3**; situs memakai kohort lain |
| 46 Publikasi mahasiswa | 1,51 | ⚠️ | Tabel 6.e.1 hanya menghitung publikasi dengan mahasiswa sebagai **penulis pertama**; situs menghitung semua publikasi dosen yang mencantumkan mahasiswa |
| 47 Luaran mahasiswa | 0,38 | ✅ rumus, ❌ data | |
| 49–51 Tracer | 3,18 × 3 | ✅ rumus, ❌ data | lembar `tracer_lulusan` 0 baris. Bobot total 9,54 |
| 52 Kepuasan pengguna | 2,47 | ✅ 📝 | |

### 3.2 Butir kualitatif (29), semuanya 📝 skor diisi sendiri

1–5, 7, 8, 12–17, 20–22, 24, 29, 38, 39, 48, 53–60. Rumus gabungan I/II di
`site/bobot.js` dan `site/butir-manual.js` sudah sesuai matriks. Butir dengan
bobot terbesar: 38 sarana prasarana (5,32), 53 SPMI (4,84), 48 tracer study
(3,39), 21, 54, 58 (2,92 masing-masing), 56 (2,91), 57 (2,75).

## 4. Ketidakjelasan di instrumen

**Keputusan pemilik 2026-10-12:** semua tafsiran di kolom "Usul" dipakai. Kalau
LAM Teknik atau asesor kelak memberi penjelasan lain, perbarui tabel ini dan kodenya.

| Hal | Isi | Tafsiran yang dipakai |
|---|---|---|
| Butir 45 PTW | a, b tidak didefinisikan | a = jumlah masuk, b = lulus 3,5–4,5 th, pada kohort bertanda (a)(b) di Tabel 6.d (baris TS-3) |
| Butir 44 MS | 3 < MS ≤ 3,5 dan MS > 8 tanpa skor; MS dihitung dari pita | MS rata-rata tertimbang titik tengah pita, kohort TS-7…TS. Celah rubrik diberi skor 4 (3–3,5) dan 0 (> 8) |
| Butir 10/11 | "rata-rata dana penelitian DTPS/tahun" tidak menyebut per dosen | konfirmasi. Ambang 10 juta hanya masuk akal kalau per DTPS |
| Butir 26 | dua definisi B tumpang tindih; "skor = 2" di kolom 1 | ikuti rumus yang sekarang |
| Butir 30 | RBK < 12 dan > 20 tanpa skor | skor 1 (lantai) |
| Tabel 2.a | Excel memakai 4 TA, matriks 3 tahun | ikuti matriks |
| Sampul matriks | tertulis "Program Diploma Satu" | isi seluruhnya Sarjana; abaikan |
| Varian berkas | "pasca akreditasi pertama dan unggul" tanpa perbedaan isi | perlakukan sebagai instrumen yang sama |

## 5. Kesenjangan dan usulan pekerjaan, menurut prioritas

### P1: cepat dan berdampak langsung pada kesimpulan

a. **Status akreditasi**: hitung NA (skala 400), periksa syarat perlu
   **Terakreditasi** dan Unggul 3/5 tahun, lalu tampilkan perkiraan status sesuai
   Tabel 3. Ini mengubah kesimpulan halaman skor dari "persen" menjadi status.
b. **Tiga syarat rerata** (tata pamong, kurikulum, penjaminan mutu) dari skor
   butir manual, dengan pemetaan di §2.2 (setelah disetujui).
c. **`ambang.js`**: isi `versi: 'APS-AV 2025 1.0'`, tandai syarat Sarjana
   lengkap, tambahkan kolom Terakreditasi.
d. **Butir 44/45**: samakan jendela dengan Tabel 6.d (kohort TS-7…TS, PTW
   kohort TS-3), setelah tafsiran §4 disetujui.
e. **Butir 46**: hitung hanya publikasi dengan mahasiswa sebagai penulis
   pertama. Perlu penanda di `karya_mahasiswa`; kolom `peran` mungkin sudah bisa
   dipakai, periksa dulu isinya.
f. **Butir 43**: pakai `tahun_ts`.
g. **Galat `bangun.py`**: `bangun()` (`bangun.py:657`) memakai `ctt` di baris
   1064, 1073, dan 1141 tanpa menerimanya sebagai parameter. Build akan berhenti
   (`NameError`) begitu lembar `kerjasama` atau `kohort_lulusan` berisi kasus yang
   memicu peringatan.

### P2: data yang belum ada

| Data | Butir | Bobot | Sumber yang disarankan |
|---|---|---|---|
| Tracer study (6.f.1, 6.f.2, 6.g.1) | 49–51 (+48) | 9,54 (+3,39) | hasil tracer PT, per tahun lulus |
| Kohort lulusan (6.d) | 44, 45 | 2,44 | ekspor SIAKAD, per tahun masuk |
| Kerja sama (2.a) | 6 | 1,53 | daftar MoU/MoA/IA prodi |
| Publikasi/luaran mahasiswa (6.e.1, 6.e.3) | 46, 47 | 1,89 | form situs atau lembar xlsx |
| BKD semua DTPS (4.c) | 30 | 0,28 | SISTER/BKD |
| Daftar MK K26 (3.a.1, 3.a.4) | 17, 18, 19 | 4,21 | **data induk MK yang sudah direncanakan untuk sistem CPL**. Tambahkan kolom sks kuliah/seminar/praktikum, MK kompetensi, basic sciences |

### P3: mengisi LKPS resmi otomatis

SAKTI menilai dari LKPS Excel. Situs sebaiknya bisa menulis datanya ke templat
LKPS resmi (sheet 2a, 3b, 3c, 4a, 4d, 4f, 4h, 4j, 6a, 6b, 6c1, 6c2, 6d, 6e1,
6e3, 6f, 6g, 6h1, 6i), sehingga:
- tidak ada pengetikan ulang;
- skor di situs sama dengan skor SAKTI, karena sumbernya sama.

### P4: bukti untuk butir kualitatif (LED)

- Indeks bukti per butir dan per kriteria. Tautan bukti di Google Drive prodi
  sudah tersedia lewat fitur unggah. LED mewajibkan bukti sahih diunggah ke cloud
  dan dilampirkan sebagai tautan.
- Kerangka LED: maksimal 150 halaman; tiap kriteria berisi latar belakang,
  kebijakan, IKU, analisis faktor, dan strategi (SWOT).

## 6. Kaitan dengan sistem CPL dan form rapat

Instrumen tidak meminta angka ketercapaian CPL. Yang dinilai adalah **adanya
pengukuran, tinjauan rutin, dan tindakan perbaikan yang berbukti**:

| Butir | Bobot | Yang dinilai | Bukti dari sistem |
|---|---|---|---|
| 13-II (4) | bagian dari 2,42 | CPL "diukur dan ditinjau secara rutin" | laporan `run_cpl.py` per semester |
| 14-II | bagian dari 2,11 | tinjauan rutin CPL melibatkan pemangku internal dan eksternal | notulen rapat CPL (form rapat) |
| 15-II | bagian dari 2,47 | tinjauan RPS: analisis CPL, metode penilaian | bahan rapat per MK (CPMK terlemah, butir asesmen) |
| 16-II | bagian dari 2,04 | tinjauan pembelajaran sampai tindakan perbaikan | form tindak lanjut beserta statusnya |
| 55, 56 | 1,93 + 2,91 | PPEPP, evaluasi capaian dengan akar masalah | siklus temuan → tindak lanjut → evaluasi |

Butir 12, 13, dan 16 juga membentuk **syarat perlu kurikulum** (§2.2), jadi
sistem ini ikut menentukan status Unggul.

## 7. Urutan kerja yang diusulkan

1. P1-g (galat `bangun.py`), P1-c, P1-f: kecil dan aman.
2. ~~Keputusan pemilik atas §2.2 dan §4~~ (diputuskan 2026-10-12).
3. P1-a dan P1-b: status akreditasi dan syarat perlu.
4. P1-d dan P1-e, lalu P2 sesuai data yang tersedia.
5. P3: pengisian LKPS resmi.
6. P4, bersama form rapat dan tindak lanjut CPL.
