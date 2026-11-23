// Simulasi PJP butir 18 (pemilik 2026-11-19; site/pjp.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { hitungPjp, catatanMK, skor18, csvPjp } from '../../site/pjp.js';

const mk = (kode, nama, sks, praktik, sifat = 'wajib', o = {}) => ({ kurikulum: 'K26', kode, nama, sks, sks_kuliah: sks - praktik, sks_seminar: 0, sks_praktikum: praktik, sifat, aktif: true, ...o });

test('skor butir 18 sama dengan butir-manual.js: <20% = 20 x PJP, 20-50% = 4, >50% = 8 - 8 x PJP', () => {
  assert.equal(skor18(10, 134).toFixed(2), '1.49');
  assert.equal(skor18(27, 134), 4);
  assert.equal(skor18(60, 100).toFixed(2), '3.20');
  assert.equal(skor18(0, 0), null);
});

test('PJP sekarang dan simulasi; basis wajib atau semua MK; batas simulasi', () => {
  const xs = [mk('A1', 'Mekanika', 3, 0), mk('A2', 'Praktikum Fisika', 1, 1), mk('A3', 'Perancangan', 4, 0), mk('P1', 'Pilihan', 2, 0, 'pilihan'),
              mk('X1', 'Lama', 3, 0, 'wajib', { aktif: false })];
  const H = hitungPjp(xs, {}, 'wajib');
  assert.deepEqual([H.jb, H.jp, H.pjp, H.skor, H.kurang20], [8, 1, 12.5, 2.5, 0.6]);
  const S = hitungPjp(xs, { A1: '0,5', A3: '1', A2: '' }, 'wajib');
  assert.deepEqual([S.jpSim, S.pjpSim, S.skorSim, S.kurang20Sim], [2.5, 31.25, 4, 0]);
  assert.deepEqual(S.baris.map(r => [r.kode, r.simulasi, r.ubah]), [['A1', 0.5, 0.5], ['A2', 1, 0], ['A3', 1, 1]]);
  assert.equal(hitungPjp(xs, {}, 'semua').jb, 10);
  assert.deepEqual(hitungPjp(xs, { A1: '9', A3: '-2' }).baris.map(r => r.simulasi), [3, 1, 0]);   // tidak lebih dari sks MK, tidak negatif
});

test('catatan data dan CSV', () => {
  assert.deepEqual(catatanMK(mk('41322', 'Praktikum Mekanika Tanah 1', 1, 0)), ['namanya praktikum/praktik, tetapi sks praktikum 0']);
  assert.deepEqual(catatanMK({ nama: 'Statika', sks: 3, sks_kuliah: 2, sks_praktikum: 0 }), ['sebaran 2 sks ≠ 3 sks MK']);
  assert.deepEqual(catatanMK(mk('A1', 'Mekanika', 3, 0)), []);
  const c = csvPjp(hitungPjp([mk('A1', 'Mekanika; Teknik', 3, 0)], { A1: '0.5' }));
  assert.ok(c.startsWith('kode;nama;semester;sifat;sks;sks praktik sekarang;sks praktik simulasi;perubahan;catatan'));
  assert.ok(c.includes('"Mekanika; Teknik"') && c.includes(';3,00;0,00;0,50;0,50;') && c.includes('PJP simulasi (%);16,67'));
  assert.ok(c.includes('JB (sks);3,00') && c.includes('Skor butir 18 sekarang;0,00'));
});

test('kalkulator per MK: tugas besar di 4 pekan terakhir', async () => {
  const { hitungPekan } = await import('../../site/pjp.js');
  // Konsultasi 50' di pekan 12-15, target 1 sks (2700').
  const a = hitungPekan({ mulai: 12, akhir: 15, terjadwal: 50, luar: 0, target: 1 });
  assert.deepEqual([a.n, a.menitTerjadwal, a.total, a.sksTerjadwal, a.sksTotal, a.perluPerPekan, a.cukupTerjadwal, a.cukupTotal],
    [4, 200, 200, 0.07, 0.07, 675, false, false]);
  // Ditambah kerja luar kelas berlogbook 625' per pekan: tafsiran longgar cukup 1 sks, tafsiran aman tidak.
  const b = hitungPekan({ mulai: 12, akhir: 15, terjadwal: 50, luar: 625, target: 1 });
  assert.deepEqual([b.total, b.sksTotal, b.cukupTerjadwal, b.cukupTotal], [2700, 1, false, true]);
  // Pekan UTS (8) dan UAS (16) tidak dihitung; rentang dibatasi 1-16.
  assert.deepEqual(hitungPekan({ mulai: 7, akhir: 20 }).pekan, [7, 9, 10, 11, 12, 13, 14, 15]);
  assert.equal(hitungPekan({ mulai: 9, akhir: 15, terjadwal: 390, target: 1 }).cukupTerjadwal, true);
});
