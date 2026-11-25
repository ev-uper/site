// Rencana bukti per instrumen (2026-11-25): site/instrumen/<id>/rencana-bukti-isi.js, shown by site/rencana-bukti.js.
// Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync } from 'node:fs';

const SITE = new URL('../../site/', import.meta.url);
const folder = readdirSync(new URL('instrumen/', SITE), { withFileTypes: true }).filter(d => d.isDirectory()).map(d => d.name);

test('every instrument has a rencana bukti entry for exactly its butir, with the fields the card reads', async () => {
  for (const id of folder) {
    const { RENCANA_BUKTI } = await import(new URL(`instrumen/${id}/rencana-bukti-isi.js`, SITE));
    const { BOBOT } = await import(new URL(`instrumen/${id}/bobot.js`, SITE));
    assert.deepEqual(Object.keys(RENCANA_BUKTI).sort(), Object.keys(BOBOT).sort(), `${id}: keys = butir`);
    for (const [no, r] of Object.entries(RENCANA_BUKTI)) {
      for (const k of ['bagian', 'skor4']) assert.ok(typeof r[k] === 'string' && r[k].trim(), `${id} ${no} ${k}`);
      assert.ok(Array.isArray(r.bukti) && r.bukti.length && r.bukti.every(b => typeof b === 'string' && b.trim()), `${id} ${no} bukti`);
    }
  }
});

test('LAMDEPILAR rencana bukti: Buku 2 document lists, LKPS tables by element code (Buku 6 old headings)', async () => {
  const { RENCANA_BUKTI: R } = await import(new URL('instrumen/lamdepilar-magister/rencana-bukti-isi.js', SITE));
  const { BUTIR_MANUAL } = await import(new URL('instrumen/lamdepilar-magister/butir-manual.js', SITE));
  const per = kode => R[BUTIR_MANUAL.find(b => b.kode === kode).no];
  assert.deepEqual(per('D.1').bukti, ['Daftar program studi di unit pengelola program studi (UPPS)',
    'Dokumen legalitas pendirian institusi dan program studi']);
  assert.equal(per('E.4').bukti[2], 'Analisis untuk memastikan terjadinya perbaikan berkelanjutan kinerja pembelajaran');
  assert.deepEqual(['D.1', 'E.1', 'E.2', 'E.5', 'A.2', 'A.5', 'R.3'].map(k => per(k).lkps),
    ['Tabel D.1', '', 'Tabel E.1.1, E.1.2', 'Tabel E.4.1, E.4.2, E.4.3', 'Tabel A.1', 'Tabel A.5.1, A.5.2', 'Tabel R.3.1']);
  assert.match(per('A.2').catatan, /Indikator Kuantitatif/);
  assert.equal(per('A.2').bagian, 'A.1 (bab 3), elemen A.2');      // LED template heading A.1 holds A.1 and A.2
  assert.match(per('P.1').skor4, /^Skor 3 .*; serta data kuantitatif/);   // quantitative element
  assert.ok(!/; serta/.test(per('D.1').skor4));
  assert.equal(Object.values(R).reduce((a, x) => a + x.bukti.length, 0), 101);
  assert.ok(Object.values(R).every(x => x.unit === ''), 'PJ decided by the prodi');
});
