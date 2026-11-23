// Pengingat pembaruan karya dan profil dosen (owner 2026-11-12).
import test from 'node:test';
import assert from 'node:assert/strict';
import { kurangProfil, penerimaProfil, rincianKarya, penerimaKarya, isiPola } from '../../site/pengingat-dosen.js';

const KINI = new Date(2026, 10, 12);
const DOSEN = [
  { id: 'a', nama: 'Ani', email: 'ani@x.id', aktif: true, peran: 'dosen', sinta_id: '1', orcid: '0000', scopus_id: null, jabatan: 'lektor',
    riwayat_pendidikan: [{ jenjang: 'doktor' }], topik_keahlian: [] },
  { id: 'b', nama: 'Budi', email: 'budi@x.id', aktif: true, peran: 'dosen', sinta_id: '2', orcid: '1', scopus_id: '3', jabatan: 'lektor',
    riwayat_pendidikan: [{}], topik_keahlian: ['AIR02'] },
  { id: 'c', nama: 'Cici', email: 'cici@x.id', aktif: true, peran: 'asesor', sinta_id: '' },
  { id: 'd', nama: 'Dodi', email: '', aktif: true, peran: 'dosen', sinta_id: '' },
  { id: 'e', nama: 'Eko', email: 'eko@x.id', aktif: false, peran: 'dosen', sinta_id: '' },
  { id: 'f', nama: 'Staf Admin', email: 'staf@x.id', aktif: true, peran: 'admin', dtps: false, sinta_id: '' },   // non-DTPS staff: skipped
];

test('profile: lists empty fields only; complete lecturers, assessors, inactive and email-less are skipped', () => {
  assert.deepEqual(kurangProfil(DOSEN[0]), ['Scopus ID (bila sudah punya)', 'Topik keahlian']);
  assert.deepEqual(kurangProfil({ sinta_id: '1' }), []);                  // columns not read: not reported
  const p = penerimaProfil(DOSEN);
  assert.deepEqual(p.map(x => x.email), ['ani@x.id']);
  assert.equal(p[0].rinci, '- Scopus ID (bila sudah punya)\n- Topik keahlian');
});

test('profile: empty photo is reminded only when the column was read (2026-11-21)', () => {
  const lengkap = { ...DOSEN[1] };
  assert.deepEqual(kurangProfil({ ...lengkap, foto_url: null }), ['Foto profil (tampil di situs publik)']);
  assert.deepEqual(kurangProfil({ ...lengkap, foto_url: 'https://drive.google.com/file/d/x/view' }), []);
  assert.deepEqual(kurangProfil(lengkap), []);                            // patch 85 not run: no foto_url key
});

const K = [
  { id: 1, judul: 'Jurnal A', tahun: 2026, kategori: 'publikasi', status: 'terverifikasi', bukti_url: null, karya_penulis: [{ dosen_id: 'a' }] },
  { id: 2, judul: 'Riset B', tahun: 2026, kategori: 'penelitian', status: 'terverifikasi', bukti_url: 'https://x', karya_penulis: [{ dosen_id: 'a' }] },
  { id: 3, judul: 'PkM C', tahun: 2025, kategori: 'pkm', status: 'diajukan', karya_penulis: [{ dosen_id: 'a' }, { dosen_id: 'b' }] },
  { id: 4, judul: 'Ditolak D', tahun: 2026, kategori: 'publikasi', status: 'ditolak', catatan: 'DOI salah', karya_penulis: [{ dosen_id: 'a' }] },
  { id: 5, judul: 'Bukti terpisah', tahun: 2024, kategori: 'luaran', status: 'terverifikasi', karya_penulis: [{ dosen_id: 'a' }] },
  { id: 6, judul: 'Draf', tahun: 2026, kategori: 'publikasi', status: 'draf', karya_penulis: [{ dosen_id: 'a' }] },
];

test('works: counts this and last year, pending, missing evidence (karya_bukti counts), returned with admin note', () => {
  const r = rincianKarya('a', K, new Set([5]), KINI);
  assert.match(r.teks, /Karya tercatat 2026: 1 publikasi, 1 penelitian; 2025: 1 PkM\./);
  assert.match(r.teks, /Menunggu verifikasi admin: 1 karya/);
  assert.match(r.teks, /belum ada buktinya \(mohon unggah\):\n {2}- Jurnal A/);
  assert.ok(!r.teks.includes('Bukti terpisah') && !r.teks.includes('Riset B') && !r.teks.includes('Draf'));
  assert.match(r.teks, /Dikembalikan untuk diperbaiki:\n {2}- Ditolak D \(catatan admin: DOI salah\)/);
  assert.deepEqual([r.tanpaBukti, r.ditolak, r.menunggu], [1, 1, 1]);
  assert.match(rincianKarya('b', K, new Set(), KINI).teks, /2026: belum ada; 2025: 1 PkM/);
});

test('works reminder goes to every active non-assessor with email; long lists are cut at five', () => {
  assert.deepEqual(penerimaKarya(DOSEN, K, new Set(), KINI).map(x => x.email), ['ani@x.id', 'budi@x.id']);
  const banyak = Array.from({ length: 7 }, (_, i) => ({ id: 10 + i, judul: `J${i}`, tahun: 2026, kategori: 'publikasi', status: 'terverifikasi', karya_penulis: [{ dosen_id: 'b' }] }));
  const t = rincianKarya('b', banyak, new Set(), KINI).teks;
  assert.ok(t.includes('J4') && !t.includes('J5') && t.includes('dan 2 lainnya'));
});

test('template placeholders', () => {
  assert.equal(isiPola('Yth. {nama}, {rinci} di {situs} — {prodi}', { nama: 'Ani', rinci: 'x' }, { situs: 'https://s/', prodi: 'Teknik' }),
    'Yth. Ani, x di https://s/ — Teknik');
});
