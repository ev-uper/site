// Ringkasan jawaban per responden untuk menghapus isian uji coba/iseng (kelola-survei.html, pemilik 2026-11-20).
import test from 'node:test';
import assert from 'node:assert/strict';
import { ringkasJawaban } from '../../site/survei-kepuasan.js';

const Q = [{ id: 'q1', jenis: 'skala' }, { id: 'q2', jenis: 'skala' }, { id: 'q3', jenis: 'skala' }, { id: 'status', jenis: 'pilihan' },
  { id: 'bidang', jenis: 'centang' }, { id: 'saran', jenis: 'teks' }];

test('ringkasJawaban: scale string, uniform flag, other answers joined and trimmed', () => {
  assert.deepEqual(ringkasJawaban(Q, { q1: 4, q2: 3, q3: 4, status: 'Bekerja', bidang: ['a', 'b'], saran: 'Bagus' }),
    { skala: '4 3 4', seragam: false, lain: 'Bekerja · a/b · Bagus' });
  assert.equal(ringkasJawaban(Q, { q1: 1, q2: 1, q3: 1 }).seragam, true);
  assert.equal(ringkasJawaban(Q, { q1: 1, q2: 1 }).seragam, false);             // kurang dari 3 butir terjawab
  assert.equal(ringkasJawaban(Q, { q1: 2, q3: 2 }).skala, '2 - 2');
  assert.equal(ringkasJawaban(Q, { saran: 'x'.repeat(300) }, 20).lain.length, 20);
  assert.deepEqual(ringkasJawaban(null, null), { skala: '', seragam: false, lain: '' });
});
