# Apps Script: unggah berkas bukti

`Code.gs` menerima berkas dari `site/input.html`, memeriksa login dosen ke
Supabase, lalu menyimpannya di Google Drive akun prodi:

```
data-lkps/<tahun>/<nama dosen>/<yyyyMMdd-HHmmss>_<nama berkas>      bukti karya tanpa judul (input.html)
data-lkps/<tahun>/<nama dosen>/<judul karya>/<yyyyMMdd-HHmmss>_<…>  bukti karya ber-judul (`group`), satu atau
                                                                    beberapa berkas; folder judul dibagikan Viewer
data-lkps/butir-manual/butir-NN/<yyyyMMdd-HHmmss>_<nama berkas>     bukti butir (panel bukti di isian butir dan
                                                                    kartu skor, khusus admin; semua 60 butir)
data-lkps/dokumen/<jenis>/<tahun>/[<judul>/]<yyyyMMdd-HHmmss>_<berkas>
                                                                    pustaka dokumen (statuta, kurikulum, SK, …;
data-lkps/dokumen/<jenis>/<tahun>/[<judul>/]_arsip/…                jenis di site/rencana-bukti.js JENIS_DOKUMEN;
                                                                    khusus admin)
data-lkps/dokumen/<tabel lkps_*>/<tahun>/<label baris>/<…>          bukti baris Data prodi (data-prodi.html,
                                                                    khusus admin, mode `tambah`)
```

Semua unggahan berupa berkas satu per satu; situs tidak lagi mengunggah
folder (pemilik 2026-11-03). Tiap berkas menjadi satu catatan bukti di
Supabase: `karya_bukti`, `butir_bukti`, `dokumen`, atau `lkps_bukti`.

Dokumen bernama dicatat di tabel Supabase `dokumen`
(`supabase/instal-lengkap.sql`, unik pada jenis + tahun + judul):

- jenis **tunggal** (statuta, kurikulum, renstra, …): judul kosong; unggah
  dengan tahun yang sama **mengganti** (berkas aktif pindah ke `_arsip`), tahun
  berbeda menjadi versi lain;
- jenis **banyak** (SK, notulen, laporan kegiatan, …): judul/nomor wajib;
  judul dan tahun sama mengganti, selain itu entri baru.

Pustaka mengunggah satu berkas per entri dan tautannya selalu ke berkas itu.
Berkas yang diganti tidak dihapus (pindah ke `_arsip`) dan tautan lamanya
tetap bisa dibuka. Mode `tambah` menyimpan berkas tanpa mengarsipkan yang
lama; kini hanya dipakai bukti baris Data prodi.

Folder `data-lkps` privat. Tiap berkas dibagikan "siapa pun yang punya
link: Viewer" supaya tautan di LKPS/LED bisa dibuka asesor tanpa login
(keputusan pemilik 2026-10-09). Folder `butir-NN` dan folder judul karya juga
dibagikan Viewer, jadi satu tautan folder membuka semua berkas di dalamnya.
Supabase hanya menyimpan tautannya.

Kode masih menerima field `path` (subfolder) dari masa unggah folder; situs
tidak mengirimnya lagi, jadi berkas selalu langsung di folder tujuan.

Menghapus (kind `hapus`, pemilik 2026-11-03): admin yang menghapus bukti di
situs (bukti karya, pustaka dokumen, bukti butir, bukti baris Data prodi)
memindah berkasnya ke **Sampah** Drive akun prodi, lalu catatannya dihapus
dari Supabase. Hanya berkas di dalam folder bukti (`FOLDER_ID`) yang dibuang;
tautan lain (DOI, halaman jurnal) dilewati. Berkas di Sampah bisa dipulihkan
30 hari lewat drive.google.com > Sampah > Pulihkan, tetapi catatannya di situs
harus dibuat ulang. Dosen yang menghapus bukti miliknya hanya menghapus
catatan; berkasnya tetap di Drive. Admin yang menghapus karya (langsung atau
menyetujui ajuan hapus) ikut membuang berkas bukti milik karya itu.

LKD privat (kind `bkd` dan `buka_bkd`, pemilik 2026-11-06): Laporan Kinerja Dosen
memuat nomor HP, tanggal lahir, dan nama mahasiswa, jadi disimpan di
`data-lkps/bkd-privat/<2025-2026>/<nama dosen>/` tanpa tautan publik. Situs
membukanya lewat `buka_bkd`, hanya untuk admin dan dosen pemiliknya. Folder dosen
memakai nama dosen, jadi LKD lama tidak terbuka oleh dosen itu bila namanya diubah.

Berkas privat (pemilik 2026-11-06): jenis di `JENIS_PRIVAT` (`Code.gs`) disimpan tanpa
tautan publik di `dokumen/<jenis>/` atau `berkas-privat/`, dan database mencatat alamat
`lkd.html?f=<id>`. Admin dan pemilik yang login langsung masuk; yang lain memakai
kata sandi `LKD_SANDI`. Kind `privatkan` memindahkan berkas lama ke
`berkas-privat/dipindah/` dan mencabut tautannya (tombol di Data prodi › Dokumen).

