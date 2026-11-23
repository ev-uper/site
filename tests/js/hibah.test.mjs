// Pelacak pengajuan hibah (owner 2026-11-11; instal-lengkap.sql).
import test from 'node:test';
import assert from 'node:assert/strict';
import { judulNorm, juta, tenggatBerikut, penerimaHibah, panggilanTerbuka, penerimaPanggilan,
  karyaDariHibah, rekapHibah, rasio, htmlRekap, timUrut } from '../../site/hibah.js';

const KINI = new Date(2026, 10, 11);      // 11 Nov 2026
const ani = { nama: 'Ani', email: 'ani@x.id' }, budi = { nama: 'Budi', email: 'budi@x.id' };
const tim = [{ peran: 'anggota', dosen_id: 'b', dosen: budi }, { peran: 'ketua', dosen_id: 'a', dosen: ani }];

test('title normalisation matches karya.judul_norm', () => {
  assert.equal(judulNorm('  Riset  Banjir: Ciliwung–Cisadane! '), 'riset banjir ciliwung cisadane ');
  assert.equal(judulNorm('A&B'), 'a b');
});

test('million rupiah', () => {
  assert.equal(juta(75500000), '75,5');
  assert.equal(juta(null), '—');
});

test('next deadline: proposal while planned, then progress and final report while funded', () => {
  assert.deepEqual(tenggatBerikut({ status: 'rencana', tenggat_ajuan: '2026-11-20' }, KINI).hari, 9);
  assert.equal(tenggatBerikut({ status: 'rencana', tenggat_ajuan: '2026-11-20', tanggal_ajuan: '2026-11-10' }, KINI), null);
  assert.equal(tenggatBerikut({ status: 'didanai', tenggat_kemajuan: '2026-11-01', tenggat_akhir: '2026-12-31' }, KINI).jenis, 'kemajuan');
  assert.equal(tenggatBerikut({ status: 'didanai', tenggat_kemajuan: '2026-11-01', kemajuan_selesai: '2026-10-30', tenggat_akhir: '2026-12-31' }, KINI).jenis, 'akhir');
  assert.equal(tenggatBerikut({ status: 'ditolak', tenggat_ajuan: '2026-11-20' }, KINI), null);
});

test('reminders go to the team leader, within 14 days; overdue reports included, overdue proposals not', () => {
  const A = [
    { judul: 'P1', status: 'rencana', tenggat_ajuan: '2026-11-20', hibah_tim: tim },
    { judul: 'P2', status: 'rencana', tenggat_ajuan: '2026-12-20', hibah_tim: tim },      // 39 days: too early
    { judul: 'P3', status: 'rencana', tenggat_ajuan: '2026-11-01', hibah_tim: tim },      // passed
    { judul: 'L1', status: 'didanai', tenggat_kemajuan: '2026-11-01', hibah_tim: tim },   // 10 days late
    { judul: 'L2', status: 'didanai', tenggat_akhir: '2026-11-15', hibah_tim: [{ peran: 'anggota', dosen: budi }] },  // no leader: whole team
    { judul: 'L3', status: 'didanai', tenggat_akhir: '2026-11-15', hibah_tim: [{ peran: 'ketua', dosen: { nama: 'X' } }] },
  ];
  const p = penerimaHibah(A, 'pengajuan', KINI);
  assert.deepEqual(p.penerima.map(x => x.email), ['ani@x.id']);
  assert.match(p.penerima[0].rinci, /P1 \(Kirim proposal: 20\/11\/2026, 9 hari lagi\)/);
  const l = penerimaHibah(A, 'laporan', KINI);
  assert.deepEqual(l.penerima.map(x => x.email).sort(), ['ani@x.id', 'budi@x.id']);
  assert.match(l.penerima.find(x => x.email === 'ani@x.id').rinci, /L1 \(Laporan kemajuan: 01\/11\/2026, lewat 10 hari\)/);
  assert.deepEqual(l.tanpaEmail.map(x => x.judul), ['L3']);
});

