// Klaim insentif publikasi (pemilik 2026-11-24; site/insentif.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { tahunWIB, berkasKurang, bolehKlaim, langkahPengklaim, tugasInsentif, barisExcel } from '../../site/insentif.js';

const KINI = new Date('2026-11-24T03:00:00Z');
const PUB = { kategori: 'publikasi', tahun: 2026, status: 'terverifikasi' };

test('tahun WIB: 31 Desember 18.00 UTC sudah 1 Januari di WIB', () => {
  assert.equal(tahunWIB(new Date('2026-12-31T16:59:00Z')), 2026);
  assert.equal(tahunWIB(new Date('2026-12-31T17:00:00Z')), 2027);
});

test('berkas kurang urut artikel, indeksasi, LoA, pernyataan', () => {
  assert.deepEqual(berkasKurang([]), ['naskah', 'indeksasi', 'loa', 'pernyataan']);
  assert.deepEqual(berkasKurang([{ jenis: 'loa' }, { jenis: 'naskah' }, { jenis: 'sk' }]), ['indeksasi', 'pernyataan']);
});

test('boleh klaim: publikasi tahun berjalan, penulis, satu klaim per publikasi, klaim ulang setelah dikembalikan', () => {
  assert.equal(bolehKlaim(PUB, { sayaPenulis: true, kini: KINI }).boleh, true);
  assert.match(bolehKlaim({ ...PUB, tahun: 2025 }, { sayaPenulis: true, kini: KINI }).alasan, /tahun 2026/);
  assert.match(bolehKlaim(PUB, { sayaPenulis: false, kini: KINI }).alasan, /Hanya penulis/);
  assert.match(bolehKlaim({ ...PUB, kategori: 'penelitian' }, { sayaPenulis: true, kini: KINI }).alasan, /hanya untuk publikasi/);
  assert.match(bolehKlaim(PUB, { sayaPenulis: true, sayaId: 'a', klaim: { pengklaim_id: 'b', status: 'diklaim' }, kini: KINI }).alasan, /penulis lain/);
  assert.equal(bolehKlaim(PUB, { sayaPenulis: true, sayaId: 'a', klaim: { pengklaim_id: 'a', status: 'diklaim' }, kini: KINI }).boleh, false);
  assert.equal(bolehKlaim(PUB, { sayaPenulis: true, sayaId: 'a', klaim: { pengklaim_id: 'a', status: 'dikembalikan' }, kini: KINI }).boleh, true);
});

test('langkah pengklaim', () => {
  assert.equal(langkahPengklaim({ status: 'diklaim' }, PUB, [{ jenis: 'naskah' }]), 'Unggah Bukti indeksasi, LoA / bukti terbit, Surat pernyataan di bukti karya.');
  assert.equal(langkahPengklaim({ status: 'diklaim' }, { status: 'diajukan' }, BERKAS()), 'Menunggu verifikasi publikasi.');
  assert.equal(langkahPengklaim({ status: 'diklaim' }, PUB, BERKAS()), 'Lengkap; menunggu pemeriksaan prodi.');
  assert.match(langkahPengklaim({ status: 'dikembalikan', catatan: 'Lampirkan LoA.' }, PUB, []), /Lampirkan LoA\..*Klaim ulang/);
});
const BERKAS = () => ['naskah', 'indeksasi', 'loa', 'pernyataan'].map(jenis => ({ jenis, url: `https://drive.google.com/file/d/${jenis}/view` }));

test('Tugas saya: dikembalikan, berkas kurang untuk pengklaim; menunggu pemeriksaan untuk pengelola', () => {
  const klaim = [{ karya_id: 'k1', pengklaim_id: 'a', status: 'dikembalikan', catatan: 'Lampirkan LoA.' },
    { karya_id: 'k2', pengklaim_id: 'a', status: 'diklaim' }, { karya_id: 'k3', pengklaim_id: 'b', status: 'diklaim' }];
  const karya = new Map([['k1', { judul: 'P1' }], ['k2', { judul: 'P2' }], ['k3', { judul: 'P3' }]]);
  const bukti = new Map([['k2', [{ jenis: 'naskah' }]], ['k3', BERKAS()]]);
  const t = tugasInsentif({ saya: { id: 'a' }, klaim, karya, bukti });
  assert.deepEqual(t.map(x => x.judul), ['Insentif publikasi: 1 klaim dikembalikan prodi', 'Insentif publikasi: berkas 1 klaim belum lengkap']);
  assert.match(t[1].rinci, /P2 \(kurang: Bukti indeksasi, LoA \/ bukti terbit, Surat pernyataan\)/);
  const p = tugasInsentif({ saya: { id: 'z' }, klaim, karya, bukti, pengelola: true });
  assert.deepEqual(p.map(x => x.judul), ['Insentif publikasi: 2 klaim menunggu pemeriksaan']);
});

test('baris Excel pengajuan: kolom tetap, DOI baku, tautan berkas per jenis', () => {
  const rows = barisExcel([{ karya_id: 'k1', pengklaim_id: 'a', status: 'diajukan' }],
    new Map([['k1', { judul: 'Banjir', penulis: ['Ani', 'Budi'], nama_terbitan: 'J. Air', volume: '3', nomor: '1', halaman: '1-9', tahun: 2026,
      indeksasi: 'scopus_q2', doi: 'https://doi.org/10.1/AB' }]]),
    new Map([['k1', BERKAS()]]), new Map([['a', { nama: 'Ani', nidn: '001' }]]));
  assert.equal(rows[0].length, rows[1].length);
  assert.deepEqual(rows[1].slice(0, 10), [1, 'Ani', '001', 'Banjir', 'Ani, Budi', 'J. Air', 'Vol. 3 No. 1 hlm. 1-9', 2026, 'scopus_q2', 'https://doi.org/10.1/AB']);
  assert.equal(rows[1][12], 'https://drive.google.com/file/d/loa/view');
  assert.equal(rows[1].at(-1), 'Diajukan ke fakultas');
});
