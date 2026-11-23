// Berkas review sejawat RPS (119, pemilik 2026-11-19): catatan reviewer dan tanggapan penyusun berdampingan; hanya review terkirim.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { modelBerkasReview, dokumenReview, buatReviewDocx, namaBerkasReview } from '../../site/review-docx.js';
import { butirTanggapan, sudahDitanggapi } from '../../site/rps.js';

const AKAR = join(import.meta.dirname, '..', '..');
const mk = { kurikulum: 'K26', kode: '41301', nama: 'Statika', sks: 3 };
const kirim = { nama: 'Dr. Kalab', kirim_pada: '2026-11-19T03:00:00Z', revisi: 1, sama: false, kesimpulan: 'perbaikan_kecil',
  skor: { A1: 4, B4: 2 }, catatan: { A1: 'Prasyarat & <isi>' }, umum: 'Rapi',
  tanggapan: { A1: { status: 'diperbaiki', teks: 'Prasyarat diisi' } }, tanggapan_umum: 'Terima kasih',
  tanggapan_pada: '2026-11-19T05:00:00Z', tanggapan_oleh: 'Dr. Penyusun' };

test('butir yang perlu ditanggapi dan status ditanggapi', () => {
  assert.deepEqual(butirTanggapan(kirim).map(b => b.kode), ['A1', 'B4']);   // A1 ada catatan, B4 skor 2
  assert.equal(sudahDitanggapi(kirim), true);
  assert.equal(sudahDitanggapi({ ...kirim, kirim_pada: '2026-11-19T06:00:00Z' }), false);   // dikirim ulang sesudah ditanggapi
});

test('model: hanya review terkirim; tanggapan berdampingan dengan catatan', () => {
  const M = modelBerkasReview({ mk, rps: { status: 'disahkan', revisi: 2 }, review: [kirim, { nama: 'Belum', kirim_pada: null }],
    prodi: 'Teknik Contoh', pengembang: 'Dr. Penyusun', kini: new Date('2026-11-20T00:00:00Z') });
  assert.equal(M.review.length, 1);
  const r = M.review[0], a1 = r.baris.find(b => b.kode === 'A1');
  assert.equal(a1.skor, '4 (Sangat baik)');
  assert.equal(a1.tanggapan, 'Diperbaiki: Prasyarat diisi');
  assert.equal(r.rerata, '3');
  assert.equal(r.kesimpulan, 'Layak dengan perbaikan kecil');
  assert.equal(r.tanggapan, 'Dr. Penyusun, 19 November 2026');
  assert.deepEqual(M.identitas[4], ['Status RPS saat dicetak', 'disahkan (revisi 1)']);
  assert.equal(M.dicetak, '20 November 2026');
});

test('Word: teks di-escape, berkas lengkap', { skip: !existsSync(join(AKAR, 'tools', 'node_modules', 'jszip')) && 'butuh: npm install --prefix tools' }, async () => {
  const M = modelBerkasReview({ mk, review: [kirim], prodi: 'Teknik Contoh' });
  const xml = dokumenReview(M);
  assert.match(xml, /Prasyarat &amp; &lt;isi&gt;/);
  assert.match(xml, /RPS sudah diubah sesudah review ini/);
  const JSZip = createRequire(join(AKAR, 'tools', 'package.json'))('jszip');
  const z = await JSZip.loadAsync(await buatReviewDocx(M, { JSZip, type: 'nodebuffer' }));
  assert.ok(z.file('word/document.xml'));
  assert.match(await z.file('word/document.xml').async('string'), /w:pgSz w:w="11906" w:h="16838"/);
  assert.equal(namaBerkasReview(mk), 'Review_RPS_K26_41301.docx');
});

test('Tugas saya: reviewer belum mengirim, penyusun belum menanggapi (pemilik 2026-11-19)', async () => {
  const { tugasReview, tugasSaya } = await import('../../site/tugas-saya.js');
  const mkNama = new Map([['K26|41301', 'Statika'], ['K26|41302', 'Fisika']]);
  const reviewSaya = [{ kurikulum: 'K26', kode_mk: '41301', kirim_pada: null }, { kurikulum: 'K26', kode_mk: '41302', kirim_pada: '2026-11-19' }];
  const rekapReview = [{ kurikulum: 'K26', kode_mk: '41302', terkirim: 2, ditanggapi: 1 }, { kurikulum: 'K26', kode_mk: '41303', terkirim: 1, ditanggapi: 0 }];
  const xs = tugasReview({ reviewSaya, rekapReview, bolehRps: [{ kurikulum: 'K26', kode_mk: '41302' }], mkNama });
  assert.deepEqual(xs.map(x => [x.judul, x.href]), [['Review RPS 41301 Statika', 'rps.html?kur=K26&kode=41301'],
    ['Tanggapi review RPS 41302 Fisika', 'rps.html?kur=K26&kode=41302']]);
  assert.match(xs[1].rinci, /41302 Fisika \(1 review\)/);
  assert.deepEqual(tugasReview({ rekapReview, bolehRps: [] }), []);   // bukan penyusun (mis. admin) = tidak ada tugas tanggapan
  const semua = tugasSaya({ saya: { id: 'x', peran: 'dosen', dtps: false }, reviewSaya, mkNama });
  assert.ok(semua.some(t => t.jenis === 'review' && t.judul === 'Review RPS 41301 Statika'));
});
