// RPS K26 (pemilik 2026-11-18; site/rps.js, site/rps-docx.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import * as R from '../../site/rps.js';
import { dokumenRps, tanggalPanjang } from '../../site/rps-docx.js';

const mk = { kurikulum: 'K26', kode: '13301', nama: 'Mekanika Tanah', sks: 3, sks_kuliah: 2, sks_praktikum: 1, semester: 5 };
const cpl = [{ kode: 'C', rumusan: 'Mampu menganalisis rekayasa geoteknik' }];
const struktur = () => ({ versi: '1', cpmk: [{ kode: 'CPMK-1', rumusan: 'Mahasiswa mampu menganalisis sifat tanah (C4)' }],
  sub: [{ kode: 'S1', cpmk: 'CPMK-1', cpl: 'C', rumusan: 'Mahasiswa mampu menjelaskan klasifikasi tanah (C2)' },
        { kode: 'S2', cpmk: 'CPMK-1', cpl: 'C', rumusan: 'Mahasiswa mampu menganalisis konsolidasi (C4, HOTS)' }],
  asesmen: [{ nama: 'Kuis 1' }, { nama: 'Tugas 1' }, { nama: 'UTS' }, { nama: 'UAS' }],
  bobot: { S1: { 'Kuis 1': 20, UTS: 20 }, S2: { 'Tugas 1': 30, UAS: 30 } } });

/** RPS lengkap: semua butir wajib Panduan bagian 6 terisi. */
function rpsLengkap(){
  const r = R.rpsKosong(mk, { prodi: 'Teknik Contoh' }, new Date('2026-11-18T00:00:00Z'));
  Object.assign(r, { pengembang: 'd1', pengampu: 'Adi', tujuan: '1. A\n2. B\n3. C', deskripsi: 'Tanah', pustaka: [{ kode: 'DAS', teks: 'Das (2019). Soil.' }],
    scl: { ada: true, teks: 'Case Method pekan 9' }, integrasi: { ada: false, teks: '' }, direktori: { status: 'tidak_tersedia', teks: '' },
    evaluasi: { baru: true }, peta: { sub: { S2: { ke: 'S1', jenis: 'hierarkikal' } }, entry: '' },
    rubrik: { 'Tugas 1': { tingkat: ['Sangat baik', 'Baik', 'Cukup', 'Kurang'], kriteria: [{ nama: 'Analisis', bobot: '100', deskriptor: ['a', 'b', 'c', 'd'] }] } } });
  r.pekan = r.pekan.map(p => (p.jenis !== 'kuliah' ? p : { ...p, sub: [+p.pekan < 8 ? 'S1' : 'S2'], materi: 'Materi', indikator: 'Ketepatan ≥ 80%',
    luring: 'Kuliah + Case Method; PB 2×50′', asesmen: p.pekan === '3' ? ['Kuis 1'] : p.pekan === '12' ? ['Tugas 1'] : [],
    bentuk_pb: ['5', '6', '7'].includes(p.pekan) ? ['kuliah', 'praktikum'] : ['kuliah'], scl: ['9', '10'].includes(p.pekan) ? ['case'] : [],
    penugasan: p.pekan === '12' ? 'Laporan analisis konsolidasi' : '' }));
  return r;
}
const ctx = (r, o = {}) => ({ mk, struktur: struktur(), rps: r, cpl, pengembang: { nama: 'Adi', nama_gelar: 'Adi, S.T., M.T.', nip: '123' },
  kaprodi: { nama: 'Budi', nip: '9' }, ...o });

test('jenis asesmen, jenis MK, Bloom, tahun, rentang pekan', () => {
  assert.deepEqual(['Kuis 2', 'UTS', 'Ujian Akhir', 'Tugas Besar', 'Laporan praktikum', 'Keaktifan'].map(R.tebakJenis),
    ['kuis', 'uts', 'uas', 'tugas', 'tugas', 'lainnya']);
  assert.equal(R.jenisAsesmen({ nama: 'Kuis 1', jenis: 'tugas' }), 'tugas');
  assert.deepEqual(['21307', '13101', '13201', '13401', 'SI201'].map(R.jenisDariKode), ['MKPS', 'MKPT', 'MKU', 'MKP', '']);
  assert.deepEqual(R.bloom('Mahasiswa mampu ... dengan tepat (C4, A3, HOTS)'), { kode: ['C4', 'A3'], c: 4 });
  assert.deepEqual(R.bloom('tanpa kode'), { kode: [], c: 0 });
  assert.deepEqual([1, 2, 5, 8, 'Genap'].map(R.tahunMK), [1, 1, 3, 4, null]);
  assert.deepEqual(R.rentangPekan('11 - 13'), [11, 12, 13]);
  assert.deepEqual(R.rentangPekan('8'), [8]);
  assert.deepEqual(R.rentangPekan('7-5'), []);
  assert.deepEqual(R.kerangkaPekan().map(p => p.jenis === 'kuliah' ? p.pekan : p.jenis), ['1', '2', '3', '4', '5', '6', '7', 'uts', '9', '10', '11', '12', '13', '14', '15', 'uas']);
});

