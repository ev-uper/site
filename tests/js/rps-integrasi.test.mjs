// Isi RPS untuk akreditasi (pemilik 2026-11-19): LKPS 3.a.3 "Sudah tercantum di RPS" dari RPS disahkan, kecocokan, rekap SCL/integrasi.
import test from 'node:test';
import assert from 'node:assert/strict';
import { integrasiDisahkan, cocokIntegrasi, kunciIntegrasi, rekapPembelajaran, teksLedPembelajaran } from '../../site/rps-integrasi.js';
import { petaDaftar } from '../../site/lkps.js';

const mk = [{ kurikulum: 'K26', kode: 'A1', nama: 'Hidrologi', aktif: true }, { kurikulum: 'K26', kode: 'A2', nama: 'Statika', aktif: true },
  { kurikulum: 'K26', kode: 'A3', nama: 'Beton', aktif: true }];
const sahA1 = { rps: { integrasi: { ada: true, karya: [{ id: 'p1', judul: 'Banjir', kategori: 'penelitian', bentuk: 'studi_kasus' }] },
  pekan: [{ scl: ['case'] }, { scl: ['pbl', 'case'] }] } };
const sahA2 = { rps: { integrasi: { ada: false, karya: [] }, scl: { ada: true }, pekan: [] } };
const rpsRows = [{ kurikulum: 'K26', kode_mk: 'A1', sah: sahA1 }, { kurikulum: 'K26', kode_mk: 'A2', sah: sahA2 },
  { kurikulum: 'K26', kode_mk: 'A3', integ: { ada: true, karya: [{ id: 'p2', judul: 'Jembatan', bentuk: 'bahan_kajian' }] }, ref_mata_kuliah: { nama: 'Beton' } }];

test('integrasi dari RPS disahkan; nama MK dari relasi atau daftar MK', () => {
  assert.deepEqual(integrasiDisahkan(rpsRows, mk).map(x => [x.kode_mk, x.nama_mk, x.induk, x.bentuk]),
    [['A1', 'Hidrologi', 'p1', 'studi_kasus'], ['A3', 'Beton', 'p2', 'bahan_kajian']]);
  assert.equal(kunciIntegrasi('p1', ' Hidrologi '), 'p1|hidrologi');
});

test('kecocokan dengan catatan karya integrasi (ditolak diabaikan)', () => {
  const karya = [{ kategori: 'integrasi', induk_id: 'p1', mata_kuliah: 'hidrologi', status: 'diajukan', judul: 'Banjir' },
    { kategori: 'integrasi', induk_id: 'p9', mata_kuliah: 'Statika', status: 'terverifikasi', judul: 'Lain' },
    { kategori: 'integrasi', induk_id: 'p2', mata_kuliah: 'Beton', status: 'ditolak', judul: 'Jembatan' }];
  const C = cocokIntegrasi({ rps: rpsRows, mk, karya });
  assert.deepEqual(C.belumDicatat.map(x => x.kode_mk), ['A3']);   // p2 hanya ada karya ditolak
  assert.deepEqual(C.tidakDiRps.map(k => k.induk_id), ['p9']);
});

test('rekap SCL/integrasi prodi dan kalimat LED', () => {
  const rps = new Map(rpsRows.filter(r => r.sah).map(r => [`${r.kurikulum}|${r.kode_mk}`, r]));
  const R = rekapPembelajaran({ mk, rps, kur: 'K26' });
  assert.deepEqual({ aktif: R.aktif, disahkan: R.disahkan, integrasi: R.integrasi, scl: R.scl, pScl: R.pScl }, { aktif: 3, disahkan: 2, integrasi: 1, scl: 2, pScl: 100 });
  assert.deepEqual(R.metode, [{ label: 'Case Method', jumlah: 1 }, { label: 'Problem Based Learning', jumlah: 1 }]);
  assert.match(teksLedPembelajaran(R, 'K26'), /^Dari 2 mata kuliah kurikulum K26 .* 2 mata kuliah \(100%\) menerapkan .* 1 mata kuliah \(50%\) mengintegrasikan .* sebagai studi kasus \(1 MK\)\.$/);
});

test('LKPS 3.a.3 kolom K: otomatis "V" bila RPS disahkan memuatnya, walau dosen belum mencentang', () => {
  const daftar = { karya: [
    { id: 'p1', status: 'terverifikasi', kategori: 'penelitian', judul: 'Banjir', tahun: 2025, bulan: 3, karya_penulis: [] },
    { status: 'terverifikasi', kategori: 'integrasi', judul: 'Banjir', tahun: 2026, bulan: 2, mata_kuliah: 'Hidrologi', sub_jenis: 'studi_kasus',
      induk_id: 'p1', sesuai_rps: false, karya_penulis: [{ peran: 'ketua', dosen: { nama: 'Adi' } }] },
    { status: 'terverifikasi', kategori: 'integrasi', judul: 'Lain', tahun: 2026, bulan: 2, mata_kuliah: 'Statika', sub_jenis: 'studi_kasus',
      induk_id: 'p9', sesuai_rps: false, karya_penulis: [{ peran: 'ketua', dosen: { nama: 'Adi' } }] }],
    integrasiRps: [kunciIntegrasi('p1', 'Hidrologi')] };
  const L = petaDaftar({ ts: 2026, daftar });
  const baris = [13, 14].map(r => [L['3a3'][`D${r}`], L['3a3'][`K${r}`]]);
  assert.deepEqual(baris.sort(), [['Hidrologi', 'V'], ['Statika', undefined]]);
});
