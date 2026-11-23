// Optional modules switched off per site (owner 2026-11-12: accreditation-only template).
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fiturAktif, fiturHalaman, halamanAktif, PAKET, MODUL_OPSIONAL } from '../../site/fitur.js';

const SITE = new URL('../../site/', import.meta.url);
const baca = f => readFileSync(new URL(f, SITE), 'utf8');

test('nothing is off by default; FITUR_MATI switches pages off by module', () => {
  delete globalThis.FITUR_MATI;
  assert.ok(fiturAktif('rapat') && halamanAktif('rapat.html') && halamanAktif('skor.html'));
  globalThis.FITUR_MATI = PAKET.akreditasi;
  assert.ok(!fiturAktif('rapat') && !halamanAktif('hadir.html?t=abc') && !halamanAktif('/cv-site/keahlian.html?tab=peta'));
  assert.ok(halamanAktif('skor.html') && halamanAktif('nilai-cpl.html') && halamanAktif('kelola-survei.html') && fiturAktif(''));
  assert.equal(fiturHalaman('https://x.github.io/cv-site/sdgs.html#a'), 'sdgs');
  delete globalThis.FITUR_MATI;
});

test('accreditation package switches off exactly the modules not used by scores', () => {
  assert.deepEqual(PAKET.lengkap, []);
  assert.deepEqual([...PAKET.akreditasi].sort(), Object.keys(MODUL_OPSIONAL).sort());
});

test('every optional page exists; guarded public pages load config.js and fitur.js', () => {
  const menu = baca('menu.js');
  // SDGs: menu ruang kerja ke sdgs-bukti.html (dengan bukti); sdgs.html tetap halaman publik (pemilik 2026-11-16).
  for (const h of ['rapat.html', 'hibah.html', 'kalender.html', 'pengingat.html', 'keahlian.html', 'sdgs-bukti.html'])
    assert.ok(menu.includes(`href: '${h}'`), h);
  // halamanBoleh dan bolehBuka menyaring halaman fitur mati sebelum aturan peran (bolehHalaman, 157).
  assert.equal((menu.match(/halamanAktif\(h\.href\) && bolehHalaman\(saya, h\)/g) || []).length, 2);
  for (const h of ['keahlian.html', 'sdgs.html', 'sdgs-bukti.html', 'hadir.html']) {
    const t = baca(h);
    assert.ok(t.includes('src="config.js'), h + ' loads config.js');
    assert.ok(t.includes('if (!jagaHalaman()) await new Promise'), h + ' is guarded');
  }
  for (const h of ['index.html', 'dosen.html', 'panduan.html', 'monitoring.html'])
    assert.ok(baca(h).includes('src="config.js'), h + ' loads config.js');
  assert.match(baca('config.js'), /^window\.FITUR_MATI = \[\];$/m);
});