test('HOTS = bobot Sub-CPMK C4-C6 terhadap total, dengan target per tahun', () => {
  assert.deepEqual(R.hots(struktur(), 5), { persen: 60, sub: ['S2'], tahun: 3, target: 30 });
  assert.equal(R.hots(struktur(), 1).target, 0);
});

test('isian awal dari data MK', () => {
  const r = R.rpsKosong({ ...mk, kode: '21307' }, { prodi: 'Teknik Contoh' }, new Date('2026-11-18T00:00:00Z'));
  assert.equal(r.versi, '1');
  assert.deepEqual(r.identitas, { jenis_mk: 'MKPS', sks: { t: 2, p: 1, pl: 0, s: 0 }, semester: '5', tanggal: '2026-11-18',
    penyelenggara: 'Program Studi Teknik Contoh' });
  assert.equal(R.rpsKosong({ kode: '13101', sks: 2 }).identitas.penyelenggara, 'Universitas Pertamina');
  assert.equal(r.pekan.length, 16);
  const lama = R.rapikanRps({ versi: '1', tujuan: 'X', identitas: { semester: '6' } }, mk, {});
  assert.equal(lama.tujuan, 'X'); assert.equal(lama.identitas.semester, '6'); assert.equal(lama.identitas.sks.t, 2); assert.equal(lama.pekan.length, 16);
});

test('daftar periksa: RPS lengkap bersih, RPS kosong menyebut kekurangan per bagian', () => {
  assert.deepEqual(R.periksaRps(ctx(rpsLengkap())), []);
  const kosong = R.periksaRps(ctx(R.rpsKosong(mk), { struktur: null, pengembang: null, kaprodi: null }));
  const bagian = new Set(kosong.filter(t => t.tingkat === 'galat').map(t => t.bagian));
  assert.deepEqual([...bagian].sort(), ['A', 'B', 'C', 'D', 'E']);
  assert.ok(kosong.some(t => t.tingkat === 'saran' && /Kaprodi/.test(t.pesan)));
});

test('daftar periksa: aturan Panduan bagian 6 satu per satu', () => {
  const pesan = (r, o) => R.periksaRps(ctx(r, o)).map(t => t.pesan).join(' | ');
  const S = struktur(); S.sub[0].cpl = ''; S.sub[1].rumusan = 'tanpa kode'; S.bobot.S2.UAS = 10;
  const p = pesan(rpsLengkap(), { struktur: S });
  assert.match(p, /S1: pilih CPL/); assert.match(p, /S2: akhiri rumusan dengan kode Bloom/); assert.match(p, /Total bobot penilaian 80%/);
  const r = rpsLengkap(); r.pekan = r.pekan.filter(x => x.pekan !== '4'); r.pekan[0].pekan = '1-2';
  assert.match(pesan(r), /Pekan tercantum lebih dari sekali: 2/); assert.match(pesan(r), /Pekan belum terisi: 4/);
  const r2 = rpsLengkap(); r2.pekan.forEach(x => { x.luring = 'Kuliah'; x.scl = []; }); r2.scl.ada = false;
  assert.match(pesan(r2), /minimal satu metode SCL/);
  const r3 = rpsLengkap(); r3.identitas.sks = { t: 3, p: 1, pl: 0, s: 0 };
  assert.match(pesan(r3), /T\+P\+PL\+S \(4\) tidak sama dengan sks MK \(3\)/);
  const r4 = rpsLengkap(); r4.pekan = r4.pekan.map(x => ({ ...x, asesmen: [] }));
  assert.match(pesan(r4), /Kuis 1 \(bagian B\) belum dijadwalkan/);
  const r5 = rpsLengkap(); r5.identitas.semester = '7';   // semester di identitas RPS menentukan tahun MK
  assert.match(pesan(r5, { struktur: { ...struktur(), sub: struktur().sub.map(x => ({ ...x, rumusan: x.rumusan.replace('C4', 'C3') })) } }),
    /HOTS 0%; disarankan ≥ 50% untuk MK tahun ke-4/);
});

