// site/led-saran.js: a suggestion for every LED blank (owner 2026-11-05). Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { saranIsian, masihKerangka } from '../../site/led-saran.js';
import { bagianNarasi, pisahKalimat } from '../../site/led-narasi.js';
import { faktaNarasi } from '../../site/led-isi.js';
import { BUTIR_MANUAL } from '../../site/butir-manual.js';
import { BUTIR_DATA } from '../../site/butir-data.js';

const C = { ts: 2026, ta: '2025/2026', ta2: '2023/2024', dokumen: [], daftar: {}, manual: new Set(BUTIR_MANUAL.map(b => String(b.no))),
  judulButir: Object.fromEntries([...BUTIR_DATA, ...BUTIR_MANUAL].map(b => [String(b.no), b.judul])) };
C.P = { ps: 'Program Studi X', pt: 'Univ X', ...faktaNarasi(C) };
const semua = bagianNarasi(C).flatMap(g => g.bagian).flatMap(b => b.kalimat.flatMap(x => pisahKalimat(x.teks, b.lingkup, x.id).filter(p => p.kunci)));

test('every blank has a suggestion', () => {
  assert.ok(semua.length > 400);
  assert.deepEqual([...new Set(semua.filter(p => !saranIsian(p.kunci)).map(p => p.label))], []);
});

test('suggestions follow their context', () => {
  assert.match(saranIsian('C5|swot0|uraian|1'), /sarana, prasarana/);
  assert.match(saranIsian('C7|swot3|uraian|1'), /Ancaman bagi penjaminan mutu/);
  assert.equal(saranIsian('umum|ringkasan2|uraian|2'), '[tantangan 1] dan [tantangan 2]');
  assert.notEqual(saranIsian('b16|k0.0|contoh|1'), saranIsian('b56|k0.0|contoh|1'));
});

test('masihKerangka: blanks left in the text', () => {
  assert.ok(masihKerangka('SK No. [nomor]'));
  assert.ok(!masihKerangka('SK No. 12/2024'));
});
