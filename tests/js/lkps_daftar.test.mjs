// site/lkps.js stage 2: list sheets from Supabase tables (owner 2026-11-04).
// Fictitious data. Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { petaDaftar, serialTanggal, serialISO } from '../../site/lkps.js';

const TS = 2026;                                  // 3-TS window 2024..2026
const pen = (nama, peran = 'ketua') => ({ peran, dosen: { nama } });
const DAFTAR = {
  dosen: [
    { nama: 'Zahra Uji', nidn: '002', pendidikan: 'S2', jabatan: 'asisten_ahli', dtps: true, peran: 'dosen' },
    { nama: 'Adi Uji', nidn: '001', pendidikan: 'S3', jabatan: 'lektor_kepala', dtps: true, peran: 'admin',
      kategori: 'tetap', bidang_keahlian: 'Hidrologi', sesuai_kompetensi_inti: true, sesuai_keahlian_mk: true,
      nomor_serdos: 'SD-9', skip: 'IPM', stri: 'ST-1', mk_ps_lain: 'Hidrolika (T. Lingkungan)',
      riwayat_pendidikan: [
        { jenjang: 'sarjana', program_studi: 'Teknik Contoh', perguruan_tinggi: 'Univ A', bidang_ilmu: 'Keairan' },
        { jenjang: 'magister', program_studi: 'Teknik Contoh', perguruan_tinggi: 'Univ B' },
        { jenjang: 'doktor_terapan', program_studi: 'Rekayasa Air', perguruan_tinggi: 'Univ C', bidang_ilmu: 'Hidrologi' }],
      sertifikat: [{ jenis: 'kompetensi', bidang: 'Ahli SDA', lembaga: 'LPJK' }, { jenis: 'profesi', bidang: 'Insinyur', lembaga: 'PII' }] },
    { nama: 'Budi Industri', nidn: 'NUPTK-7', dtps: false, peran: 'dosen', kategori: 'industri', perusahaan: 'PT Beton' },
    { nama: 'Staf Admin', nidn: 'STAF-1', pendidikan: null, jabatan: null, dtps: false, peran: 'admin' },
  ],
  karya: [
    { id: 'k1', status: 'terverifikasi', kategori: 'penelitian', judul: 'Banjir', tahun: 2025, bulan: 3, kerjasama_id: 5,
      tema_id: 1, keterlibatan_mhs: 'tugas_akhir',
      karya_penulis: [pen('Adi Uji')], karya_mitra: [{ institusi: 'BBWS', tingkat: 'nasional' }],
      karya_mahasiswa: [{ nama: 'Mhs A' }, { nama: 'Mhs B' }] },
    { status: 'terverifikasi', kategori: 'pkm', judul: 'Desa', tahun: 2023, bulan: 10, tema_id: 2,   // TS 2024
      karya_penulis: [pen('Zahra Uji')], karya_mitra: [{ institusi: 'Desa X', tingkat: 'wilayah_lokal' }],
      karya_mahasiswa: [{ nama: 'Mhs C' }] },
    { status: 'terverifikasi', kategori: 'pkm', judul: 'Lama', tahun: 2023, bulan: 5,      // TS 2023: outside
      karya_penulis: [pen('Zahra Uji')], karya_mitra: [{ institusi: 'Lama', tingkat: 'nasional' }] },
    { status: 'terverifikasi', kategori: 'integrasi', judul: 'Banjir', tahun: 2026, bulan: 2,
      mata_kuliah: 'Hidrologi', sub_jenis: 'studi_kasus', karya_penulis: [pen('Adi Uji')],
      induk_id: 'k1', bukti_integrasi: 'laporan_akhir', sesuai_rps: true },
    { status: 'terverifikasi', kategori: 'luaran', sub_jenis: 'ttg', judul: 'Alat filter', tahun: 2025, bulan: 8,
      tkt: 6, nomor_tkt: 'TKT-06/2025', karya_penulis: [pen('Zahra Uji')] },
    { status: 'terverifikasi', kategori: 'publikasi', jenis: 'jurnal', indeksasi: 'scopus_q2', judul: 'Model debit',
      nama_terbitan: 'J Hydrol', tahun: 2025, bulan: 4, doi: '10.1/x', jumlah_sitasi: 12,
      karya_penulis: [pen('Adi Uji', 'penulis_pertama'), { peran: 'anggota', korespondensi: true, dosen: { nama: 'Zahra Uji' } }] },
    { status: 'terverifikasi', kategori: 'publikasi', jenis: 'jurnal', indeksasi: 'wos', judul: 'Artikel lama',
      nama_terbitan: 'J Teknik', tahun: 2020, jumlah_sitasi: 3, karya_penulis: [pen('Zahra Uji', 'penulis_pertama')] },
    { status: 'terverifikasi', kategori: 'luaran', sub_jenis: 'paten', judul: 'Alat ukur', tahun: 2025, bulan: 6,
      nama_terbitan: 'P00202500001', karya_penulis: [pen('Adi Uji')] },
    { status: 'terverifikasi', kategori: 'luaran', sub_jenis: 'buku_isbn', judul: 'Buku', tahun: 2026, bulan: null,
      nama_terbitan: '978-1', karya_penulis: [pen('Zahra Uji')] },
    { status: 'terverifikasi', kategori: 'rekognisi', sub_jenis: 'narasumber', judul: 'Narasumber BNPB',
      tahun: 2025, bulan: 1, tingkat: 'nasional', karya_penulis: [pen('Zahra Uji', 'penerima')] },
    { status: 'diajukan', kategori: 'rekognisi', sub_jenis: 'editor', judul: 'Belum verif', tahun: 2025,
      karya_penulis: [pen('Adi Uji')] },
  ],
  kerjasama: [
    { mitra: 'PT Magang', jenis: 'pendidikan', tingkat: 'internasional', kegiatan: 'MBKM', tahun_mulai: 2024, tahun_selesai: 2027 },
    { mitra: 'Selesai lama', jenis: 'pendidikan', tingkat: 'nasional', tahun_mulai: 2019, tahun_selesai: 2022 },
    { id: 5, mitra: 'bbws ', jenis: 'penelitian', tingkat: 'nasional', kegiatan: 'MoU SDA', tahun_mulai: 2024,
      tanggal_mulai: '2024-02-01', tanggal_selesai: '2027-01-31', manfaat: 'Data hidrologi', jenis_bukti: 'spk' },
    { id: 6, mitra: 'Pemda', jenis: 'pkm', tingkat: 'wilayah', kegiatan: 'Desa binaan', tahun_mulai: 2025,
      tanggal_mulai: '2025-03-15', jenis_bukti: 'bukti_pelaksanaan' },
  ],
  bkd: [
    { nidn: '001', tahun_akademik: '2025/2026', semester: 'ganjil', sks_pendidikan: 6, sks_penelitian: 3, sks_pkm: 1, sks_penunjang: 2 },
    { nidn: '001', tahun_akademik: '2025/2026', semester: 'genap', sks_pendidikan: 8, sks_penelitian: 2, sks_pkm: 1, sks_penunjang: 1 },
    { nidn: '002', tahun_akademik: '2024/2025', semester: 'ganjil', sks_pendidikan: 9 },
  ],
  prestasi: [
    { nama_kegiatan: 'Lomba jembatan', bidang: 'akademik', tahun: 2022, bulan: 9, tingkat: 'internasional', capaian: 'Juara 1' },
    { nama_kegiatan: 'Futsal', bidang: 'non_akademik', tahun: 2026, bulan: 4, tingkat: 'wilayah_lokal', capaian: 'Juara 2' },
    { nama_kegiatan: 'Terlalu lama', bidang: 'akademik', tahun: 2021, bulan: 3, tingkat: 'nasional', capaian: 'x' },
  ],
  luaranMhs: [{ tahun: 2025, bulan: 7, jenis: 'hak_cipta', judul: 'Aplikasi', nomor: 'EC00202501' },
    { tahun: 2025, bulan: 9, jenis: 'paten_sederhana', judul: 'Alat ukur mhs', status_hki: 'granted', nomor: 'S00202500002' },
    { tahun: 2026, bulan: 1, jenis: 'ttg', judul: 'Filter mhs', tkt: 5, nomor: 'TKT-05' }],
  mhs: [{ tahun_akademik: '2025/2026', jumlah_mahasiswa_aktif: 255, jumlah_lulusan: 40, ipk_min: 2.75, rerata_ipk_lulusan: 3.3, ipk_maks: 3.92,
          jumlah_mahasiswa_asing_penuh: 2, jumlah_mahasiswa_asing_paruh: 1 },
        { tahun_akademik: '2023/2024', jumlah_lulusan: 0, ipk_min: 3, ipk_maks: 3.5 }],
  tracer: [{ tahun_lulus: 2024, wt_kurang_3: 5, wt_3_18: 7, wt_lebih_18: 1, kesesuaian_rendah: 2, kesesuaian_sedang: 6, kesesuaian_tinggi: 5 },
           { tahun_lulus: 2026, wt_kurang_3: 99 }],
  tema: [{ id: 1, nama: 'Mitigasi banjir' }, { id: 2, nama: 'Desa tangguh' }],
  vmts: [{ id: 1, jenis: 'pt', visi: 'Unggul global', misi: 'Mendidik', nomor_sk: 'SK-01' },
         { id: 3, jenis: 'ps', visi: 'Rekayasa air berkelanjutan' }],
  buktiVmts: [{ baris_id: 3, url: 'https://drive/visi-ps' }, { baris_id: 1, url: null, dokumen: { url: 'https://drive/sk-pt' } }],
  prasarana: [{ prasarana: 'Lab Hidrolika', jumlah_prasarana: 1, alat: 'Flume', jumlah_standar: 1, jumlah_dimiliki: 2,
                kepemilikan: 'sendiri', kondisi: 'terawat' },
              { prasarana: 'Lab Hidrolika', alat: 'Current meter', kepemilikan: 'sewa', kondisi: 'tidak_terawat' },
              { prasarana: 'Ruang kelas', jumlah_prasarana: 8, urutan: 1 }],
  dokK3l: [{ jenis_dokumen: 'SOP evakuasi', jumlah: 2, riwayat_pengesahan: 'SK 12/2024' }],
  fasK3l: [{ nama_sarana: 'APAR', fungsi: 'Pemadam api', jumlah_unit: 6, kondisi: 'terawat' }],
  dokumen: [{ id: 81, jenis: 'kebijakan_spmi', tahun: 2023, nomor: 'KEB-01', tanggal: '2023-03-01', url: 'https://d/keb23' },
            { id: 82, jenis: 'kebijakan_spmi', tahun: 2027, nomor: 'KEB-02', url: 'https://d/keb27' },
            { id: 83, jenis: 'standar_spmi', tahun: 2024, url: 'https://d/standar' },
            { id: 84, jenis: 'laporan_ami', tahun: 2025, judul: 'AMI 2025', url: 'https://d/ami' }],
  ppepp: [{ tahap: 'evaluasi', dokumen_id: 83, audit_dokumen_id: 84 }, { tahap: 'peningkatan', rtm_dokumen_id: 999 }],
  prodiUpps: [{ jenis_program: 'Sarjana', nama_prodi: 'Teknik Contoh', diakreditasi: true, status_akreditasi: 'baik_sekali',
                nomor_sk: '123/SK/2022', tanggal_sk: '2022-05-10', tanggal_kedaluwarsa: '2027-05-09', urutan: 1 },
              { jenis_program: 'Sarjana', nama_prodi: 'Teknik Lingkungan', diakreditasi: false, status_akreditasi: 'baik',
                mahasiswa_ts2: 100, mahasiswa_ts1: 110, mahasiswa_ts: 120, urutan: 2 }],
  dana: [{ tahun_akademik: '2025/2026', jenis: 'biaya_dosen', dana_upps: 5e9, dana_ps: 1.2e9 },
         { tahun_akademik: '2023/2024', jenis: 'penelitian', dana_ps: 3e8 },
         { tahun_akademik: '2020/2021', jenis: 'pkm', dana_ps: 1 }],
  tendik: [{ nama: 'Wawan', pendidikan: 'd3', sertifikat: 'K3 Lab', unit_kerja: 'prodi' },
           { nama: 'Ayu', pendidikan: 's1', unit_kerja: 'upps' },
           { nama: 'Lama', pendidikan: 's2', aktif: false }],
  mk: [
    { kode: 'SI401', nama: 'Tugas Akhir Desain', semester: 7, sks: 4, capstone: true,
      capstone_pendukung: ['SI301', 'MA101'], capstone_cakupan: 'Desain bendung', pengampu: ['001'] },
    { kode: 'MA101', nama: 'Kalkulus', semester: 1, sks: 3, basic_science: true, unit_penyelenggara: 'universitas' },
    { kode: 'SI301', nama: 'Hidrologi', semester: 5, sks: 3, sks_kuliah: 2, sks_praktikum: 1, inti: true,
      rps_ada: true, unit_penyelenggara: 'prodi', pengampu: ['001', '002'] },
    { kode: 'SI999', nama: 'Lama', semester: 2, sks: 2, aktif: false, pengampu: ['002'] },
    // Kode sama di kurikulum lama (70-patch), tidak aktif: pendukung capstone tetap MK aktif.
    { kode: 'SI301', kurikulum: 'K21', nama: 'Hidrologi K21', semester: 4, sks: 2, aktif: false },
  ],
};
const KOHORT = [
  { tahun_masuk: 2022, masuk: 60, lulus_3_5_sd_4_5: 20, lulus_4_5_sd_5_5: 5, lulus_5_5_sd_6_5: 0, lulus_6_5_sd_8: 0 },
  { tahun_masuk: 2017, masuk: 50, lulus_3_5_sd_4_5: 30 },
];
const L = petaDaftar({ ts: TS, daftar: DAFTAR, D: { akreditasi: { kohort: KOHORT } } });