test('model ekspor: kolom asesmen per jenis, total, orang', () => {
  const M = R.modelRps(ctx(rpsLengkap()));
  assert.deepEqual(M.kolom.map(c => [c.label, c.total]), [['Kuis', 20], ['Tugas', 30], ['UTS', 20], ['UAS', 30]]);
  assert.deepEqual(M.sub.map(x => [x.kode, x.cpl, x.asesmen.kuis, x.asesmen.uas, x.bobot]), [['S1', 'C', ['Kuis 1'], [], 40], ['S2', 'C', [], ['UAS'], 60]]);
  assert.equal(M.total, 100);
  assert.deepEqual(M.pengembang, { nama: 'Adi, S.T., M.T.', nip: '123' });
  assert.deepEqual(M.kaprodi, { nama: 'Budi', nip: '9' });
  assert.equal(R.namaBerkasRps(mk), 'RPS_K26_13301_Mekanika_Tanah.docx');
});

test('Word: enam bagian formulir, judul tabel, UTS/UAS, nama pengesah', () => {
  const x = dokumenRps(R.modelRps(ctx(rpsLengkap())));
  for (const t of ['Identitas Mata Kuliah dan Lembar Pengesahan', 'Capaian Pembelajaran', 'SUB-CPMK DAN PEMETAAN KORELASI CAPAIAN PEMBELAJARAN',
    'Tujuan dan Deskripsi Mata Kuliah', 'Rencana Pembelajaran', 'EVALUASI PELAKSANAAN MATA KULIAH PADA PENYELENGGARAAN SEBELUMNYA', 'Daftar Revisi RPS',
    'DISETUJUI/DITETAPKAN OLEH DEKAN', 'Adi, S.T., M.T.', 'NIP 123', 'Ujian Tengah Semester (UTS)', 'Ujian Akhir Semester (UAS)', 'HOTS = 60%',
    'belum pernah diselenggarakan', 'Belum ada revisi', 'T=2', 'P=1', '18 November 2026']) assert.ok(x.includes(t), t);
  assert.equal((x.match(/<w:tbl>/g) || []).length, 13);   // 7 tabel formulir + 5 tabel lampiran rekap (termasuk butir 18) + 1 rubrik (Tugas 1)
  for (const t of ['Lampiran: Rekapitulasi Beban Belajar, Bentuk Pembelajaran, dan Penilaian', '100′ PB + 120′ PT + 120′ KM', '170′ kegiatan',
    'Case Method', 'Laporan analisis konsolidasi', 'Asesmen non-tes']) assert.ok(x.includes(t), t);
  assert.equal((x.match(/<w:tr>|<w:tr /g) || []).length, (x.match(/<\/w:tr>/g) || []).length);
  assert.equal(tanggalPanjang('2026-02-01'), '1 Februari 2026');
});

test('penyusun MK (112): koordinator MK dan pengampu kelas semester terakhir; pengembang harus salah satunya', () => {
  const dosen = [{ id: 'a', nidn: '001', email: 'a@u.id' }, { id: 'b', nidn: '002', email: 'b@u.id' }, { id: 'c', nidn: '003', email: 'c@u.id' }];
  const kelas = [{ tahun_akademik: '2025/2026', semester: 'Genap', kode_mk: '13301', dosen_email: 'c@u.id' },
                 { tahun_akademik: '2026/2027', semester: 'Ganjil', kode_mk: '13301', dosen_email: 'B@u.id' },
                 { tahun_akademik: '2026/2027', semester: 'Ganjil', kode_mk: '99999', dosen_email: 'c@u.id' }];
  assert.deepEqual(R.penyusunMK({ kode: '13301', pengampu: ['001'] }, dosen, kelas).map(d => d.id), ['a', 'b']);
  const r = rpsLengkap(); r.pengembang = 'c';
  assert.ok(R.periksaRps(ctx(r, { penyusun: [{ id: 'a' }, { id: 'b' }] })).some(t => /pengembang harus koordinator MK/.test(t.pesan)));
  r.pengembang = 'a';
  assert.deepEqual(R.periksaRps(ctx(r, { penyusun: [{ id: 'a' }] })), []);
});

