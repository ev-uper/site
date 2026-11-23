// site/tracer-skor.js: tracer study for score items 49 and 50 (owner 2026-11-05).
// Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { cekPitaWT, adaTingkat, sesuaiTracer } from '../../site/tracer-skor.js';

test('cekPitaWT: bands not filled -> no check', () => {
  assert.equal(cekPitaWT([{ tahun_lulus: 2024, wt_kurang_3: null, wt_3_18: null, wt_lebih_18: null }], 5), null);
  assert.equal(cekPitaWT([{ tahun_lulus: 2024 }], 5), null);
});

test('cekPitaWT: possible mean range from Table 6.f.1 bands', () => {
  // 6 under 3 months, 4 in 3-18 months, none above: mean between 1.2 and 9 months
  const tr = [{ wt_kurang_3: 4, wt_3_18: 1, wt_lebih_18: 0 }, { wt_kurang_3: 2, wt_3_18: 3, wt_lebih_18: 0 }];
  const P = cekPitaWT(tr, 4);
  assert.deepEqual([P.a, P.b, P.c, P.bawah, P.atas, P.cocok], [6, 4, 0, 1.2, 9, true]);
  assert.equal(cekPitaWT(tr, 10).cocok, false, 'mean above the largest possible');
  assert.equal(cekPitaWT(tr, 1).cocok, false, 'mean below the smallest possible');
});

test('cekPitaWT: someone above 18 months -> no upper bound', () => {
  const P = cekPitaWT([{ wt_kurang_3: 0, wt_3_18: 1, wt_lebih_18: 1 }], 40);
  assert.deepEqual([P.bawah, P.atas, P.cocok], [10.5, Infinity, true]);
});

test('sesuaiTracer: KBK counts Sedang + Tinggi; old field when levels are empty', () => {
  const baru = { sesuai_bidang: 1, kesesuaian_rendah: 2, kesesuaian_sedang: 3, kesesuaian_tinggi: 4 };
  const lama = { sesuai_bidang: 5, kesesuaian_rendah: null, kesesuaian_sedang: null, kesesuaian_tinggi: null };
  assert.equal(adaTingkat(baru), true);
  assert.equal(sesuaiTracer(baru), 7);
  assert.equal(adaTingkat(lama), false);
  assert.equal(sesuaiTracer(lama), 5);
  assert.equal(sesuaiTracer({ kesesuaian_rendah: 3, kesesuaian_sedang: 0, kesesuaian_tinggi: 0 }), 0, 'all low = 0, not old field');
});