test('calls: open ones, nearest first; announcement lists new calls to every active non-assessor', () => {
  const P = [{ id: 1, judul: 'Lama', tenggat: '2026-10-01' }, { id: 2, judul: 'Dua', tenggat: '2026-12-01', diumumkan: '2026-11-01' },
    { id: 3, judul: 'Tiga', tenggat: '2026-11-25', penyelenggara: 'DPPM', kategori: 'penelitian', tautan: 'https://x.id' }, { id: 4, judul: 'Tanpa tenggat' }];
  assert.deepEqual(panggilanTerbuka(P, KINI).map(p => p.id), [3, 2, 4]);
  const D = [{ nama: 'A', email: 'a@x.id', peran: 'dosen' }, { nama: 'S', email: 's@x.id', peran: 'asesor' },
    { nama: 'N', email: 'n@x.id', peran: 'dosen', aktif: false }, { nama: 'K', peran: 'dosen' }];
  const u = penerimaPanggilan(D, P, KINI);
  assert.deepEqual(u.penerima.map(x => x.email), ['a@x.id']);
  assert.deepEqual(u.panggilan.map(p => p.id), [3, 4]);
  assert.match(u.penerima[0].rinci, /- Tiga \(DPPM\), Penelitian, tenggat 25\/11\/2026\n  https:\/\/x\.id/);
  assert.deepEqual(penerimaPanggilan(D, [P[1]], KINI).panggilan.map(p => p.id), [2]);   // all announced: repeat open ones
  assert.deepEqual(penerimaPanggilan(D, [P[0]], KINI).penerima, []);
});

test('funded proposal becomes a draft karya with the team as authors', () => {
  const a = { status: 'didanai', kategori: 'pkm', judul: ' Abdimas ', skema_kode: 'internal_pkm', tahun_mulai: 2026,
    dana_disetujui: 15000000, nama_pemberi_dana: 'LPPM', hibah_tim: tim };
  const { karya, penulis } = karyaDariHibah(a, 'pelapor');
  assert.deepEqual(karya, { kategori: 'pkm', judul: 'Abdimas', tahun: 2026, skema_kode: 'internal_pkm', nama_pemberi_dana: 'LPPM',
    besaran_dana: 15000000, status: 'draf', dilaporkan_oleh: 'pelapor' });
  assert.deepEqual(penulis.map(p => [p.dosen_id, p.peran]), [['a', 'ketua'], ['b', 'anggota']]);
  assert.match(karyaDariHibah({ ...a, status: 'diajukan' }).galat, /didanai/);
  assert.match(karyaDariHibah({ ...a, skema_kode: null }).galat, /skema/);
  assert.match(karyaDariHibah({ ...a, tahun_mulai: null }).galat, /tahun/);
  assert.match(karyaDariHibah({ ...a, karya_id: 'k' }).galat, /sudah tertaut/);
  assert.deepEqual(timUrut(a).map(t => t.dosen.nama), ['Ani', 'Budi']);
});

test('summary: success rate counts decided proposals only; plans and cancellations carry no money', () => {
  const rows = [
    { tahun: 2025, kategori: 'penelitian', skema: 'Fundamental', kelompok: 'DPPM', status: 'didanai', n: 2, dana_usulan: 200e6, dana_disetujui: 150e6 },
    { tahun: 2025, kategori: 'penelitian', skema: 'Fundamental', kelompok: 'DPPM', status: 'ditolak', n: 2, dana_usulan: 180e6, dana_disetujui: 0 },
    { tahun: 2026, kategori: 'pkm', skema: 'Internal', kelompok: '', status: 'diajukan', n: 1, dana_usulan: 10e6, dana_disetujui: 0 },
    { tahun: 2026, kategori: 'pkm', skema: 'Internal', kelompok: '', status: 'rencana', n: 3, dana_usulan: 99e6, dana_disetujui: 0 },
  ];
  const R = rekapHibah(rows);
  assert.deepEqual(R.tahun.map(g => g.tahun), [2026, 2025]);
  assert.equal(rasio(R.tahun[1]), 0.5);
  assert.equal(rasio(R.tahun[0]), null);
  assert.equal(R.total.usulan, 390e6);
  assert.equal(R.total.disetujui, 150e6);
  assert.equal(R.skema[0].skema, 'Fundamental');
  const h = htmlRekap(rows);
  assert.match(h, /<b>5<\/b> proposal diajukan, <b>2<\/b> didanai/);
  assert.match(h, /3 masih rencana/);
  assert.match(h, /Tingkat keberhasilan <b>50%<\/b>/);
  assert.match(htmlRekap([]), /Belum ada proposal/);
});
