// Rekap RPS kurikulum (pemilik 2026-11-19): kalender asesmen dan peta CPL.
import test from 'node:test';
import assert from 'node:assert/strict';
import { versiRps, semesterKurikulum, kalenderAsesmen, petaCplKurikulum } from '../../site/rps-kurikulum.js';

const MK = [
  { kurikulum: 'K26', kode: 'A1', nama: 'Mekanika', sks: 3, semester: 3, aktif: true },
  { kurikulum: 'K26', kode: 'A2', nama: 'Hidrolika', sks: 3, semester: 3, aktif: true },
  { kurikulum: 'K26', kode: 'A3', nama: 'Struktur', sks: 3, semester: 7, aktif: true },
  { kurikulum: 'K26', kode: 'P1', nama: 'Pilihan', sks: 2, semester: null, aktif: true },
  { kurikulum: 'K21', kode: 'L1', nama: 'Lama', sks: 2, semester: 3, aktif: false },
];
const pk = (pekan, asesmen, jenis = 'kuliah') => ({ pekan, jenis, asesmen });
const RPS = new Map([
  ['K26|A1', { status: 'disahkan', data: { pekan: [] }, sah: { rps: { pekan: [pk('3', ['Kuis 1']), pk('8', [], 'uts'), pk('12', ['Tugas 1'])] } } }],
  ['K26|A2', { status: 'draf', data: { pekan: [pk('11-12', ['Tugas besar']), pk('16', [], 'uas')] } }],
]);

test('versi RPS dan semester kurikulum', () => {
  assert.equal(versiRps(RPS.get('K26|A1')).versi, 'disahkan');
  assert.equal(versiRps({ status: 'draf', data: { a: 1 }, sah: { rps: { b: 1 } } }).versi, 'disahkan (revisi berjalan)');
  assert.equal(versiRps(null), null);
  assert.deepEqual(semesterKurikulum(MK, 'K26'), ['3', '7', '']);
});

test('kalender asesmen: pekan, UTS/UAS tidak dihitung, pekan terpadat', () => {
  const K = kalenderAsesmen({ mk: MK, rps: RPS, kur: 'K26', semester: '3' });
  assert.deepEqual(K.baris.map(b => [b.kode, b.versi]), [['A1', 'disahkan'], ['A2', 'draf']]);
  assert.deepEqual(K.baris[0].pekan, { 3: ['Kuis 1'], 8: ['UTS'], 12: ['Tugas 1'] });
  assert.deepEqual(K.baris[1].pekan, { 11: ['Tugas besar'], 12: ['Tugas besar'], 16: ['UAS'] });
  assert.deepEqual(K.perPekan.filter(x => x.n).map(x => [x.pekan, x.n]), [[3, 1], [11, 1], [12, 2]]);
  assert.equal(K.maks, 2);
  assert.equal(kalenderAsesmen({ mk: MK, rps: RPS, kur: 'K26', semester: '7' }).tanpaRps, 1);
});

test('peta CPL: MK yang menilai, Bloom tertinggi, dibebankan tidak dinilai, HOTS per tahun', () => {
  const S = (subs, bobot) => ({ sub: subs, bobot });
  const struktur = new Map([
    ['K26|A1', S([{ kode: 'S1', cpl: 'C', rumusan: 'menjelaskan (C2)' }, { kode: 'S2', cpl: 'C', rumusan: 'menganalisis (C4, P2)' }],
                 { S1: { Kuis: 40 }, S2: { Tugas: 60 } })],
    ['K26|A3', S([{ kode: 'S1', cpl: 'D', rumusan: 'merancang (C6)' }], { S1: { Proyek: 100 } })],
    ['K26|A2', S([{ kode: 'S1', cpl: 'C', rumusan: 'menghitung (C3)' }], { S1: {} })],
  ]);
  const refCpl = [{ kurikulum: 'K26', kode: 'D', rumusan: 'Merancang', urutan: 2 }, { kurikulum: 'K26', kode: 'C', rumusan: 'Menganalisis', urutan: 1 }];
  const petaMk = [{ kurikulum: 'K26', kode_mk: 'A2', cpl: 'C' }];
  const P = petaCplKurikulum({ mk: MK, struktur, refCpl, petaMk, kur: 'K26' });
  assert.deepEqual(P.sems, ['3', '7', '']);
  assert.deepEqual(P.baris.map(c => [c.kode, c.nMk, c.levelMax, c.tanpaNilai]), [['C', 1, 'C4', ['A2']], ['D', 1, 'C6', []]]);
  assert.deepEqual(P.baris[0].sel['3'], [{ kode: 'A1', nama: 'Mekanika', level: 'C4', ranah: ['P2'], bobot: 100 }]);
  assert.deepEqual(P.belumStruktur, ['P1']);
  assert.deepEqual(P.hotsTahun, [{ tahun: 2, n: 2, rata: 30, target: 10 }, { tahun: 4, n: 1, rata: 100, target: 50 }]);
});