test('4a: lecturers with a category, profile columns; 4c DTPS only, BKD summed over TS', () => {
  assert.deepEqual([L['4a'].B14, L['4a'].C14, L['4a'].D14, L['4a'].J14, L['4a'].K14],
                   ['Adi Uji', '001', 'Dosen Tetap', 'V', 'Lektor Kepala']);
  assert.deepEqual([L['4a'].E14, L['4a'].F14, L['4a'].G14],
                   ['Teknik Contoh, Univ A (Keairan)', 'Teknik Contoh, Univ B', 'Rekayasa Air, Univ C (Hidrologi) [terapan]']);
  assert.deepEqual([L['4a'].H14, L['4a'].L14, L['4a'].M14, L['4a'].N14, L['4a'].O14, L['4a'].P14, L['4a'].R14, L['4a'].S14],
                   ['Hidrologi', 'SD-9', 'Ahli SDA; Insinyur', 'LPJK; PII', 'IPM', 'ST-1', 'V', 'Hidrolika (T. Lingkungan)']);
  assert.deepEqual([L['4a'].B15, L['4a'].D15, L['4a'].I15, L['4a'].J15], ['Budi Industri', 'Dosen Industri', 'PT Beton', undefined]);
  assert.ok(L['4a'].E16.startsWith('[isi:') && L['4a'].F16 && !L['4a'].G16);   // Zahra: no history, S2
  assert.equal(L['4a'].J16, undefined);                                         // not assessed: no V
  assert.equal(L['4a'].B17, undefined);                                         // staff: no category, not DTPS
  assert.deepEqual([L['4c'].B11, L['4c'].C11, L['4c'].D11, L['4c'].G11, L['4c'].H11, L['4c'].I11],
                   ['Adi Uji', 'V', 14, 5, 2, 3]);
  assert.equal(L['4c'].B12, undefined);                                         // no BKD for TS
});

