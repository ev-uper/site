// Laporan kinerja tahunan (owner 2026-11-11): document XML from public data.
import test from 'node:test';
import assert from 'node:assert/strict';
import { isiLaporan } from '../../site/laporan-tahunan.js';

const D = { prodi: 'Teknik Contoh', institusi: 'Universitas Contoh', dtps: { jumlah: 10, doktor: 7 },
  publikasi: [{ tahun_ts: 2026, judul: 'A & B', indeksasi: 'scopus_q1', sdgs: [6], penulis: [{ nama: 'Adi' }] }],
  kegiatan: [{ tahun_ts: 2026, judul: 'PkM desa', kategori: 'pkm', sdgs: [11], penulis: [] }], luaran_dosen: [] };

test('sections, escaping, automatic IKU and SDGs', () => {
  const x = isiLaporan({ D, ts: 2026, NA: 300, status: 'Baik',
    iku: [{ jenis: 'iku', nama: 'Publikasi per DTPS', tahun_ts: 2026, arah: 'minimal', target: 1, sumber: 'publikasi_per_dtps' }],
    langkah: [{ no: '38', n: 1, label: 'Daftar alat', pihak: 'Prodi', naik: 8 }] });
  for (const j of ['1. Ringkasan kinerja', '2. Capaian IKU dan IKT', '3. Kontribusi pada SDGs', '4. Publikasi',
    '5. Penelitian dan pengabdian', '6. Kesiapan akreditasi', '7. Catatan dan tindak lanjut']) assert.ok(x.includes(j), j);
  assert.ok(x.includes('A &amp; B') && !x.includes('A & B'));          // XML-escaped
  assert.ok(x.includes('Publikasi per DTPS (otomatis)') && x.includes('>0,1<'));   // 1 publication / 10 DTPS
  assert.ok(x.includes('2 dari 2 karya TS 2025/2026 terkait SDGs'));
  assert.ok(x.includes('Clean Water and Sanitation'));
});

test('IKU not readable (non-admin) -> note instead of table', () => {
  const x = isiLaporan({ D, ts: 2026, iku: null });
  assert.ok(x.includes('hanya terbaca oleh admin'));
});
