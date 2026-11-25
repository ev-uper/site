# Panduan Pemasangan

Situs Kinerja dan Akreditasi Program Studi

Untuk LAM Teknik, APS-AV 2025, Program Sarjana. Versi 9 November 2026.

## Gambaran singkat

Situs ini membuat dosen bisa mengisi karya dan bukti, admin bisa mengisi data prodi, skor LAM dihitung otomatis, dan draf LED serta LKPS bisa diunduh dari situs.

Setiap prodi memasang salinannya sendiri. Pemasangan dikerjakan **sekali**. Setelah selesai, situs berjalan sendiri di GitHub, tanpa komputer yang harus menyala.

| Bagian | Fungsi | Biaya |
|---|---|---|
| Repo GitHub situs (publik) | kode dan situs yang terbit | gratis |
| GitHub Actions | membangun situs tiap jam, menghitung CPL dan mengirim cadangan tiap malam | gratis |
| Supabase | database dan login dosen | paket gratis |
| Gmail prodi | mengirim email login | gratis |
| Google Drive dan Apps Script prodi | berkas bukti, cadangan data, berkas privat | gratis |
| Miniforge di satu komputer | dipakai sekali saat pemasangan | gratis |

### Lambang dalam panduan ini

| Lambang | Artinya | Contoh |
|---|---|---|
| `<org>` | nama akun atau organisasi GitHub prodi, huruf kecil | `prodi-contoh` |
| `<repo>` | nama repo situs yang Anda pilih di tahap 3; bawaan `cv-site` | `cv-site` |
| `<alamat-situs>` | `https://<org>.github.io/<repo>` | `https://prodi-contoh.github.io/cv-site` |
| `<kode>` | kode proyek Supabase, 20 huruf | `abcdefghijklmnopqrst` |

Ganti lambang itu dengan nilai Anda setiap kali menyalin perintah atau alamat.

### Urutan tahap

| Tahap | Pekerjaan | Tempat |
|---|---|---|
| 1 | Buat akun prodi dan minta akses templat | Google, GitHub, Supabase |
| 2 | Pasang Miniforge | komputer |
| 3 | Buat repo dari templat | GitHub, komputer |
| 3b | (pilihan) Coba situs di komputer sendiri, dengan data contoh | komputer |
| 4 | Buat database dan ambil kunci | Supabase |
| 5 | Sambungkan email login (Gmail ke Supabase) | akun Google, Supabase |
| 6 | Jalankan pemasang | komputer, Supabase |
| 7 | Pasang unggah bukti, cadangan, dan kata sandi berkas privat | Google Drive, Apps Script, komputer |
| 8 | Isi pengaturan GitHub | GitHub |
| 9 | Terbitkan situs | komputer, GitHub |
| 10 | Periksa hasilnya | situs, Drive |
| 11 | Isi data awal | situs |

Kerjakan berurutan. Jangan lakukan `git push` sebelum tahap 9. Kerjakan tahap 1 beberapa hari lebih dulu, karena akses ke repo templat menunggu pengelola templat.

### Yang perlu disiapkan

- Nomor HP pengelola, untuk verifikasi akun Google.
- Email kampus pengelola, sebagai email pemulihan akun.
- Komputer Windows untuk memasang.
- Logo prodi berformat `.png`, kalau sudah ada. Bisa diganti nanti.
- Kontak pengelola templat, untuk meminta akses ke repo templat (tahap 1).
- Pengelola kata sandi atau tempat aman untuk menyimpan sementara kunci dan token (bukan berkas di repo).

### Tiga aturan penting

> **Repo ini publik.** Kode dan riwayat commit bisa dibaca siapa saja. Jangan pernah memasukkan data dosen, cadangan, kata sandi, atau kunci rahasia ke dalamnya.

> **Secret key Supabase hanya disimpan di GitHub Secrets.** Jangan ditulis di berkas mana pun, jangan dimasukkan ke `install.py`, dan jangan ke Apps Script. Kunci ini menembus seluruh aturan akses database.

> **`instal-lengkap.sql` dijalankan sekali, pada proyek kosong.** Satu berkas ini berisi seluruh tabel. Kalau tabelnya sudah ada, ia berhenti dengan galat dan data tetap aman.

### Rahasia dan tempat menyimpannya

| Rahasia | Dibuat di | Disimpan **hanya** di |
|---|---|---|
| Kata sandi akun Gmail, GitHub, dan Supabase prodi, serta *recovery codes* GitHub | tahap 1 | pengelola kata sandi prodi; diserahkan saat serah terima |
| Kata sandi database Supabase | tahap 4 | pengelola kata sandi prodi; situs tidak memakainya |
| Secret key Supabase (`sb_secret_...`) | tahap 4 | GitHub Secrets `SUPABASE_SERVICE_KEY` |
| Sandi Aplikasi Gmail | tahap 5 | pengaturan SMTP Supabase |
| Token cadangan | tahap 6 | Script Properties `CADANGAN_TOKEN` dan GitHub Secrets `CADANGAN_TOKEN` |
| Kata sandi berkas privat | tahap 7 | Script Properties `LKD_SANDI`, dan diserahkan ke asesor |

Publishable key Supabase (`sb_publishable_...`) **bukan** rahasia. Ia memang tertulis di `site/config.js` dan aman di repo publik, karena aksesnya dibatasi aturan database.

## Tahap 1. Buat akun prodi dan minta akses templat

Semua akun dibuat **atas nama prodi**, bukan atas nama pribadi, supaya bisa diserahterimakan saat pengelola berganti. Buat berurutan: Gmail lebih dulu, karena akun lain didaftarkan dengan alamat Gmail itu.

| No | Akun | Untuk apa | Didaftarkan dengan |
|---|---|---|---|
| 1 | Gmail prodi | pengirim email login dosen, Google Drive, Apps Script, alamat pendaftaran akun lain | nomor HP pengelola |
| 2 | GitHub prodi | menyimpan kode dan menerbitkan situs | Gmail prodi |
| 3 | Organisasi GitHub prodi (disarankan) | pemilik repo situs; bisa dikelola beberapa orang | akun GitHub prodi |
| 4 | Supabase | database dan login dosen | Gmail prodi |

Google Drive dan Apps Script **tidak** perlu akun tersendiri: keduanya bagian dari akun Gmail prodi. Email login (tahap 5) juga **bukan** akun baru, melainkan pengaturan yang menyambungkan Gmail prodi ke Supabase.

### 1a. Akun Gmail prodi