test('daftar revisi (112): pengesahan pertama bukan revisi; berikutnya satu baris per pengesahan', () => {
  const log = [
    { aksi: 'ajukan', oleh_nama: 'Adi', catatan: null, waktu: '2026-11-18T01:00:00Z' },
    { aksi: 'kembalikan', oleh_nama: 'Budi', catatan: 'Lengkapi', waktu: '2026-11-18T02:00:00Z' },
    { aksi: 'ajukan', oleh_nama: 'Adi', catatan: null, waktu: '2026-11-18T03:00:00Z' },
    { aksi: 'sahkan', oleh_nama: 'Budi', catatan: null, waktu: '2026-11-19T01:00:00Z' },
    { aksi: 'ajukan', oleh_nama: 'Adi', catatan: 'Pustaka dimutakhirkan', waktu: '2027-02-01T01:00:00Z' },
    { aksi: 'sahkan', oleh_nama: 'Budi', catatan: 'Baik', waktu: '2027-02-03T01:00:00Z' }];
  assert.deepEqual(R.revisiDariLog([]), []);
  assert.deepEqual(R.revisiDariLog(log.slice(0, 4)), []);
  assert.deepEqual(R.revisiDariLog(log), [{ tanggal: '2027-02-01', pengusul: 'Adi', deskripsi: 'Pustaka dimutakhirkan', validasi: '2027-02-03', catatan: 'Budi: Baik' }]);
  const x = dokumenRps(R.modelRps({ ...ctx(rpsLengkap()), revisi: R.revisiDariLog(log) }));
  assert.ok(x.includes('Pustaka dimutakhirkan') && x.includes('3 Februari 2027') && !x.includes('Belum ada revisi'));
});

test('lampiran rekap (pemilik 2026-11-19): beban belajar per bentuk, rencana pekanan, komposisi penilaian', () => {
  const B = R.bebanBelajar({ t: 2, p: 1, pl: 0, s: 0 });
  assert.deepEqual(B.baris.map(r => [r.bentuk, r.sks, r.menit, r.pb, r.pt, r.km, r.kegiatan, r.jam]), [
    ['Kuliah/Responsi/Tutorial', 2, '100′ PB + 120′ PT + 120′ KM', 26.47, 31.76, 31.76, 0, 90],
    ['Praktikum', 1, '170′ kegiatan', 0, 0, 0, 45, 45], ['Praktik lapangan', 0, '-', 0, 0, 0, 0, 0], ['Simulasi', 0, '-', 0, 0, 0, 0, 0]]);
  assert.deepEqual(B.jumlah, { sks: 3, pb: 26.47, pt: 31.76, km: 31.76, kegiatan: 45, jam: 135 });
  assert.equal(R.ringkasPekan([10, 1, 2, 3, 5, 9, 3]), '1-3, 5, 9-10');
  const X = R.rekapRps(ctx(rpsLengkap()));
  assert.deepEqual(X.bentuk.map(b => [b.label, b.pekan, b.jumlah]), [['Kuliah', '1-7, 9-15', 14], ['Praktikum', '5-7', 3]]);
  assert.deepEqual(X.scl.map(b => [b.label, b.pekan, b.jumlah]), [['Case Method', '9-10', 2]]);
  assert.deepEqual(X.ujian, [{ pekan: '8', label: 'UTS' }, { pekan: '16', label: 'UAS' }]);
  assert.deepEqual(X.penugasan, [{ pekan: '3', penugasan: '', sumatif: 'Kuis 1' }, { pekan: '12', penugasan: 'Laporan analisis konsolidasi', sumatif: 'Tugas 1' }]);
  assert.deepEqual(X.penilaian, { jenis: [{ jenis: 'kuis', label: 'Kuis', persen: 20 }, { jenis: 'tugas', label: 'Tugas', persen: 30 },
    { jenis: 'uts', label: 'UTS', persen: 20 }, { jenis: 'uas', label: 'UAS', persen: 30 }], hots: 60, nontes: 30, total: 100 });
  // Penugasan (tugas besar/proyek) tanpa sks P/PL/S: saran butir 18; dengan P=1 tidak ada saran.
  const pen = /Penugasan \(tugas besar\/proyek\) dicentang/;
  const r3 = rpsLengkap(); r3.pekan[0].bentuk_pb = ['kuliah', 'penugasan'];
  assert.ok(!R.periksaRps(ctx(r3)).some(t => pen.test(t.pesan)));
  r3.identitas.sks = { t: 3, p: 0, pl: 0, s: 0 };
  assert.deepEqual(R.periksaRps(ctx(r3)).filter(t => pen.test(t.pesan)).map(t => [t.bagian, t.tingkat]), [['D', 'saran']]);
  const r = rpsLengkap(); r.pekan[0].bentuk_pb = [];
  assert.ok(R.periksaRps(ctx(r)).some(t => /Pekan 1: centang bentuk pembelajaran/.test(t.pesan)));
});

