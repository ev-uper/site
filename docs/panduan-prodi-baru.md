# Memakai situs kinerja ini

Langkah pemasangan ada di `README.md`. Panduan ini menjelaskan syarat, komponen, instrumen lain, dan pemeriksaan.

## 1. Syarat dan batas

- **Instrumen.** Skor, bobot, syarat perlu, rencana bukti, dan templat LED
  mengikuti **LAM Teknik, APS-AV 2025 1.0, Program Sarjana**. Prodi sarjana
  lain di bawah LAM Teknik bisa memakainya hampir apa adanya. Prodi di LAM
  lain (LAMEMBA, LAMINFOKOM, LAMDIK, …), BAN-PT, atau jenjang lain harus
  mengganti bagian 7 lebih dulu; tanpa itu skornya salah.
- **Biaya.** Semua komponen memakai paket gratis: Supabase (database dan
  login), GitHub (repo, Actions, Pages), Google Drive dan Apps Script (berkas
  bukti). Proyek Supabase gratis dijeda bila lama tidak dipakai; workflow
  `pemeliharaan.yml` menjaganya tetap hidup. Batas paket gratis (supabase.com/pricing,
  dibaca 2026-11-24): basis data 500 MB per proyek, Storage 1 GB, paling banyak
  2 proyek gratis aktif per akun. Prodi Teknik Sipil UPer memakai 26 MB
  (2026-11-24). Panel Kesehatan sistem di Dasbor menandai "Perlu dicek" bila
  basis data atau Storage mencapai 50% (patch 170).
- **Orang.** Satu pengelola teknis untuk pemasangan (bagian 3–6), lalu admin
  prodi yang bekerja lewat situs saja.

## 2. Komponen

| Komponen | Isi | Siapa yang melihat |
|---|---|---|
| Repo `cv-site` (publik, GitHub Pages) | kode, halaman, patch SQL, workflow | semua orang |
| Proyek Supabase | data karya, dosen, data prodi; login email | lewat situs, sesuai peran |
| Folder Google Drive + Apps Script | berkas bukti yang diunggah | pemegang tautan |
| GitHub Actions | membangun dan menerbitkan situs tiap jam | otomatis |
| Folder cadangan di Google Drive | cadangan bulanan, memuat data pribadi | akun Google prodi |

## 3. Siapkan akun

1. **Akun Google prodi** (bukan akun pribadi), misalnya `prodi.x.dashboard@gmail.com`.
   Pemilik folder bukti dan Apps Script.
2. **Organisasi GitHub prodi**, dengan satu repo publik (nama bawaan `cv-site`).
3. **Proyek Supabase** baru (supabase.com, paket gratis), sebaiknya di akun
   Supabase milik prodi itu sendiri: satu akun hanya boleh punya 2 proyek
   gratis yang aktif, jadi pengelola yang memasang untuk beberapa prodi
   akan cepat terbentur batas ini.

## 4-6. Pasang

Ikuti `README.md`.

## 7. Bila instrumennya bukan LAM Teknik Sarjana

Bagian ini harus disusun ulang mengikuti instrumen Anda **sebelum** skor
dipakai.

Sejak 2026-11-24 instrumen dipindah bertahap ke folder sendiri,
`site/instrumen/<id>/` (berisi `instrumen.json` dan modulnya). Instrumen
dipilih saat pemasangan: `install.py` menanyakan "Instrumen akreditasi"
(daftar dari `site/instrumen/*/instrumen.json`, bawaan `lam-teknik-s1`;
2026-11-25), menulis `accreditation.instrument` di `config.yaml`, lalu
menjalankan `python tools/pilih_instrumen.py` yang menulis pintu di `site/`
dan memeriksa bahwa folder itu lengkap (butuh Node.js; lingkungan pemasang
`conda create -n pasang-situs python git nodejs`). Bila gagal, `config.yaml`
dikembalikan ke instrumen lama. Modul yang sudah pindah ditandai *(folder
instrumen)*; sisanya masih di `site/`.

Instrumen yang tersedia (2026-11-24):