1. Buka `accounts.google.com/signup`. Bila ditanya akun untuk apa, pilih **untuk penggunaan pribadi**. Yang dibuat adalah akun Gmail biasa (`...@gmail.com`).
2. Jangan memakai akun dari kampus (`...@kampus.ac.id`). Menurut bantuan Google, Sandi Aplikasi yang diperlukan di tahap 5 tidak tersedia untuk akun kerja atau sekolah.
3. Nama: nama prodi, misalnya `Prodi Teknik Lingkungan`. Alamat: misalnya `prodi.x.dashboard@gmail.com`.
4. Kata sandi: panjang dan baru. Simpan di pengelola kata sandi prodi.
5. Nomor HP dan email pemulihan: nomor HP dan email kampus pengelola. Perbarui saat serah terima.
6. Setelah akun jadi, buka `myaccount.google.com` › **Keamanan**, lalu aktifkan **Verifikasi 2 Langkah** dengan SMS atau aplikasi autentikator. Jangan hanya memakai kunci keamanan (*security key*), karena dengan cara itu Sandi Aplikasi tidak bisa dibuat.

### 1b. Akun GitHub prodi

1. Buka `github.com/signup` dan daftar dengan alamat Gmail prodi.
2. *Username*: huruf kecil, misalnya `prodi-contoh-admin`. Bila tidak memakai organisasi (1c), username ini menjadi `<org>` dan bagian alamat situs `https://<org>.github.io/...`.
3. Masukkan kode verifikasi yang dikirim ke Gmail prodi.
4. Bila GitHub meminta autentikasi dua faktor (2FA), ikuti langkahnya. Simpan *recovery codes* di pengelola kata sandi prodi; tanpa kode itu, akun yang kehilangan HP autentikator sulit dipulihkan.

### 1c. Organisasi GitHub prodi (disarankan)

Dengan organisasi, beberapa pengelola bisa mengurus repo dengan akun GitHub masing-masing, tanpa berbagi kata sandi.

1. Masuk dengan akun GitHub prodi. Klik foto profil di kanan atas › **Settings** › **Organizations** › **New organization**, lalu pilih paket **Free**.
2. *Organization name*: huruf kecil, misalnya `prodi-contoh`. Nama ini menjadi `<org>` dan bagian alamat situs. *Contact email*: Gmail prodi.
3. Undang akun GitHub pribadi pengelola sebagai **Owner** (halaman organisasi › **People** › **Invite member**). Sebaiknya ada sedikitnya dua owner, supaya organisasi tidak terkunci bila satu akun hilang.

Tanpa organisasi pun bisa: akun GitHub prodi langsung menjadi pemilik repo.

### 1d. Akun Supabase

1. Buka `supabase.com`, klik **Sign up**, lalu daftar dengan alamat Gmail prodi dan kata sandi baru.
2. Buka email konfirmasi dari Supabase di Gmail prodi, lalu klik tautannya.
3. Proyek database dibuat nanti, di tahap 4.

### 1e. Minta akses ke repo templat

Repo templat bersifat privat. Kirim ke pengelola templat:

- username GitHub prodi (1b), dan
- nama organisasi (1c), bila ada.

Tunggu email undangan dari GitHub di Gmail prodi, lalu klik **Accept invitation**. Setelah itu repo templat bisa dibuka dan tahap 3 bisa dikerjakan.

Catat username GitHub, `<org>`, dan alamat Gmail prodi di lembar catatan di akhir panduan.

## Tahap 2. Pasang Miniforge

Miniforge menyediakan Python, git, dan Node.js. Ketiganya hanya dipakai saat pemasangan (Node.js untuk memasang instrumen akreditasi di tahap 6).

1. Buka `github.com/conda-forge/miniforge`, bagian **Download**, lalu unduh penginstal Windows `Miniforge3-Windows-x86_64.exe`.
2. Jalankan penginstalnya dan pilih **Just Me**. Pengaturan lain biarkan bawaan.
3. Dari menu Start, buka **Miniforge Prompt**. Semua perintah di panduan ini diketik di jendela itu.
4. Buat lingkungan kerja berisi Python, git, dan Node.js:

```
conda create -n pasang-situs python git nodejs -y
conda activate pasang-situs
```

Baris perintah kini diawali `(pasang-situs)`.

5. Perkenalkan diri ke git. Nama dan email ini tercatat pada commit dan **terlihat publik**, jadi pakai nama dan alamat prodi:

```
git config --global user.name "Prodi X"
git config --global user.email "prodi.x.dashboard@gmail.com"
```

Kalau Miniforge Prompt ditutup, saat membukanya lagi jalankan `conda activate pasang-situs`, lalu masuk ke folder repo dengan `cd`.

## Tahap 3. Buat repo dari templat

### Memilih nama repo

Nama repo menjadi bagian alamat situs: `https://<org>.github.io/<repo>/`.

- Nama bawaan dan yang disarankan: `cv-site`.
- Nama lain boleh, misalnya `kinerja`. Pakai **huruf kecil**, angka, tanda minus, titik, atau garis bawah, tanpa spasi.
- Kalau repo dinamai persis `<org>.github.io`, situs tayang di akar alamat: `https://<org>.github.io/`. Satu akun hanya bisa punya satu repo seperti ini.
- Tetapkan sekarang. Mengganti nama belakangan berarti mengubah alamat situs dan pengaturan Supabase (lihat "Mengganti nama repo" di bagian Setelah terpasang).

### Membuat repo

1. Masuk ke GitHub dengan akun prodi (tahap 1b), lalu buka alamat repo templat dari pengelola templat.
2. Klik **Use this template › Create a new repository**.
3. Pada *Owner*, pilih organisasi prodi (atau akun GitHub prodi bila tanpa organisasi), isi *Repository name* dengan `<repo>`, pilih **Public**, lalu klik **Create repository**.
4. Di repo baru, buka **Settings › Pages**. Pada *Source*, pilih **GitHub Actions**.

Alamat situs Anda nantinya: `<alamat-situs>/`. Catat di lembar catatan di akhir panduan.

5. Di Miniforge Prompt, salin repo ke komputer:

```
cd %USERPROFILE%\Documents
git clone https://github.com/<org>/<repo>.git
cd <repo>
```

## Tahap 3b (pilihan). Coba situs di komputer sendiri

Tahap ini boleh dilewati. Gunanya melihat dan mencoba seluruh situs **sebelum** membuat Supabase, email, dan Google Drive, misalnya untuk ditunjukkan ke kaprodi atau untuk memilih paket lengkap atau akreditasi. Situs coba berisi data fiktif "Teknik Contoh" (13 dosen, karya 2023–2026, data LKPS, BKD, rapat, kalender). Tidak ada yang dikirim ke internet: login, isian, verifikasi, dan unggah bukti ditiru di peramban, dan perubahan hanya tersimpan di peramban komputer ini.

**1. Pasang pustaka yang dibutuhkan (sekali saja).** Di Miniforge Prompt yang sudah aktif `(pasang-situs)`:

```
conda install -y pandas requests openpyxl pyyaml
```

