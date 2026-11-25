// CV dosen otomatis (.docx), owner 2026-11-11.
import test from 'node:test';
import assert from 'node:assert/strict';
import { kumpulKarya, isiCV, tahunAwal, namaBerkasCV, urlProfil, urlDoi } from '../../site/cv-dosen.js';

const D = {
  prodi: 'Teknik Contoh', institusi: 'Universitas Contoh',
  dosen: [{ nama: 'Ani Contoh', slug: 'ani-contoh' }, { nama: 'Budi Lain', slug: 'budi-lain' }],
  publikasi: [
    { judul: 'Hujan & <banjir>', tahun: 2025, jenis: 'jurnal', terbitan: 'Jurnal Air', volume: '12', nomor: '3', halaman: '401–415', indeksasi: 'scopus_q2', doi: 'https://doi.org/10.1/AB',
      penulis: [{ nama: 'Budi Lain', slug: 'budi-lain', peran: 'penulis_pertama' }, { nama: 'Ani Contoh', slug: 'ani-contoh', peran: 'anggota', korespondensi: true }] },
    { judul: 'Lama', tahun: 2018, jenis: 'prosiding', indeksasi: 'sinta_3_4', penulis: [{ nama: 'ANI CONTOH', slug: 'x', peran: 'penulis_pertama' }] },
    { judul: 'Bukan milik', tahun: 2025, penulis: [{ nama: 'Budi Lain', slug: 'budi-lain' }] },
  ],
  kegiatan: [
    { judul: 'Riset A', tahun: 2026, kategori: 'penelitian', skema: 'Fundamental', kelompok: 'DPPM', mitra: [{ nama: 'PUPR' }], penulis: [{ slug: 'ani-contoh', nama: 'Ani Contoh', peran: 'ketua' }] },
    { judul: 'Abdimas B', tahun: 2024, kategori: 'pkm', penulis: [{ slug: 'ani-contoh', nama: 'Ani Contoh', peran: 'anggota' }] },
  ],
  luaran_dosen: [{ tahun: 2026, jenis: 'buku_isbn', nama_bagian: 'Buku ber-ISBN', judul: 'Buku C', dosen: ['ani contoh'] }],
  rekognisi: [{ tahun: 2026, dosen: 'Ani Contoh', bentuk: 'invited_speaker', nama_kegiatan: ' Simposium ', tingkat: 'internasional' }],
};
const P = { nama: 'Ani Contoh', nidn: '0101', jabatan: 'lektor', kategori: 'tetap', email: 'ani@contoh.ac.id', sinta_id: '123',
  riwayat_pendidikan: [{ jenjang: 'doktor', perguruan_tinggi: 'Univ B', tahun_lulus: '2015' }, { jenjang: 'sarjana', perguruan_tinggi: 'Univ A', tahun_lulus: '2005' }],
  sertifikat: [{ jenis: 'profesi', bidang: 'Insinyur', lembaga: 'PII' }] };

test('works are matched by slug or name (case-insensitive), with role, newest first', () => {
  const K = kumpulKarya(P, D);
  assert.deepEqual(K.publikasi.map(p => p.judul), ['Hujan & <banjir>', 'Lama']);
  assert.equal(K.publikasi[0].korespondensi, true);
  assert.equal(K.penelitian[0].peran, 'ketua');
  assert.equal(K.pkm.length, 1);
  assert.equal(K.luaran.length, 1);
  assert.equal(K.rekognisi.length, 1);
});

test('five-year period filter', () => {
  assert.equal(tahunAwal('5', new Date(2026, 10, 11)), 2022);
  assert.equal(tahunAwal('semua'), null);
  const K = kumpulKarya(P, D, 2022);
  assert.deepEqual(K.publikasi.map(p => p.judul), ['Hujan & <banjir>']);
});

