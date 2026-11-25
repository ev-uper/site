// Impor kerja sama dari Excel (pemilik 2026-11-24; site/impor-kerjasama.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { bacaKerjasama, rencanaImporKS, tanggalSel, pilihan, JENIS_KS, KOLOM_KS } from '../../site/impor-kerjasama.js';

const JUDUL = KOLOM_KS.map(k => k[1]);
const baris = o => JUDUL.map((_, i) => o[KOLOM_KS[i][0]] ?? null);

test('tanggal: Date, nomor seri Excel, teks ISO dan Indonesia; tanggal mustahil ditolak', () => {
  assert.equal(tanggalSel(new Date(2025, 1, 1)), '2025-02-01');
  // SheetJS kadang memberi sel "1 Feb 2025" sebagai 31 Jan 23:59:40 waktu lokal: tetap dibaca 1 Februari.
  assert.equal(tanggalSel(new Date(2025, 1, 1, 0, 0, -20)), '2025-02-01');
  assert.equal(tanggalSel(45689), '2025-02-01');
  assert.equal(tanggalSel('2025-02-01'), '2025-02-01');
  assert.equal(tanggalSel('1/2/2025'), '2025-02-01');
  assert.equal(tanggalSel('01-02-2025'), '2025-02-01');
  assert.equal(tanggalSel(''), '');
  assert.equal(tanggalSel('31/02/2025'), null);
  assert.equal(tanggalSel('Februari 2025'), null);
});

test('pilihan: kode, label, sinonim; tidak dikenali = null', () => {
  assert.equal(pilihan('PkM', JENIS_KS), 'pkm');
  assert.equal(pilihan(' pendidikan ', JENIS_KS), 'pendidikan');
  assert.equal(pilihan('Magang', JENIS_KS), null);
  assert.equal(pilihan('', JENIS_KS), '');
});

test('baca lembar: judul bertanda * atau keterangan, label pilihan, tahun dari tanggal, baris kosong dilewati', () => {
  const rows = [['Templat kerja sama'], ['Lembaga mitra *', 'Jenis', 'Tingkat (pilih)', ...JUDUL.slice(3), 'Catatan'],
    baris({ mitra: '  PT  Beton  ', jenis: 'Pendidikan', tingkat: 'Wilayah/lokal', tanggal_mulai: new Date(2024, 6, 1), tanggal_selesai: '2027-06-30',
            jenis_bukti: 'Surat Perjanjian Kerjasama (SPK)', sembunyikan_publik: 'Ya' }),
    [],
    baris({ mitra: 'Univ X', jenis: 'pengabdian kepada masyarakat', tingkat: 'Internasional', tahun_mulai: 2023 })];
  const h = bacaKerjasama(rows);
  assert.deepEqual(h.hilang, []);
  assert.deepEqual(h.takDikenal, ['Catatan']);
  assert.equal(h.baris.length, 2);
  assert.deepEqual(h.baris[0], { no: 3, galat: [], data: { mitra: 'PT Beton', jenis: 'pendidikan', tingkat: 'wilayah', tanggal_mulai: '2024-07-01',
    tanggal_selesai: '2027-06-30', tahun_mulai: 2024, tahun_selesai: 2027, jenis_bukti: 'spk', sembunyikan_publik: true } });
  assert.deepEqual(h.baris[1].data, { mitra: 'Univ X', jenis: 'pkm', tingkat: 'internasional', tahun_mulai: 2023, sembunyikan_publik: false });
  assert.equal(h.baris[1].no, 5);
});

test('galat per baris: wajib kosong, pilihan salah, tanggal terbalik, tautan tanpa https, tanpa tanggal/tahun', () => {
  const rows = [JUDUL,
    baris({ mitra: '', jenis: 'Magang', tingkat: 'Nasional', tanggal_mulai: '2025-01-01' }),
    baris({ mitra: 'A', jenis: 'Penelitian', tingkat: 'Nasional', tanggal_mulai: '2025-05-01', tanggal_selesai: '2025-01-01', tautan_bukti: 'drive.google.com/x' }),
    baris({ mitra: 'B', jenis: 'Penelitian', tingkat: 'Nasional' })];
  const g = bacaKerjasama(rows).baris.map(b => b.galat);
  assert.deepEqual(g[0], ['Lembaga mitra kosong', 'Jenis "Magang" tidak dikenali']);
  assert.deepEqual(g[1], ['Tanggal akhir lebih awal dari tanggal awal', 'Tautan bukti harus diawali http:// atau https:// dan tanpa spasi']);
  assert.deepEqual(g[2], ['Isi tanggal awal (atau tahun mulai)']);
  assert.deepEqual(bacaKerjasama([['Nama', 'Alamat']]).tanpaJudul, true);
  assert.deepEqual(bacaKerjasama([['Lembaga mitra', 'Jenis']]).hilang, ['Tingkat']);
});

test('rencana: yang sudah ada dan kembar di berkas dilewati; galat tidak disimpan; tanpa bukti tetap diimpor', () => {
  const rows = [JUDUL,
    baris({ mitra: 'PT Beton', jenis: 'Pendidikan', tingkat: 'Nasional', tanggal_mulai: '2024-07-01' }),
    baris({ mitra: 'pt  beton', jenis: 'Pendidikan', tingkat: 'Nasional', tanggal_mulai: '2024-07-01' }),
    baris({ mitra: 'Univ X', jenis: 'Penelitian', tingkat: 'Internasional', tanggal_mulai: '2023-01-01' }),
    baris({ mitra: 'PT Baru', jenis: 'PkM', tingkat: 'Wilayah/lokal', tahun_mulai: 2025 }),
    baris({ mitra: 'Rusak', jenis: 'PkM', tingkat: '?', tahun_mulai: 2025 })];
  const ada = [{ mitra: 'Univ X', jenis: 'penelitian', tanggal_mulai: '2023-01-01', tahun_mulai: 2023 }];
  const r = rencanaImporKS(bacaKerjasama(rows), ada);
  assert.deepEqual(r.baru.map(x => x.mitra), ['PT Beton', 'PT Baru']);
  assert.deepEqual(r.lewat.map(x => [x.no, x.alasan]), [[3, 'kembar dengan baris sebelumnya di berkas'], [4, 'sudah ada di situs']]);
  assert.deepEqual(r.galat.map(x => x.no), [6]);
  assert.ok(r.baru.every(x => !('tautan_bukti' in x)));
});
