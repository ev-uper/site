// Pertanyaan pemandu dan arti skor review RPS (pemilik 2026-11-24). Jawaban disimpan di catatan dengan kunci '?<kode>.<n>'.
import test from 'node:test';
import assert from 'node:assert/strict';
import { BUTIR_REVIEW, PEMANDU_REVIEW, kunciTanya, jawabanPemandu, ringkasPemandu, butirTanggapan, rerataReview,
  saranSkor, saranKesimpulan, periksaKirimReview } from '../../site/rps.js';

test('setiap butir punya 3-4 pertanyaan pemandu dan arti untuk skor 1-4', () => {
  assert.deepEqual(Object.keys(PEMANDU_REVIEW).sort(), BUTIR_REVIEW.map(b => b.kode).sort());
  for (const [k, p] of Object.entries(PEMANDU_REVIEW)) {
    assert.ok(p.tanya.length >= 3 && p.tanya.length <= 4, k);
    assert.ok(p.tanya.every(t => t.trim().endsWith('?')), k);
    assert.equal(p.arti.length, 4, k);
  }
});

test('jawaban pemandu terbaca dari catatan dan tidak mengubah rerata skor', () => {
  assert.equal(kunciTanya('B2', 0), '?B2.1');
  const v = { skor: { B2: 3 }, catatan: { B2: 'Sub-CPMK 2 kabur', '?B2.1': 'ya', '?B2.2': 'belum' } };
  assert.deepEqual(ringkasPemandu(v.catatan, 'B2'), { ya: 1, belum: 1, ta: 0, n: 4, kosong: 2 });
  assert.deepEqual(jawabanPemandu(v.catatan, 'B2').map(x => x.jawab), ['ya', 'belum', '', '']);
  assert.equal(rerataReview(v.skor), 3);
});

test('jawaban Belum meminta tanggapan penyusun walau skor 3 dan tanpa catatan', () => {
  const v = { skor: { A1: 3, D5: 3 }, catatan: { '?D5.2': 'belum', '?A1.1': 'ya' } };
  assert.deepEqual(butirTanggapan(v).map(b => b.kode), ['D5']);
});

test('saran skor dari jawaban pemandu; T/A tidak dihitung', () => {
  const c = j => Object.fromEntries(j.map((w, i) => [kunciTanya('D2', i), w]));
  assert.equal(saranSkor(c(['ya', 'ya', 'ya']), 'D2'), 4);
  assert.equal(saranSkor(c(['ya', 'belum', 'ya']), 'D2'), 3);
  assert.equal(saranSkor(c(['belum', 'belum', 'ya']), 'D2'), 2);
  assert.equal(saranSkor(c(['belum', 'belum', 'belum']), 'D2'), 1);
  assert.equal(saranSkor(c(['ya', 'ta', 'ta']), 'D2'), 4);
  assert.equal(saranSkor(c(['ta', 'ta', 'ta']), 'D2'), null);
  assert.equal(saranSkor(c(['ya', 'ya']), 'D2'), null);   // belum semua dijawab
});

test('saran kesimpulan dari skor', () => {
  assert.equal(saranKesimpulan({}), null);
  assert.equal(saranKesimpulan({ A1: 4, B1: 3 }), 'layak');
  assert.equal(saranKesimpulan({ A1: 4, B1: 2 }), 'perbaikan_kecil');
  assert.equal(saranKesimpulan({ A1: 2, B1: 2, B2: 2 }), 'perbaikan_besar');
  assert.equal(saranKesimpulan({ A1: 4, B1: 1 }), 'perbaikan_besar');
});

test('syarat kirim: pemandu dijawab, skor rendah atau jauh dari saran diberi catatan, kesimpulan longgar dijelaskan', () => {
  const skor = {}, catatan = {};
  for (const b of BUTIR_REVIEW) {
    skor[b.kode] = 4;
    PEMANDU_REVIEW[b.kode].tanya.forEach((_, i) => { catatan[kunciTanya(b.kode, i)] = 'ya'; });
  }
  assert.deepEqual(periksaKirimReview({ skor, catatan, kesimpulan: 'layak' }), []);
  const m1 = periksaKirimReview({ skor: { ...skor, D5: 2 }, catatan: { ...catatan, '?A1.1': '' }, kesimpulan: 'layak' });
  assert.equal(m1.length, 3);
  assert.match(m1[0], /pemandu.*A1/);
  assert.match(m1[1], /1-2: D5/);
  assert.match(m1[2], /catatan umum/);
  assert.deepEqual(periksaKirimReview({ skor: { ...skor, D5: 2 }, catatan: { ...catatan, D5: 'Rubrik tugas besar belum ada.' },
    kesimpulan: 'perbaikan_kecil' }), []);
  const c2 = { ...catatan, '?E1.1': 'belum', '?E1.2': 'belum', '?E1.3': 'belum' };   // saran 1, skor 4, tanpa catatan
  assert.match(periksaKirimReview({ skor, catatan: c2, kesimpulan: 'layak' }).join(' '), /jauh dari saran.*E1/);
  assert.deepEqual(periksaKirimReview({ skor, catatan: { ...c2, E1: 'Evaluasi sudah dibahas di rapat KK.' }, kesimpulan: 'layak' }), []);
});
