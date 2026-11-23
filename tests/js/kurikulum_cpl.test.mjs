// CPL per kurikulum, peta MK-CPL, korelasi (owner 2026-11-13; instal-lengkap.sql).
import test from 'node:test';
import assert from 'node:assert/strict';
import { bacaCSV, normKur, normCpl, rencanaImpor, porsiMK, sebaranCPL, htmlSebaran, trenLintas, htmlTrenLintas }
  from '../../site/kurikulum-cpl.js';
import { htmlCPL } from '../../site/capaian-cpl.js';

const MK = [{ kurikulum: 'K21', kode: '41405', nama: 'Tugas Akhir', sks: 4, sifat: 'wajib' },
  { kurikulum: 'K21', kode: '41101', nama: 'Matematika Lanjut', sks: 3, sifat: 'wajib' },
  { kurikulum: 'K26', kode: '01207', nama: 'Bahasa Inggris 1', sks: 2, sifat: 'wajib' },
  { kurikulum: 'K26', kode: '41101', nama: 'Kalkulus', sks: 3, sifat: 'wajib' }];
const CPL = [{ kurikulum: 'K21', kode: 'a', rumusan: 'karakter' }, { kurikulum: 'K21', kode: 'j', rumusan: 'masalah' },
  { kurikulum: 'K21', kode: 'd', rumusan: 'kritis' }, { kurikulum: 'K26', kode: 'A', rumusan: 'sikap', urutan: 10 },
  { kurikulum: 'K26', kode: 'E', rumusan: 'masalah rekayasa', urutan: 50 }, { kurikulum: 'K26', kode: 'D', rumusan: 'sains', urutan: 40 }];

test('CSV reader: separator from header, quotes, BOM, blank lines', () => {
  assert.deepEqual(bacaCSV('﻿a;b\r\n"x;1";"he said ""hi"""\r\n\r\n'), [['a', 'b'], ['x;1', 'he said "hi"']]);
  assert.deepEqual(bacaCSV('a,b\n1,"2\n3"'), [['a', 'b'], ['1', '2\n3']]);
});

test('curriculum and CPL code normalisation', () => {
  assert.deepEqual(['K26', 'k 26', '2026', 'Kurikulum 2026', 'K-21'].map(normKur), ['K26', 'K26', 'K26', 'K26', 'K21']);
  assert.equal(normKur('lama'), 'LAMA');
  assert.deepEqual(['CPL-A', 'cpl a', 'a', ' CPL_10 '].map(normCpl), ['A', 'a', 'a', '10']);
});

test('CPL import: new rows need rumusan, blank cells keep old values, order from row position', () => {
  const r = rencanaImpor('cpl', bacaCSV('kurikulum;kode;rumusan;ranah\nK26;CPL-B;baru;Sikap\nK26;A;;\n2026;C;x;\nK2;Z;x;\nK26;Q;;\nK26;B;lagi;'),
    { cpl: CPL });
  assert.deepEqual(r.sah.map(x => [x.isi.kode, x.baru, x.isi.urutan]), [['B', true, 10], ['A', false, undefined], ['C', true, 30]]);
  assert.equal('rumusan' in r.sah[1].isi, false);
  assert.deepEqual(r.salah.map(x => x.baris), [5, 6, 7]);
  assert.match(r.salah[1].galat[0], /rumusan kosong/);
  assert.match(r.salah[2].galat.join(), /ganda/);
  assert.match(rencanaImpor('cpl', bacaCSV('kode;rumusan\nA;x'), {}).galat, /kurikulum/);
});

test('MK-CPL map import: long form, unknown MK/CPL, weights, MK-level replace', () => {
  const peta = [{ id: 1, kurikulum: 'K21', kode_mk: '41405', cpl: 'a' }, { id: 2, kurikulum: 'K21', kode_mk: '41405', cpl: 'j' },
    { id: 3, kurikulum: 'K21', kode_mk: '41101', cpl: 'd' }];
  const r = rencanaImpor('peta', bacaCSV('kurikulum;kode_mk;cpl;indikator;bobot\nK21;41405;j;j-1, j-2;2\nK21;41405;d;;\n'
    + 'K21;99999;j;;\nK26;41101;j;;\nK21;41405;d;;0'), { mk: MK, cpl: CPL, peta });
  assert.deepEqual(r.sah.map(x => [x.isi.cpl, x.isi.indikator, x.isi.bobot, x.baru]), [['j', 'j-1, j-2', 2, false], ['d', null, null, true]]);
  assert.deepEqual(r.salah.map(x => x.baris), [4, 5, 6]);
  assert.match(r.salah[0].galat.join(), /MK 99999 tidak ada di kurikulum K21/);
  assert.match(r.salah[1].galat.join(), /CPL j tidak ada di kurikulum K26/);
  assert.match(r.salah[2].galat.join(), /ganda|bobot/);
  assert.deepEqual(r.hapus, [1], 'old pair a of 41405 removed; 41101 untouched');
});

test('MK-CPL map import: matrix form from the draft workbook', () => {
  const r = rencanaImpor('peta', bacaCSV('kurikulum;kode;nama;sks;CPL A;CPL D;CPL E;catatan\nK26;01207;Bahasa Inggris 1;2;v;;;\n'
    + 'K26;41101;Kalkulus;3;;v;(baris CPL);x'), { mk: MK, cpl: CPL, peta: [] });
  assert.equal(r.galat, '');
  assert.deepEqual(r.sah.map(x => `${x.isi.kode_mk}:${x.isi.cpl}:${x.isi.indikator}`), ['01207:A:null', '41101:D:null', '41101:E:null']);
  assert.deepEqual(r.asing, []);
  assert.equal('bobot' in r.sah[0].isi, false, 'no bobot column = weights untouched');
  const k21 = rencanaImpor('peta', bacaCSV('kurikulum;kode;CPL-j;CPL-d\nK21;41405;"j-1, j-2";d-1'), { mk: MK, cpl: CPL, peta: [] });
  assert.deepEqual(k21.sah.map(x => x.isi.indikator), ['j-1, j-2', 'd-1']);
});

