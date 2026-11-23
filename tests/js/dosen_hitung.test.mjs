// Pengelompokan dosen dan hitungan akreditasi per TS (patch 154, pemilik 2026-11-22).
import test from 'node:test';
import assert from 'node:assert/strict';
import { kelompokDosen, ampuPerTA, statusTS, hitungTS, sedangTB, batasTA, tbLewat } from '../../site/dosen-hitung.js';

const DOSEN = [
  { id: 'a', nama: 'DTPS Mengajar', kategori: 'tetap', dtps: true, peran: 'dosen', aktif: true },
  { id: 'b', nama: 'DTPS Tidak Mengajar', kategori: 'tetap', dtps: true, peran: 'admin', aktif: true },
  { id: 'c', nama: 'DT Prodi Lain', kategori: 'tetap', dtps: false, peran: 'dosen', aktif: true },
  { id: 'd', nama: 'Tugas Belajar', kategori: 'tetap', dtps: false, peran: 'dosen', aktif: true, tugas_belajar: 'S3, ITB' },
  { id: 'e', nama: 'DTT', kategori: 'tidak_tetap', dtps: false, peran: 'dosen', aktif: true },
  { id: 'f', nama: 'Praktisi', kategori: 'industri', dtps: false, peran: 'dosen', aktif: true },
  { id: 'g', nama: 'Staf TU', kategori: null, dtps: false, peran: 'admin', aktif: true },
  { id: 'h', nama: 'Dekan', kategori: null, dtps: false, peran: 'pimpinan', aktif: true },
  { id: 'i', nama: 'Asesor', kategori: 'tetap', dtps: false, peran: 'asesor', aktif: true },
  { id: 'j', nama: 'DTPS Lama', kategori: null, dtps: 'ya', peran: 'dosen', aktif: true },
  { id: 'k', nama: 'DTPS Nonaktif', kategori: 'tetap', dtps: true, peran: 'dosen', aktif: false },
];
const AMPU = ampuPerTA({
  kelas: [{ id: 1, tahun_akademik: '2026/2027' }, { id: 2, tahun_akademik: '2026/2027' }, { id: 3, tahun_akademik: '2025/2026' }],
  kd: [{ kelas_id: 1, dosen_id: 'a' }, { kelas_id: 2, dosen_id: 'c' }, { kelas_id: 2, dosen_id: 'f' }, { kelas_id: 3, dosen_id: 'b' }],
  manual: [{ dosen_id: 'j', tahun_akademik: '2026/2027' }, { dosen_id: 'k', tahun_akademik: '2026/2027' }],
});

test('groups: DTPS, DT, study leave, DTT, industry, staff, leader, assessor, old DTPS without category', () => {
  assert.deepEqual(DOSEN.map(d => kelompokDosen(d)), ['dtps', 'dtps', 'dt', 'tb', 'dtt', 'industri', 'staf', 'pimpinan', 'asesor', 'dtps', 'dtps']);
});

test('teaching per academic year from classes (team teaching) and manual ticks', () => {
  assert.deepEqual([...AMPU.get('2026/2027')].sort(), ['a', 'c', 'f', 'j', 'k']);
  assert.deepEqual([...AMPU.get('2025/2026')], ['b']);
});

test('counted on TS only when teaching; reasons for the others', () => {
  const st = id => statusTS(DOSEN.find(d => d.id === id), '2026/2027', AMPU);
  assert.deepEqual([st('a').dtps, st('a').dt], [true, true]);
  assert.equal(st('b').alasan, 'tidak mengampu MK pada 2026/2027');
  assert.deepEqual([st('c').dt, st('c').dtps], [true, false]);
  assert.equal(st('d').alasan, 'tugas belajar');
  assert.equal(st('f').dtt, true);
  assert.equal(st('g').alasan, 'bukan dosen prodi');
  assert.equal(st('k').alasan, 'tidak aktif');
  const h = hitungTS(DOSEN, '2026/2027', AMPU);
  assert.deepEqual([h.ndtps, h.ndt, h.ndtt, h.industri, h.diterapkan], [2, 3, 1, 1, true]);   // a, j | a, c, j | f
  assert.deepEqual(h.tidakMengampu, ['DTPS Tidak Mengajar', 'DTT']);
});

test('safeguard: a TS without any teaching data does not apply the teaching rule', () => {
  const h = hitungTS(DOSEN, '2027/2028', AMPU);
  assert.equal(h.diterapkan, false);
  assert.deepEqual([h.ndtps, h.ndt, h.ndtt], [3, 4, 2]);   // a, b, j | + c | e, f
  assert.equal(statusTS(DOSEN[1], '2027/2028', AMPU).alasan, '');
});

