// Standar SPMI, impor rekap SPM, dan siklus PPEPP (pemilik 2026-11-12).
import test from 'node:test';
import assert from 'node:assert/strict';
import { ringkasLembar, kodeButir, petaSub, bacaLembarStandar, bacaRekapSPM, pilihanLembar, rencanaImporSPM, siklusPPEPP, tsDariTanggal, tsSiklus,
  perluAnalisis } from '../../site/standar-spmi.js';

// Bentuk rekap SPM: dua baris judul (kolom, lalu TS), kode di kolom B, baris tanpa kode = rincian butir di atasnya.
const KEPALA = [['Standar', 'Butir Standar', 'Pernyataan Isi Standar', 'Jenis Luaran', 'PIC 1', 'PIC 2', 'Target Capaian', null, 'Referensi'],
  [null, null, null, null, null, null, '2026/2027', '2027/2028', null]];
const LEMBAR = [...KEPALA,
  ['A\nPendidikan', 'A.01.01', 'WRA memastikan kriteria CPL', 'Pedoman kurikulum', 'WRA', null, 'Tersedia', 'Tersedia', 'Pasal 6'],
  [null, 'A.03.6a', 'Dekan memastikan dosen tetap', 'Jumlah SKS mata kuliah dasar.\na.\tDiploma 3', 'Dekan', null, '≥ 20 SKS', '≥ 20 SKS', 'Pasal 9'],
  [null, null, null, 'b.  Sarjana', 'Dekan', 'Kaprodi', '≥ 25 SKS', '≥ 30 SKS', null],
  [null, null, null, null, null, null, null, null, null]];
const DAFTAR = [['No.', 'Standar', null, 'Keterangan'], ['A', 'Standar Pendidikan', '1', 'Standar Luaran Pendidikan'],
  [null, null, '3', 'Standar Masukan Pendidikan'], ['J', 'Standar Perpustakaan', '1', null]];

test('kode butir dinormalkan; selain kode = kosong', () => {
  assert.equal(kodeButir('A.03.6a'), 'A.03.06a');
  assert.equal(kodeButir('O.04. 13'), 'O.04.13');
  assert.equal(kodeButir(' A.01.02b '), 'A.01.02b');
  assert.equal(kodeButir('Butir Standar'), '');
  assert.equal(kodeButir(null), '');
});

test('nama sub-standar dari Daftar Tabel; keterangan kosong memakai nama standar', () => {
  assert.deepEqual(petaSub(DAFTAR), { 'A.01': 'Standar Luaran Pendidikan', 'A.03': 'Standar Masukan Pendidikan', 'J.01': 'Standar Perpustakaan' });
});

test('lembar: butir, induk terbawa, rincian per jenjang digabung ke butir di atasnya', () => {
  const xs = bacaLembarStandar('Pendidikan', LEMBAR, petaSub(DAFTAR));
  assert.equal(xs.length, 2);
  assert.deepEqual(xs[0], { kode: 'A.01.01', induk: 'A Pendidikan', sub: 'Standar Luaran Pendidikan', lembar: 'Pendidikan',
    pernyataan: 'WRA memastikan kriteria CPL', luaran: 'Pedoman kurikulum', pic: 'WRA', referensi: 'Pasal 6',
    target: { 2027: 'Tersedia', 2028: 'Tersedia' } });
  const b = xs[1];
  assert.equal(b.kode, 'A.03.06a');
  assert.equal(b.induk, 'A Pendidikan');
  assert.equal(b.sub, 'Standar Masukan Pendidikan');
  assert.equal(b.pic, 'Dekan; Kaprodi');
  assert.equal(b.luaran, 'Jumlah SKS mata kuliah dasar.\na. Diploma 3\nb. Sarjana');
  assert.equal(b.target[2027], 'a. Diploma 3: ≥ 20 SKS\nb. Sarjana: ≥ 25 SKS');
  assert.equal(b.target[2028], 'a. Diploma 3: ≥ 20 SKS\nb. Sarjana: ≥ 30 SKS');
  assert.deepEqual(bacaLembarStandar('Kosong', [['tanpa judul kolom']]), []);
});

