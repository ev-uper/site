// Pengajuan mahasiswa KP/lomba (pemilik 2026-11-17; site/pengajuan-mhs.js, tugas-saya.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
// Kecocokan dengan teks patch bernomor: hanya di repo sumber (repo prodi hanya punya instal-lengkap.sql hasil pg_dump,
// formatnya lain). Penanda repo sumber: tools/make_package.py (tidak ikut templat).
const SUMBER = existsSync(new URL('../../tools/make_package.py', import.meta.url));
const HANYA_SUMBER = { skip: !SUMBER && 'hanya di repo sumber (patch bernomor)' };
import { JENIS, LABEL_BERKAS, jalur, bolehUbah, bacaAnggota, teksAnggota, periksaIsian, judulPengajuan } from '../../site/pengajuan-mhs.js';
import { tugasSaya } from '../../site/tugas-saya.js';
import { BERKAS_YUDISIUM_BAWAAN, kelengkapanYudisium, labelBerkas, labelStatus, jalurTahap, rekapPengajuan,
         lembarPengajuan, JENIS_KEGIATAN } from '../../site/pengajuan-mhs.js';
import { bolehPengajuan } from '../../site/koordinator.js';

const keadaan = (s, r) => jalur(s, r).map(t => `${t.kunci}:${t.keadaan}`);

test('jalur proses mengikuti status', () => {
  assert.deepEqual(keadaan('draf'), ['draf:kini', 'pembimbing:nanti', 'admin:nanti', 'disetujui:nanti']);
  assert.deepEqual(keadaan('pembimbing'), ['draf:selesai', 'pembimbing:kini', 'admin:nanti', 'disetujui:nanti']);
  assert.deepEqual(keadaan('admin'), ['draf:selesai', 'pembimbing:selesai', 'admin:kini', 'disetujui:nanti']);
  assert.deepEqual(keadaan('disetujui'), ['draf:selesai', 'pembimbing:selesai', 'admin:selesai', 'disetujui:selesai']);
  assert.deepEqual(keadaan('ditolak').at(-1), 'ditolak:tolak');
  const r = [{ status: 'pembimbing', oleh: 'mahasiswa', waktu: '2026-11-01' },
             { status: 'dikembalikan', oleh: 'Pembimbing Satu', catatan: 'Lengkapi surat', waktu: '2026-11-02' }];
  const j = jalur('dikembalikan', r);
  assert.equal(j[0].keadaan, 'kembali');
  assert.equal(j[0].catatan, 'Lengkapi surat');
  assert.equal(j[0].oleh, 'Pembimbing Satu');
  // Tahap pembimbing selesai: waktu dan pemeriksa diambil dari perpindahan ke tahap admin.
  const a = jalur('admin', [...r, { status: 'pembimbing', oleh: 'mahasiswa', waktu: '2026-11-03' },
                            { status: 'admin', oleh: 'Pembimbing Satu', waktu: '2026-11-04' }]);
  assert.equal(a[1].oleh, 'Pembimbing Satu');
  assert.equal(a[1].waktu, '2026-11-04');
  // Catatan unggah surat pengantar (status sama) tidak menggantikan siapa yang memutuskan.
  const b = jalur('admin', [{ status: 'pembimbing', oleh: 'mahasiswa', waktu: '2026-11-03' },
    { status: 'admin', oleh: 'Pembimbing Satu', waktu: '2026-11-04' },
    { status: 'admin', oleh: 'Admin Prodi', catatan: 'Mengunggah surat pengantar', waktu: '2026-11-05' }]);
  assert.equal(b[1].oleh, 'Pembimbing Satu');
  assert.equal(b[1].catatan, '');
  assert.ok(bolehUbah('draf') && bolehUbah('dikembalikan') && !bolehUbah('pembimbing') && !bolehUbah('disetujui'));
});

