# Bangun situs otomatis

Situs dibangun di GitHub Actions dan diterbitkan GitHub Pages dari repo yang
sama. Tidak perlu komputer pengelola. Pemasangan: `README.md`.

| Bagian | Berkas |
|---|---|
| Bangun dan terbit | `.github/workflows/bangun-situs.yml` |
| Jaga database, cadangan, arsip | `.github/workflows/pemeliharaan.yml` |

## Kapan situs dibangun

- tiap jam pada menit ke-23;
- tiap push ke `main` yang mengubah `site/`, `bangun.py`, atau workflow-nya;
- manual: **Actions › Bangun situs › Run workflow**.

## Cadangan

Repo ini publik, jadi data tidak pernah disimpan di dalamnya. Tiap malam
(01:40 WIB) seluruh tabel menjadi satu zip di folder cadangan Google Drive prodi.
Cadangan yang lebih dari 35 hari dipindah ke Sampah Drive (bisa dipulihkan 30 hari),
kecuali cadangan tanggal 1 tiap bulan, yang disimpan. Arsip tahunan tiap
1 September masuk ke folder yang sama dan tidak pernah dipangkas.

Untuk memangkas data lama (`supabase_archive.py prune`), unduh zip arsip dari
Drive, ekstrak ke `arsip/` di komputer pengelola, lalu jalankan perintahnya.
Folder `cadangan/` dan `arsip/` diabaikan git; jangan memaksa memasukkannya.

Jejak perubahan data (tabel `jejak`, Admin prodi › Jejak perubahan) tidak ikut
cadangan. Jejak yang lebih tua dari 3 tahun dihapus oleh langkah "Hapus jejak
perubahan" pada job cadangan (fungsi `bersihkan_jejak`); kegagalannya tidak
menghalangi cadangan.

## Pemulihan

Bila proyek Supabase hilang atau rusak, atau untuk gladi tahunan: unduh zip
cadangan terbaru dari Drive, ekstrak ke `cadangan/`, lalu jalankan

    python supabase_archive.py pulihkan cadangan

Hasilnya folder `pulih/cadangan-<tanggal>/` berisi `1-skema.sql`,
`2-data.sql`, `3-periksa.sql`, dan `LANGKAH.md` (urutan menjalankan di SQL
Editor proyek baru, gladi bulat-balik dengan `backup --folder` dan
`bandingkan`, dan pengaturan yang harus diarahkan ke proyek baru). Folder itu
memuat data pribadi dan diabaikan git; hapus setelah selesai.

## Tanda aktif

GitHub mematikan jadwal repo publik setelah 60 hari tanpa aktivitas. Karena
itu tugas cadangan menulis tanggal ke `.github/aktivitas.txt` tiap tanggal 1 (dan
saat cadangan gagal). Bila
situs berhenti diperbarui, buka **Actions**, pilih workflow-nya, lalu klik
**Enable workflow**.