test('3a1 / 3a4 / 3a5 / 4a Q: active courses by semester, split credits, capstone pairs, teachers', () => {
  const k = (l, c, rows) => rows.map(r => L[l][`${c}${r}`]);
  assert.deepEqual(k('3a1', 'C', [10, 11, 12, 13]), ['MA101', 'SI301', 'SI401', undefined]);   // inactive dropped
  assert.deepEqual([L['3a1'].B10, L['3a1'].F10, L['3a1'].G10, L['3a1'].K10], [1, 3, undefined, 'Universitas']);
  assert.deepEqual([L['3a1'].E11, L['3a1'].F11, L['3a1'].G11, L['3a1'].H11, L['3a1'].J11], ['V', 2, undefined, 1, 'Ada']);
  assert.equal(L['3a1'].J10, undefined);                                      // RPS not stated
  assert.deepEqual([L['3a4'].B10, L['3a4'].C10, L['3a4'].D10, L['3a4'].B11], ['Kalkulus', 1, 3, undefined]);
  assert.deepEqual(k('3a5', 'B', [10, 11]), ['Hidrologi', 'Kalkulus']);
  assert.deepEqual([L['3a5'].D11, L['3a5'].E11, L['3a5'].F11, L['3a5'].G11], ['Tugas Akhir Desain', 4, 7, 'Desain bendung']);
  assert.equal(L['4a'].Q14, 'Hidrologi; Tugas Akhir Desain');                 // Adi (001), course order
  assert.equal(L['4a'].Q16, 'Hidrologi');                                      // Zahra: inactive SI999 dropped
});

