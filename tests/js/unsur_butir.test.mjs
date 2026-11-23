// Butir 20, 22, 24 from evidence per element (owner 2026-11-10;
// supabase/instal-lengkap.sql). APS-AV 2025 Sarjana matrix: 4 = elements
// (1)-(4), 3 = (1)-(3), 2 = (1)+(2), 1 = only (1), 0 = none.
// Fictitious data. Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { skorUnsur, berlakuTS, hitungUnsur, UNSUR } from '../../site/unsur-butir.js';
import { loadFormulas } from './score_harness.mjs';

const F = loadFormulas();
const TS = 2026;
const b = (tabel, baris_id, ...unsur) => unsur.map(u => ({ tabel, baris_id, unsur: u }));

test('skorUnsur counts consecutive elements from element 1', () => {
  assert.equal(skorUnsur(new Set([1, 2, 3, 4])), 4);
  assert.equal(skorUnsur(new Set([1, 2, 3])), 3);
  assert.equal(skorUnsur(new Set([1, 2, 4])), 2);   // gap at 3
  assert.equal(skorUnsur(new Set([1])), 1);
  assert.equal(skorUnsur(new Set([2, 3, 4])), 0);   // element 1 missing
  assert.equal(skorUnsur(new Set()), 0);
});

test('four elements each for capstone and road map', () => {
  assert.equal(UNSUR.capstone.length, 4);
  assert.equal(UNSUR.peta_jalan.length, 4);
});

test('berlakuTS: start <= TS, end >= TS-1, empty = open', () => {
  assert.ok(berlakuTS({ tahun_mulai: 2022, tahun_selesai: 2026 }, TS));
  assert.ok(berlakuTS({ tahun_mulai: 2021, tahun_selesai: 2025 }, TS));   // TS 2025/2026
  assert.ok(!berlakuTS({ tahun_mulai: 2018, tahun_selesai: 2024 }, TS));
  assert.ok(!berlakuTS({ tahun_mulai: 2027 }, TS));
  assert.ok(berlakuTS({}, TS));
});

test('butir 20: only capstone MK count, best one used', () => {
  const mk = [{ id: 1, kode: 'SI1', nama: 'Capstone A', capstone: true },
              { id: 2, kode: 'SI2', nama: 'Capstone B', capstone: true },
              { id: 3, kode: 'SI3', nama: 'Biasa', capstone: false }];
  const bukti = [...b('ref_mata_kuliah', 1, 1, 2), ...b('ref_mata_kuliah', 2, 1, 2, 3),
                 ...b('ref_mata_kuliah', 3, 1, 2, 3, 4), ...b('lkps_peta_jalan', 1, 1, 2, 3, 4)];
  const h = hitungUnsur('20', { mk, bukti, ts: TS });
  assert.equal(h.skor, 3);
  assert.equal(h.terbaik.label, 'SI2 Capstone B');
  assert.equal(h.rinci.length, 2);
});

test('butir 20: no evidence or no capstone MK scores 0; data not loaded = null', () => {
  assert.equal(hitungUnsur('20', { mk: [{ id: 1, capstone: true }], bukti: [], ts: TS }).skor, 0);
  assert.equal(hitungUnsur('20', { mk: [{ id: 1, capstone: false }], bukti: [], ts: TS }).skor, 0);
  assert.equal(hitungUnsur('20', { mk: [{ id: 1, capstone: false }], bukti: [], ts: TS }).terbaik, null);
  assert.equal(hitungUnsur('20', { mk: [{ id: 1, capstone: true }], bukti: null, ts: TS }), null);
  assert.equal(hitungUnsur('20', { mk: null, bukti: [], ts: TS }), null);
});

