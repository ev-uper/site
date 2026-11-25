// site/tema.css is the one source of institution colours (owner 2026-11-05):
// another programme changes its identity there. Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';

const SITE = new URL('../../site/', import.meta.url);
const baca = f => readFileSync(new URL(f, SITE), 'utf8');
const TEMA = baca('tema.css');
const DEKL = new Map([...TEMA.matchAll(/(--[\w-]+):([^;]+);/g)].map(m => [m[1], m[2].trim()]));
const halaman = readdirSync(SITE).filter(f => f.endsWith('.html'));
// recursive: instrument modules in site/instrumen/<id>/ are checked too (2026-11-24)
const berkas = readdirSync(SITE, { recursive: true }).map(f => f.replaceAll('\\', '/'))
  .filter(f => /\.(html|js|css)$/.test(f) && !f.startsWith('tema.'));

test('tema.css: every page links it before its own styles', () => {
  for (const f of halaman) {
    const t = baca(f), i = t.search(/<link rel="stylesheet" href="tema\.css/);
    assert.ok(i >= 0, `${f}: tema.css not linked`);
    const gaya = t.indexOf('<style');
    assert.ok(gaya < 0 || i < gaya, `${f}: tema.css must come before <style>`);
  }
});

test('institution colours live only in tema.css', () => {
  // karya.html keeps its own neutrals, so only the brand families are checked
  const merek = [...DEKL].filter(([k, v]) => /^--(biru|merah)/.test(k) && v.startsWith('#')).map(([, v]) => v.toUpperCase());
  assert.ok(merek.length > 20);
  for (const f of berkas) {
    const hex = (baca(f).match(/(?<![&\w])#[0-9A-Fa-f]{6}\b/g) || []).map(h => h.toUpperCase());
    assert.deepEqual(hex.filter(h => merek.includes(h)), [], `${f} repeats a theme colour`);
    assert.ok(!/rgba\(\s*(12\s*,\s*42\s*,\s*77|8\s*,\s*29\s*,\s*54)/.test(baca(f)), `${f}: use rgba(var(--biru-rgb),…)`);
  }
});

test('every var(--name) used on a page is defined', () => {
  for (const f of berkas) {
    const t = baca(f);
    const lokal = new Set([...t.matchAll(/(--[\w-]+)\s*:/g)].map(m => m[1]));
    for (const [, nama] of t.matchAll(/var\((--[\w-]+)\)/g)) {
      if (nama === '--nama') continue;                       // comment text
      assert.ok(DEKL.has(nama) || lokal.has(nama), `${f}: ${nama} is not defined`);
    }
  }
});

test('drawn images read literal values, not var()', () => {
  // canvas and the exported SVG cannot resolve var(--name)
  const kode = baca('grafik.html').match(/<script>\n([\s\S]*?)<\/script>/)[1];
  assert.ok(!/(fill|stroke)="var\(/.test(kode));
  assert.ok(!baca('led-grafik.js').includes("'var("));
  // both files have a local variable `warna` (the series colour), hence warnaTema
  for (const f of ['grafik.html', 'led-grafik.js'])
    assert.ok(!/(?<!\w)warna\('--/.test(baca(f)), `${f}: call warnaTema, not warna`);
});