- `lam-teknik-s1`: LAM Teknik, APS-AV 2025 1.0, Program Sarjana (acuan kontrak).
- `lamdepilar-magister`: LAMDEPILAR, IAPS DEPILAR 1.0, Magister akademik, untuk
  **perolehan status** (skor elemen 0–3, Terakreditasi bila NA > 200 dan syarat
  Tabel 7 terpenuhi). Id butir 101–130 = elemen D.1 … R.6, supaya tidak
  bertabrakan dengan nomor butir LAM Teknik di modul umum; **wajib**
  `supabase/instal-lengkap.sql` (tanpa itu bukti butir > 60
  ditolak database). Halaman Skor, draf LED (templat resmi LAMDEPILAR,
  kerangka per elemen lewat `site/led-kerangka.js`), dan LKPS (templat resmi
  diisi langsung lewat `site/lkps-lamdepilar.js`: semua contoh fiktif
  dikosongkan menurut `lkps-contoh.json`, lalu Cover, D.1, E.2.1, E.4.1–E.4.2
  (CPL dan matriks MK–CPL kurikulum terbaru; bobot dibagi per CPL sehingga tiap
  kolom berjumlah 1; CPL > 5 menambah kolom setelah O), E.4.3 (prestasi
  TS-4…TS), E.1.1–E.1.2 (per angkatan), P.1.1, P.1.2 (pembimbing utama TA), P.1.3–P.1.7 (EWMP dari BKD, dosen tidak tetap, praktisi,
  rekognisi, tendik), L.1 (sarana menurut standar), L.4.1 (lulusan, terlacak,
  WT < 3 bulan), A.1, dan A.5.1–A.5.2 blok Program Magister (A.5.3 neraca dari
  rumus templat) diisi dari situs) sudah diuji. L.1 dibaca dari tab
  Data prodi **Sarana menurut standar** (`lkps_sarana_standar`); **wajib**
  `supabase/instal-lengkap.sql`. E.1.1–E.1.2 dibaca dari tab **Mahasiswa
  per angkatan** (`lkps_mahasiswa_angkatan`, satu baris per angkatan TS-4…TS: admisi,
  teregistrasi, status pada TS, mahasiswa asing; kolom periksa dan E.1.3 dari rumus
  templat); **wajib** `supabase/instal-lengkap.sql`. P.1.2 dibaca dari tab **Pembimbing
  utama TA** (`lkps_bimbingan_utama`, satu baris per dosen per tahun akademik,
  PS ini dan PS lain); **wajib** `supabase/instal-lengkap.sql`. Analisis P.1.2
  ditulis sebagai rumus: pembimbing = banyak baris tabel, jumlah dosen = banyak dosen tetap
  Tabel P.1.1, "> 6 mhs" = rata-rata bimbingan per tahun di semua program
  ((D+E+F+H+I+J)/3) lebih dari 6. Analisis P.1.1 juga rumus atas baris Tabel P.1.1: tidak
  sesuai = mengampu MK di PS ini tanpa V kesesuaian, sertifikat pendidik = nomor serdos terisi,
  sertifikat profesi = kolom K terisi, Profesor/Lektor Kepala dari kolom jabatan.
  Analisis P.1.3: kolom K berisi jumlah dua semester TS, jadi "< 12 SKS" dan "> 20 SKS"
  dibandingkan dengan K/2 (rata-rata per semester); jumlah dosen = banyak baris Tabel P.1.3.
  Analisis P.1.4: dosen tidak tetap = baris Tabel P.1.4; jumlah dosen = baris P.1.1 + baris
  P.1.4, jadi persentasenya NDTT / (NDT + NDTT). Tabel P.1.5 (praktisi) hanya untuk Diploma
  Tiga/Sarjana Terapan menurut templat: Magister tidak mengisi barisnya, rumus analisisnya
  tetap ada (jumlah dosen = P.1.1 + P.1.4 + P.1.5). Analisis P.1.6: dosen **unik** dengan
  rekognisi per tingkat (satu dosen dengan beberapa rekognisi dihitung sekali), dibagi dosen
  tetap P.1.1. Analisis P.1.7: banyak V per kolom pendidikan tendik (DIV/S1 = kolom I + J).
  Semua pilihan ini keputusan pemilik 2026-11-25.
  Draf LED (`site/led-kerangka.js`, 2026-11-25) juga mengisi di luar judul elemen: sampul
  (logo prodi, Program Studi Magister <prodi>, UPPS dan kota dari Narasi LED › Identitas,
  perguruan tinggi, bulan dan tahun), surat pengantar (tabel usulan = prodi ini, status
  terakreditasi), dan bab 1, 2, 4, 5 (kalimat petunjuk templat tetap, teks pengisi diganti
  [isi] dan fakta situs: TS dan instrumen di 1.1, tim penyusun dari Narasi LED › Tim di 1.2,
  CPL kurikulum terbaru di 4.1, rujukan matriks ke LKPS E.4.2). Rencana bukti per elemen
  (`site/instrumen/lamdepilar-magister/rencana-bukti-isi.js`) berisi daftar "Uraian, data,
  atau dokumen" Buku 2 dan tabel LKPS per elemen menurut Buku 6 (Buku 6 memakai susunan
  elemen lama; dicocokkan menurut nama). Halaman Skor menampilkan "Jalan menuju
  Terakreditasi" dengan satu sasaran; grafik tren potret memakai batas 200 dari 300.
  A.5 dibaca dari tab **Keuangan A.5** (`lkps_keuangan`, satu baris per pos per
  tahun akademik dalam rupiah; LKPS menulis juta rupiah; daftar pos dan barisnya di
  `site/keuangan-a5.js`); **wajib** `supabase/instal-lengkap.sql`, serta
  `supabase/instal-lengkap.sql` supaya bukti baris ketiga tab ini
  diterima database (`lkps_bukti_tabel_check`, dipasang ulang lagi oleh 171;
  `tests/test_bukti_tabel.py` menjaga tab baru berikutnya). Keempat tab itu dan barisnya di Kelengkapan
  hanya muncul bila instrumen aktif memakai `lkps-lamdepilar.js` (penanda
  `mesinLkps` di `data-prodi.html`, elemen ke-5 `TAB_DATA` di `kelengkapan.js`).
  Bila data melebihi baris templat di lembar P.1 atau L.1, baris disisipkan
  (rumus, sel gabungan, validasi, dan Daftar Isi ikut bergeser seperti di
  Excel); E.4 menambah kolom bila CPL > 5. Semua sel analisis P.1 berupa rumus. R.3/R.6 ditunda
  (pemilik 2026-11-24). Indeks bukti LKPS (`site/lkps-bukti.js`) memakai
  `TABEL_LAMDEPILAR` (25 tabel Magister; tanpa E.1.3, A.5.3, dan lembar
  Diploma/Terapan) bila mesinnya `lkps-lamdepilar.js`; R.3.1/R.6.1 berisi karya
  terverifikasi TS-2…TS walau tabelnya diisi tangan. Lembar LKPS lain, rencana
  bukti, dan penanggung jawab per unsur belum disesuaikan.

