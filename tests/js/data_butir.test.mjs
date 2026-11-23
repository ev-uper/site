// site/data-butir.js: rows behind each butir card must follow the same filters
// as bangun.py and the score functions in skor.html (owner 2026-11-07).
// Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { dataButir, pendukungButir, buktiBaris, dosenDTPS, htmlTabelData, BUTIR_RINCIAN_DATA } from '../../site/data-butir.js';

const TS = 2026;

test('bukti: row link columns plus lkps_bukti by table and row id, no duplicates', () => {
  const B = [{ tabel: 'lkps_tracer_lulusan', baris_id: 7, judul: 'Laporan', url: 'https://a/1' },
    { tabel: 'lkps_tracer_lulusan', baris_id: 7, judul: 'Sama', url: 'https://a/0' },
    { tabel: 'lkps_tracer_lulusan', baris_id: 8, url: 'https://a/2' },
    { tabel: 'lkps_kohort_lulusan', baris_id: 7, url: 'https://a/3' },
    { tabel: 'lkps_tracer_lulusan', baris_id: 7, dokumen: { url: 'https://a/4' } }];
  const xs = buktiBaris('lkps_tracer_lulusan', { id: 7, bukti_url: 'https://a/0' }, B);
  assert.deepEqual(xs.map(x => x.url), ['https://a/0', 'https://a/1', 'https://a/4']);
  assert.deepEqual(buktiBaris('x', { bukti_url: 'bukan url' }, []), []);
});

test('butir 6: Data prodi rows count once per TS in range; karya partners once, minus the parent partner', () => {
  const P = {
    kerjasama: [
      { id: 1, mitra: 'PT Induk', tingkat: 'nasional', jenis: 'pendidikan', tahun_mulai: 2023, tahun_selesai: 2030 },
      { id: 2, mitra: 'Pemda', tingkat: 'wilayah', tahun_mulai: 2025, tahun_selesai: null },
      { id: 3, mitra: 'Lama', tingkat: 'nasional', tahun_mulai: 2018, tahun_selesai: 2020 },
      { id: 4, mitra: '', tahun_mulai: 2025 },
      { id: 5, mitra: 'Terbalik', tahun_mulai: 2026, tahun_selesai: 2024 }],
    karya: [
      { kategori: 'pkm', tahun: 2025, bulan: 10, judul: 'A', kerjasama_id: 1,
        karya_mitra: [{ institusi: 'pt induk', tingkat: 'nasional' }, { institusi: 'Desa X', tingkat: 'lokal' }] },
      { kategori: 'publikasi', tahun: 2024, bulan: 3, judul: 'B', karya_mitra: [{ institusi: 'Univ Y', tingkat: 'internasional' }] },
      { kategori: 'penelitian', tahun: 2025, judul: 'C', relevan_visi: false, karya_mitra: [{ institusi: 'Z' }] },
      { kategori: 'penelitian', tahun: 2022, judul: 'D', karya_mitra: [{ institusi: 'Tua' }] }],
  };
  const D = { akreditasi: { kerjasama: [{ tahun: 2024, internasional: 1, nasional: 1, wilayah: 0, tanpa_tingkat: 0 },
    { tahun: 2025, nasional: 1, wilayah: 1 }, { tahun: 2026, nasional: 1, wilayah: 2 }] } };
  const x = dataButir('6', P, TS, D);
  const per = Object.fromEntries(x.baris.map(r => [r._nama, r._n]));
  assert.equal(per['PT Induk'], 3);
  assert.equal(per['Pemda'], 2);          // 2025, 2026 (empty end = until next year)
  assert.equal(per['Desa X'], 1);
  assert.equal(per['Univ Y'], 1);
  for (const n of ['pt induk', 'Lama', 'Z', 'Tua', 'Terbalik']) assert.equal(per[n], undefined, n);
  assert.equal(x.pakai, 7);
  assert.equal(x.pembanding, 7);
});

