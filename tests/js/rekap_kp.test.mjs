// Ruang KP (site/rekap-kp.js; instal-lengkap.sql, pemilik 2026-11-18).
import test from 'node:test';
import assert from 'node:assert/strict';
import { kunciInstansi, saranInstansi, rekapKP, buktiSelesai, teksPelaksanaan, tautanAsesor, dariRekap } from '../../site/rekap-kp.js';

const ID = 'A'.repeat(25);

test('institution key matches the SQL nama_instansi_kunci', () => {
  assert.equal(kunciInstansi(' PT. Wijaya  Karya '), 'pt wijaya karya');   // sama dengan uji PGlite kp_kunci
  assert.equal(kunciInstansi('CV, Lain'), 'cv lain');
  assert.equal(kunciInstansi(null), '');
});

test('name suggestions: partners first, one per key, sorted', () => {
  const D = { kerja_sama: [{ mitra: 'PT Wijaya Karya' }, { mitra: '' }], tempat_kp: [{ instansi: 'pt. wijaya karya' }, { instansi: 'Dinas PU  Kota' }] };
  assert.deepEqual(saranInstansi(D), ['Dinas PU Kota', 'PT Wijaya Karya']);
  assert.deepEqual(saranInstansi(), []);
});

test('recap merges spellings, marks partner status, and flags heavy supervision load', () => {
  const kp = [
    { id: 1, status: 'disetujui', tahap: 'selesai', pembimbing_id: 'd1', data: { instansi: 'PT Wijaya Karya' }, data_selesai: { tanggal_mulai: '2026-07-01' } },
    { id: 2, status: 'pembimbing', tahap: 'pengajuan', pembimbing_id: 'd1', data: { instansi: 'PT. Wijaya karya', rencana_mulai: '2027-01-05' } },
    { id: 3, status: 'disetujui', tahap: 'pengajuan', pembimbing_id: 'd1', data: { instansi: 'CV Lain', program: 'magang', rencana_mulai: '2027-02-01' } },
    { id: 4, status: 'admin', tahap: 'pengajuan', pembimbing_id: 'd1', data: { instansi: 'Dinas PU' } , dibuat: '2027-03-01' },
    { id: 5, status: 'ditolak', tahap: 'pengajuan', pembimbing_id: 'd2', data: { instansi: 'PT Tolak' }, dibuat: '2027-03-02' },
    { id: 6, status: 'draf', tahap: 'pengajuan', pembimbing_id: 'd2', data: { instansi: 'PT Draf' } },
  ];
  const r = rekapKP({ kp, dosen: [{ id: 'd1', nama: 'Bu A' }, { id: 'd2', nama: 'Pak B' }, { id: 'd3', nama: 'Pak C' }],
    kerjasama: [{ id: 9, mitra: 'PT Wijaya Karya', jenis: 'pendidikan', tingkat: 'nasional', tahun_mulai: 2024 }],
    keputusan: [{ kunci: 'cv lain', nama: 'CV Lain', keputusan: 'tidak' }] });
  assert.deepEqual(r.tahun.map(t => [t.tahun, t.semua, t.proses, t.berjalan, t.selesai, t.ditolak, t.magang]),
    [[2027, 4, 2, 1, 0, 1, 1], [2026, 1, 0, 0, 1, 0, 0]]);
  const w = r.instansi.find(x => x.kunci === 'pt wijaya karya');
  assert.deepEqual([w.nama, w.varian.length, w.mahasiswa, w.selesai, w.status, w.mitra[0].berlaku, w.ids],
    ['PT Wijaya Karya', 2, 2, 1, 'mitra', '2024–…', [1, 2]]);
  assert.equal(r.instansi.find(x => x.kunci === 'cv lain').status, 'tidak');
  assert.equal(r.instansi.find(x => x.kunci === 'dinas pu').status, 'belum');
  assert.ok(!r.instansi.some(x => x.kunci === 'pt tolak' || x.kunci === 'pt draf'));   // ditolak dan draf tidak dihitung
  // Beban: d1 aktif 3 (proses 2 + berjalan 1), d2 0, d3 0 -> rata 1; 3 > max(2, 1,5) -> tinggi.
  assert.deepEqual(r.dosen.map(d => [d.nama, d.aktif, d.selesai, d.tinggi]), [['Bu A', 3, 1, true], ['Pak B', 0, 0, false], ['Pak C', 0, 0, false]]);
  assert.equal(r.rata, 1);
});

test('completed KP evidence lists only report and completion letter, with assessor links', () => {
  const kp = [{ id: 1, nim: '104', nama: 'Ani', status: 'disetujui', tahap: 'selesai', pembimbing_id: 'd1',
                data: { instansi: 'PT X' }, data_selesai: { tanggal_mulai: '2026-07-01' } },
              { id: 2, status: 'disetujui', tahap: 'pengajuan', data: { instansi: 'PT Y' } }];
  const berkas = [{ id: 10, pengajuan_id: 1, jenis: 'laporan_kp', url: `https://drive.google.com/file/d/${ID}/view` },
                  { id: 11, pengajuan_id: 1, jenis: 'logbook', url: 'https://drive.google.com/file/d/B/view' }];
  const b = buktiSelesai(kp, berkas, [{ id: 'd1', nama: 'Bu A' }]);
  assert.deepEqual(b, [{ id: 1, nim: '104', nama: 'Ani', instansi: 'PT X', program: 'KP', tahun: 2026, pembimbing: 'Bu A',
    berkas: [{ id: 10, jenis: 'laporan_kp', asesor: `lkd.html?f=${ID}` }] }]);
  assert.equal(tautanAsesor('https://contoh.id/x'), '');
});

test('partner implementation text and recap row shape', () => {
  const t = teksPelaksanaan([{ kerjasama_id: 9, tahun: 2026, kp: 1, magang: 0 }, { kerjasama_id: 9, tahun: 2025, kp: 2, magang: 1 }]);
  assert.equal(t.get(9), '2025: 2 KP, 1 magang · 2026: 1 KP');
  const p = dariRekap({ id: 3, instansi: 'PT X', program: 'magang', status: 'disetujui', tahap: 'selesai', mulai: '2026-07-01' });
  assert.deepEqual([p.jenis, p.data.program, p.data.rencana_mulai], ['kp', 'magang', '2026-07-01']);
});

test('kuota pembimbing KP (107): sisa, penuh, teks pilihan', async () => {
  const { barisKuota, teksPilihanPembimbing, dariRekap } = await import('../../site/rekap-kp.js');
  const xs = barisKuota([{ dosen_id: 'a', nama: 'Ani', kuota: 3, kuota_sendiri: false, beban: 3 },
                         { dosen_id: 'b', nama: 'Budi', kuota: 4, kuota_sendiri: true, beban: 1 },
                         { dosen_id: 'c', nama: 'Cici', kuota: null, kuota_sendiri: false, beban: 2 }]);
  assert.deepEqual(xs.map(x => [x.sisa, x.lebih]), [[0, true], [3, false], [null, false]]);
  assert.deepEqual(xs.map(teksPilihanPembimbing), ['Ani — 3/3 (kuota penuh)', 'Budi — 1/4', 'Cici — 2']);
  assert.equal(dariRekap({ id: 1, status: 'disetujui', tahap: 'pengajuan', jawaban: 'diterima', mulai: '2026-12-01' }).data.jawaban_instansi, 'diterima');
});