| Berkas | Isi yang khusus instrumen |
|---|---|
| `site/instrumen/<id>/bobot.js` *(folder instrumen)* | bobot tiap butir (jumlah harus 100), skor tertinggi satu butir `SKOR_MAKS` (LAM Teknik 4), nama instrumen di kartu `NAMA_INSTRUMEN`, rujukan rumus di kaki halaman `SUMBER_RUMUS`, `BUTIR_LAM_TEKNIK` (true hanya bila nomor butir 1–60 yang tertulis di modul umum milik instrumen ini; false: halaman menyembunyikan bagian itu, mis. butir berumus `butir-data.js`, tautan butir di Verifikasi, isian Narasi LED selain Identitas dan Tim, grafik bernomor dan catatan kaki aturan butir di Grafik, Simulasi PJP di menu, B3/C seksi Jalan di Skor; 2026-11-25) |
| `site/instrumen/<id>/butir-manual.js` *(folder instrumen)* | daftar butir yang dinilai manual, rumus gabungan komponennya, rumus kepuasan pengguna, susunan bagian kartu di halaman Skor `SEKSI_KARTU` |
| `site/instrumen/<id>/unsur-butir.js` *(folder instrumen)* | unsur bukti per butir dan aturan skornya, penanggung jawab per unsur |
| `site/instrumen/<id>/rumus-butir.js` *(folder instrumen)* | rumus butir yang dihitung dari data (`butir06` … `butir51`) dan daftar butir berumus; pembantu halaman dikirim lewat `buatRumus(h)` |
| `site/skor.html` | sisa yang masih khusus LAM Teknik: sumber isian `IS()` (JP/JB, BOP, RBK, butir 20/22/24) dan catatan butir 18/20/22/24/30; skala dan batas status sudah dari instrumen (`SKOR_MAKS`, `TEKS_BATAS`) |
| modul umum lain (`data-butir.js`, `kelengkapan.js`, `led*.js`, `rencana-bukti.js`, `survei-kepuasan.js`, …) | nomor butir LAM Teknik tertulis langsung. Instrumen lain memakai nomor yang tidak bertabrakan (LAMDEPILAR: 101–130, pemilik 2026-11-24) |
| `site/instrumen/<id>/ambang.js`, `site/instrumen/<id>/syarat-unggul.js` *(folder instrumen)* | syarat perlu terakreditasi dan unggul, status menurut NA, teks batasnya (`TEKS_BATAS`), rujukannya (`SUMBER_STATUS`), sasaran yang dapat dicapai (`SASARAN`, `NAMA_SASARAN`), judul seksi `JUDUL_JALAN`, garis batas grafik potret `BATAS_NA` |
| `site/instrumen/<id>/rencana-bukti-isi.js` *(folder instrumen)* | bukti yang disiapkan per butir (`RENCANA_BUKTI`: yang dinilai untuk skor tertinggi, bukti, tabel LKPS, bagian LED, unit, catatan); tampilannya di `site/rencana-bukti.js` |
| `site/rencana-bukti.js` | jenis dokumen pustaka (`JENIS_DOKUMEN`) dan indeks tabel LKPS (`LKPS_TABEL`), masih milik LAM Teknik |
| `site/instrumen/<id>/dokumen.js` *(folder instrumen)* | `LED = {mesin, templat}`: mesin penyusun draf LED (`led.js` untuk LAM Teknik, `led-kerangka.js` untuk templat dengan satu paragraf pengisi per elemen) dan berkas templatnya; `LKPS = {mesin, templat, contoh?, jenjang?}`: `lkps-tabel.js` (LAM Teknik, salin-tempel) atau mesin yang mengisi templat resmi langsung |
| `site/led-template.docx`, `site/led.js`, `site/led-data.js`, `site/led-grafik.js` | templat LED LAM Teknik, peta isinya (`docs/led-peta-butir.md`), tabel data dan grafik per butir |
| `site/lkps-template.xlsx`, `site/lkps.js` | templat LKPS resmi (Sarjana) dan peta sel yang diisi (lembar rekap dan lembar daftar) |
| `tests/js/` | tes rumus; nilai harapannya mengikuti rumus LAM Teknik |

