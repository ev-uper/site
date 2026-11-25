// Koordinator dan tim MK (158, pemilik 2026-11-23).
import test from 'node:test';
import assert from 'node:assert/strict';
import { dosenPilihan, petaStatus, statusMK, peranDi, bebanDosen, usulanPadanan, mkSaya, luarProdi, ringkasKoordinasi } from '../../site/koordinator-mk.js';

const MK = [
  { kurikulum: 'K21', kode: '411', nama: 'Hidrologi', semester: 4, pengampu: ['A', 'B'], koordinator_nidn: 'A', aktif: true },
  { kurikulum: 'K21', kode: '412', nama: 'Hidrolika', semester: 4, pengampu: ['C'], koordinator_nidn: 'C', aktif: true },
  { kurikulum: 'K26', kode: 'CV201', nama: 'Hidrologi Terapan', semester: 3, pengampu: [], koordinator_nidn: null, aktif: true },
  { kurikulum: 'K26', kode: 'CV202', nama: 'Hidrolika', semester: 3, pengampu: ['B', 'D'], koordinator_nidn: 'D', aktif: true },
  { kurikulum: 'K26', kode: 'CV999', nama: 'Lama', semester: 8, pengampu: ['A'], koordinator_nidn: 'A', aktif: false },
];

test('eligible lecturers exclude staff, assessors, inactive and those without NIDN', () => {
  const d = [{ nidn: '1', nama: 'Zed', kategori: 'tetap', dtps: true, aktif: true }, { nidn: '2', nama: 'Ana', kategori: 'tidak_tetap', aktif: true },
    { nidn: 'S1', nama: 'Staf', kategori: null, dtps: false, peran: 'admin', aktif: true }, { nidn: '3', nama: 'Aso', peran: 'asesor', aktif: true },
    { nidn: '4', nama: 'Off', kategori: 'tetap', dtps: true, aktif: false }, { nidn: null, nama: 'Tanpa', kategori: 'tetap', aktif: true }];
  assert.deepEqual(dosenPilihan(d).map(x => x.nama), ['Ana', 'Zed']);
});

test('document status per course: syllabus, CPMK, RPS (set = ditetapkan)', () => {
  const p = petaStatus({ silabus: [{ kurikulum: 'K26', kode_mk: 'CV202', status: 'disahkan' }],
    struktur: [{ kurikulum: 'K26', kode_mk: 'CV202' }], rps: [{ kurikulum: 'K26', kode_mk: 'CV202', status: 'disahkan', tetap_pada: '2026-11-01' },
      { kurikulum: 'K26', kode_mk: 'CV201', status: 'diajukan' }] });
  assert.deepEqual(statusMK(p, MK[3]), { silabus: 'disahkan', cpmk: 'ada', rps: 'ditetapkan' });
  assert.deepEqual(statusMK(p, MK[2]), { silabus: 'belum', cpmk: 'belum', rps: 'diajukan' });
  assert.deepEqual(statusMK(p, MK[0]), { silabus: 'belum', cpmk: 'belum', rps: 'belum' });
});

test('roles and load per lecturer count active courses only', () => {
  assert.equal(peranDi(MK[0], 'A'), 'koordinator');
  assert.equal(peranDi(MK[0], 'B'), 'tim');
  assert.equal(peranDi(MK[0], 'X'), null);
  const b = bebanDosen(MK.filter(m => m.kurikulum === 'K26'));
  assert.deepEqual(Object.fromEntries(b), { B: { koordinator: 0, tim: 1, pic: 0 }, D: { koordinator: 1, tim: 0, pic: 0 } });
});

test('suggestion from the old curriculum through the equivalence table', () => {
  const padanan = [{ kurikulum_lama: 'K21', kode_lama: '411', kurikulum_baru: 'K26', kode_baru: 'CV201' },
    { kurikulum_lama: 'K21', kode_lama: '412', kurikulum_baru: 'K26', kode_baru: 'CV202' }];
  assert.deepEqual(usulanPadanan(MK, padanan, 'K26'), [{ kode: 'CV201', nama: 'Hidrologi Terapan', koordinator: 'A', tim: ['B'], dari: ['411'] }]);
});

test('my courses: coordinator first, active only', () => {
  assert.deepEqual(mkSaya(MK, 'B').map(m => [m.kode, m.peran]), [['CV202', 'tim'], ['411', 'tim']]);
  assert.deepEqual(mkSaya(MK, 'A').map(m => [m.kode, m.peran]), [['411', 'koordinator']]);
});

// MK universitas/fakultas (pemilik 2026-11-24): PIC prodi, tanpa tim; tidak ikut hitungan koordinator dan usulan padanan.
const MKU = [
  { kurikulum: 'K26', kode: '01X01', nama: 'Kalkulus 1', semester: 1, unit_penyelenggara: 'universitas', pengampu: ['A', 'B'], koordinator_nidn: 'A', aktif: true },
  { kurikulum: 'K26', kode: '01102', nama: 'Pancasila', semester: 2, unit_penyelenggara: 'universitas', pengampu: [], koordinator_nidn: null, aktif: true },
  { kurikulum: 'K26', kode: 'F101', nama: 'Pengantar Teknik', semester: 1, unit_penyelenggara: 'fakultas', pengampu: ['B'], koordinator_nidn: 'B', aktif: true },
];

test('university/faculty courses: PIC role only, own counts, no equivalence suggestion', () => {
  assert.equal(luarProdi(MKU[0]), true);
  assert.equal(luarProdi(MKU[2]), true);
  assert.equal(luarProdi(MK[0]), false);
  assert.equal(peranDi(MKU[0], 'A'), 'pic');
  assert.equal(peranDi(MKU[0], 'B'), null);   // sisa pengampu lama tidak dihitung
  const semua = [...MK.filter(m => m.kurikulum === 'K26'), ...MKU];
  assert.deepEqual(ringkasKoordinasi(semua), { prodi: 2, adaKoordinator: 1, luar: 3, adaPic: 2 });
  assert.deepEqual(Object.fromEntries(bebanDosen(MKU)), { A: { koordinator: 0, tim: 0, pic: 1 }, B: { koordinator: 0, tim: 0, pic: 1 } });
  const padanan = [{ kurikulum_lama: 'K21', kode_lama: '411', kurikulum_baru: 'K26', kode_baru: '01102' }];
  assert.deepEqual(usulanPadanan([...MK, ...MKU], padanan, 'K26'), []);
  assert.deepEqual(mkSaya([...MK, ...MKU], 'B').map(m => [m.kode, m.peran]), [['CV202', 'tim'], ['411', 'tim'], ['F101', 'pic']]);
});
