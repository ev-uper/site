// Tinjauan RPS (instal-lengkap.sql, pemilik 2026-11-19).
import test from 'node:test';
import assert from 'node:assert/strict';
import * as T from '../../site/tinjauan-rps.js';

const RG = {
  berkas: [
    { course_code: '41210', course_name: 'Mekanika Tanah I', curriculum: 'K21', term: '2025/2026 Genap', jenis: 'nilai_akhir', class_name: 'A' },
    { course_code: '41210', course_name: 'Mekanika Tanah I', curriculum: 'K21', term: '2025/2026 Genap', jenis: 'nilai_akhir', class_name: 'B' },
    { course_code: '41101', course_name: 'Matematika Lanjut', curriculum: 'K21', term: '2025/2026 Genap', jenis: 'nilai_akhir', class_name: 'A' },
    { course_code: '41101', course_name: 'Matematika Lanjut', curriculum: 'K21', term: '2025/2026 Ganjil', jenis: 'nilai_akhir', class_name: 'A' },
    { course_code: '41101', course_name: 'Matematika Lanjut', curriculum: 'K21', term: '2024/2025 Genap', jenis: 'nilai_akhir', class_name: 'A' },
  ],
  kelas: [
    { course_code: '41210', class_name: 'A', cpl: 'c', counted: 40, above_threshold: 30, status: 'TERCAPAI', term: '2025/2026 Genap' },
    { course_code: '41210', class_name: 'B', cpl: 'c', counted: 10, above_threshold: 4, status: 'BELUM', term: '2025/2026 Genap' },
    { course_code: '41210', class_name: 'A', cpl: 'c', counted: 30, above_threshold: 30, status: 'TERCAPAI', term: '2024/2025 Genap' },
  ],
};
const MK = [
  { kurikulum: 'K21', kode: '41210', nama: 'Mekanika Tanah I', aktif: false, pengampu: [] },
  { kurikulum: 'K21', kode: '41101', nama: 'Matematika Lanjut', aktif: false, pengampu: [] },
  { kurikulum: 'K21', kode: '41999', nama: 'Lama', aktif: false, pengampu: [] },
  { kurikulum: 'K26', kode: '41321', nama: 'Mekanika Tanah 1', aktif: true, pengampu: ['111'] },
  { kurikulum: 'K26', kode: '41301', nama: 'Kalkulus 1', aktif: true, pengampu: ['222'] },
];
const PAD = [{ kurikulum_lama: 'K21', kode_lama: '41210', kurikulum_baru: 'K26', kode_baru: '41321', tidak_berlanjut: false },
             { kurikulum_lama: 'K21', kode_lama: '41999', kurikulum_baru: null, kode_baru: null, tidak_berlanjut: true }];

test('semester terbuka: nilai akhir ada dan >= semester mulai', () => {
  assert.equal(T.urutTerm('2025/2026', 'Genap'), 20252);
  assert.deepEqual(T.pecahTerm('2025/2026 genap'), { term: '2025/2026 Genap', ta: '2025/2026', semester: 'Genap', urut: 20252 });
  assert.equal(T.pecahTerm('Genap 2025'), null);
  assert.deepEqual(T.daftarSemester(RG).map(t => t.term), ['2025/2026 Genap']);
  assert.deepEqual(T.daftarSemester(RG, 20242).map(t => t.term), ['2025/2026 Genap', '2025/2026 Ganjil', '2024/2025 Genap']);
  assert.deepEqual(T.mkSemester(RG, '2025/2026 Genap').map(m => [m.kode, m.kelas]), [['41101', 1], ['41210', 2]]);
});

test('analisis CPL per CPL dan per kelas', () => {
  const A = T.analisisCpl(RG, '41210', '2025/2026 Genap');
  assert.deepEqual(A.perCpl.map(x => [x.cpl, x.n, x.persen, x.belum]), [['c', 50, 68, ['B']]]);
  assert.equal(A.kelas.length, 2);
  assert.equal(A.teks, 'Capaian CPL 2025/2026 Genap: CPL c 68% mahasiswa di atas ambang (belum tercapai di kelas B).');
  assert.deepEqual(T.analisisCpl(RG, '41101', '2025/2026 Genap').perCpl, []);
});