test('butir 22/24: road map by kind, valid in TS', () => {
  const peta = [{ id: 1, jenis: 'penelitian', judul: 'RIP 2022-2026', tahun_mulai: 2022, tahun_selesai: 2026 },
                { id: 2, jenis: 'pkm', judul: 'Renstra PkM', tahun_mulai: 2022 },
                { id: 3, jenis: 'penelitian', judul: 'RIP lama', tahun_mulai: 2015, tahun_selesai: 2019 }];
  const bukti = [...b('lkps_peta_jalan', 1, 1, 2, 3, 4), ...b('lkps_peta_jalan', 2, 1, 3),
                 ...b('lkps_peta_jalan', 3, 1, 2, 3, 4), ...b('ref_mata_kuliah', 2, 1, 2)];
  assert.equal(hitungUnsur('22', { peta, bukti, ts: TS }).skor, 4);
  assert.equal(hitungUnsur('22', { peta, bukti, ts: TS }).rinci.length, 1);   // old one not valid
  assert.equal(hitungUnsur('24', { peta, bukti, ts: TS }).skor, 1);           // 1 and 3: gap at 2
  assert.equal(hitungUnsur('22', { peta: [peta[2]], bukti, ts: TS }).skor, 0);  // none valid -> 0
});

test('IS b20/b22/b24: from evidence only, manual entry ignored', () => {
  const MK_DATA = [{ id: 7, kode: 'SI7', nama: 'Capstone', capstone: true }];
  const PETA_JALAN = [{ id: 1, jenis: 'penelitian', judul: 'RIP', tahun_mulai: 2022 }];
  const UNSUR_BUKTI = [...b('ref_mata_kuliah', 7, 1, 2), ...b('lkps_peta_jalan', 1, 1, 2, 3)];
  const st = { TS, MK_DATA, PETA_JALAN, UNSUR_BUKTI, PENG: { b20: 4, b22: 1, b24: 2 } };
  assert.equal(F.run('IS', st, 'b20'), 2);
  assert.equal(F.run('IS', st, 'b22'), 3);
  assert.equal(F.run('IS', st, 'b24'), 0);           // no PkM road map -> 0
  assert.equal(F.run('IS', { TS, PENG: { b20: 4 } }, 'b20'), null);   // nothing loaded -> no score
});

test('catatanUnsur names the elements and the score', () => {
  const st = { TS, MK_DATA: [{ id: 7, kode: 'SI7', nama: 'Capstone', capstone: true }],
               UNSUR_BUKTI: b('ref_mata_kuliah', 7, 1, 2, 4) };
  const c = F.run('catatanUnsur', st, '20');
  assert.match(c, /SI7 Capstone/);
  assert.match(c, /\(1\) ada, \(2\) ada, \(3\) belum, \(4\) ada/);
  assert.match(c, /Skor = 2/);
  assert.match(F.run('catatanUnsur', { TS }, '22'), /belum terbaca/);
  assert.match(F.run('catatanUnsur', { TS, PETA_JALAN: [], UNSUR_BUKTI: [] }, '22'), /skor 0/);
});

// ---- butir 38, 39, 48, 53-60 from evidence on the item card (owner 2026-11-10)
import { UNSUR_BUTIR, skorKunci, unsurAda, KUNCI_UNSUR } from '../../site/unsur-butir.js';
const bb = (no, ...unsur) => unsur.map(u => ({ tabel: 'butir', baris_id: +no, unsur: u }));
const sk = (kunci, ...xs) => skorKunci(kunci, xs.flat());

test('every element-based item has labels for all its numbers', () => {
  for (const [no, d] of Object.entries(UNSUR_BUTIR))
    for (const k of d.komponen) for (const n of k.nomor) assert.ok(d.unsur[n], `${no} unsur ${n}`);
  assert.equal(Object.keys(KUNCI_UNSUR).length, 36);
});

test('no evidence for the item -> 0; not loaded or not element-based -> null', () => {
  assert.equal(sk('b39', bb(38, 1)), 0);
  assert.equal(skorKunci('b39', null), null);
  assert.equal(sk('b21', bb(21, 1)), null);           // not an element-based item
});