Tunggu sampai muncul `done`. Pustaka ini sama dengan yang dipakai GitHub saat membangun situs.

**2. Jalankan situs coba.** Masih di folder `<repo>`:

```
python coba_lokal.py
```

Yang tampil, kira-kira:

```
Folder repo : C:\Users\...\Documents\<repo>
Port        : 8790 (config.yaml coba_lokal.port)
Paket       : sesuai site/config.js
Membangun data.json dengan bangun.py ...

Situs coba berjalan di http://localhost:8790/ruang-kerja.html
Bilah MODE COBA di bawah halaman: ganti peran (Admin, Dosen, Tamu) dan Atur ulang data.
Tekan Ctrl+C di jendela ini untuk berhenti.
```

Peramban terbuka sendiri di alamat itu. Kalau tidak, salin alamatnya ke peramban. **Jangan tutup jendela Miniforge Prompt** selama mencoba; situs berhenti bila jendela ditutup.

**3. Coba sebagai admin, dosen, dan tamu.** Di bagian bawah setiap halaman ruang kerja ada bilah cokelat **MODE COBA**:

| Tombol | Yang terjadi |
|---|---|
| **Admin** | masuk sebagai Admin Contoh: semua menu, termasuk Verifikasi, Data prodi, Skor & LED, Jejak perubahan |
| **Dosen (Adi)** | masuk sebagai Adi Contoh: Profil saya, Karya dosen, Tugas saya (ada tindak lanjut rapat dan temuan AMI yang menunggu) |
| **Tamu** | keluar; halaman ruang kerja menampilkan layar masuk, halaman umum (Beranda, Dosen) tetap terbuka |
| **Atur ulang data** | semua isian Anda dibuang dan data kembali ke contoh awal |

Hal yang patut dicoba: isi satu karya sebagai Adi, lalu verifikasi sebagai Admin; buka **Akreditasi › Skor & LED** dan unduh draf LED atau tabel LKPS (berkas Word/Excel dibuat dari data contoh); buka **Beranda umum** untuk melihat tampilan publik.

**4. Berhenti.** Kembali ke Miniforge Prompt, tekan **Ctrl+C**. Muncul `Berhenti.` Folder `coba-lokal` yang dibuat di dalam `<repo>` boleh dibiarkan; folder itu diabaikan git dan tidak pernah ikut ter-push.

**Mencoba paket akreditasi.** Jalankan:

```
python coba_lokal.py --paket akreditasi
```

Menu tanpa rapat, hibah, kalender, pengingat, Kepakaran, dan Rekap SDGs akan tampil. Pilihan ini hanya untuk percobaan; paket situs sungguhan dipilih di tahap 6.

**Kalau ada masalah:**

| Pesan atau gejala | Penyebab | Yang dilakukan |
|---|---|---|
| `No module named 'pandas'` (atau `yaml`, `requests`, `openpyxl`) | langkah 1 belum dikerjakan, atau `(pasang-situs)` belum aktif | `conda activate pasang-situs`, lalu ulangi langkah 1 |
| `Port 8790 sedang dipakai program lain` | situs coba lain masih berjalan, atau program lain memakai port itu | tutup jendela situs coba yang lama, atau jalankan `python coba_lokal.py --port 8791` |
| `supabase/instal-lengkap.sql tidak ada` | perintah dijalankan di luar folder `<repo>` | `cd` ke folder `<repo>` lalu ulangi |
| `bangun.py gagal` | lihat pesan di atasnya | kirim seluruh pesan ke pengelola templat |
| halaman kosong atau "gagal dimuat" | peramban memakai berkas lama | tekan **Ctrl+Shift+R** |
| data yang diisi tadi hilang | **Atur ulang data** ditekan, atau situs coba dijalankan ulang (data contoh dibuat baru) | memang begitu; situs coba tidak menyimpan data sungguhan |

Situs coba tidak memerlukan dan tidak menyentuh Supabase, GitHub, atau Google Drive. Setelah selesai mencoba, lanjutkan ke tahap 4.

## Tahap 4. Buat database dan ambil kunci

### Membuat proyek

1. Buka `supabase.com`, klik **Sign in**, lalu masuk dengan akun Supabase prodi (tahap 1d).
2. Kalau baru pertama, Supabase meminta membuat organisasi. Beri nama prodi dan pilih paket **Free**.
3. Klik **New project** dan isi:
    - *Name*: nama yang mudah dikenali, misalnya `dashboard-prodi`.
    - *Database Password*: klik **Generate a password**, lalu simpan di pengelola kata sandi prodi. Situs tidak memakai kata sandi ini, tetapi Supabase memintanya untuk keperluan pemulihan.
    - *Region*: pilih yang terdekat, misalnya Singapura.
    - Kotak **Grant API access to new tables automatically** (di bagian keamanan formulir, sejak akhir 2026 tidak
      dicentang secara bawaan): **centang**. `instal-lengkap.sql` sudah menulis sendiri hak akses semua tabelnya,
      tetapi patch pembaruan berikutnya yang menambah tabel bergantung pada kotak ini; tanpa centang, tabel baru
      itu tidak bisa dibaca situs. Keamanan data tetap dijaga aturan baris (RLS) tiap tabel.
4. Klik **Create new project** dan tunggu beberapa menit sampai proyek siap.

### Membuat tabel

1. Di menu kiri, buka **SQL Editor**, lalu **New query**.
2. Buka berkas `supabase\instal-lengkap.sql` dari folder repo dengan Notepad. Tekan Ctrl+A, lalu Ctrl+C.
3. Tempel di SQL Editor, lalu klik **Run**.
4. Pastikan hasilnya *Success* tanpa pesan galat berwarna merah. Kalau muncul galat `already exists`, berkas ini sudah pernah dijalankan; jangan diulang.

### Mengatur login

1. Buka **Authentication › Sign In / Providers** dan pastikan **Email** aktif.
2. Buka **Authentication › URL Configuration** dan isi:
    - *Site URL*: `<alamat-situs>/`
    - *Redirect URLs*: klik **Add URL**, isi `<alamat-situs>/**`, lalu simpan.

    Contoh dengan repo `cv-site`: Site URL `https://prodi-contoh.github.io/cv-site/`, Redirect URL `https://prodi-contoh.github.io/cv-site/**`. Di tahap 6, `install.py` mencetak kedua alamat ini; cocokkan.

    Tanpa langkah ini, tautan di email login tidak membuka situs.

### Mengambil Project URL dan kunci

1. **Project URL.** Klik tombol **Connect** di bagian atas halaman proyek. URL berbentuk `https://<kode>.supabase.co`. `<kode>` sama dengan bagian alamat browser setelah `supabase.com/dashboard/project/`.
2. **Publishable key.** Buka **Project Settings › API Keys**. Salin nilai pada baris *Publishable key*, yang diawali `sb_publishable_`.
3. **Secret key.** Di halaman yang sama, bagian *Secret keys*, tampilkan dan salin kuncinya, yang diawali `sb_secret_`. Langsung simpan di pengelola kata sandi sampai tahap 8.

