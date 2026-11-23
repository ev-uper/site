// Grafik Capaian CPL (owner 2026-11-13; site/grafik-cpl.js): aggregate only, no NIM.
import test from 'node:test';
import assert from 'node:assert/strict';
import { svgRadar, htmlRadarAngkatan, htmlProgresKecil, htmlPetaPanas, petaMK } from '../../site/grafik-cpl.js';
import { htmlCPL } from '../../site/capaian-cpl.js';

const amb = { individu: 45, kelas_persen: 60 };
const cpl = ['a', 'b', 'c', 'j'];
const S = { versi: 1, ambang: amb, cpl: [], berkas: [], kumulatif: [],
  angkatan: [2022, 2023].flatMap((a, i) => cpl.map(c => ({ curriculum: 'K21', cohort: a, cpl: c, students: 30 + i, mean_score: 60 + i * 5, share_achieved: 0.9, status: 'TERCAPAI' }))),
  progres: ['2024/2025 Ganjil', '2024/2025 Genap', '2025/2026 Ganjil'].flatMap((t, i) => cpl.map(c => ({ curriculum: 'K21', cpl: c, term: t,
    term_order: [20241, 20242, 20251][i], students: 50, share_achieved: c === 'j' ? 0.7 - i * 0.1 : 0.9, status: c === 'j' && i === 2 ? 'BELUM' : 'TERCAPAI' }))),
  kelas: [{ curriculum: 'K21', course_code: '41209', course_name: 'Mekanika Bahan', class_name: 'CV4', term: 't1', cpl: 'j', counted: 40, above_threshold: 20 },
    { curriculum: 'K21', course_code: '41209', course_name: 'Mekanika Bahan', class_name: 'CV4', term: 't2', cpl: 'j', counted: 40, above_threshold: 30 },
    { curriculum: 'K21', course_code: '41101', course_name: 'Matematika <Lanjut>', class_name: 'CV1', term: 't1', cpl: 'g', counted: 10, above_threshold: 10 }] };

test('radar: one polygon per series plus grid and threshold ring', () => {
  const svg = svgRadar(['a', 'b', 'c'], [{ label: 'x', nilai: { a: 50, b: 60, c: 70 }, warna: 'red' }], { ambang: 45 });
  assert.equal((svg.match(/<polygon/g) || []).length, 5 + 1 + 1);
  assert.equal(svgRadar(['a', 'b'], []), '');
});

test('radar per cohort lists cohorts and the weakest CPL', () => {
  const h = htmlRadarAngkatan(S);
  assert.match(h, /Angkatan 2022 \(30 mhs\)/);
  assert.match(h, /Angkatan 2023 \(31 mhs\)/);
  assert.match(h, /Terendah \(angkatan 2022–2023\):\s+CPL a \(60\.0\)/);
  assert.equal(htmlRadarAngkatan({ ...S, angkatan: [] }), '');
});

test('small multiples: one figure per CPL, change arrow, red point for BELUM', () => {
  const h = htmlProgresKecil(S);
  assert.equal((h.match(/<figure>/g) || []).length, 4);
  assert.match(h, /<b>j<\/b> <span class="ket">50%.*▼20/);
  assert.match(h, /fill="var\(--merah\)"><title>2025\/2026 Ganjil: 50%/);
});

test('heatmap: classes pooled per course and CPL, escaped names, red below 60 %', () => {
  const m = petaMK(S);
  assert.equal(m.find(x => x.kode === '41209').cpl.get('j').atas, 50);
  const h = htmlPetaPanas(S);
  assert.match(h, /Matematika &lt;Lanjut&gt;/);
  assert.match(h, /terendah: Mekanika Bahan 63%/);
  assert.match(h, /<td style="background:#FFF2CC" title="Mekanika Bahan · CPL j">63%<\/td>/);
});

test('htmlCPL shows the charts section when data allow', () => {
  const h = htmlCPL(S);
  assert.match(h, /<h3 class="cpl-h">Grafik<\/h3>/);
  assert.match(h, /Peta panas MK × CPL/);
});

test('radar keeps the 5 newest cohorts on top, older ones folded', () => {
  const rows = [2016, 2017, 2018, 2019, 2020, 2021, 2022].flatMap(a => cpl.map(c => ({ curriculum: 'K21', cohort: a, cpl: c, students: 20, mean_score: 50 })));
  const h = htmlRadarAngkatan({ ...S, angkatan: rows });
  assert.equal((h.match(/<svg/g) || []).length, 2);
  assert.match(h, /Angkatan lebih lama \(2016, 2017\)/);
  assert.ok(h.indexOf('Angkatan 2018') < h.indexOf('<details>'));
});

test('radar: a missing CPL is a gap, not a zero', () => {
  const svg = svgRadar(['a', 'b', 'c', 'd'], [{ label: 'x', nilai: { a: 50, b: 60, d: 70 }, warna: 'red' }], { ambang: 45 });
  assert.match(svg, /<path d="M[^"]+"[^>]*><title>x \(tanpa c\)<\/title>/);
  assert.equal((svg.match(/<polygon/g) || []).length, 5 + 1);          // grid + threshold only, no series polygon
  assert.equal((svg.match(/M/g) || []).length, 2);                     // segments d-a and a-b
  const rows = S.angkatan.filter(r => !(r.cohort === 2023 && r.cpl === 'b'));
  assert.match(htmlRadarAngkatan({ ...S, angkatan: rows }), /Angkatan 2023 \(31 mhs; belum ada CPL b\)/);
});
