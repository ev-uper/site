// Pemeriksaan situs publik yang ditambahkan 2026-11-22 di Kelengkapan situs (site/kelengkapan-situs.js): kelompok
// keahlian, bidang, silabus disahkan, kelengkapan lab, kalender, biaya/beasiswa, nama Inggris MK, dan tautan internal.
// (Nama berkas lama: pemeriksaan ini sempat berada di Mutu data, lalu dipindah supaya tidak kembar.)
import test from 'node:test';
import assert from 'node:assert/strict';
import { periksaKelengkapan, tautanInternal } from '../../site/kelengkapan-situs.js';

const D = {
  dosen: [{ nama: 'Ani', foto: 'foto-dosen/ani.jpg', kelompok: 'AIR', topik_keahlian: ['T1'] },
          { nama: 'Budi', kelompok: null, topik_keahlian: [] }],
  situs: { kelompok_keahlian: [{ kode: 'AIR', nama: 'Sumber Daya Air', cakupan: 'Hidrologi', berkas: 'bidang-sda.html' },
                               { kode: 'GEO', nama: 'Geoteknik' }],
           biaya: [{ judul: 'PMB', url: 'https://pmb.contoh.ac.id' }] },
  kurikulum: [{ kode: 'K26', cpl: [], mk: [
    { kode: '41413', nama: 'Hidrologi Lanjut', nama_en: 'Advanced Hydrology', berkas: 'mk-41413.html', silabus: { deskripsi: 'x' }, cpl: ['A'] },
    { kode: '41301', nama: 'Geologi Dasar', berkas: 'mk-41301.html', cpl: ['A'] }] }],
  laboratorium: [{ nama: 'Lab Air', foto: ['a.jpg'], bidang: ['AIR'], mk: [{ kode: '41413' }] }, { nama: 'Lab Tanah', foto: [], bidang: [], mk: [] }],
  kalender: [{ semester: 'Ganjil 2026/2027', kegiatan: 'UAS', mulai: '2026-12-14' }],
};
const cari = id => periksaKelengkapan(D).find(x => x.id === id);

test('situs publik: kelompok, bidang, silabus, lab, kalender, biaya, nama Inggris', () => {
  assert.equal(cari('kelompok-dosen').status, 'sebagian');
  assert.equal(cari('kelompok-dosen').nilai, '1 dari 2');
  assert.equal(cari('bidang').status, 'sebagian');
  assert.match(cari('bidang').catatan, /Geoteknik/);
  assert.equal(cari('bidang').halaman.href, 'bidang-sda.html');
  assert.deepEqual([cari('silabus').status, cari('silabus').nilai], ['sebagian', '1 dari 2 MK']);
  assert.deepEqual([cari('lab-lengkap').status, cari('lab-lengkap').nilai], ['sebagian', '1 dari 2 laboratorium']);
  assert.equal(cari('kalender').status, 'terisi');
  assert.equal(cari('biaya').status, 'terisi');
  assert.equal(cari('nama-en').status, 'sebagian');
  assert.match(cari('nama-en').catatan, /Geologi Dasar/);
});

test('tautan internal: hanya .html di situs ini, tanpa # dan ?', () => {
  const akar = 'https://x.github.io/cv-site/';
  const html = `<a href="kurikulum.html#cpl">a</a> <a href="../index.html">b</a> <a href="mk-1.html?v=2">c</a>
    <a href="https://doi.org/10.1/x">d</a> <a href="mailto:a@b.id">e</a> <a href="#atas">f</a> <link href="tema.css?v=1">
    <a href="daftar.html?jenis=dosen&amp;q=x">g</a> <a href="/lain/x.html">h</a> <a href="\${x}.html">i</a>`;
  assert.deepEqual(tautanInternal(html, akar + 'dosen/ani.html', akar).sort(),
    [akar + 'dosen/daftar.html', akar + 'dosen/kurikulum.html', akar + 'dosen/mk-1.html', akar + 'index.html'].sort());
});

test('situs publik: arsip TA dan kontak', () => {
  const xs = periksaKelengkapan({ arsip_ta: [{ id: 1, judul: 'A', bidang: 'AIR' }, { id: 2, judul: 'B' }],
                                  situs: { kontak: { address: 'Jl. Contoh', email: 'a@b.id' } } });
  const c = id => xs.find(x => x.id === id);
  assert.deepEqual([c('arsip-ta').status, c('arsip-ta').nilai], ['sebagian', '2 judul']);
  assert.match(c('arsip-ta').catatan, /1 judul tanpa bidang/);
  assert.deepEqual([c('kontak').status, c('kontak').nilai], ['sebagian', '2 dari 4']);
});
