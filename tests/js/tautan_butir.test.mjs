// site/tautan-butir.js: links from input data to butir cards, and the BKD rows
// behind butir 30 (owner 2026-11-07). Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { nomorButir, tsDariTA, tsBaris, urlButir, htmlTautanButir, butirKarya, barisBkd } from '../../site/tautan-butir.js';
import { tautanBkd } from '../../site/bkd.js';

test('nomorButir expands ranges and lists, ignores LKPS table names', () => {
  assert.deepEqual(nomorButir('48–51'), ['48', '49', '50', '51']);
  assert.deepEqual(nomorButir('15, 17, 19, 20'), ['15', '17', '19', '20']);
  assert.deepEqual(nomorButir('30'), ['30']);
  assert.deepEqual(nomorButir('PS, 6.a'), []);
  assert.deepEqual(nomorButir(null), []);
});

test('TS from academic year and from a dated row (September starts the next TS)', () => {
  assert.equal(tsDariTA('2025/2026'), 2026);
  assert.equal(tsDariTA('2025/2027'), null);
  assert.equal(tsDariTA(''), null);
  assert.equal(tsBaris(2025, 9), 2026);
  assert.equal(tsBaris(2025, 8), 2025);
  assert.equal(tsBaris(2025, null), 2025);
  assert.equal(tsBaris(null, 3), null);
});

test('links open the card on the row TS', () => {
  assert.equal(urlButir('30', 2027), 'skor.html?ts=2027#butir-30');
  assert.equal(urlButir('30', null), 'skor.html#butir-30');
  const h = htmlTautanButir(['30', '30'], 2027);
  assert.equal((h.match(/<a /g) || []).length, 1);
  assert.match(h, /TS 2026\/2027/);
  assert.equal(htmlTautanButir([], 2027), '');
});

test('karya: butir by category, butir 6 only with a named partner', () => {
  assert.deepEqual(butirKarya({ kategori: 'pkm' }), ['11', '25', '32']);
  assert.deepEqual(butirKarya({ kategori: 'publikasi', karya_mitra: [{ institusi: 'PT X' }] }), ['6', '33']);
  assert.deepEqual(butirKarya({ kategori: 'publikasi', karya_mitra: [{ institusi: ' ' }] }), ['33']);
  assert.deepEqual(butirKarya({ kategori: 'luaran', karya_mitra: [{ institusi: 'PT X' }] }), ['34']);
  assert.deepEqual(butirKarya({ kategori: 'lain' }), []);
});

test('barisBkd follows rbk_prodi: verified, DTPS non-assessor, TA = TS, beban = SKS/2', () => {
  const dosen = [{ nama: 'Budi', nidn: '1', dtps: true, peran: 'dosen' },
    { nama: 'Ani', nidn: '2', dtps: true, peran: 'dosen' },
    { nama: 'Luar', nidn: '3', dtps: false, peran: 'dosen' },
    { nama: 'Asesor', nidn: '4', dtps: true, peran: 'asesor' }];
  const v = 'terverifikasi', ta = '2026/2027';
  const bkd = [
    { nidn: '1', tahun_akademik: ta, semester: 'ganjil', verifikasi: v, sks_pendidikan: 9, sks_penelitian: 3, bukti_url: 'u1' },
    { nidn: '1', tahun_akademik: ta, semester: 'genap', verifikasi: v, sks_pendidikan: 8, sks_ps_lain_dalam: 2, sks_pkm: 2 },
    { nidn: '2', tahun_akademik: ta, semester: 'ganjil', verifikasi: v, sks_pendidikan: 7, sks_penunjang: 1.5 },
    { nidn: '2', tahun_akademik: ta, semester: 'genap', verifikasi: 'diajukan', sks_pendidikan: 99 },
    { nidn: '3', tahun_akademik: ta, semester: 'ganjil', verifikasi: v, sks_pendidikan: 12 },
    { nidn: '4', tahun_akademik: ta, semester: 'ganjil', verifikasi: v, sks_pendidikan: 12 },
    { nidn: '1', tahun_akademik: '2025/2026', semester: 'ganjil', verifikasi: v, sks_pendidikan: 50 },
  ];
  const { baris, rbk } = barisBkd(bkd, dosen, 2027);
  assert.deepEqual(baris.map(b => b.nama), ['Ani', 'Budi']);
  const budi = baris[1];
  assert.equal(budi.sks, 24);
  assert.equal(budi.beban, 12);
  assert.ok(budi.lengkap);
  assert.deepEqual(budi.berkas, [{ semester: 'ganjil', url: 'u1' }]);
  assert.equal(baris[0].beban, 4.25);
  assert.ok(!baris[0].lengkap);
  // rbk_prodi: round(avg(sks/2), 4)
  assert.equal(rbk, (12 + 4.25) / 2);
  assert.deepEqual(barisBkd([], dosen, 2027), { baris: [], rbk: null });
});

test('BKD rows link to butir 30 on their TS; rejected and non-DTPS rows do not', () => {
  assert.match(tautanBkd({ tahun_akademik: '2026/2027', verifikasi: 'terverifikasi' }), /Dipakai di.*\?ts=2027#butir-30/);
  assert.match(tautanBkd({ tahun_akademik: '2026/2027', verifikasi: 'diajukan' }), /setelah diverifikasi/);
  assert.equal(tautanBkd({ tahun_akademik: '2026/2027', verifikasi: 'ditolak' }), '');
  assert.doesNotMatch(tautanBkd({ tahun_akademik: '2026/2027', verifikasi: 'terverifikasi' }, false), /butir-30/);
});
