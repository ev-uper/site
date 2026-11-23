// Bahan Rapat Tinjauan Manajemen (pemilik 2026-11-12).
import test from 'node:test';
import assert from 'node:assert/strict';
import { isiBahanRTM } from '../../site/bahan-rtm.js';

// Teks polos: paragraf = baris baru, sel tabel = " | " (paragraf di dalam sel tidak memecah baris).
const polos = xml => xml.replace(/<w:tc>.*?<w:p>/g, '<w:tc>').replace(/<w:tr>/g, '\n').replace(/<w:p>/g, '\n').replace(/<w:tc>/g, ' | ').replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
const NAMA = { a: 'Ani', b: 'Budi' };
const X = {
  prodi: 'Program Studi Teknik Contoh', ts: 2026, namaDosen: id => NAMA[id] || '',
  standar: [{ id: 1, kode: 'A.01.01', pernyataan: 'Kriteria CPL tersedia', lembar: 'Pendidikan', dipantau: true },
            { id: 2, kode: 'O.02.10', pernyataan: 'SKS basic science cukup', lembar: 'Akreditasi Unggul LAMTEK', dipantau: true }],
  capaian: [{ standar_id: 1, tahun_ts: 2026, target: 'Tersedia', capaian: 'Ada', status: 'tercapai', bukti_url: 'https://x.id/a' },
            { standar_id: 2, tahun_ts: 2026, target: '≥ 25 SKS', capaian: '22 SKS', status: 'belum', analisis: 'Fisika 2 dihapus', rencana: 'Tambah kalkulus lanjut' }],
  revisi: [{ standar_id: 2, tanggal: '2026-03-10', perubahan: 'Target 25 → 28 SKS', dasar: 'rtm' }, { standar_id: 1, tanggal: '2026-10-01', perubahan: 'TS lain', dasar: 'ami' }],
  target: [{ jenis: 'iku', nama: 'Lulus tepat waktu', tahun_ts: 2026, target: 70, capaian: 60, arah: 'minimal', satuan: '%' },
           { jenis: 'iku', nama: 'Publikasi per DTPS', tahun_ts: 2026, target: 1, capaian: 1.2, arah: 'minimal' }],
  temuan: [{ tahun_ts: 2026, kode: 'T-01', uraian: 'RPS belum ditinjau', kategori: 'kts_minor', status: 'proses', rencana: 'Tinjau RPS', tenggat: '2026-12-01' },
           { tahun_ts: 2026, kode: 'T-02', uraian: 'Sudah beres', kategori: 'observasi', status: 'ditutup' },
           { tahun_ts: 2025, kode: 'T-09', uraian: 'TS lalu', kategori: 'kts_mayor', status: 'terbuka' }],
  rapat: [{ id: 1, jenis: 'rtm', tanggal: '2025-03-01', judul: 'RTM 2025' }, { id: 2, jenis: 'rapat_prodi', tanggal: '2026-02-01', judul: 'Rapat kurikulum' }],
  tindakRapat: [{ rapat_id: 1, keputusan: 'Susun SOP magang', status: 'proses', pj_dosen_id: 'a', tenggat: '2025-12-01' },
                { rapat_id: 1, keputusan: 'Sudah selesai', status: 'selesai' },
                { rapat_id: 2, keputusan: 'Revisi RPS Hidrologi', status: 'terbuka', pj_nama: 'Koordinator kurikulum' }],
  tindakEval: [{ status: 'terbuka', masalah: 'EDOM 2,8', rencana: 'Studi kasus', pj_id: 'b', tenggat: '2026-05-20',
                 evaluasi_mk: { kode_mk: 'SI2201', tahun_akademik: '2025/2026', semester: 'Genap' } }],
  survei: [{ judul: 'Kepuasan mahasiswa 2026', kelompok: 'mahasiswa', tahun_ts: 2026, n: 20,
             pertanyaan: [{ id: 'q1', jenis: 'skala', aspek: 'keandalan' }, { id: 'q2', jenis: 'skala', aspek: 'tangible' }],
             hitung: { q1: [0, 2, 10, 8], q2: [4, 8, 6, 2] } },
           { judul: 'TS lain', kelompok: 'dosen', tahun_ts: 2025, n: 5, pertanyaan: [], hitung: {} },
           { judul: 'Tanpa responden', kelompok: 'mitra', tahun_ts: 2026, n: 0, pertanyaan: [], hitung: {} }],
  rekapEval: [{ tahun_akademik: '2025/2026', semester: 'Genap', jumlah: 2, rerata_edom: 3.18, di_bawah_ambang: 1, bawah_bertindak: 1, rps_terisi: 1, tindak: 1, tindak_selesai: 0 }],
};

