// Kegiatan dan berita dipisah di menu publik (pemilik 2026-11-23): Kegiatan prodi = kabar.html (diunggah dosen/admin
// atau mahasiswa lalu diverifikasi), Berita = laman berita universitas (config.yaml public_site.news_url).
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.document ??= { querySelector: () => null, querySelectorAll: () => [], title: '' };
const { MENU } = await import('../../site/kerangka.js');

test('Profil menu has Kegiatan prodi (kabar.html) and Berita as two separate items', () => {
  const isi = MENU.find(m => m.id === 'profil').isi;
  const keg = isi.find(x => x.kr === 'kegiatan'), ber = isi.find(x => x.kr === 'berita');
  assert.deepEqual([keg?.judul, keg?.href], ['Kegiatan prodi', 'kabar.html']);
  assert.equal(ber?.judul, 'Berita');
  assert.ok(!isi.some(x => /Berita dan kegiatan/.test(x.judul)));
});

test('Berita always points to the university news page, never to kabar.html', () => {
  const src = readFileSync(new URL('../../site/kerangka.js', import.meta.url), 'utf8');
  assert.match(src, /const berita = D\.situs\?\.berita,/);
  assert.ok(!/\? 'kabar\.html' : D\.situs\?\.berita/.test(src));
});