test('butir 43: verified, TS-4..TS by month rule, academic/non-academic only', () => {
  const P = { prestasi: [
    { id: 1, nama_kegiatan: 'A', bidang: 'akademik', tahun: 2021, bulan: 9, status: 'terverifikasi' },   // TS 2022
    { id: 2, nama_kegiatan: 'B', bidang: 'non_akademik', tahun: 2026, bulan: 1, status: 'terverifikasi' },
    { id: 3, nama_kegiatan: 'C', bidang: 'akademik', tahun: 2021, bulan: 8, status: 'terverifikasi' },   // TS 2021: out
    { id: 4, nama_kegiatan: 'D', bidang: 'lain', tahun: 2025, status: 'terverifikasi' },
    { id: 5, nama_kegiatan: 'E', bidang: 'akademik', tahun: 2025, status: 'diajukan' }] };
  const D = { prestasi_agregat: [{ tahun: 2021, tahun_ts: 2022, bidang: 'akademik', jumlah: 1 },
    { tahun: 2026, tahun_ts: 2026, bidang: 'non_akademik', jumlah: 1 }, { tahun: 2021, tahun_ts: 2021, bidang: 'akademik', jumlah: 1 }] };
  const x = dataButir('43', P, TS, D);
  assert.deepEqual(x.baris.map(r => r.nama_kegiatan).sort(), ['A', 'B']);
  assert.equal(x.pakai, 2);
  assert.equal(x.pembanding, 2);
});

test('butir 46: student first-author publications from karya plus all Data prodi rows, 3 TS', () => {
  const P = {
    karya: [{ kategori: 'publikasi', tahun: 2025, judul: 'K1', karya_mahasiswa: [{ peran: 'penulis_pertama' }] },
      { kategori: 'publikasi', tahun: 2025, judul: 'K2', karya_mahasiswa: [{ peran: 'anggota' }] },
      { kategori: 'publikasi', tahun: 2025, judul: 'K3', relevan_visi: false, karya_mahasiswa: [{ peran: 'penulis_pertama' }] }],
    pubMhs: [{ id: 1, tahun: 2023, bulan: 10, judul: 'M1' }, { id: 2, tahun: 2023, bulan: 2, judul: 'M2' }],
  };
  const D = { akreditasi: { publikasi_mhs: [{ tahun: 2025, na1: 1 }, { tahun: 2024, nb1: 1 }, { tahun: 2023, na2: 1 }] } };
  const x = dataButir('46', P, TS, D);
  assert.deepEqual(x.baris.map(r => r.judul), ['K1', 'M1']);
  assert.equal(x.pembanding, 2);
});

test('butir 47: every student output in the window, component named', () => {
  const P = { luaranMhs: [{ id: 1, tahun: 2026, jenis: 'Hak Cipta', judul: 'H' }, { id: 2, tahun: 2024, jenis: 'merek', judul: 'M' },
    { id: 3, tahun: 2020, jenis: 'paten', judul: 'P' }] };
  const x = dataButir('47', P, TS, { akreditasi: { luaran_mhs: [{ tahun: 2026, hki: 1 }, { tahun: 2024, lainnya: 1 }] } });
  assert.deepEqual(x.baris.map(r => [r.judul, r._komponen]), [['H', 'NHKI ×1'], ['M', 'tidak masuk rumus']]);
  assert.equal(x.pakai, x.pembanding);
});

test('butir 44/45: cohorts TS-8..TS-1 with graduates; TS-4 cohort; fallback to TS rows', () => {
  const P = { kohort: [{ id: 1, tahun_masuk: 2018, jumlah_masuk: 50, lulus_3_5_sd_4_5: 20, lulus_4_5_sd_5_5: 5 },
    { id: 2, tahun_masuk: 2022, jumlah_masuk: 60 }, { id: 3, tahun_masuk: 2017, jumlah_masuk: 40, lulus_3_5_sd_4_5: 9 }] };
  const D = { akreditasi: { kohort: [{ tahun_masuk: 2018, masuk: 50, lulus: 25 }, { tahun_masuk: 2022, masuk: 60, lulus: 0 }] } };
  const x44 = dataButir('44', P, TS, D);
  assert.deepEqual(x44.baris.map(r => [r.tahun_masuk, r._lulus]), [[2018, 25]]);
  assert.equal(x44.pembanding, 1);
  const x45 = dataButir('45', P, TS, D);
  assert.deepEqual(x45.baris.map(r => r.tahun_masuk), [2022]);
  const cad = dataButir('44', { mhs: [{ id: 9, tahun_akademik: '2024/2025', jumlah_lulusan: 10, rerata_masa_studi_tahun: 4.6 },
    { id: 8, tahun_akademik: '2021/2022', jumlah_lulusan: 10, rerata_masa_studi_tahun: 4.6 }] }, TS,
    { akreditasi: { ta: [{ tahun_ts: 2025, lulusan: 10, rerata_masa_studi: 4.6 }] } });
  assert.equal(cad.tab, 'mahasiswa');
  assert.deepEqual(cad.baris.map(r => r.tahun_akademik), ['2024/2025']);
  assert.equal(cad.pakai, cad.pembanding);
});

