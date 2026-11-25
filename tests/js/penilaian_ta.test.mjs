// Penilaian seminar/sidang TA dan berita acara (pemilik 2026-11-25; site/penilaian-ta.js, instal-lengkap.sql).
import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { RUBRIK_AWAL, TINGKAT_AWAL, totalNilai, cekNilai, rekapNilai, cekRubrik, bobotBagian, tingkatDari, labelTingkat, angka, htmlBA }
  from '../../site/penilaian-ta.js';

// Patch sumber di cv-data. Paket templat: make_package.py menulis rujukan patch menjadi instal-lengkap.sql, yang memuat
// draf sebagai INSERT tanpa blok ini, jadi uji dilewati bila bloknya tidak ada.
const SQL = new URL('../../supabase/instal-lengkap.sql', import.meta.url);
const BLOK = (existsSync(SQL) ? readFileSync(SQL, 'utf8') : '').match(/\$rubrik_awal\$([\s\S]*?)\$rubrik_awal\$/);

test('draf awal di JS sama persis dengan blok rubrik_awal di SQL', { skip: !BLOK && 'blok rubrik_awal tidak ada (paket templat)' }, () => {
  const m = BLOK;
  assert.deepEqual(JSON.parse(m[1]), RUBRIK_AWAL);
});

test('draf awal: bobot pemilik (seminar 40/60/0, sidang 40/10/50), komponen sah', () => {
  assert.deepEqual(Object.keys(RUBRIK_AWAL), ['seminar_proposal', 'seminar_kemajuan', 'sidang_akhir']);
  assert.deepEqual(bobotBagian(RUBRIK_AWAL.seminar_proposal), { penguji: 40, bimbingan: 0, pembimbing: 60 });
  assert.deepEqual(bobotBagian(RUBRIK_AWAL.seminar_kemajuan), { penguji: 40, bimbingan: 0, pembimbing: 60 });
  assert.deepEqual(bobotBagian(RUBRIK_AWAL.sidang_akhir), { penguji: 40, bimbingan: 50, pembimbing: 10 });
  assert.equal(RUBRIK_AWAL.sidang_akhir.komponen_bimbingan.length, 4);
  for (const r of Object.values(RUBRIK_AWAL)) {
    assert.equal(r.komponen.length, 5);
    assert.deepEqual(cekRubrik({ ...r, batas_lulus: 55, tingkat: TINGKAT_AWAL }), []);
  }
});

const K = RUBRIK_AWAL.seminar_proposal.komponen;                        // 20, 20, 30, 15, 15
const semua = v => Object.fromEntries(K.map(k => [k.kode, v]));

test('total satu penilai: rata-rata berbobot, 2 desimal; isian kurang/lebih ditolak', () => {
  assert.equal(totalNilai(K, semua(80)), 80);
  assert.equal(totalNilai(K, { masalah: 90, pustaka: 80, metode: 70, penulisan: 60, presentasi: 100 }), 79);   // 18+16+21+9+15
  assert.equal(totalNilai(K, { ...semua(80), metode: 77.777 }), 79.33);
  assert.equal(totalNilai(K, { masalah: 80 }), null);
  assert.match(cekNilai(K, { masalah: 80 }), /Isi nilai "Tinjauan pustaka"/);
  assert.match(cekNilai(K, semua(120)), /harus 0–100/);
  assert.match(cekNilai(K, { ...semua(80), asing: 1 }), /tidak ada di form/);
});

const panel = [{ peran: 'pembimbing', nidn: '002', nama: 'Pembimbing Satu' }, { peran: 'penguji', nidn: '003', nama: 'Penguji Dua' }];
const seminar = { bobot_penguji: 40, bobot_bimbingan: 0, batas_lulus: 55 };
const sidang = { bobot_penguji: 40, bobot_bimbingan: 50, batas_lulus: 55 };

