// Instrument data in site/instrumen/<id>/ (owner 2026-11-24): every function
// inside the data must run without the general modules in site/. A name left
// behind when the data was split off (cekKepuasan, 2026-11-24) throws here.
// Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync } from 'node:fs';

const DIR = new URL('../../site/instrumen/', import.meta.url);
const INSTRUMEN = readdirSync(DIR, { withFileTypes: true }).filter(d => d.isDirectory()).map(d => d.name);
const ADA = new Set(Array.from({ length: 20 }, (_, i) => i + 1));
const D = { akreditasi: { kepuasan: [] } };

for (const id of INSTRUMEN) {
  const bm = await import(new URL(`${id}/butir-manual.js`, DIR));
  const ub = await import(new URL(`${id}/unsur-butir.js`, DIR));
  const rb = await import(new URL(`${id}/rumus-butir.js`, DIR));
  const bo = await import(new URL(`${id}/bobot.js`, DIR));

  // rumus-butir.js (irisan 3, 2026-11-24): helpers come from skor.html via buatRumus(h).
  test(`${id}: buatRumus names a missing helper`, () => {
    assert.throws(() => rb.buatRumus({ keadaan: () => ({}) }), new RegExp(rb.PEMBANTU_RUMUS[0]));
  });

  test(`${id}: every formula butir has a weight and is not also a manual butir`, () => {
    const h = Object.fromEntries(rb.PEMBANTU_RUMUS.map(n => [n, () => null]));
    const daftar = rb.buatRumus({ ...h, keadaan: () => ({ D: {}, TS: 2026 }) }).daftar();
    const manual = new Set(bm.BUTIR_MANUAL.map(b => String(b.no)));
    for (const { no, f } of daftar) {
      assert.equal(typeof f, 'function', `butir ${no}`);
      assert.ok(String(no) in bo.BOBOT, `butir ${no} tanpa bobot`);
      assert.ok(!manual.has(String(no)), `butir ${no} juga butir manual`);
    }
    assert.equal(new Set(daftar.map(x => x.no)).size, daftar.length, 'nomor butir ganda');
  });

  // SEKSI_KARTU (2026-11-24): skor.html only renders cards that sit in a section;
  // a butir outside every section disappears without any error.
  test(`${id}: every butir card sits in exactly one SEKSI_KARTU section`, () => {
    const h = Object.fromEntries(rb.PEMBANTU_RUMUS.map(n => [n, () => null]));
    const rumus = rb.buatRumus({ ...h, keadaan: () => ({ D: {}, TS: 2026 }) }).daftar().map(x => String(x.no));
    const ids = bm.SEKSI_KARTU.map(s => s.id);
    assert.equal(new Set(ids).size, ids.length, 'id seksi ganda');
    const tempat = new Map();
    for (const s of bm.SEKSI_KARTU) {
      assert.ok(s.judul, `seksi ${s.id} tanpa judul`);
      for (const no of s.rumus || []) {
        assert.ok(rumus.includes(String(no)), `seksi ${s.id}: butir ${no} bukan butir berumus`);
        tempat.set(String(no), (tempat.get(String(no)) || 0) + 1);
      }
    }
    for (const b of bm.BUTIR_MANUAL) {
      assert.ok(ids.includes(b.seksi), `butir ${b.no}: seksi '${b.seksi}' tidak ada di SEKSI_KARTU`);
      tempat.set(String(b.no), (tempat.get(String(b.no)) || 0) + 1);
    }
    for (const no of rumus) assert.equal(tempat.get(no), 1, `butir berumus ${no} tidak tepat satu seksi`);
    for (const b of bm.BUTIR_MANUAL) assert.equal(tempat.get(String(b.no)), 1, `butir ${b.no} tidak tepat satu seksi`);
  });

  test(`${id}: butir manual functions run on empty data`, () => {
    for (const b of bm.BUTIR_MANUAL) {
      if (b.konteks) assert.equal(typeof b.konteks(D, 2026), 'string', `butir ${b.no} konteks`);
      if (b.hitung) b.hitung.f(...b.hitung.kunci.map(() => 1));
      if (b.komponen) assert.ok(Number.isFinite(b.gabung(2, 3)), `butir ${b.no} gabung`);
    }
  });

  // SKOR_MAKS and TEKS_BATAS (irisan 4, 2026-11-24): scale and status thresholds come from the instrument.
  const su = await import(new URL(`${id}/syarat-unggul.js`, DIR));
  test(`${id}: score scale and threshold text are defined`, () => {
    assert.ok(Number.isInteger(bo.SKOR_MAKS) && bo.SKOR_MAKS > 0, `SKOR_MAKS ${bo.SKOR_MAKS}`);
    assert.equal(typeof su.TEKS_BATAS, 'string');
    assert.ok(su.TEKS_BATAS.trim().length > 0);
  });

  test(`${id}: unsur rules give a score 0-SKOR_MAKS for none, some, and all elements`, () => {
    for (const [no, d] of Object.entries(ub.UNSUR_BUTIR)) {
      for (const k of d.komponen) {
        for (const ada of [new Set(), new Set([1]), ADA]) {
          const s = k.f(ada);
          assert.ok(Number.isFinite(s) && s >= 0 && s <= bo.SKOR_MAKS, `butir ${no} ${k.kunci}: ${s}`);
        }
      }
    }
  });
}