test('butir 40-42, 49-52: TS rows and windows', () => {
  const P = { mhs: [{ id: 1, tahun_akademik: '2025/2026', jumlah_mahasiswa_aktif: 300, jumlah_lulusan: 0 },
      { id: 2, tahun_akademik: '2024/2025', jumlah_lulusan: 40, rerata_ipk_lulusan: 3.3 }],
    tracer: [{ id: 1, tahun_lulus: 2024 }, { id: 2, tahun_lulus: 2025 }, { id: 3, tahun_lulus: 2026 }],
    kepuasan: [{ id: 1, tahun_akademik: '2025/2026', aspek: 'etika' }, { id: 2, tahun_akademik: '2024/2025', aspek: 'etika' }] };
  const D = { akreditasi: { ta: [{ tahun_ts: 2026, mahasiswa_aktif: 300, lulusan: 0 }, { tahun_ts: 2025, lulusan: 40 }],
    kepuasan: [{ tahun_ts: 2026, aspek: 'etika' }] }, tracer: [{ tahun_lulus: 2024 }, { tahun_lulus: 2025 }] };
  assert.deepEqual(dataButir('40', P, TS, D).baris.map(r => r.id), [1]);
  assert.deepEqual(dataButir('42', P, TS, D).baris.map(r => r.id), [2]);
  const t = dataButir('50', P, TS, D);
  assert.deepEqual(t.baris.map(r => r.tahun_lulus), [2025, 2024]);
  assert.equal(t.pakai, t.pembanding);
  assert.deepEqual(dataButir('52', P, TS, D).baris.map(r => r.id), [1]);
});

test('butir 10/11 and 27/28: rows the score uses', () => {
  const P = { dana: [{ kategori: 'penelitian', tahun: 2023, bulan: 9, judul: 'A', besaran_dana: 5e6 },
      { kategori: 'penelitian', tahun: 2023, bulan: 8, judul: 'B' }, { kategori: 'pkm', tahun: 2025, judul: 'C' }],
    dosen: [{ nama: 'A', dtps: true, pendidikan: 'S3', jabatan: 'Lektor' }, { nama: 'B', dtps: false },
      { nama: 'C', peran: 'asesor', dtps: true }, { nama: 'D', dtps: null, aktif: true, pendidikan: 'S2', jabatan: 'asisten ahli' }] };
  assert.deepEqual(dataButir('10', P, TS, {}).baris.map(r => r.judul), ['A']);
  assert.deepEqual(dataButir('11', P, TS, {}).baris.map(r => r.judul), ['C']);
  assert.deepEqual(dosenDTPS(P.dosen).map(d => d.nama), ['A', 'D']);
  const x27 = dataButir('27', P, TS, { dtps: { jumlah: 2 } });
  assert.deepEqual(x27.baris.map(r => r._hitung), ['doktor', '']);
  assert.equal(x27.pakai, x27.pembanding);
  assert.deepEqual(dataButir('28', P, TS, {}).baris.map(r => r._hitung), ['L/LK/GB', '']);
});

test('manual butir: supporting Data prodi rows, filtered where the butir is narrower', () => {
  const P = { pendukung: {
    ref_mata_kuliah: [{ id: 1, nama: 'Capstone', capstone: true }, { id: 2, nama: 'Kalkulus', basic_science: true, rps_url: 'https://r' },
      { id: 3, nama: 'Lama', capstone: true, aktif: false }],
    ref_tema_peta_jalan: [{ id: 1, nama: 'Banjir', jenis: 'penelitian' }, { id: 2, nama: 'Desa', jenis: 'pkm' }, { id: 3, nama: 'Air', jenis: 'keduanya' }],
    lkps_target_kinerja: [{ id: 1, nama: 'Waktu tunggu', butir: 49 }, { id: 2, nama: 'Sitasi', butir: 54 }],
    lkps_dokumen_k3l: [{ id: 1 }], lkps_fasilitas_k3l: [{ id: 1 }, { id: 2 }] } };
  assert.deepEqual(pendukungButir('20', P)[0].baris.map(r => r.nama), ['Capstone']);
  assert.deepEqual(pendukungButir('15', P)[0].baris.map(r => r.nama), ['Kalkulus']);
  assert.equal(pendukungButir('15', P)[0].baris[0]._bukti[0].url, 'https://r');
  assert.deepEqual(pendukungButir('22', P)[0].baris.map(r => r.nama), ['Banjir', 'Air']);
  assert.deepEqual(pendukungButir('24', P)[0].baris.map(r => r.nama), ['Desa', 'Air']);
  assert.deepEqual(pendukungButir('54', P)[0].baris.map(r => r.nama), ['Sitasi']);
  assert.deepEqual(pendukungButir('39', P).map(x => x.baris.length), [1, 2]);
  assert.ok(pendukungButir('39', P).every(x => x.pendukung));
  assert.deepEqual(pendukungButir('33', P), []);
  assert.equal(dataButir('1', P, TS, {}), null);
});