test('rekap seminar: penguji 40, pembimbing 60, penguji luar ikut rata-rata penguji; sama dengan uji PGlite (76 dan 34)', () => {
  const nilai = [{ nidn: '003', total: 80 }, { nidn: null, nama: 'Ir. Luar', total: 90 }, { nidn: '002', total: 70 }];
  assert.deepEqual(rekapNilai({ rubrik: seminar, panel, nilai, penguji_luar: 'Ir. Luar' }),
    { rataPenguji: 85, rataPembimbing: 70, rataBimbingan: null, akhir: 76, kurang: [], saran: 'lulus' });
  const r = rekapNilai({ rubrik: seminar, panel, nilai: nilai.map(n => n.nidn === '002' ? { ...n, total: 0 } : n), penguji_luar: 'Ir. Luar' });
  assert.equal(r.akhir, 34); assert.equal(r.saran, 'mengulang');
});

test('rekap sidang: 40 penguji + 10 pembimbing saat sidang + 50 proses bimbingan; dua pembimbing dirata-rata (84)', () => {
  const p2 = [...panel, { peran: 'pembimbing', nidn: '004', nama: 'Pembimbing Dua' }];
  const nilai = [{ nidn: '003', total: 80 }, { nidn: '002', total: 70 }, { nidn: '004', total: 70 },
                 { bagian: 'bimbingan', nidn: '002', total: 95 }, { bagian: 'bimbingan', nidn: '004', total: 85 }];
  const r = rekapNilai({ rubrik: sidang, panel: p2, nilai });
  assert.deepEqual([r.rataPenguji, r.rataPembimbing, r.rataBimbingan, r.akhir], [80, 70, 90, 84]);   // 32 + 7 + 45
  assert.deepEqual(r.kurang, []);
  const belum = rekapNilai({ rubrik: sidang, panel: p2, nilai: nilai.slice(0, 4) });
  assert.deepEqual(belum.kurang, [{ peran: 'pembimbing', bagian: 'bimbingan', nidn: '004', nama: 'Pembimbing Dua' }]);
  // Nilai proses bimbingan dari penguji tidak dihitung.
  assert.equal(rekapNilai({ rubrik: sidang, panel, nilai: [{ bagian: 'bimbingan', nidn: '003', total: 10 }] }).rataBimbingan, null);
});

test('rekap: yang belum menilai, bagian yang belum ada nilainya, dan nilai dari luar panel tidak dihitung', () => {
  const r = rekapNilai({ rubrik: seminar, panel, nilai: [{ nidn: '003', total: 80 }], penguji_luar: 'Ir. Luar' });
  assert.deepEqual(r.kurang.map(k => k.nama), ['Pembimbing Satu', 'Ir. Luar']);
  assert.equal(r.akhir, 80);                                             // hanya bagian penguji yang ada nilainya
  const bekas = rekapNilai({ rubrik: seminar, panel, nilai: [{ nidn: '009', total: 10 }, { nidn: '002', total: 60 }] });
  assert.equal(bekas.rataPenguji, null); assert.equal(bekas.akhir, 60);
  assert.equal(rekapNilai({ rubrik: seminar, panel, nilai: [] }).akhir, null);
  assert.equal(rekapNilai({ rubrik: { bobot_penguji: 50, batas_lulus: 55 }, panel, nilai: [{ nidn: '003', total: 55 }, { nidn: '002', total: 54.98 }] }).saran, 'mengulang');   // 54,99
});

test('pemeriksa form: jumlah bobot, kode, uraian, bobot bagian, batas tingkat', () => {
  const k = [{ kode: 'a', label: 'Is', bobot: 50, uraian: ['', '', '', ''] }, { kode: 'a', label: 'Isi naskah', bobot: 40, uraian: ['', ''] }];
  const g = cekRubrik({ komponen: k, bobot_penguji: 60, batas_lulus: 55, tingkat: [85, 70, 55, 0] });
  assert.ok(g.some(x => /dipakai dua kali/.test(x)));
  assert.ok(g.some(x => /3–200 huruf/.test(x)));
  assert.ok(g.some(x => /harus 4 tingkat/.test(x)));
  assert.ok(g.some(x => /harus 100 \(sekarang 90\)/.test(x)));
  assert.ok(cekRubrik({ komponen: K, bobot_penguji: 120, batas_lulus: 55 }).some(x => /Bobot penguji/.test(x)));
  assert.ok(cekRubrik({ komponen: K, bobot_penguji: 60, bobot_bimbingan: 50, komponen_bimbingan: K, batas_lulus: 55 }).some(x => /paling besar 100/.test(x)));
  assert.ok(cekRubrik({ komponen: K, bobot_penguji: 40, bobot_bimbingan: 50, batas_lulus: 55 }).some(x => /^Proses bimbingan: Form penilaian berisi/.test(x)));
  assert.ok(cekRubrik({ komponen: K, bobot_penguji: 60, batas_lulus: 55, tingkat: [70, 85, 55, 0] }).some(x => /menurun/.test(x)));
});

