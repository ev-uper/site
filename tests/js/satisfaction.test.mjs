// Butir 52 (user satisfaction, Tabel 6.g.2) from Data prodi per TS
// (owner 2026-11-04). Hand-computed: TKi = 4a + 3b + 2c + d (fractions),
// score = sum(TKi) / 7. Fictitious data. Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { ASPEK_KEPUASAN, BUTIR_MANUAL, skorManual, tkKepuasan, cekKepuasan }
  from '../../site/butir-manual.js';
import { loadFormulas } from './score_harness.mjs';

const dekat = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} != ${b}`);
const B52 = BUTIR_MANUAL.find(b => b.no === '52');
const TS = 2026;

// rows for one TS; `p` maps aspect -> [sb, b, c, k], default 50/30/20/0
const survei = (ts, p = {}, tanpa = []) => ASPEK_KEPUASAN
  .filter(([a]) => !tanpa.includes(a))
  .map(([a]) => {
    const [sangat_baik, baik, cukup, kurang] = p[a] || [50, 30, 20, 0];
    return { tahun_ts: ts, aspek: a, sangat_baik, baik, cukup, kurang };
  });
const D = rows => ({ akreditasi: { kepuasan: rows } });

test('seven aspects listed once each', () => {
  assert.equal(ASPEK_KEPUASAN.length, 7);
  assert.equal(new Set(ASPEK_KEPUASAN.map(([a]) => a)).size, 7);
});

test('uniform survey: TKi 3.3 each -> sum 23.1, score 3.3', () => {
  // 4*.5 + 3*.3 + 2*.2 + 0 = 3.3
  dekat(tkKepuasan(D(survei(TS)), TS), 23.1);
  dekat(skorManual(B52, () => tkKepuasan(D(survei(TS)), TS)).skor, 3.3);
});

test('mixed survey: one aspect all very good, six at 40/40/10/10', () => {
  const p = Object.fromEntries(ASPEK_KEPUASAN.map(([a], i) =>
    [a, i === 0 ? [100, 0, 0, 0] : [40, 40, 10, 10]]));
  // 4 + 6 * (1.6 + 1.2 + .2 + .1) = 4 + 18.6 = 22.6 -> 22.6 / 7
  dekat(tkKepuasan(D(survei(TS, p)), TS), 22.6);
  dekat(skorManual(B52, () => 22.6).skor, 22.6 / 7);
});

test('other TS rows are ignored', () => {
  const rows = [...survei(2025, Object.fromEntries(ASPEK_KEPUASAN.map(([a]) => [a, [0, 0, 0, 100]]))),
                ...survei(TS)];
  dekat(tkKepuasan(D(rows), TS), 23.1);
  dekat(tkKepuasan(D(rows), 2025), 7);      // all "kurang": TKi 1 each
});

test('incomplete survey: missing or invalid aspects count 0 (owner 2026-11-10)', () => {
  dekat(tkKepuasan(D(survei(TS, {}, ['etika'])), TS), 23.1 - 3.3);               // 6 aspects
  dekat(tkKepuasan(D(survei(TS, { etika: [50, 30, 15, 0] })), TS), 23.1 - 3.3);  // sums to 95
  const c = cekKepuasan(D(survei(TS, { etika: [50, 30, 15, 0] }, ['bahasa_asing'])), TS);
  assert.deepEqual(c.salah, ['Etika']);
  assert.deepEqual(c.kosong, ['Kemampuan berbahasa asing']);
  assert.equal(tkKepuasan(D([]), TS), null);
  assert.equal(tkKepuasan(null, TS), null);
});

test('rounding tolerance of 1 point, as in patch 21', () => {
  dekat(tkKepuasan(D(survei(TS, { etika: [50.5, 30, 20, 0] })), TS), 23.1 + 0.02);
});

test('skor.html IS(): always from the table, tk_total entry ignored', () => {
  const F = loadFormulas();
  Object.assign(F, { D: D(survei(TS)), TS, PENG: { tk_total: '20' } });
  dekat(F.IS('tk_total'), 23.1);
  Object.assign(F, { D: D(survei(TS, {}, ['etika'])) });
  dekat(F.IS('tk_total'), 23.1 - 3.3);
  Object.assign(F, { D: D([]) });
  assert.equal(F.IS('tk_total'), null);
});