test('2a: cooperation from Data prodi and karya partners, level ticks, 3-TS window', () => {
  assert.deepEqual([L['2a1'].B13, L['2a1'].C13, L['2a1'].F13], ['PT Magang', 'V', 'MBKM']);
  assert.equal(L['2a1'].B14, undefined);                                        // ended 2022
  // Banjir -> induk 5: mitra/tanggal/manfaat/bukti dari induk, mitra karya "BBWS" tidak diulang.
  assert.deepEqual([L['2a2'].B12, L['2a2'].D12, L['2a2'].F12, L['2a2'].G12, L['2a2'].L12],
                   ['bbws ', 'V', 'Banjir', 'Data hidrologi', 'Surat Perjanjian Kerjasama (SPK)']);
  assert.deepEqual([L['2a2'].H12, L['2a2'].I12], [serialISO('2024-02-01'), serialISO('2027-01-31')]);
  assert.equal(L['2a2'].B13, undefined);
  // Induk PkM tanpa karya terkait -> barisnya sendiri, lalu mitra karya tanpa induk.
  assert.deepEqual([L['2a3'].B12, L['2a3'].E12, L['2a3'].F12, L['2a3'].I12, L['2a3'].L12],
                   ['Pemda', 'V', 'Desa binaan', undefined, 'Bukti-bukti Pelaksanaan (Laporan, Hasil Kerjasama, Luaran Kerjasama)']);
  assert.deepEqual([L['2a3'].B13, L['2a3'].E13, L['2a3'].G13], ['Desa X', 'V', undefined]);
  assert.equal(L['2a3'].B14, undefined);                                        // TS 2023 karya
  assert.equal(serialISO('2024-02-01').tanggal, 45323);                         // 1 Feb 2024
});