test('tingkat rubrik dan labelnya', () => {
  assert.deepEqual(labelTingkat(), ['≥ 85', '70–84', '55–69', '< 55']);
  assert.deepEqual([90, 85, 84.99, 70, 55, 54.9, 0].map(v => tingkatDari(v)), [0, 0, 1, 1, 2, 3, 3]);
  assert.equal(tingkatDari(null), null);
  assert.equal(angka(78.5), '78,50'); assert.equal(angka(null), '–');
});

test('berita acara: identitas, nilai per komponen, hasil, DRAF sebelum ditetapkan, isi di-escape', () => {
  const x = { jadwal: { tahap: 'seminar_proposal', nama_mahasiswa: 'Ani <b>', nim: '104', judul: 'Judul & uji', tanggal: '2026-11-24',
      penguji_luar: null, hasil: null, ba_ditetapkan: null },
    rubrik: { versi: 1, komponen: K, ...seminar }, panel,
    nilai: [{ nidn: '002', nama: 'Pembimbing Satu', peran: 'pembimbing', nilai: semua(70), total: 70 },
            { nidn: '003', nama: 'Penguji Dua', peran: 'penguji', nilai: semua(80), total: 80, catatan: 'Perbaiki <metode>' }] };
  const h = htmlBA(x, { prodi: 'Teknik Contoh', institusi: 'Universitas Contoh' });
  assert.match(h, /BERITA ACARA SEMINAR PROPOSAL TUGAS AKHIR/);
  assert.match(h, /Ani &lt;b&gt;/); assert.match(h, /Judul &amp; uji/); assert.match(h, /Perbaiki &lt;metode&gt;/);
  assert.match(h, /class="draf"/);
  assert.match(h, /<th>Nilai akhir<\/th><th class="n">74,00<\/th>/);         // 80×0,4 + 70×0,6
  assert.doesNotMatch(h, /proses bimbingan/);
  assert.match(h, /Program Studi Teknik Contoh · Universitas Contoh/);
  const tetap = htmlBA({ ...x, jadwal: { ...x.jadwal, hasil: 'lulus_revisi', batas_revisi: '2026-12-10', ba_ditetapkan: '2026-11-24T03:00:00Z',
    ba_oleh: 'Koor', nilai_akhir: 74, catatan_revisi: 'Bab 3' } });
  assert.doesNotMatch(tetap, /class="draf"/);
  assert.match(tetap, /Lulus dengan revisi/); assert.match(tetap, /Tenggat revisi/); assert.match(tetap, /oleh Koor/);
});

test('berita acara sidang: tabel proses bimbingan dan tiga bobot', () => {
  const S = RUBRIK_AWAL.sidang_akhir, isi = (ks, v) => Object.fromEntries(ks.map(k => [k.kode, v]));
  const h = htmlBA({ jadwal: { tahap: 'sidang_akhir', nama_mahasiswa: 'Budi', tanggal: '2026-11-24', ba_ditetapkan: null },
    rubrik: { versi: 1, ...S, batas_lulus: 55 }, panel,
    nilai: [{ nidn: '003', nama: 'Penguji Dua', peran: 'penguji', nilai: isi(S.komponen, 80), total: 80 },
            { nidn: '002', nama: 'Pembimbing Satu', peran: 'pembimbing', nilai: isi(S.komponen, 70), total: 70 },
            { bagian: 'bimbingan', nidn: '002', nama: 'Pembimbing Satu', peran: 'pembimbing', nilai: isi(S.komponen_bimbingan, 90), total: 90 }] });
  assert.match(h, /BERITA ACARA SIDANG AKHIR TUGAS AKHIR/);
  assert.match(h, /<h2>Nilai proses bimbingan<\/h2>/);
  assert.match(h, /Rata-rata penguji \(bobot 40 %\)/);
  assert.match(h, /Rata-rata pembimbing saat sidang \(bobot 10 %\)/);
  assert.match(h, /Rata-rata proses bimbingan \(bobot 50 %\)<\/td><td class="n">90,00/);
  assert.match(h, /<th>Nilai akhir<\/th><th class="n">84,00<\/th>/);
});