test('correlation import: levels, status default, same-curriculum and unknown CPL rejected', () => {
  const r = rencanaImpor('korelasi', bacaCSV('kurikulum_asal;cpl_asal;kurikulum_tujuan;cpl_tujuan;tingkat;alasan;jumlah_mk_pendukung;mk_pendukung;status\n'
    + 'K21;a;K26;A;setara;sama;3;x;disetujui\nK21;j;K26;E;Sebagian;;;;\nK21;a;K21;j;setara;;;;\nK21;z;K26;A;setara;;;;\nK21;d;K26;D;mirip;;;;'),
    { cpl: CPL, korelasi: [] });
  assert.deepEqual(r.sah.map(x => [x.isi.cpl_asal, x.isi.tingkat, x.isi.status]), [['a', 'setara', 'disetujui'], ['j', 'sebagian', 'usulan']]);
  assert.deepEqual(r.asing, []);
  assert.deepEqual(r.salah.map(x => x.galat.join()).map(g => /berbeda/.test(g) || /tidak ada/.test(g) || /tingkat/.test(g)), [true, true, true]);
});

test('shares: equal by default, weighted when bobot is filled', () => {
  const p = porsiMK([{ kurikulum: 'K21', kode_mk: '41405', cpl: 'j', bobot: 2 }, { kurikulum: 'K21', kode_mk: '41405', cpl: 'd', bobot: 1 },
    { kurikulum: 'K26', kode_mk: '41101', cpl: 'D' }, { kurikulum: 'K26', kode_mk: '41101', cpl: 'E' }]);
  assert.deepEqual(p.get('K21|41405').map(x => +x.porsi.toFixed(3)), [0.667, 0.333]);
  assert.deepEqual(p.get('K26|41101').map(x => x.porsi), [0.5, 0.5]);
});

test('sebaran per curriculum: MK count, SKS equivalent, gaps', () => {
  const s = sebaranCPL(MK, CPL, [{ kurikulum: 'K26', kode_mk: '41101', cpl: 'D' }, { kurikulum: 'K26', kode_mk: '41101', cpl: 'E' },
    { kurikulum: 'K26', kode_mk: '01207', cpl: 'A' }]);
  assert.deepEqual(s.map(x => x.kurikulum), ['K26', 'K21']);
  const k26 = s[0];
  assert.deepEqual(k26.cpl.map(c => [c.kode, c.mk, c.sks]), [['A', 1, 2], ['D', 1, 1.5], ['E', 1, 1.5]]);
  assert.equal(k26.cpl[0].persen, 0.4);
  assert.deepEqual(s[1].cplTanpaMk, ['a', 'd', 'j']);
  assert.equal(s[1].mkTanpaCpl.length, 2);
  const h = htmlSebaran(s);
  assert.match(h, /K26: 2 dari 2 MK terpetakan/);
  assert.match(h, /CPL tanpa MK: a, d, j/);
  assert.match(htmlSebaran([]), /Belum ada CPL/);
});

const RING = { versi: 1, ambang: { individu: 45, kelas_persen: 60 }, cpl: [], berkas: [], kelas: [], kumulatif: [],
  progres: [{ curriculum: 'K21', cpl: 'CPL-a', term: '2024/2025 Genap', term_order: 20242, share_achieved: 0.7, status: 'TERCAPAI' },
    { curriculum: 'Kurikulum 2021', cpl: 'j', term: '2024/2025 Genap', term_order: 20242, share_achieved: 0.5, status: 'BELUM' },
    { curriculum: 'K26', cpl: 'CPL-A', term: '2026/2027 Ganjil', term_order: 20261, share_achieved: 0.8, status: 'TERCAPAI' }] };
const KOR = [{ kurikulum_asal: 'K21', cpl_asal: 'a', kurikulum_tujuan: 'K26', cpl_tujuan: 'A', tingkat: 'setara', status: 'disetujui' },
  { kurikulum_asal: 'K21', cpl_asal: 'j', kurikulum_tujuan: 'K26', cpl_tujuan: 'A', tingkat: 'sebagian', status: 'usulan' },
  { kurikulum_asal: 'K21', cpl_asal: 'd', kurikulum_tujuan: 'K26', cpl_tujuan: 'D', tingkat: 'setara', status: 'usulan' }];

test('cross-curriculum trend: target first, then setara, then sebagian; groups without data dropped', () => {
  const t = trenLintas(RING, KOR);
  assert.deepEqual(t.terms.map(x => x[1]), ['2024/2025 Genap', '2026/2027 Ganjil']);
  assert.equal(t.kelompok.length, 1, 'D has no data in any term');
  assert.deepEqual(t.kelompok[0].baris.map(b => `${b.kurikulum}${b.cpl}:${b.tingkat}:${b.nilai.size}`),
    ['K26A:ini:1', 'K21a:setara:1', 'K21j:sebagian:1']);
  const h = htmlTrenLintas(RING, KOR);
  assert.match(h, /Tren lintas kurikulum/);
  assert.match(h, /sebagian\*/);
  assert.match(h, /70%/);
  assert.equal(htmlTrenLintas(RING, []), '');
});

test('htmlCPL shows the trend only when correlations are given', () => {
  assert.doesNotMatch(htmlCPL(RING), /Tren lintas/);
  assert.match(htmlCPL(RING, { korelasi: KOR }), /Tren lintas kurikulum/);
});
