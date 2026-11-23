// Rekap seminar/sidang TA dan beban dosen (pemilik 2026-11-17; site/rekap-ta.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { waktuJadwal, rekapTA, lembarTA } from '../../site/rekap-ta.js';

const D = { '001': 'Ani', '002': 'Budi', '003': 'Cici' };
const X = [
  { tahap: 'seminar_proposal', status: 'selesai', tanggal: '2026-09-02', pembimbing: ['001'], penguji: ['002', '003'], nama_mahasiswa: 'M1', nim: '1' },
  { tahap: 'sidang_akhir', status: 'terjadwal', tanggal: '2026-12-01', pembimbing: ['001', '002'], penguji: ['003'], nama_mahasiswa: 'M2', nim: '2' },
  { tahap: 'sidang_akhir', status: 'batal', tanggal: '2026-12-05', pembimbing: ['003'], penguji: ['001'], nama_mahasiswa: 'M3', nim: '3' },
];

test('waktu jadwal untuk saringan TS', () => {
  assert.deepEqual(waktuJadwal({ tanggal: '2026-09-02' }), { tahun: 2026, bulan: 9 });
  assert.deepEqual(waktuJadwal({}), { tahun: 0, bulan: 0 });
});

test('rekap per tahap dan beban dosen; batal tidak dihitung', () => {
  const r = rekapTA(X, D);
  assert.equal(r.jumlah, 2);
  assert.deepEqual(r.tahap.sidang_akhir, { semua: 1, selesai: 0, terjadwal: 1 });
  assert.deepEqual(r.tahap.seminar_proposal, { semua: 1, selesai: 1, terjadwal: 0 });
  const ani = r.dosen.find(d => d.nidn === '001'), cici = r.dosen.find(d => d.nidn === '003');
  assert.equal(ani.bimbing, 2); assert.equal(ani.uji, 0);                // jadwal batal (Ani penguji) tidak ikut
  assert.equal(cici.uji, 2); assert.equal(cici.uji_sidang_akhir, 1); assert.equal(cici.bimbing, 0);
  assert.equal(rekapTA(X, D, { hanyaSelesai: true }).jumlah, 1);
});

test('lembar Excel memuat nama dosen, bukan NIDN', () => {
  const L = lembarTA(X, D, r => r.nim === '1' ? '2026/2027' : '');
  assert.equal(L.Jadwal.length, 4);
  // Tanggal, Jam, Tahap, Nama, NIM, Judul (kosong di contoh), Pembimbing, Penguji, Penguji luar
  assert.deepEqual(L.Jadwal[1].slice(1, 10), ['2026-09-02', '', 'Seminar proposal', 'M1', '1', '', 'Ani', 'Budi; Cici', '']);
  assert.equal(L.Jadwal[1][13], '2026/2027');
  assert.deepEqual(L['Beban dosen'][1].slice(0, 3), ['Ani', '001', 2]);
});

test('revisi berjalan dan penerima pengingat (instal-lengkap.sql)', async () => {
  const { revisiBerjalan, penerimaRevisi } = await import('../../site/rekap-ta.js');
  const kini = new Date('2026-12-10T05:00:00Z');
  const R = [
    { id: 1, tahap: 'sidang_akhir', nama_mahasiswa: 'M1', judul: 'J1', pembimbing: ['001', '002'], hasil: 'lulus_revisi', batas_revisi: '2026-12-05' },
    { id: 2, tahap: 'seminar_proposal', nama_mahasiswa: 'M2', judul: 'J2', pembimbing: ['001'], hasil: 'lulus_revisi', batas_revisi: '2026-12-20' },
    { id: 3, tahap: 'sidang_akhir', nama_mahasiswa: 'M3', judul: 'J3', pembimbing: ['001'], hasil: 'lulus_revisi', batas_revisi: '2027-02-01' },
    { id: 4, tahap: 'sidang_akhir', nama_mahasiswa: 'M4', judul: 'J4', pembimbing: ['001'], hasil: 'lulus_revisi', revisi_selesai: '2026-12-01' },
    { id: 5, tahap: 'sidang_akhir', nama_mahasiswa: 'M5', judul: 'J5', pembimbing: ['001'], hasil: 'lulus' },
  ];
  assert.deepEqual(revisiBerjalan(R, kini).map(r => [r.id, r.hari]), [[1, -5], [2, 10], [3, 53]]);
  const { penerima, tanpaEmail } = penerimaRevisi(R, { '001': { nama: 'Ani', email: 'ani@u.id' }, '002': { nama: 'Budi', email: '' } },
    new Map([[1, 'm1@s.id']]), kini);
  assert.deepEqual(penerima.map(p => p.email), ['m1@s.id', 'ani@u.id']);       // M3 belum dekat; Budi tanpa email
  assert.match(penerima[0].rinci, /lewat 5 hari/);
  assert.equal(penerima[1].rinci.split('\n').length, 2);                         // Ani: M1 dan M2
  assert.deepEqual(tanpaEmail.map(r => r.id), [2]);
});

test('Tugas saya: revisi TA hanya untuk pembimbingnya', async () => {
  const { tugasSaya } = await import('../../site/tugas-saya.js');
  const r = [{ nama_mahasiswa: 'M1', judul: 'J1', pembimbing: ['001'], hasil: 'lulus_revisi', batas_revisi: '2026-12-05' }];
  const t = tugasSaya({ saya: { id: 'x', nidn: '001', peran: 'dosen', dtps: false }, revisiTa: r }, new Date('2026-12-10T05:00:00Z'))
    .find(x => x.jenis === 'revisi_ta');
  assert.equal(t.judul, 'Revisi TA M1'); assert.equal(t.hari, -5); assert.equal(t.tingkat, 'lewat');
  assert.equal(tugasSaya({ saya: { id: 'y', nidn: '009', peran: 'dosen', dtps: false }, revisiTa: r }).some(x => x.jenis === 'revisi_ta'), false);
});
