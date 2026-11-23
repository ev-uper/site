// Tarik publikasi dari ORCID lewat OpenAlex (site/impor-karya.js, pemilik 2026-11-10).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { karyaOrcid } from '../../site/impor-karya.js';

const jawab = body => ({ status: 200, ok: true, json: async () => body });

test('penulis dari ORCID, lalu karyanya per halaman sampai habis', async () => {
  const url = [];
  const palsu = async u => {
    url.push(u);
    if (u.includes('/authors/orcid:')) return jawab({ id: 'https://openalex.org/A123', display_name: 'Dosen Contoh', works_count: 150 });
    const hal = +u.match(/[?&]page=(\d+)/)[1];
    const n = hal === 1 ? 100 : 50;
    return jawab({ meta: { count: 150 }, results: Array.from({ length: n }, (_, i) => ({ id: `W${hal}-${i}` })) });
  };
  const r = await karyaOrcid('https://orcid.org/0000-0002-0000-000X', palsu);
  assert.equal(r.nama, 'Dosen Contoh');
  assert.equal(r.works.length, 150);
  assert.match(url[0], /\/authors\/orcid:0000-0002-0000-000X$/);
  assert.match(url[1], /\/works\?filter=author\.id:A123&per_page=100&page=1&/);
  assert.equal(url.length, 3);                                  // penulis + 2 halaman
});

test('ORCID tidak dikenal OpenAlex: null; batas habis: galat batas', async () => {
  assert.equal(await karyaOrcid('0000-0000-0000-0000', async () => ({ status: 404, ok: false })), null);
  const batas = async () => ({ status: 429, ok: false, headers: { get: () => '60' } });
  await assert.rejects(karyaOrcid('0000-0000-0000-0001', batas), e => e.batas === true && e.tunggu === 60);
});
