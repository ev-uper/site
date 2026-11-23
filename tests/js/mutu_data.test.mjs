// Pemeriksa mutu data (owner 2026-11-11).
import test from 'node:test';
import assert from 'node:assert/strict';
import { periksaMutu, normDOI, mirip, tsBerjalan, csvMutu } from '../../site/mutu-data.js';

const KINI = new Date(2026, 10, 11);   // TS berjalan 2027
const K = (id, x) => ({ id, kategori: 'publikasi', jenis: 'jurnal', tahun: 2026, status: 'terverifikasi',
  dibuat_pada: '2026-11-01T00:00:00Z', judul: `Kajian ${id.repeat(3)} lokasi ${id.repeat(4)} model ${id.repeat(5)}`, ...x });
const M = {
  karya: [
    K('a', { doi: 'https://doi.org/10.1234/ABC', bukti_url: 'https://x/a' }),
    K('b', { doi: '10.1234/abc', judul: 'Model hujan limpasan untuk DAS Ciliwung hulu', bukti_url: 'https://x/b' }),
    K('c', { doi: '10.12/x y', judul: 'Model hujan limpasan untuk DAS Ciliwung bagian hulu' }),
    K('d', { kategori: 'penelitian', jenis: null, judul: 'Penelitian induk' }),
    K('e', { kategori: 'publikasi', induk_id: 'd', url: 'https://x/e', status: 'diajukan', dibuat_pada: '2026-09-01T00:00:00Z' }),
    K('f', { status: 'draf' }),
  ],
  karyaBukti: [{ karya_id: 'd' }],
  karyaPenulis: ['a', 'b', 'c', 'd'].map(karya_id => ({ karya_id })),
  dosen: [
    { nama: 'Adi', aktif: true, dtps: true, peran: 'dosen', sinta_id: '1', scopus_id: '2', orcid: '3', pendidikan: 'S3', jabatan: 'lektor', nidn: '01' },
    { nama: 'Budi', aktif: true, dtps: true, peran: 'dosen', sinta_id: '1', pendidikan: 'S2' },
    { nama: 'Asesor', aktif: true, peran: 'asesor' },
    { nama: 'Lama', aktif: false, dtps: true },
  ],
  mk: [
    { kode: 'SI101', nama: 'Mekanika', aktif: true, rps_ada: false, sks: 3, sks_kuliah: 2, sks_praktikum: 1 },
    { kode: 'SI102', nama: 'Hidrologi', aktif: true, rps_url: 'https://x/rps', rps_9_komponen: false, sks: 3, sks_kuliah: 2 },
    { kode: 'SI999', nama: 'Lama', aktif: false, rps_ada: false },
  ],
  kerjasama: [{ mitra: 'PT A', jenis: 'penelitian', tanggal_selesai: '2026-06-30' }, { mitra: 'PT B', tahun_selesai: 2027 }],
  tracer: [{ tahun_lulus: 2026, jumlah_lulusan: 40, jumlah_terlacak: 45 }],
};
const R = Object.fromEntries(periksaMutu(M, KINI).map(h => [h.id, h.temuan.map(t => t.teks)]));

test('helpers', () => {
  assert.equal(normDOI('https://doi.org/10.1/AB'), '10.1/ab');
  assert.equal(tsBerjalan(KINI), 2027);
  assert.equal(tsBerjalan(new Date(2026, 7, 31)), 2026);
  assert.ok(mirip('Model hujan limpasan untuk DAS Ciliwung hulu', 'Model hujan limpasan untuk DAS Ciliwung bagian hulu') >= 0.85);
  assert.equal(mirip('Satu dua', 'Satu dua'), 0);   // too short to judge
});

test('karya checks ignore drafts and count parent evidence', () => {
  assert.equal(R.karya_tanpa_bukti.length, 1);                 // c only; e uses parent d's evidence
  assert.match(R.karya_tanpa_bukti[0], /Ciliwung bagian hulu/);
  assert.equal(R.doi_ganda.length, 1);
  assert.match(R.doi_ganda[0], /^10\.1234\/abc:/);
  assert.equal(R.doi_format.length, 1);
  assert.equal(R.judul_mirip.length, 1);                        // b ~ c (a and b share a DOI already)
  assert.equal(R.publikasi_tanpa_tautan.length, 0);
  assert.equal(R.karya_tanpa_penulis.length, 1);                 // e
  assert.equal(R.menunggu_lama.length, 1);                       // e, since 1 Sep
});

