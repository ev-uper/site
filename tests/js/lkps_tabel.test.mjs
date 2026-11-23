// site/lkps-tabel.js: the programme's own LKPS workbook for copy-paste into the
// LAM template (owner 2026-11-05). Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { blokSalin, hurufKolom, lembarXml, susunBagian } from '../../site/lkps-tabel.js';

const OUTLINE = JSON.parse(readFileSync(new URL('../../site/lkps-outline.json', import.meta.url), 'utf8'));

test('hurufKolom: column index to letters', () => {
  assert.deepEqual([1, 26, 27, 52, 703].map(hurufKolom), ['A', 'Z', 'AA', 'AZ', 'AAA']);
});

test('blokSalin: consecutive rows form one block; empty optional cells stay inside', () => {
  assert.deepEqual(blokSalin({ B7: 1, C7: 2, D7: 3, B8: 4, D8: 5 }), ['B7:D8']);
  assert.deepEqual(blokSalin({ C11: 1 }), ['C11']);
  assert.deepEqual(blokSalin({ B7: 1, B9: 2 }), ['B7', 'B9'], 'empty row splits');
});

test('blokSalin: a block never covers a template formula', () => {
  assert.deepEqual(blokSalin({ B13: 1, I13: 2, L13: 3 }, ['J13', 'K13']), ['B13:I13', 'L13']);
  assert.deepEqual(blokSalin({ B7: 1, D7: 2, B8: 3, D8: 4 }, ['C8']), ['B7:B8', 'D7:D8'], 'formula in one row splits the band');
});

test('blokSalin: a merged cell with a value stays whole; empty merge blocks a gap', () => {
  assert.deepEqual(blokSalin({ B7: 1 }, [], ['B7:D7']), ['B7:D7']);
  assert.deepEqual(blokSalin({ B7: 1, F7: 2 }, [], ['C7:D7']), ['B7', 'F7']);
});

test('lembarXml: sorted rows and cells, dates as numbers, text escaped, control characters removed', () => {
  const x = lembarXml({ sel: { C2: ['a&b<c\x07', 5], B2: [5, 5], A1: [{ tanggal: 45809 }, 5] }, gabung: ['A1:B1'], lebar: { B: 12, C: 0 },
                        sembunyi: [[4, 5]], tab: '00954E', tautan: { B2: "'4a'!A1" } });
  assert.match(x, /<row r="1"><c r="A1" s="6"><v>45809<\/v><\/c><\/row><row r="2"><c r="B2" s="5"><v>5<\/v><\/c><c r="C2"/);
  assert.match(x, /a&amp;b&lt;c<\/t>/);
  assert.match(x, /<col min="2" max="2" width="12" customWidth="1"\/><col min="3" max="3" width="1" hidden="1"/);
  assert.match(x, /<mergeCell ref="A1:B1"\/>/);
  assert.match(x, /<row r="4" hidden="1"><\/row><row r="5" hidden="1">/);
  assert.match(x, /<tabColor rgb="FF00954E"\/>/);
  assert.match(x, /<hyperlink ref="B2" location="'4a'!A1"\/>/);
  // schema order: sheetPr, sheetViews, cols, sheetData, mergeCells, hyperlinks
  assert.ok(x.indexOf('<sheetPr') < x.indexOf('<sheetViews') && x.indexOf('<cols') < x.indexOf('<sheetData')
    && x.indexOf('</sheetData') < x.indexOf('<mergeCells') && x.indexOf('<mergeCells') < x.indexOf('<hyperlinks'));
});

test('outline: the 44 Sarjana tables of Daftar Tabel, in order', () => {
  const nama = OUTLINE.wajib.map(w => w.nama);
  assert.equal(nama.length, 44);
  assert.deepEqual(nama.slice(0, 3), ['PS', '1', '2a1']);
  assert.deepEqual(nama.slice(-2), ['7a', '7b']);
  for (const n of ['PSPPI', '3a2', '4e', '4g', '4k', '6e2', '6e4', '6h2']) assert.ok(!nama.includes(n), `${n} is not for Sarjana`);
  assert.equal(OUTLINE.lembar['Daftar Tabel'], undefined);
  assert.equal(Object.values(OUTLINE.lembar).reduce((n, k) => n + k.rumus.length, 0), 3221);
  assert.ok(Object.values(OUTLINE.lembar).every(k => k.boleh.length));
});