test('document body: owner bold, DOI normalised, text escaped, sections present', () => {
  const x = isiCV(P, D, { tanggal: '2026-11-11' });
  assert.match(x, /<w:b\/><\/w:rPr><w:t xml:space="preserve">Ani Contoh<\/w:t>/);
  assert.match(x, /https:\/\/doi\.org\/10\.1\/AB/);
  // Sitasi: Jurnal Air, 12(3), 401–415 (patch 74); teks gabungan semua <w:t>.
  // Kode kolom HYPERLINK (instrText) bukan teks yang tampil.
  assert.ok(x.replace(/<w:instrText[^>]*>[^<]*<\/w:instrText>/g, '').replace(/<[^>]+>/g, '').includes('Jurnal Air, 12(3), 401–415. https://doi.org/10.1/AB. '));
  // Tautan yang bisa diklik (pemilik 2026-11-24): DOI, SINTA, ORCID, email.
  assert.ok(x.includes('HYPERLINK "https://doi.org/10.1/AB"'));
  assert.ok(x.includes('HYPERLINK "https://sinta.kemdiktisaintek.go.id/authors/profile/123"'));
  assert.ok(x.includes('HYPERLINK "mailto:ani@contoh.ac.id"'));
  assert.ok(x.includes('Hujan &amp; &lt;banjir&gt;') && !x.includes('<banjir>'));
  for (const s of ['Identitas', 'Riwayat pendidikan', 'Sertifikasi', 'Publikasi (2)', 'Penelitian (1)', 'Pengabdian kepada masyarakat (1)', 'Luaran dan HKI (1)', 'Rekognisi (1)'])
    assert.ok(x.includes(s), s);
  assert.match(x, /Scopus Q2, korespondensi/);
  assert.ok(x.indexOf('Sarjana') < x.indexOf('Doktor'));          // education in order
  assert.match(x, /2 publikasi \(1 terindeks Scopus\)/);
});

test('empty profile still gives a sensible document; file name is safe', () => {
  const x = isiCV({ nama: 'Tanpa Karya' }, D, {});
  assert.match(x, /Belum diisi di profil/);
  assert.match(x, /Belum ada publikasi terverifikasi/);
  assert.ok(!x.includes('Sertifikasi'));
  assert.equal(namaBerkasCV({ nama: 'Dr. Ani Contoh, S.T.' }, '2026-11-11'), 'CV_Dr_Ani_Contoh_S_T_2026-11-11.docx');
});

test('scheme and funding source are not repeated when identical', () => {
  const D2 = { ...D, kegiatan: [{ judul: 'R', tahun: 2026, kategori: 'penelitian', skema: 'Mandiri', kelompok: 'Mandiri',
    penulis: [{ slug: 'ani-contoh', nama: 'Ani Contoh', peran: 'ketua' }] }] };
  const x = isiCV(P, D2, {});
  assert.ok(x.includes('>Mandiri<') && !x.includes('Mandiri — Mandiri'));
});

// Biodata pengusul hibah, susunan A–J (owner 2026-11-11).
import { isiBiodataHibah, mkDiampu } from '../../site/cv-dosen.js';

