// Per-lecturer performance targets (owner 2026-11-12).
import test from 'node:test';
import assert from 'node:assert/strict';
import { targetEfektif, capaianDosen, statusTarget, barisDosen, angka, INDIKATOR } from '../../site/target-kinerja.js';
import { tugasSaya } from '../../site/tugas-saya.js';

const ANI = { id: 'a', nama: 'Ani', jabatan: 'lektor', peran: 'dosen', sinta_id: '1' };
const BAKU = [
  { tahun: 2026, jabatan: 'lektor', indikator: 'publikasi', target: 2 },
  { tahun: 2026, jabatan: 'lektor', indikator: 'publikasi_bereputasi', target: 1 },
  { tahun: 2026, jabatan: 'lektor', indikator: 'hibah_eksternal', target: 1 },
  { tahun: 2026, jabatan: 'asisten_ahli', indikator: 'publikasi', target: 1 },
  { tahun: 2025, jabatan: 'lektor', indikator: 'pkm', target: 3 },
];
const KHUSUS = [{ tahun: 2026, dosen_id: 'a', indikator: 'publikasi', target: 1.5, catatan: 'tugas tambahan' },
                { tahun: 2026, dosen_id: 'b', indikator: 'pkm', target: 9 }];
const P = id => [{ dosen_id: id }];
const KARYA = [
  { kategori: 'publikasi', indeksasi: 'scopus_q2', tahun: 2026, status: 'terverifikasi', karya_penulis: P('a') },
  { kategori: 'publikasi', indeksasi: 'sinta_3_4', tahun: 2026, status: 'diajukan', karya_penulis: P('a') },
  { kategori: 'publikasi', indeksasi: 'wos', tahun: 2026, status: 'draf', karya_penulis: P('a') },        // draft: ignored
  { kategori: 'publikasi', indeksasi: 'scopus_q1', tahun: 2025, status: 'terverifikasi', karya_penulis: P('a') },   // other year
  { kategori: 'penelitian', tahun: 2026, status: 'terverifikasi', karya_penulis: [{ dosen_id: 'b' }, { dosen_id: 'a' }] },
  { kategori: 'publikasi', indeksasi: 'scopus_q1', tahun: 2026, status: 'terverifikasi', karya_penulis: P('b') },
];
const HIBAH = [
  { status: 'diajukan', tanggal_ajuan: '2026-03-01', tahun_usulan: 2026, skema: { kelompok: 'nasional' }, hibah_tim: P('a') },
  { status: 'didanai', tanggal_ajuan: '2026-05-01', skema: { kelompok: 'internal' }, hibah_tim: P('a') },      // internal: no
  { status: 'rencana', tahun_usulan: 2026, skema: { kelompok: 'industri' }, hibah_tim: P('a') },              // not submitted
  { status: 'ditolak', tanggal_ajuan: '2025-12-20', tahun_usulan: 2026, skema: { kelompok: 'internasional' }, hibah_tim: P('a') },  // submitted 2025
];

test('per-lecturer target overrides the rank default; other years and ranks ignored', () => {
  const t = targetEfektif(ANI, 2026, BAKU, KHUSUS);
  assert.deepEqual(Object.keys(t).sort(), ['hibah_eksternal', 'publikasi', 'publikasi_bereputasi']);
  assert.deepEqual(t.publikasi, { target: 1.5, sumber: 'dosen', catatan: 'tugas tambahan' });
  assert.equal(t.publikasi_bereputasi.sumber, 'jabatan');
  assert.deepEqual(targetEfektif({ id: 'z', jabatan: null }, 2026, BAKU, KHUSUS), {});
});

test('achievement: verified counts, submitted waits, drafts and other years skipped, external grants only', () => {
  const c = capaianDosen('a', 2026, KARYA, HIBAH);
  assert.deepEqual(c.publikasi, { sah: 1, menunggu: 1 });
  assert.deepEqual(c.publikasi_bereputasi, { sah: 1, menunggu: 0 });
  assert.deepEqual(c.publikasi_sinta, { sah: 0, menunggu: 1 });
  assert.deepEqual(c.penelitian, { sah: 1, menunggu: 0 });           // member counts
  assert.deepEqual(c.hibah_eksternal, { sah: 1, menunggu: 0 });
  assert.equal(INDIKATOR.length, 8);
});

test('status: reached, nearly (>= 80%), not yet; zero target is reached', () => {
  assert.equal(statusTarget(2, 2), 'tercapai');
  assert.equal(statusTarget(5, 4), 'hampir');
  assert.equal(statusTarget(2, 1), 'belum');
  assert.equal(statusTarget(0, 0), 'tercapai');
  assert.equal(angka(1.5), '1,5');
  assert.equal(angka(2), '2');
});

test('rows only for indicators with a target, in fixed order', () => {
  const r = barisDosen(ANI, 2026, { baku: BAKU, khusus: KHUSUS, karya: KARYA, hibah: HIBAH });
  assert.deepEqual(r.map(x => [x.kode, x.sah, x.target, x.status]),
    [['publikasi', 1, 1.5, 'belum'], ['publikasi_bereputasi', 1, 1, 'tercapai'], ['hibah_eksternal', 1, 1, 'tercapai']]);
});

test('Tugas saya: one short item when some targets are not reached', () => {
  const target = barisDosen(ANI, 2026, { baku: BAKU, khusus: KHUSUS, karya: KARYA, hibah: HIBAH });
  const t = tugasSaya({ saya: ANI, target, tahunTarget: 2026 }, new Date(2026, 10, 12)).filter(x => x.jenis === 'target');
  assert.equal(t.length, 1);
  assert.equal(t[0].judul, 'Target kinerja 2026: 1 indikator belum tercapai');
  assert.equal(t[0].rinci, 'Publikasi 1 dari 1,5 (+1 menunggu verifikasi)');
  assert.equal(t[0].href, 'target.html');
  assert.deepEqual(tugasSaya({ saya: ANI, target: target.filter(x => x.status === 'tercapai') }).filter(x => x.jenis === 'target'), []);
});

test('pengingat target: hanya dosen dengan indikator belum tercapai', async () => {
  const { penerimaTarget } = await import('../../site/target-kinerja.js');
  const ds = [{ ...ANI, email: 'ani@x.id' }, { id: 'b', nama: 'Budi', jabatan: 'lektor', email: 'b@x.id' }, { id: 'c', nama: 'Cici', jabatan: 'lektor', email: 'c@x.id', aktif: false }];
  const r = penerimaTarget(ds, 2026, { baku: BAKU, khusus: KHUSUS, karya: KARYA, hibah: HIBAH });
  assert.deepEqual(r.map(x => x.email), ['ani@x.id', 'b@x.id']);
  assert.equal(r[0].rinci, '- Publikasi: 1 dari target 1,5 judul (+1 menunggu verifikasi)');
});