test('Tugas saya: isi nilai untuk penilai, tetapkan untuk koordinator; tenggat = hari seminar', async () => {
  const { tugasSaya } = await import('../../site/tugas-saya.js');
  const nilaiTa = [{ jadwal_id: 7, tahap: 'sidang_akhir', nama_mahasiswa: 'M1', tanggal: '2026-12-08', tugas: 'nilai' },
                   { jadwal_id: 8, tahap: 'seminar_proposal', nama_mahasiswa: 'M2', tanggal: '2026-12-10', tugas: 'tetapkan' }];
  const t = tugasSaya({ saya: { id: 'x', nidn: '001', peran: 'dosen', dtps: false }, nilaiTa }, new Date('2026-12-10T05:00:00Z'))
    .filter(x => x.jenis === 'nilai_ta');
  assert.deepEqual(t.map(x => [x.judul, x.href, x.hari, x.tingkat]), [
    ['Isi nilai sidang akhir M1', 'penilaian-ta.html#j=7', -2, 'lewat'],
    ['Tetapkan berita acara seminar proposal M2', 'penilaian-ta.html#j=8', 0, 'dekat']]);
});

test('lembar Excel nilai untuk SIUP: hanya berita acara ditetapkan, urut tanggal, nilai angka, penguji luar ikut', async () => {
  const { lembarSiup } = await import('../../site/penilaian-ta.js');
  const L = lembarSiup([
    { tanggal: '2026-11-20', tahap: 'sidang_akhir', nim: '2', nama_mahasiswa: 'Budi', judul: 'J2', nilai_akhir: '84.00', hasil: 'lulus',
      pembimbing: ['001'], penguji: ['002'], penguji_luar: 'Ir. Luar', ba_ditetapkan: '2026-11-21T03:00:00Z', siup_diunggah: null },
    { tanggal: '2026-11-10', tahap: 'seminar_proposal', nim: '1', nama_mahasiswa: 'Ani', judul: 'J1', nilai_akhir: 76, hasil: 'lulus_revisi',
      pembimbing: ['001'], penguji: [], ba_ditetapkan: '2026-11-10T05:00:00Z', siup_diunggah: '2026-11-12T01:00:00Z' },
    { tanggal: '2026-11-15', tahap: 'seminar_kemajuan', nim: '3', nama_mahasiswa: 'Cici', ba_ditetapkan: null }], { '001': 'Adi', '002': 'Dewi' });
  assert.deepEqual(L[0], ['No', 'NIM', 'Nama', 'Tahap', 'Tanggal', 'Nilai akhir', 'Hasil', 'Judul', 'Pembimbing', 'Penguji', 'Berita acara ditetapkan', 'Diunggah ke SIUP']);
  assert.equal(L.length, 3);
  assert.deepEqual(L[1], [1, '1', 'Ani', 'Seminar proposal', '2026-11-10', 76, 'Lulus dengan revisi', 'J1', 'Adi', '', '2026-11-10', '2026-11-12']);
  assert.deepEqual(L[2], [2, '2', 'Budi', 'Sidang akhir', '2026-11-20', 84, 'Lulus', 'J2', 'Adi', 'Dewi; Ir. Luar', '2026-11-21', 'belum']);
});

