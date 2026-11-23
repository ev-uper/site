// Tombol admin "Perbarui sitasi dari OpenAlex" (site/impor-karya.js, pemilik 2026-11-10).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ambilBanyakDoi, rencanaSitasi } from '../../site/impor-karya.js';

test('banyak DOI diambil dalam kelompok, dipetakan menurut DOI rapi', async () => {
  const url = [];
  const palsu = async u => {
    url.push(u);
    const dois = decodeURIComponent(u.match(/filter=doi:([^&]*)/)[1]).split('|');
    return { status: 200, ok: true, json: async () => ({ results: dois.filter(d => !d.includes('hilang'))
      .map(d => ({ doi: 'https://doi.org/' + d.toUpperCase(), publication_year: 2024, counts_by_year: [] })) }) };
  };
  const dois = ['10.1/a', 'https://doi.org/10.1/B', '10.1/c', '10.1/hilang', '10.1/a'];
  const m = await ambilBanyakDoi(dois, palsu, 2);
  assert.equal(url.length, 2);                                   // 4 DOI unik, 2 per permintaan
  assert.match(url[0], /filter=doi:10\.1%2Fa\|10\.1%2Fb&per_page=2&/);
  assert.deepEqual([...m.keys()].sort(), ['10.1/a', '10.1/b', '10.1/c']);
});

test('rencana: tahun kosong atau bersumber OpenAlex diperbarui; isian dosen dibiarkan', () => {
  const works = new Map([['10.1/a', { publication_year: 2024,
    counts_by_year: [{ year: 2024, cited_by_count: 2 }, { year: 2025, cited_by_count: 5 }, { year: 2026, cited_by_count: 1 }] }]]);
  const karya = [
    { id: 'K1', doi: 'https://doi.org/10.1/A', karya_sitasi: [
      { tahun: 2024, jumlah: 2, sumber: 'openalex' },          // sama -> tidak ditulis ulang
      { tahun: 2025, jumlah: 3, sumber: 'openalex' },          // berubah -> diperbarui
      { tahun: 2026, jumlah: 9, sumber: 'google_scholar' }] }, // isian dosen -> dibiarkan
    { id: 'K2', doi: '10.1/tidak-ada', karya_sitasi: [] },
  ];
  const r = rencanaSitasi(karya, works, '2026-11-11');
  assert.deepEqual(r.baris, [{ karya_id: 'K1', tahun: 2025, jumlah: 5, sumber: 'openalex', diambil: '2026-11-11' }]);
  assert.equal(r.diperbarui, 1);
  assert.equal(r.dibiarkan, 1);
  assert.equal(r.sama, 1);
  assert.deepEqual(r.tidakDitemukan.map(k => k.id), ['K2']);
});

test('rencana: karya tanpa sitasi mendapat semua tahun sejak terbit', () => {
  const works = new Map([['10.1/b', { publication_year: 2025, counts_by_year: [{ year: 2026, cited_by_count: 4 }] }]]);
  const r = rencanaSitasi([{ id: 'K3', doi: '10.1/b' }], works, '2026-11-11');
  assert.deepEqual(r.baris.map(x => [x.tahun, x.jumlah]), [[2025, 0], [2026, 4]]);
});
