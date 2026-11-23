// Lampiran rubrik penilaian di Word (pemilik 2026-11-19).
import test from 'node:test';
import assert from 'node:assert/strict';
import { lampiranRubrik } from '../../site/rps-docx.js';

test('lampiran rubrik: judul, satu tabel per asesmen, skor tingkat n..1', () => {
  const x = lampiranRubrik([{ asesmen: 'Tugas 1', tingkat: ['Sangat baik', 'Baik', 'Cukup', 'Kurang'],
    kriteria: [{ nama: 'Analisis', bobot: '60', deskriptor: ['d4', 'd3', 'd2', 'd1'] }] }]);
  assert.match(x, /Lampiran: Rubrik Penilaian/);
  assert.match(x, /Rubrik Tugas 1/);
  assert.equal((x.match(/<w:tbl>/g) || []).length, 1);
  for (const t of ['Sangat baik (4)', 'Kurang (1)', 'Analisis', 'd4', 'd1']) assert.ok(x.includes(t), t);
});
