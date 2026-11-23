// site/pustaka-dokumen.js: one stored file per document key (owner 2026-11-04).
// Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { kunciDokumen, cariDokumen, labelDokumen, opsiPustaka, opsiJenis, versiUntukTS } from '../../site/pustaka-dokumen.js';

const DOK = [
  { id: 1, jenis: 'rps', tahun: 2025, judul: 'SI301 Hidrologi', url: 'u1' },
  { id: 2, jenis: 'kebijakan_k3l', tahun: 2024, judul: '', url: 'u2' },
  { id: 3, jenis: 'kebijakan_k3l', tahun: 2026, judul: '', url: 'u3' },
];

test('document key: title only for multi-per-year types', () => {
  assert.deepEqual(kunciDokumen('kebijakan_k3l', '2024', 'abaikan'), { jenis: 'kebijakan_k3l', tahun: 2024, judul: '' });
  assert.deepEqual(kunciDokumen('rps', 2025, '  SI301 Hidrologi '), { jenis: 'rps', tahun: 2025, judul: 'SI301 Hidrologi' });
});

test('same key is found (upload replaces it, no second copy); other year is another version', () => {
  assert.equal(cariDokumen(DOK, 'rps', 2025, 'SI301 Hidrologi').id, 1);
  assert.equal(cariDokumen(DOK, 'kebijakan_k3l', '2024', 'judul apa pun').id, 2);
  assert.equal(cariDokumen(DOK, 'kebijakan_k3l', 2025, ''), null);
  assert.equal(cariDokumen(DOK, 'rps', 2025, 'SI302'), null);
});

test('labels and option lists put the tab suggestions first', () => {
  assert.equal(labelDokumen(DOK[0]), 'RPS mata kuliah — SI301 Hidrologi (2025)');
  const o = opsiPustaka(DOK, ['kebijakan_k3l']);
  assert.ok(o.indexOf('Disarankan') < o.indexOf('Dokumen lain'));
  assert.ok(o.indexOf('value="3"') < o.indexOf('value="2"'));          // newest first within a type
  assert.ok(o.indexOf('value="2"') < o.indexOf('value="1"'));          // suggested type before others
  assert.ok(opsiJenis(['rps'], 'rps').includes('value="rps" selected'));
});

test('version for a TS: newest year <= TS, else the newest', () => {
  assert.equal(versiUntukTS(DOK, 'kebijakan_k3l', 2025).id, 2);
  assert.equal(versiUntukTS(DOK, 'kebijakan_k3l', 2023).id, 3);
  assert.equal(versiUntukTS(DOK, 'tidak_ada', 2025), null);
  assert.equal(labelDokumen({ jenis: 'rps', tahun: 2025, judul: 'X', nomor: '12/2025' }), 'RPS mata kuliah — X, No. 12/2025 (2025)');
});