test('3a3 / 4f / 4j: dropdown wording, 1st-of-month dates, verified only', () => {
  assert.deepEqual([L['3a3'].B13, L['3a3'].D13, L['3a3'].E13, L['3a3'].H13],
                   ['Adi Uji', 'Hidrologi', 'Studi Kasus', 'V']);
  assert.deepEqual([L['4f-1'].B7, L['4f-1'].C7, L['4f-1'].D7], ['Alat ukur', serialTanggal(2025, 6), 'P00202500001']);
  assert.deepEqual([L['4f-4'].B7, L['4f-4'].C7, L['4f-4'].D7], ['Buku', undefined, '978-1']);  // no month
  assert.deepEqual([L['4j'].B12, L['4j'].D12, L['4j'].G12, L['4j'].I12],
                   ['Zahra Uji', 'staf ahli/narasumber ', 'V', 2025]);                       // trailing space
  assert.equal(L['4j'].B13, undefined);                                         // unverified excluded
});

test('6c / 6d / 6e3 / 6h1 / 6i', () => {
  assert.deepEqual([L['6c1'].B10, L['6c1'].F10, L['6c1'].G10], ['Lomba jembatan', 'V', 'Juara 1']);
  assert.equal(L['6c1'].B11, undefined);                                        // 2021 outside 5 TS
  assert.deepEqual([L['6c2'].B11, L['6c2'].D11], ['Futsal', 'V']);
  assert.deepEqual([L['6d'].B38, L['6d'].C38, L['6d'].D38], [60, 20, undefined]); // TS-3 row = entry 2022; template opens B:C only
  assert.equal(L['6d'].B33, undefined);                                         // 2017 outside TS-7
  assert.deepEqual([L['6e3-2'].B8, L['6e3-2'].C8], ['Aplikasi', serialTanggal(2025, 7)]);
  assert.deepEqual([L['6h1'].B11, L['6h1'].C11, L['6h1'].D11, L['6h1'].E11, L['6h1'].F11],
                   ['Adi Uji', 'Mitigasi banjir', 'Mhs A, Mhs B', 'Tugas Akhir', 2025]);
  assert.deepEqual([L['6i'].B6, L['6i'].C6, L['6i'].E6, L['6i'].D6], ['Zahra Uji', 'Desa tangguh', 'Desa', 'Mhs C']);
  assert.equal(serialTanggal(2025, 6).tanggal, 45809);                          // 1 Jun 2025
});

