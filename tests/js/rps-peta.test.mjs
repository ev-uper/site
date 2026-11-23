// Peta Analisis dan bagian E dari data prodi (RPS K26 tahap 3, pemilik 2026-11-18; site/rps-peta.js, site/rps.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { relasiPeta, petaSvg, usulPeta } from '../../site/rps-peta.js';
import { evaluasiDariData, periksaRps, rpsKosong, bloom, rentangPekan } from '../../site/rps.js';
import { ukuranPeta } from '../../site/rps-docx.js';

const S = { cpmk: [{ kode: 'CPMK-1', rumusan: 'Mahasiswa mampu merancang (C6)' }],
  sub: ['S1', 'S2', 'S3', 'S4'].map(k => ({ kode: k, cpmk: 'CPMK-1', rumusan: `Mahasiswa mampu langkah ${k} (C3)` })) };

test('hubungan peta: bawaan ke CPMK, lingkaran diputus, prosedural ke CPMK jadi hierarkikal', () => {
  assert.deepEqual(relasiPeta(S, {}).relasi.S1, { ke: 'CPMK-1', jenis: 'hierarkikal' });
  const r = relasiPeta(S, { sub: { S1: { ke: 'S2', jenis: 'hierarkikal' }, S2: { ke: 'S1', jenis: 'hierarkikal' }, S3: { ke: 'CPMK-1', jenis: 'prosedural' },
    S4: { ke: 'S4', jenis: 'kelompok' } } });
  assert.deepEqual(r.melingkar, ['S1']);
  assert.deepEqual(r.relasi.S1, { ke: 'CPMK-1', jenis: 'hierarkikal' });
  assert.deepEqual(r.relasi.S2, { ke: 'S1', jenis: 'hierarkikal' });
  assert.deepEqual(r.relasi.S3, { ke: 'CPMK-1', jenis: 'hierarkikal' });
  assert.deepEqual(r.relasi.S4, { ke: 'CPMK-1', jenis: 'hierarkikal' });   // menuju diri sendiri = tidak sah
});

test('tata letak peta: hierarkikal di bawah, prosedural di kiri setingkat, pengelompokan tanpa panah, entry behaviour', () => {
  const peta = { sub: { S4: { ke: 'CPMK-1', jenis: 'hierarkikal' }, S3: { ke: 'S4', jenis: 'prosedural' }, S1: { ke: 'S3', jenis: 'kelompok' },
    S2: { ke: 'S3', jenis: 'kelompok' } } };
  const { svg, w, h, simpul } = petaSvg(S, peta, 'MK prasyarat: Kalkulus');
  assert.ok(simpul['CPMK-1'].y < simpul.S4.y);                                   // CPMK di puncak
  assert.equal(simpul.S3.y, simpul.S4.y); assert.ok(simpul.S3.x < simpul.S4.x);  // prosedural: setingkat, di kiri
  assert.ok(simpul.S1.y > simpul.S3.y && simpul.S2.y === simpul.S1.y);          // kelompok di bawah S3, sejajar
  assert.equal((svg.match(/marker-end/g) || []).length, 2);                      // S4->CPMK dan S3->S4; S1, S2 tanpa panah
  assert.ok(svg.includes('Garis entry behaviour') && svg.includes('MK prasyarat: Kalkulus'));
  assert.ok(w > 0 && h > simpul.S1.y);
  assert.equal((svg.match(/<svg/g) || []).length, 1);
  assert.ok(!svg.includes('Mahasiswa mampu'));                                   // rumusan diringkas
});

test('ukuran gambar peta di Word: diperkecil agar muat', () => {
  assert.deepEqual(ukuranPeta(400, 200), { cx: 3810000, cy: 1905000 });
  const b = ukuranPeta(4000, 600);
  assert.ok(b.cx <= 13800 * 635 && Math.abs(b.cx / b.cy - 4000 / 600) < 0.01);
});

