// Tabel ekuivalensi MK (instal-lengkap.sql, pemilik 2026-11-21).
import test from 'node:test';
import assert from 'node:assert/strict';
import { susunEkuivalensi, htmlEkuivalensi, csvEkuivalensi, KETENTUAN } from '../../site/ekuivalensi.js';
import { bacaCsvPadanan } from '../../site/tinjauan-rps.js';

const m = (kode, nama, sks = 2, semester = 1, sifat = 'wajib') => ({ kode, nama, sks, semester, sifat });
const S = {
  kurikulum_lama: 'K21', kurikulum_baru: 'K26',
  mk_lama: [m('L1', 'Mekanika Tanah I'), m('L2', 'Fisika Dasar', 3), m('L3', 'Berpikir Kritis', 1), m('L4', 'Berpikir Kreatif', 1),
            m('L5', 'Matematika Lanjut', 3), m('L6', 'Beton Prategang', 3, null, 'pilihan'), m('L7', 'Belum diisi')],
  mk_baru: [m('B1', 'Mekanika Tanah 1'), m('B2', 'Fisika Dasar 1', 3), m('B3', 'Fisika Dasar 2', 3), m('B4', 'Berpikir Integratif'),
            m('B5', 'Kalkulus 1', 4), m('B6', 'Etika Profesi Keinsinyuran')],
  padanan: [
    { kode_lama: 'L1', kode_baru: 'B1', model: 'nama sama', tidak_berlanjut: false, catatan: 'Nama sama' },
    { kode_lama: 'L2', kode_baru: 'B2', model: '1:2', tidak_berlanjut: false, catatan: 'Bab 7 Tabel 7-3 no 1' },
    { kode_lama: 'L2', kode_baru: 'B3', model: '1:2', tidak_berlanjut: false, catatan: 'Bab 7 Tabel 7-3 no 1' },
    { kode_lama: 'L3', kode_baru: 'B4', model: '2:1', tidak_berlanjut: false, catatan: null },
    { kode_lama: 'L4', kode_baru: 'B4', model: '2:1', tidak_berlanjut: false, catatan: null },
    { kode_lama: 'L5', kode_baru: 'B5', model: '1:1', tidak_berlanjut: false, catatan: 'Bab 7 Tabel 7-2 no 1' },
    { kode_lama: 'L6', kode_baru: null, model: null, tidak_berlanjut: true, catatan: 'Tidak diselenggarakan' },
    { kode_lama: 'LX', kode_baru: 'B6', model: '1:1', tidak_berlanjut: false, catatan: null },
  ],
};

test('model dibaca dari bentuk pasangan; MK baru, belum berbaris, dan kode asing terdeteksi', () => {
  const h = susunEkuivalensi(S);
  const ringkas = h.kelompok.map(k => [k.model, k.lama.map(x => x.kode).join('+'), k.baru.map(x => x.kode).join('+'), k.berubah]);
  assert.deepEqual(ringkas.sort(), [
    ['1:1', 'L1', 'B1', false],            // "Mekanika Tanah I" = "Mekanika Tanah 1": angka Romawi tidak dihitung berubah
    ['1:1', 'L5', 'B5', true],             // nama dan sks berubah
    ['1:1', 'LX', 'B6', true],
    ['1:2', 'L2', 'B2+B3', true],
    ['2:1', 'L3+L4', 'B4', true],
  ].sort());
  assert.deepEqual(h.tidak.map(t => [t.mk.kode, t.catatan]), [['L6', 'Tidak diselenggarakan']]);
  assert.deepEqual(h.baru.map(x => x.kode), []);                       // B6 punya sumber (LX) meski LX asing
  assert.deepEqual(h.belum.map(x => x.kode), ['L7']);
  assert.deepEqual(h.asing, ['LX']);
  assert.equal(h.ringkas['1:2'], 1);
  assert.equal(h.ringkas['2:1'], 1);
  assert.equal(h.ringkas.belum, 1);
});

test('MK baru tanpa sumber dihitung dari daftar MK baru', () => {
  const h = susunEkuivalensi({ ...S, padanan: S.padanan.filter(p => p.kode_lama !== 'LX') });
  assert.deepEqual(h.baru.map(x => x.kode), ['B6']);
  assert.deepEqual(h.asing, []);
});

test('HTML: ketentuan per model, saring cari, 1:1 hanya yang berubah, isi di-escape', () => {
  const h = susunEkuivalensi({ ...S, mk_lama: [...S.mk_lama, m('L8', '<b>x</b>')],
    padanan: [...S.padanan, { kode_lama: 'L8', kode_baru: null, tidak_berlanjut: true, catatan: '<i>' }] });
  const semua = htmlEkuivalensi(h, { lama: 'K21', baru: 'K26' });
  assert.match(semua, /Ekuivalensi 1:2/);
  assert.match(semua, /Ekuivalensi 2:1/);
  assert.ok(semua.includes(KETENTUAN['2:1'].slice(0, 30)));
  assert.match(semua, /MK K21 yang tidak berlanjut/);
  assert.ok(semua.includes('&lt;b&gt;x&lt;/b&gt;') && !semua.includes('<b>x</b>'));
  const cari = htmlEkuivalensi(h, { cari: 'fisika' });
  assert.match(cari, /Fisika Dasar 2/);
  assert.doesNotMatch(cari, /Kalkulus/);
  assert.match(htmlEkuivalensi(h, { cari: 'tidak ada mk ini' }), /Tidak ada mata kuliah yang cocok/);
});

test('CSV unduhan bisa diimpor ulang (catatan ikut; ; di isian diganti)', () => {
  const s = { ...S, padanan: [...S.padanan.filter(p => p.kode_lama !== 'LX'),
    { kode_lama: 'L7', kode_baru: 'B6', model: '1:1', tidak_berlanjut: false, catatan: 'a; b\nc' }] };
  const csv = csvEkuivalensi(s);
  assert.match(csv.split('\r\n')[0], /^kode_k21;kode_k26;cara;catatan;nama_k21;nama_k26$/);
  const MK = [...s.mk_lama.map(x => ({ ...x, kurikulum: 'K21' })), ...s.mk_baru.map(x => ({ ...x, kurikulum: 'K26' }))];
  const { baris, galat } = bacaCsvPadanan(csv, MK, 'K21', 'K26');
  assert.deepEqual(galat, []);
  assert.equal(baris.length, s.padanan.length);
  assert.deepEqual(baris.find(b => b.kode_lama === 'L7'), { kurikulum_lama: 'K21', kode_lama: 'L7', kurikulum_baru: 'K26', kode_baru: 'B6',
    model: '1:1', tidak_berlanjut: false, catatan: 'a, b c' });
  assert.deepEqual(baris.find(b => b.kode_lama === 'L6'), { kurikulum_lama: 'K21', kode_lama: 'L6', kurikulum_baru: null, kode_baru: null,
    model: null, tidak_berlanjut: true, catatan: 'Tidak diselenggarakan' });
  assert.equal(baris.find(b => b.kode_lama === 'L3').catatan, null);   // catatan kosong -> null
});