test('laporan selesai KP: label, jalur per tahap, pemeriksaan isian', async () => {
  const { labelStatus, jalurTahap, periksaSelesai } = await import('../../site/pengajuan-mhs.js');
  // 107: tidak ada "KP berjalan"; label mengikuti jawaban instansi atas surat pengantar.
  assert.equal(labelStatus({ jenis: 'kp', tahap: 'pengajuan', status: 'disetujui' }), 'Surat pengantar terbit; menunggu jawaban instansi');
  assert.equal(labelStatus({ jenis: 'kp', tahap: 'pengajuan', status: 'disetujui', data: { jawaban_instansi: 'diterima' } }),
    'Diterima instansi; KP dilaksanakan (pelaporan selesai belum dikirim)');
  assert.equal(labelStatus({ jenis: 'kp', tahap: 'pengajuan', status: 'ditolak', data: { jawaban_instansi: 'ditolak' } }), 'Ditolak instansi; pengajuan ditutup');
  assert.equal(labelStatus({ jenis: 'kp', tahap: 'pengajuan', status: 'ditolak' }), 'Ditolak');
  assert.equal(labelStatus({ jenis: 'kp', tahap: 'pengajuan', status: 'admin' }), 'Diperiksa koordinator KP/admin');
  // Jalur pengajuan KP: dikirim langsung ke koordinator (draf -> admin -> disetujui).
  assert.deepEqual(jalurTahap({ jenis: 'kp', status: 'admin', riwayat: [] }, 'pengajuan').map(t => [t.label, t.keadaan]), [
    ['Isi pengajuan dan unggah surat', 'selesai'], ['Dikirim ke koordinator KP', 'selesai'],
    ['Diperiksa koordinator KP; pembimbing ditetapkan', 'kini'], ['Surat pengantar terbit', 'nanti']]);
  assert.equal(labelStatus({ jenis: 'kp', tahap: 'selesai', status: 'disetujui' }), 'KP selesai');
  assert.equal(labelStatus({ jenis: 'lomba', status: 'disetujui' }), 'Disahkan; tercatat sebagai prestasi');   // 108
  const riwayat = [{ status: 'draf', waktu: '1' }, { status: 'pembimbing', waktu: '2' }, { status: 'admin', oleh: 'P', waktu: '3' },
    { status: 'disetujui', oleh: 'A', waktu: '4' }, { status: 'pembimbing', tahap: 'selesai', waktu: '5' },
    { status: 'admin', tahap: 'selesai', oleh: 'P', waktu: '6' }];
  const p = { jenis: 'kp', tahap: 'selesai', status: 'admin', riwayat };
  assert.deepEqual(jalurTahap(p, 'pengajuan').map(t => t.keadaan), ['selesai', 'selesai', 'selesai', 'selesai']);
  const s = jalurTahap(p, 'selesai');
  assert.deepEqual(s.map(t => t.label), ['Isi laporan selesai', 'Diperiksa dosen pembimbing', 'Diperiksa koordinator KP/admin', 'KP selesai']);
  assert.deepEqual(s.map(t => t.keadaan), ['selesai', 'selesai', 'kini', 'nanti']);
  assert.equal(s[1].oleh, 'P');
  // KP disetujui, laporan belum dikirim: jalur selesai di langkah pertama.
  assert.deepEqual(jalurTahap({ ...p, tahap: 'pengajuan', status: 'disetujui', riwayat: riwayat.slice(0, 4) }, 'selesai').map(t => t.keadaan),
                   ['kini', 'nanti', 'nanti', 'nanti']);
  assert.deepEqual(periksaSelesai({ tanggal_mulai: '2027-02-01', tanggal_selesai: '2027-01-01', pembimbing_lapangan: 'B', ringkasan: 'pendek' }),
                   ['Tanggal selesai tidak boleh sebelum tanggal mulai.', 'Tulis ringkasan kegiatan (minimal 30 huruf).']);
});

test('anggota tim dari teks dan kembali', () => {
  const xs = bacaAnggota('104123011 - Cici\n104123012 Dodi\n\nEko Luar\n12 - bukan nim');
  assert.deepEqual(xs, [{ nim: '104123011', nama: 'Cici' }, { nim: '104123012', nama: 'Dodi' }, { nim: '', nama: 'Eko Luar' },
                        { nim: '', nama: '12 - bukan nim' }]);
  assert.equal(teksAnggota(xs.slice(0, 3)), '104123011 - Cici\n104123012 - Dodi\nEko Luar');
  assert.equal(bacaAnggota(Array(15).fill('A').join('\n')).length, 10);
});