test('lembar: LAM lain tidak ditawarkan, unit lain tanpa centang, Daftar Tabel bukan butir', () => {
  assert.equal(pilihanLembar('Akreditasi Unggul LAMTEK'), 'bawaan');
  assert.equal(pilihanLembar('Pendidikan'), 'bawaan');
  assert.equal(pilihanLembar('IKU PT'), 'bawaan');
  assert.equal(pilihanLembar('Akreditasi Unggul LAMINFOKOM'), 'lain');
  assert.equal(pilihanLembar('Akreditasi Unggul Prodi BAN-PT'), 'lain');
  assert.equal(pilihanLembar('Perpustakaan'), 'pilihan');
  assert.equal(pilihanLembar('Daftar Tabel'), 'daftar');
  const R = bacaRekapSPM({ 'Daftar Tabel': DAFTAR, Pendidikan: LEMBAR, 'Akreditasi Unggul LAMSAMA': LEMBAR });
  assert.deepEqual(R.lembar.map(l => [l.nama, l.jenis, l.butir.length]), [['Pendidikan', 'bawaan', 2], ['Akreditasi Unggul LAMSAMA', 'lain', 2]]);
});

test('rencana impor: baru, berubah, sama, ganda; butir hilang dilaporkan, standar prodi tidak', () => {
  const xs = bacaLembarStandar('Pendidikan', LEMBAR, petaSub(DAFTAR));
  const lama = [{ id: 1, ...xs[0], target: undefined }, { id: 2, ...xs[1], pernyataan: 'teks lama' },
    { id: 3, kode: 'A.09.09', lembar: 'Pendidikan', asal: 'institusi' }, { id: 4, kode: 'P.01.01', lembar: 'Pendidikan', asal: 'prodi' }];
  const r = rencanaImporSPM([...xs, xs[0]], lama);
  assert.deepEqual([r.baru.length, r.ubah.length, r.sama.length], [0, 1, 1]);
  assert.equal(r.ubah[0].id, 2);
  assert.deepEqual(r.ganda, ['A.01.01']);
  assert.deepEqual(r.hilang.map(x => x.kode), ['A.09.09']);
  assert.equal(r.target, 4);
});

test('TS dari tanggal: September mulai TS baru', () => {
  assert.equal(tsDariTanggal('2026-08-31'), 2026);
  assert.equal(tsDariTanggal('2026-09-01'), 2027);
  assert.equal(tsDariTanggal(''), null);
});

const S = [{ id: 1, kode: 'A.01.01', pernyataan: 'x', dipantau: true, aktif: true },
  { id: 2, kode: 'A.01.02', pernyataan: 'y', dipantau: true, aktif: true },
  { id: 3, kode: 'A.01.03', pernyataan: 'z', dipantau: false, aktif: true },
  { id: 4, kode: 'A.01.04', pernyataan: 'w', dipantau: true, aktif: true },
  { id: 5, kode: 'A.01.05', pernyataan: 'v', dipantau: true, aktif: true, berlaku_sejak: '2027-01-01' }];
const X = {
  standar: S,
  capaian: [{ standar_id: 1, tahun_ts: 2026, target: 'Tersedia', capaian: 'Ada', status: 'tercapai', bukti_url: 'https://contoh.id/a' },
            { standar_id: 2, tahun_ts: 2026, target: '≥ 70%', capaian: '60%', status: 'belum', bukti_url: 'https://contoh.id/b' },
            { standar_id: 4, tahun_ts: 2026, target: 'Tersedia', status: 'tidak_berlaku' }],
  revisi: [{ standar_id: 2, tanggal: '2026-03-10', perubahan: 'target naik' }, { standar_id: 2, tanggal: '2026-10-01', perubahan: 'TS lain' }],
  target: [{ jenis: 'iku', nama: 'Lulus tepat waktu', tahun_ts: 2026, target: 70, capaian: 60, arah: 'minimal', standar_id: 1 },
           { jenis: 'iku', nama: 'Lepas', tahun_ts: 2026, target: 1, capaian: 1, arah: 'minimal' }],
  temuan: [{ id: 9, tahun_ts: 2026, standar_id: 1, rencana: 'tinjau RPS', status: 'proses' }, { id: 10, tahun_ts: 2026, standar_id: null }],
  rapat: [{ id: 1, jenis: 'rtm', tanggal: '2026-02-01', judul: 'RTM 2026' }, { id: 2, jenis: 'rapat_prodi', tanggal: '2026-02-02', judul: 'x' }],
};