test('butir 30: BKD rows per DTPS lecturer, checked against rbk_prodi count and mean', () => {
  const v = 'terverifikasi', ta = '2025/2026';
  const P = { dosen: [{ nama: 'Budi', nidn: '1', dtps: true }, { nama: 'Ani', nidn: '2', dtps: true }],
    bkd: [{ nidn: '1', tahun_akademik: ta, semester: 'ganjil', verifikasi: v, sks_pendidikan: 12, bukti_url: 'https://d/1' },
      { nidn: '1', tahun_akademik: ta, semester: 'genap', verifikasi: v, sks_pendidikan: 12 },
      { nidn: '2', tahun_akademik: ta, semester: 'ganjil', verifikasi: v, sks_pendidikan: 14 }],
    rbk: [{ tahun_akademik: ta, rbk: 9.5, n_dosen: 2 }] };
  const x = dataButir('30', P, TS, {});
  assert.deepEqual(x.baris.map(r => [r.nama, r._beban]), [['Ani', '7'], ['Budi', '12']]);
  assert.deepEqual(x.baris[1]._lkd, [{ url: 'https://d/1', label: 'LKD ganjil' }]);
  assert.equal(x.pakai, 2);
  assert.equal(x.pembanding, 2);
  assert.equal(x.periksa, '');
  const beda = dataButir('30', { ...P, rbk: [{ tahun_akademik: ta, rbk: 13.6, n_dosen: 2 }] }, TS, {});
  assert.match(beda.periksa, /9,5 sks.*13,6 sks/);
  assert.equal(dataButir('30', { ...P, rbk: [] }, TS, {}).pembanding, null);
});

test('htmlTabelData: LKD buttons, hidden bukti column, PERIKSA on mismatch', () => {
  const esc = t => String(t).replace(/</g, '&lt;');
  const x = { kolom: [['Nama', 'nama']], baris: [{ nama: 'A', _lkd: [{ url: 'u', label: 'LKD ganjil' }] }, { nama: 'B' }],
    pakai: 2, pembanding: 3, labelPakai: 'dosen', periksa: '' };
  const h = htmlTabelData(x, { esc, admin: true });
  assert.match(h.tabel, /data-lkd="u"/);
  assert.match(h.tabel, /tanpa bukti/);
  assert.match(h.cek, /PERIKSA: daftar 2 dosen, angka kartu 3/);
  assert.equal(h.ringkas, '2 baris · bukti 1/2');
  const tanpa = htmlTabelData({ ...x, tanpaBukti: true, pembanding: 2 }, { esc });
  assert.doesNotMatch(tanpa.tabel, /Bukti/);
  assert.match(tanpa.cek, /sama dengan angka/);
  assert.match(htmlTabelData({ ...x, baris: [] }, { esc, ts: 2026 }).tabel, /TS 2025\/2026 \(atau belum dapat Anda baca\)/);
});

test('every butir with a data list is offered on the rincian page', () => {
  for (const no of ['6', '10', '30', '40', '52', '1', '39', '56']) assert.ok(BUTIR_RINCIAN_DATA.includes(no), no);
  assert.ok(!BUTIR_RINCIAN_DATA.includes('33'));
});

