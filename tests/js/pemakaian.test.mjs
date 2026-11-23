// Pemakaian halaman ruang kerja (instal-lengkap.sql, pemilik 2026-11-20).
import test from 'node:test';
import assert from 'node:assert/strict';
import { gabungPemakaian, statusPakai, berkasDari } from '../../site/pemakaian.js';

const MODUL = [
  { judul: 'Mata kuliah saya', halaman: [{ href: 'rps.html', judul: 'RPS' }, { href: 'silabus.html', judul: 'Silabus' }] },
  { judul: 'Pengelolaan', halaman: [{ href: 'data-prodi.html?tab=mk', judul: 'Mata kuliah dan CPL' }, { href: 'data-prodi.html', judul: 'Data prodi' },
    { href: 'hasil-survei.html', judul: 'Hasil survei' }] }];

test('statusPakai and berkasDari', () => {
  assert.equal(statusPakai(null), 'tidak');
  assert.equal(statusPakai({ kunjungan: 2, pengguna: 1 }), 'jarang');
  assert.equal(statusPakai({ kunjungan: 25, pengguna: 1 }), 'aktif');
  assert.equal(statusPakai({ kunjungan: 3, pengguna: 3 }), 'aktif');
  assert.equal(statusPakai(null, true), 'publik');
  assert.equal(berkasDari('monitoring.html#cpl'), 'monitoring.html');
});

test('gabungPemakaian lists unopened menu pages first, merges duplicate menu entries, keeps pages outside the menu', () => {
  const rekap = { halaman: [{ halaman: 'rps.html', kunjungan: 40, pengguna: 6, hari: 10, terakhir: '2026-12-01', peran: { dosen: 6 }, jabatan: {} },
    { halaman: 'data-prodi.html', kunjungan: 2, pengguna: 1, hari: 1, terakhir: '2026-11-25' },
    { halaman: 'ruang-kerja.html', kunjungan: 90, pengguna: 9 }] };
  const g = gabungPemakaian(MODUL, rekap);
  assert.deepEqual(g.menu.map(b => [b.berkas, b.status]), [['silabus.html', 'tidak'], ['data-prodi.html', 'jarang'], ['rps.html', 'aktif'],
    ['hasil-survei.html', 'publik']]);
  assert.deepEqual(g.menu.find(b => b.berkas === 'data-prodi.html').judul, ['Mata kuliah dan CPL', 'Data prodi']);
  assert.deepEqual(g.lain.map(r => r.halaman), ['ruang-kerja.html']);
  assert.deepEqual(g.ringkas, { aktif: 1, jarang: 1, tidak: 1, publik: 1 });
  assert.equal(gabungPemakaian(MODUL, null).ringkas.tidak, 3);
});