test('siklus: lima tahap per butir dipantau yang berlaku pada TS', () => {
  const R = siklusPPEPP(X, 2026);
  assert.deepEqual(R.baris.map(b => b.standar.kode), ['A.01.01', 'A.01.02', 'A.01.04']);
  const [a, b, d] = R.baris;
  // A.01.01 tercapai, tetapi IKU terkait belum tercapai tanpa rencana perbaikan -> pengendalian kurang.
  assert.deepEqual(Object.fromEntries(Object.entries(a.tahap).map(([k, v]) => [k, v.status])),
    { penetapan: 'ada', pelaksanaan: 'ada', evaluasi: 'ada', pengendalian: 'kurang', peningkatan: 'na' });
  // A.01.02 belum tercapai tanpa rencana -> kurang; ada revisi pada TS -> peningkatan ada.
  assert.equal(b.tahap.pengendalian.status, 'kurang');
  assert.equal(b.tahap.peningkatan.status, 'ada');
  assert.equal(b.revisi.length, 1);
  assert.ok(Object.values(d.tahap).every(t => t.status === 'na'));
  assert.equal(R.rtm.length, 1);
  assert.deepEqual(R.lepas, { iku: 1, temuan: 1 });
  assert.equal(R.lengkap, 1);
  assert.equal(R.hitung.penetapan.ada, 2);
});

test('siklus: rencana diisi -> pengendalian ada; tanpa capaian -> penetapan/pelaksanaan/evaluasi kurang', () => {
  const Y = { ...X, capaian: X.capaian.map(c => c.standar_id === 2 ? { ...c, rencana: 'klinik TA' } : c),
    target: X.target.map(r => r.standar_id === 1 ? { ...r, rencana_perbaikan: 'bimbingan intensif' } : r) };
  const R = siklusPPEPP(Y, 2026);
  assert.equal(R.baris[0].tahap.pengendalian.status, 'ada');
  assert.equal(R.baris[1].tahap.pengendalian.status, 'ada');
  const K = siklusPPEPP({ standar: [S[0]] }, 2027);
  assert.deepEqual(['penetapan', 'pelaksanaan', 'evaluasi'].map(k => K.baris[0].tahap[k].status), ['kurang', 'kurang', 'kurang']);
  assert.ok(tsSiklus(X, new Date('2026-11-12')).includes(2027));
});

test('analisis IKU: hanya indikator belum tercapai yang belum lengkap analisis dan rencananya', () => {
  const r = { target: 70, capaian: 60, arah: 'minimal' };
  assert.equal(perluAnalisis(r), true);
  assert.equal(perluAnalisis({ ...r, analisis: 'a' }), true);
  assert.equal(perluAnalisis({ ...r, analisis: 'a', rencana_perbaikan: 'b' }), false);
  assert.equal(perluAnalisis({ ...r, capaian: 70 }), false);
  assert.equal(perluAnalisis({ ...r, capaian: null }), false);
});

test('pantauan per lembar: jumlah dipantau dari total, standar prodi tanpa lembar dikelompokkan', () => {
  const r = ringkasLembar([{ lembar: 'Perpustakaan', dipantau: true }, { lembar: 'Perpustakaan', dipantau: false },
    { lembar: 'Akreditasi Unggul LAMTEK', dipantau: true }, { asal: 'prodi', dipantau: true }, {}]);
  assert.deepEqual(r.map(({ lembar, total, dipantau }) => ({ lembar, total, dipantau })),
    [{ lembar: '(tanpa lembar)', total: 1, dipantau: 1 }, { lembar: 'Akreditasi Unggul LAMTEK', total: 1, dipantau: 1 },
    { lembar: 'Perpustakaan', total: 2, dipantau: 1 }, { lembar: 'Standar prodi', total: 1, dipantau: 1 }]);
});

test('PIC prodi: Dekan atau Kaprodi dari kolom PIC Excel SPM (pemilik 2026-11-13)', async () => {
  const { picProdi, PIC_PRODI } = await import('../../site/standar-spmi.js');
  assert.deepEqual(PIC_PRODI, ['dekan', 'kaprodi']);
  assert.equal(picProdi({ pic: 'Dekan' }), true);
  assert.equal(picProdi({ pic: 'WRA; Kaprodi' }), true);
  assert.equal(picProdi({ pic: 'WRA; WRS' }), false);
  assert.equal(picProdi({ pic: 'Rektor' }), false);
  assert.equal(picProdi({}), false);
  const r = ringkasLembar([{ lembar: 'IKU PT', pic: 'Dekan', dipantau: true }, { lembar: 'IKU PT', pic: 'WRA', dipantau: true },
    { lembar: 'Pendidikan', pic: 'Kaprodi', dipantau: true }, { lembar: 'Pendidikan', pic: 'WRS', dipantau: false }]);
  assert.deepEqual(r.map(x => [x.lembar, x.dipantau, x.picProdi, x.hanyaProdi]), [['IKU PT', 2, 1, false], ['Pendidikan', 1, 1, true]]);
});
