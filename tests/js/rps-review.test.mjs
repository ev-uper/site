// Mode review (pemilik 2026-11-19): ringkasan otomatis per butir form review dan tujuan tiap butir.
import test from 'node:test';
import assert from 'node:assert/strict';
import { faktaReview, BUTIR_REVIEW, rapikanRps } from '../../site/rps.js';

const mk = { kurikulum: 'K26', kode: '41301', nama: 'Statika', sks: 3, semester: 3, sks_kuliah: 3 };
const S = {
  versi: '1', cpmk: [{ kode: 'CPMK-1', rumusan: 'Menganalisis gaya (C4)' }],
  sub: [{ kode: 'Sub-CPMK-1-1', cpmk: 'CPMK-1', rumusan: 'Menjelaskan gaya (C2)', cpl: 'C' },
        { kode: 'Sub-CPMK-1-2', cpmk: 'CPMK-1', rumusan: 'Menganalisis rangka (C4)' }],
  asesmen: [{ nama: 'Tugas 1', jenis: 'tugas' }, { nama: 'UTS' }, { nama: 'UAS' }],
  bobot: { 'Sub-CPMK-1-1': { 'Tugas 1': 20, UTS: 30 }, 'Sub-CPMK-1-2': { 'Tugas 1': 10, UAS: 40 } },
};

test('tiap butir punya tujuan dan ringkasan', () => {
  const F = faktaReview({ mk, struktur: S, rps: rapikanRps(null, mk, {}) });
  for (const b of BUTIR_REVIEW) { assert.ok(b.ke, b.kode); assert.ok(F[b.kode]?.length, b.kode); }
});

test('ringkasan memuat angka yang dihitung dari RPS dan bagian B', () => {
  const R = rapikanRps(null, mk, {});
  R.pustaka = [{ kode: 'A', teks: 'Hibbeler (2016). Statics.' }, { kode: 'B', teks: 'Beer (2010). Mechanics.' }];
  R.pekan[0] = { ...R.pekan[0], sub: ['Sub-CPMK-1-1'], materi: 'Gaya', indikator: 'Skor ≥ 60', scl: ['case'] };
  const F = faktaReview({ mk, struktur: S, rps: R, cpl: [{ kode: 'C' }], kini: new Date('2026-11-19') });
  assert.equal(F.B4[0], 'Total bobot 100%: Tugas 30%, UTS 30%, UAS 40%');
  assert.equal(F.B4[1], 'Kelompok Penugasan 30%, ujian/kuis 70%; HOTS 50% (disarankan ≥ 10%)');
  assert.equal(F.B1[1], 'CPL yang didukung Sub-CPMK: C; 1 Sub-CPMK tanpa CPL');
  assert.equal(F.B2[1], 'Level: C2 ×1, C4 ×2');
  assert.equal(F.C2[0], '2 pustaka; terbaru 2016; 1 terbit 2016 atau sesudahnya');
  assert.equal(F.D1[1], '13 baris kuliah tanpa materi; 1 Sub-CPMK belum dijadwalkan');
  assert.equal(F.D3[0], 'Metode SCL: Case Method (1 pekan)');
  assert.equal(F.D5[0], '1 asesmen non-tes berbobot, 0 sudah berubrik (belum: Tugas 1)');
});