Kalau halaman itu hanya menampilkan kunci lama bernama `anon` dan `service_role` (panjang, diawali `eyJ`), buat publishable key dan secret key baru di halaman yang sama. Kunci lama akan dihentikan Supabase pada akhir 2026, dan `install.py` hanya menerima publishable key yang baru.

| Nilai | Bentuk | Dipakai di |
|---|---|---|
| Project URL | `https://<kode>.supabase.co` | tahap 6 (`install.py`), 7 (Apps Script), 8 (GitHub Secrets) |
| Publishable key | diawali `sb_publishable_` | tahap 6, 7 |
| Secret key | diawali `sb_secret_` | tahap 8 saja |

## Tahap 5. Sambungkan email login (Gmail ke Supabase)

### Apa yang dikerjakan di tahap ini

Dosen masuk situs lewat tautan yang dikirim ke emailnya. Pengirim email itu adalah Supabase. Menurut dokumen Supabase, layanan email bawaannya hanya mengirim ke anggota tim proyek, sekitar 2 email per jam, sehingga dosen tidak akan menerima tautan.

Karena itu Supabase diatur untuk mengirim email **lewat akun Gmail prodi**. Cara mengirim email seperti ini disebut **SMTP**. Tahap ini **tidak membuat akun baru**; yang dipakai adalah Gmail prodi dari tahap 1a.

| Bagian | Dikerjakan di | Hasil |
|---|---|---|
| A | akun Google prodi (`myaccount.google.com`) | Sandi Aplikasi: kode 16 huruf khusus untuk Supabase |
| B | dasbor Supabase, proyek dari tahap 4 | Supabase mengirim email lewat Gmail prodi |
| C | dasbor Supabase | batas jumlah email per jam dinaikkan |

Gmail bisa mengirim sampai sekitar 500 email per hari, cukup untuk login seluruh dosen.

### A. Buat Sandi Aplikasi di akun Google prodi

Sandi Aplikasi adalah kata sandi khusus yang memberi izin kepada satu aplikasi, di sini Supabase, untuk mengirim email dari Gmail prodi. Sandi ini **bukan** kata sandi Gmail.

1. Masuk ke Gmail prodi di browser.
2. Pastikan **Verifikasi 2 Langkah** sudah aktif (tahap 1a langkah 6): `myaccount.google.com` › **Keamanan** › **Verifikasi 2 Langkah**.
3. Buka `myaccount.google.com/apppasswords`. Google mungkin meminta kata sandi Gmail sekali lagi.
4. Pada kotak nama aplikasi (**App name** bila tampilan berbahasa Inggris), ketik misalnya `Supabase situs prodi`, lalu klik **Buat** (**Create**).
5. Google menampilkan kode 16 huruf, biasanya dalam empat kelompok berspasi. **Kode ini hanya tampil sekali.** Salin, lalu langsung kerjakan bagian B; tempel tanpa spasi. Boleh disimpan di pengelola kata sandi prodi.

Bila halaman Sandi Aplikasi tidak tersedia, menurut bantuan Google penyebabnya salah satu dari ini: Verifikasi 2 Langkah belum aktif atau hanya memakai kunci keamanan; akun yang dipakai akun kerja atau sekolah; atau akun memakai Perlindungan Lanjutan.

### B. Isi pengaturan SMTP di Supabase

1. Buka `supabase.com/dashboard` dan pilih proyek dari tahap 4.
2. Di menu kiri, buka **Authentication**, lalu **Emails** (bagian *NOTIFICATIONS*). Halaman ini punya dua tab, **Templates** dan **SMTP Settings**: klik **SMTP Settings**, atau tombol **Set up SMTP** di tab Templates. Alamat langsungnya `https://supabase.com/dashboard/project/<kode>/auth/smtp`.
3. Nyalakan sakelar **Enable custom SMTP**, lalu isi:

| Isian | Nilai | Keterangan |
|---|---|---|
| Sender email address | alamat Gmail prodi | alamat pengirim yang dilihat dosen |
| Sender name | misalnya `Kinerja Teknik Lingkungan` | nama pengirim yang dilihat dosen |
| Host | `smtp.gmail.com` | server pengirim Gmail |
| Port number | `587` | ganti angka bawaan 465; Gmail menerima keduanya |
| Username | alamat Gmail prodi lengkap | sama dengan Sender email address |
| Password | Sandi Aplikasi dari bagian A | **bukan** kata sandi Gmail |

4. Klik **Save changes**. Catatan di bawah formulir menyebut batas email naik menjadi 30 per jam; naikkan lagi di bagian C.

Setelah Host diisi `smtp.gmail.com`, Supabase menampilkan peringatan kuning **Check your SMTP provider**: Gmail dibuat untuk email pribadi, bukan email otomatis, sehingga sebagian email bisa masuk Spam. Ini peringatan, bukan galat; simpan saja. Untuk satu prodi Gmail biasanya cukup. Kalau banyak dosen tidak menerima tautan, ganti dengan penyedia email transaksional, misalnya Resend, dengan isian di halaman yang sama.

### C. Naikkan batas kirim email

Menurut dokumen Supabase, setelah SMTP sendiri dipasang, batas kirim awalnya 30 email per jam untuk seluruh situs.

1. Di menu **Authentication**, bagian *CONFIGURATION*, buka **Rate Limits**.
2. Naikkan batas email per jam sesuai jumlah dosen. Contoh: prodi dengan 40 dosen yang sering masuk bersamaan bisa memakai 100.
3. Simpan.

### D. Isi email berbahasa Indonesia (disarankan)

Setelah SMTP sendiri terpasang, isi email bisa diubah. Tanpa langkah ini dosen menerima email bawaan berbahasa Inggris.

1. Buka **Authentication › Emails**, tab **Templates**.
2. Klik **Magic link or OTP**. Templat ini dipakai setiap kali dosen meminta tautan masuk.
3. Ganti isi **Subject** dan **Body** (tab **Source**) dengan contoh di bawah, lalu klik **Save changes**. Tab **Preview** menampilkan hasilnya; di pratinjau, `{{ .Email }}` tampil apa adanya dan baru diganti alamat dosen di email sungguhan.
4. Ulangi untuk **Confirm sign up**, yang mungkin dikirim saat dosen pertama kali masuk.
5. Tunggu sekitar 10 menit, lalu minta tautan masuk untuk diri sendiri. Templat yang baru disimpan perlu beberapa menit sebelum dipakai; email yang datang sebelum itu masih berisi teks lama.

