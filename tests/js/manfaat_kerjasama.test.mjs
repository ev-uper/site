// site/manfaat-kerjasama.js and LKPS 2.a filled by lecturers (owner 2026-11-05).
// Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { CONTOH_MANFAAT, JENIS_BUKTI_KS, htmlContoh, durasiKS } from '../../site/manfaat-kerjasama.js';
import { petaDaftar } from '../../site/lkps.js';

test('durasiKS: full years like DATEDIF, status like the template formula (TS 2026 window 31/8/2022..31/8/2026)', () => {
  assert.deepEqual(durasiKS('2024-02-01', '2027-01-31', 2026), { tahun: 2, valid: true });
  assert.deepEqual(durasiKS('2024-02-01', '2027-02-01', 2026), { tahun: 3, valid: true });
  assert.deepEqual(durasiKS('2019-01-01', '2021-01-01', 2026), { tahun: 2, valid: false });
  assert.deepEqual(durasiKS('2020-01-01', '2030-01-01', 2026), { tahun: 10, valid: true }, 'spans the window');
  assert.equal(durasiKS('2025-01-01', '2024-01-01', 2026), null);
  assert.equal(durasiKS('2025-01-01', '', 2026), null);
});

test('contoh: every type has examples with blanks to replace; four template proof types', () => {
  for (const xs of Object.values(CONTOH_MANFAAT)) { assert.ok(xs.length >= 3); xs.forEach(t => assert.match(t, /\[[^\]]+\]/)); }
  assert.equal(JENIS_BUKTI_KS.length, 4);
  assert.match(htmlContoh('f_x', ['pkm']), /data-contoh-manfaat="f_x"/);
  assert.ok(!htmlContoh('f_x', ['pkm']).includes('Penelitian</b>'));
});

const pen = nama => ({ peran: 'ketua', dosen: { nama } });
const dasar = { status: 'terverifikasi', tahun: 2025, bulan: 3, karya_penulis: [pen('Adi')] };

test('2.a: lecturer input fills manfaat, dates and proof; empty falls back to the parent cooperation', () => {
  const L = petaDaftar({ ts: 2026, D: { akreditasi: {} }, daftar: {
    dosen: [{ nama: 'Adi', dtps: true, bidang_keahlian: 'Hidrologi' }],
    kerjasama: [{ id: 5, mitra: 'BBWS', jenis: 'penelitian', tingkat: 'nasional', manfaat: 'Induk', tanggal_mulai: '2024-01-01',
                  tanggal_selesai: '2027-01-01', jenis_bukti: 'spk', tahun_mulai: 2024 }],
    karya: [
      { ...dasar, id: 'a', kategori: 'penelitian', judul: 'A', kerjasama_id: 5, manfaat_ks: 'Dari dosen', jenis_bukti_ks: 'surat_penugasan' },
      { ...dasar, id: 'b', kategori: 'penelitian', judul: 'B', karya_mitra: [{ institusi: 'PT X', tingkat: 'nasional' }],
        manfaat_ks: 'Mitra lepas', mulai_ks: '2025-01-01', selesai_ks: '2026-01-01', jenis_bukti_ks: 'bukti_pelaksanaan' },
      { ...dasar, id: 'c', kategori: 'rekognisi', sub_jenis: 'editor', judul: 'Editor' }] } });
  const S = L['2a2'];
  assert.deepEqual([S.B12, S.F12, S.G12, S.L12], ['BBWS', 'A', 'Dari dosen', 'Surat Penugasan']);
  assert.ok(S.H12 && S.I12, 'dates fall back to the parent');
  assert.deepEqual([S.B13, S.G13, S.L13], ['PT X', 'Mitra lepas', 'Bukti-bukti Pelaksanaan (Laporan, Hasil Kerjasama, Luaran Kerjasama)']);
  assert.ok(S.H13.tanggal < S.I13.tanggal);
  assert.equal(L['4j'].C12, 'Hidrologi');
});

test('4.c other programmes and 6.g.1 responding users', () => {
  const L = petaDaftar({ ts: 2026, D: { akreditasi: {} }, daftar: {
    dosen: [{ nama: 'Adi', nidn: '1', dtps: true }], karya: [],
    bkd: [{ nidn: '1', tahun_akademik: '2025/2026', sks_pendidikan: 8, sks_ps_lain_dalam: 2, sks_ps_lain_luar: 0 }],
    tracer: [{ tahun_lulus: 2024, pengguna_tanggapan: 7 }] } });
  assert.deepEqual([L['4c'].D11, L['4c'].E11, L['4c'].F11], [8, 2, undefined]);
  assert.equal(L['6g1'].C7, 7);
});
