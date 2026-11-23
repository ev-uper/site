// Masa berlaku MoU/SK/dokumen (owner 2026-11-11; instal-lengkap.sql).
import test from 'node:test';
import assert from 'node:assert/strict';
import { daftarBerlaku, penerimaBerlaku, htmlBerlaku, selisihHari, HARI_SEGERA } from '../../site/masa-berlaku.js';

const KINI = new Date(2026, 10, 11, 16, 0);
const S = {
  kerjasama: [
    { mitra: 'PT A', jenis: 'penelitian', tanggal_selesai: '2026-12-31' },     // 50 hari: segera
    { mitra: 'PT B', jenis: 'pkm', tahun_selesai: 2028 },                       // aman, perkiraan akhir tahun
    { mitra: 'PT C', tanggal_selesai: '2024-01-01' },                           // > 1 tahun lalu: dibuang
    { mitra: 'PT D' },                                                          // tanpa tanggal: dibuang
  ],
  karyaKS: [{ judul: 'Survei banjir', mitra_institusi: 'BPBD', selesai_ks: '2026-10-01',
    karya_penulis: [{ dosen: { nama: 'Adi', email: 'adi@x.id' } }, { dosen: { nama: 'Tanpa', email: null } }] }],
  prodiUpps: [{ nama_prodi: 'Teknik Contoh', nomor_sk: '123/SK', tanggal_kedaluwarsa: '2027-02-01' }],
  petaJalan: [{ judul: 'Peta jalan penelitian', tahun_selesai: 2026 }],
  dokumen: [{ jenis: 'sk_unit_pm', tahun: 2024, judul: 'SK GPM', berlaku_sampai: '2026-11-11' }, { jenis: 'statuta', tahun: 2020 }],
  tautanAmi: [{ judul: 'AMI 2026', sampai: '2027-01-11T10:00:00Z' }, { judul: 'Lama', sampai: '2026-12-01T00:00:00Z', dicabut: true }],
};
const D = daftarBerlaku(S, KINI);

test('day difference is by calendar date', () => {
  assert.equal(selisihHari('2026-11-11', KINI), 0);
  assert.equal(selisihHari('2026-12-31', KINI), 50);
  assert.equal(selisihHari('2026-10-01', KINI), -41);
});

test('collects every source, drops old and undated rows, sorts by date', () => {
  assert.deepEqual(D.map(x => x.sumber), ['Kerja sama di karya', 'Dokumen', 'Kerja sama', 'Peta jalan',
    'Tautan AMI', 'SK akreditasi prodi', 'Kerja sama']);
  assert.deepEqual(D.map(x => x.keadaan), ['lewat', 'segera', 'segera', 'segera', 'segera', 'segera', 'aman']);
  assert.equal(D.find(x => x.sumber === 'Peta jalan').perkiraan, true);
  assert.equal(D.find(x => x.label.startsWith('PT B')).sampai, '2028-12-31');
  assert.ok(!D.some(x => x.label === 'Lama'));                 // revoked AMI link
  assert.equal(D.find(x => x.sumber === 'SK akreditasi prodi').hari <= HARI_SEGERA, true);
});

test('recipients: unit items to the Prodi email, partnership in a work to its authors', () => {
  const p = penerimaBerlaku(D, 'prodi@x.id', 'Prodi');
  assert.deepEqual(p.map(x => x.email).sort(), ['adi@x.id', 'prodi@x.id']);
  assert.match(p.find(x => x.email === 'adi@x.id').rinci, /BPBD — Survei banjir — berakhir 01\/10\/2026 \(41 hari lalu\)/);
  assert.equal(p.find(x => x.email === 'prodi@x.id').rinci.split('\n').length, 5);
  assert.deepEqual(penerimaBerlaku(D, '', 'Prodi').map(x => x.email), ['adi@x.id']);
});

test('table hides long-valid rows by class and escapes text', () => {
  const html = htmlBerlaku(daftarBerlaku({ kerjasama: [{ mitra: '<PT>', tanggal_selesai: '2030-01-01' }] }, KINI));
  assert.match(html, /class="aman"/);
  assert.match(html, /&lt;PT&gt;/);
  assert.match(htmlBerlaku([]), /Belum ada tanggal berakhir/);
});
