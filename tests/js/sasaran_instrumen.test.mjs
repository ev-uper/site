// Sasaran status per instrumen (2026-11-25): table columns, section title and potret trend lines come from
// site/instrumen/<id>/syarat-unggul.js, not from skor.html / potret-skor.js.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync } from 'node:fs';

const SITE = new URL('../../site/', import.meta.url);
const folder = readdirSync(new URL('instrumen/', SITE), { withFileTypes: true }).filter(d => d.isDirectory()).map(d => d.name);

test('each instrument names its targets, section title and NA lines within its NA range', async () => {
  for (const id of folder) {
    const S = await import(new URL(`instrumen/${id}/syarat-unggul.js`, SITE));
    const B = await import(new URL(`instrumen/${id}/bobot.js`, SITE));
    const maks = Math.round(B.BOBOT_TOTAL * B.SKOR_MAKS);
    assert.ok(S.SASARAN.length && S.SASARAN[0] === 't', `${id}: Terakreditasi first`);
    for (const sa of S.SASARAN) assert.ok(S.NAMA_SASARAN[sa], `${id}: name for ${sa}`);
    assert.ok(S.JUDUL_JALAN.startsWith('Jalan menuju '), id);
    assert.ok(S.BATAS_NA.length && S.BATAS_NA.every(([v, l]) => v > 0 && v < maks && l), `${id}: lines inside 0..${maks}`);
  }
  const L = await import(new URL('instrumen/lamdepilar-magister/syarat-unggul.js', SITE));
  assert.deepEqual(L.SASARAN, ['t']);
  assert.equal(L.JUDUL_JALAN, 'Jalan menuju Terakreditasi');
  const T = await import(new URL('instrumen/lam-teknik-s1/syarat-unggul.js', SITE));
  assert.deepEqual(T.SASARAN, ['t', 'u3', 'u5']);
  assert.deepEqual(T.BATAS_NA.map(([v]) => v), [200, 331, 361]);
});

// Pages hide LAM Teknik butir 1-60 parts for other instruments (2026-11-25): one flag per instrument.
test('BUTIR_LAM_TEKNIK per instrument, and Narasi LED keeps only Identitas and Tim when false', async () => {
  const lam = (await import(new URL('instrumen/lam-teknik-s1/bobot.js', SITE))).BUTIR_LAM_TEKNIK;
  const ldp = (await import(new URL('instrumen/lamdepilar-magister/bobot.js', SITE))).BUTIR_LAM_TEKNIK;
  assert.deepEqual([lam, ldp], [true, false]);
  const { bagianNarasi, pisahKalimat } = await import(new URL('led-narasi.js', SITE));
  const C = { hanyaIdentitasTim: true, P: { ps: 'Program Studi X', pt: 'U', timPenyusun: '[isi: nama anggota tim]' }, ta: '2025/2026', ta2: '2023/2024' };
  const g = bagianNarasi(C);
  assert.deepEqual(g.map(x => x.id), ['identitas', 'A']);
  const kunci = g[0].bagian.flatMap(b => b.kalimat.flatMap(x => pisahKalimat(x.teks, b.lingkup, x.id).filter(p => p.kunci).map(p => p.kunci)));
  for (const k of ['umum|identitas|Unit Pengelola Program Studi|1', 'umum|identitas|Kota kedudukan perguruan tinggi|1'])
    assert.ok(kunci.includes(k), k);   // the keys led-kerangka.js isiDepan reads for the cover
});
