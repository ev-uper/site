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
  `pemeliharaan.yml` menjaganya tetap hidup.
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
3. **Proyek Supabase** baru (supabase.com, paket gratis).

## 4-6. Pasang

Ikuti `README.md`.

## 7. Bila instrumennya bukan LAM Teknik Sarjana

Bagian ini harus disusun ulang mengikuti instrumen Anda **sebelum** skor
dipakai:

| Berkas | Isi yang khusus instrumen |
|---|---|
| `site/bobot.js` | bobot tiap butir (jumlah harus 100) |
| `site/butir-manual.js` | daftar butir yang dinilai manual dan rumus gabungan komponennya |
| `site/skor.html` | rumus butir yang dihitung dari data (`butir06` … `butir51`) |
| `site/ambang.js`, `site/syarat-unggul.js` | syarat perlu terakreditasi dan unggul |
| `site/rencana-bukti.js` | bukti yang disiapkan per butir, jenis dokumen |
| `site/led-template.docx`, `site/led.js`, `site/led-data.js`, `site/led-grafik.js` | templat LED, peta isinya (`docs/led-peta-butir.md`), tabel data dan grafik per butir |
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
