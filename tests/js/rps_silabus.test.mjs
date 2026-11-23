// Bagian C RPS dari silabus MK (instal-lengkap.sql, pemilik 2026-11-20).
import test from 'node:test';
import assert from 'node:assert/strict';
import { rpsDariSilabus, kodePustaka, rpsKosong } from '../../site/rps.js';

const SIL = { tujuan: 'Mahasiswa mampu menganalisis hidrologi.', deskripsi: 'Siklus hidrologi. Pokok bahasan: 1. Hujan 2. Limpasan',
  prasyarat: '41310 Mekanika Fluida', bersamaan: '', pustaka: '1. Chow, V.T. (1988). Applied Hydrology.\n2. Linsley, R.K. Hydrology for Engineers\nModul Praktikum Hidrologi' };

test('rpsDariSilabus fills part C from the syllabus and keeps the rest of the RPS', () => {
  const R0 = { ...rpsKosong({ kode: '41317', nama: 'Hidrologi', sks: 3, semester: 4 }), pengampu: 'Dosen A', pustaka: [{ kode: 'LAMA', teks: 'x' }] };
  const R = rpsDariSilabus(R0, SIL);
  assert.equal(R.tujuan, SIL.tujuan); assert.equal(R.deskripsi, SIL.deskripsi);
  assert.deepEqual(R.syarat, { prasyarat: '41310 Mekanika Fluida', bersamaan: '' });
  assert.deepEqual(R.pustaka, [{ kode: 'CHOW', teks: 'Chow, V.T. (1988). Applied Hydrology.' },
    { kode: 'LINSLE', teks: 'Linsley, R.K. Hydrology for Engineers' }, { kode: 'P3', teks: 'Modul Praktikum Hidrologi' }]);
  assert.equal(R.pengampu, 'Dosen A'); assert.deepEqual(R.pekan, R0.pekan); assert.equal(R.kriteria, R0.kriteria);
  assert.equal(rpsDariSilabus(R0, null), R0);
  assert.deepEqual(rpsDariSilabus(R0, { ...SIL, pustaka: '' }).pustaka, R0.pustaka);   // pustaka silabus kosong: pustaka RPS tetap
});

test('kodePustaka: first author, clashes numbered, no author -> P<n>', () => {
  assert.deepEqual(kodePustaka(['Das, B. M. Principles', 'Das, B. M. Advanced', 'The Code of Practice', '2. SNI 2847:2019', '']),
    ['DAS', 'DAS2', 'P3', 'SNI', 'P5']);
});
