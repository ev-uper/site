# Templat

## Template_Input_Data_CPL.xlsx

Templat nilai CPL untuk dosen: **satu berkas per kelas per semester**.
Versi: `CPL-2026.10.09` (tertulis di `Info!B13`).

Perubahan dari templat asal:

| Lembar | Perubahan | Alasan |
|---|---|---|
| Info | baris 12 `Kelas` (isian dosen) | satu berkas per kelas (pemilik 2026-10-09) |
| Info | baris 13 `Versi templat` | pembaca mengenali versi berkas |
| Periksa | baris 20 memeriksa `Info!B4:B12` (termasuk Kelas) | identitas lengkap |
| Petunjuk | baris 3 dan 29 menyebut kelas | sesuai aturan satu berkas per kelas |
| Turunan, Hasil, Periksa | dikunci (Protect Sheet, tanpa kata sandi) | cegah salah sunting (pemilik 2026-10-09) |

Isi contoh (MK 41214, rumusan CPL di `Rumusan`, dan tiga baris oranye CONTOH
di `Nilai`) harus diganti dengan milik prodi Anda sebelum dibagikan ke dosen.

Ambang di `Periksa!B4:B5` (45 dan 60) hanya tampilan untuk dosen. Analisis
prodi memakai ambang dari config (keputusan pemilik 2026-10-09: individu 45 =
batas nilai C, kelas 60% mahasiswa).

Kalau templat diubah: naikkan `Info!B13`, perbarui tata letak sel di
`cpl/template.py` bila perlu, lalu buat ulang berkas uji
(`tests/data/make_golden.py`, lalu `tests/data/recalc_excel.ps1`) dan
jalankan `pytest`.
