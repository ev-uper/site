// site/led-isi.js: facts, links, supporting tables and evidence for the LED draft
// (owner 2026-11-05). Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { faktaNarasi, namaTim, anggotaTim, kalimatTren, buktiOtomatis, dokumenBelumAda, periksaTersisa, buktiLembar,
         tabelPenjelas, dokumenKriteria, tokenTautan } from '../../site/led-isi.js';

const DOK = [
  { id: 1, jenis: 'statuta', tahun: 2023, judul: '', nomor: '12/2023', url: 'u-statuta' },
  { id: 2, jenis: 'statuta', tahun: 2030, judul: '', url: 'u-depan' },
  { id: 3, jenis: 'rps', tahun: 2025, judul: 'SI301 Hidrologi', url: 'u-rps' },
  { id: 4, jenis: 'kebijakan_spmi', tahun: 2024, judul: '', nomor: 'KEB/1', tanggal: '2024-02-15', url: 'u-keb' },
];
const X = {
  vmts: [{ id: 1, jenis: 'ps', visi: 'Unggul di bidang air', nomor_sk: 'SK-1' }],
  mk: [{ kode: 'SI301', nama: 'Hidrologi', sks: 3, semester: 5, rps_ada: true },
       { kode: 'SI401', nama: 'Capstone', sks: 4, semester: 7, capstone: true, capstone_pendukung: ['SI301'] },
       { kode: 'MA101', nama: 'Kalkulus', sks: 3, semester: 1, basic_science: true, rps_ada: false }],
  dosen: [{ nama: 'Zahra', nidn: '2', dtps: true, pendidikan: 'S3', jabatan: 'lektor', bidang_keahlian: 'Air' },
          { nama: 'Staf', nidn: '9', dtps: false }],
  tema: [{ nama: 'Banjir', jenis: 'penelitian' }, { nama: 'Desa', jenis: 'pkm' }, { nama: 'Mitigasi', jenis: 'keduanya' }],
  tendik: [{ nama: 'Ani', jabatan: 'laboran' }, { nama: 'Budi', jabatan: 'laboran' }, { nama: 'Cici', jabatan: 'teknisi' },
           { nama: 'Dedi', jabatan: 'asisten_lab', status_kerja: 'magang' }, { nama: 'Eka', jabatan: 'administrator_sistem' }],
  tracer: [{ tahun_lulus: 2024, jumlah_lulusan: 20, jumlah_terlacak: 10 }, { tahun_lulus: 2025, jumlah_lulusan: 20, jumlah_terlacak: 6 }],
  karya: [{ kategori: 'integrasi', tahun: 2025, mata_kuliah: 'Hidrologi', judul: 'Banjir' }],
  buktiBaris: [{ tabel: 'lkps_tracer_lulusan', baris_id: 1, judul: 'Laporan tracer', url: 'u-tracer' },
               { tabel: 'ref_mata_kuliah', baris_id: 1, url: null, dokumen: DOK[2] }],
};
const C = { daftar: X, dokumen: DOK, butirBukti: [], ts: 2026 };

test('faktaNarasi: document is a link with number and year, newest version up to TS', () => {
  const P = faktaNarasi(C);
  assert.equal(P.d('statuta', 'x'), tokenTautan('u-statuta', 'Statuta perguruan tinggi No. 12/2023 (2023)'));
  assert.equal(P.d('otk', 'nomor SK'), '[isi: nomor SK]', 'not in the library: stays to be filled');
  assert.equal(P.tahunDok('statuta', 't'), '2023');
});

test('faktaNarasi: facts from the system; missing data stays [isi]', () => {
  const P = faktaNarasi(C);
  assert.equal(P.visi('ps', 'v'), 'Unggul di bidang air');
  assert.equal(P.visi('pt', 'visi PT'), '[isi: visi PT]');
  assert.deepEqual([P.jumlahMK, P.jumlahRPS, P.jumlahIntegrasi], ['3', '1', '1']);
  assert.equal(P.capstone, 'Capstone (4 SKS)');
  assert.equal(P.capstonePendukung, 'Hidrologi');
  assert.equal(P.tema('penelitian'), 'Banjir dan Mitigasi');
  assert.equal(P.tendik, '2 laboran, 1 teknisi dan 1 administrator sistem');   // magang Dedi left out (164)
  assert.equal(P.responsTracer, '40% (16 dari 40 lulusan)');
  const K = faktaNarasi({ daftar: {}, dokumen: [], ts: 2026 });
  assert.equal(K.jumlahMK, '[isi: jumlah]');
  assert.equal(K.tendik, '[isi: jumlah admin prodi, laboran, asisten laboratorium, dan teknisi]');
});