test('Tugas saya: nilai belum diunggah ke SIUP digabung jadi satu tugas', async () => {
  const { tugasSaya } = await import('../../site/tugas-saya.js');
  const nilaiTa = ['A', 'B', 'C', 'D'].map((n, i) => ({ jadwal_id: i, tahap: 'sidang_akhir', nama_mahasiswa: n, tanggal: '2026-11-01', tugas: 'siup' }));
  const t = tugasSaya({ saya: { id: 'x', nidn: '001', peran: 'admin', dtps: false }, nilaiTa }, new Date('2026-11-25T03:00:00Z')).filter(x => x.jenis === 'nilai_ta');
  assert.deepEqual(t.map(x => [x.judul, x.rinci, x.href]), [['4 nilai TA belum diunggah ke SIUP', 'A, B, C, …', 'penilaian-ta.html#nilai-siup']]);
});

test('arsip TA: identitas, ringkasan tahap, riwayat bimbingan, berita acara per halaman tanpa tanda DRAF', async () => {
  const { htmlArsipTA } = await import('../../site/penilaian-ta.js');
  const S = RUBRIK_AWAL.sidang_akhir, isi = (ks, v) => Object.fromEntries(ks.map(k => [k.kode, v]));
  const ba = { jadwal: { tahap: 'sidang_akhir', nama_mahasiswa: 'Ani', nim: '1', tanggal: '2026-11-20', hasil: 'lulus', nilai_akhir: 84,
      ba_ditetapkan: '2026-11-21T03:00:00Z', ba_oleh: 'Koor' },
    rubrik: { versi: 1, ...S, batas_lulus: 55 }, panel,
    nilai: [{ nidn: '003', nama: 'Penguji Dua', peran: 'penguji', nilai: isi(S.komponen, 80), total: 80 },
            { nidn: '002', nama: 'Pembimbing Satu', peran: 'pembimbing', nilai: isi(S.komponen, 70), total: 70 },
            { bagian: 'bimbingan', nidn: '002', nama: 'Pembimbing Satu', peran: 'pembimbing', nilai: isi(S.komponen_bimbingan, 90), total: 90 }] };
  const h = htmlArsipTA({ nim: '1', nama: 'Ani <b>', judul: 'Judul & uji', lulus: '2026-11-20', pembimbing: 'Pembimbing Satu',
    jadwal: [{ tahap: 'sidang_akhir', tanggal: '2026-11-20', status: 'selesai', hasil: 'lulus', nilai_akhir: 84, ba_ditetapkan: '2026-11-21T03:00:00Z' },
             { tahap: 'seminar_proposal', tanggal: '2026-03-01', status: 'selesai', hasil: 'lulus_revisi', revisi_selesai: '2026-03-20' },
             { tahap: 'seminar_kemajuan', tanggal: '2026-06-01', status: 'batal' }],
    rekap: [ba], bimbingan: [{ id: 2, tanggal: '2026-10-02', cara: 'daring', topik: 'Bab 4', status: 'dikonfirmasi', konfirmasi_oleh: 'Pembimbing Satu', pembimbing: 'Pembimbing Satu' },
                             { id: 1, tanggal: '2026-09-01', cara: 'tatap_muka', topik: 'Bab 1', status: 'menunggu', diajukan: '2026-09-01T00:00:00Z' }] },
    { prodi: 'Teknik Contoh', oleh: 'Koor', kini: '2026-11-25T03:00:00Z' });
  assert.match(h, /ARSIP TUGAS AKHIR/); assert.match(h, /Ani &lt;b&gt;/); assert.match(h, /Judul &amp; uji/);
  assert.ok(h.indexOf('Seminar proposal') < h.indexOf('Sidang akhir'));                       // urut tahap
  assert.doesNotMatch(h, /Seminar kemajuan<\/td>/);                                           // jadwal batal tidak masuk
  assert.match(h, /revisi selesai/);
  assert.match(h, /Riwayat bimbingan \(2\)/);
  assert.ok(h.indexOf('Bab 1') < h.indexOf('Bab 4'));                                         // bimbingan urut tanggal
  assert.match(h, /Terkonfirmasi otomatis/);                                                  // 14 hari lewat pada tanggal arsip
  assert.match(h, /class="halaman"[\s\S]*BERITA ACARA SIDANG AKHIR TUGAS AKHIR/);
  assert.doesNotMatch(h, /class="draf"/);
  assert.match(h, /84,00/); assert.match(h, /oleh Koor/);
});