test('patch 25: 4f-3 TKT, 3a3 roadmap/evidence/RPS, 4i citations, 4h by role', () => {
  assert.deepEqual([L['4f-3'].B16, L['4f-3'].D16, L['4f-3'].E16], ['Alat filter', 'TKT 6', 'TKT-06/2025']);
  assert.deepEqual([L['3a3'].I13, L['3a3'].J13, L['3a3'].K13], ['Sesuai', 'Laporan Akhir', 'V']);
  // 4.i: any publication year (2020 WoS article listed), most cited first; author = lecturer in 4.a
  assert.deepEqual([L['4i'].B6, L['4i'].C6, L['4i'].D6], ['Adi Uji', 'Model debit, J Hydrol, 2025. DOI: 10.1/x', 12]);
  assert.deepEqual([L['4i'].B7, L['4i'].D7, L['4i'].B8], ['Zahra Uji', 3, undefined]);
  // 4.h: Scopus article + patent (TS 2025 = column D), first author vs corresponding; SINTA excluded
  assert.deepEqual([L['4h'].B16, L['4h'].F16, L['4h'].C16, L['4h'].D16, L['4h'].E16], ['Adi Uji', 'Penulis Pertama', 0, 2, 0]);
  assert.deepEqual([L['4h'].B17, L['4h'].F17, L['4h'].D17], ['Zahra Uji', 'Korespondensi', 1]);
  assert.equal(L['4h'].B18, undefined);
});

test('patch 26: 6a foreign full/part-time, 6b IPK range, 6e3 status/number/TKT, 6f1 Sarjana bands, 6f2 match', () => {
  assert.deepEqual([L['6a'].I7, L['6a'].L7, L['6a'].G7], [2, 1, undefined]);      // TS column; no TS-2 row
  assert.deepEqual([L['6b'].C8, L['6b'].D8, L['6b'].E8, L['6b'].F8, L['6b'].D6], [40, 2.75, 3.3, 3.92, undefined]); // TS-2 had no graduates
  assert.deepEqual([L['6e3-2'].D8], ['EC00202501']);
  assert.deepEqual([L['6e3-1'].B12, L['6e3-1'].D12, L['6e3-1'].E12], ['Alat ukur mhs', 'Granted', 'S00202500002']);
  assert.deepEqual([L['6e3-3'].B18, L['6e3-3'].D18, L['6e3-3'].E18], ['Filter mhs', 'TKT 5', 'TKT-05']);
  assert.deepEqual([L['6f1'].D31, L['6f1'].E31, L['6f1'].F31, L['6f1'].D32], [5, 7, 1, undefined]);  // TS-2 = 2024
  assert.deepEqual([L['6f2'].D7, L['6f2'].E7, L['6f2'].F7], [2, 6, 5]);
});

test('patch 27: PS list, Tabel 1 VMTS, 2b funds, 4b staff, 6a other study programmes', () => {
  assert.deepEqual([L['PS'].B17, L['PS'].C17, L['PS'].D17, L['PS'].E17, L['PS'].F17, L['PS'].G17],
    ['Sarjana', 'Teknik Contoh', 'Terakreditasi Baik Sekali', '123/SK/2022, 10/05/2022', serialISO('2027-05-09'), 255]);
  assert.deepEqual([L['PS'].C18, L['PS'].G18], ['Teknik Lingkungan', 120]);
  assert.deepEqual([L['1'].C7, L['1'].D7, L['1'].C9, L['1'].C11, L['1'].E11],
    ['Visi: Unggul global; Misi: Mendidik', 'SK-01', undefined, 'Visi: Rekayasa air berkelanjutan', 'https://drive/visi-ps']);
  assert.equal(L['1'].E7, 'https://drive/sk-pt');                               // library document link
  assert.deepEqual([L['2b'].E7, L['2b'].I7, L['2b'].G15, L['2b'].G16], [5e9, 1.2e9, 3e8, undefined]);  // 2020 outside
  assert.deepEqual([L['4b'].B11, L['4b'].E11, L['4b'].L11], ['Ayu', 'V', 'UPPS']);
  assert.deepEqual([L['4b'].B12, L['4b'].G12, L['4b'].K12, L['4b'].L12, L['4b'].B13], ['Wawan', 'V', 'K3 Lab', 'Program Studi', undefined]);
  assert.deepEqual([L['6a'].B8, L['6a'].D8, L['6a'].F8, L['6a'].C8], ['Teknik Lingkungan', 100, 120, undefined]);
});