test('integrasi dari karya tersimpan dan butir 18 (pemilik 2026-11-19)', () => {
  const I = { ada: true, teks: 'Data lapangan dipakai di tugas besar.', karya: [
    { id: 1, kategori: 'penelitian', judul: 'Analisis Konsolidasi Tanah Lunak', tahun: 2025, pelaksana: 'Adi dkk.', bentuk: 'studi_kasus', ket: 'Sub-CPMK 2' },
    { id: 2, kategori: 'pkm', judul: 'Pelatihan Uji Tanah', tahun: 2024, pelaksana: 'Budi', bentuk: '', ket: '' }] };
  assert.equal(R.teksIntegrasi(I), 'Penelitian "Analisis Konsolidasi Tanah Lunak" (Adi dkk., 2025), sebagai studi kasus pada Sub-CPMK 2.\n'
    + 'PkM "Pelatihan Uji Tanah" (Budi, 2024).\nData lapangan dipakai di tugas besar.');
  const r = rpsLengkap(); r.integrasi = { ada: true, teks: '', karya: [] };
  assert.ok(R.periksaRps(ctx(r)).some(t => /pilih penelitian\/PkM yang sudah tersimpan/.test(t.pesan)));
  assert.equal(R.modelRps(ctx({ ...rpsLengkap(), integrasi: I })).integrasi_teks.split('\n').length, 3);
  // Butir 18: JP = sks praktikum/praktik (P+PL+S) x 50, JB = sks x 50; PT di dalam sks kuliah tidak dihitung.
  assert.deepEqual(R.butir18({ t: 2, p: 1, pl: 0, s: 0 }), { sks_praktik: 1, sks: 3, jp_menit: 50, jb_menit: 150, persen: 33.33 });
  assert.deepEqual(R.butir18({ t: 3 }), { sks_praktik: 0, sks: 3, jp_menit: 0, jb_menit: 150, persen: 0 });
  // Sebaran sks RPS harus sama dengan data MK (dipakai Tabel 3.a.1 LKPS).
  const beda = R.periksaRps(ctx(rpsLengkap(), { mk: { ...mk, sks_kuliah: 3, sks_praktikum: 0 } }));
  assert.ok(beda.some(t => t.tingkat === 'saran' && /berbeda dengan data MK/.test(t.pesan)));
  assert.ok(!R.periksaRps(ctx(rpsLengkap())).some(t => /berbeda dengan data MK/.test(t.pesan)));
});

test('keselarasan Sub-CPMK dengan rencana pekanan (pemilik 2026-11-19)', () => {
  const pesan = r => R.periksaRps(ctx(r)).filter(t => t.bagian === 'D').map(t => `${t.tingkat}: ${t.pesan}`);
  assert.ok(!pesan(rpsLengkap()).some(p => /belum dijadwalkan di pekan|tidak memuat/.test(p)));
  // S2 tidak dipilih di pekan mana pun -> galat.
  const a = rpsLengkap(); a.pekan = a.pekan.map(p => (p.jenis === 'kuliah' ? { ...p, sub: ['S1'] } : p));
  assert.ok(pesan(a).includes('galat: S2 belum dijadwalkan di pekan mana pun; pilih di rencana pekanan.'));
  // Kuis 1 (menilai S1) dijadwalkan di pekan 12 yang hanya memuat S2 -> saran.
  const b = rpsLengkap(); b.pekan = b.pekan.map(p => (p.jenis !== 'kuliah' ? p : { ...p, asesmen: p.pekan === '12' ? ['Tugas 1', 'Kuis 1'] : [] }));
  assert.ok(pesan(b).includes('saran: S1 dinilai lewat Kuis 1, tetapi Kuis 1 dijadwalkan di pekan yang tidak memuat S1.'));
});