test('RPS sasaran dari padanan; tanpa padanan MK aktif itu sendiri', () => {
  assert.deepEqual(T.sasaranRps(PAD, MK, 'K21', '41210').sasaran.map(m => m.kode), ['41321']);
  assert.deepEqual(T.sasaranRps(PAD, MK, 'K21', '41999'), { adaPadanan: true, tidakBerlanjut: true, sasaran: [] });
  assert.deepEqual(T.sasaranRps(PAD, MK, 'K21', '41101').sasaran, []);
  assert.deepEqual(T.sasaranRps(PAD, MK, 'K26', '41301').sasaran.map(m => m.kode), ['41301']);
});

test('yang boleh mengisi: koordinator MK padanan atau pengampu kelas semester itu', () => {
  const o = { mk: MK, padanan: PAD, kur: 'K21', kode: '41210', ta: '2025/2026', semester: 'Genap',
    kelas: [{ kode_mk: '41210', tahun_akademik: '2025/2026', semester: 'Genap', dosen_email: 'b@u.id' }] };
  assert.equal(T.bolehTinjau({ ...o, saya: { nidn: '111', email: 'a@u.id' } }), true);
  assert.equal(T.bolehTinjau({ ...o, saya: { nidn: '999', email: 'B@u.id' } }), true);
  assert.equal(T.bolehTinjau({ ...o, saya: { nidn: '222', email: 'c@u.id' } }), false);
  assert.equal(T.bolehTinjau({ ...o, semester: 'Ganjil', saya: { nidn: '999', email: 'b@u.id' } }), false);
});

test('pemeriksaan sebelum diajukan sama dengan tinjauan_ajukan', () => {
  const S = T.sasaranRps(PAD, MK, 'K21', '41210');
  assert.equal(T.periksaTinjauan({ data: T.tinjauanKosong() }, S).length, 5);
  const lengkap = { data: { ...T.tinjauanKosong(), analisis_cpl: 'a', materi_metode: 'b', penilaian: 'c', pembaruan: 'd' } };
  assert.deepEqual(T.periksaTinjauan({ ...lengkap, keputusan: 'tetap' }, S), []);
  assert.match(T.periksaTinjauan({ ...lengkap, keputusan: 'revisi' }, S).join(), /rencana perubahan/);
  assert.match(T.periksaTinjauan({ ...lengkap, keputusan: 'revisi', data: { ...lengkap.data, rencana: 'x' } }, { sasaran: [], tidakBerlanjut: false }).join(), /RPS sasaran/);
  assert.match(T.periksaTinjauan({ ...lengkap, keputusan: 'tidak_berlanjut' }, S).join(), /tidak berlanjut/);
});

test('tindak lanjut selesai bila semua RPS sasaran disahkan lagi', () => {
  const t = { keputusan: 'revisi', status: 'disetujui', rps_dasar: { 'K26|41321': 1 }, data: { tenggat: '2999-01-01' } };
  assert.equal(T.statusTindak(t, new Map([['K26|41321', { revisi: 1 }]])).kode, 'terbuka');
  assert.equal(T.statusTindak({ ...t, data: { tenggat: '2000-01-01' } }, new Map()).kode, 'lewat');
  assert.equal(T.statusTindak(t, new Map([['K26|41321', { revisi: 2 }]])).kode, 'selesai');
  assert.equal(T.statusTindak({ ...t, status: 'diajukan' }).kode, 'menunggu');
  assert.equal(T.statusTindak({ keputusan: 'tetap' }).kode, 'tidak_ada');
});

test('CSV padanan: draf dari dokumen K26, TIDAK_BERLANJUT, galat per baris', () => {
  const csv = '\uFEFFkode_k21;nama_k21;kode_k26;cara\n41210;Mekanika Tanah I;41321;nama sama\n41101;Matematika Lanjut;41301;tabel 1:1\n'
    + '41999;Lama;TIDAK_BERLANJUT;\n41888;Tak ada;41301;\n41210;Mekanika Tanah I;;\n';
  const { baris, galat } = T.bacaCsvPadanan(csv, MK);
  assert.deepEqual(baris.map(b => [b.kode_lama, b.kode_baru, b.model, b.tidak_berlanjut]),
    [['41210', '41321', 'nama sama', false], ['41101', '41301', '1:1', false], ['41999', null, null, true]]);
  assert.equal(galat.length, 2);
  assert.match(galat[0], /41888 tidak ada di MK K21/);
  assert.match(T.bacaCsvPadanan('a;b\n1;2', MK).galat[0], /wajib ada/);
});