test('38: I consecutive (min 1), II count (min 2)', () => {
  assert.equal(sk('b38_i', bb(38, 1, 2, 3, 4)), 4);
  assert.equal(sk('b38_i', bb(38, 2, 3, 5)), 1);
  assert.equal(sk('b38_ii', bb(38, 5, 6, 7)), 4);
  assert.equal(sk('b38_ii', bb(38, 5, 7)), 3);
  assert.equal(sk('b38_ii', bb(38, 1)), 2);
});

test('39, 54, 55, 56: consecutive, min 1', () => {
  assert.equal(sk('b39', bb(39, 1, 2, 3)), 3);
  assert.equal(sk('b54', bb(54, 1, 2, 4)), 2);
  assert.equal(sk('b55', bb(55, 4)), 1);
  assert.equal(sk('b56', bb(56, 1, 2, 3, 4)), 4);
});

test('48: 5 aspects -> 4 ... 2 -> 1, min 1', () => {
  assert.equal(sk('b48', bb(48, 1, 2, 3, 4, 5)), 4);
  assert.equal(sk('b48', bb(48, 1, 3, 5)), 2);
  assert.equal(sk('b48', bb(48, 2)), 1);
});

test('53: I documents consecutive; II tiers', () => {
  assert.equal(sk('b53_i', bb(53, 1, 2, 3, 4)), 4);
  assert.equal(sk('b53_i', bb(53, 2, 5)), 0);
  assert.equal(sk('b53_ii', bb(53, 5, 6, 7, 8, 9, 11)), 4);
  assert.equal(sk('b53_ii', bb(53, 5, 6, 7, 8, 9, 10)), 3);
  assert.equal(sk('b53_ii', bb(53, 5, 6, 7, 8, 10)), 2);
  assert.equal(sk('b53_ii', bb(53, 5, 6, 7, 9, 10, 11)), 1);   // set incomplete
});

test('57: aspects 1-4 required; all stakeholders; 5 and 6 raise', () => {
  assert.equal(sk('b57', bb(57, 1, 2, 3, 4, 5, 6, 7)), 4);
  assert.equal(sk('b57', bb(57, 1, 2, 3, 4, 5, 7)), 3);
  assert.equal(sk('b57', bb(57, 1, 2, 3, 4, 5)), 2);
  assert.equal(sk('b57', bb(57, 2, 3, 4, 5, 6, 7)), 1);
  assert.equal(sk('b57', bb(57, 1, 2, 3, 5)), 0);
});

test('58: I and II consecutive', () => {
  assert.equal(sk('b58_i', bb(58, 1, 2, 3)), 3);
  assert.equal(sk('b58_ii', bb(58, 5, 6, 8)), 2);
  assert.equal(sk('b58_ii', bb(58, 1, 2)), 0);
});

test('59 and 60: base element required, then tiers', () => {
  assert.equal(sk('b59', bb(59, 1, 2, 3, 4, 5, 6)), 4);
  assert.equal(sk('b59', bb(59, 1, 2, 3, 4)), 2);
  assert.equal(sk('b59', bb(59, 1, 3)), 1);
  assert.equal(sk('b59', bb(59, 2, 3, 4, 5, 6)), 0);
  assert.equal(sk('b60', bb(60, 1, 2, 3, 4, 5, 6)), 4);
  assert.equal(sk('b60', bb(60, 1, 2, 3, 4, 6)), 3);
  assert.equal(sk('b60', bb(60, 1, 2, 3, 4, 5)), 2);   // no derived regulations
  assert.equal(sk('b60', bb(60, 1)), 1);
});

test('IS: from evidence only, manual entries ignored; unsurAda reads item rows only', () => {
  const st = { TS, UNSUR_BUKTI: bb(39, 1, 2), PENG: { b39: 4, b54: 3 } };
  assert.equal(F.run('IS', st, 'b39'), 2);
  assert.equal(F.run('IS', st, 'b54'), 0);
  assert.equal(F.run('IS', { TS, PENG: { b54: 3 } }, 'b54'), null);   // evidence not loaded
  assert.deepEqual([...unsurAda('39', [...bb(39, 1), { tabel: 'lkps_peta_jalan', baris_id: 39, unsur: 2 }])], [1]);
});