const DH = {
  prodi: 'Teknik Contoh', institusi: 'Universitas Contoh', dosen: [{ nama: 'Ani Contoh', slug: 'ani-contoh' }],
  publikasi: [
    { judul: 'Jurnal baru', tahun: 2025, jenis: 'jurnal', terbitan: 'Jurnal <Air>', volume: '7', nomor: '2', halaman: '11–20', penulis: [{ slug: 'ani-contoh', nama: 'Ani Contoh' }] },
    { judul: 'Makalah seminar', tahun: 2024, jenis: 'prosiding', terbitan: 'Seminar HATHI', penulis: [{ slug: 'ani-contoh', nama: 'Ani Contoh' }] },
    { judul: 'Jurnal lama', tahun: 2015, jenis: 'jurnal', terbitan: 'J', penulis: [{ slug: 'ani-contoh', nama: 'Ani Contoh' }] },
  ],
  kegiatan: [{ judul: 'Riset Banjir', tahun: 2026, kategori: 'penelitian', skema: 'Fundamental', kelompok: 'DPPM', penulis: [{ slug: 'ani-contoh', nama: 'Ani Contoh', peran: 'ketua' }] }],
  luaran_dosen: [
    { tahun: 2025, jenis: 'buku_isbn', judul: 'Buku Hidrologi', dosen: ['Ani Contoh'] },
    { tahun: 2024, jenis: 'hak_cipta', judul: 'Program Banjir', dosen: ['Ani Contoh'] },
    { tahun: 2024, jenis: 'produk', judul: 'Alat ukur', dosen: ['Ani Contoh'] },
  ],
  rekognisi: [
    { tahun: 2019, dosen: 'Ani Contoh', bentuk: 'penghargaan', nama_kegiatan: 'Dosen Berprestasi' },
    { tahun: 2025, dosen: 'Ani Contoh', bentuk: 'invited_speaker', nama_kegiatan: 'Pembicara' },
    { tahun: 2012, dosen: 'Ani Contoh', bentuk: 'penghargaan', nama_kegiatan: 'Terlalu lama' },
  ],
};
const PH = { nama: 'Ani Contoh', nidn: '0101', jabatan: 'lektor', email: 'ani@x.id',
  riwayat_pendidikan: [{ jenjang: 'sarjana', perguruan_tinggi: 'Univ A', bidang_ilmu: 'Teknik Contoh', tahun_lulus: '2005' },
    { jenjang: 'doktor', perguruan_tinggi: 'Univ C', tahun_lulus: '2015' }] };
const O = { kini: new Date(2026, 10, 11), tanggal: '2026-11-11',
  dana: [{ kategori: 'penelitian', judul: 'riset banjir', tahun: 2026, besaran_dana: 75500000 },
    { kategori: 'luaran', judul: 'Buku Hidrologi', tahun: 2025, nama_terbitan: 'Penerbit Contoh' },
    { kategori: 'luaran', judul: 'Program Banjir', tahun: 2024, nama_terbitan: 'EC00202412345' }],
  mk: [{ kode: 'SI2', nama: 'Hidrologi', sks: 3, pengampu: ['0101', '0202'] }, { kode: 'SI1', nama: 'Irigasi', sks: 2, pengampu: '0303; 0101' },
    { kode: 'SI3', nama: 'Lain', pengampu: ['0202'] }, { kode: 'SI4', nama: 'Nonaktif', aktif: false, pengampu: ['0101'] }] };

test('courses taught are matched by NIDN in array or text form, active only', () => {
  assert.deepEqual(mkDiampu(PH, O.mk).map(m => m.kode), ['SI1', 'SI2']);
  assert.deepEqual(mkDiampu({ nama: 'X' }, O.mk), []);
});

test('grant biodata: A–J sections, funds in million rupiah, journals vs seminars, books and IPR, awards', () => {
  const x = isiBiodataHibah(PH, DH, O);
  for (const s of ['A. Identitas Diri', 'B. Riwayat Pendidikan', 'C. Pengalaman Penelitian', 'D. Pengalaman Pengabdian', 'E. Publikasi Artikel',
    'F. Pemakalah Seminar', 'G. Karya Buku', 'H. Perolehan HKI', 'I. Pengalaman Merumuskan', 'J. Penghargaan']) assert.ok(x.includes(s), s);
  assert.ok(x.includes('>75,5<'));                                         // 75.500.000 -> 75,5 juta
  assert.ok(x.includes('Irigasi (2 SKS); Hidrologi (3 SKS)'));
  assert.ok(x.includes('Jurnal &lt;Air&gt;') && !x.includes('Jurnal lama'));   // 5-year window, escaped
  assert.ok(x.includes('7/2/2025'));                                        // Volume/Nomor/Tahun (patch 74)
  assert.ok(x.indexOf('Seminar HATHI') > x.indexOf('F. Pemakalah'));
  assert.ok(x.includes('Penerbit Contoh') && x.includes('EC00202412345') && x.includes('Hak cipta'));
  assert.ok(!x.includes('Alat ukur'));                                      // product is neither book nor IPR
  assert.ok(x.includes('Dosen Berprestasi') && !x.includes('Pembicara') && !x.includes('Terlalu lama'));
  assert.ok(x.includes('(isi)'));
  assert.ok(x.includes('Univ A') && x.includes('Univ C'));
  assert.match(x, /Pengusul,/);
});

