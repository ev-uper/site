// Student butir 43-46 of site/skor.html against hand-computed values
// (owner 2026-11-04). Expected numbers follow the rule printed on each card;
// the working is in the comments. Fictitious data. Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { loadFormulas } from './score_harness.mjs';

const F = loadFormulas();
const TS = 2026;
const dekat = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} != ${b}`);
const ta = (tahun_ts, lain = {}) => ({ tahun_ts, mahasiswa_aktif: 0, lulusan: 0, ...lain });

// ----------------------------------------------------------------- butir 43
// 5-TS window 2022..2026, NM from the TA row of TS; a .002, b .02, c .04.
const prestasi = [
  { tahun_ts: 2024, tingkat: 'internasional', bidang: 'akademik', jumlah: 1 },
  { tahun_ts: 2025, tingkat: 'nasional', bidang: 'akademik', jumlah: 10 },
  { tahun: 2026, tingkat: 'wilayah_lokal', bidang: 'akademik', jumlah: 20 },  // no tahun_ts
  { tahun_ts: 2021, tingkat: 'internasional', bidang: 'akademik', jumlah: 5 }, // outside
  { tahun_ts: 2026, tingkat: 'internasional', bidang: 'non_akademik', jumlah: 3 },
];

test('butir 43: (I*3 + II)/4 over 5 TS', () => {
  const D = { prestasi_agregat: prestasi, akreditasi: { ta: [ta(2026, { mahasiswa_aktif: 1000 })] } };
  // I: .001/.002, .01/.02, .02/.04 -> A = B = C = .5 -> 3.046875
  // II: RI .003 >= a and RN 0 < b -> RI = a -> A = 1 -> 3.75
  dekat(F.run('butir43', { D, TS }), (3.046875 * 3 + 3.75) / 4);
});

test('butir 43: no NM for TS -> no score', () => {
  const D = { prestasi_agregat: prestasi, akreditasi: { ta: [ta(2025, { mahasiswa_aktif: 1000 })] } };
  assert.equal(F.run('butir43', { D, TS }), null);
});

// ----------------------------------------------------------------- butir 46
test('butir 46: student publications, 3-year window', () => {
  const D = { akreditasi: { ta: [ta(2026, { mahasiswa_aktif: 1000 })], publikasi_mhs: [
    { tahun: 2023, na4: 99 },                                  // outside
    { tahun: 2024, na4: 5 }, { tahun: 2025, na2: 50 }, { tahun: 2026, na1: 250 },
  ] } };
  // RI .005/.01, RN .05/.1, RW .25/.5 -> A = B = C = .5
  dekat(F.run('butir46', { D, TS }), 3.046875);
});

// ----------------------------------------------------------------- butir 44
test('skorMS: bands and the two rubric gaps', () => {
  assert.equal(F.skorMS(4.5), 4);
  assert.equal(F.skorMS(3.2), 4);          // gap 3 < MS <= 3.5 -> 4 (owner 2026-10-12)
  assert.equal(F.skorMS(3), 0);
  dekat(F.skorMS(8), 1);                   // (55 - 48) / 7
  assert.equal(F.skorMS(8.5), 0);          // gap MS > 8 -> 0
});

test('butir 44: graduate-weighted MS over cohorts TS-7..TS', () => {
  // cohort rows TS-7..TS = entry years 2018..2025
  const D = { akreditasi: { kohort: [
    { tahun_masuk: 2020, masuk: 30, lulus: 10, ms_tertimbang: 4.0 },
    { tahun_masuk: 2019, masuk: 30, lulus: 10, ms_tertimbang: 6.0 },
    { tahun_masuk: 2017, masuk: 60, lulus: 50, ms_tertimbang: 7.25 },  // outside
  ] } };
  // MS = (4*10 + 6*10) / 20 = 5 -> (55 - 30) / 7
  dekat(F.run('butir44', { D, TS }), 25 / 7);
});

test('butir 44: falls back to TA average study length', () => {
  const D = { akreditasi: { kohort: [], ta: [
    ta(2026, { lulusan: 10, rerata_masa_studi: 6 }),
    ta(2025, { lulusan: 10, rerata_masa_studi: 5 }),
    ta(2023, { lulusan: 90, rerata_masa_studi: 9 }),                 // outside
  ] } };
  // MS = (60 + 50) / 20 = 5.5 -> (55 - 33) / 7
  dekat(F.run('butir44', { D, TS }), 22 / 7);
});

// ----------------------------------------------------------------- butir 45
test('butir 45: PTW = b/a on cohort row TS-3 (entry 2022)', () => {
  const kohort = (b) => ({ akreditasi: { kohort: [
    { tahun_masuk: 2022, masuk: 40, lulus: b, lulus_3_5_sd_4_5: b, ms_tertimbang: 4 },
    { tahun_masuk: 2021, masuk: 40, lulus: 40, lulus_3_5_sd_4_5: 40, ms_tertimbang: 4 },
  ] } });
  dekat(F.run('butir45', { D: kohort(10), TS }), 2.5);      // 1 + 6 * .25
  assert.equal(F.run('butir45', { D: kohort(20), TS }), 4);  // 50%
  assert.equal(F.run('butir45', { D: kohort(0), TS }), 0);
});

test('butir 45: falls back to TA on-time percentage', () => {
  const D = { akreditasi: { kohort: [], ta: [
    ta(2026, { lulusan: 10, persen_tepat_waktu: 20 }),
    ta(2025, { lulusan: 30, persen_tepat_waktu: 40 }),
  ] } };
  // P = (200 + 1200) / 40 = 35% -> 1 + 6 * .35
  dekat(F.run('butir45', { D, TS }), 3.1);
});