test('pemeriksaan isian sebelum dikirim', () => {
  assert.deepEqual(periksaIsian('kp', { nim: '104123002', nama: 'Ani', pembimbing: 'x', data: { instansi: 'PT A' } }), []);
  assert.equal(periksaIsian('kp', { nim: '12', nama: 'A', pembimbing: '', data: {} }).length, 4);
  const g = periksaIsian('lomba', { nama: 'Budi', pembimbing: 'x', data: { nama_kegiatan: 'L', tingkat: 'nasional', bidang: '', tanggal: '2026-1-2' } });
  assert.deepEqual(g, ['Pilih bidang lomba.', 'Isi tanggal lomba.']);   // tanpa nim (perbaikan): nim tidak diperiksa
  assert.equal(judulPengajuan({ jenis: 'kp', data: { instansi: 'PT A' } }), 'PT A');
  assert.equal(judulPengajuan({ jenis: 'lomba', data: {} }), 'Lomba');
});

test('jenis berkas sama dengan Apps Script dan patch 90', HANYA_SUMBER, () => {
  const gs = readFileSync(new URL('../../apps-script/Code.gs', import.meta.url), 'utf8');
  // Jenis berkas bertambah di patch berikutnya (93 surat, 94 TA): baca semua patch pengajuan.
  const sql = ['90-patch-pengajuan-mahasiswa', '91-patch-laporan-selesai-kp', '93-patch-pengajuan-surat', '94-patch-jadwal-ta', '96-patch-luaran-mahasiswa',
               '144-patch-kabar-mahasiswa']
    .map(f => readFileSync(new URL(`../../supabase/${f}.sql`, import.meta.url), 'utf8')).join(' ');
  for (const [j, x] of Object.entries(JENIS)) {
    if (j === 'yudisium') continue;   // 122: kode yud_* dari tabel yudisium_berkas; diuji di bawah
    assert.match(gs, new RegExp(`${j}: \\[${x.berkas.map(b => `'${b}'`).join(',\\s*')}\\]`), j);
    for (const b of x.berkas) { assert.ok(sql.includes(`'${b}'`), b); assert.ok(LABEL_BERKAS[b], b); }
    if (x.wajib) assert.ok(sql.includes(`wajib := '${x.wajib}'`), x.wajib);   // surat: tanpa berkas wajib
  }
});