test('kalimatTren: values and direction per series', () => {
  const t = kalimatTren({ judul: 'Publikasi DTPS', satuan: 'judul', kategori: ['2023/2024', '2024/2025'],
    seri: [{ nama: 'Jurnal', nilai: [2, 5] }, { nama: 'Prosiding', nilai: [3, 1] }] });
  assert.equal(t, 'Pada 2023/2024 s.d. 2024/2025, publikasi DTPS berturut-turut: Jurnal 2, 5 (naik); Prosiding 3, 1 (turun), dalam satuan judul.');
  assert.equal(kalimatTren(null), '');
  const b = kalimatTren({ judul: 'Publikasi', kategori: ['A', 'B'], seri: [{ nama: 'J', nilai: [5, 0] }] }, { berjalan: true });
  assert.ok(!b.includes('turun') && b.includes('Data B belum lengkap'), 'running TS: no direction');
});

test('buktiOtomatis: library documents and row evidence with links, each file once', () => {
  const b15 = buktiOtomatis('15', C);
  assert.deepEqual(b15.map(x => x.url), ['u-rps'], 'library doc and row evidence are the same file');
  assert.deepEqual(buktiOtomatis('49', C).map(x => x.url), ['u-tracer']);
  const b1 = buktiOtomatis('1', { ...C, butirBukti: [{ id: 1, butir: 1, jenis_dokumen: 'statuta' }] });
  assert.equal(b1.filter(x => x.url === 'u-statuta').length, 1);
});

test('dokumenBelumAda / periksaTersisa: only what truly has no file is left to fill', () => {
  const j = dokumenBelumAda('53', C).map(x => x.id);
  assert.ok(j.includes('manual_spmi') && !j.includes('kebijakan_spmi'));
  assert.deepEqual(periksaTersisa(['Kebijakan SPMI', 'Daftar hadir sosialisasi'], [{ label: 'Kebijakan SPMI No. KEB/1 (2024)' }]),
                   ['Daftar hadir sosialisasi']);
});

test('buktiLembar: LKPS sheet to row evidence links', () => {
  assert.deepEqual(buktiLembar('6f1 (blok Sarjana)', C), [{ url: 'u-tracer', t: 'Laporan tracer' }]);
  assert.deepEqual(buktiLembar('4d', C), []);
});

test('tabelPenjelas: lecturer list and others; nothing when there is no data', () => {
  const [d] = tabelPenjelas('26', C);
  assert.equal(d.judul, 'Daftar dosen tetap program studi (DTPS)');
  assert.deepEqual(d.baris[1], ['1', 'Zahra', '2', 'S3', 'Air', 'Lektor']);
  assert.equal(d.baris.length, 2, 'non-DTPS left out');
  const [r] = tabelPenjelas('15', C);
  assert.deepEqual(r.baris[1].slice(1, 3), ['MA101', 'Kalkulus']);
  assert.equal(r.baris[1][5], 'Belum');
  assert.deepEqual(r.baris[2][5], { url: 'u-rps', t: 'buka' }, 'RPS links to the library');
  assert.equal(tabelPenjelas('20', C)[0].baris[1][4], 'SI301');
  assert.equal(tabelPenjelas('53', C)[0].baris[1][3], '15/02/2024');
  assert.deepEqual(tabelPenjelas('38', C), []);
  assert.deepEqual(tabelPenjelas('2', C), []);
});

test('dokumenKriteria: documents of a criterion, each once', () => {
  assert.deepEqual(dokumenKriteria(['1', '4'], C).map(d => d.url), ['u-statuta']);
});

import { tercapai, teksTarget, targetBerlaku } from '../../site/led-isi.js';
import { kalimatCapaian } from '../../site/led-narasi.js';

