// Judul tab ruang kerja (pemilik 2026-11-19): "<halaman> — Ruang kerja <prodi>"; tidak berlipat bila dipasang dua kali.
import test from 'node:test';
import assert from 'node:assert/strict';
globalThis.document ??= { querySelector: () => null, querySelectorAll: () => [], title: '' };
const { judulRuangKerja } = await import('../../site/menu.js');

test('judulRuangKerja: halaman biasa, halaman Ruang kerja, dan pemasangan kedua', () => {
  assert.equal(judulRuangKerja('Skor akreditasi dan LED', 'Teknik Contoh'), 'Skor akreditasi dan LED — Ruang kerja Teknik Contoh');
  assert.equal(judulRuangKerja('Ruang kerja', 'Teknik Contoh'), 'Ruang kerja Teknik Contoh');
  assert.equal(judulRuangKerja('Ruang kerja Teknik Contoh', 'Teknik Contoh'), 'Ruang kerja Teknik Contoh');
  assert.equal(judulRuangKerja('Karya dosen', ''), 'Karya dosen — Ruang kerja');
});
