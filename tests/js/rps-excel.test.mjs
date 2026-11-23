// Templat Excel pengisian RPS (pemilik 2026-11-19): unduh -> isi -> impor kembali; tanpa SheetJS (baris array of array).
import test from 'node:test';
import assert from 'node:assert/strict';
import { lembarRps, bacaRpsExcel, bagianBerubah, LEMBAR, VERSI_TEMPLAT } from '../../site/rps-excel.js';
import { rpsKosong, rapikanRps } from '../../site/rps.js';

const mk = { kurikulum: 'K26', kode: '41301', nama: 'Statika', sks: 3, semester: 1, sks_kuliah: 3 };
const S = {
  versi: '1', cpmk: [{ kode: 'CPMK-1', rumusan: 'Menganalisis gaya (C4)', indikator: { x: 1 } }],
  sub: [{ kode: 'Sub-CPMK-1-1', cpmk: 'CPMK-1', rumusan: 'Menjelaskan gaya (C2)', cpl: 'C' },
        { kode: 'Sub-CPMK-1-2', cpmk: 'CPMK-1', rumusan: 'Menghitung reaksi (C3)', cpl: 'C' }],
  asesmen: [{ nama: 'Tugas 1', jenis: 'tugas' }, { nama: 'UTS' }, { nama: 'UAS', kelompok: 'ujian' }],
  bobot: { 'Sub-CPMK-1-1': { 'Tugas 1': 20, UTS: 30 }, 'Sub-CPMK-1-2': { 'Tugas 1': 10, UAS: 40 } },
};
function rpsContoh(){
  const R = rapikanRps(null, mk, { prodi: 'Teknik Contoh' });
  Object.assign(R, { tujuan: 'Tujuan satu\nTujuan dua', deskripsi: 'Deskripsi', pengampu: 'Dr. A\nIr. B', pustaka: [{ kode: 'HIB', teks: 'Hibbeler (2016). Statics.' }] });
  R.scl = { ada: true, teks: 'Case Method pekan 9' }; R.integrasi = { ada: false, teks: '', karya: [] }; R.direktori = { status: 'tidak_langsung', teks: '' };
  R.identitas.semester = '1';
  R.pekan[0] = { ...R.pekan[0], sub: ['Sub-CPMK-1-1'], materi: 'Vektor gaya', indikator: 'Skor ≥ 60', luring: 'Kuliah; Case Method', bentuk_pb: ['kuliah', 'penugasan'],
    scl: ['case'], asesmen: ['Tugas 1'] };
  R.evaluasi = { ...R.evaluasi, baru: true };
  return R;
}
// Seperti SheetJS sheet_to_json(header:1, raw:false): angka menjadi teks, rumus tanpa nilai tersimpan menjadi kosong.
const keBuku = lembar => Object.fromEntries(lembar.map(([n, rows]) => [n, rows.map(r => r.map(v => (v && typeof v === 'object' ? '' : v == null ? null : String(v))))]));

test('templat dibaca kembali sama persis (A, B, C, D, E)', () => {
  const R = rpsContoh(), buku = keBuku(lembarRps(mk, R, S, { cpl: [{ kode: 'C', rumusan: 'CPL C' }] }));
  const h = bacaRpsExcel(buku, mk, R, S);
  assert.deepEqual(h.galat, []);
  assert.deepEqual(h.catatan, []);
  assert.equal(h.ubahB, false);
  assert.deepEqual(bagianBerubah(R, h.R), []);
  assert.deepEqual(h.R.pekan, R.pekan.map(p => ({ ...p, pekan: String(p.pekan) })));
  assert.deepEqual(h.S.sub, S.sub);
  assert.deepEqual(h.S.bobot, S.bobot);
  assert.deepEqual(h.S.cpmk[0].indikator, { x: 1 });   // indikator CPMK dari halaman CPMK dipertahankan
});

