// Aturan payung kerja sama (site/kerjasama-karya.js, pemilik 2026-11-10).
// Kasus bersama dengan tests/test_kerjasama_karya.py: tests/data/kerjasama_karya.json.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { barisKerjaSama } from '../../site/kerjasama-karya.js';

const K = JSON.parse(readFileSync(new URL('../data/kerjasama_karya.json', import.meta.url), 'utf8'));
const MOU = new Map(K.kerjasama.map(k => [k.id, k]));
const baris = barisKerjaSama(K.karya, MOU);
const rapi = s => String(s).trim().toLowerCase();

test('kerja sama dari karya mengikuti aturan payung', () => {
  const dapat = baris.filter(b => !b.dariInduk).map(b => [b.ts, b.kategori, rapi(b.mitra), b.judul])
    .sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
  assert.deepEqual(dapat, K.harapan);
});

test('mitra MoU tampil sekali per kegiatan, mitra turunan yang sama dengan payung tidak menambah baris', () => {
  assert.deepEqual(baris.filter(b => b.dariInduk).map(b => [b.karya.id, b.mitra]),
    [['K2', 'Pemda Contoh'], ['K1', 'Mitra MoU']]);
  assert.equal(baris.filter(b => rapi(b.mitra) === 'univ a').length, 1);
  assert.equal(baris.filter(b => rapi(b.mitra) === 'pemda contoh').length, 1);
});

test('publikasi berpayung menjadi bukti luaran kegiatannya, urut dari yang paling awal', () => {
  const k1 = baris.find(b => b.karya.id === 'K1' && !b.dariInduk);
  assert.deepEqual(k1.luaran.map(t => t.id), ['P2', 'P1']);
  assert.ok(baris.filter(b => b.tanpaPayung).every(b => b.luaran.length === 0));
  assert.deepEqual([...new Set(baris.filter(b => b.tanpaPayung).map(b => b.karya.id))], ['P3', 'P4', 'P5']);
});