test('Tugas saya: arsip TA mahasiswa lulus belum disimpan, satu tugas', async () => {
  const { tugasSaya } = await import('../../site/tugas-saya.js');
  const nilaiTa = [{ jadwal_id: 1, tahap: 'sidang_akhir', nama_mahasiswa: 'Ani', tanggal: '2026-11-20', tugas: 'arsip' }];
  const t = tugasSaya({ saya: { id: 'x', nidn: '001', peran: 'admin', dtps: false }, nilaiTa }, new Date('2026-11-25T03:00:00Z')).filter(x => x.jenis === 'nilai_ta');
  assert.deepEqual(t.map(x => [x.judul, x.href]), [['1 arsip TA mahasiswa lulus belum disimpan', 'bimbingan-ta.html#arsip-ta']]);
});

test('lembar nilai per komponen untuk SIUP: tiap penilai tiap komponen + total, proses bimbingan terpisah', async () => {
  const { lembarKomponenSiup } = await import('../../site/penilaian-ta.js');
  const S = RUBRIK_AWAL.sidang_akhir, isi = (ks, v) => Object.fromEntries(ks.map(k => [k.kode, v]));
  const L = lembarKomponenSiup([{ id: 9, tanggal: '2026-11-20', tahap: 'sidang_akhir', nim: '2', nama_mahasiswa: 'Budi', ba_ditetapkan: '2026-11-21' },
                                { id: 8, tanggal: '2026-11-01', tahap: 'sidang_akhir', nim: '3', nama_mahasiswa: 'Cici', ba_ditetapkan: null }],
    [{ jadwal_id: 9, rubrik_id: 1, bagian: 'seminar', peran: 'penguji', penilai_nama: 'Dewi', nilai: isi(S.komponen, 80), total: 80 },
     { jadwal_id: 9, rubrik_id: 1, bagian: 'bimbingan', peran: 'pembimbing', penilai_nama: 'Adi', nilai: isi(S.komponen_bimbingan, 90), total: 90 },
     { jadwal_id: 9, rubrik_id: 1, bagian: 'seminar', peran: 'pembimbing', penilai_nama: 'Adi', nilai: isi(S.komponen, 70), total: 70 },
     { jadwal_id: 8, rubrik_id: 1, bagian: 'seminar', peran: 'penguji', penilai_nama: 'X', nilai: {}, total: 1 }],
    [{ id: 1, komponen: S.komponen, komponen_bimbingan: S.komponen_bimbingan }]);
  assert.deepEqual(L[0], ['No', 'NIM', 'Nama', 'Tahap', 'Tanggal', 'Penilai', 'Peran', 'Bagian', 'Komponen', 'Bobot (%)', 'Nilai']);
  assert.equal(L.length, 1 + (5 + 1) * 2 + (4 + 1));                       // 2 penilai sidang + 1 proses bimbingan; jadwal tanpa BA tidak masuk
  assert.deepEqual(L[1], [1, '2', 'Budi', 'Sidang akhir', '2026-11-20', 'Adi', 'Pembimbing', 'Sidang akhir', 'Penguasaan materi dan dasar teori', 20, 70]);
  assert.deepEqual(L[6], [6, '2', 'Budi', 'Sidang akhir', '2026-11-20', 'Adi', 'Pembimbing', 'Sidang akhir', 'Total (rata-rata berbobot)', 100, 70]);
  assert.equal(L[7][5], 'Dewi');
  assert.deepEqual(L.at(-1).slice(5), ['Adi', 'Pembimbing', 'Proses bimbingan', 'Total (rata-rata berbobot)', 100, 90]);
});