const TARGET = [
  { jenis: 'iku', nama: 'Waktu tunggu', butir: 49, satuan: 'bulan', arah: 'maksimal', target: 6, capaian: 4.5, tahun_ts: 2026 },
  { jenis: 'iku', nama: 'Waktu tunggu', butir: 49, satuan: 'bulan', arah: 'maksimal', target: 8, capaian: 9, tahun_ts: 2025 },
  { jenis: 'ikt', nama: 'Sitasi internasional', arah: 'minimal', target: 50, capaian: 30, tahun_ts: 2026, tujuan_strategis: 'Reputasi' },
  { jenis: 'ikt', nama: 'Rencana', arah: 'minimal', target: 5, tahun_ts: 2030 },
];

test('target: direction decides achievement; missing number is unknown', () => {
  assert.equal(tercapai(TARGET[0]), true);
  assert.equal(tercapai(TARGET[1]), false);
  assert.equal(tercapai(TARGET[2]), false);
  assert.equal(tercapai({ target: 5 }), null);
  assert.equal(teksTarget(TARGET[0]), 'Waktu tunggu: target ≤ 6 bulan, capaian 4,5 bulan (tercapai)');
});

test('target: newest row per indicator up to TS', () => {
  assert.deepEqual(targetBerlaku({ target: TARGET }, 2026).map(r => [r.nama, r.tahun_ts]).sort(), [['Sitasi internasional', 2026], ['Waktu tunggu', 2026]]);
});

test('target flows into the item sentence, IKT facts and tables', () => {
  const D = { ...C, ta: '2025/2026', ta2: '2023/2024', daftar: { ...X, target: TARGET } };
  D.P = faktaNarasi(D);
  const s = kalimatCapaian(D, true, '49').teks;
  assert.match(s, /dibanding Waktu tunggu: target ≤ 6 bulan, capaian 4,5 bulan \(tercapai\)\./);
  assert.ok(!s.includes('target Renstra'));
  assert.match(kalimatCapaian(D, true, '50').teks, /\[isi: target Renstra atau IKU\]/, 'no target: stays to fill');
  assert.equal(D.P.daftarIKT, 'Sitasi internasional (target ≥ 50)');
  assert.equal(D.P.capaianIKT, '0 dari 1 IKT tercapai');
  assert.equal(D.P.tahunIKT, '2025/2026');
  assert.equal(tabelPenjelas('54', D)[0].baris[1][2], 'Reputasi');
  assert.equal(tabelPenjelas('56', D)[0].baris.length, 3);
  assert.deepEqual(tabelPenjelas('56', C), []);
});

const DOSEN_TIM = [{ id: 'a', nama: 'Ani', nidn: '01', jabatan: 'lektor_kepala' }, { id: 'b', nama: 'Budi', nidn: '02' },
  { id: 'c', nama: 'Cici', nidn: '03', aktif: false }, { id: 'e', nama: 'Eka', nidn: '05', peran: 'asesor' }];
const TIM = [{ id: 1, urutan: 3, dosen_id: 'a', deskripsi: 'Kriteria 1' }, { id: 2, urutan: 1, dosen_id: 'b' },
  { id: 3, urutan: 2, jenis: 'nondosen', nama: 'Dewi', nomor: '99', jabatan: 'Laboran' },
  { id: 4, urutan: 4, dosen_id: 'c' }, { id: 5, urutan: 5, dosen_id: 'e' }];

test('anggotaTim: mengikuti urutan; data dosen dari sistem, orang luar dari barisnya', () => {
  assert.deepEqual(anggotaTim(TIM, DOSEN_TIM).map(d => [d.nama, d.nomor, d.jabatan, d.jenis, d.deskripsi]), [
    ['Budi', '02', '', 'dosen', ''], ['Dewi', '99', 'Laboran', 'nondosen', ''], ['Ani', '01', 'Lektor Kepala', 'dosen', 'Kriteria 1']]);
});

test('namaTim: urut susunan; nonaktif dan asesor tidak tertulis; kosong tetap [isi]', () => {
  assert.equal(namaTim(TIM, DOSEN_TIM), 'Budi, Dewi dan Ani');
  assert.equal(namaTim([], []), '[isi: nama anggota tim]');
});
