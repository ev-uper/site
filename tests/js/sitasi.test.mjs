// Sitasi per tahun untuk LKPS 4.i (site/sitasi.js, pemilik 2026-11-10).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { sitasiTS, karya4i, tahunJendela } from '../../site/sitasi.js';

const per = (...xs) => xs.map(([tahun, jumlah]) => ({ tahun, jumlah, sumber: 'manual' }));

test('jendela TS-2 s.d. TS = empat tahun kalender yang beririsan', () => {
  assert.deepEqual(tahunJendela(2026), [2023, 2026]);
  const k = { karya_sitasi: per([2021, 9], [2022, 1], [2023, 2], [2024, 3], [2025, 4], [2026, 5]) };
  assert.deepEqual(sitasiTS(k, 2026), { n: 14, asal: 'tahunan' });
  assert.deepEqual(sitasiTS(k, 2025), { n: 10, asal: 'tahunan' });
});

test('angka total lama dipakai hanya bila belum ada sitasi per tahun', () => {
  assert.deepEqual(sitasiTS({ jumlah_sitasi: 12 }, 2026), { n: 12, asal: 'lama' });
  assert.deepEqual(sitasiTS({ jumlah_sitasi: 12, karya_sitasi: per([2026, 1]) }, 2026), { n: 1, asal: 'tahunan' });
  assert.deepEqual(sitasiTS({}, 2026), { n: 0, asal: null });
});

test('4.i: jurnal/prosiding Scopus/WoS sesuai visi dengan sitasi > 0, urut terbanyak', () => {
  const dasar = { kategori: 'publikasi', jenis: 'jurnal', indeksasi: 'scopus_q2', tahun: 2022 };
  const karya = [
    { ...dasar, judul: 'A', karya_sitasi: per([2025, 2]) },
    { ...dasar, judul: 'B', jumlah_sitasi: 5 },
    { ...dasar, judul: 'C', karya_sitasi: per([2019, 50]) },          // di luar jendela -> 0
    { ...dasar, judul: 'D', indeksasi: 'sinta_1_2', jumlah_sitasi: 9 },
    { ...dasar, judul: 'E', relevan_visi: false, jumlah_sitasi: 9 },
    { ...dasar, judul: 'F', jenis: 'buku', jumlah_sitasi: 9 },
  ];
  assert.deepEqual(karya4i(karya, 2026).map(x => [x.k.judul, x.n, x.asal]), [['B', 5, 'lama'], ['A', 2, 'tahunan']]);
});

// ---- Tautan karya yang mengutip (OpenAlex, instal-lengkap.sql; owner 2026-11-10)
import { tautanPengutip } from '../../site/sitasi.js';
import { idOA, drafDari, rencanaSitasi } from '../../site/impor-karya.js';

test('tautanPengutip: citing works in the TS window, empty without a valid id', () => {
  assert.equal(tautanPengutip('W2159974629', 2026),
    'https://openalex.org/works?filter=cites:W2159974629,publication_year:2023-2026');
  assert.equal(tautanPengutip(null, 2026), '');
  assert.equal(tautanPengutip('https://openalex.org/W1', 2026), '');
});

test('idOA, drafDari carry the OpenAlex id; rencanaSitasi lists new or changed ids', () => {
  assert.equal(idOA('https://openalex.org/W123'), 'W123');
  assert.equal(idOA(undefined), null);
  const w = { id: 'https://openalex.org/W77', doi: 'https://doi.org/10.1/a', title: 'A', publication_year: 2024,
    counts_by_year: [{ year: 2025, cited_by_count: 2 }] };
  assert.equal(drafDari(w, { hariIni: '2026-11-10' }).karya.openalex_id, 'W77');
  assert.equal(drafDari({ ...w, id: '' }, { hariIni: '2026-11-10' }).karya.openalex_id, undefined);
  const works = new Map([['10.1/a', w]]);
  const r = rencanaSitasi([{ id: 'k1', doi: '10.1/a', karya_sitasi: [] }, { id: 'k2', doi: '10.1/a', openalex_id: 'W77', karya_sitasi: [] }],
    works, '2026-11-10');
  assert.deepEqual(r.oa, [{ id: 'k1', oa: 'W77' }]);
});