test('kemajuan RPS: belum, draf, revisi, diajukan, disahkan, bertanda tangan (pemilik 2026-11-19)', async () => {
  const { kemajuanRps, statusKemajuan, csvKemajuan } = await import('../../site/rps-kurikulum.js');
  assert.deepEqual(statusKemajuan(null, []), { kode: 'belum', lama: false });
  assert.deepEqual(statusKemajuan(null, [{ revisi: null }]), { kode: 'ttd', lama: false });            // RPS di luar situs
  assert.equal(statusKemajuan({ status: 'draf', sah: null }).kode, 'draf');
  assert.equal(statusKemajuan({ status: 'draf', sah: {} }).kode, 'revisi');
  assert.equal(statusKemajuan({ status: 'diajukan' }).kode, 'diajukan');
  // 121 (pemilik 2026-11-19): lengkap = ditetapkan Dekan secara elektronik; tanpa Dekan aktif cukup disahkan; unggahan tidak menentukan.
  assert.deepEqual(statusKemajuan({ status: 'disahkan', revisi: 2, tetap_pada: null }, [], true), { kode: 'disahkan', lama: false });
  assert.deepEqual(statusKemajuan({ status: 'disahkan', revisi: 2, tetap_pada: '2026-11-19T03:00:00Z' }, [], true), { kode: 'ttd', lama: false });
  assert.deepEqual(statusKemajuan({ status: 'disahkan', revisi: 2, tetap_pada: null }, [], false), { kode: 'ttd', lama: false });
  assert.deepEqual(statusKemajuan({ status: 'disahkan', revisi: 2, tetap_pada: null }, [{ revisi: 2 }], true), { kode: 'disahkan', lama: false });
  const mk = ['A1', 'A2', 'A3', 'B1'].map((kode, i) => ({ kurikulum: i < 3 ? 'K26' : 'K21', kode, nama: kode, semester: '1', pengampu: ['01'] }));
  const rps = new Map([['K26|A2', { status: 'diajukan', diperbarui: '2026-11-19T03:00:00Z' }], ['K26|A3', { status: 'disahkan', revisi: 1 }]]);
  const h = kemajuanRps({ mk, rps, ttd: new Map([['K26|A3', [{ revisi: 1 }]]]), kur: 'K26', nama: m => m.pengampu.map(n => `Dosen ${n}`) });
  assert.equal(h.total, 3);
  assert.deepEqual({ belum: h.jumlah.belum, diajukan: h.jumlah.diajukan, ttd: h.jumlah.ttd }, { belum: 1, diajukan: 1, ttd: 1 });
  assert.match(csvKemajuan(h), /^"kode","nama","semester","sifat","status","penyusun","diperbarui","review_terkirim","kesimpulan_review","rerata_review","ditanggapi"\r\n"A1","A1","1","","Belum dibuat","Dosen 01","","","","",""/);
});

test('kemajuan RPS: rekap review sejawat per MK dan kategori saringan (119, pemilik 2026-11-19)', async () => {
  const { kemajuanRps, csvKemajuan, jumlahReview, teksReview } = await import('../../site/rps-kurikulum.js');
  const mk = ['A1', 'A2', 'A3', 'A4'].map(kode => ({ kurikulum: 'K26', kode, nama: kode, semester: '1', pengampu: [] }));
  const rps = new Map(['A2', 'A3', 'A4'].map(k => [`K26|${k}`, { status: 'diajukan' }]));
  const review = new Map([['K26|A2', { ditunjuk: 2, terkirim: 2, kesimpulan: ['layak', 'perbaikan_besar'], rerata: 3.25, ditanggapi: 1 }],
    ['K26|A3', { ditunjuk: 1, terkirim: 0, kesimpulan: [], rerata: null, ditanggapi: 0 }]]);
  const h = kemajuanRps({ mk, rps, kur: 'K26', review });
  assert.deepEqual(jumlahReview(h), { direview: 1, menunggu: 1, tanpa: 1, besar: 1, belum_tanggap: 1 });
  assert.equal(teksReview(review.get('K26|A2')), '2/2 terkirim · rerata 3,25 · ditanggapi 1/2');
  assert.equal(teksReview(review.get('K26|A3')), '0/1 terkirim');
  assert.match(csvKemajuan(h), /"A2","A2","1","","Diajukan","","","2\/2","Layak disahkan; Perlu perbaikan besar","3,25","1\/2"/);
});