Tautan sementara (kind `bagikan_sementara`, `buka_lkd_token`, pemilik 2026-11-06): admin
atau pemilik berkas membuat tautan `lkd.html?f=<id>&t=<token>` yang bisa dibuka siapa pun
selama 2 bulan, untuk laporan SISTER. Masa berlakunya tertanda tangan; tidak ada pemicu
terjadwal. Script Property `TAUTAN_RAHASIA` dibuat otomatis; menghapusnya mematikan
semua tautan sementara.

Asesor membuka LKD dengan kata sandi (kind `buka_lkd_sandi`, pemilik 2026-11-06):
indeks bukti LKPS menautkan `site/lkd.html?f=<id berkas>`. Kata sandinya Script
Property **`LKD_SANDI`**, minimal 8 karakter, diisi sendiri di Project Settings dan
tidak pernah ditulis di repo. Mengubahnya tidak perlu deploy ulang. Kosongkan
setelah visitasi: akses tertutup. 20 kali salah menutup akses satu jam.

Berkas tak terpakai (kind `daftar_berkas`, pemilik 2026-11-03): halaman Isian butir,
bagian "Berkas tak terpakai di Drive", mendaftar berkas di folder bukti yang tidak
dirujuk catatan mana pun di situs (tabelnya di `site/berkas-yatim.js`,
TABEL_RUJUKAN). Berkas yang dirujuk lewat tautan folder induknya, berkas
berumur < 24 jam, dan isi folder `_arsip` tidak ikut. Admin memilih berkas,
lalu berkas dibuang lewat kind `hapus`.

Kode ini dijalankan dari editor Apps Script, bukan dari repo. Berkas di sini
adalah sumbernya: kalau berubah, salin ulang seluruhnya ke editor lalu buat
versi deploy baru (langkah 5).

## Pemasangan (sekali, di akun prodi)

Akun: `<akun Google prodi>` (pemilik folder `data-lkps`).

1. Buka https://script.google.com dengan akun prodi, lalu **New project**.
   Ganti nama proyek (kiri atas) menjadi `cv-site-upload`.
2. Hapus isi `Code.gs` di editor, tempel seluruh isi `Code.gs` dari folder
   ini, lalu simpan (Ctrl+S).
3. **Project Settings** (ikon roda gigi):
   - **Time zone**: `(GMT+07:00) Jakarta`.
   - **Script Properties** > **Add script property**, lima kunci:

   | Property | Nilai | Asal |
   |---|---|---|
   | `FOLDER_ID` | `<ID folder bukti>` | folder `data-lkps`, pemilik 2026-10-09; skrip memakai ID, nama folder boleh diganti |
   | `SUPABASE_URL` | `https://<kode>.supabase.co` | proyek Supabase dashboard-prodi |
   | `SUPABASE_KEY` | publishable key `sb_publishable_...` | Supabase > Project Settings > API Keys; sama dengan `SB_KEY` di `site/config.js`. **Bukan** secret key |
   | `MAX_MB` | `20` | usulan 2026-10-09; samakan dengan `UPLOAD_MAX_MB` di `config.js` |
   | `ALLOWED_EXT` | `pdf,jpg,jpeg,png,docx,xlsx` | usulan 2026-10-09; samakan dengan `UPLOAD_EXT` di `config.js` |

4. **Deploy** > **New deployment** > ikon roda gigi > **Web app**:
   - Description: `cv-site upload`
   - Execute as: **Me**
   - Who has access: **Anyone**

   Klik **Deploy** > **Authorize access** > pilih akun prodi. Muncul
   "Google hasn't verified this app": klik **Advanced** > **Go to
   cv-site-upload (unsafe)** > **Allow**. Ini wajar untuk skrip milik
   sendiri. Salin **Web app URL** (berakhiran `/exec`).
5. Uji: buka Web app URL di jendela **Incognito** (browser yang login ke
   beberapa akun Google bisa menampilkan "Sorry, unable to open the file").
   "This project has not been deployed yet" di Manage deployments berarti
   langkah 4 belum tuntas. Harus tampil
   `{"ok":true,"folder":"data-lkps",...}`. Bila `ok:false`, pesannya
   menyebut property yang kurang atau salah.
6. Jalankan `python install.py` lagi dan isi URL itu saat ditanya.

## Cadangan ke Drive (kind `cadangan`, repo publik)

Prodi yang situsnya satu repo publik tidak bisa menyimpan cadangan di repo,
karena cadangan memuat email dan NIDN dosen. GitHub Actions mengirim zip-nya ke
Web App ini (`supabase_archive.py send`). Permintaan ini memakai token
sendiri, bukan login dosen. Tanpa dua kunci di bawah, cadangan ditolak dan
unggahan bukti tetap berjalan.

1. Buat folder baru di **luar** folder bukti, misalnya `cadangan-situs`. Jangan
   dibagikan: isinya data pribadi. Berkas di dalamnya tidak dibagikan skrip.
2. Tambahkan dua Script Properties, lalu buat versi deploy baru bila Web App
   sudah terpasang:

   | Property | Nilai |
   |---|---|
   | `CADANGAN_FOLDER_ID` | ID folder itu (bagian URL setelah `/folders/`) |
   | `CADANGAN_TOKEN` | token dari `install.py`, sama dengan GitHub Secret `CADANGAN_TOKEN` |