Templat lain (**Invite user**, **Change email address**, **Reset password**, **Reauthentication**) tidak dipakai situs ini; biarkan. Jangan klik **Reset template**, karena isinya kembali ke bawaan.

Tautan masuk harus tetap memakai `{{ .ConfirmationURL }}`. Jangan menggantinya dengan kode `{{ .Token }}`: situs tidak punya kotak isian kode.

**Magic link or OTP**

Subject:

```
Tautan masuk Dashboard Teknik Lingkungan
```

Body:

```
<h2>Masuk ke Dashboard Teknik Lingkungan</h2>
<p>Yth. Bapak/Ibu,</p>
<p>Seseorang meminta tautan masuk untuk alamat {{ .Email }}. Klik tombol di bawah untuk masuk:</p>
<p><a href="{{ .ConfirmationURL }}" style="display:inline-block;padding:10px 18px;background:#0C2A4D;color:#ffffff;text-decoration:none;border-radius:4px">Masuk ke situs</a></p>
<p>Tautan ini hanya bisa dipakai sekali dan berlaku untuk waktu terbatas. Bila tautan sudah kedaluwarsa, minta tautan baru dari halaman masuk.</p>
<p>Bila Anda tidak meminta tautan ini, abaikan email ini.</p>
<p>Program Studi Teknik Lingkungan, Universitas Contoh</p>
```

**Confirm sign up**

Subject:

```
Konfirmasi dan masuk ke Dashboard Teknik Lingkungan
```

Body:

```
<h2>Selamat datang di Dashboard Teknik Lingkungan</h2>
<p>Yth. Bapak/Ibu,</p>
<p>Alamat {{ .Email }} baru pertama kali masuk ke situs. Klik tombol di bawah untuk mengonfirmasi alamat ini sekaligus masuk:</p>
<p><a href="{{ .ConfirmationURL }}" style="display:inline-block;padding:10px 18px;background:#0C2A4D;color:#ffffff;text-decoration:none;border-radius:4px">Konfirmasi dan masuk</a></p>
<p>Tautan ini hanya bisa dipakai sekali. Bila Anda tidak meminta tautan ini, abaikan email ini.</p>
<p>Program Studi Teknik Lingkungan, Universitas Contoh</p>
```

Ganti nama situs, nama prodi, dan warna tombol (`#0C2A4D`, warna utama dari tahap 6) sesuai prodi Anda.

Menurut dokumen Supabase, sebagian layanan email kantor (misalnya Microsoft Defender Safe Links) membuka tautan di email lebih dulu untuk memeriksanya, sehingga tautan sekali pakai bisa sudah terpakai saat dosen mengkliknya, dengan pesan "Token has expired or is invalid". Bila banyak dosen mengalaminya, laporkan ke pengelola templat.

### Diuji kapan

Pengiriman email baru bisa diuji setelah situs terbit, di tahap 10 nomor 1 dan 2. Bila tautan tidak sampai, periksa folder Spam, lalu periksa kembali isian bagian B.

Kalau kata sandi Gmail prodi diganti, Google otomatis mencabut Sandi Aplikasi dan email login berhenti. Ulangi bagian A, lalu tempel kode baru di bagian B.

## Tahap 6. Jalankan pemasang

Di Miniforge Prompt, di folder `<repo>`:

```
python install.py
```

Jawab pertanyaan berikut. Di atas beberapa pertanyaan, pemasang menulis petunjuk dalam tanda kurung tentang tempat mencari nilainya. Tekan Enter untuk memakai nilai dalam kurung siku.

| Pertanyaan | Contoh | Asal nilai |
|---|---|---|
| Nama program studi, tanpa kata "Program Studi" | `Teknik Lingkungan` | |
| Nama institusi | `Universitas Contoh` | |
| Nama organisasi atau akun GitHub | `prodi-contoh` | tahap 1 |
| Nama repo situs | Enter untuk `cv-site`, atau nama pilihan Anda | tahap 3 |
| Supabase Project URL | `https://abcdefghijklmnopqrst.supabase.co` | tahap 4, tombol Connect |
| Supabase publishable key | `sb_publishable_...` | tahap 4, API Keys |
| URL Web App Apps Script | kosongkan dulu, tekan Enter | diisi di tahap 7 |
| Email admin pertama | email orang yang menjadi admin, sebaiknya email kampusnya | lihat "Email prodi dan email admin" di bawah |
| NIDN admin pertama | staf tanpa NIDN: nomor pegawai | |
| Nama lengkap admin pertama | | |
| Berkas logo `.png` | path berkas, atau kosongkan | |
| Warna utama dan warna aksen | `#0C2A4D`, atau Enter | |
| Paket situs | `lengkap` (Enter) atau `akreditasi` | lihat "Paket lengkap atau akreditasi" di bawah |
| Instrumen akreditasi | `lam-teknik-s1` (Enter) atau `lamdepilar-magister` | lihat "Instrumen akreditasi" di bawah |

### Instrumen akreditasi

Instrumen menentukan butir skor, bobot, syarat status, serta templat LKPS dan LED yang diunduh dari halaman Skor & LED. Pilih sesuai LAM dan jenjang prodi; daftar lengkap dicetak pemasang di atas pertanyaannya.

| Id | Instrumen |
|---|---|
| `lam-teknik-s1` | LAM Teknik, APS-AV 2025 1.0, Program Sarjana (60 butir, skor 0–4, NA maksimal 400) |
| `lamdepilar-magister` | LAMDEPILAR, IAPS DEPILAR 1.0, Magister program akademik, perolehan status terakreditasi (30 elemen, skor 0–3 diisi manual, NA maksimal 300) |

Pemasang menulis pilihan ke `config.yaml` (`accreditation.instrument`), lalu menjalankan `tools/pilih_instrumen.py` yang mengarahkan halaman ke folder `site/instrumen/<id>/`. Langkah ini butuh Node.js dari tahap 2. Kalau muncul "node tidak ditemukan", jalankan `conda install nodejs -y` di lingkungan `pasang-situs`, lalu ulangi `python install.py`. Berganti instrumen kelak juga lewat `python install.py`, lalu commit dan push. Data yang sudah diisi tetap ada, tetapi skor dan bukti per butir milik instrumen lama tidak tampil di instrumen baru.

### Paket lengkap atau akreditasi

Keduanya memakai kode dan database yang sama; bedanya hanya modul yang tampil.