// 156 (pemilik 2026-11-22): tidak dihitung pada TS yang beririsan dengan masa tugas belajar; di luar itu DTPS homebase.
test('study leave period: overlapping academic years only; open end = still away; no start date = always', () => {
  assert.deepEqual(batasTA('2026/2027'), ['2026-09-01', '2027-08-31']);
  assert.equal(batasTA('2026'), null);
  const tb = { id: 't', nama: 'TB', kategori: 'tetap', dtps: false, peran: 'dosen', aktif: true, tugas_belajar: 'S3, Kyoto',
    tugas_belajar_mulai: '2024-02-01', tugas_belajar_selesai: '2027-02-15' };
  assert.deepEqual(['2022/2023', '2023/2024', '2024/2025', '2026/2027', '2027/2028'].map(ta => sedangTB(tb, ta)), [false, true, true, true, false]);
  assert.equal(kelompokDosen(tb, '2027/2028'), 'dtps');
  assert.equal(kelompokDosen(tb, '2026/2027'), 'tb');
  assert.equal(sedangTB({ ...tb, tugas_belajar_selesai: null }, '2030/2031'), true);
  assert.equal(sedangTB({ ...tb, tugas_belajar_mulai: null, tugas_belajar_selesai: null }, '2010/2011'), true);
  assert.equal(sedangTB({ ...tb, tugas_belajar: null }, '2026/2027'), false);
  // tanpa TS: tanggal hari
  assert.equal(sedangTB(tb, null, '2027-03-01'), false);
  assert.equal(sedangTB(tb, null, '2027-02-15'), true);
  assert.equal(tbLewat(tb, '2027-03-01'), true);
  assert.equal(tbLewat(tb, '2027-01-01'), false);
  // hitungan: kembali dan mengampu pada 2027/2028 = DTPS; 2026/2027 tidak
  const ampu = ampuPerTA({ manual: [{ dosen_id: 't', tahun_akademik: '2027/2028' }, { dosen_id: 't', tahun_akademik: '2026/2027' }] });
  assert.equal(statusTS(tb, '2027/2028', ampu).dtps, true);
  assert.equal(statusTS(tb, '2026/2027', ampu).alasan, 'tugas belajar');
  assert.equal(hitungTS([tb], '2027/2028', ampu).ndtps, 1);
});

// LKPS 4.a/4.c, LED, rincian butir (pemilik 2026-11-22): dosenTS = aturan yang sama dengan Kelola dosen dan Skor.
test('dosenTS: DT not teaching on TS and study leave are out of 4.a; staff never', async () => {
  const { dosenTS } = await import('../../site/dosen-hitung.js');
  const { petaDaftar } = await import('../../site/lkps.js');
  const ds = [
    { id: 'a', nama: 'Adi', nidn: '1', kategori: 'tetap', dtps: true, aktif: true, peran: 'dosen' },
    { id: 'r', nama: 'Ari', nidn: '2', kategori: 'tetap', dtps: false, aktif: true, peran: 'pimpinan' },
    { id: 't', nama: 'Tina', nidn: '3', kategori: 'tetap', dtps: false, aktif: true, peran: 'dosen', tugas_belajar: 'S3', tugas_belajar_mulai: '2024-01-01' },
    { id: 's', nama: 'Staf', nidn: 'STAF-1', kategori: null, dtps: false, aktif: true, peran: 'admin' },
  ];
  const ampu = { kelas: [{ id: 1, tahun_akademik: '2025/2026' }], kd: [{ kelas_id: 1, dosen_id: 'a' }], manual: [] };
  const h = dosenTS(ds, '2025/2026', ampuPerTA(ampu));
  assert.deepEqual([h.dtps.map(d => d.id), h.hitung.map(d => d.id)], [['a'], ['a']]);
  // TS lain tanpa data mengampu: pengaman, Ari dihitung DT; Tina tetap tugas belajar
  assert.deepEqual(dosenTS(ds, '2024/2025', ampuPerTA(ampu)).hitung.map(d => d.id), ['a', 'r']);
  const L = petaDaftar({ ts: 2026, prodi: 'Uji', D: { akreditasi: {} }, daftar: { dosen: ds, ampu } });
  assert.deepEqual([L['4a'].B14, L['4a'].B15], ['Adi', undefined]);
});
