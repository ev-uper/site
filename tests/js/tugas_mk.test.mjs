// Tugas saya koordinator MK dan pengampu (pemilik 2026-11-17; site/tugas-mk.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { tugasMK } from '../../site/tugas-mk.js';

const refCpl = [{ kurikulum: 'K26', kode: 'A', rumusan: 'Sikap', indikator: '1. Integritas' }];
const peta = [{ kurikulum: 'K26', kode_mk: 'S1', cpl: 'A' }, { kurikulum: 'K26', kode_mk: 'S2', cpl: 'A' }, { kurikulum: 'K26', kode_mk: 'S3', cpl: 'A' }];
const lengkap = { versi: '1', cpmk: [{ kode: 'CPMK-1', rumusan: 'x', indikator: { A1: 1 } }], sub: [{ kode: 'Sub-CPMK-1-1', cpmk: 'CPMK-1', rumusan: 'y' }],
                  asesmen: [{ nama: 'UTS' }], bobot: { 'Sub-CPMK-1-1': { UTS: 100 } } };
const mk = [{ kurikulum: 'K26', kode: 'S1', nama: 'Statika', pengampu: ['01'], rps_url: 'https://r' },
            { kurikulum: 'K26', kode: 'S2', nama: 'Hidrologi', pengampu: ['01'], rps_url: null },
            { kurikulum: 'K26', kode: 'S3', nama: 'Beton', pengampu: [], rps_url: null },
            { kurikulum: 'K26', kode: 'S4', nama: 'Lama', pengampu: ['01'], aktif: false }];
const struktur = [{ kurikulum: 'K26', kode_mk: 'S1', data: lengkap }, { kurikulum: 'K26', kode_mk: 'S3', data: lengkap }];
const kelas = [{ tahun_akademik: '2026/2027', semester: 'Ganjil', kode_mk: 'S1', kelas: 'A', dosen_email: 'lain@u.id' },
               { tahun_akademik: '2026/2027', semester: 'Ganjil', kode_mk: 'S1', kelas: 'B', dosen_email: 'saya@u.id' },
               { tahun_akademik: '2026/2027', semester: 'Ganjil', kode_mk: 'S3', kelas: 'A', dosen_email: 'saya@u.id' },
               { tahun_akademik: '2025/2026', semester: 'Genap', kode_mk: 'S2', kelas: 'A', dosen_email: 'saya@u.id' }];
const B = (kode, kls, komponen, asesmen) => ({ tahun_akademik: '2026/2027', semester: 'Ganjil', kurikulum: 'K26', kode_mk: kode, kelas: kls, komponen, asesmen });

test('koordinator MK: CPMK/RPS belum lengkap; MK nonaktif dan lengkap tidak diingatkan', () => {
  const t = tugasMK({ saya: { nidn: '01', email: 'saya@u.id' }, mk, struktur, refCpl, peta, kelas: [], berkas: [] });
  assert.equal(t.length, 1);
  assert.equal(t[0].judul, 'CPMK dan penilaian: 1 mata kuliah yang Anda koordinasikan belum lengkap');
  // 113: RPS belum disahkan Kaprodi; bila sudah disahkan tetapi tanpa bukti: 'RPS bertanda tangan Dekan belum diunggah'.
  assert.equal(t[0].rinci, 'S2 Hidrologi: CPMK belum diisi, RPS belum disahkan.');
  assert.equal(t[0].href, 'cpmk.html?kode=S2');
});

test('portofolio semester terbaru: tingkat MK untuk koordinator, kelas sendiri untuk pengampu, MK tanpa koordinator', () => {
  const berkas = [B('S1', null, 'materi'), B('S1', null, 'soal', 'UTS'), B('S1', 'B', 'presensi'), B('S3', null, 'materi')];
  const t = tugasMK({ saya: { nidn: '01', email: 'saya@u.id' }, mk, struktur, refCpl, peta, kelas, berkas }).find(x => x.jenis === 'portofolio');
  assert.equal(t.judul, 'Portofolio 2026/2027 Ganjil: 2 mata kuliah belum lengkap');
  // S1: koordinator -> kunci/rubrik UTS (1); kelas B milik saya -> 3 contoh + BAP (4); kelas A orang lain tidak dihitung.
  // S3: tanpa koordinator, saya pengampu kelas A -> tingkat MK soal + kunci (2), kelas A 5 komponen.
  assert.match(t.rinci, /^S1 \(tingkat MK 1 komponen, kelas B 4 komponen\); S3 \(tingkat MK 2 komponen, kelas A 5 komponen\)\./);
  assert.equal(t.href, 'portofolio.html?ta=2026%2F2027&sm=Ganjil');
  // Dosen yang bukan koordinator dan tidak mengajar tidak mendapat butir apa pun.
  assert.deepEqual(tugasMK({ saya: { nidn: '99', email: 'x@u.id' }, mk, struktur, refCpl, peta, kelas, berkas }), []);
});