Prodi di bawah LAM Teknik **tidak** perlu mengubah bagian ini.

## 8. Isi awal oleh admin prodi

Setelah situs jalan, admin mengisi lewat situs:

1. **Kelola dosen**: semua dosen, peran, aktif, DTPS, pendidikan, jabatan.
2. **Data prodi**: mahasiswa per TS, kohort lulusan, tracer, kepuasan
   pengguna, kerja sama, BKD, prestasi/publikasi/luaran mahasiswa.
3. **Isian butir & dokumen**: nilai butir manual, angka pengaturan, pustaka
   dokumen.
4. **Daftar mata kuliah**: Data prodi, tab Mata kuliah.
5. Dosen mengisi karya masing-masing; admin memverifikasi. Panduan pengguna
   ada di situs: menu **Bantuan › Panduan pengguna**.

## 9. Pemeriksaan

- `python -m pytest -q` (butuh Python dengan `pandas`,
  `requests`, `pytest`, dan Node.js untuk tes rumus): semua harus lulus.
- Supabase SQL Editor: jalankan `supabase/ekspor-skema.sql`; tabel, policy,
  dan fungsi harus sesuai berkas patch (cara mencocokkan di
  `supabase/README.md`).
- Buka situs tanpa login: beranda menampilkan grafik dan angka rekap, tanpa
  tautan bukti.
