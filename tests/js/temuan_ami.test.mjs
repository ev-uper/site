// Temuan AMI dan tindak lanjut (owner 2026-11-11; instal-lengkap.sql).
import test from 'node:test';
import assert from 'node:assert/strict';
import { hariKeTenggat, keadaanTenggat, ringkasTemuan, urutTemuan, htmlTemuan, penerimaTemuan,
  buktiPerBaris, KATEGORI_TEMUAN, STATUS_TEMUAN } from '../../site/temuan-ami.js';

const KINI = new Date(2026, 10, 11, 15, 0);   // 11 Nov 2026, sore
const T = [
  { id: 1, kode: 'T-01', uraian: 'RPS <lama>', kategori: 'kts_minor', pihak: 'P', tenggat: '2026-11-01', status: 'proses', tahun_ts: 2026 },
  { id: 2, kode: 'T-02', uraian: 'Tracer rendah', kategori: 'observasi', pihak: 'S', tenggat: '2026-11-20', status: 'terbuka', tahun_ts: 2026,
    pj_nama: 'Bu Ani', pj_email: 'ani@x.id' },
  { id: 3, kode: 'T-03', uraian: 'Lab K3', kategori: 'kts_mayor', pihak: 'F', tenggat: '2027-03-01', status: 'terbuka', tahun_ts: 2026 },
  { id: 4, kode: 'T-04', uraian: 'SOP', kategori: 'peluang', pihak: 'P', tenggat: '2026-10-01', status: 'ditutup', tahun_ts: 2026,
    tanggal_selesai: '2026-09-30', verifikasi: 'efektif' },
];

test('options cover the database check values', () => {
  assert.deepEqual(KATEGORI_TEMUAN.map(x => x[0]).sort(), ['kts_mayor', 'kts_minor', 'observasi', 'peluang']);
  assert.deepEqual(STATUS_TEMUAN.map(x => x[0]), ['terbuka', 'proses', 'selesai', 'ditutup']);
});

test('deadline state uses calendar days and ignores finished rows', () => {
  assert.equal(hariKeTenggat('2026-11-11', KINI), 0);
  assert.equal(hariKeTenggat('2026-11-01', KINI), -10);
  assert.equal(keadaanTenggat(T[0], KINI), 'lewat');
  assert.equal(keadaanTenggat(T[1], KINI), 'dekat');
  assert.equal(keadaanTenggat(T[2], KINI), 'aman');
  assert.equal(keadaanTenggat(T[3], KINI), null);
  assert.equal(keadaanTenggat({ status: 'terbuka' }, KINI), null);
});

test('summary and order', () => {
  const s = ringkasTemuan(T, KINI);
  assert.equal(s.jumlah, 4);
  assert.equal(s.lewat, 1);
  assert.equal(s.dekat, 1);
  assert.equal(s.persenDitutup, 25);
  assert.equal(s.kategori.kts_mayor, 1);
  assert.deepEqual(urutTemuan(T, KINI).map(r => r.kode), ['T-01', 'T-02', 'T-03', 'T-04']);
});

test('table escapes text and shows evidence links', () => {
  const html = htmlTemuan(T, buktiPerBaris([{ baris_id: 1, judul: 'Notulen', url: 'https://contoh.id/n' }]), { kini: KINI });
  assert.match(html, /RPS &lt;lama&gt;/);
  assert.match(html, /lewat 10 hari/);
  assert.match(html, /href="https:\/\/contoh.id\/n"/);
  assert.match(html, /1 lewat tenggat/);
});

test('reminders group by PJ email, else the unit email; rows without email are reported', () => {
  const { penerima, tanpaEmail } = penerimaTemuan(T, { P: 'prodi@x.id' }, KINI);
  assert.deepEqual(penerima.map(p => p.email).sort(), ['ani@x.id', 'prodi@x.id']);
  assert.match(penerima.find(p => p.email === 'prodi@x.id').rinci, /T-01: RPS <lama> \(tenggat 01\/11\/2026, lewat 10 hari/);
  assert.equal(penerima.find(p => p.email === 'ani@x.id').nama, 'Bu Ani');
  assert.equal(tanpaEmail.length, 0);
  assert.equal(penerimaTemuan(T, {}, KINI).tanpaEmail.map(r => r.kode).join(), 'T-01');
});