test('outline: other study levels, helper lists and INFO boxes stay out of the table', () => {
  const L = OUTLINE.lembar;
  const tutup = (n, b) => L[n].sembunyi.some(([a, z]) => b >= a && b <= z);
  assert.ok(tutup('6f1', 7) && tutup('6f1', 39) && !tutup('6f1', 31));      // Diploma, Sarjana Terapan hidden
  assert.ok(tutup('6d', 7) && tutup('6d', 47) && !tutup('6d', 38));
  assert.ok(tutup('4a', 3) && !tutup('4a', 11));                            // helper lists
  assert.ok(!Object.values(L['4a'].label).includes('Check'));
  assert.ok(!Object.values(L['4i'].label).includes('INFO'));
  assert.equal(L['4a'].label.A13, '1', 'column numbers under the header');
  assert.deepEqual(['H7', 'H11', 'H23', 'S73'].filter(r => L.Menu.ketik.includes(r)), ['H7', 'H11', 'H23', 'S73']);
});

test('susunBagian: all 44 tables, Petunjuk first, same cell addresses, Menu typed', () => {
  const peta = { Menu: { H7: 'Univ Uji', S73: { tanggal: 46265 } }, '4i': { B6: 'Adi', C6: 'Judul & jurnal', D6: 12 } };
  const { bagian, daftar, ketik } = susunBagian(peta, OUTLINE, { ts: 2026, prodi: 'Teknik Uji' });
  assert.equal(daftar.length, 44, 'empty tables are listed too');
  assert.deepEqual(ketik.map(k => k[0]), ['H7', 'S73']);
  assert.deepEqual(daftar.find(x => x.nama === '4i').blok, ['B6:D6']);
  assert.deepEqual(daftar.find(x => x.nama === '4h').blok, []);
  const wb = bagian['xl/workbook.xml'];
  assert.equal((wb.match(/<sheet /g) || []).length, 45);
  assert.ok(!wb.includes('name="Menu"'));
  assert.match(wb, /<sheet name="Petunjuk" sheetId="1"[^>]*\/><sheet name="PS" sheetId="2"/);
  const petunjuk = bagian['xl/worksheets/sheet1.xml'];
  assert.match(petunjuk, /1 dari 44 tabel wajib sudah berisi data situs/);
  assert.match(petunjuk, /31\/08\/2026/);
  assert.match(petunjuk, /Data prodi › Tracer study/);
  assert.match(petunjuk, /Belum ada data/);
  assert.match(petunjuk, /<hyperlink ref="B\d+" location="'4i'!A1"\/>/);
  const i = daftar.findIndex(x => x.nama === '4i') + 2;
  const l4i = bagian[`xl/worksheets/sheet${i}.xml`];
  assert.match(l4i, /<c r="D6" s="5"><v>12<\/v><\/c>/);
  assert.match(l4i, /Judul &amp; jurnal/);
  assert.match(l4i, /Nama DTPS/, 'table header from the template');
  assert.match(l4i, /<tabColor rgb="FF00954E"\/>/, 'green tab: has data');
  assert.ok(!/<f[ >]/.test(l4i), 'no formulas');
  const kosong = bagian[`xl/worksheets/sheet${daftar.findIndex(x => x.nama === '4h') + 2}.xml`];
  assert.match(kosong, /<tabColor rgb="FFB8C0C8"\/>/, 'grey tab: empty');
  assert.match(kosong, /<c r="B16" s="7"\/>/, 'empty table still has its grid');
});

test('every Sarjana table has a data source named', () => {
  const { bagian } = susunBagian({}, OUTLINE, { ts: 2026 });
  const t = bagian['xl/worksheets/sheet1.xml'];
  const baris = [...t.matchAll(/<row r="(\d+)">(.*?)<\/row>/g)].filter(m => /Belum ada data/.test(m[2]));
  assert.equal(baris.length, 44);
  for (const m of baris) assert.match(m[2], /r="D\d+" s="11" t="inlineStr"/, `row ${m[1]} has no source`);
});