test('every qualitative item is element-based (owner 2026-11-10: no manual scores)', async () => {
  const { BUTIR_MANUAL } = await import('../../site/butir-manual.js');
  const sisa = BUTIR_MANUAL.filter(b => !b.hitung && !UNSUR_BUTIR[b.no] && !['20', '22', '24'].includes(b.no)).map(b => b.no);
  assert.deepEqual(sisa, []);
});

test('1-17, 21, 29: matrix tiers', () => {
  assert.equal(sk('b1', bb(1, 1)), 2);                    // floor 2
  assert.equal(sk('b1', bb(1, 1, 2, 3)), 3);
  assert.equal(sk('b2', bb(2, 1, 2, 3, 4)), 4);
  assert.equal(sk('b4_ii', bb(4, 5, 6)), 2);
  assert.equal(sk('b5_i', bb(5, 1, 3)), 3);
  assert.equal(sk('b5_i', bb(5, 2, 3)), 1);
  assert.equal(sk('b5_ii', bb(5, 4, 5, 6)), 3);
  assert.equal(sk('b5_ii', bb(5, 4, 5, 6, 7)), 4);
  assert.equal(sk('b7', bb(7, 1, 3)), 3);
  assert.equal(sk('b8', bb(8, 1, 2, 3, 4)), 3);
  assert.equal(sk('b8', bb(8, 1, 3, 4, 5)), 0);           // compliance missing
  assert.equal(sk('b12', bb(12, 1, 2, 3)), 2);
  assert.equal(sk('b13_i', bb(13, 1, 2, 3, 4, 5)), 4);
  assert.equal(sk('b13_ii', bb(13, 6, 9)), 2);
  assert.equal(sk('b14_i', bb(14, 1, 2, 3)), 3);
  assert.equal(sk('b14_ii', bb(14, 5, 6)), 3);
  assert.equal(sk('b15_i', bb(15, 1, 2, 3)), 4);
  assert.equal(sk('b15_i', bb(15, 4)), 1);
  assert.equal(sk('b15_ii', bb(15, 5, 6)), 2);
  assert.equal(sk('b16_ii', bb(16, 5, 6, 7, 8)), 4);
  assert.equal(sk('b17', bb(17, 2, 3, 4, 5)), 0);         // < 10% of core courses
  assert.equal(sk('b17', bb(17, 1, 2, 3)), 2);
  assert.equal(sk('b21_ii', bb(21, 5, 7)), 3);
  assert.equal(sk('b29', bb(29, 1, 2, 4)), 3);
  assert.equal(sk('b29', bb(29, 1, 5)), 1);               // qualification not shown
});

// ---- Penanggung jawab per unsur dan per butir (owner 2026-11-10)
import { PJ_UNSUR, pihakUnsur, pihakButir, PIHAK } from '../../site/unsur-butir.js';

test('every item 1-60 and every element has a responsible party', () => {
  for (let no = 1; no <= 60; no++) assert.ok(pihakButir(no), `butir ${no}`);
  for (const [no, d] of Object.entries(UNSUR_BUTIR))
    for (const n of Object.keys(d.unsur)) assert.ok(pihakUnsur(no, n), `${no} unsur ${n}`);
  for (const no of ['20', '22', '24']) for (let n = 1; n <= 4; n++) assert.ok(pihakUnsur(no, n), `${no} unsur ${n}`);
  for (const u of Object.values(PJ_UNSUR)) for (const k of Object.values(u).flat()) assert.ok(PIHAK[k], k);
});

