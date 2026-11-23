// Penyusunan kelas (instal-lengkap.sql, pemilik 2026-11-21).
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkDitawarkan, kelasBerikut, usulanKelasAwal, csvKelas, bacaCsvKelas, rekapBeban, csvBeban } from '../../site/kelas.js';

const MK = [
  { kurikulum: 'K26', kode: '41315', nama: 'Mekanika Tanah 1', sks: 2, semester: 4, sifat: 'wajib', pengampu: ['0011'] },
  { kurikulum: 'K26', kode: '41301', nama: 'Geologi Dasar', sks: 2, semester: 3, sifat: 'wajib', pengampu: ['0011', '0012'] },
  { kurikulum: 'K26', kode: '41406', nama: 'Rekayasa Fondasi Lanjut', sks: 3, semester: null, sifat: 'pilihan', pengampu: [] },
  { kurikulum: 'K26', kode: '41399', nama: 'Tidak aktif', sks: 2, semester: 1, sifat: 'wajib', aktif: false },
  { kurikulum: 'K21', kode: '41301', nama: 'Struktur Baja I', sks: 3, semester: 5, sifat: 'wajib', pengampu: ['0012'] },
];
const DOSEN = [{ id: 'a', nidn: '0011', email: 'ani@u.id', nama: 'Ani' }, { id: 'b', nidn: '0012', email: 'budi@u.id', nama: 'Budi' },
               { id: 'c', nidn: null, email: 'luar@u.id', nama: 'Cici' }];

test('MK ditawarkan: paritas semester per kurikulum, pilihan selalu ikut, yang tidak aktif tidak', () => {
  assert.deepEqual(mkDitawarkan(MK, 'K26', 'Ganjil').map(m => [m.kode, m.pilihan]), [['41301', false], ['41406', true]]);
  assert.deepEqual(mkDitawarkan(MK, 'K26', 'Genap').map(m => m.kode), ['41315', '41406']);
  assert.deepEqual(mkDitawarkan(MK, 'K21', 'Ganjil').map(m => m.kode), ['41301']);
});

test('kelasBerikut dan usulan kelas A dari pengampu MK', () => {
  assert.equal(kelasBerikut([]), 'A');
  assert.equal(kelasBerikut(['A', 'b']), 'C');
  assert.equal(kelasBerikut('ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')), 'A2');
  const u = usulanKelasAwal(mkDitawarkan(MK, 'K26', 'Ganjil'), [], DOSEN);
  assert.deepEqual(u.baris, [{ kurikulum: 'K26', kode_mk: '41301', kelas: 'A',
    dosen: [{ dosen_id: 'a', peran: 'koordinator' }, { dosen_id: 'b', peran: 'anggota' }] }]);
  assert.deepEqual(u.tanpaPengampu, ['41406']);
  assert.deepEqual(usulanKelasAwal(mkDitawarkan(MK, 'K26', 'Ganjil'), [{ kurikulum: 'K26', kode_mk: '41301' }], DOSEN).baris, []);
});

test('CSV ekspor lalu impor ulang: team teaching, koordinator dulu, kurikulum ikut', () => {
  const kelas = [{ id: 1, tahun_akademik: '2026/2027', semester: 'Ganjil', kurikulum: 'K26', kode_mk: '41301', kelas: 'A', kapasitas: 40, angkatan: '2025', catatan: 'Lab; ruang besar' },
                 { id: 2, tahun_akademik: '2026/2027', semester: 'Ganjil', kurikulum: 'K21', kode_mk: '41301', kelas: 'A', kapasitas: null }];
  const kd = [{ kelas_id: 1, dosen_id: 'b', peran: 'anggota', urutan: 0, pertemuan: 7 }, { kelas_id: 1, dosen_id: 'a', peran: 'koordinator', urutan: 1, pertemuan: 7 },
              { kelas_id: 1, dosen_id: 'c', peran: 'anggota', urutan: 2 }, { kelas_id: 2, dosen_id: 'b', peran: 'koordinator', urutan: 0 }];
  const csv = csvKelas(kelas, kd, MK, DOSEN), b = csv.split('\r\n');
  assert.equal(b.length, 3);
  assert.equal(b[1], '2026/2027;Ganjil;K21;41301;Struktur Baja I;3;5;wajib;A;;;0012;;Budi;;');
  assert.equal(b[2], '2026/2027;Ganjil;K26;41301;Geologi Dasar;2;3;wajib;A;40;2025;0011;0012|luar@u.id;Ani|Budi|Cici;7|7|;Lab, ruang besar');
  const r = bacaCsvKelas(csv, { mk: MK });
  assert.deepEqual(r.galat, []);
  assert.deepEqual(r.baris[1], { kurikulum: 'K26', kode_mk: '41301', kelas: 'A', kapasitas: 40, angkatan: '2025', catatan: 'Lab, ruang besar',
    dosen: ['0011', '0012', 'luar@u.id'] });
});

