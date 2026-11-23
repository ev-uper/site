// Rapat dan notulen terstruktur (owner 2026-11-12; instal-lengkap.sql).
import test from 'node:test';
import assert from 'node:assert/strict';
import { JENIS_RAPAT, jenisRapat, tanggalPanjang, waktuRapat, tokenBaru, tindakTerbuka, penerimaTindak, ringkasTindak,
  saranBukti, isiNotulen, namaBerkasNotulen } from '../../site/rapat.js';
import { UNSUR_BUTIR } from '../../site/unsur-butir.js';

const KINI = new Date(2026, 10, 12);   // Kamis 12 Nov 2026

test('meeting kinds suggest the evidence items that ask for minutes; every suggestion exists in UNSUR_BUTIR', () => {
  assert.equal(jenisRapat('tinjauan_cpl').nama, 'Tinjauan CPL');
  assert.equal(jenisRapat('tidak-ada').id, 'lainnya');
  for (const j of JENIS_RAPAT) for (const [b, u] of j.saran) assert.ok(UNSUR_BUTIR[String(b)]?.unsur?.[u], `${j.id}: butir ${b} unsur ${u}`);
  const s = saranBukti('tinjau_vmts', UNSUR_BUTIR);
  assert.deepEqual(s.map(x => [x.butir, x.unsur]), [[1, 4], [2, 1]]);
  assert.match(s[0].label, /Notulen\/berita acara tinjau ulang VMTS/);
});

test('dates and times read naturally', () => {
  assert.equal(tanggalPanjang('2026-11-12'), 'Kamis, 12 November 2026');
  assert.equal(waktuRapat({ mulai: '09:00:00', selesai: '11:30:00' }), '09:00–11:30 WIB');
  assert.equal(waktuRapat({}), '');
});

test('attendance token: 40 hex characters', () => {
  const t = tokenBaru(n => n.fill(171));
  assert.equal(t, 'ab'.repeat(20));
  assert.match(tokenBaru(), /^[0-9a-f]{40}$/);
});

const T = [
  { id: 1, keputusan: 'Revisi CPL-3', status: 'terbuka', tenggat: '2026-11-20', rapat: { judul: 'Tinjauan CPL', tanggal: '2026-11-01' }, pj: { nama: 'Ani', email: 'ani@x.id' } },
  { id: 2, keputusan: 'Unggah RPS', status: 'proses', tenggat: '2026-11-02', rapat: { judul: 'Rapat prodi', tanggal: '2026-10-01' }, pj: { nama: 'Ani', email: 'ani@x.id' } },
  { id: 3, keputusan: 'Kelak', status: 'terbuka', tenggat: '2027-03-01', rapat: { judul: 'R' }, pj: { nama: 'Budi', email: 'budi@x.id' } },
  { id: 4, keputusan: 'Sudah', status: 'selesai', tenggat: '2026-11-01', pj: { nama: 'Budi', email: 'budi@x.id' } },
  { id: 5, keputusan: 'Tanpa PJ berpemail', status: 'terbuka', tenggat: '2026-11-13', pj: { nama: 'Tamu' } },
  { id: 6, keputusan: 'Tanpa tenggat', status: 'terbuka' },
];

test('reminders: open items overdue or due within 14 days, grouped per PJ; missing email reported', () => {
  const { penerima, tanpaEmail } = penerimaTindak(T, KINI);
  assert.deepEqual(penerima.map(p => p.email), ['ani@x.id']);
  assert.match(penerima[0].rinci, /Unggah RPS .*lewat 10 hari/);
  assert.match(penerima[0].rinci, /Revisi CPL-3 .*8 hari lagi/);
  assert.deepEqual(tanpaEmail.map(t => t.id), [5]);
});

test('summary for Monitoring: counts per status, overdue, open items soonest first', () => {
  const r = ringkasTindak(T, KINI);
  assert.deepEqual([r.terbuka, r.proses, r.selesai, r.batal, r.lewat], [4, 1, 1, 0, 1]);
  assert.deepEqual(r.buka.map(t => t.id), [2, 5, 1, 3, 6]);
  assert.deepEqual(tindakTerbuka([{ status: 'batal' }], KINI), []);
});

test('minutes body: header, attendees present only, agenda lines, decisions in order, signature, draft mark, escaping', () => {
  const R = { judul: 'Tinjauan CPL <2026>', jenis: 'tinjauan_cpl', tanggal: '2026-11-12', mulai: '09:00', selesai: '11:00', tempat: 'R. 301',
    pimpinan: 'Kaprodi', notulis: 'Sekprodi', agenda: 'Capaian CPL\nRencana perbaikan', pembahasan: 'CPL-3 rendah', status: 'draf' };
  const P = [{ nama: 'Ani', dosen_id: 'a', peran: 'pimpinan', hadir: true }, { nama: 'Pak Industri', instansi: 'PT X', cara: 'daring', hadir: true },
             { nama: 'Absen', hadir: false }];
  const x = isiNotulen(R, P, [{ urutan: 2, keputusan: 'Kedua', pj_nama: 'Budi', status: 'terbuka' }, { urutan: 1, keputusan: 'Pertama', tenggat: '2026-12-01', status: 'selesai' }],
    { prodi: 'Teknik Contoh', institusi: 'Univ Contoh' });
  assert.ok(x.includes('NOTULEN RAPAT') && x.includes('TEKNIK CONTOH · UNIV CONTOH'));
  assert.ok(x.includes('Tinjauan CPL &lt;2026&gt;') && !x.includes('<2026>'));
  assert.ok(x.includes('Kamis, 12 November 2026') && x.includes('09:00–11:00 WIB') && x.includes('2 orang'));
  assert.ok(x.includes('PT X') && x.includes('daftar hadir daring') && x.includes('Pimpinan rapat') && !x.includes('Absen'));
  assert.ok(x.indexOf('>Capaian CPL<') < x.indexOf('>Rencana perbaikan<'));
  assert.ok(x.indexOf('Pertama') < x.indexOf('Kedua') && x.includes('01/12/2026') && x.includes('Selesai'));
  assert.ok(x.includes('DRAF, belum final'));
  assert.equal(namaBerkasNotulen(R), 'Notulen_2026-11-12_Tinjauan_CPL_2026.docx');
});