| Paket | Isi |
|---|---|
| `lengkap` | semua modul dan situs publik (beranda, daftar dosen, kurikulum, kinerja, dan halaman umum lain) |
| `akreditasi` | **hanya ruang kerja**, tanpa situs publik. Isinya: Skor & LED, LKPS, narasi dan kelengkapan LED, isian butir dan dokumen, Siklus PPEPP, survei kepuasan, mutu data, grafik, Monitoring, Dasbor; Data prodi (semua tabel LKPS), verifikasi, kelola dosen, penugasan koordinator, jejak perubahan; profil, karya, BKD, dan target kinerja dosen; kurikulum dan CPL, CPMK, RPS, silabus, tinjauan RPS, portofolio, evaluasi pembelajaran, PJP, ekuivalensi, penyusunan kelas, berkas nilai CPL; panel Tugas saya. Tanpa layanan dan pengajuan mahasiswa (KP, TA, lomba, surat), jadwal kuliah dan jadwal berhalangan, rapat, kalender, kabar kegiatan, hibah, kepakaran, SDGs, pengingat email, serta kelola profil prodi dan laboratorium. |

Pada paket akreditasi, alamat situs langsung membuka halaman masuk ruang kerja, dan mesin pencari diminta tidak mengindeks situs. Tiga halaman tanpa login tetap hidup karena dibutuhkan akreditasi: kuesioner kepuasan (`survei.html`), berkas privat untuk asesor (`lkd.html`), dan pemeriksaan QR RPS (`verifikasi-rps.html`).

Data SDGs dan topik keahlian tetap diisi dosen di paket akreditasi, karena dipakai capaian IKU dan tabel dosen di LED; yang dimatikan hanya halaman rekapnya. Untuk berganti paket kelak, jalankan `python install.py` lagi dan pilih paket lain, lalu commit dan push. Tidak ada data yang hilang.

### Email prodi dan email admin

Keduanya berbeda, walaupun boleh sama:

- **Email prodi** (`prodi.x.dashboard@gmail.com`, tahap 1a) adalah pemilik layanan: dipakai mendaftar GitHub dan Supabase, menyimpan Google Drive dan Apps Script, dan menjadi **pengirim** email login (tahap 5). Email ini tidak perlu masuk ke situs.
- **Email admin** adalah alamat **orang** yang masuk ke situs sebagai admin, untuk Kelola dosen, Verifikasi, dan Data prodi. Pemasang memintanya bersama NIDN dan nama lengkap, lalu mencetak SQL yang mencatat orang itu di tabel dosen dengan peran admin.

Sebaiknya admin memakai email kampusnya sendiri, bukan email prodi. Kalau email prodi dijadikan admin, siapa pun yang tahu kata sandinya bisa masuk sebagai admin, dan tidak tercatat siapa yang memverifikasi atau mengubah data. Admin berikutnya cukup ditambahkan dari halaman **Kelola dosen** dengan peran admin; tidak perlu SQL lagi. Saat serah terima, tambahkan admin baru di Kelola dosen dan serahkan email prodi.

Kalau jawaban tidak sah, pemasang menjelaskan sebabnya dan bertanya lagi. Misalnya, kalau yang ditempel secret key, pemasang menolak.

Di akhir, layar menampilkan:

1. **Alamat situs, Site URL, dan Redirect URLs.** Cocokkan dengan isian di tahap 4 "Mengatur login". Kalau berbeda, perbaiki di Supabase.
2. **SQL admin pertama.** Salin, tempel di **SQL Editor** Supabase, lalu **Run**.
3. **Token cadangan.** Salin dan simpan sementara di pengelola kata sandi untuk tahap 7 dan 8.

SQL admin dan token **tidak disimpan di berkas mana pun**, jadi kerjakan sekarang.

## Tahap 7. Pasang unggah bukti, cadangan, dan kata sandi berkas privat

Kerjakan dengan akun Gmail prodi.

### Buat dua folder di Google Drive

1. Buka `drive.google.com`, klik **Baru › Folder**, beri nama `data-lkps`. Ini folder bukti.
2. Kembali ke **Drive Saya**, buat folder kedua bernama `cadangan-situs`. Ini folder cadangan.
3. Buka tiap folder dan lihat alamat browser. ID folder adalah bagian setelah `/folders/`. Contoh: pada `https://drive.google.com/drive/folders/1AbC...xyz`, ID-nya `1AbC...xyz`.

| Folder | Contoh nama | Dibagikan? |
|---|---|---|
| Folder bukti | `data-lkps` | tidak; skrip membagikan berkasnya sendiri |
| Folder cadangan | `cadangan-situs` | **jangan pernah**; isinya data pribadi dosen |

Keduanya harus terpisah. Folder cadangan **tidak boleh** berada di dalam folder bukti.

### Pasang Apps Script

1. Buka `script.google.com`, klik **New project**. Klik judul *Untitled project* di kiri atas, lalu beri nama `situs-upload`.
2. Hapus seluruh isi `Code.gs` di editor. Buka `apps-script\Code.gs` dari folder repo dengan Notepad, salin seluruh isinya, tempel, lalu simpan (Ctrl+S).
3. Buka **Project Settings** (ikon roda gigi di menu kiri). Pada *Time zone*, pilih `(GMT+07:00) Jakarta`, atau zona waktu kampus Anda.
4. Masih di halaman itu, gulir ke **Script Properties**, klik **Add script property** untuk tiap baris berikut, lalu **Save script properties**:

| Property | Nilai | Keterangan |
|---|---|---|
| `FOLDER_ID` | ID folder bukti | wajib |
| `SUPABASE_URL` | Project URL | wajib; sama dengan tahap 4 |
| `SUPABASE_KEY` | publishable key | wajib; **bukan** secret key, skrip menolak secret key |
| `MAX_MB` | `20` | wajib; batas ukuran satu berkas, bilangan bulat 1 sampai 40 |
| `ALLOWED_EXT` | `pdf,jpg,jpeg,png,docx,xlsx` | wajib; huruf kecil, dipisah koma |
| `CADANGAN_FOLDER_ID` | ID folder cadangan | untuk cadangan otomatis |
| `CADANGAN_TOKEN` | token cadangan dari tahap 6 | untuk cadangan otomatis; sama persis dengan GitHub Secrets |

5. Klik **Deploy › New deployment**. Di sebelah *Select type*, klik ikon roda gigi lalu pilih **Web app**, dan isi:
    - Description: `situs upload`
    - Execute as: **Me**
    - Who has access: **Anyone**
6. Klik **Deploy**, lalu **Authorize access**, dan pilih akun prodi. Kalau muncul "Google hasn't verified this app", klik **Advanced › Go to situs-upload (unsafe) › Allow**. Ini wajar untuk skrip milik sendiri.
7. Salin **Web app URL**, yang berakhiran `/exec`. Catat di lembar catatan.
8. Uji: buka URL itu di jendela Incognito. Harus tampil `{"ok":true,"folder":"data-lkps",...}`. Kalau `ok:false`, pesannya menyebut isian yang kurang atau salah.

"Who has access: Anyone" diperlukan supaya situs bisa mengirim berkas. Skrip tetap memeriksa login dosen ke Supabase sebelum menerima berkas.