// ---------- Tahap 2 (pemilik 2026-11-19) ----------
const TIN = [
  { id: 1, kurikulum: 'K21', kode_mk: '41210', tahun_akademik: '2025/2026', semester: 'Genap', status: 'disetujui', keputusan: 'revisi',
    rps_dasar: { 'K26|41321': 1 }, disetujui_pada: '2026-11-19T01:00:00Z',
    data: { analisis_cpl: 'CPL c belum di kelas B', materi_metode: 'm', penilaian: 'p', pembaruan: 'u', rencana: 'Tambah studi kasus', tenggat: '2999-01-31' } },
  { id: 2, kurikulum: 'K21', kode_mk: '41101', tahun_akademik: '2025/2026', semester: 'Genap', status: 'diajukan', keputusan: 'tetap', data: {} },
];

test('rekap semester, CSV, dan kalimat LED', () => {
  const R = T.rekapSemester({ ringkasan: RG, term: '2025/2026 Genap', tinjauan: TIN, padanan: PAD, mk: MK, rpsMap: new Map() });
  assert.deepEqual([R.n, R.disetujui, R.diajukan, R.revisi, R.tetap, R.tindak.terbuka], [2, 1, 1, 1, 0, 1]);
  assert.deepEqual(R.baris.find(b => b.kode === '41210').belumCpl, ['c']);
  const csv = T.csvTinjauan(R).split('\r\n');
  assert.equal(csv.length, 3);
  assert.ok(csv[0].startsWith('\uFEFFsemester;kurikulum;kode'));
  assert.match(csv.find(l => l.includes(';41210;')), /RPS direvisi;CPL c;CPL c belum di kelas B;m;p;u;Tambah studi kasus;2999-01-31;RPS 41321 belum disahkan ulang;2026-11-19$/);
  const L = T.kalimatLed(R);
  assert.match(L, /^Pada semester 2025\/2026 Genap, RPS 2 mata kuliah .* 1 tinjauan telah disetujui Ketua Program Studi dan 1 belum selesai./);
  assert.match(L, /CPL c \(41210\)/);
  assert.match(L, /0 RPS dinyatakan tetap dan 1 RPS diputuskan direvisi; tindak lanjut revisi telah selesai untuk 0 RPS dan masih berjalan untuk 1 RPS\./);
  assert.equal(T.kalimatLed({ n: 0 }), '');
});

test('unsur 5-8 hanya bila semua MK semester terbaru disetujui', () => {
  assert.deepEqual(T.unsurDariTinjauan({ ringkasan: RG, tinjauan: TIN }), { term: '2025/2026 Genap', n: 2, disetujui: 1, unsur: [] });
  const semua = TIN.map(t => ({ ...t, status: 'disetujui' }));
  assert.deepEqual(T.unsurDariTinjauan({ ringkasan: RG, tinjauan: semua }).unsur, [5, 6, 7, 8]);
  assert.deepEqual(T.unsurDariTinjauan({ ringkasan: null }).unsur, []);
});

test('bagian E RPS K26 dari padanan dan tinjauan disetujui terbaru', () => {
  const B = T.bahanTinjauan({ tinjauan: TIN, padanan: PAD, kur: 'K26', kode: '41321' });
  assert.equal(B.kodeLama, '41210');
  assert.equal(B.bahan[0], 'Tinjauan RPS Genap 2025/2026 (MK 41210, disetujui Kaprodi):');
  assert.ok(B.bahan.includes('Analisis CPL: CPL c belum di kelas B'));
  assert.equal(B.bahan.at(-1), 'Rencana revisi: Tambah studi kasus');
  assert.deepEqual(T.bahanTinjauan({ tinjauan: TIN, padanan: PAD, kur: 'K26', kode: '41301' }), { kodeLama: '', tinjauan: null, bahan: [] });
});

test('137: anggota team teaching (Penyusunan kelas) boleh meninjau MK itu pada semester itu saja', () => {
  const o = { mk: MK, padanan: PAD, kur: 'K21', kode: '41210', ta: '2025/2026', semester: 'Genap', kelas: [],
    tim: [{ tahun_akademik: '2025/2026', semester: 'Genap', kurikulum: 'K21', kode_mk: '41210', kelas: 'A', peran: 'anggota' }] };
  assert.equal(T.bolehTinjau({ ...o, saya: { nidn: '555', email: 'tim@u.id' } }), true);
  assert.equal(T.bolehTinjau({ ...o, semester: 'Ganjil', saya: { nidn: '555', email: 'tim@u.id' } }), false);
  assert.equal(T.bolehTinjau({ ...o, tim: [], saya: { nidn: '555', email: 'tim@u.id' } }), false);
});