test('berkas yudisium (122): daftar bawaan = isi awal tabel; Apps Script menerima kode yud_*; kelengkapan', HANYA_SUMBER, () => {
  const sql = readFileSync(new URL('../../supabase/instal-lengkap.sql', import.meta.url), 'utf8');
  const gs = readFileSync(new URL('../../apps-script/Code.gs', import.meta.url), 'utf8');
  const benih = [...sql.matchAll(/\('(yud_[a-z0-9_]+)', '([^']+)', (true|false), \d+\)/g)].map(m => ({ kode: m[1], label: m[2], wajib: m[3] === 'true' }));
  assert.deepEqual(BERKAS_YUDISIUM_BAWAAN.map(({ kode, label, wajib }) => ({ kode, label, wajib })), benih);
  assert.equal(benih.filter(b => b.wajib).length, 14);
  assert.match(gs, /MHS_BERKAS_YUDISIUM = \/\^yud_\[a-z0-9_\]\{2,40\}\$\//);
  assert.ok(JENIS.yudisium.tanpaPembimbing);
  const k = kelengkapanYudisium(BERKAS_YUDISIUM_BAWAAN, [{ jenis: 'yud_transkrip' }, { jenis: 'yud_transkrip' }, { jenis: 'yud_bukti_tambahan' }]);
  assert.equal(k.wajib, 14); assert.equal(k.ada, 1); assert.equal(k.kurang.length, 13); assert.ok(!k.kurang.includes('Transkrip'));
  assert.equal(k.butir.find(b => b.kode === 'yud_transkrip').berkas.length, 2);
  assert.equal(labelBerkas('yud_pem'), 'PEM'); assert.equal(labelBerkas('laporan_kp'), 'Laporan KP');
  const p = { jenis: 'yudisium', status: 'admin', data: {} };
  assert.equal(labelStatus(p), 'Diperiksa admin prodi'); assert.equal(judulPengajuan(p), 'Berkas yudisium');
  assert.deepEqual(periksaIsian('yudisium', { nim: '104122040', nama: 'Ani', pembimbing: '', data: {} }), []);
  assert.equal(jalurTahap(p, 'pengajuan')[2].label, 'Diperiksa admin prodi');
  const r = rekapPengajuan([p, { ...p, status: 'disetujui' }, { ...p, status: 'draf' }]);
  assert.deepEqual(r.yudisium, { semua: 2, diperiksa: 1, disahkan: 1, dikembalikan: 0 });
  const L = lembarPengajuan([{ ...p, nim: '1', nama: 'Ani', pengajuan_berkas: [{ jenis: 'yud_pem', nama: 'pem.pdf', url: 'https://drive.google.com/x' }] }]);
  assert.equal(L.Yudisium[1][4], '1/14'); assert.equal(L.Berkas[1][3], 'PEM');
});

test('Tugas saya: pengajuan menunggu pembimbing atau admin', () => {
  const kini = new Date('2026-11-17T10:00:00Z');
  const ps = [
    { nama: 'Ani', jenis: 'kp', status: 'pembimbing', pembimbing_id: 'd1', diperbarui: '2026-11-15T10:00:00Z' },
    { nama: 'Budi', jenis: 'lomba', status: 'admin', pembimbing_id: 'd1', diperbarui: '2026-11-01T10:00:00Z' },
    { nama: 'Cici', jenis: 'kp', status: 'pembimbing', pembimbing_id: 'd2', diperbarui: '2026-11-16T10:00:00Z' }];
  const cari = t => t.find(x => x.jenis === 'pengajuan_mhs');
  const dosen = cari(tugasSaya({ saya: { id: 'd1', peran: 'dosen', dtps: false }, pengajuanMhs: ps }, kini));
  assert.equal(dosen.judul, 'Periksa 1 pengajuan mahasiswa (KP/lomba)');
  assert.equal(dosen.rinci, 'Ani (KP)');
  assert.equal(dosen.hari, 5);
  const admin = cari(tugasSaya({ saya: { id: 'd9', peran: 'admin', dtps: false }, pengajuanMhs: ps }, kini));
  assert.equal(admin.rinci, 'Budi (lomba)');
  assert.equal(admin.tingkat, 'lewat');                // 16 hari sejak berubah
  assert.equal(cari(tugasSaya({ saya: { id: 'd3', peran: 'dosen', dtps: false }, pengajuanMhs: ps }, kini)), undefined);
});

test('rekap KP/lomba: waktu, keadaan, per instansi, lembar Excel', async () => {
  const { waktuPengajuan, keadaanKP, rekapPengajuan, lembarPengajuan } = await import('../../site/pengajuan-mhs.js');
  const xs = [
    { jenis: 'kp', nim: '1', nama: 'A', status: 'disetujui', tahap: 'selesai', data: { instansi: 'PT Satu', rencana_mulai: '2026-08-01' },
      data_selesai: { tanggal_mulai: '2026-09-02', pembimbing_lapangan: 'Ir. B' }, pengajuan_berkas: [{ jenis: 'laporan_kp', nama: 'l.pdf', url: 'https://d/1' }],
      dosen: { nama: 'Dosen P' } },
    { jenis: 'kp', nim: '2', nama: 'B', status: 'disetujui', tahap: 'pengajuan', data: { instansi: ' pt  satu ', rencana_mulai: '2026-10-01' } },
    { jenis: 'kp', nim: '3', nama: 'C', status: 'pembimbing', tahap: 'pengajuan', data: { instansi: 'PT Dua' }, dibuat: '2026-11-17T00:00:00Z' },
    { jenis: 'kp', nim: '4', nama: 'D', status: 'draf', data: { instansi: 'PT Tiga' } },
    { jenis: 'lomba', nim: '5', nama: 'E', status: 'disetujui', data: { nama_kegiatan: 'L', tingkat: 'nasional', tanggal: '2026-05-03' } },
  ];
  assert.deepEqual(waktuPengajuan(xs[0]), { tahun: 2026, bulan: 9 });      // tanggal mulai menang atas rencana
  assert.deepEqual(waktuPengajuan(xs[2]), { tahun: 2026, bulan: 11 });     // tanpa tanggal: dibuat
  assert.deepEqual(xs.map(keadaanKP), ['selesai', 'berjalan', 'proses', 'draf', 'berjalan']);
  const r = rekapPengajuan(xs);
  assert.deepEqual(r.kp, { semua: 3, selesai: 1, berjalan: 1, proses: 1 });
  assert.deepEqual(r.instansi, [{ instansi: 'PT Satu', mahasiswa: 2, selesai: 1, berjalan: 1 }, { instansi: 'PT Dua', mahasiswa: 1, selesai: 0, berjalan: 0 }]);
  assert.equal(r.lomba.disetujui, 1); assert.equal(r.lomba.tingkat.nasional, 1);
  const L = lembarPengajuan(xs, p => p.nim === '1' ? '2026/2027' : '');
  assert.equal(L.KP.length, 4);                                            // draf tidak ikut
  assert.deepEqual(L.KP[1].slice(0, 12), [1, '1', 'A', 'Kerja Praktik (KP)', 'PT Satu', 'Dosen P', '2026-09-02', '', 'Ir. B', '2026/2027', 'KP selesai', 1]);   // 99: kolom Program
  assert.equal(L.Lomba[1][5], 'Nasional');
  assert.deepEqual(L.Berkas[1], ['1', 'A', 'KP', 'Laporan KP', 'l.pdf', { t: 'https://d/1', l: 'https://d/1' }]);
  assert.equal(L['Instansi KP'].length, 3);
});

test('permohonan surat: tanpa pembimbing, isian per jenis, jalur sendiri', async () => {
  const m = await import('../../site/pengajuan-mhs.js');
  assert.deepEqual(m.periksaIsian('surat', { nim: '104123099', nama: 'Rina', data: { jenis_surat: 'aktif_kuliah', keperluan: 'Beasiswa' } }), []);
  assert.deepEqual(m.periksaIsian('surat', { nama: 'Rina', data: { jenis_surat: 'izin_penelitian', keperluan: 'TA' } }),
    ['Tulis keperluan surat.', 'Tulis tujuan surat (kepada siapa).', 'Tulis judul penelitian.']);
  assert.equal(m.judulPengajuan({ jenis: 'surat', data: { jenis_surat: 'rekomendasi' } }), 'Surat rekomendasi');
  assert.equal(m.labelStatus({ jenis: 'surat', status: 'disetujui' }), 'Surat terbit');
  const j = m.jalurTahap({ jenis: 'surat', status: 'admin', riwayat: [{ status: 'draf', waktu: '1' }, { status: 'admin', oleh: 'mahasiswa', waktu: '2' }] });
  assert.deepEqual(j.map(t => `${t.label}:${t.keadaan}`), ['Isi permohonan:selesai', 'Dikirim ke prodi:selesai', 'Diproses admin prodi:kini', 'Surat terbit:nanti']);
});

test('seminar/sidang TA: isian, label, jalur', async () => {
  const m = await import('../../site/pengajuan-mhs.js');
  assert.deepEqual(m.periksaIsian('ta', { nim: '104123077', nama: 'Tono', pembimbing: 'a', data: { tahap_ta: 'sidang_akhir', judul: 'Banjir' } }), []);
  assert.deepEqual(m.periksaIsian('ta', { nama: 'Tono', pembimbing: 'a', data: { judul: 'B', pembimbing_2: 'a' } }),
    ['Pilih tahap TA.', 'Tulis judul TA.', 'Pembimbing 2 harus berbeda dari pembimbing 1.']);
  assert.equal(m.labelStatus({ jenis: 'ta', status: 'admin' }), 'Menunggu jadwal dari admin prodi');
  assert.equal(m.judulPengajuan({ jenis: 'ta', data: {} }), 'Tugas Akhir');
  assert.deepEqual(m.jalurTahap({ jenis: 'ta', status: 'disetujui', riwayat: [] }).map(t => t.label).at(-1), 'Terjadwal');
});

test('publikasi/luaran mahasiswa: isian dan judul', async () => {
  const m = await import('../../site/pengajuan-mhs.js');
  assert.deepEqual(m.periksaIsian('luaran', { nama: 'Lia', pembimbing: 'x', data: { kategori: 'luaran', judul: 'Aplikasi', tahun: '2026', jenis_luaran: 'hak_cipta' } }), []);
  assert.deepEqual(m.periksaIsian('luaran', { nama: 'Lia', pembimbing: 'x', data: { kategori: 'publikasi', judul: 'Artikel', tahun: '26' } }),
    ['Isi tahun terbit/terdaftar.', 'Pilih jenis publikasi.']);
  assert.equal(m.judulPengajuan({ jenis: 'luaran', data: { judul: 'Simulasi banjir' } }), 'Simulasi banjir');
  assert.ok(m.LABEL_BERKAS.bukti_luaran);
});

test('laporan lomba satu persetujuan (108): label dan jalur', async () => {
  const { labelStatus, jalurTahap } = await import('../../site/pengajuan-mhs.js');
  assert.equal(labelStatus({ jenis: 'lomba', status: 'pembimbing' }), 'Diperiksa dosen pembimbing atau pembina kemahasiswaan');
  assert.equal(labelStatus({ jenis: 'lomba', status: 'disetujui' }), 'Disahkan; tercatat sebagai prestasi');
  assert.deepEqual(jalurTahap({ jenis: 'lomba', status: 'disetujui', riwayat: [] }).map(t => [t.label, t.keadaan]), [
    ['Isi laporan dan unggah bukti', 'selesai'], ['Diperiksa dosen pembimbing atau pembina kemahasiswaan', 'selesai'],
    ['Disahkan (satu persetujuan)', 'selesai'], ['Tercatat sebagai prestasi', 'selesai']]);
});

test('pembimbing TA menurut kelompok keahlian (110): label, saring, urutan koordinator', async () => {
  const m = await import('../../site/pengajuan-mhs.js');
  const aju = { jenis: 'ta', status: 'admin', data: { tahap_ta: 'penetapan_pembimbing' } };
  assert.equal(m.penetapanTA(aju), true);
  assert.equal(m.labelStatus(aju), 'Diperiksa koordinator TA');
  assert.equal(m.labelStatus({ ...aju, status: 'disetujui' }), 'Pembimbing TA ditetapkan');
  assert.equal(m.labelStatus({ jenis: 'ta', status: 'admin', data: { tahap_ta: 'seminar_proposal' } }), 'Menunggu jadwal dari admin prodi');
  assert.equal(m.jalurTahap({ ...aju, riwayat: [] }).map(t => t.label).at(-1), 'Pembimbing TA ditetapkan');
  assert.deepEqual(m.periksaIsian('ta', { nama: 'Ani', pembimbing: 'a', data: { tahap_ta: 'penetapan_pembimbing', judul: '' } }),
    ['Pilih kelompok keahlian topik TA.', 'Tulis judul awal TA.']);
  const dosen = [{ id: 'a', nama: 'A', kk: 'AIR', kk_cocok: ['AIR', 'GEO'] }, { id: 'g', nama: 'G', kk: 'GEO', kk_cocok: ['AIR', 'GEO', 'STR', 'TRN'] },
                 { id: 'x', nama: 'X', kk: null, kk_cocok: [] }];
  assert.deepEqual(m.pembimbingCocok(dosen, 'TRN').map(d => d.id), ['g']);
  assert.deepEqual(m.pembimbingCocok(dosen, '').map(d => d.id), []);
  const dekat = [{ kk_a: 'GEO', kk_b: 'STR' }, { kk_a: 'MRK', kk_b: 'STR' }, { kk_a: 'AIR', kk_b: 'GEO' }, { kk_a: 'GEO', kk_b: 'TRN' }];
  assert.equal(m.kkCocok('STR', 'GEO', dekat), true);
  assert.equal(m.kkCocok('AIR', 'TRN', dekat), false);
  assert.equal(m.kkCocok('MRK', 'MRK', []), true);
  const xs = m.pilihanPembimbingTA([{ dosen_id: 'a', nama: 'Ani', kk: 'AIR', kuota: 2, beban: 2 }, { dosen_id: 'b', nama: 'Budi', kk: 'GEO', kuota: null, beban: 1 },
    { dosen_id: 'c', nama: 'Cici', kk: null, kuota: 3, beban: 0 }], 'TRN', dekat);
  assert.deepEqual(xs.map(r => [r.nama, r.cocok, r.teks]), [['Budi', true, 'Budi — GEO — 1'], ['Ani', false, 'Ani — AIR — 2/2 (kuota penuh) (di luar KK)'],
    ['Cici', false, 'Cici — KK belum diisi — 0/3 (di luar KK)']]);
});

test('kabar kegiatan (144): pendamping opsional, satu persetujuan, jenis kegiatan = kabar_kegiatan', () => {
  const ok = { judul: 'Kuliah tamu gempa', tanggal: '2026-11-10', ringkasan: 'Kuliah tamu tentang rekayasa gempa untuk mahasiswa.' };
  assert.deepEqual(periksaIsian('kabar', { nim: '104122050', nama: 'Ani', pembimbing: null, data: ok }), []);   // tanpa pendamping
  assert.deepEqual(periksaIsian('kabar', { nama: 'Ani', pembimbing: null, data: { judul: 'K', tanggal: '', ringkasan: 'pendek', tautan: 'ftp://x' } }),
    ['Tulis judul kegiatan.', 'Isi tanggal kegiatan.', 'Tulis ringkasan kegiatan (20–1200 huruf).', 'Tautan harus diawali https://']);
  assert.deepEqual(periksaIsian('kabar', { nama: 'Ani', data: { ...ok, ringkasan: 'x'.repeat(1201) } }), ['Tulis ringkasan kegiatan (20–1200 huruf).']);
  assert.equal(judulPengajuan({ jenis: 'kabar', data: {} }), 'Kabar kegiatan');
  assert.equal(judulPengajuan({ jenis: 'kabar', data: { judul: 'Kunjungan' } }), 'Kunjungan');
  assert.equal(labelStatus({ jenis: 'kabar', status: 'pembimbing', pembimbing_id: null }), 'Diperiksa pembina kemahasiswaan/admin');
  assert.equal(labelStatus({ jenis: 'kabar', status: 'pembimbing', pembimbing_id: 'd1' }), 'Diperiksa dosen pendamping atau pembina kemahasiswaan');
  assert.equal(labelStatus({ jenis: 'kabar', status: 'disetujui' }), 'Disahkan; terbit di situs prodi');
  assert.equal(jalurTahap({ jenis: 'kabar', status: 'disetujui', riwayat: [] }, 'pengajuan')[3].label, 'Terbit di situs prodi');
  assert.equal(JENIS.kabar.wajib, 'foto');
  // Nilai sama dengan kabar_kegiatan.jenis (patch 81) dan mhs_rapikan (144); 'penelitian' (92) khusus kabar dosen.
  const sql81 = readFileSync(new URL('../../supabase/instal-lengkap.sql', import.meta.url), 'utf8');
  const sql144 = readFileSync(new URL('../../supabase/instal-lengkap.sql', import.meta.url), 'utf8');
  for (const [k] of JENIS_KEGIATAN) { assert.ok(sql81.includes(`'${k}'`), k); assert.ok(sql144.includes(`'${k}'`), k); }
  assert.equal(JENIS_KEGIATAN.length, 8);
  assert.ok(bolehPengajuan({ peran: 'dosen', koordinator: ['pembina_kemahasiswaan'] }, 'kabar'));
  assert.ok(!bolehPengajuan({ peran: 'dosen', koordinator: ['koordinator_kp'] }, 'kabar'));
});

test('Tugas saya: kabar tanpa pendamping menunggu pembina kemahasiswaan/admin', () => {
  const kini = new Date('2026-11-21T10:00:00Z');
  const ps = [{ nama: 'Dewi', jenis: 'kabar', status: 'pembimbing', pembimbing_id: null, diperbarui: '2026-11-20T10:00:00Z' },
              { nama: 'Eka', jenis: 'kabar', status: 'pembimbing', pembimbing_id: 'd1', diperbarui: '2026-11-20T10:00:00Z' }];
  const cari = t => t.find(x => x.jenis === 'pengajuan_mhs');
  const pmb = cari(tugasSaya({ saya: { id: 'd5', peran: 'dosen', dtps: false, koordinator: ['pembina_kemahasiswaan'] }, pengajuanMhs: ps }, kini));
  assert.equal(pmb.rinci, 'Dewi (kabar kegiatan)');
  assert.equal(cari(tugasSaya({ saya: { id: 'd1', peran: 'dosen', dtps: false }, pengajuanMhs: ps }, kini)).rinci, 'Eka (kabar kegiatan)');
  assert.equal(cari(tugasSaya({ saya: { id: 'd3', peran: 'dosen', dtps: false }, pengajuanMhs: ps }, kini)), undefined);
});