test('tinjauan RPS (115): MK belum diajukan dan RPS yang harus direvisi', async () => {
  const mkT = [{ kurikulum: 'K21', kode: '41210', nama: 'Mekanika Tanah I', aktif: false, pengampu: [] },
               { kurikulum: 'K26', kode: '41321', nama: 'Mekanika Tanah 1', aktif: true, pengampu: ['01'], rps_url: 'x' }];
  const ringkasan = { berkas: [{ course_code: '41210', course_name: 'Mekanika Tanah I', curriculum: 'K21', term: '2025/2026 Genap', jenis: 'nilai_akhir', class_name: 'A' }] };
  const padanan = [{ kurikulum_lama: 'K21', kode_lama: '41210', kurikulum_baru: 'K26', kode_baru: '41321', tidak_berlanjut: false }];
  const dasar = { saya: { nidn: '01', email: 'saya@u.id' }, mk: mkT, struktur: [], refCpl: [], peta: [], kelas: [], berkas: [] };
  const tin = (x = {}) => ({ patch: true, ringkasan, padanan, mulai: 20252, rps: [{ kurikulum: 'K26', kode_mk: '41321', revisi: 1 }], tinjauan: [], ...x });
  const a = tugasMK({ ...dasar, tinjau: tin() }).filter(t => t.jenis === 'tinjauan');
  assert.deepEqual(a.map(t => t.judul), ['Tinjauan RPS 2025/2026 Genap: 1 mata kuliah belum diajukan']);
  const disetujui = { kurikulum: 'K21', kode_mk: '41210', tahun_akademik: '2025/2026', semester: 'Genap', status: 'disetujui', keputusan: 'revisi',
                      rps_dasar: { 'K26|41321': 1 }, data: { tenggat: '2027-01-31' } };
  const b = tugasMK({ ...dasar, tinjau: tin({ tinjauan: [disetujui] }) }).filter(t => t.jenis === 'tinjauan');
  assert.deepEqual(b.map(t => t.judul), ['Revisi RPS hasil tinjauan: 1 RPS perlu diperbaiki dan diajukan ulang']);
  assert.equal(b[0].href, 'rps.html?kur=K26&kode=41321');
  assert.deepEqual(tugasMK({ ...dasar, tinjau: tin({ tinjauan: [disetujui], rps: [{ kurikulum: 'K26', kode_mk: '41321', revisi: 2 }] }) })
    .filter(t => t.jenis === 'tinjauan'), []);
});

test('137: anggota team teaching mendapat butir portofolio kelasnya walau bukan dosen di daftar kelas CPL', () => {
  const berkas = [B('S1', null, 'materi'), B('S1', null, 'soal', 'UTS'), B('S1', 'B', 'presensi')];
  const tim = [{ tahun_akademik: '2026/2027', semester: 'Ganjil', kurikulum: 'K26', kode_mk: 'S1', kelas: 'A', peran: 'anggota' }];
  const t = tugasMK({ saya: { nidn: '99', email: 'x@u.id' }, mk, struktur, refCpl, peta, kelas, berkas, tim }).find(x => x.jenis === 'portofolio');
  assert.match(t.rinci, /^S1 \(kelas A 5 komponen\)\./);                          // kelas B milik orang lain tidak dihitung
  assert.deepEqual(tugasMK({ saya: { nidn: '99', email: 'x@u.id' }, mk, struktur, refCpl, peta, kelas, berkas, tim: [] }), []);
});
