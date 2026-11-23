// Butir formulas of site/skor.html against hand-computed values
// (owner 2026-11-04). Expected numbers come from the rule printed on each
// card (the `rumus` line), worked out by hand in the comments, not from the
// code's own output. Fictitious data. Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { loadFormulas } from './score_harness.mjs';

const F = loadFormulas();
const TS = 2026;                       // window TS-2..TS = 2024..2026
const dekat = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} != ${b}`);

// ---------------------------------------------------------------- skorRasio
test('skorRasio: interior point, A = B = C = 0.5', () => {
  // 3.75 * ((.5 + .5 + .25) - .25 - .125 - .125 + .0625) = 3.75 * .8125
  dekat(F.skorRasio(0.25, 0.5, 1, 0.5, 1, 2), 3.046875);
});

test('skorRasio: RI > a and RN > b gives 4', () => {
  assert.equal(F.skorRasio(0.6, 1.1, 0, 0.5, 1, 2), 4);
});

test('skorRasio: all ratios zero gives 0', () => {
  assert.equal(F.skorRasio(0, 0, 0, 0.5, 1, 2), 0);
});

test('skorRasio: RI >= a with RN < b caps RI at a', () => {
  // A = 1, B = .5, C = 0: 3.75 * (1.5 - .5) = 3.75
  dekat(F.skorRasio(0.8, 0.5, 0, 0.5, 1, 2), 3.75);
});

test('skorRasio: RN >= b with RI < a caps RN at b', () => {
  // A = 0, B = 1, C = 0: 3.75 * 1
  dekat(F.skorRasio(0, 2, 0, 0.5, 1, 2), 3.75);
});

test('skorRasio: RW >= c caps RW at c', () => {
  // A = 0, B = 0, C = 1: 3.75 * (1/2); just above c too (uncapped would be 2.34)
  dekat(F.skorRasio(0, 0, 5, 0.5, 1, 2), 1.875);
  dekat(F.skorRasio(0, 0, 2.5, 0.5, 1, 2), 1.875);
});

// ----------------------------------------------------------------- butir 33
test('butir 33: publications DTPS, 3-year window', () => {
  const D = { dtps: { jumlah: 4 }, akreditasi: { publikasi_dtps: [
    { tahun: 2023, na4: 9 },                 // outside the window
    { tahun: 2024, na1: 4 },
    { tahun: 2025, na4: 1 },
    { tahun: 2026, na2: 2 },
  ] } };
  // RI = 1/4, RN = 2/4, RW = 4/4 with a .5, b 1, c 2 -> A = B = C = .5
  dekat(F.run('butir33', { D, TS }), 3.046875);
});

test('butir 33: no DTPS gives no score', () => {
  assert.equal(F.run('butir33', { D: { dtps: { jumlah: 0 } }, TS }), null);
});

// ----------------------------------------------------------------- butir 35
const rinci35 = slugs => ({ dtps: { jumlah: 4, karya_utama_rinci: slugs } });

test('butir 35: PKDTPS 25% -> 1 + 6 * .25', () => {
  const D = rinci35([{ slug: 'a', tahun: 2025 }, { slug: 'a', tahun: 2026 },
                     { slug: 'c', tahun: 2023 }]);   // c outside the window
  dekat(F.run('butir35', { D, TS }), 2.5);
});

test('butir 35: PKDTPS exactly 50% -> 4', () => {
  const D = rinci35([{ slug: 'a', tahun: 2024 }, { slug: 'b', tahun: 2026 }]);
  assert.equal(F.run('butir35', { D, TS }), 4);
});

test('butir 35: no main work -> minimum 1', () => {
  assert.equal(F.run('butir35', { D: rinci35([]), TS }), 1);
});

// ----------------------------------------------------------------- butir 36
// Tanpa isian manual kib_3th (pemilik 2026-11-10): KIB hanya dari sitasi per tahun.
const pubSitasi = n => Array.from({ length: n }, (_, i) => ({ judul: 'P' + i, kategori: 'publikasi', jenis: 'jurnal',
  indeksasi: 'scopus_q2', tahun: TS - 2, karya_sitasi: [{ tahun: TS, jumlah: 1 }] }));
test('butir 36: PKIB 12.5% -> 2 + 8 * .125', () => {
  dekat(F.run('butir36', { D: { dtps: { jumlah: 8 } }, TS, KARYA_SITASI: pubSitasi(1) }), 3);
});

test('butir 36: PKIB >= 25% -> 4', () => {
  assert.equal(F.run('butir36', { D: { dtps: { jumlah: 8 } }, TS, KARYA_SITASI: pubSitasi(2) }), 4);
});

test('butir 36: citations not loaded -> no score; loaded but none -> KIB 0 -> 2; manual entry ignored', () => {
  assert.equal(F.run('butir36', { D: { dtps: { jumlah: 8 } }, TS, PENG: { kib_3th: 5 } }), null);
  assert.equal(F.run('butir36', { D: { dtps: { jumlah: 8 } }, TS, PENG: { kib_3th: 5 }, KARYA_SITASI: [] }), 2);
});

// Sitasi per tahun (pemilik 2026-11-10): KIB = judul Tabel 4.i untuk TS ini.
test('butir 36: KIB dihitung otomatis dari sitasi per tahun, mengalahkan isian manual', () => {
  const pub = (judul, sitasi, extra = {}) => ({ judul, kategori: 'publikasi', jenis: 'jurnal', indeksasi: 'scopus_q2',
    tahun: TS - 2, karya_sitasi: sitasi.map(([tahun, jumlah]) => ({ tahun, jumlah })), ...extra });
  const KARYA_SITASI = [
    pub('A', [[TS, 1]]),
    pub('B', [[TS - 3, 2]]),                        // tahun awal TS-2: masih beririsan
    pub('C', [[TS - 4, 9]]),                        // di luar jendela
    pub('D', [[TS, 5]], { indeksasi: 'sinta_1_2' }), // bukan Scopus/WoS
  ];
  // KIB 2 dari 8 DTPS = 25% -> 4 (isian manual diabaikan).
  assert.equal(F.run('butir36', { D: { dtps: { jumlah: 8 } }, TS, PENG: { kib_3th: 0 }, KARYA_SITASI }), 4);
  // KIB 2 dari 16 = 12,5% -> 3
  dekat(F.run('butir36', { D: { dtps: { jumlah: 16 } }, TS, KARYA_SITASI }), 3);
  // Belum ada sitasi untuk TS ini -> KIB 0 -> skor terendah 2 (isian manual diabaikan).
  assert.equal(F.run('butir36', { D: { dtps: { jumlah: 8 } }, TS, PENG: { kib_3th: 1 }, KARYA_SITASI: [pub('C', [[TS - 4, 9]])] }), 2);
});

// ----------------------------------------------------------------- butir 37
test('butir 37: counts lecturers, not recognitions', () => {
  const D = { dtps: { jumlah: 8 }, akreditasi: { rekognisi_dtps: [
    { slug: 'a', tahun: 2026 }, { slug: 'a', tahun: 2025 },  // a counted once
    { slug: 'b', tahun: 2024 }, { slug: 'c', tahun: 2023 },  // c outside
  ] } };
  // PRDTPS = 2/8 = .25 -> 2 + 4 * .25
  dekat(F.run('butir37', { D, TS }), 3);
});

// ------------------------------------------------------------ butir 49 - 51
// Tracer window is graduation years TS-2..TS-1 = 2024..2025.
const tracer = rows => ({ tracer: rows });
const LUAR = [{ tahun_lulus: 2023, lulusan: 99, terlacak: 50, waktu_tunggu_bulan: 30,
                sesuai_bidang: 0, kerja_internasional: 50 },
              { tahun_lulus: 2026, lulusan: 99, terlacak: 50, waktu_tunggu_bulan: 30 }];

test('butir 49: traced-weighted waiting time 7 months -> (23 - 7)/5', () => {
  const D = tracer([...LUAR,
    { tahun_lulus: 2024, lulusan: 20, terlacak: 10, waktu_tunggu_bulan: 2 },
    { tahun_lulus: 2025, lulusan: 20, terlacak: 10, waktu_tunggu_bulan: 12 }]);
  // WT = (2*10 + 12*10) / 20 = 7
  dekat(F.run('butir49', { D, TS }), 3.2);
});

test('butir 49: WT <= 3 -> 4; WT > 18 -> 1', () => {
  const satu = wt => tracer([{ tahun_lulus: 2025, lulusan: 10, terlacak: 10, waktu_tunggu_bulan: wt }]);
  assert.equal(F.run('butir49', { D: satu(3), TS }), 4);
  assert.equal(F.run('butir49', { D: satu(20), TS }), 1);
  assert.equal(F.run('butir49', { D: satu(18), TS }), 1);   // (23 - 18)/5
});

test('butir 49: nobody traced in the window -> no score', () => {
  assert.equal(F.run('butir49', { D: tracer(LUAR), TS }), null);
});

test('butir 50: KBK 45% -> 20 * .45 / 3', () => {
  const D = tracer([...LUAR,
    { tahun_lulus: 2024, lulusan: 20, terlacak: 10, sesuai_bidang: 5 },
    { tahun_lulus: 2025, lulusan: 20, terlacak: 10, sesuai_bidang: 4 }]);
  dekat(F.run('butir50', { D, TS }), 3);
});

test('butir 50: KBK >= 60% -> 4', () => {
  const D = tracer([{ tahun_lulus: 2025, lulusan: 10, terlacak: 10, sesuai_bidang: 6 }]);
  assert.equal(F.run('butir50', { D, TS }), 4);
});

test('butir 50: Sedang + Tinggi of Table 6.f.2; year without levels uses old field (owner 2026-11-05)', () => {
  // 2024: levels filled, sedang 2 + tinggi 1 of 10; 2025: no levels, sesuai_bidang 3 of 10 -> 6/20 = 30%
  const D = tracer([...LUAR,
    { tahun_lulus: 2024, lulusan: 20, terlacak: 10, sesuai_bidang: 9,
      kesesuaian_rendah: 7, kesesuaian_sedang: 2, kesesuaian_tinggi: 1 },
    { tahun_lulus: 2025, lulusan: 20, terlacak: 10, sesuai_bidang: 3,
      kesesuaian_rendah: null, kesesuaian_sedang: null, kesesuaian_tinggi: null }]);
  dekat(F.run('butir50', { D, TS }), 2);
});

test('butir 49: bands only check the mean; score still from the mean', () => {
  const D = tracer([{ tahun_lulus: 2025, lulusan: 10, terlacak: 10, waktu_tunggu_bulan: 2,
                      wt_kurang_3: 2, wt_3_18: 8, wt_lebih_18: 0 }]);   // possible mean 2.4..15: does not match
  assert.equal(F.run('butir49', { D, TS }), 4);
});

test('butir 51: workplace level against all graduates (NL)', () => {
  const D = tracer([...LUAR,
    { tahun_lulus: 2024, lulusan: 20, terlacak: 10,
      kerja_internasional: 1, kerja_nasional: 2, kerja_wilayah: 9 },
    { tahun_lulus: 2025, lulusan: 20, terlacak: 10,
      kerja_internasional: 0, kerja_nasional: 2, kerja_wilayah: 9 }]);
  // NL 40: RI 1/40 = .025, RN 4/40 = .1, RW 18/40 = .45;
  // a .05, b .2, c .9 -> A = B = C = .5 -> 3.046875
  dekat(F.run('butir51', { D, TS }), 3.046875);
});

test('butir 51: no workplace data -> no score', () => {
  const D = tracer([{ tahun_lulus: 2025, lulusan: 10, terlacak: 5 }]);
  assert.equal(F.run('butir51', { D, TS }), null);
});
