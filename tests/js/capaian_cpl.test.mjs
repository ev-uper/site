// Capaian CPL di situs (owner 2026-11-11, option 1; instal-lengkap.sql).
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { cekRingkasan, tsDariTerm, tindakLanjutCPL, temuanDariCPL, htmlCPL } from '../../site/capaian-cpl.js';

const S = {
  versi: 1, dibuat: '2026-11-11T15:00:00+07:00', ambang: { individu: 45, kelas_persen: 60 },
  cpl: [{ curriculum: 'K26', cpl: 'CPL-A', text: 'Bertakwa <dan> berintegritas' }],
  berkas: [{ course_code: '41214', class_name: 'A', term: '2025/2026 Ganjil', used: true }, { used: false }],
  kelas: [{ curriculum: 'K26', course_code: '41214', course_name: 'Hidrologi', class_name: 'A', term: '2025/2026 Ganjil', term_order: 20251,
    cpl: 'CPL-A', counted: 10, above_threshold: 5, share: 0.5, status: 'BELUM' },
    { curriculum: 'K26', course_code: '41214', course_name: 'Hidrologi', class_name: 'B', term: '2025/2026 Ganjil', term_order: 20251,
      cpl: 'CPL-A', counted: 8, above_threshold: 7, share: 0.875, status: 'TERCAPAI' }],
  progres: [{ curriculum: 'K26', cpl: 'CPL-A', term: '2024/2025 Genap', term_order: 20242, share_achieved: 0.8, status: 'TERCAPAI', change_share: null },
    { curriculum: 'K26', cpl: 'CPL-A', term: '2025/2026 Ganjil', term_order: 20251, share_achieved: 0.55, status: 'BELUM', change_share: -0.25 }],
  kumulatif: [{ curriculum: 'K26', cpl: 'CPL-A', students: 18, mean_score: 50.25, share_achieved: 0.55, status: 'BELUM' }],
};

test('upload checks: version, parts, and NIM guard', () => {
  assert.equal(cekRingkasan(S), '');
  assert.match(cekRingkasan({ ...S, versi: 2 }), /Versi/);
  assert.match(cekRingkasan({ ...S, kelas: undefined }), /kelas/);
  assert.match(cekRingkasan(S, JSON.stringify({ ...S, extra: [{ nim: '104123033' }] })), /NIM/);
  assert.match(cekRingkasan({ ...S, kelas: [], kumulatif: [] }), /kosong/);
  assert.match(cekRingkasan([]), /objek/);
});

test('follow-up items: cumulative and per-class BELUM, short unique codes, butir 14', () => {
  assert.equal(tsDariTerm('2025/2026 Ganjil'), 2026);
  const t = tindakLanjutCPL(S);
  assert.deepEqual(t.map(x => x.kode), ['CPL-K26-CPL-A', 'CK-2526Ga-41214-A-CPL-A']);
  assert.ok(t.every(x => x.kode.length <= 30));
  const k = temuanDariCPL(t[1], S, 2027);
  assert.deepEqual([k.butir, k.tahun_ts, k.kategori, k.standar], [14, 2026, 'peluang', 'Pembelajaran (capaian CPL)']);
  assert.equal(temuanDariCPL(t[0], S, 2027).tahun_ts, 2027);
});

test('rendered view escapes text and shows progress change', () => {
  const html = htmlCPL(S);
  assert.match(html, /Bertakwa &lt;dan&gt;/);
  assert.match(html, /▼25/);
  assert.match(html, /Kelas dengan CPL belum tercapai \(1\)/);
  assert.match(html, /1 ditolak pemeriksaan/);
});

test('works with a summary written by run_cpl.py (shape from cpl/archive.py)', () => {
  // Same keys as cpl/archive.py _KELAS/_PROGRES/_KUMULATIF; guards against drift between Python and JS.
  const py = readFileSync(new URL('../../cpl/archive.py', import.meta.url), 'utf8');
  for (const k of ['course_name', 'class_name', 'share', 'above_threshold', 'share_achieved', 'change_share', 'mean_score'])
    assert.ok(py.includes(`"${k}"`), k);
});

test('estimates from final grades are labelled', () => {
  const E = { ...S, aturan: { estimasi: 'nilai akhir MK' }, berkas: [{ used: true, jenis: 'nilai_akhir' }],
    kumulatif: [{ ...S.kumulatif[0], estimate: true }], progres: S.progres.map(r => ({ ...r, estimate: true })) };
  const h = htmlCPL(E);
  assert.match(h, /<b>Estimasi<\/b>: 1 kelas/);
  assert.match(h, /· estimasi/);
  assert.match(h, /<sup title="estimasi dari nilai akhir MK">e<\/sup>/);
  assert.doesNotMatch(htmlCPL(S), /estimasi/);
});

test('CPL text falls back to ref_cpl (estimates carry no template text)', () => {
  const E = { ...S, cpl: [], kumulatif: [{ ...S.kumulatif[0], curriculum: 'K21', cpl: 'g', estimate: true }] };
  assert.match(htmlCPL(E, { cplRef: [{ kurikulum: 'K21', kode: 'g', rumusan: 'Memperoleh & menerapkan pengetahuan' }] }),
    /Memperoleh &amp; menerapkan pengetahuan/);
  assert.match(htmlCPL(S, { cplRef: [{ kurikulum: 'K26', kode: 'A', rumusan: 'lain' }] }), /Bertakwa &lt;dan&gt;/);
});
