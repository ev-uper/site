// "MK saya" di Mata kuliah saya (pemilik 2026-11-21).
import test from 'node:test';
import assert from 'node:assert/strict';
import { peninjauMK, bawaanHanyaSaya, mkMilikSaya, pesanKosongSaya, kelasMengajarSaya, kunciKelasSaya } from '../../site/mk-saya.js';

const DOSEN = { peran: 'dosen', nidn: '0011', koordinator: [] };

test('peninjau melihat semua MK; dosen bawaannya MK saya; pilihan tersimpan menang', () => {
  assert.equal(peninjauMK(DOSEN), false);
  for (const s of [{ peran: 'admin' }, { peran: 'pimpinan' }, { peran: 'asesor' }, { peran: 'dosen', koordinator: ['kaprodi'] },
                   { peran: 'dosen', koordinator: ['dekan'] }, { peran: 'dosen', koordinator: ['gkm'] }]) assert.equal(peninjauMK(s), true, JSON.stringify(s));
  assert.equal(peninjauMK({ peran: 'dosen', koordinator: ['koordinator_ta'] }), false);
  assert.equal(bawaanHanyaSaya('rps', DOSEN, undefined), true);       // tanpa localStorage (Node): bawaan
  assert.equal(bawaanHanyaSaya('rps', { peran: 'admin' }, undefined), false);
  assert.equal(bawaanHanyaSaya('rps', DOSEN, '0'), false);            // dosen memilih semua MK
  assert.equal(bawaanHanyaSaya('rps', { peran: 'admin' }, '1'), true);
});

test('MK saya = pengampu memuat NIDN + mk_boleh_saya (kecuali admin/GKM yang mendapat semua MK)', () => {
  const MK = [{ kurikulum: 'K26', kode: 'A', pengampu: ['0011'] }, { kurikulum: 'K26', kode: 'B', pengampu: ['0099'] },
              { kurikulum: 'K26', kode: 'C', pengampu: null }, { kurikulum: 'K21', kode: 'A', pengampu: [11] }];
  const boleh = [{ kurikulum: 'K26', kode_mk: 'C' }];                 // mengajar kelas C semester terakhir
  assert.deepEqual([...mkMilikSaya(MK, boleh, DOSEN)].sort(), ['K26|A', 'K26|C']);
  const semua = MK.map(m => ({ kurikulum: m.kurikulum, kode_mk: m.kode }));
  assert.deepEqual([...mkMilikSaya(MK, semua, { peran: 'admin', nidn: '0099' })], ['K26|B']);   // admin: hanya yang ia ampu
  assert.deepEqual([...mkMilikSaya(MK, semua, { peran: 'dosen', nidn: '7', koordinator: ['gkm'] })], []);
  assert.deepEqual([...mkMilikSaya(MK, [], { peran: 'dosen', nidn: '11' })], ['K21|A']);       // NIDN angka vs teks
  assert.deepEqual([...mkMilikSaya(MK, boleh, DOSEN, (k, c) => `${k}/${c}`)].sort(), ['K26/A', 'K26/C']);
});

test('pesan kosong hanya bila ada MK lain', () => {
  assert.equal(pesanKosongSaya(0), '');
  assert.match(pesanKosongSaya(12), /Hanya MK saya/);
});

test('137: kelasMengajarSaya (dua kueri) dan kunciKelasSaya', async () => {
  const data = { kelas_dosen: [{ kelas_id: 7, dosen_id: 'd1', peran: 'anggota' }, { kelas_id: 8, dosen_id: 'd2', peran: 'koordinator' }],
    kelas_kuliah: [{ id: 7, tahun_akademik: '2026/2027', semester: 'Genap', kurikulum: 'K26', kode_mk: '41315', kelas: 'B' },
                   { id: 8, tahun_akademik: '2026/2027', semester: 'Genap', kurikulum: 'K26', kode_mk: '41316', kelas: 'A' }] };
  const q = t => { let xs = data[t]; const o = { select: () => o, eq: (k, v) => { xs = xs.filter(r => r[k] === v); return o; },
    in: (k, vs) => { xs = xs.filter(r => vs.includes(r[k])); return o; }, then: (f, g) => Promise.resolve({ data: xs, error: null }).then(f, g) }; return o; };
  const sb = { from: q };
  const tim = await kelasMengajarSaya(sb, { id: 'd1' });
  assert.deepEqual(tim, [{ tahun_akademik: '2026/2027', semester: 'Genap', kurikulum: 'K26', kode_mk: '41315', kelas: 'B', peran: 'anggota' }]);
  assert.deepEqual(await kelasMengajarSaya(sb, { id: 'zz' }), []);
  assert.deepEqual(await kelasMengajarSaya({ from: () => { throw new Error('belum ada tabel'); } }, { id: 'd1' }), []);
  assert.deepEqual([...kunciKelasSaya(tim)], ['2026/2027|Genap|41315|B']);
});
