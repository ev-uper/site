// "Tugas saya" di Ruang kerja (owner 2026-11-12).
import test from 'node:test';
import assert from 'node:assert/strict';
import { tugasSaya } from '../../site/tugas-saya.js';

const KINI = new Date(2026, 10, 12);
const SAYA = { id: 'a', nama: 'Ani', email: 'Ani@x.id', peran: 'dosen', aktif: true, sinta_id: '1', orcid: '', topik_keahlian: ['AIR02'] };
const P = id => [{ dosen_id: id }];
const DATA = {
  saya: SAYA,
  karya: [
    { id: 1, judul: 'Draf A', status: 'draf', dilaporkan_oleh: 'a', karya_penulis: [] },
    { id: 2, judul: 'Ditolak B', status: 'ditolak', catatan: 'DOI salah', karya_penulis: P('a') },
    { id: 3, judul: 'Tanpa bukti C', status: 'terverifikasi', karya_penulis: P('a') },
    { id: 4, judul: 'Bukti terpisah D', status: 'terverifikasi', karya_penulis: P('a') },
    { id: 5, judul: 'Milik orang lain', status: 'ditolak', karya_penulis: P('b') },
  ],
  berBukti: new Set([4]),
  bkd: [{ tahun_akademik: '2025/2026', semester: 'genap', verifikasi: 'ditolak', catatan: 'Lampiran kurang' },
        { tahun_akademik: '2025/2026', semester: 'ganjil', verifikasi: 'terverifikasi' }],
  tindak: [
    { id: 1, rapat_id: 7, keputusan: 'Revisi RPS', tenggat: '2026-11-05', status: 'terbuka', pj_dosen_id: 'a', rapat: { judul: 'Rapat kurikulum', tanggal: '2026-10-01' } },
    { id: 2, rapat_id: 7, keputusan: 'Sudah', tenggat: '2026-11-05', status: 'selesai', pj_dosen_id: 'a', rapat: {} },
    { id: 3, rapat_id: 7, keputusan: 'Orang lain', tenggat: '2026-11-05', status: 'terbuka', pj_dosen_id: 'b', rapat: {} },
  ],
  hibah: [
    { judul: 'Hibah X', status: 'rencana', tenggat_ajuan: '2026-11-20', hibah_tim: [{ dosen_id: 'a', peran: 'ketua' }] },
    { judul: 'Hibah lama', status: 'didanai', tenggat_akhir: '2024-01-01', hibah_tim: [{ dosen_id: 'a' }] },
  ],
  temuan: [{ kode: 'T1', siklus: '2026', uraian: 'SOP belum ada', status: 'proses', tenggat: '2027-01-30', pj_email: 'ani@x.id' },
           { kode: 'T2', uraian: 'Selesai', status: 'ditutup', pj_email: 'ani@x.id' }],
  kelasCpl: [{ id: 10, tahun_akademik: '2025/2026', semester: 'Genap', kode_mk: 'SI101', nama_mk: 'Hidrologi', kelas: 'A' },
             { id: 11, tahun_akademik: '2025/2026', semester: 'Genap', kode_mk: 'SI102', kelas: 'B' }],
  berkasCpl: [{ kelas_id: 11 }],
};

test('collects own tasks from every source, overdue first', () => {
  const t = tugasSaya(DATA, KINI);
  assert.deepEqual(t.map(x => x.jenis), ['rapat', 'hibah', 'ami', 'profil', 'karya', 'karya', 'karya', 'bkd', 'cpl']);
  assert.equal(t[0].tingkat, 'lewat');
  assert.equal(t[0].href, 'rapat.html?id=7');
  assert.match(t[0].rinci, /lewat 7 hari/);
  assert.equal(t[1].tingkat, 'dekat');
  assert.match(t[1].judul, /Kirim proposal: Hibah X/);
  assert.equal(t[2].href, '');                       // admin changes AMI status: no link
  assert.match(t[2].rinci, /Laporkan perkembangannya/);
  assert.equal(t[3].rinci, 'ORCID');
  assert.match(t[4].judul, /1 draf karya/);
  assert.match(t[5].rinci, /Ditolak B \(catatan admin: DOI salah\)/);
  assert.match(t[6].rinci, /^Tanpa bukti C$/);
  assert.match(t[7].rinci, /Lampiran kurang/);
  assert.equal(t[7].href, 'karya.html#bkd');
  assert.match(t[8].judul, /SI101 kelas A/);
  const semua = JSON.stringify(t);
  assert.ok(!semua.includes('Milik orang lain') && !semua.includes('Orang lain') && !semua.includes('Hibah lama') && !semua.includes('Selesai'));
});

test('assessors have no tasks; non-DTPS staff get no profile reminder; nothing pending = empty', () => {
  assert.deepEqual(tugasSaya({ ...DATA, saya: { ...SAYA, peran: 'asesor' } }, KINI), []);
  assert.ok(!tugasSaya({ ...DATA, saya: { ...SAYA, dtps: false } }, KINI).some(x => x.jenis === 'profil'));
  assert.deepEqual(tugasSaya({ saya: { id: 'z', peran: 'dosen', sinta_id: '1' } }, KINI), []);
});
