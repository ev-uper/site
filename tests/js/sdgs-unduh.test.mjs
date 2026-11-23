// Periode TS dan unduhan Excel Rekap SDGs (pemilik 2026-11-17; site/sdgs-unduh.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { tsKarya, taTeks, opsiPeriode, cocokPeriode, labelPeriode, namaBerkas, lembarUnduh } from '../../site/sdgs-unduh.js';

test('TS mengikuti bangun.py _ts: bulan >= 9 masuk TS berikutnya, bulan kosong = tahun', () => {
  assert.equal(tsKarya({ tahun: 2025, bulan: 8 }), 2025);
  assert.equal(tsKarya({ tahun: 2025, bulan: 9 }), 2026);
  assert.equal(tsKarya({ tahun: 2025 }), 2025);
  assert.equal(tsKarya({}), 0);
  assert.equal(taTeks(2026), '2025/2026');
});

test('periode tahun, TS, dan 3 TS', () => {
  const k = { tahun: 2024, bulan: 10 };            // TS 2024/2025
  assert.ok(cocokPeriode(k, ''));
  assert.ok(cocokPeriode(k, 'th:2024'));
  assert.ok(!cocokPeriode(k, 'ts:2024'));
  assert.ok(cocokPeriode(k, 'ts:2025'));
  assert.ok(cocokPeriode(k, 'ts3:2027'));
  assert.ok(!cocokPeriode(k, 'ts3:2028'));
  assert.equal(labelPeriode('ts3:2026'), 'TS 2023/2024 s.d. 2025/2026');
  assert.equal(namaBerkas('ts:2026', 11), 'rekap-sdgs-TS2025-2026-sdg11.xlsx');
  assert.equal(namaBerkas('ts3:2026'), 'rekap-sdgs-TS2023-2026.xlsx');
  assert.equal(namaBerkas(''), 'rekap-sdgs-semua.xlsx');
});

test('opsi periode: TS berjalan selalu ada, TS masa depan tidak', () => {
  const g = opsiPeriode([{ tahun: 2024 }, { tahun: 2030 }], new Date(2026, 10, 17));
  const ts = g[0].opsi.map(o => o[0]);
  assert.deepEqual(ts, ['ts:2027', 'ts:2024']);
  assert.match(g[0].opsi[0][1], /berjalan/);
  assert.deepEqual(g[2].opsi.map(o => o[0]), ['th:2030', 'th:2024']);
});

test('lembar unduhan: satu baris bukti per berkas, karya tanpa bukti tetap tercatat', () => {
  const SDGS = [[11, 'Kota berkelanjutan'], [13, 'Iklim']];
  const xs = [
    { judul: 'A', kategori: 'publikasi', tahun: 2025, bulan: 10, status: 'terverifikasi', doi: '10.1/x', tautan: 'https://doi.org/10.1/x',
      dosen: ['Budi'], sdgs: [11, 13], bukti: [{ jenis: 'naskah', judul: 'PDF', url: 'https://drive/1' }, { jenis: 'sk', url: 'https://drive/2' }] },
    { judul: 'B', kategori: 'pkm', tahun: 2025, status: 'diajukan', dosen: ['Ani', 'Budi'], sdgs: [11], bukti: [] },
  ];
  const L = lembarUnduh(xs, { sdgs: SDGS, kat: { publikasi: 'Publikasi', pkm: 'PkM' }, jenisBukti: { naskah: 'Naskah', sk: 'SK' } });
  assert.equal(L.Daftar.length, 3);
  assert.deepEqual(L.Daftar[1].slice(0, 9), [1, 'A', 'Publikasi', 2025, 10, '2025/2026', 'Budi', '11, 13', 'Kota berkelanjutan; Iklim']);
  assert.deepEqual(L.Daftar[1][9], { t: 'DOI 10.1/x', l: 'https://doi.org/10.1/x' });
  assert.equal(L.Daftar[2][10], 'menunggu verifikasi');
  assert.equal(L.Bukti.length, 4);
  assert.deepEqual(L.Bukti[1][5], { t: 'https://drive/1', l: 'https://drive/1' });
  assert.equal(L.Bukti[3][3], '(belum ada bukti)');
  assert.deepEqual(L['Rekap SDG'][1], [11, 'Kota berkelanjutan', 2, 1, 1]);
});
