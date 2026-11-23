// Silabus mata kuliah (instal-lengkap.sql, pemilik 2026-11-20): isian, kelengkapan, CPL terkait, impor, lampiran Word.
import test from 'node:test';
import assert from 'node:assert/strict';
import { rapikanSilabus, kekuranganSilabus, cplTerkait, rencanaImpor, lampiranSilabus, penyelenggara, statusSilabus, dariUniversitas } from '../../site/silabus.js';

const LENGKAP = { nama_en: 'Hydrology', tujuan: 'Tujuan', tujuan_en: 'Aim', deskripsi: 'Deskripsi', deskripsi_en: 'Description', pustaka: '1. Chow\n2. Linsley' };
const MK = [
  { kurikulum: 'K26', kode: '41319', nama: 'Hidrologi', sks: 3, semester: 4, sifat: 'wajib', unit_penyelenggara: 'prodi' },
  { kurikulum: 'K26', kode: '41301', nama: 'Praktikum Fisika Dasar 1', sks: 1, sks_praktikum: 1, semester: 1, sifat: 'wajib', unit_penyelenggara: 'prodi' },
  { kurikulum: 'K26', kode: '01301', nama: 'Kalkulus 1', sks: 4, semester: 1, sifat: 'wajib', unit_penyelenggara: 'universitas' },
  { kurikulum: 'K26', kode: '41415', nama: 'Hidrologi Lanjut', sks: 3, semester: null, sifat: 'pilihan', unit_penyelenggara: 'prodi' },
  { kurikulum: 'K21', kode: '41301', nama: 'Kalkulus I', sks: 4, semester: 1, sifat: 'wajib' },
];

test('rapikanSilabus keeps known keys only and trims; kekuranganSilabus lists empty required fields', () => {
  const d = rapikanSilabus({ tujuan: '  T  ', asing: 'x', pustaka: null });
  assert.equal(d.versi, '1'); assert.equal(d.tujuan, 'T'); assert.equal(d.pustaka, ''); assert.ok(!('asing' in d));
  assert.deepEqual(kekuranganSilabus(rapikanSilabus(LENGKAP)), []);
  assert.deepEqual(kekuranganSilabus({ ...LENGKAP, tujuan_en: ' ', pustaka: '' }), ['Tujuan umum (Inggris)', 'Pustaka (satu per baris)']);
  assert.equal(statusSilabus(undefined), 'belum'); assert.equal(statusSilabus({ status: 'diajukan' }), 'diajukan');
});

test('cplTerkait follows the MK-CPL map of the same curriculum, ordered by urutan', () => {
  const peta = [{ kurikulum: 'K26', kode_mk: '41319', cpl: 'G' }, { kurikulum: 'K26', kode_mk: '41319', cpl: 'C' }, { kurikulum: 'K21', kode_mk: '41319', cpl: 'a' }];
  const ref = [{ kurikulum: 'K26', kode: 'C', rumusan: 'Rumus C', rumusan_en: 'Formula C', urutan: 3 }, { kurikulum: 'K26', kode: 'G', rumusan: 'Rumus G', urutan: 7 },
    { kurikulum: 'K21', kode: 'a', rumusan: 'lama', urutan: 1 }];
  assert.deepEqual(cplTerkait('K26', '41319', peta, ref), [{ kode: 'C', rumusan: 'Rumus C', rumusan_en: 'Formula C' }, { kode: 'G', rumusan: 'Rumus G', rumusan_en: '' }]);
});