test('lecturer, course, partnership and tracer checks', () => {
  assert.deepEqual(R.dosen_tanpa_id, ['Budi: Scopus, ORCID']);
  assert.deepEqual(R.dosen_data_akademik, ['Budi: jabatan, NIDN']);
  assert.deepEqual(R.mk_tanpa_rps, ['SI101 Mekanika']);
  assert.deepEqual(R.mk_rps_9, ['SI102 Hidrologi']);
  assert.equal(R.mk_sks.length, 1);                              // SI102: 3 vs 2
  assert.equal(R.ks_berakhir.length, 1);                         // PT A
  assert.equal(R.tracer.length, 2);                              // 2025 missing; 2026 inconsistent
});

test('114: signed RPS evidence older than the latest approval is listed', () => {
  const mk = [{ kurikulum: 'K26', kode: 'A1', nama: 'Lama', aktif: true, rps_ada: true, rps_url: 'https://x/a' },
              { kurikulum: 'K26', kode: 'A2', nama: 'Baru', aktif: true, rps_ada: true, rps_url: 'https://x/b' },
              { kurikulum: 'K21', kode: 'A3', nama: 'Luar situs', aktif: true, rps_ada: true, rps_url: 'https://x/c' }];
  const rps = [{ kurikulum: 'K26', kode_mk: 'A1', revisi: 2 }, { kurikulum: 'K26', kode_mk: 'A2', revisi: 2 }];
  const rpsTtd = [{ kurikulum: 'K26', kode_mk: 'A1', revisi: 1 }, { kurikulum: 'K26', kode_mk: 'A2', revisi: 1 },
                  { kurikulum: 'K26', kode_mk: 'A2', revisi: 2 }, { kurikulum: 'K21', kode_mk: 'A3', revisi: null }];
  const H = periksaMutu({ mk, rps, rpsTtd }, KINI).find(h => h.id === 'mk_rps_ttd_lama');
  assert.deepEqual(H.temuan.map(t => t.teks), ['A1 Lama']);
});

test('CSV has BOM, header and one line per finding', () => {
  const csv = csvMutu(periksaMutu(M, KINI));
  assert.equal(csv.charCodeAt(0), 0xFEFF);
  const total = periksaMutu(M, KINI).reduce((a, h) => a + h.temuan.length, 0);
  assert.equal(csv.split('\r\n').length, total + 1);
});

test('dosen tanpa nama dengan gelar dan bidang di luar daftar baku (pemilik 2026-11-20)', () => {
  const dosen = [{ nama: 'Ani Contoh', aktif: true, peran: 'dosen', nama_gelar: '', bidang_keahlian: 'Rekayasa Trasnportasi' },
    { nama: 'Vina Contoh', aktif: true, peran: 'dosen', nama_gelar: 'Dr. Ir. Vina Contoh, S.T., M.T.', bidang_keahlian: 'rekayasa transportasi' },
    { nama: 'Asesor', aktif: true, peran: 'asesor', nama_gelar: '' }];
  const bidang = [{ nama: 'Rekayasa Transportasi', aktif: true }, { nama: 'Rekayasa Struktur', aktif: true }];
  const h = periksaMutu({ dosen, bidang });
  const cari = id => h.find(x => x.id === id).temuan.map(t => t.teks);
  assert.deepEqual(cari('dosen_tanpa_gelar'), ['Ani Contoh']);
  assert.deepEqual(cari('dosen_bidang_tidak_baku'), ['Ani Contoh: "Rekayasa Trasnportasi" — mungkin "Rekayasa Transportasi"']);
  assert.deepEqual(periksaMutu({ dosen }).find(x => x.id === 'dosen_bidang_tidak_baku').temuan, []);   // tanpa daftar baku: tidak dinilai
});
