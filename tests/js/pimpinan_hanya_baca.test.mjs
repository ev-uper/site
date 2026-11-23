// Pimpinan bukan DTPS = hanya-baca (instal-lengkap.sql, pemilik 2026-11-22): menu hanya halaman pantauan;
// Dekan aktif juga RPS dan ekuivalensi (penetapan); pimpinan DTPS seperti dosen biasa.
import test from 'node:test';
import assert from 'node:assert/strict';

globalThis.document ??= { querySelector: () => null, querySelectorAll: () => [], title: '' };   // menu.js memasang judul halaman
const { hanyaBaca, halamanBoleh, bolehBuka } = await import('../../site/menu.js');
const daftar = s => [...new Set(halamanBoleh(s).flatMap(m => m.halaman.map(h => h.href.split(/[?#]/)[0])))].sort();

test('leader who is not DTPS sees monitoring pages only', () => {
  const dekan = { peran: 'pimpinan', dtps: false, aktif: true, koordinator: [] };
  assert.equal(hanyaBaca(dekan), true);
  assert.deepEqual(daftar(dekan), ['dasbor.html', 'grafik.html', 'hasil-survei.html', 'kalender.html', 'monitoring.html', 'panduan.html', 'skor.html']);
  assert.equal(bolehBuka(dekan, 'karya.html'), false);
  assert.equal(bolehBuka(dekan, 'profil.html'), false);
});

test('active dean also gets the RPS and equivalence approval pages', () => {
  const dekan = { peran: 'pimpinan', dtps: false, aktif: true, koordinator: ['dekan'] };
  assert.ok(daftar(dekan).includes('rps.html') && daftar(dekan).includes('ekuivalensi.html'));
  assert.equal(bolehBuka(dekan, 'karya.html'), false);
});

test('leader who is DTPS, lecturers and admins are not read-only', () => {
  assert.equal(hanyaBaca({ peran: 'pimpinan', dtps: true }), false);
  assert.equal(hanyaBaca({ peran: 'pimpinan', dtps: 'ya' }), false);
  assert.equal(hanyaBaca({ peran: 'dosen', dtps: false }), false);
  assert.equal(bolehBuka({ peran: 'pimpinan', dtps: true, aktif: true, koordinator: [] }, 'karya.html'), true);
});
