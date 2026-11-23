// site/prestasi.js and site/saran-bukti.js (owner 2026-11-06).
// Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { mirip, cariMirip, barisMahasiswa, gabungMahasiswa, periksaIsian, ubahan, ubahLangsung } from '../../site/prestasi.js';
import { SARAN_BUKTI, htmlSaran } from '../../site/saran-bukti.js';

test('mirip: same event and result; other result is another achievement', () => {
  const a = { nama_kegiatan: 'Lomba Karya Tulis Ilmiah Eco Polis Universitas Airlangga', capaian: 'Juara 3' };
  assert.ok(mirip(a, { nama_kegiatan: 'LOMBA KARYA TULIS ILMIAH ECO POLIS, Universitas Airlangga 2025', capaian: 'juara 3' }));
  assert.ok(mirip(a, { nama_kegiatan: 'Karya Tulis Ilmiah Eco Polis', capaian: '' }), 'shorter name, result unknown');
  assert.ok(!mirip(a, { ...a, capaian: 'Juara 1' }));
  assert.ok(!mirip(a, { nama_kegiatan: 'Lomba Jembatan Nasional', capaian: 'Juara 3' }));
  assert.ok(!mirip({ nama_kegiatan: 'Lomba Nasional' }, { nama_kegiatan: 'Lomba Nasional' }), 'too few distinctive words');
  assert.deepEqual(cariMirip({ id: 1, ...a }, [{ id: 1, ...a }]), [], 'never itself');
});

test('students: split and join keep name and NIM paired', () => {
  const rows = barisMahasiswa({ nama_mahasiswa: 'Ani; Budi', nim: '101; 102' });
  assert.deepEqual(rows, [{ nama: 'Ani', nim: '101' }, { nama: 'Budi', nim: '102' }]);
  assert.deepEqual(gabungMahasiswa(rows), { nama_mahasiswa: 'Ani; Budi', nim: '101; 102' });
  assert.deepEqual(barisMahasiswa(null), []);
  assert.deepEqual(gabungMahasiswa([]), { nama_mahasiswa: null, nim: null });
});

const isi = { nama_kegiatan: 'Lomba', bidang: 'akademik', tingkat: 'nasional', tahun: 2026, pembimbing: ['1'] };
const mhs = [{ nama: 'Ani', nim: '101' }];
test('periksaIsian: certificate required for new entries only', () => {
  assert.deepEqual(periksaIsian(isi, mhs, [{ jenis: 'sertifikat' }], true), []);
  assert.match(periksaIsian(isi, mhs, [{ jenis: 'foto' }], true).join(), /sertifikat/);
  assert.deepEqual(periksaIsian(isi, mhs, [], false), []);
  assert.match(periksaIsian({ ...isi, pembimbing: [] }, mhs, [], false).join(), /pembimbing/);
  assert.match(periksaIsian(isi, [{ nama: 'Ani', nim: '' }], [], false).join(), /NIM/);
  assert.match(periksaIsian(isi, [], [], false).join(), /mahasiswa/);
  assert.match(periksaIsian({ ...isi, tahun: null }, mhs, [], false).join(), /Tahun/);
});

test('ubahan: only changed columns, arrays compared by value', () => {
  const lama = { capaian: 'Juara 3', pembimbing: ['1'], bulan: null, id: 9 };
  assert.deepEqual(ubahan(lama, { capaian: 'Juara 2', pembimbing: ['1'], bulan: null }),
    { data: { capaian: 'Juara 2' }, lama: { capaian: 'Juara 3' } });
  assert.deepEqual(ubahan(lama, { pembimbing: ['1', '2'] }).data, { pembimbing: ['1', '2'] });
  assert.deepEqual(ubahan(lama, { capaian: 'Juara 3' }).data, {});
});

test('ubahLangsung: reporter before verification only', () => {
  const saya = { id: 'a' };
  assert.ok(ubahLangsung({ dilaporkan_oleh: 'a', status: 'diajukan' }, saya));
  assert.ok(ubahLangsung({ dilaporkan_oleh: 'a', status: 'ditolak' }, saya));
  assert.ok(!ubahLangsung({ dilaporkan_oleh: 'a', status: 'terverifikasi' }, saya));
  assert.ok(!ubahLangsung({ dilaporkan_oleh: 'b', status: 'diajukan' }, saya));
});

test('saran bukti: every input form and Data prodi tab has one', () => {
  const dp = readFileSync(new URL('../../site/data-prodi.html', import.meta.url), 'utf8');
  // FORM pindah dari karya.html ke form-karya.js (2026-11-08).
  const ip = readFileSync(new URL('../../site/form-karya.js', import.meta.url), 'utf8');
  const alih = { publikasi: 'publikasi_mhs', luaran: 'luaran_mhs' };
  // Tab bertanda tanpaBukti (daftar keahlian baku, patch 61) sengaja tanpa bukti baris.
  const tanpa = new Set([...dp.matchAll(/\{ id: '(\w+)',[^\n]*\n[^\n]*tanpaBukti: true/g)].map(m => m[1]));
  const tab = [...dp.matchAll(/\{ id: '(\w+)', (?:tabel|judul):/g)].map(m => m[1]).filter(t => !tanpa.has(t));
  assert.ok(tab.length >= 20, 'tab list found');
  tab.forEach(t => assert.ok(SARAN_BUKTI[alih[t] || t], `tab ${t}`));
  const form = ip.slice(ip.indexOf('export const FORM = {'), ip.indexOf('export function labelKolom'));
  const kunci = [...form.matchAll(/^ {2}(\w+): \{$/gm)].map(m => m[1]);
  assert.deepEqual(kunci, ['publikasi', 'kegiatan', 'luaran', 'rekognisi', 'integrasi']);
  kunci.forEach(k => assert.ok(SARAN_BUKTI[k], k));
});

test('htmlSaran: marks guide items; unknown key is empty', () => {
  assert.match(htmlSaran('kerjasama'), /MoU\/MoA/);
  assert.match(htmlSaran('rekognisi'), /\*<\/li>/);
  assert.match(htmlSaran('bkd'), /Saran, bukan syarat resmi/);
  assert.equal(htmlSaran('tidak_ada'), '');
});
