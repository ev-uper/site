// Potret skor akreditasi berkala (owner 2026-11-11; instal-lengkap.sql).
import test from 'node:test';
import assert from 'node:assert/strict';
import { isiPotret, bandingPotret, bulanDari, svgTrenPotret, htmlRiwayatPotret } from '../../site/potret-skor.js';

const CTX = {
  tsData: 2026, NA: 287.456, NAmax: 330.1, st: { status: 'Terakreditasi', durasi: null },
  skorButir: { 6: { n: 3.254, ada: true }, 9: { n: 0, ada: false }, 26: { n: 2, ada: true } },
  semuaSy: [{ no: '26', tok: true, u3ok: false, u5ok: false }, { indikator: ['x'], label: 'Rerata kurikulum', tok: true, u3ok: null, u5ok: null }],
};

test('first day of the local month', () => {
  assert.equal(bulanDari(new Date(2026, 10, 30, 23, 59)), '2026-11-01');
  assert.equal(bulanDari(new Date(2027, 0, 1)), '2027-01-01');
});

test('row from the render context keeps the summary numbers', () => {
  const p = isiPotret(CTX, { cakupan: 81.234, butirTerisi: 2, butirTotal: 3 });
  assert.equal(p.ts, 2026);
  assert.equal(p.na, 287.46);
  assert.equal(p.na_maks, 330.1);
  assert.equal(p.cakupan, 81.23);
  assert.equal(p.status, 'Terakreditasi');
  assert.deepEqual(p.skor, { 6: 3.25, 9: null, 26: 2 });
  assert.equal(p.syarat.t, true);
  assert.equal(p.syarat.u3, false);   // false wins over unknown
  assert.deepEqual(p.syarat.gagal, ['u3: butir 26', 'u5: butir 26']);
});

test('comparison lists rises, falls, newly filled and emptied items', () => {
  const lama = { na: 250, skor: { 6: 3, 9: null, 26: 2, 30: 1 } };
  const baru = { na: 262.5, skor: { 6: 3.5, 9: 2, 26: 1.5, 30: null } };
  const b = bandingPotret(baru, lama);
  assert.equal(b.dNA, 12.5);
  assert.deepEqual(b.naik.map(x => x.no), ['6']);
  assert.deepEqual(b.turun.map(x => x.no), ['26']);
  assert.deepEqual(b.terisi.map(x => x.no), ['9']);
  assert.deepEqual(b.kosong.map(x => x.no), ['30']);
  assert.equal(bandingPotret(baru, null).dNA, null);
});

test('chart needs two snapshots; table is newest first with deltas and escaping', () => {
  const rows = [
    { id: 1, diambil: '2026-09-02T03:00:00Z', ts: 2026, na: 240, status: 'Terakreditasi', otomatis: true, skor: { 6: 3 }, syarat: { t: true } },
    { id: 2, diambil: '2026-10-05T03:00:00Z', ts: 2027, na: 255.5, status: 'Terakreditasi', otomatis: false, catatan: 'sebelum <AMI>', skor: { 6: 3.5 }, syarat: { t: true, u3: false } },
  ];
  assert.equal(svgTrenPotret(rows.slice(0, 1)), '');
  assert.match(svgTrenPotret(rows), /<polyline/);
  const html = htmlRiwayatPotret(rows, { admin: true });
  assert.ok(html.indexOf('05/10/2026') < html.indexOf('02/09/2026'));
  assert.match(html, /\+15,50/);
  assert.match(html, /sebelum &lt;AMI&gt;/);
  assert.match(html, /naik: 6 \(3,00→3,50\)/);
  assert.match(html, /TS berganti/);
  assert.match(html, /data-hapus-potret="2"/);
  assert.doesNotMatch(htmlRiwayatPotret(rows), /data-hapus-potret/);
});