test('lembar unggah SIUP: komponen kelas TA di SIUP (sidang akhir), nilai = rata-rata dosen peran, satu lembar per pembimbing 1', async () => {
  const { lembarSiupPeran } = await import('../../site/penilaian-ta.js');
  const R = [{ id: 1, bobot_penguji: 40, bobot_bimbingan: 50 }];
  const j = (id, tahap, nim, penguji, pembimbing, na) => ({ id, tahap, nim, nama_mahasiswa: 'M' + nim, tanggal: '2026-11-1' + id,
    ba_ditetapkan: 'x', nilai_akhir: na, rubrik_id: 1, penguji, pembimbing });
  const n = (jadwal_id, peran, penilai_nama, total, bagian = 'seminar') => ({ jadwal_id, peran, bagian, penilai_nama, total });
  const { lembar, keterangan } = lembarSiupPeran([
      j(1, 'sidang_akhir', '2', ['003', '004'], ['002'], 86), j(2, 'sidang_akhir', '1', ['003'], ['002', '005'], 78.5),
      j(3, 'seminar_proposal', '3', ['003'], ['002'], 76), j(4, 'sidang_akhir', '4', ['004'], ['005'], 80)],
    [n(1, 'penguji', 'Cici', 80), n(1, 'penguji', 'Ir. Luar', 90), n(1, 'pembimbing', 'Budi', 70), n(1, 'pembimbing', 'Budi', 90, 'bimbingan'),
     n(2, 'penguji', 'Cici', 80), n(2, 'pembimbing', 'Budi', 70), n(2, 'pembimbing', 'Eko', 80), n(2, 'pembimbing', 'Budi', 80, 'bimbingan'),
     n(2, 'pembimbing', 'Eko', 76, 'bimbingan'), n(3, 'penguji', 'Cici', 85), n(3, 'pembimbing', 'Budi', 70),
     n(4, 'penguji', 'Dewi', 80), n(4, 'pembimbing', 'Eko', 80), n(4, 'pembimbing', 'Eko', 80, 'bimbingan')],
    R, { '002': 'Budi Contoh', '005': 'Eko Contoh' });
  assert.deepEqual(lembar.map(l => [l.nama, l.baris.length - 1]), [['TA Budi Contoh', 2], ['TA Eko Contoh', 1]]);   // seminar tidak masuk
  assert.deepEqual(lembar[0].baris[0], ['No', 'NIM', 'Nama', 'Sidang (Penguji - Sidang) (40.00%)', 'Sidang (Pembimbing - Sidang) (10.00%)',
    'Bimbingan (Pembimbing - Bimbingan) (50.00%)', 'Nilai Akhir']);
  assert.deepEqual(lembar[0].baris[1], [1, '1', 'M1', 80, 75, 78, 78.5]);   // dua pembimbing: (70+80)/2, (80+76)/2
  assert.deepEqual(lembar[0].baris[2], [2, '2', 'M2', 85, 70, 90, 86]);     // dua penguji (termasuk luar): (80+90)/2
  for (const l of lembar) for (const r of l.baris.slice(1))
    assert.ok(Math.abs(r[3] * 0.4 + r[4] * 0.1 + r[5] * 0.5 - r[6]) < 0.01, `${l.nama} ${r[1]}`);   // jumlah berbobot = nilai akhir
  assert.ok(keterangan.some(k => k[1] === '2' && k[3] === 'Sidang (Penguji - Sidang)' && k[4] === 'Cici; Ir. Luar'));
});

test('CSV unggah SIUP meniru ekspor SIUP: titik koma, judul berkutip, Nama berkutip, nilai 2 desimal, LF, tanpa BOM', async () => {
  const { csvSiup } = await import('../../site/penilaian-ta.js');
  const t = csvSiup([['No', 'NIM', 'Nama', 'Sidang (Penguji - Sidang) (40.00%)', 'Sidang (Pembimbing - Sidang) (10.00%)',
    'Bimbingan (Pembimbing - Bimbingan) (50.00%)', 'Nilai Akhir'], [1, '104221001', 'Ani "A"', 85, 70.5, 90, 86.05], [2, '104221002', 'Budi', '', 70, 80, 78]]);
  assert.equal(t, 'No;NIM;Nama;"Sidang (Penguji - Sidang) (40.00%)";"Sidang (Pembimbing - Sidang) (10.00%)";'
    + '"Bimbingan (Pembimbing - Bimbingan) (50.00%)";"Nilai Akhir"\n'
    + '1;104221001;"Ani ""A""";85.00;70.50;90.00;86.05\n2;104221002;"Budi";;70.00;80.00;78.00\n');
  assert.notEqual(t.charCodeAt(0), 0xfeff);
  assert.ok(!t.includes('\r'));
});
