// Tenggat RPS dan review (120, pemilik 2026-11-19): pengingat (admin), Tugas saya, tenggat review N hari.
import test from 'node:test';
import assert from 'node:assert/strict';
import { isoDari, hariKe, teksHari, tenggatReview, mkTenggatRps, penerimaTenggatRps, penerimaReviewBelum, penerimaTanggapBelum,
  tugasTenggatRps } from '../../site/pengingat-rps.js';
import { tugasReview } from '../../site/tugas-saya.js';

const KINI = new Date(2026, 7, 28);   // 28 Agustus 2026 (lokal)
const mk = [
  { kurikulum: 'K26', kode: 'A1', nama: 'Statika', semester: 1, aktif: true, pengampu: ['01'] },
  { kurikulum: 'K26', kode: 'A2', nama: 'Fisika', semester: 1, aktif: true, pengampu: ['02'] },
  { kurikulum: 'K26', kode: 'A3', nama: 'Kalkulus 2', semester: 2, aktif: true, pengampu: ['01'] },
  { kurikulum: 'K26', kode: 'P1', nama: 'Pilihan', semester: null, sifat: 'pilihan', aktif: true, pengampu: ['01'] },
  { kurikulum: 'K21', kode: 'L1', nama: 'Lama', semester: 1, aktif: false, pengampu: ['01'] },
];
const rps = new Map([['K26|A2', { status: 'diajukan' }], ['K26|P1', { status: 'draf', smt: 'Ganjil' }]]);
const dosen = [{ id: 'd1', nidn: '01', nama: 'Adi', email: 'adi@u.id' }, { id: 'd2', nidn: '02', nama: 'Budi', email: 'budi@u.id' },
  { id: 'd3', nidn: '03', nama: 'Cici', email: 'cici@u.id' }];
const tenggat = { Ganjil: '2026-09-02', Genap: '2027-02-10' };

test('tanggal dan hari', () => {
  assert.equal(isoDari(20260902), '2026-09-02');
  assert.equal(isoDari(null), '');
  assert.equal(hariKe('2026-09-02', KINI), 5);
  assert.equal(teksHari(-3), 'lewat 3 hari');
  assert.equal(teksHari(0), 'hari ini');
  assert.equal(tenggatReview({ ditunjuk_pada: '2026-08-20T03:00:00Z' }, 14), '2026-09-03');
  assert.equal(tenggatReview({ tenggat: '2026-09-10', ditunjuk_pada: '2026-08-20T03:00:00Z' }, 14), '2026-09-10');   // dari basis data
});

test('MK belum diajukan: ganjil saja (genap masih jauh), MK pilihan dari semester RPS, tidak aktif dilewati', () => {
  const xs = mkTenggatRps({ mk, rps, tenggat, kini: KINI });
  assert.deepEqual(xs.map(x => [x.m.kode, x.paritas, x.hari, x.status]), [['A1', 'Ganjil', 5, 'belum dibuat'], ['P1', 'Ganjil', 5, 'draf, belum diajukan']]);
  assert.deepEqual(mkTenggatRps({ mk, rps, tenggat, kini: new Date(2026, 10, 20) }), []);   // lewat > 60 hari: semester lalu
  const p = penerimaTenggatRps({ mk, rps, tenggat, dosen, kini: KINI });
  assert.deepEqual(p.penerima.map(x => x.email), ['adi@u.id']);
  assert.match(p.penerima[0].rinci, /- A1 Statika: belum dibuat \(tenggat 2 September 2026, 5 hari lagi\)/);
});

test('review belum dikirim (reviewer) dan belum ditanggapi (penyusun)', () => {
  const review = [
    { kurikulum: 'K26', kode_mk: 'A1', reviewer_id: 'd3', ditunjuk_pada: '2026-08-10T03:00:00Z', kirim_pada: null },
    { kurikulum: 'K26', kode_mk: 'A2', reviewer_id: 'd3', ditunjuk_pada: '2026-08-01T03:00:00Z', kirim_pada: '2026-08-05T03:00:00Z', tanggapan_pada: null },
    { kurikulum: 'K26', kode_mk: 'A3', reviewer_id: 'd2', ditunjuk_pada: '2026-08-01T03:00:00Z', kirim_pada: '2026-08-05T03:00:00Z', tanggapan_pada: '2026-08-06T03:00:00Z' }];
  const r = penerimaReviewBelum({ review, mk, dosen, hari: 14, kini: KINI });
  assert.deepEqual(r.map(x => [x.email, x.rinci]), [['cici@u.id', '- A1 Statika (K26): tenggat 24 Agustus 2026, lewat 4 hari']]);
  const t = penerimaTanggapBelum({ review, mk, dosen });
  assert.deepEqual(t.map(x => [x.email, x.rinci]), [['budi@u.id', '- A2 Fisika (K26): 1 review belum ditanggapi']]);
});

test('Tugas saya: tenggat RPS milik sendiri, tenggat review menentukan segera/lewat', () => {
  const xs = tugasTenggatRps({ mk, rps, bolehRps: [{ kurikulum: 'K26', kode_mk: 'A1' }], tenggat, kini: KINI });
  assert.deepEqual(xs.map(x => [x.judul, x.hari, x.href]), [['Ajukan RPS semester ganjil sebelum 2 September 2026: 1 mata kuliah', 5, 'rps.html?kur=K26&kode=A1']]);
  const rv = tugasReview({ reviewSaya: [{ kurikulum: 'K26', kode_mk: 'A1', ditunjuk_pada: '2026-08-10T03:00:00Z', kirim_pada: null }], hariReview: 14 }, KINI);
  assert.equal(rv[0].hari, -4);
  assert.match(rv[0].rinci, /tenggat 24 Agustus 2026, lewat 4 hari/);
});

test('Tugas saya Dekan: RPS disahkan yang belum ditetapkan, hanya untuk jabatan Dekan', async () => {
  const { tugasTetapDekan } = await import('../../site/pengingat-rps.js');
  const { tugasSaya } = await import('../../site/tugas-saya.js');
  const rpsStatus = new Map([['K26|A1', { status: 'disahkan', tetap_pada: null }], ['K26|A2', { status: 'disahkan', tetap_pada: '2026-11-19T03:00:00Z' }],
    ['K26|A3', { status: 'diajukan', tetap_pada: null }], ['K26|A4', { status: 'disahkan' }]]);   // A4: tanpa kolom tetap_pada (sebelum 116)
  const mkNama = new Map([['K26|A1', 'Statika']]);
  assert.deepEqual(tugasTetapDekan({ rps: rpsStatus, mkNama }).map(x => [x.judul, x.href]),
    [['Tetapkan RPS: 1 mata kuliah menunggu penetapan Anda', 'rps.html?tetap=1']]);
  const dekan = tugasSaya({ saya: { id: 'x', peran: 'pimpinan', dtps: false, koordinator: ['dekan'] }, rpsStatus, mkNama });
  assert.ok(dekan.some(t => /menunggu penetapan Anda/.test(t.judul) && /A1 Statika/.test(t.rinci)));
  const bukan = tugasSaya({ saya: { id: 'y', peran: 'dosen', dtps: false, koordinator: [] }, rpsStatus, mkNama });
  assert.ok(!bukan.some(t => /penetapan/.test(t.judul)));
});
