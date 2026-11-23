// Peringatan sebelum menghapus/melepas/mengganti foto prestasi yang tampil di situs (pemilik 2026-11-21).
import test from 'node:test';
import assert from 'node:assert/strict';
import { fotoPrestasiPublik, PERINGATAN_FOTO } from '../../site/hapus-berkas.js';

const T = 'lkps_prestasi_mahasiswa', FOTO = { id: 3, jenis: 'foto' };

test('hanya foto kegiatan pada prestasi mahasiswa terverifikasi yang tidak disembunyikan', () => {
  assert.equal(fotoPrestasiPublik(T, { status: 'terverifikasi' }, FOTO), true);
  assert.equal(fotoPrestasiPublik(T, {}, FOTO), true);                                      // status kosong = terverifikasi (sama dengan bangun)
  assert.equal(fotoPrestasiPublik(T, { status: 'diajukan' }, FOTO), false);
  assert.equal(fotoPrestasiPublik(T, { status: 'terverifikasi', sembunyikan_publik: true }, FOTO), false);
  assert.equal(fotoPrestasiPublik(T, { status: 'terverifikasi' }, { id: 4, jenis: 'sertifikat' }), false);
  assert.equal(fotoPrestasiPublik('lkps_publikasi_mahasiswa', { status: 'terverifikasi' }, FOTO), false);
  assert.equal(fotoPrestasiPublik(T, { status: 'terverifikasi' }, undefined), false);
  assert.match(PERINGATAN_FOTO, /halaman publik Prestasi/);
});