test('responsible party text', () => {
  assert.equal(pihakUnsur(1, 1), 'UPPS, Universitas');
  assert.equal(pihakUnsur(53, 3), 'SPM');
  assert.equal(pihakButir(16), 'Prodi, SPM');
  assert.equal(pihakButir(36), 'Dosen');
});

test('every recommended evidence item of data-based items has a responsible party', async () => {
  const { RENCANA_BUKTI } = await import('../../site/rencana-bukti.js');
  const { PJ_BUKTI, pihakBukti } = await import('../../site/unsur-butir.js');
  for (const [no, r] of Object.entries(RENCANA_BUKTI)) {
    if (UNSUR_BUTIR[no] || ['20', '22', '24'].includes(no)) continue;
    assert.equal((PJ_BUKTI[no] || []).length, r.bukti.length, `butir ${no}`);
    r.bukti.forEach((_, i) => assert.ok(pihakBukti(no, i), `butir ${no} bukti ${i + 1}`));
  }
  assert.equal(pihakBukti(6, 1), 'Prodi, Dosen');
});

// ---- Butir 15 unsur 1/4 dari RPS mata kuliah (instal-lengkap.sql; owner 2026-11-10)
test('butir 15: RPS elements 1 and 4 come from the course list', () => {
  const mk = (rps_ada, rps_9_komponen, rps_url = null) => ({ kode: 'X', rps_ada, rps_9_komponen, rps_url });
  const UNSUR_BUKTI = [...bb(15, 1, 4, 2, 3)];   // uploaded 1 and 4 are ignored
  const st = MK_DATA => ({ TS, MK_DATA, UNSUR_BUKTI });
  // all courses complete -> element 1 (+ uploaded 2, 3) -> I = 4
  assert.equal(F.run('IS', st([mk(true, true), mk(false, true, 'https://x')]), 'b15_i'), 4);
  // one course incomplete -> element 4 only -> I = 1
  assert.equal(F.run('IS', st([mk(true, true), mk(true, false)]), 'b15_i'), 1);
  // no RPS at all -> neither -> I = 0
  assert.equal(F.run('IS', st([mk(false, false)]), 'b15_i'), 0);
  // no active courses -> nothing derived
  assert.equal(F.run('IS', st([]), 'b15_i'), 0);
  const r = F.run('rpsMK', st([mk(true, true), mk(true, null), mk(false, false)]));
  assert.deepEqual([r.n, r.ada, r.lengkap, r.belum.length], [3, 2, 1, 2]);
});

// ---- Langkah tercepat (owner 2026-11-11)
test('langkahTercepat: next element per item, ranked by weighted gain', () => {
  const xs = F.run('langkahTercepat', { TS, MK_DATA: [], UNSUR_BUKTI: bb(39, 1, 2) });
  const k39 = xs.filter(x => x.no === '39');
  assert.equal(JSON.stringify(k39.map(x => x.n)), '[3]');   // only the next consecutive element raises the score
  assert.equal(k39[0].kini, 2); assert.equal(k39[0].baru, 3);
  for (let i = 1; i < xs.length; i++) assert.ok(xs[i - 1].naik >= xs[i].naik);
  assert.ok(!xs.some(x => x.no === '15' && [1, 4].includes(x.n)));
  assert.equal(F.run('langkahTercepat', { TS, UNSUR_BUKTI: null }), null);
});

test('butir 15: unsur 5-8 dari tinjauan RPS (115) bila semua MK semester terbaru disetujui', () => {
  const xs = F.run('buktiEfektif', { TS, MK_DATA: [], UNSUR_BUKTI: [], TINJAU: { unsur: [5, 6, 7, 8] } });
  assert.equal(JSON.stringify(xs.filter(b => +b.baris_id === 15).map(b => +b.unsur)), '[5,6,7,8]');   // larik dari konteks vm
  assert.equal(F.run('buktiEfektif', { TS, MK_DATA: [], UNSUR_BUKTI: [], TINJAU: { unsur: [] } }).length, 0);
});
