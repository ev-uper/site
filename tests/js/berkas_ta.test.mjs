// Berkas pendaftaran seminar/sidang TA per tahap (pemilik 2026-11-25; instal-lengkap.sql, site/pengajuan-mhs.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { BERKAS_TA_BAWAAN, berkasTahapTA, kelengkapanYudisium, labelBerkas } from '../../site/pengajuan-mhs.js';

// Patch sumber di cv-data; paket templat menulis rujukan patch menjadi instal-lengkap.sql (tanpa blok ini): dilewati.
// Daftar bawaan = isi awal 174 + 176, tanpa bukti bimbingan SIUP yang dinonaktifkan 176.
const baca = n => { const u = new URL(`../../supabase/${n}`, import.meta.url); return existsSync(u) ? readFileSync(u, 'utf8') : ''; };
const BLOK = ['instal-lengkap.sql', 'instal-lengkap.sql'].map(n => baca(n).match(/insert into public\.ta_berkas[^;]*;/));

test('daftar bawaan di JS sama dengan isi ta_berkas sesudah patch 174 dan 176', { skip: !BLOK.every(Boolean) && 'patch 174/176 tidak ada (paket templat)' }, () => {
  const baris = BLOK.flatMap(b => [...b[0].matchAll(/\('(\w+)', '(\w+)', '([^']*)', '([^']*)', (true|false), \d+\)/g)])
    .map(([, tahap, kode, label, keterangan, wajib]) => ({ tahap, kode, label, keterangan, wajib: wajib === 'true' }))
    .filter(x => x.kode !== 'ta_bukti_bimbingan');
  assert.equal(baris.length, 6);
  const kunci = x => x.tahap + '|' + x.kode;
  assert.deepEqual([...baris].sort((a, b) => kunci(a).localeCompare(kunci(b))), [...BERKAS_TA_BAWAAN].sort((a, b) => kunci(a).localeCompare(kunci(b))));
});

test('berkas per tahap: pembimbing = bukti SIUP; proposal/kemajuan = naskah; sidang + transkrip + artikel; Lainnya opsional', () => {
  const kode = t => berkasTahapTA(BERKAS_TA_BAWAAN, t).map(x => x.kode + (x.wajib ? '*' : ''));
  assert.deepEqual(kode('penetapan_pembimbing'), ['ta_terdaftar_siup*', 'lainnya']);
  assert.deepEqual(kode('seminar_proposal'), ['naskah_ta*', 'lainnya']);
  assert.deepEqual(kode('seminar_kemajuan'), ['naskah_ta*', 'lainnya']);
  assert.deepEqual(kode('sidang_akhir'), ['naskah_ta*', 'ta_transkrip*', 'ta_artikel*', 'lainnya']);
  const k = kelengkapanYudisium(berkasTahapTA(BERKAS_TA_BAWAAN, 'sidang_akhir'), [{ jenis: 'naskah_ta' }, { jenis: 'ta_transkrip' }, { jenis: 'lainnya' }]);
  assert.deepEqual([k.ada, k.wajib, k.kurang], [2, 3, ['Draf artikel atau bukti publikasi']]);
});

test('label berkas TA: bawaan, dari daftar (kode baru koordinator), atau kodenya', () => {
  assert.equal(labelBerkas('ta_bukti_bimbingan'), 'Bukti bimbingan SIUP');   // berkas lama tetap berlabel
  assert.equal(labelBerkas('ta_terdaftar_siup'), 'Bukti terdaftar TA di SIUP');
  assert.equal(labelBerkas('ta_persetujuan', [{ kode: 'ta_persetujuan', label: 'Surat persetujuan pembimbing' }]), 'Surat persetujuan pembimbing');
  assert.equal(labelBerkas('ta_x', []), 'ta_x');
});