test('perubahan dibanding versi disahkan (pemilik 2026-11-19)', () => {
  const a = rpsLengkap(), b = JSON.parse(JSON.stringify(a));
  assert.deepEqual(R.bedaRps(a, b, struktur(), struktur()), []);
  b.tujuan = '1. A\n2. B baru\n3. C'; b.identitas.tanggal = '2027-01-01';
  b.pekan = b.pekan.map(p => (p.pekan === '3' ? { ...p, materi: 'Klasifikasi USCS', asesmen: [] } : p));
  const sb = struktur(); sb.bobot.S1['Kuis 1'] = 25; sb.bobot.S1.UTS = 15; sb.sub[1].rumusan = 'Mahasiswa mampu mengevaluasi konsolidasi (C5)';
  const xs = R.bedaRps(a, b, struktur(), sb);
  assert.deepEqual(xs.map(x => [x.bagian, x.label]), [['B', 'S2'], ['B', 'Bobot S1'], ['C', 'Tujuan'], ['D', 'Pekan 3 · Asesmen sumatif'], ['D', 'Pekan 3 · Materi']]);
  assert.deepEqual(xs.find(x => x.label === 'Bobot S1'), { bagian: 'B', label: 'Bobot S1', lama: 'Kuis 1 20, UTS 20', baru: 'Kuis 1 25, UTS 15' });
  assert.equal(xs.find(x => x.label === 'Pekan 3 · Asesmen sumatif').baru, '');
  assert.equal(R.teksNilai({ t: 2, p: 1, pl: 0, s: '' }), 'T=2 P=1 PL=0 S=0');
  assert.equal(R.teksNilai([{ kode: 'DAS', teks: 'Das (2019).' }]), 'DAS: Das (2019).');
});

test('salin dari RPS lain: bagian C dan pekan; identitas, pengampu, evaluasi tetap', () => {
  const sumber = rpsLengkap(); sumber.pengampu = 'Orang lain'; sumber.evaluasi = { baru: false, kode: 'X1' };
  sumber.pekan = sumber.pekan.map(p => (p.jenis === 'kuliah' ? { ...p, sub: ['S1', 'S9'], asesmen: ['Kuis 1', 'Proyek X'] } : p));
  const tujuan = R.rpsKosong({ kode: '41321', sks: 3, semester: 5 }); tujuan.pengampu = 'Saya';
  const h = R.salinRps(tujuan, sumber, struktur());
  assert.equal(h.tujuan, sumber.tujuan);
  assert.deepEqual(h.pustaka, sumber.pustaka);
  assert.equal(h.pengampu, 'Saya');
  assert.deepEqual(h.evaluasi, tujuan.evaluasi);
  assert.deepEqual(h.identitas, tujuan.identitas);
  assert.deepEqual(h.pekan.find(p => p.jenis === 'kuliah').sub, ['S1']);
  assert.deepEqual(h.pekan.find(p => p.jenis === 'kuliah').asesmen, ['Kuis 1']);
  h.pustaka.push({ kode: 'Z', teks: 'z' });
  assert.equal(sumber.pustaka.length, 1);   // salinan, bukan rujukan
});

test('ranah A/P hanya dinilai kuis/UTS/UAS -> saran (Panduan)', () => {
  const S = struktur(); S.sub[0].rumusan = 'Mahasiswa mampu menunjukkan kerja sama dalam praktikum (A3, P2)';
  const ps = R.periksaRps(ctx(rpsLengkap(), { struktur: S })).filter(t => t.bagian === 'B').map(t => `${t.tingkat}: ${t.pesan}`);
  assert.ok(ps.some(p => /^saran: S1 memuat ranah A \(sikap\) dan P \(keterampilan\), tetapi hanya dinilai lewat kuis\/UTS\/UAS/.test(p)), ps.join('\n'));
  assert.ok(!R.periksaRps(ctx(rpsLengkap())).some(t => /memuat ranah/.test(t.pesan)));
});