test('CSV impor sederhana: kolom dosen, kurikulum bawaan, galat per baris', () => {
  const csv = 'kode_mk;kelas;dosen;kapasitas\n41301;A;0011|0012;45\n41301;B;budi@u.id;\n99999;A;0011;\n41301;A;0012;\n41301;X Y Z 12345;0011;\n41301;C;;\n41301;D;0011;900\n';
  const r = bacaCsvKelas(csv, { mk: MK, kurikulumBawaan: 'K26' });
  assert.deepEqual(r.baris.map(x => [x.kelas, x.dosen.join('|'), x.kapasitas]), [['A', '0011|0012', 45], ['B', 'budi@u.id', null]]);
  assert.equal(r.galat.length, 5);
  assert.match(r.galat[0], /99999 tidak ada di K26/);
  assert.match(r.galat[1], /ganda/);
  assert.match(bacaCsvKelas('kode;nama\n1;2', { mk: MK }).galat[0], /wajib ada/);
  assert.match(bacaCsvKelas('kode_mk;kelas;dosen\n41301;A;0011', { mk: MK }).galat[0], /kurikulum kosong/);
});

test('rekap beban: sks dibagi menurut pertemuan (semua mengisi) atau rata; bimbingan per TS; dosen tanpa beban tetap tampil', () => {
  const kelas = [{ id: 1, kurikulum: 'K26', kode_mk: '41301', kelas: 'A' }, { id: 2, kurikulum: 'K26', kode_mk: '41301', kelas: 'B' },
                 { id: 3, kurikulum: 'K21', kode_mk: '41301', kelas: 'A' }, { id: 4, kurikulum: 'K26', kode_mk: '41315', kelas: 'A' }];
  const kd = [{ kelas_id: 1, dosen_id: 'a', peran: 'koordinator', pertemuan: 10 }, { kelas_id: 1, dosen_id: 'b', peran: 'anggota', pertemuan: 4 },
              { kelas_id: 2, dosen_id: 'a', peran: 'koordinator', pertemuan: 7 }, { kelas_id: 2, dosen_id: 'b', peran: 'anggota' },
              { kelas_id: 3, dosen_id: 'b', peran: 'koordinator' }];                       // kelas 4 belum berdosen: tidak dihitung
  const dosen = [...DOSEN.map(d => ({ ...d, peran: 'dosen' })), { id: 'x', nama: 'Staf', peran: 'admin' }];
  const r = rekapBeban({ kelas, kd, mk: MK, dosen, bimbingan: [{ dosen_id: 'c', nama: 'Cici', kp: 3, ta: 2, uji: 4, lomba: 1 }] });
  const per = Object.fromEntries(r.baris.map(b => [b.nama, b]));
  // a: kelas 1 = 2 sks x 10/14, kelas 2 = 2 sks x 1/2 (b tanpa pertemuan -> rata) = 1,43 + 1 = 2,43.
  assert.equal(per.Ani.sks, 2.43);
  assert.deepEqual([per.Ani.kelas, per.Ani.sks_penuh, per.Ani.tim, per.Ani.mk], [2, 4, 2, ['41301']]);
  // b: 2 x 4/14 + 2 x 1/2 + K21 41301 (3 sks) = 0,57 + 1 + 3 = 4,57.
  assert.equal(per.Budi.sks, 4.57);
  assert.deepEqual([per.Cici.sks, per.Cici.kp, per.Cici.ta, per.Cici.uji, per.Cici.lomba], [0, 3, 2, 4, 1]);
  assert.equal(per.Staf, undefined);                                                 // admin tanpa beban tidak tampil
  assert.deepEqual(r.baris.map(b => b.nama), ['Budi', 'Ani', 'Cici']);
  assert.deepEqual(r.ringkas, { n: 3, rata: 2.33, min: 0, max: 4.57 });
  const csv = csvBeban(r, { ta: '2026/2027', semester: 'Ganjil', ts: 2027 }).split('\r\n');
  assert.equal(csv[0], 'tahun_akademik;semester;dosen;kelas;mk;sks_mengajar;sks_penuh;kelas_team_teaching;kp_ts2027;ta_ts2027;menguji_ts2027;lomba_ts2027');
  assert.equal(csv[1], '2026/2027;Ganjil;Budi;3;41301;4,57;7;2;0;0;0;0');
});
