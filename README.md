# Situs kinerja dan akreditasi program studi

Dosen mengisi karya dan bukti, admin mengisi data prodi, skor LAM dihitung
otomatis, dan draf LED serta LKPS diunduh dari situs. Dibuat untuk **LAM
Teknik, APS-AV 2025, Program Sarjana**. Untuk instrumen lain, baca dulu
`docs/panduan-prodi-baru.md` bagian 7.

Ada dua paket yang dipilih saat pemasangan: **lengkap** (semua modul, termasuk
rapat, hibah, kalender, pengingat) dan **akreditasi** (hanya yang dibutuhkan
skor, LKPS, dan LED). Lihat langkah 5.

**Ingin melihat dulu sebelum memasang?** Setelah repo disalin ke komputer, jalankan
`python coba_lokal.py` (butuh `conda install -y pandas requests openpyxl pyyaml`).
Situs terbuka di `http://localhost:8790/` dengan data contoh, tanpa Supabase,
GitHub, atau Google; bilah MODE COBA di bawah halaman untuk berganti peran
admin, dosen, atau tamu. Langkah rincinya: panduan lengkap, tahap 3b.

Prodi memakai **satu repo publik**, yang sekaligus menjadi situsnya. Yang perlu
disiapkan: akun atau organisasi GitHub prodi, akun Google prodi, proyek Supabase
baru, dan Miniforge di komputer pemasang. Miniforge hanya dipakai sekali, saat
pemasangan. Setelah itu semuanya berjalan di GitHub. Semua layanan bisa memakai
paket gratis.

**Panduan lengkap langkah demi langkah:** `docs/panduan-pemasangan.pdf`. Halaman
ini ringkasannya.

**Repo ini publik.** Kode dan riwayat commit bisa dibaca siapa saja. Jangan
pernah memasukkan data dosen, secret key, atau cadangan ke dalamnya. Data
tersimpan di Supabase, dan cadangannya di Google Drive prodi.

## 1. Buat akun prodi

Semua akun atas nama prodi, supaya bisa diserahterimakan. Rinciannya di
panduan lengkap, tahap 1.

1. **Gmail prodi** (`accounts.google.com/signup`, akun pribadi biasa, bukan akun
   kampus). Aktifkan **Verifikasi 2 Langkah** dengan SMS atau aplikasi
   autentikator. Drive, Apps Script, dan pengirim email login memakai akun ini.
2. **GitHub prodi** (`github.com/signup`), didaftarkan dengan Gmail prodi.
   Disarankan juga **organisasi GitHub** prodi (paket Free) dengan sedikitnya dua
   owner. Nama organisasi (atau username) menjadi `<org>` di alamat situs.
3. **Supabase** (`supabase.com`, Sign up), didaftarkan dengan Gmail prodi.
4. Repo templat ini privat: kirim username GitHub prodi dan nama organisasi ke
   pengelola templat, lalu terima undangannya di Gmail prodi.

Simpan semua kata sandi di pengelola kata sandi prodi, jangan di repo.

## 2. Buat repo

1. Di halaman repo templat ini, klik **Use this template › Create a new
   repository**, pilih **Public**. Nama repo bebas, huruf kecil tanpa spasi;
   bawaan dan saran: `cv-site`. Di bawah, `<repo>` berarti nama itu.
2. Di repo baru: **Settings › Pages**, *Source* pilih **GitHub Actions**. Alamat
   situs: `https://<org>.github.io/<repo>/` (repo bernama `<org>.github.io`
   tayang di `https://<org>.github.io/`).
3. Pasang Miniforge, lalu di **Miniforge Prompt** siapkan Python dan git, dan
   clone repo itu:

       conda create -n pasang-situs python git -y
       conda activate pasang-situs
       git config --global user.name "Prodi X"
       git config --global user.email "prodi.x@gmail.com"
       git clone https://github.com/<org>/<repo>.git
       cd <repo>

   Nama dan email ini tercatat pada commit dan terlihat publik.

## 3. Supabase

1. Buat proyek baru yang **kosong**.
2. **SQL Editor › New query**, tempel seluruh isi `supabase/instal-lengkap.sql`,
   lalu **Run**. Satu berkas ini berisi seluruh tabel. Jalankan **sekali saja**;
   kalau tabelnya sudah ada, ia berhenti dengan galat dan data tetap aman.
3. **Authentication › URL Configuration**: isi *Site URL* dengan alamat situs,
   dan tambahkan `https://<org>.github.io/<repo>/**` ke *Redirect URLs*.
4. Catat:
   - Project URL (`https://<kode>.supabase.co`): tombol **Connect** di atas
     halaman proyek.
   - Publishable key (`sb_publishable_...`) dan secret key (`sb_secret_...`):
     **Project Settings › API Keys**. Kalau yang tampil hanya kunci lama `anon`
     dan `service_role` (`eyJ...`), buat kunci baru di halaman itu.

   Secret key hanya boleh disimpan di GitHub Secrets.

## 4. Email login (wajib sebelum dipakai dosen)

Ini **bukan** akun baru. Supabase diatur untuk mengirim email login lewat Gmail
prodi (disebut SMTP): buat Sandi Aplikasi di akun Google prodi, lalu isi di
pengaturan SMTP Supabase.

Situs masuk lewat tautan email. Menurut dokumen Supabase, layanan email
bawaannya hanya mengirim ke anggota tim proyek, sekitar 2 email per jam. Karena
itu pasang SMTP sendiri. Cara gratis tanpa domain sendiri: Gmail akun prodi,
sampai 500 email per hari.

1. Pakai akun Gmail biasa milik prodi, bukan akun kampus: pada akun organisasi,
   pilihan App Password bisa tidak muncul.