test('butir 35: DTPS first/corresponding authors of reputable publications and patent holders, unique lecturers', () => {
  const pen = (nama, peran, korespondensi = false) => ({ peran, korespondensi, dosen: { nama } });
  const P = { dosen: [{ nama: 'Budi Santoso', dtps: true }, { nama: 'Ani', dtps: true }, { nama: 'Luar', dtps: false }],
    karya: [
      { id: 1, kategori: 'publikasi', tahun: 2025, judul: 'Q1', jenis: 'jurnal', indeksasi: 'scopus_q1',
        karya_penulis: [pen('Budi Santoso', 'penulis_pertama'), pen('Ani', 'anggota')] },
      { id: 2, kategori: 'publikasi', tahun: 2024, judul: 'Konf', jenis: 'prosiding', indeksasi: 'ieee',
        karya_penulis: [pen('Ani', 'anggota', true), pen('Luar', 'penulis_pertama')] },
      { id: 3, kategori: 'publikasi', tahun: 2025, judul: 'Nasional', jenis: 'jurnal', indeksasi: 'sinta_2',
        karya_penulis: [pen('Budi Santoso', 'penulis_pertama')] },
      { id: 4, kategori: 'publikasi', tahun: 2025, judul: 'Luar visi', jenis: 'jurnal', indeksasi: 'scopus', relevan_visi: false,
        karya_penulis: [pen('Ani', 'penulis_pertama')] },
      { id: 5, kategori: 'luaran', tahun: 2026, bulan: 2, judul: 'Paten', sub_jenis: 'paten_sederhana',
        karya_penulis: [pen('Budi Santoso', 'anggota')] },
      { id: 6, kategori: 'publikasi', tahun: 2022, judul: 'Lama', jenis: 'jurnal', indeksasi: 'scopus',
        karya_penulis: [pen('Ani', 'penulis_pertama')] }] };
  const D = { dtps: { karya_utama_rinci: [{ slug: 'budi-santoso', tahun: 2025 }, { slug: 'ani', tahun: 2024 }, { slug: 'ani', tahun: 2022 }] } };
  const x = dataButir('35', P, TS, D);
  assert.deepEqual(x.baris.map(r => [r.nama, r.judul, r._peran]),
    [['Ani', 'Konf', 'korespondensi'], ['Budi Santoso', 'Paten', 'pemegang paten'], ['Budi Santoso', 'Q1', 'penulis pertama']]);
  assert.equal(x.pakai, 2);
  assert.equal(x.pembanding, 2);
});

test('supporting rows for butir 7-11, 17, 26, 48 follow the windows of their related scores', () => {
  const tahunDepan = new Date().getFullYear() + 1;
  const P = { dosen: [{ nama: 'A', dtps: true, jabatan: 'Lektor', pendidikan: 'S3' }, { nama: 'B', dtps: false }],
    pendukung: {
      lkps_kerjasama: [{ id: 1, mitra: 'Lama', tahun_mulai: 2018, tahun_selesai: 2020 }, { id: 2, mitra: 'Aktif', tahun_mulai: 2025 },
        { id: 3, mitra: 'Tanpa tahun' }, { id: 4, mitra: 'Depan', tahun_mulai: tahunDepan + 5 }],
      lkps_penggunaan_dana: [{ id: 1, tahun_akademik: '2023/2024' }, { id: 2, tahun_akademik: '2022/2023' }, { id: 3, tahun_akademik: '2025/2026' }],
      lkps_tracer_lulusan: [{ id: 1, tahun_lulus: 2024 }, { id: 2, tahun_lulus: 2025 }, { id: 3, tahun_lulus: 2026 }] } };
  const D = { integrasi: [{ tahun: 2024, tahun_ts: 2025, judul_kegiatan: 'I1', bentuk: 'materi_kuliah' }, { tahun: 2022, tahun_ts: 2023, judul_kegiatan: 'Lama' }] };
  assert.deepEqual(pendukungButir('7', P, TS, D)[0].baris.map(r => r.mitra), ['Aktif']);
  for (const no of ['8', '9', '10', '11']) assert.deepEqual(pendukungButir(no, P, TS, D)[0].baris.map(r => r.id), [1, 3], no);
  assert.deepEqual(pendukungButir('48', P, TS, D)[0].baris.map(r => r.tahun_lulus), [2024, 2025]);
  const i17 = pendukungButir('17', P, TS, D);
  assert.equal(i17.length, 1);
  assert.deepEqual(i17[0].baris.map(r => [r.judul_kegiatan, r._bentuk]), [['I1', 'materi kuliah']]);
  assert.deepEqual(i17[0].baris[0]._karya, { kategori: 'integrasi', tahun: 2024, judul: 'I1' });
  const x26 = dataButir('26', P, TS, { dtps: { jumlah: 1 } });
  assert.deepEqual(x26.baris.map(r => [r.nama, r._isi, r._hitung]), [['A', 'Lektor', 'S3']]);
  assert.equal(x26.pakai, x26.pembanding);
  for (const no of ['7', '8', '9', '17', '26', '48']) assert.ok(BUTIR_RINCIAN_DATA.includes(no), no);
});