test('rubrik penilaian: saran, model Word, rubrikRps', () => {
  const pesan = r => R.periksaRps(ctx(r)).map(t => t.pesan).filter(p => /^Rubrik/.test(p));
  const r0 = rpsLengkap(); r0.rubrik = {};
  assert.deepEqual(pesan(r0), ['Rubrik Tugas 1 belum disusun (bagian Rubrik penilaian); Panduan meminta rubrik untuk asesmen non-tes.']);
  assert.deepEqual(pesan(rpsLengkap()), []);
  const r = rpsLengkap(); r.rubrik = { 'Tugas 1': R.rubrikKosong() };
  r.rubrik['Tugas 1'].kriteria = [{ nama: 'Analisis', bobot: '60', deskriptor: ['a', 'b', 'c', 'd'] }, { nama: 'Laporan', bobot: '30', deskriptor: ['a', '', 'c', 'd'] }];
  assert.deepEqual(pesan(r), ['Rubrik Tugas 1: lengkapi deskriptor tiap tingkat.', 'Rubrik Tugas 1: total bobot kriteria 90%, seharusnya 100%.']);
  r.rubrik['Tugas 1'].kriteria[1] = { nama: 'Laporan', bobot: '40', deskriptor: ['a', 'b', 'c', 'd'] };
  assert.deepEqual(pesan(r), []);
  const M = R.modelRps(ctx(r));
  assert.deepEqual(M.rubrik.map(x => [x.asesmen, x.tingkat.length, x.kriteria.map(k => k.nama)]), [['Tugas 1', 4, ['Analisis', 'Laporan']]]);
  assert.deepEqual([...R.rubrikRps(r)], ['Tugas 1']);
  assert.deepEqual([...R.rubrikRps({ rubrik: { X: { kriteria: [{ nama: '' }] } } })], []);
  assert.ok(R.bedaRps(R.rapikanRps(r0, mk, {}), r).some(x => x.bagian === 'Rubrik'));
});

test('susunan daftar MK: per semester Ganjil/Genap, lalu MK pilihan menurut semester RPS (pemilik 2026-11-19)', async () => {
  const { susunanMK, paritas, jenisMK } = await import('../../site/rps.js');
  assert.equal(paritas('1'), 'Ganjil'); assert.equal(paritas('4'), 'Genap'); assert.equal(paritas('genap'), 'Genap'); assert.equal(paritas(''), '');
  assert.equal(jenisMK({ kode: '01207' }), 'MKU'); assert.equal(jenisMK({ kode: '41302' }), 'MKPS');
  assert.equal(jenisMK({ kode: '41503', sifat: 'wajib' }), ''); assert.equal(jenisMK({ kode: '41503', sifat: 'pilihan' }), 'MKP');
  const g = susunanMK([{ kode: '41303', semester: '1', sks: '1', sifat: 'wajib' }, { kode: '41302', semester: 1, sks: '3', sifat: 'wajib' },
    { kode: '41320', semester: '4', sks: '2', sifat: 'wajib' }, { kode: '41415', semester: null, sks: '3', sifat: 'pilihan' },
    { kode: '41408', sks: '3', sifat: 'pilihan' }, { kode: '49999', sifat: 'wajib' }], { 41415: 'Ganjil' });
  assert.deepEqual(JSON.parse(JSON.stringify(g.map(x => [x.judul, x.paritas, x.xs.map(m => m.kode), x.sks]))), [
    ['Semester 1', 'Ganjil', ['41302', '41303'], 4], ['Semester 4', 'Genap', ['41320'], 2],
    ['MK pilihan · Ganjil', 'Ganjil', ['41415'], 3], ['MK pilihan · semester belum ditetapkan', '', ['41408'], 3],
    ['Tanpa semester', '', ['49999'], 0]]);
});