### Kata sandi berkas privat (`LKD_SANDI`)

Berkas privat, seperti laporan kinerja dosen dan notulen, tidak punya tautan publik. Admin dan dosen pemilik berkas membukanya setelah login. Asesor, yang tidak punya akun, membukanya dengan satu kata sandi. Langkah ini boleh dilewati sekarang dan dikerjakan menjelang visitasi.

**Membuat kata sandi.** Minimal 8 karakter; disarankan 12 karakter acak atau lebih, dan bukan kata sandi lain yang sudah dipakai. Cara membuat yang acak, di Miniforge Prompt:

```
python -c "import secrets; print(secrets.token_urlsafe(9))"
```

Hasilnya 12 karakter acak, berbeda tiap kali dijalankan.

**Memasang:**

1. Di Apps Script, **Project Settings › Script Properties**, klik **Add script property**.
2. *Property*: `LKD_SANDI`. *Value*: kata sandi tadi. Klik **Save script properties**.
3. Tidak perlu deploy ulang; nilai baru langsung berlaku.

**Memakai:**

1. Saat mengunduh indeks bukti LKPS dari situs, ketik kata sandi yang sama. Kata sandi ditulis di bawah tautan berkas privat untuk asesor, dan tidak disimpan di situs.
2. Asesor membuka tautan berkas privat dan memasukkan kata sandi itu.

**Setelah visitasi:** kosongkan atau hapus `LKD_SANDI` di Script Properties. Untuk visitasi berikutnya, buat kata sandi baru.

Selama `LKD_SANDI` kosong atau kurang dari 8 karakter, akses dengan kata sandi tertutup. Satu kata sandi berlaku untuk semua berkas privat. Setelah 20 kali salah, akses ditutup selama 1 jam. Jangan menulis kata sandi ini di repo, di config, atau di lembar catatan.

### Hitung CPL otomatis (`CPL_KUNCI`, `GITHUB_REPO`, `GITHUB_DISPATCH_TOKEN`)

Tiap malam (01:30 WIB) alur kerja **Hitung CPL** di GitHub mengunduh berkas nilai CPL yang diunggah dosen, menghitung capaian CPL, lalu menyimpan ringkasannya ke database. Langkah ini boleh dikerjakan nanti, sebelum berkas nilai CPL pertama diunggah.

**Kunci CPL (wajib untuk hitungan malam):**

