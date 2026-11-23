// Kalender kegiatan prodi (owner 2026-11-12).
import test from 'node:test';
import assert from 'node:assert/strict';
import { kumpulkanAcara, acaraPada, kisiBulan, keIcs } from '../../site/kalender.js';

const DOSEN = { id: 'a', email: 'Ani@x.id', peran: 'dosen' };
const ADMIN = { id: 'z', email: 'adm@x.id', peran: 'admin' };
const DATA = {
  kegiatan: [{ id: 1, judul: 'UAS Ganjil', jenis: 'akademik', mulai: '2026-12-07', selesai: '2026-12-18' },
             { id: 2, judul: 'Kuliah tamu', jenis: 'seminar', mulai: '2026-11-20', jam_mulai: '09:00:00', jam_selesai: '11:30:00', tempat: 'Aula, Gedung A', tautan: 'https://x.id/a' }],
  rapat: [{ id: 7, judul: 'Rapat kurikulum', tanggal: '2026-11-20', mulai: '13:00:00', tempat: 'R. 301' }],
  panggilan: [{ id: 3, judul: 'Hibah BIMA', tenggat: '2026-11-30' }, { id: 4, judul: 'Tanpa tenggat' }],
  hibah: [{ id: 'h1', judul: 'Riset A', status: 'rencana', tenggat_ajuan: '2026-11-25', hibah_tim: [{ dosen_id: 'a' }] },
          { id: 'h2', judul: 'Riset B', status: 'didanai', tenggat_kemajuan: '2026-12-01', kemajuan_selesai: '2026-11-01', tenggat_akhir: '2027-03-01', hibah_tim: [{ dosen_id: 'b' }] }],
  tindak: [{ id: 1, rapat_id: 7, keputusan: 'Revisi RPS', tenggat: '2026-11-28', status: 'terbuka', pj_dosen_id: 'a', rapat: { judul: 'Rapat kurikulum' } },
           { id: 2, rapat_id: 7, keputusan: 'Orang lain', tenggat: '2026-11-28', status: 'proses', pj_dosen_id: 'b' },
           { id: 3, rapat_id: 7, keputusan: 'Selesai', tenggat: '2026-11-28', status: 'selesai', pj_dosen_id: 'a' }],
  temuan: [{ id: 5, kode: 'T1', uraian: 'SOP', tenggat: '2026-12-10', status: 'terbuka', pj_email: 'ani@x.id' },
           { id: 6, kode: 'T2', uraian: 'Lain', tenggat: '2026-12-10', status: 'proses', pj_email: 'budi@x.id' }],
};

test('lecturer sees shared events plus own deadlines only; admin sees every deadline', () => {
  const a = kumpulkanAcara(DATA, DOSEN);
  assert.deepEqual(a.map(x => x.uid), ['kegiatan-2', 'rapat-7', 'hibah-h1-ajuan', 'tindak-1', 'panggilan-3', 'kegiatan-1', 'ami-5']);
  assert.equal(a[0].jamMulai, '09:00');
  assert.equal(a[1].href, 'rapat.html?id=7');
  const b = kumpulkanAcara(DATA, ADMIN).map(x => x.uid);
  assert.ok(b.includes('hibah-h2-akhir') && !b.includes('hibah-h2-kemajuan'));   // progress report already done
  assert.ok(b.includes('tindak-2') && b.includes('ami-6') && !b.includes('tindak-3'));
});

test('multi-day events appear on every day; month grid starts on Monday', () => {
  const a = kumpulkanAcara(DATA, DOSEN);
  assert.deepEqual(acaraPada(a, '2026-12-10').map(x => x.uid), ['kegiatan-1', 'ami-5']);
  const k = kisiBulan(2026, 11);                     // 1 Nov 2026 = Sunday
  assert.equal(k.length, 6);
  assert.deepEqual([k[0][0].iso, k[0][6].iso, k[0][6].bulanIni, k[0][5].bulanIni], ['2026-10-26', '2026-11-01', true, false]);
});

test('ics: all-day end is exclusive, WIB times become UTC, text escaped, long lines folded with CRLF', () => {
  const a = kumpulkanAcara(DATA, DOSEN);
  const ics = keIcs(a, { nama: 'Kegiatan Teknik', domain: 'contoh.id', kini: new Date(Date.UTC(2026, 10, 12, 1, 2, 3)), situs: 'https://s.id/' });
  assert.ok(ics.startsWith('BEGIN:VCALENDAR\r\nVERSION:2.0\r\n') && ics.endsWith('END:VCALENDAR\r\n'));
  assert.ok(!/[^\r]\n/.test(ics));                   // every line break is CRLF
  assert.match(ics, /UID:kegiatan-1@contoh\.id\r\nDTSTAMP:20261112T010203Z\r\nDTSTART;VALUE=DATE:20261207\r\nDTEND;VALUE=DATE:20261219/);
  assert.match(ics, /DTSTART:20261120T020000Z\r\nDTEND:20261120T043000Z/);      // 09:00-11:30 WIB
  assert.match(ics, /UID:rapat-7@contoh\.id[\s\S]*?DTSTART:20261120T060000Z\r\nDTEND:20261120T070000Z/);   // no end time = 1 hour
  assert.match(ics, /LOCATION:Aula\\, Gedung A/);
  assert.match(ics, /URL:https:\/\/s\.id\/rapat\.html\?id=7/);
  const panjang = keIcs([{ uid: 'x', sumber: 'kegiatan', judul: 'é'.repeat(80), mulai: '2026-01-01', selesai: '2026-01-01' }]);
  for (const baris of panjang.split('\r\n')) assert.ok(new TextEncoder().encode(baris).length <= 75, baris);
  assert.match(panjang, /\r\n é/);
});