test('dua kolom Ganjil/Genap dan saringan daftar MK (pemilik 2026-11-19)', async () => {
  const { susunanMK, bagiParitas, saringMK } = await import('../../site/rps.js');
  const mk = [{ kode: '41301', nama: 'Kalkulus 1', semester: '1', sifat: 'wajib', sks: 3 }, { kode: '01209', nama: 'Literasi Digital', semester: '2', sifat: 'wajib', sks: 2 },
    { kode: '41415', nama: 'Hidrologi Lanjut', sifat: 'pilihan', sks: 3 }, { kode: '41408', nama: 'Rekayasa Fondasi Lanjut', sifat: 'pilihan', sks: 3 }];
  const b = bagiParitas(susunanMK(mk, { 41415: 'Genap' }));
  assert.deepEqual(b.ganjil.map(g => g.judul), ['Semester 1']);
  assert.deepEqual(b.genap.map(g => g.judul), ['Semester 2', 'MK pilihan · Genap']);
  assert.deepEqual(b.lain.map(g => g.xs.map(m => m.kode)), [['41408']]);
  assert.deepEqual(saringMK(mk, { jenis: 'MKU' }).map(m => m.kode), ['01209']);
  assert.deepEqual(saringMK(mk, { sifat: 'pilihan', cari: 'fondasi' }).map(m => m.kode), ['41408']);
  assert.deepEqual(saringMK(mk, { status: 'belum' }, { status: m => (m.kode === '41301' ? 'draf' : 'belum') }).map(m => m.kode), ['01209', '41415', '41408']);
  assert.deepEqual(saringMK(mk, { cari: 'adi' }, { teksCari: m => (m.kode === '41415' ? 'Adi Contoh' : '') }).map(m => m.kode), ['41415']);
});

test('ringkasan jumlah MK dan sks per semester (pemilik 2026-11-19)', async () => {
  const { ringkasSemester, htmlRingkasSemester } = await import('../../site/rps.js');
  const r = ringkasSemester([{ semester: '1', sks: 3 }, { semester: 1, sks: 1, sks_praktikum: 1 }, { semester: '2', sks: 2 },
    { sifat: 'pilihan', sks: 3 }, { sifat: 'wajib', sks: 2 }]);
  assert.deepEqual(r.kolom.map(c => [c.label, c.mk, c.sks, c.sksP]), [['Smt 1', 2, 4, 1], ['Smt 2', 1, 2, 0], ['Pilihan', 1, 3, 0], ['Tanpa smt', 1, 2, 0]]);
  assert.deepEqual([r.ganjil, r.genap, r.total], [{ mk: 2, sks: 4 }, { mk: 1, sks: 2 }, { mk: 5, sks: 11 }]);
  assert.match(htmlRingkasSemester(r), /<th>Smt 1<\/th>.*<b>11<\/b>/s);
});

test('saringan banyak pilihan: semester, jenis, status; tombol dan hapus saringan (pemilik 2026-11-19)', async () => {
  const { saringMK, ubahSaringan, htmlSaringan, kunciSemester } = await import('../../site/rps.js');
  const mk = [{ kode: '41301', nama: 'Kalkulus 1', semester: '1', sifat: 'wajib' }, { kode: '01209', nama: 'Literasi Digital', semester: '2', sifat: 'wajib' },
    { kode: '41320', nama: 'Mekanika Bahan', semester: 3, sifat: 'wajib' }, { kode: '41415', nama: 'Hidrologi Lanjut', sifat: 'pilihan' }];
  assert.equal(kunciSemester(mk[3]), 'pilihan');
  assert.deepEqual(saringMK(mk, { semester: ['1', '3'] }).map(m => m.kode), ['41301', '41320']);
  assert.deepEqual(saringMK(mk, { semester: ['pilihan', '2'], jenis: ['MKU', 'MKP'] }).map(m => m.kode), ['01209', '41415']);
  assert.deepEqual(saringMK(mk, { semester: [], jenis: [] }).length, 4);
  const grup = [{ kunci: 'semester', label: 'Semester', opsi: [['1', '1'], ['3', '3']] }, { kunci: 'jenis', label: 'Jenis', opsi: [['MKU', 'MKU']] }];
  const f = { semester: [], jenis: [] };
  ubahSaringan(f, 'semester', '1', grup); ubahSaringan(f, 'semester', '3', grup); ubahSaringan(f, 'jenis', 'MKU', grup); ubahSaringan(f, 'semester', '1', grup);
  assert.deepEqual(f, { semester: ['3'], jenis: ['MKU'] });
  const h = htmlSaringan(f, grup);
  assert.match(h, /data-nilai="3"\s+aria-pressed="true"/); assert.match(h, /Hapus saringan/);
  ubahSaringan(f, null, null, grup);
  assert.deepEqual(f, { semester: [], jenis: [] });
  assert.doesNotMatch(htmlSaringan(f, grup), /Hapus saringan/);
});