test('isian Excel menggantikan isian lama; label bentuk/SCL dipetakan ke kode', () => {
  const R = rpsContoh(), buku = keBuku(lembarRps(mk, R, S));
  const d = buku[LEMBAR.d]; d[2][3] = 'Momen'; d[2][2] = 'Sub-CPMK-1-2'; d[2][9] = 'Praktikum, kuliah'; d[2][10] = 'Problem Based Learning, xyz';
  const c = buku[LEMBAR.c]; c.find(r => r[0] === 'tujuan')[1] = 'Baru';
  const b = buku[LEMBAR.bBobot]; b[1][2] = '25';   // Sub-CPMK-1-1 / UTS
  const h = bacaRpsExcel(buku, mk, R, S);
  assert.deepEqual(h.galat, []);
  assert.equal(h.R.pekan[1].materi, 'Momen');
  assert.deepEqual(h.R.pekan[1].bentuk_pb, ['praktikum', 'kuliah']);
  assert.deepEqual(h.R.pekan[1].scl, ['pbl']);
  assert.match(h.catatan.join(' '), /metode SCL "xyz" tidak dikenal/);
  assert.equal(h.R.tujuan, 'Baru');
  assert.equal(h.ubahB, true);
  assert.equal(h.S.bobot['Sub-CPMK-1-1'].UTS, 25);
  assert.deepEqual(bagianBerubah(R, h.R), ['C Tujuan, deskripsi, kriteria', 'D Rencana pekanan']);
});

test('berkas MK lain, versi lain, dan nilai tidak sah ditolak dengan lembar/baris', () => {
  const R = rpsContoh(), lain = keBuku(lembarRps({ ...mk, kode: '41302' }, R, S));
  assert.match(bacaRpsExcel(lain, mk, R, S).galat.join(' '), /untuk K26 41302, bukan K26 41301/);
  const buku = keBuku(lembarRps(mk, R, S));
  buku[LEMBAR.petunjuk].find(r => r[0] === 'Versi templat')[1] = 'lama';
  buku[LEMBAR.a].find(r => r[0] === 'jenis_mk')[1] = 'MKX';
  buku[LEMBAR.bCpmk][2][2] = 'CPMK-9';
  buku[LEMBAR.d][3][1] = 'kuis';
  buku[LEMBAR.d][3][2] = 'Sub-CPMK-7-1';
  buku[LEMBAR.c].find(r => r[0] === 'scl_ada')[1] = 'mungkin';
  const g = bacaRpsExcel(buku, mk, R, S).galat.join('\n');
  assert.match(g, new RegExp(`Versi templat "lama" tidak dikenal \\(harus ${VERSI_TEMPLAT}\\)`));
  assert.match(g, /jenis_mk: "MKX"/);
  assert.match(g, /B CPMK baris 3: CPMK induk "CPMK-9"/);
  assert.match(g, /D Pekan baris 4: Jenis "kuis"/);
  assert.match(g, /D Pekan baris 4: Sub-CPMK "Sub-CPMK-7-1"/);
  assert.match(g, /scl_ada: tulis "Ada" atau "Tidak ada"/);
});

test('lembar yang dihapus = bagian itu tidak diubah; RPS kosong pun bisa diunduh', () => {
  const R = rpsContoh(), buku = keBuku(lembarRps(mk, R, S));
  delete buku[LEMBAR.bCpmk]; delete buku[LEMBAR.bAsesmen]; delete buku[LEMBAR.bBobot]; delete buku[LEMBAR.d];
  const h = bacaRpsExcel(buku, mk, R, S);
  assert.deepEqual(h.galat, []);
  assert.equal(h.ubahB, false);
  assert.equal(h.S, S === null ? null : h.S);
  assert.deepEqual(h.R.pekan, R.pekan);
  assert.ok(!h.bagian.includes('D Pekan'));
  const kosong = lembarRps(mk, rpsKosong(mk), null);
  assert.equal(kosong.length, 9);
  assert.deepEqual(bacaRpsExcel(keBuku(kosong), mk, rpsKosong(mk), null).galat, []);
});

test('rumus Jumlah di B Bobot membawa nilai awal (SheetJS 0.18.5 tidak menulis sel rumus tanpa nilai)', () => {
  const b = Object.fromEntries(lembarRps(mk, rpsContoh(), S))[LEMBAR.bBobot];
  assert.deepEqual(b[1][4], { f: 'SUM(B2:D2)', v: 50 });
  assert.deepEqual(b[2][4], { f: 'SUM(B3:D3)', v: 50 });
  assert.deepEqual(b[3].slice(1), [{ f: 'SUM(B2:B3)', v: 30 }, { f: 'SUM(C2:C3)', v: 30 }, { f: 'SUM(D2:D3)', v: 40 }, { f: 'SUM(B4:D4)', v: 100 }]);
});