2. Di akun Google itu, pastikan **Verifikasi 2 Langkah** aktif, lalu buka
   `myaccount.google.com/apppasswords` dan buat Sandi Aplikasi. Kode 16 huruf
   ini hanya tampil sekali.
3. Di Supabase, **Authentication › Emails**, tab **SMTP Settings**
   (`supabase.com/dashboard/project/<kode>/auth/smtp`), nyalakan **Enable custom SMTP**
   lalu isi, kemudian **Save changes**:

   | Isian | Nilai |
   |---|---|
   | Host | `smtp.gmail.com` |
   | Port number | `587` |
   | Username | alamat Gmail prodi lengkap |
   | Password | App Password, bukan kata sandi Gmail |
   | Sender email address | alamat Gmail prodi yang sama |
   | Sender name | nama situs, misalnya `Kinerja Teknik Lingkungan` |

4. Naikkan batas kirim email di halaman **Rate Limits** sesuai jumlah dosen;
   menurut dokumen Supabase, batas awalnya 30 email per jam.
5. Disarankan: ganti isi email ke Bahasa Indonesia di **Authentication › Emails ›
   Templates** (**Magic link or OTP** dan **Confirm sign up**). Contoh isinya di
   panduan lengkap, tahap 5 bagian D. Templat baru berlaku setelah beberapa menit.
6. Setelah situs terbit (langkah 8), minta satu dosen yang bukan anggota tim
   Supabase mencoba masuk. Periksa juga folder Spam.

App Password hanya disimpan di Supabase, jangan di repo. Kalau kata sandi Gmail
diganti, App Password ikut batal dan email login berhenti sampai kode baru
dipasang. Bila pengirim harus memakai domain kampus, pakai penyedia SMTP seperti
Resend; isiannya di tempat yang sama.

## 5. Jalankan pemasang

Di Miniforge Prompt, di folder repo:

    python install.py

Jawab pertanyaannya: nama prodi, institusi, organisasi GitHub, nama repo
(Enter untuk `cv-site`), Project URL, publishable key, admin pertama, logo,
warna, dan paket situs. URL Apps Script boleh dikosongkan. **Jangan** memasukkan secret key.

Paket situs: `lengkap` (Enter) untuk semua modul, atau `akreditasi` untuk
modul yang dibutuhkan skor LAM, LKPS, dan LED saja (tanpa rapat, hibah,
kalender, pengingat email, halaman Kepakaran dan Rekap SDGs). Bisa diganti
kapan saja dengan menjalankan `python install.py` lagi; data tidak hilang.

Admin pertama adalah **orang** yang akan masuk ke situs sebagai admin. Isi dengan
email kampusnya, bukan Gmail prodi: Gmail prodi hanya pemilik layanan dan pengirim
email login. Admin berikutnya ditambahkan dari halaman Kelola dosen.

Di akhir, layar menampilkan alamat situs serta *Site URL* dan *Redirect URLs*
untuk Supabase; cocokkan dengan langkah 3.3. Lalu dua hal yang tidak disimpan
di berkas mana pun:

1. **SQL admin pertama:** jalankan di SQL Editor Supabase.
2. **Token cadangan:** simpan sementara untuk langkah 6 dan 7.

Belum perlu push. Selesaikan langkah 6 dan 7 dulu.

## 6. Unggah bukti dan cadangan (Google Drive)

Ikuti `apps-script/README.md` bagian Pemasangan dengan akun Google prodi,
termasuk folder cadangan dan token dari langkah 5. Lalu jalankan
`python install.py` lagi untuk mengisi URL Web App; jawaban lain tinggal Enter.

Menjelang visitasi, tambahkan Script Property `LKD_SANDI` (kata sandi berkas
privat untuk asesor, minimal 8 karakter); kosongkan lagi setelah visitasi.
Rinciannya di panduan lengkap, tahap 7.

## 7. Isi pengaturan GitHub

Di repo: **Settings › Secrets and variables › Actions**.

Tab **Secrets**:

| Nama | Isi |
|---|---|
| `SUPABASE_URL` | Project URL |
| `SUPABASE_SERVICE_KEY` | secret key Supabase |
| `CADANGAN_TOKEN` | token dari langkah 5 |

Tab **Variables**:

| Nama | Isi | Contoh |
|---|---|---|
| `NAMA_PRODI` | nama prodi, tanpa kata "Program Studi" | `Teknik Lingkungan` |
| `NAMA_INSTITUSI` | nama perguruan tinggi | `Universitas Contoh` |

Workflow tidak berjalan sebelum `NAMA_PRODI` terisi.

## 8. Terbitkan

    git add -A
    git commit -m "Pasang situs"
    git push

Tunggu **Actions › Bangun situs** hijau, lalu buka alamat situs dan masuk memakai
email admin pertama. Uji cadangan sekali: **Actions › Pemeliharaan basis data ›
Run workflow**, pilih `cadangkan`, lalu lihat zip-nya di folder cadangan Drive.

## 9. Isi awal

1. **Kelola dosen:** semua dosen, peran, aktif, DTPS, pendidikan, jabatan.
2. Buka **Akreditasi › Kelengkapan LED**. Halaman ini menghitung yang belum
   terisi dan menautkan ke tempat mengisinya.
3. Bila perlu, kata kunci visi keilmuan dengan contoh di
   `supabase/contoh-kata-visi.sql`.

Panduan pengguna ada di situs, menu **Bantuan**. Cara kerja otomatisnya:
`docs/bangun-otomatis.md`. Penjelasan lengkap: `docs/panduan-prodi-baru.md`.

## Hak cipta

Perangkat lunak ini milik Program Studi Teknik Sipil, Universitas Pertamina, dan hanya boleh
dipakai program studi di lingkungan Universitas Pertamina dengan izin tertulis. Ketentuan
lengkap: `LICENSE`.