test('patch 28: 5a facilities and equipment, 5b K3L documents, 5c K3L facilities', () => {
  assert.deepEqual([L['5a'].B10, L['5a'].C10, L['5a'].D10], ['Ruang kelas', 8, undefined]);      // urutan 1 first
  assert.deepEqual([L['5a'].B11, L['5a'].D11, L['5a'].H11, L['5a'].J11], ['Lab Hidrolika', 'Current meter', 'V', 'V']);
  assert.deepEqual([L['5a'].D12, L['5a'].E12, L['5a'].F12, L['5a'].G12, L['5a'].I12], ['Flume', 1, 2, 'V', 'V']);
  assert.deepEqual([L['5b'].B17, L['5b'].C17, L['5b'].D17], ['SOP evakuasi', 2, 'SK 12/2024']);
  assert.deepEqual([L['5c'].B17, L['5c'].D17, L['5c'].E17, L['5c'].F17], ['APAR', 6, 'V', undefined]);
});

test('patch 30: 7a SPMI documents from the library (newest year <= TS), 7b PPEPP links', () => {
  assert.deepEqual([L['7a'].C5, L['7a'].D5], ['KEB-01', serialISO('2023-03-01')]);   // 2027 version is after TS
  assert.deepEqual([L['7a'].C7, L['7a'].D7, L['7a'].C6], ['https://d/standar', undefined, undefined]);
  assert.deepEqual([L['7b'].C7, L['7b'].D7, L['7b'].E7], ['https://d/standar', 'https://d/ami', undefined]);
  assert.equal(L['7b'].E9, undefined);                                           // deleted document
});

test('4i: only Scopus/WoS journal or proceedings relevant to the programme (LKPS guide p. 16)', () => {
  const tambah = [
    { status: 'terverifikasi', kategori: 'publikasi', jenis: 'jurnal', indeksasi: 'sinta_1_2', judul: 'SINTA banyak sitasi',
      tahun: 2024, jumlah_sitasi: 50, karya_penulis: [pen('Adi Uji', 'penulis_pertama')] },
    { status: 'terverifikasi', kategori: 'publikasi', jenis: 'jurnal', indeksasi: 'scopus_q1', judul: 'Di luar visi',
      tahun: 2024, jumlah_sitasi: 40, relevan_visi: false, karya_penulis: [pen('Adi Uji', 'penulis_pertama')] },
    { status: 'terverifikasi', kategori: 'publikasi', jenis: 'prosiding', indeksasi: 'scopus_q4', judul: 'Prosiding lama',
      tahun: 2015, jumlah_sitasi: 5, karya_penulis: [pen('Zahra Uji', 'penulis_pertama')] },
  ];
  const M = petaDaftar({ ts: TS, daftar: { ...DAFTAR, karya: [...DAFTAR.karya, ...tambah] }, D: { akreditasi: { kohort: KOHORT } } });
  const judul = [6, 7, 8, 9].map(r => String(M['4i'][`C${r}`] || '').split(',')[0]);
  assert.deepEqual(judul, ['Model debit', 'Prosiding lama', 'Artikel lama', '']);
});

test('daftarProdi: urut Data prodi; prodi kosong tetap tampil tanpa menebak peringkat', async () => {
  const { daftarProdi } = await import('../../site/pustaka-dokumen.js');
  const X = { mhs: [{ tahun_akademik: '2025/2026', jumlah_mahasiswa_aktif: 120 }] };
  const [p] = daftarProdi(X, 'Teknik Contoh', 2026);
  assert.equal(p.nama_prodi, 'Teknik Contoh');
  assert.equal(p.status_akreditasi, undefined);
  assert.equal(p.mahasiswa, 120);
  const ada = daftarProdi({ prodiUpps: [{ nama_prodi: 'B', urutan: 2, diakreditasi: true, mahasiswa_ts: 9 }, { nama_prodi: 'A', urutan: 1 }] }, 'B', 2026);
  assert.deepEqual(ada.map(x => [x.nama_prodi, x.mahasiswa ?? null]), [['A', null], ['B', 9]]);
});
