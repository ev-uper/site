// Remaining computed butir of site/skor.html (6, 9-11, 19, 23/25, 26-28,
// 31/32, 34, 40-42, 47) against hand-computed values (owner 2026-11-04).
// Calls with parameters use the same arguments as render() in skor.html.
// Working in the comments. Fictitious data. Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { loadFormulas } from './score_harness.mjs';

const F = loadFormulas();
const TS = 2026;                       // 3-year window 2024..2026
const dekat = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} != ${b}`);
const dtps = (jumlah, lain = {}) => ({ dtps: { jumlah, ...lain } });

// ------------------------------------------------------------------ butir 6
test('butir 6: (I + 2*II)/3, I = RK capped at 4, II = skorRasio a2 b6 c8', () => {
  const D = { ...dtps(4), akreditasi: { kerjasama: [
    { tahun: 2023, internasional: 9 },                                   // outside
    { tahun: 2025, internasional: 1, nasional: 3, wilayah: 4, tanpa_tingkat: 0, pendidikan: 2 },
  ] } };
  // I: RK = 8/4 = 2; II: A = B = C = .5 -> 3.046875
  dekat(F.run('butir06', { D, TS }), (2 + 2 * 3.046875) / 3);
});

test('butir 6: RK above 4 is capped', () => {
  const D = { ...dtps(1), akreditasi: { kerjasama: [
    { tahun: 2026, internasional: 2, nasional: 6, wilayah: 8 }] } };
  // I: min(4, 16) = 4; II: RI = a and RN = b exactly -> A = B = 1 -> 3.75
  dekat(F.run('butir06', { D, TS }), (4 + 2 * 3.75) / 3);
});

// ------------------------------------------------------------- butir 9-11
test('butir 9: BOP below Rp20 million -> value / 5 million', () => {
  const st = bop => ({ TS, DANA_PRODI: [{ tahun_akademik: `${TS - 1}/${TS}`, jenis: 'biaya_dosen', dana_ps: bop * 100 }],
    MHS_TA: [{ tahun_akademik: `${TS - 1}/${TS}`, jumlah_mahasiswa_aktif: 100 }] });
  dekat(F.run('butirDana', st(10000000), 9, 'BOP', 'bop', 20000000, 1), 2);
  assert.equal(F.run('butirDana', st(20000000), 9, 'BOP', 'bop', 20000000, 1), 4);
  assert.equal(F.run('butirDana', { PENG: { bop: 20000000 } }, 9, 'BOP', 'bop', 20000000, 1), null);   // manual ignored
});

// Pemilik 2026-11-10: BOP dari Data prodi (Tabel 2.b baris a-f, dana PS) ÷ mahasiswa aktif, rata-rata TS-2..TS.
test('butir 9: BOP hanya dari Data prodi, isian manual diabaikan', () => {
  const DANA_PRODI = [
    { tahun_akademik: `${TS - 1}/${TS}`, jenis: 'biaya_dosen', dana_ps: 1500000000 },
    { tahun_akademik: `${TS - 1}/${TS}`, jenis: 'investasi', dana_ps: 500000000 },
    { tahun_akademik: `${TS - 1}/${TS}`, jenis: 'kemahasiswaan', dana_ps: 999000000 },   // bukan BOP
    { tahun_akademik: `${TS - 2}/${TS - 1}`, jenis: 'operasional_pembelajaran', dana_ps: 1000000000 },
    { tahun_akademik: `${TS - 5}/${TS - 4}`, jenis: 'biaya_dosen', dana_ps: 9e12 },        // di luar jendela
  ];
  const MHS_TA = [{ tahun_akademik: `${TS - 1}/${TS}`, jumlah_mahasiswa_aktif: 200 },
                  { tahun_akademik: `${TS - 2}/${TS - 1}`, jumlah_mahasiswa_aktif: 100 }];
  // TS: 2 M / 200 = 10 jt; TS-1: 1 M / 100 = 10 jt -> rata-rata 10 jt -> skor 2, walaupun isian manual 20 jt.
  dekat(F.run('butirDana', { TS, DANA_PRODI, MHS_TA, PENG: { bop: 20000000 } }, 9, 'BOP', 'bop', 20000000, 1), 2);
  // Data prodi kosong -> belum ada data (isian manual diabaikan).
  assert.equal(F.run('butirDana', { TS, DANA_PRODI: [], MHS_TA: [], PENG: { bop: 20000000 } }, 9, 'BOP', 'bop', 20000000, 1), null);
});

test('butir 10: research funds per DTPS per year, TS from month', () => {
  const DANA = [
    { kategori: 'penelitian', tahun: 2025, bulan: 3, besaran_dana: 6000000 },   // TS 2025
    { kategori: 'penelitian', tahun: 2025, bulan: 10, besaran_dana: 6000000 },  // TS 2026
    { kategori: 'penelitian', tahun: 2023, bulan: 9, besaran_dana: 3000000 },   // TS 2024
    { kategori: 'penelitian', tahun: 2023, bulan: 8, besaran_dana: 99000000 },  // TS 2023, outside
    { kategori: 'pkm', tahun: 2026, bulan: 1, besaran_dana: 50000000 },         // other category
  ];
  // 15 million / 3 years / 2 DTPS = 2.5 million -> 2 * 2.5 / 5
  dekat(F.run('butirDanaKarya', { D: dtps(2), TS, DANA }, 10, 'Dana penelitian', 'penelitian', 10000000, 2), 1);
});

test('butir 11: PkM funds with factor 4', () => {
  const DANA = [{ kategori: 'pkm', tahun: 2026, bulan: 1, besaran_dana: 3000000 }];
  // 3 million / 3 / 2 = .5 million -> 4 * .5 / 5
  dekat(F.run('butirDanaKarya', { D: dtps(2), TS, DANA }, 11, 'Dana PkM', 'pkm', 5000000, 4), 0.4);
});

// ----------------------------------------------------------------- butir 19
test('butir 19: discrete SKS bands; manual entry ignored', () => {
  const s = v => F.run('butir19', { MK_DATA: [{ kode: 'B', basic_science: true, sks: v }] });
  assert.deepEqual([s(25), s(22), s(15), s(10), s(9)], [4, 3, 2, 1, 0]);
  assert.equal(F.run('butir19', { MK_DATA: [], PENG: { sks_basic_sciences: 29 } }), 0);    // no MK -> 0 SKS
  assert.equal(F.run('butir19', { PENG: { sks_basic_sciences: 29 } }), null);              // MK not loaded
});

// Pemilik 2026-11-10: SKS dari mata kuliah aktif bertanda basic science; komponen SKS didahulukan.
test('butir 19 dan 18: dihitung dari mata kuliah aktif', () => {
  const MK_DATA = [
    { kode: 'A', basic_science: true, sks: 3 },
    { kode: 'B', basic_science: true, sks_kuliah: 3, sks_praktikum: 1 },          // 4 SKS
    { kode: 'C', basic_science: false, sks_kuliah: 2, sks_seminar: 0, sks_praktikum: 2 },
  ];
  // 3 + 4 = 7 SKS basic sciences -> skor 0 (isian manual diabaikan).
  assert.equal(F.run('butir19', { MK_DATA, PENG: { sks_basic_sciences: 25 } }), 0);
  // JP = (1 + 2) × 50 = 150; JB = (3 + 4 + 4) × 50 = 550.
  assert.equal(F.run('IS', { MK_DATA }, 'jp_jam'), 150);
  assert.equal(F.run('IS', { MK_DATA }, 'jb_jam'), 550);
  // Tanpa SKS praktikum sama sekali -> JP 0 (isian manual diabaikan).
  assert.equal(F.run('IS', { MK_DATA: [{ kode: 'X', sks: 3 }], PENG: { jp_jam: 7 } }, 'jp_jam'), 0);
});

// ------------------------------------------------------------ butir 23/25
test('butir 23: share of research titles with students', () => {
  const D = { akreditasi: { kegiatan_mhs: [
    { tahun: 2025, kategori: 'penelitian', total: 8, dengan_mahasiswa: 2 },
    { tahun: 2026, kategori: 'penelitian', total: 2, dengan_mahasiswa: 0 },
    { tahun: 2023, kategori: 'penelitian', total: 9, dengan_mahasiswa: 9 },   // outside
    { tahun: 2026, kategori: 'pkm', total: 4, dengan_mahasiswa: 4 },          // other category
  ] } };
  // 2/10 = .2 -> 1 + 6 * .2
  dekat(F.run('butirKegMhs', { D, TS }, 23, 'Penelitian', 'penelitian'), 2.2);
  assert.equal(F.run('butirKegMhs', { D, TS }, 25, 'PkM', 'pkm'), 4);
});

// ----------------------------------------------------------------- butir 26
test('butir 26: DTPS sufficiency bands', () => {
  // NDTT dari dosen berkategori; NDT dipaksa = NDTPS (kategori tetap tidak lebih banyak).
  const kat = ndtt => [{ kategori: 'tetap', aktif: true, peran: 'dosen' },
    ...Array(ndtt).fill({ kategori: 'tidak_tetap', aktif: true, peran: 'dosen' })];
  const s = (n, ndtt) => F.run('butir26', { D: dtps(n), DOSEN_KAT: kat(ndtt) });
  dekat(s(12, 3), 2 + 2 * (20 / 30));               // PDTT 20%, NDTPS >= 12
  dekat(s(8, 2), 2 + 2 * ((3 / 7) * (20 / 40)));    // PDTT 20%, 5 <= NDTPS < 12
  assert.equal(s(12, 1), 4);                        // PDTT 7.7%
  assert.equal(s(12, 10), 2);                       // PDTT 45% > 40%
  assert.equal(s(4, 0), 0);                         // NDTPS < 5
});

// Pemilik 2026-11-10: NDT = kategori tetap (termasuk lintas prodi), NDTT = tidak tetap + industri.
test('butir 26: NDT dan NDTT dari kategori dosen di Kelola dosen', () => {
  const dosen = (tetap, tt, ind, lain = []) => [
    ...Array(tetap).fill({ kategori: 'tetap', aktif: true, peran: 'dosen' }),
    ...Array(tt).fill({ kategori: 'tidak_tetap', aktif: true, peran: 'dosen' }),
    ...Array(ind).fill({ kategori: 'industri', aktif: true, peran: 'dosen' }), ...lain];
  const tak = [{ kategori: 'tidak_tetap', aktif: false, peran: 'dosen' },      // tidak aktif
               { kategori: 'tetap', aktif: true, peran: 'asesor' },            // asesor
               { kategori: null, aktif: true, peran: 'admin' }];               // staf tanpa kategori
  // 12 DTPS + 3 tetap lintas prodi = NDT 15; NDTT 1 + 1 = 2 -> PDTT 2/17 = 11,8% -> 2 + 2*(40-11.76)/30
  dekat(F.run('butir26', { D: dtps(12), DOSEN_KAT: dosen(15, 1, 1, tak), PENG: { ndtt: 99 } }), 2 + 2 * ((40 - 200 / 17) / 30));
  // Kategori tetap kurang dari NDTPS -> NDT memakai NDTPS: 12 DTPS, 5 tetap, NDTT 1 -> 1/13 = 7,7% -> 4
  assert.equal(F.run('butir26', { D: dtps(12), DOSEN_KAT: dosen(5, 1, 0) }), 4);
  // Belum ada kategori -> belum ada data (isian manual ndtt diabaikan).
  assert.equal(F.run('butir26', { D: dtps(12), DOSEN_KAT: [{ kategori: null, aktif: true, peran: 'dosen' }], PENG: { ndtt: 1 } }), null);
});

// ------------------------------------------------------------- butir 27/28
test('butir 27: share of doctorates', () => {
  dekat(F.run('butir27', { D: dtps(10, { doktor: 3 }) }), 3.2);   // 2 + 4 * .3
  assert.equal(F.run('butir27', { D: dtps(10, { doktor: 5 }) }), 4);
});

test('butir 28: share of L + LK + GB', () => {
  const D = dtps(10, { jabatan: { asisten_ahli: 5, lektor: 3, lektor_kepala: 1, guru_besar: 1 } });
  dekat(F.run('butir28', { D }), 2 + 20 * 0.5 / 7);
});

// ------------------------------------------------------------ butir 31/32
test('butir 31: activities by funding source, per DTPS per year', () => {
  const D = { ...dtps(40), akreditasi: { sumber_dana: [
    { tahun: 2025, kategori: 'penelitian', luar_negeri: 3, dalam_negeri: 18, pt_mandiri: 60 },
    { tahun: 2023, kategori: 'penelitian', luar_negeri: 30 },                 // outside
  ] } };
  // /3/40: .025/.05, .15/.3, .5/1 -> A = B = C = .5
  dekat(F.run('butirDanaSumber', { D, TS }, 31, 'Penelitian', 'penelitian'), 3.046875);
  assert.equal(F.run('butirDanaSumber', { D, TS }, 32, 'PkM', 'pkm'), null);
});

// ----------------------------------------------------------------- butir 34
test('butir 34: RLP = (3 paten + 2 (TTG + BC) + HKI) / NDTPS', () => {
  const D = { ...dtps(4), akreditasi: { luaran_dtps: [
    { tahun: 2025, paten: 1, ttg: 1, bc: 1, hki: 1, lainnya: 5 }] } };
  // RLP = (3 + 4 + 1) / 4 = 2 -> 2 + 2*2/3
  dekat(F.run('butir34', { D, TS }), 2 + 4 / 3);
});

// ------------------------------------------------------------- butir 40-42
const taTS = (lain) => ({ akreditasi: { ta: [{ tahun_ts: 2026, ...lain }] } });

test('butir 40: student/DTPS ratio', () => {
  const s = (n, nm) => F.run('butir40', { D: { ...dtps(n), ...taTS({ mahasiswa_aktif: nm }) }, TS });
  assert.equal(s(12, 240), 4);                    // RMD 20
  dekat(s(12, 360), 2.5);                         // RMD 30: B = .5 -> 1 + 1.5
  dekat(s(12, 144), 3.4);                         // RMD 12: B = .8 -> 1 + 2.4
  dekat(s(8, 160), 1 + 3 * (3 / 7));              // RMD 20, NDTPS 8: A = 3/7
  assert.equal(s(12, 480), 0);                    // RMD 40 > 35
});

test('butir 41: share of foreign students', () => {
  const s = (asing) => F.run('butir41', { D: taTS({ mahasiswa_aktif: 400, mahasiswa_asing: asing }), TS });
  dekat(s(2), 3);                                 // .5% -> 2 + 200 * .005
  assert.equal(s(4), 4);                          // 1%
});

test('butir 42: graduate-weighted GPA over 3 TS', () => {
  const D = { akreditasi: { ta: [
    { tahun_ts: 2026, lulusan: 10, rerata_ipk: 3.0 },
    { tahun_ts: 2025, lulusan: 30, rerata_ipk: 3.2 },
    { tahun_ts: 2023, lulusan: 99, rerata_ipk: 2.0 },                        // outside
  ] } };
  // RIPK = (30 + 96) / 40 = 3.15 -> (8 * 3.15 - 6) / 5
  dekat(F.run('butir42', { D, TS }), 3.84);
  const satu = ipk => ({ akreditasi: { ta: [{ tahun_ts: 2026, lulusan: 10, rerata_ipk: ipk }] } });
  assert.equal(F.run('butir42', { D: satu(3.25), TS }), 4);
  assert.equal(F.run('butir42', { D: satu(2.0), TS }), 2);                  // floor 2
});

// ----------------------------------------------------------------- butir 47
test('butir 47: NLP = 3 paten + 2 (TTG + BC) + HKI', () => {
  const D = { akreditasi: { luaran_mhs: [{ tahun: 2025, paten: 1, ttg: 1, hki: 2, lainnya: 3 }] } };
  dekat(F.run('butir47', { D, TS }), 3.4);       // NLP 7 -> 2 + .2 * 7
});