test('bahan RTM: sembilan bagian dengan isi dari data TS itu', () => {
  const t = polos(isiBahanRTM(X, new Date(2026, 10, 12)));
  for (const j of ['1. Tindak lanjut keputusan RTM sebelumnya', '2. Hasil audit mutu internal', '3. Capaian standar SPMI (siklus PPEPP)',
    '4. Capaian IKU dan IKT', '5. Evaluasi pembelajaran', '6. Umpan balik pemangku kepentingan', '7. Tindak lanjut rapat lain yang masih terbuka',
    '8. Perubahan standar pada TS ini', '9. Usulan keputusan RTM']) assert.ok(t.includes(j), j);
  assert.match(t, /2 keputusan dari RTM sebelum TS ini; 1 sudah selesai, 1 belum/);
  assert.match(t, /Susun SOP magang \| 01\/03\/2025 \| Ani/);
  assert.ok(t.includes('RPS belum ditinjau') && !t.includes('Sudah beres') && !t.includes('TS lalu'));
  assert.match(t, /2 butir standar dipantau; 1 lengkap kelima tahapnya/);
  assert.match(t, /O\.02\.10 \| SKS basic science cukup \| ≥ 25 SKS \| 22 SKS \| Fisika 2 dihapus \| Tambah kalkulus lanjut/);
  // 60 dari 70 = 86 %: "hampir" (≥ 80 %), tetap belum tercapai sehingga perlu analisis.
  assert.match(t, /Lulus tepat waktu \| IKU \| ≥ 70 % \| 60 % \| hampir \| BELUM DIANALISIS/);
  assert.match(t, /Genap \| 2 \| 3,18 \| 1 \| 1 dari 1 \| 1 dari 2 \| 0 dari 1/);
  assert.match(t, /SI2201 Genap \| EDOM 2,8 \| Studi kasus \| Budi/);
  assert.match(t, /Revisi RPS Hidrologi \| Rapat kurikulum 01\/02\/2026 \| Koordinator kurikulum/);
  assert.ok(t.includes('Target 25 → 28 SKS') && !t.includes('TS lain'));
  // Survei: q1 rerata 3,3 / 90% puas; q2 rerata 2,3 / 40% puas -> aspek kedua di bawah ambang.
  assert.match(t, /Mahasiswa \| Kepuasan mahasiswa 2026 \| 20 \| 2,8 \| 65%/);
  assert.match(t, /% puas 40,00 < 75; rerata 2,30 < 3/);
  assert.ok(!t.includes('Tanpa responden'));
});

test('bahan RTM: bagian kosong ditulis apa adanya; IKU tak terbaca bukan admin', () => {
  const t = polos(isiBahanRTM({ ts: 2027, target: null }, new Date(2026, 10, 12)));
  assert.match(t, /Tidak ada temuan AMI tercatat untuk TS 2026\/2027/);
  assert.match(t, /Belum ada butir standar yang dipantau prodi/);
  assert.match(t, /hanya terbaca oleh admin/);
  assert.match(t, /Belum ada data evaluasi pembelajaran untuk 2026\/2027/);
  assert.match(t, /Belum ada revisi standar tercatat/);
  assert.match(t, /Hasil survei kepuasan tidak terbaca/);
  assert.match(polos(isiBahanRTM({ ts: 2027, survei: [] })), /Belum ada survei kepuasan berjawaban untuk TS 2026\/2027/);
});
