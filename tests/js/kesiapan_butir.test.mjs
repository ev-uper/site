// Kesiapan akreditasi per butir (pemilik 2026-11-21): site/kesiapan-butir.js.
import test from 'node:test';
import assert from 'node:assert/strict';
import { pecahPJ, saringKesiapan, ringkasPJ, csvKesiapan, TANPA_PJ } from '../../site/kesiapan-butir.js';
import { pihakButir } from '../../site/unsur-butir.js';

const B = [
  { no: '1', judul: 'VMTS', bobot: 1.5, skor: 4, status: 'lengkap', pj: ['UPPS', 'Universitas'], tertaut: 5, dianjurkan: 5, unsur: { ada: 4, n: 4 }, karya: null },
  { no: '2', judul: 'Keterlibatan; pemangku "kepentingan"', bobot: 1, skor: null, status: 'kosong', pj: ['UPPS'], tertaut: 0, dianjurkan: 5, unsur: null, karya: null },
  { no: '33', judul: 'Publikasi', bobot: 2.25, skor: 3.5, status: 'sebagian', pj: ['Dosen'], tertaut: 1, dianjurkan: 2, unsur: null, karya: { ada: 3, n: 7 } },
  { no: '99', judul: 'Tanpa PJ', bobot: 0.5, skor: 0, status: 'kosong', pj: [], tertaut: 0, dianjurkan: 0, unsur: null, karya: null },
];

test('pecah PJ dari teks pihakButir', () => {
  assert.deepEqual(pecahPJ('UPPS, Universitas'), ['UPPS', 'Universitas']);
  assert.deepEqual(pecahPJ(''), []);
  assert.deepEqual(pecahPJ(pihakButir('1')), ['Universitas', 'UPPS', 'Prodi']);   // urutan PIHAK
});

test('saring per PJ dan status; butir tanpa PJ', () => {
  assert.deepEqual(saringKesiapan(B, { pj: 'UPPS' }).map(x => x.no), ['1', '2']);
  assert.deepEqual(saringKesiapan(B, { pj: 'UPPS', status: 'kosong' }).map(x => x.no), ['2']);
  assert.deepEqual(saringKesiapan(B, { status: 'kosong' }).map(x => x.no), ['2', '99']);
  assert.deepEqual(saringKesiapan(B, { pj: TANPA_PJ }).map(x => x.no), ['99']);
  assert.equal(saringKesiapan(B).length, 4);
});

test('ringkasan per PJ: urut PIHAK, bobot belum lengkap, pihak kosong dibuang', () => {
  assert.deepEqual(ringkasPJ(B), [
    { pj: 'Universitas', n: 1, lengkap: 1, sebagian: 0, kosong: 0, bobotBelum: 0 },
    { pj: 'UPPS', n: 2, lengkap: 1, sebagian: 0, kosong: 1, bobotBelum: 1 },
    { pj: 'Dosen', n: 1, lengkap: 0, sebagian: 1, kosong: 0, bobotBelum: 2.25 },
    { pj: TANPA_PJ, n: 1, lengkap: 0, sebagian: 0, kosong: 1, bobotBelum: 0.5 },
  ]);
});

test('CSV: kepala, koma desimal, kutip untuk ; dan ", tautan kartu', () => {
  const t = csvKesiapan(B, { ts: 2026, dasar: 'https://contoh/cv-site/' }).split('\r\n');
  assert.equal(t[0], 'butir;judul;bobot;skor;status;penanggung_jawab;bukti_tertaut;bukti_dianjurkan;unsur_berbukti;karya_berbukti;tautan_kartu');
  assert.equal(t[1], '1;VMTS;1,5;4;lengkap;UPPS, Universitas;5;5;4/4;;https://contoh/cv-site/skor.html?ts=2026#butir-1');
  assert.equal(t[2], '2;"Keterlibatan; pemangku ""kepentingan""";1;;kosong;UPPS;0;5;;;https://contoh/cv-site/skor.html?ts=2026#butir-2');
  assert.equal(t[3].split(';')[9], '3/7');
  assert.equal(t[4].split(';')[5], TANPA_PJ);
  assert.equal(t.at(-1), '');
});
