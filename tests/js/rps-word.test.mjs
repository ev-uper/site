// Word RPS versi disahkan dari rps_dokumen (121, pemilik 2026-11-19): halaman verifikasi tanpa login memakai bahan yang sama.
import test from 'node:test';
import assert from 'node:assert/strict';
import { konteksDokumen, entryPeta } from '../../site/rps-word.js';
import { modelRps, rapikanRps } from '../../site/rps.js';

const mk = { kurikulum: 'K26', kode: '41301', nama: 'Statika', sks: 3, semester: 1 };
const R = rapikanRps(null, mk, {}); R.pengembang = 'd1'; R.tujuan = 'Tujuan';
const D = { mk, rps: { status: 'disahkan', revisi: 2, sah: { rps: R, struktur: { cpmk: [], sub: [{ kode: 'S1', cpmk: 'C1', rumusan: 'x (C2)', cpl: 'A' }], asesmen: [], bobot: {} }, kaprodi_penyusun: true },
    sah_pada: '2026-11-19T03:00:00Z', sah_oleh: 'adm', sah_atas_nama: 'kap', tetap_pada: '2026-11-19T05:00:00Z', tetap_oleh: 'dek', tetap_atas_nama: 'dek',
    kode_verifikasi: '0f8e2c1a-1111-4222-8333-444455556666' },
  log: [{ aksi: 'ajukan', waktu: '2026-11-18T03:00:00Z', oleh_nama: 'Adi' }, { aksi: 'sahkan', waktu: '2026-11-19T03:00:00Z', oleh_nama: 'Admin' }],
  dosen: [{ id: 'd1', nama: 'Adi', nama_gelar: 'Dr. Adi', nip: '1' }, { id: 'kap', nama: 'Budi', nip: '2' }, { id: 'adm', nama: 'Admin' }, { id: 'dek', nama: 'Cici', nip: '3' }],
  cpl: [{ kurikulum: 'K26', kode: 'A', rumusan: 'CPL A', indikator: '', urutan: 1 }], peta_cpl: [{ kurikulum: 'K26', kode_mk: '41301', cpl: 'A', indikator: '' }],
  sebutan: { kaprodi: null, dekan: 'Pjs. Dekan FPI' }, tanggal: { ganjil: 20260902, genap: null } };

test('konteks Word dari rps_dokumen: pejabat, a.n., tanggal dokumen semester, CPL, QR', () => {
  const c = konteksDokumen(D, { url: 'https://x.id/verifikasi-rps.html?k=0f8e' });
  assert.equal(c.rps.identitas.tanggal, '2026-09-02');          // semester 1 = ganjil
  assert.equal(c.pengembang.nama_gelar, 'Dr. Adi');
  assert.equal(c.kaprodi.nama, 'Budi');
  assert.equal(c.dekan.nama, 'Cici');
  assert.deepEqual(c.cpl.map(x => x.kode), ['A']);
  assert.equal(c.kaprodi_penyusun, true);
  assert.equal(c.esign.sah.diwakilkan, true);                     // admin a.n. Kaprodi
  assert.equal(c.esign.tetap.sebutan, 'Pjs. Dekan FPI');
  assert.equal(c.esign.url, 'https://x.id/verifikasi-rps.html?k=0f8e');
  const M = modelRps(c);
  assert.equal(M.dekan.nip, '3');
  assert.equal(M.esign.diajukan.waktu, '2026-11-18T03:00:00Z');
});

test('titik masuk peta dari prasyarat', () => {
  assert.equal(entryPeta({ syarat: { prasyarat: 'Fisika' } }), 'MK prasyarat: Fisika');
  assert.equal(entryPeta({ peta: { entry: 'Masuk' } }), 'Masuk');
});
