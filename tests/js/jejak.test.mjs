// Audit log page helpers (owner 2026-11-12).
import test from 'node:test';
import assert from 'node:assert/strict';
import { labelTabel, tampilNilai, rincianUbah, judulBaris, idTerkait } from '../../site/jejak.js';

test('table labels: known names, lkps_/ref_ derived, unknown humanised', () => {
  assert.equal(labelTabel('karya_penulis'), 'Penulis karya');
  assert.equal(labelTabel('lkps_tracer_lulusan'), 'LKPS: tracer lulusan');
  assert.equal(labelTabel('ref_skema_dana'), 'Referensi: skema dana');
  assert.equal(labelTabel('tabel_baru'), 'tabel baru');
});

test('values: empty as dash, long text and JSON cut', () => {
  assert.equal(tampilNilai(null), '—');
  assert.equal(tampilNilai(''), '—');
  assert.equal(tampilNilai(0), '0');
  assert.equal(tampilNilai(false), 'false');
  assert.equal(tampilNilai('x'.repeat(100), 10), 'xxxxxxxxx…');
  assert.equal(tampilNilai({ a: [1, 2] }), '{"a":[1,2]}');
});

test('changed columns sorted with old and new values', () => {
  assert.deepEqual(rincianUbah({ status: ['diajukan', 'terverifikasi'], catatan: [null, 'ok'] }),
    [{ kolom: 'catatan', lama: null, baru: 'ok' }, { kolom: 'status', lama: 'diajukan', baru: 'terverifikasi' }]);
  assert.deepEqual(rincianUbah(null), []);
});

test('row titles from the row itself or from looked-up works and lecturers', () => {
  const nama = { karya: new Map([['k1', 'Banjir Jakarta']]), dosen: new Map([['d1', 'Ani']]) };
  assert.equal(judulBaris({ tabel: 'karya', baris: 'k1', aksi: 'ubah' }, nama), 'Banjir Jakarta');
  assert.equal(judulBaris({ tabel: 'karya', baris: 'k9', aksi: 'hapus', isi: { judul: 'Dihapus' } }, nama), 'Dihapus');
  assert.equal(judulBaris({ tabel: 'dosen', baris: 'd1', aksi: 'ubah' }, nama), 'Ani');
  assert.equal(judulBaris({ tabel: 'karya_penulis', baris: 'k1|d1', aksi: 'ubah' }, nama), 'karya: Banjir Jakarta · dosen: Ani');
  assert.equal(judulBaris({ tabel: 'karya_bukti', baris: '5', aksi: 'tambah', isi: { karya_id: 'k1', keterangan: 'SK' } }, nama), 'SK · karya: Banjir Jakarta');
  assert.equal(judulBaris({ tabel: 'pengaturan', baris: 'bop', aksi: 'ubah' }, nama), '');
});

test('ids to look up from one page of log rows', () => {
  const r = idTerkait([{ tabel: 'karya', baris: 'k1' }, { tabel: 'dosen', baris: 'd1' }, { tabel: 'karya_penulis', baris: 'k2|d2' },
    { tabel: 'karya_bukti', baris: '7', isi: { karya_id: 'k3' } }, { tabel: 'pengaturan', baris: 'bop' }]);
  assert.deepEqual(r, { karya: ['k1', 'k2', 'k3'], dosen: ['d1', 'd2'] });
});