test('rencanaImpor: new code used as-is, pending code matched by name, university MK and existing syllabus skipped, unknown reported', () => {
  const berkas = { kurikulum: 'K26', silabus: [
    { kode: '41301', nama: 'Praktikum Fisika Dasar 1', data: LENGKAP },     // kode baru (dulu Kalkulus 1 berkode 41301)
    { kode: null, nama: 'kalkulus  1', data: { ...LENGKAP, catatan_impor: 'kode menunggu' } },
    { kode: '41319', nama: 'Hidrologi', data: LENGKAP },
    { kode: null, nama: 'Kimia Dasar 1', data: LENGKAP },
    { kode: '99999', nama: 'Tidak ada', data: LENGKAP }] };
  const r = rencanaImpor(berkas, MK, new Map([['K26|41319', { status: 'draf' }]]));
  assert.deepEqual(r.baris.map(b => b.kode), ['41301']);
  assert.deepEqual(r.universitas, ['01301']);   // impor isi awal melewati MK universitas; diisi di situs (pemilik 2026-11-20)
  assert.deepEqual(r.sudahAda, ['41319']);
  assert.deepEqual(r.tanpaMk, [{ kode: '', nama: 'Kimia Dasar 1' }, { kode: '99999', nama: 'Tidak ada' }]);
  assert.throws(() => rencanaImpor({ silabus: [] }, MK), /kurikulum/);
});

test('lampiranSilabus uses the approved version, groups by semester, lists missing syllabi; draft option marks drafts', () => {
  const sil = new Map([
    ['K26|41319', { status: 'draf', revisi: 1, data: { ...LENGKAP, tujuan: 'Tujuan baru belum sah' }, sah: { ...LENGKAP, prasyarat: '41312' } }],
    ['K26|41301', { status: 'draf', revisi: 0, data: { ...LENGKAP, nama_en: 'Physics Lab 1' }, sah: null }]]);
  const peta = [{ kurikulum: 'K26', kode_mk: '41319', cpl: 'G' }];
  const ref = [{ kurikulum: 'K26', kode: 'G', rumusan: 'Rumus G', rumusan_en: 'Formula G' }];
  const a = lampiranSilabus({ kur: 'K26', mk: MK, silabus: sil, peta, refCpl: ref, prodi: 'Teknik Contoh', institusi: 'Universitas Contoh' });
  assert.equal(a.jumlah, 1); assert.equal(a.draf, 0);
  assert.deepEqual(a.belum.sort(), ['01301', '41301', '41415']);   // MK universitas ikut lampiran (pemilik 2026-11-20)
  assert.ok(a.xml.includes('Semester 4') && a.xml.includes('41319 Hidrologi') && a.xml.includes('CPL-G: Rumus G') && a.xml.includes('CPL-G: Formula G'));
  assert.ok(a.xml.includes('Prasyarat: 41312; Bersamaan: -') && a.xml.includes('Pre-requisite: 41312; Co-requisite: -'));
  assert.ok(a.xml.includes('Program Studi Teknik Contoh') && !a.xml.includes('Tujuan baru belum sah'));
  assert.ok(a.xml.includes('>1. Chow<') && a.xml.includes('>2. Linsley<'));   // satu pustaka per paragraf
  const b = lampiranSilabus({ kur: 'K26', mk: MK, silabus: sil, peta, refCpl: ref, draf: true });
  assert.equal(b.jumlah, 2); assert.equal(b.draf, 1);
  assert.ok(b.xml.includes('41301 Praktikum Fisika Dasar 1 (DRAF, belum disahkan)') && b.xml.includes('Physics Lab 1'));
  assert.ok(!b.xml.includes('Kalkulus I'));   // K21 tidak ikut
});

test('penyelenggara from unit_penyelenggara', () => {
  assert.equal(penyelenggara({ unit_penyelenggara: 'prodi' }, 'Teknik Contoh'), 'Program Studi Teknik Contoh');
  assert.equal(penyelenggara({ unit_penyelenggara: 'universitas' }, 'Teknik Contoh'), 'Universitas');
  assert.equal(penyelenggara({}, 'Teknik Contoh'), '');
  assert.ok(dariUniversitas({ unit_penyelenggara: 'universitas' }) && !dariUniversitas({ unit_penyelenggara: 'prodi' }) && !dariUniversitas({}));
});
