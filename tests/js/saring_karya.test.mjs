// Saringan Karya prodi (pemilik 2026-11-17; site/saring-karya.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { saringKarya, daftarNegara, ADA, TANPA } from '../../site/saring-karya.js';

const K = [
  { id: 1, judul: 'Banjir', tahun: 2026, kategori: 'publikasi', kerjasama_id: 7, karya_penulis: [{ dosen: { nama: 'Ani' } }],
    karya_mitra: [{ institusi: 'Tohoku University', tingkat: 'internasional', negara: 'Japan' }] },
  { id: 2, judul: 'Hujan', tahun: 2025, kategori: 'publikasi', karya_penulis: [{ dosen: { nama: 'Budi' } }],
    karya_mitra: [{ institusi: 'Toyama Prefectural University', tingkat: 'internasional', negara: 'Jepang' },
                  { institusi: 'UTP', tingkat: 'internasional', negara: 'Malaysia' }] },
  { id: 3, judul: 'Desa', tahun: 2025, kategori: 'pkm', karya_mitra: [{ institusi: 'Desa A', tingkat: 'wilayah_lokal', negara: '' }] },
  { id: 4, judul: 'Model', tahun: 2024, kategori: 'penelitian', karya_mitra: [] },
];
const id = xs => xs.map(k => k.id);

test('negara ditulis apa adanya, ejaan berbeda terpisah', () => {
  assert.deepEqual(daftarNegara(K), [['Japan', 1], ['Jepang', 1], ['Malaysia', 1]]);
  assert.deepEqual(id(saringKarya(K, { negara: 'japan' })), [1]);
  assert.deepEqual(id(saringKarya(K, { negara: TANPA })), [3]);
});

test('mitra, kerja sama, kategori, tahun, cari', () => {
  assert.deepEqual(id(saringKarya(K, { tingkat: ADA })), [1, 2, 3]);
  assert.deepEqual(id(saringKarya(K, { tingkat: TANPA })), [4]);
  assert.deepEqual(id(saringKarya(K, { tingkat: 'internasional' })), [1, 2]);
  assert.deepEqual(id(saringKarya(K, { ks: ADA })), [1]);
  assert.deepEqual(id(saringKarya(K, { ks: '7' })), [1]);
  assert.deepEqual(id(saringKarya(K, { ks: TANPA })), [2, 3, 4]);
  assert.deepEqual(id(saringKarya(K, { kategori: 'publikasi', tahun: '2025' })), [2]);
  assert.deepEqual(id(saringKarya(K, { q: 'malaysia' })), [2]);
  assert.deepEqual(id(saringKarya(K, { q: 'budi' })), [2]);
  assert.deepEqual(id(saringKarya(K, {})), [1, 2, 3, 4]);
});