test('profile and DOI URLs (pemilik 2026-11-24)', () => {
  assert.equal(urlProfil('orcid', '0000-0002-1825-0097'), 'https://orcid.org/0000-0002-1825-0097');
  assert.equal(urlProfil('orcid', 'orcid.org/0000-0002-1825-0097'), 'https://orcid.org/0000-0002-1825-0097');
  assert.equal(urlProfil('orcid', 'https://orcid.org/0000-0002-1825-0097'), 'https://orcid.org/0000-0002-1825-0097');
  assert.equal(urlProfil('scopus_id', ' 57190000000 '), 'https://www.scopus.com/pages/authors/57190000000');
  assert.equal(urlProfil('sinta_id', ''), '');
  assert.equal(urlDoi('10.1/AB'), 'https://doi.org/10.1/AB');
  assert.equal(urlDoi('doi:10.1/AB'), 'https://doi.org/10.1/AB');
  assert.equal(urlDoi('https://dx.doi.org/10.1/AB'), 'https://doi.org/10.1/AB');
});

test('sertifikasi: serdos, SKIP, STRI, masa berlaku; tautan bukti Drive tidak dicetak (pemilik 2026-11-24)', () => {
  const Q = { nama: 'Ani Contoh', nomor_serdos: '1234', skip: 'IPM', stri: 'STRI-9', sertifikat: [
    { jenis: 'kompetensi', bidang: 'K3', lembaga: 'BNSP', berlaku_sampai: '2025-01-31', url: 'https://drive.google.com/x' },
    { jenis: 'profesi', bidang: 'Insinyur', berlaku_sampai: '2030-12-31' }] };
  const x = isiCV(Q, D, { kini: new Date(2026, 10, 24) });
  const teks = x.replace(/<w:instrText[^>]*>[^<]*<\/w:instrText>/g, '').replace(/<[^>]+>/g, '');
  for (const s of ['Sertifikat pendidik', '1234', 'Insinyur profesional (SKIP)', 'IPM', 'STRI-9', '31 Januari 2025 (kedaluwarsa)', '31 Desember 2030'])
    assert.ok(teks.includes(s), s);
  // CV dibagikan ke luar: bukti Drive (akses terbatas) tidak dicetak; tautan publikasi (DOI) tetap.
  assert.ok(!x.includes('drive.google.com') && !teks.includes('lihat bukti'));
  assert.ok(!/Nomor sertifikat pendidik/.test(teks));   // pindah dari Identitas ke Sertifikasi
});

test('STRI tidak tercetak dua kali bila sudah dicatat sebagai sertifikat profesi (pemilik 2026-11-24)', () => {
  const hitung = Q => (isiCV(Q, D, {}).replace(/<[^>]+>/g, '').match(/STRI-9/g) || []).length;
  assert.equal(hitung({ nama: 'Ani Contoh', stri: 'STRI-9' }), 1);
  assert.equal(hitung({ nama: 'Ani Contoh', stri: 'STRI-9', sertifikat: [{ jenis: 'profesi', bidang: 'STRI', nomor: 'STRI-9', berlaku_sampai: '2029-01-01' }] }), 1);
  const x = isiCV({ nama: 'Ani Contoh', stri: 'STRI-9', sertifikat: [{ jenis: 'profesi', bidang: 'Surat Tanda Registrasi Insinyur', nomor: '123' }] }, D, {});
  assert.ok(!x.includes('STRI-9'));
  assert.equal(hitung({ nama: 'Ani Contoh', stri: 'STRI-9', sertifikat: [{ jenis: 'profesi', bidang: 'STRI PII', nomor: '555' }] }), 0);
  // 'Industri' memuat huruf s-t-r-i tetapi bukan STRI.
  assert.equal(hitung({ nama: 'Ani Contoh', stri: 'STRI-9', sertifikat: [{ jenis: 'industri', bidang: 'K3 Industri', nomor: '77' }] }), 1);
});