Zip lama tidak dihapus otomatis.

## Berkas nilai CPL (kind `cpl` dan `cpl_unduh`, 2026-11-11)

Dosen mengunggah `Template_Input_Data_CPL.xlsx` di situs (Input data › Berkas nilai
CPL). Berkas memuat NIM: disimpan di `berkas-privat/cpl/<TA semester>/<MK-kelas>/`,
versi lama ke `riwayat/`, dan hanya admin yang bisa membukanya. `run_cpl.py`
(`source: site` di `config.yaml`) mengunduh berkas terbaru tiap kelas dengan kunci.

Pasang sekali:

1. Buat kunci acak (minimal 32 karakter), misalnya di komputer admin:
   `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
2. Apps Script › **Project Settings** › **Script Properties** › tambah
   `CPL_KUNCI` = kunci itu.
3. Di setiap komputer yang menjalankan `run_cpl.py`, tambahkan baris
   `CPL_KUNCI=<kunci yang sama>` ke `rahasia.env` di akar repo ini
   (berkas itu tidak ikut git). Jangan kirim kunci lewat chat atau email terbuka.
4. Terbitkan versi baru Apps Script (lihat Memperbarui kode).

Mengganti kunci: ubah Script Property dan semua `rahasia.env`. Dua puluh kali
kunci salah menutup unduhan selama satu jam.

## Pengajuan mahasiswa KP dan lomba (kind `mhs_*`, 2026-11-17)

Mahasiswa tidak login. Di `pengajuan.html` mereka mengisi NIM, lalu tautan pribadi
dikirim ke `<NIM>@<MHS_DOMAIN>`; lewat tautan itu mereka mengunggah berkas dan melihat
proses. Pembimbing lalu admin memeriksa di ruang kerja (Pengajuan mahasiswa). Berkas di
`berkas-privat/mahasiswa/<kp|lomba>/<tahun>/<NIM nama>/`; foto lomba di
`mahasiswa-foto/<tahun>/` dibagikan dengan tautan supaya bisa tampil di halaman prestasi.

Pasang sekali, SETELAH `supabase/instal-lengkap.sql` dijalankan:

1. Supabase › SQL Editor: `select kunci from public.layanan_kunci;` lalu salin hasilnya.
2. Apps Script › **Project Settings** › **Script Properties**, tambah:
   - `MHS_KUNCI` = kunci dari langkah 1 (jangan kirim lewat chat atau email terbuka);
   - `MHS_DOMAIN` = domain email mahasiswa (bagian setelah @), mis. `student.kampus.ac.id`;
   - `MHS_SITUS` = alamat situs dengan garis miring akhir, mis.
     `https://<organisasi>.github.io/<repo-situs>/` (sama dengan alamat situs publik).
3. Terbitkan versi baru Apps Script (lihat Memperbarui kode). Buka URL Web App:
   `versi` harus `2026-11-17-koordinator-tahap2` (atau yang lebih baru).

Email dikirim dari akun Google prodi (kuota harian MailApp, ±100 untuk Gmail biasa):
satu email per pengajuan baru, per permintaan tautan ulang, dan per kabar dari
pembimbing/admin. Status selalu terlihat di tautan pribadi mahasiswa.

## Memperbarui kode

Tempel ulang `Code.gs`, simpan, lalu **Deploy** > **Manage deployments** >
ikon pensil > Version: **New version** > **Deploy**. URL tetap sama.

**Izin baru tidak diminta oleh deploy.** Bila kode baru memakai layanan
Google yang belum diizinkan (mis. `MailApp` untuk Pengingat), situs
melaporkan "You do not have permission to call …". Pilih fungsi
`izinkanEmail` di daftar fungsi editor, klik **Run**, lalu **Review
permissions** > akun prodi > **Advanced** > **Go to … (unsafe)** >
**Allow** ("developer" yang disebut peringatan itu adalah akun prodi
sendiri). Jalankan di jendela **InPrivate** yang hanya masuk ke akun
prodi: bila peramban masuk ke beberapa akun Google (alamat memuat
`authuser=3` dan sejenisnya), jendela izin berakhir di "Sorry, unable to
open the file" dan Run langsung galat (pengalaman 2026-11-11). Lalu
terbitkan versi baru. Bila editor menampilkan berkas
`appsscript.json` yang berisi `oauthScopes`, tambahkan juga
`https://www.googleapis.com/auth/script.send_mail` ke daftar itu.

**Jangan archive deployment yang aktif.** URL deployment yang di-archive
langsung mati (HTTP 404), dan browser hanya melaporkan "Failed to fetch".
URL baru harus dipasang ulang lewat `python install.py`.
**New deployment** membuat URL baru dan `config.js` harus ikut diganti.

## Serah terima

Pemilik skrip dan folder adalah akun prodi. Pengelola baru cukup memegang
akun itu; tidak ada kunci rahasia di skrip (publishable key memang publik,
login dosen diperiksa ke Supabase pada setiap unggahan).