test('bagian E dari data prodi: semester terakhir, jumlah mahasiswa, bahan rekomendasi; lulus dan rerata diisi dosen', () => {
  const kelas = [
    { course_code: 'si101', class_name: 'A', cpl: 'A', counted: 30, above_threshold: 24, status: 'TERCAPAI', term: '2024/2025 Genap', term_order: 1 },
    { course_code: 'SI101', class_name: 'A', cpl: 'A', counted: 40, above_threshold: 30, status: 'TERCAPAI', term: '2025/2026 Ganjil', term_order: 2 },
    { course_code: 'SI101', class_name: 'A', cpl: 'B', counted: 38, above_threshold: 10, status: 'BELUM', term: '2025/2026 Ganjil', term_order: 2 },
    { course_code: 'SI101', class_name: 'B', cpl: 'A', counted: 20, above_threshold: 20, status: 'TERCAPAI', term: '2025/2026 Ganjil', term_order: 2 }];
  const ev = [{ id: 7, tahun_akademik: '2025/2026', semester: 'Ganjil', kode_mk: 'SI101', rps_sesuai: 'sebagian', rps_catatan: 'Pekan 9 bergeser', metode_catatan: '' }];
  const h = evaluasiDariData({ ringkasan: { kelas }, evaluasi: ev, tindak: [{ evaluasi_id: 7, masalah: 'CPL B rendah', rencana: 'Tambah Case Method' }], kode: 'SI101' });
  assert.equal(h.semester, 'Ganjil 2025/2026');
  assert.equal(h.jumlah, '60 mahasiswa; lulus …%');
  assert.equal(h.rerata, '…');
  assert.deepEqual(h.bahan, ['Capaian CPL Ganjil 2025/2026 (2 kelas): CPL A 83% mahasiswa di atas ambang; CPL B 26% mahasiswa di atas ambang (belum tercapai).',
    'Pelaksanaan sebagian sesuai RPS: Pekan 9 bergeser', 'Tindak lanjut: Tambah Case Method (masalah: CPL B rendah)']);
  assert.equal(evaluasiDariData({ ringkasan: { kelas }, kode: 'XX' }), null);
  const r = rpsKosong({ kode: 'SI101' }); r.evaluasi = { baru: false, semester: h.semester, jumlah: h.jumlah, rerata: h.rerata, rekomendasi: 'x' };
  assert.ok(periksaRps({ rps: r }).some(t => t.bagian === 'E' && /tanda "…"/.test(t.pesan)));
});

test('usulan hubungan: Bloom rendah jadi prasyarat, setingkat urut pekan, pekan sama setara', () => {
  const st = { cpmk: [{ kode: 'CPMK-1' }, { kode: 'CPMK-2' }], sub: [
    ['S1', 'C2'], ['S2', 'C2'], ['S3', 'C2'], ['S4', 'C4'], ['S5', 'C4'], ['S6', '']].map(([k, b]) =>
      ({ kode: k, cpmk: 'CPMK-1', rumusan: `Mahasiswa mampu ${k}${b ? ` (${b})` : ''}` }))
    .concat([{ kode: 'T1', cpmk: 'CPMK-2', rumusan: 'Mahasiswa mampu T1 (C3)' }]) };
  const pekan = [{ pekan: '1', jenis: 'kuliah', sub: ['S1'] }, { pekan: '3-4', jenis: 'kuliah', sub: ['S2', 'S3'] },
    { pekan: '8', jenis: 'uts', sub: ['S1', 'S4'] }, { pekan: '5', jenis: 'kuliah', sub: ['S4'] },
    { pekan: '6', jenis: 'kuliah', sub: ['S5', 'S4'] }];
  const u = usulPeta(st, pekan, { bloomC: r => bloom(r).c, rentang: rentangPekan });
  assert.deepEqual(u.sub, {
    S1: { ke: 'S2', jenis: 'prosedural' }, S2: { ke: 'S4', jenis: 'hierarkikal' }, S3: { ke: 'S4', jenis: 'kelompok' },
    S4: { ke: 'S5', jenis: 'prosedural' }, S5: { ke: 'CPMK-1', jenis: 'hierarkikal' }, S6: { ke: 'CPMK-1', jenis: 'hierarkikal' },
    T1: { ke: 'CPMK-2', jenis: 'hierarkikal' } });
  assert.deepEqual(u.tanpaBloom, ['S6']);
  const r = relasiPeta(st, { sub: u.sub });
  assert.deepEqual(r.melingkar, []);
  assert.deepEqual(r.relasi, u.sub);                     // usulan sah apa adanya
  assert.ok(petaSvg(st, { sub: u.sub }).svg.startsWith('<svg'));
});
