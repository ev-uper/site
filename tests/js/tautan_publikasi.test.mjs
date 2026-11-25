// Tautan publikasi yang bisa diklik (pemilik 2026-11-24; site/tautan-publikasi.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { doiBaku, urlPublikasi, aTautan, htmlDoi } from '../../site/tautan-publikasi.js';
import { tautanPublikasiKarya } from '../../site/karya-tampil.js';

test('DOI dibakukan; DOI didahulukan, lalu URL; Google Drive tidak pernah ditampilkan', () => {
  assert.equal(doiBaku('https://dx.doi.org/10.1/AB'), '10.1/AB');
  assert.equal(doiBaku('doi: 10.1/AB'), '10.1/AB');
  assert.equal(urlPublikasi({ doi: 'https://doi.org/10.1/AB', url: 'https://jurnal.id/a' }), 'https://doi.org/10.1/AB');
  assert.equal(urlPublikasi({ url: 'https://jurnal.id/a' }), 'https://jurnal.id/a');
  assert.equal(urlPublikasi({ url: 'https://drive.google.com/file/d/x' }), '');
  assert.equal(urlPublikasi({ url: 'jurnal.id/a' }), '');
});

test('HTML tautan: tab baru, teks di-escape, DOI sebagai tautan', () => {
  assert.equal(aTautan('https://a.id/?x=1&y=2', 'Hujan & <banjir>'),
    '<a href="https://a.id/?x=1&amp;y=2" target="_blank" rel="noopener">Hujan &amp; &lt;banjir&gt;</a>');
  assert.equal(aTautan('', 'Judul'), 'Judul');
  assert.equal(htmlDoi({ doi: '10.1/AB' }), 'DOI <a href="https://doi.org/10.1/AB" target="_blank" rel="noopener">10.1/AB</a>');
  assert.equal(htmlDoi({}), '');
});

test('daftar Karya ruang kerja: tautan hanya untuk publikasi', () => {
  assert.match(tautanPublikasiKarya({ kategori: 'publikasi', doi: '10.1/AB' }), /href="https:\/\/doi\.org\/10\.1\/AB"[^>]*>DOI 10\.1\/AB</);
  assert.match(tautanPublikasiKarya({ kategori: 'publikasi', url: 'https://jurnal.id/a' }), />Tautan publikasi</);
  assert.equal(tautanPublikasiKarya({ kategori: 'penelitian', url: 'https://x.id' }), '');
  assert.equal(tautanPublikasiKarya({ kategori: 'publikasi' }), '');
});

test('dosen.html (skrip bukan modul) memakai aturan yang sama dengan tautan-publikasi.js', async () => {
  const { readFileSync } = await import('node:fs');
  const modul = readFileSync(new URL('../../site/tautan-publikasi.js', import.meta.url), 'utf8');
  const html = readFileSync(new URL('../../site/dosen.html', import.meta.url), 'utf8');
  for (const pola of [String.raw`/^https?:\/\/(dx\.)?doi\.org\//i`, String.raw`/^doi:\s*/i`, String.raw`/^https?:\/\/\S+$/i`,
                      String.raw`/(drive|docs|script)\.google\./i`,
                      'target="_blank" rel="noopener"'])
    assert.ok(modul.includes(pola) && html.includes(pola), pola);
  assert.ok(!/from\s+['"]\.\/tautan-publikasi\.js/.test(html), 'dosen.html tidak boleh mengimpor modul (skrip utamanya bukan modul)');
});