1. Buat kunci acak di Miniforge Prompt:
   ```
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
2. Apps Script › **Project Settings › Script Properties** › **Add script property**: *Property* `CPL_KUNCI`, *Value* kunci tadi. Klik **Save script properties**.
3. Kunci yang sama diisi lagi sebagai GitHub Secret `CPL_KUNCI` di tahap 8. Simpan sementara di catatan, hapus setelah tahap 8.

**Tombol "Hitung CPL sekarang" dan terbit segera setelah data berubah (pilihan):**

Tanpa langkah ini, CPL tetap dihitung tiap malam dan situs tetap diperbarui tiap jam. Yang tidak aktif hanya tombol hitung sekarang dan pembaruan segera.

1. Di GitHub, dengan akun prodi: foto profil › **Settings › Developer settings › Personal access tokens › Fine-grained tokens › Generate new token**.
2. Isi *Token name* `situs-pemicu`. *Resource owner*: organisasi prodi (atau akun prodi bila repo tidak di organisasi). *Expiration*: pilih yang paling lama tersedia, lalu catat tanggal berakhirnya untuk diperbarui.
3. *Repository access*: **Only select repositories**, pilih repo situs. *Permissions › Repository permissions › Actions*: **Read and write**. Klik **Generate token**, lalu salin tokennya (hanya tampil sekali). Bila organisasi mewajibkan persetujuan token, setujui di **Settings organisasi › Personal access tokens › Pending requests**.
4. Apps Script › **Script Properties**, tambahkan:

| Property | Nilai |
|---|---|
| `GITHUB_REPO` | `<organisasi>/<repo>`, mis. `prodi-contoh/cv-site` |
| `GITHUB_DISPATCH_TOKEN` | token dari langkah 3 |

Tidak perlu deploy ulang; Script Properties langsung berlaku. Token tidak pernah dikirim ke peramban; hanya admin atau GKM yang login yang bisa memicu hitung CPL.

### Masukkan URL Web App ke situs

Jalankan pemasang sekali lagi:

```
python install.py
```

Tekan Enter pada semua pertanyaan, kecuali **URL Web App**: tempel URL dari langkah 7. Layar akan menampilkan SQL admin dan token baru lagi. **Abaikan keduanya**, karena yang lama sudah terpasang.

## Tahap 8. Isi pengaturan GitHub

Di repo, buka **Settings › Secrets and variables › Actions**.

Tab **Secrets**, klik **New repository secret** untuk tiap baris. *Name* ditulis persis seperti di tabel:

| Nama | Isi |
|---|---|
| `SUPABASE_URL` | Project URL |
| `SUPABASE_SERVICE_KEY` | secret key Supabase (`sb_secret_...`) |
| `CADANGAN_TOKEN` | token cadangan yang sama dengan tahap 7 |
| `CPL_KUNCI` | kunci CPL yang sama dengan tahap 7 (hitung CPL tiap malam) |

Setelah disimpan, GitHub tidak menampilkan isinya lagi. Untuk mengganti, klik ikon pensil dan tempel nilai baru. Setelah tahap ini selesai, hapus secret key dan token dari catatan sementara Anda.

Tab **Variables**, klik **New repository variable**:

| Nama | Isi | Contoh |
|---|---|---|
| `NAMA_PRODI` | nama prodi, tanpa kata "Program Studi" | `Teknik Lingkungan` |
| `NAMA_INSTITUSI` | nama perguruan tinggi | `Universitas Contoh` |

Workflow tidak berjalan sebelum `NAMA_PRODI` terisi.

## Tahap 9. Terbitkan situs

Di Miniforge Prompt, di folder `<repo>`:

```
git add -A
git commit -m "Pasang situs"
git push
```

Saat push pertama, jendela login GitHub bisa muncul. Pilih masuk lewat browser.

Lalu buka tab **Actions** di repo, dan tunggu **Bangun situs** berwarna hijau. Kalau tidak berjalan sendiri, klik **Bangun situs › Run workflow**.

Buka `<alamat-situs>/`.

## Tahap 10. Periksa hasilnya

| No | Yang dicoba | Hasil yang benar |
|---|---|---|
| 1 | Masuk memakai email admin | tautan sampai ke email, ruang kerja terbuka |
| 2 | Tambah satu dosen di Kelola dosen, lalu minta dosen itu masuk | tautan sampai; periksa juga folder Spam |
| 3 | Unggah satu berkas bukti dari situs | berkas muncul di folder bukti Drive |
| 4 | **Actions › Pemeliharaan basis data › Run workflow**, pilih `cadangkan` | workflow hijau, ada zip baru di folder cadangan Drive |
| 5 | Bila `LKD_SANDI` sudah dipasang: buka satu berkas privat di jendela Incognito dengan kata sandinya | isi berkas terbuka |

Kalau nomor 1 sampai 4 berhasil, pemasangan selesai.

## Tahap 11. Isi data awal

1. **Kelola dosen:** semua dosen, peran, status aktif, DTPS, pendidikan, jabatan.
2. Buka **Akreditasi › Kelengkapan LED**. Halaman ini menghitung yang belum terisi dan menautkan ke tempat mengisinya.
3. Bila perlu, isi kata kunci visi keilmuan dengan contoh di `supabase\contoh-kata-visi.sql`.

Panduan untuk pengguna ada di situs, menu **Bantuan**.

## Setelah terpasang

| Yang berjalan otomatis | Kapan |
|---|---|
| Situs dibangun ulang dari data terbaru | tiap jam, menit ke-23 |
| Database dipanggil supaya Supabase tidak berhenti | tiap 3 hari |
| Hitung capaian CPL dari berkas nilai | tiap malam, 01:30 WIB |
| Cadangan seluruh tabel ke Drive | tiap malam, 01:40 WIB; cadangan lebih dari 35 hari dipindah ke Sampah Drive, kecuali cadangan tanggal 1 tiap bulan (disimpan). Tanggal 1, GitHub juga mencatat tanda aktif |
| Arsip tahunan ke Drive | 1 September |

**Memperbarui situs saat itu juga:** buka **Actions › Bangun situs › Run workflow**.

**Mengganti logo atau warna:** jalankan `python install.py` lagi, lalu `git add -A`, `git commit -m "Ganti logo"`, dan `git push`. Di komputer lain, jawaban lama tidak tersimpan, jadi semua pertanyaan harus diisi ulang.

**Mengganti `Code.gs`:** tempel ulang kodenya, simpan, lalu **Deploy › Manage deployments**, ikon pensil, *Version* **New version**, **Deploy**. Alamatnya tetap sama. Jangan melakukan *archive* pada deployment yang aktif, karena alamatnya langsung mati.

**Mengganti nama repo:**

1. Di GitHub, **Settings › General**, ubah *Repository name*.
2. Jalankan `python install.py`, isi nama repo yang baru, lalu commit dan push.
3. Di Supabase, **Authentication › URL Configuration**: ganti *Site URL* dan *Redirect URLs* dengan alamat yang dicetak pemasang.
4. Beri tahu dosen alamat situs yang baru.

**Kalau secret key Supabase atau token cadangan bocor:**
- Secret key: di **Project Settings › API Keys**, buat secret key baru, pasang di GitHub Secrets `SUPABASE_SERVICE_KEY`, lalu hapus kunci yang lama.
- Token: jalankan `python install.py` untuk mendapat token baru, lalu pasang di Script Properties dan GitHub Secrets `CADANGAN_TOKEN`.

**Serah terima pengelola:** serahkan akun Gmail prodi, akses admin ke organisasi GitHub serta proyek Supabase, dan isi pengelola kata sandi prodi.

## Bila ada masalah

| Gejala | Penyebab | Yang dilakukan |
|---|---|---|
| Actions merah: `site/config.js belum diisi` | `install.py` belum dijalankan atau belum di-push | jalankan tahap 6, lalu tahap 9 |
| **Bangun situs** tidak berjalan sama sekali | Variable `NAMA_PRODI` kosong | isi di tahap 8, lalu **Run workflow** |
| Langkah terbit (`deploy`) gagal | *Source* Pages belum **GitHub Actions** | ulangi tahap 3 langkah 4, lalu **Run workflow** |
| Langkah `Bangun data.json` gagal | Secret Supabase salah, atau `instal-lengkap.sql` belum berhasil | periksa tahap 8 dan tahap 4 |
| SQL Editor: `already exists` | `instal-lengkap.sql` sudah pernah dijalankan | tidak perlu diulang; data tidak berubah |
| `install.py`: "publishable key diawali sb_publishable_" | yang ditempel kunci lama `anon` (`eyJ...`) | buat publishable key baru, lihat tahap 4 |
| Tautan login tidak sampai | SMTP belum terpasang, Sandi Aplikasi batal, atau batas email per jam habis | ulangi tahap 5 bagian A dan B; periksa batas di bagian C dan folder Spam |
| Tautan login membuka halaman salah atau galat | *Site URL* atau *Redirect URLs* tidak sama dengan alamat situs, misalnya nama repo berbeda | samakan dengan alamat yang dicetak `install.py` (tahap 4 "Mengatur login") |
| Situs 404 setelah nama repo diganti | alamat lama | buka alamat baru; ikuti "Mengganti nama repo" |
| Login berhasil, tetapi ditolak masuk | email belum ada di tabel dosen | jalankan SQL admin, atau tambahkan di Kelola dosen |
| Unggah bukti: "Failed to fetch" | URL Web App salah, atau deployment di-archive | buka URL di Incognito; pasang ulang URL lewat `install.py` |
| Uji URL Web App: `ok:false` | Script Property kurang atau salah | baca pesannya, lengkapi tahap 7 langkah 4 |
| Cadangan: `window.UPLOAD_URL ... kosong` | URL Web App belum dimasukkan | kerjakan bagian "Masukkan URL Web App ke situs" di tahap 7 |
| Cadangan: `Token cadangan salah` | token di GitHub dan Apps Script berbeda | samakan `CADANGAN_TOKEN` di kedua tempat |
| Cadangan: `Script property ... belum diisi` | dua kunci cadangan belum ada | lengkapi tahap 7 |
| Berkas privat: `Akses dengan kata sandi sedang ditutup` | `LKD_SANDI` kosong atau kurang dari 8 karakter | isi kuncinya, lihat "Kata sandi berkas privat" di tahap 7 |
| Situs berhenti diperbarui | GitHub mematikan jadwal otomatis | **Actions**, pilih workflow, klik **Enable workflow** |
| Situs tidak bisa login setelah libur panjang | proyek Supabase berhenti | buka Supabase, pulihkan proyek, lalu periksa workflow pemeliharaan |

## Lembar catatan

Isi untuk mempermudah pemasangan. **Jangan menulis kata sandi database, secret key, Sandi Aplikasi, token, atau `LKD_SANDI` di sini.**

| Isian | Nilai |
|---|---|
| Username GitHub prodi | |
| Organisasi GitHub (`<org>`) | |
| Nama repo (`<repo>`) | |
| Alamat situs | |
| Akun Gmail prodi | |
| Project URL Supabase | |
| ID folder bukti | |
| ID folder cadangan | |
| URL Web App | |
| Email admin pertama | |
