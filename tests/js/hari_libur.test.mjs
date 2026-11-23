// Hari libur (instal-lengkap.sql, pemilik 2026-11-21): site/hari-libur.js dan sumber "libur" di kalender.js.
import test from 'node:test';
import assert from 'node:assert/strict';
import { petaLibur, tanpaLibur, tanggalAntara, isoDariTeks, jenisDariTeks, bacaCsvLibur, csvLibur, RENTANG_MAKS } from '../../site/hari-libur.js';
import { kumpulkanAcara, keIcs } from '../../site/kalender.js';

test('peta dan penyaring tanggal libur', () => {
  const p = petaLibur([{ tanggal: '2026-12-25', nama: 'Natal', jenis: 'nasional' }, { tanggal: '2026-12-26T00:00:00', nama: 'Cuti', jenis: 'cuti_bersama' }]);
  assert.equal(p.get('2026-12-26').jenis, 'cuti_bersama');
  assert.deepEqual(tanpaLibur(['2026-12-24', '2026-12-25', '2026-12-26', '2026-12-28'], p), ['2026-12-24', '2026-12-28']);
  assert.deepEqual(tanpaLibur(['2026-12-25'], null), ['2026-12-25']);
});

test('rentang tanggal: inklusif, lintas bulan, batas, galat', () => {
  assert.deepEqual(tanggalAntara('2026-12-30', '2027-01-02').tanggal, ['2026-12-30', '2026-12-31', '2027-01-01', '2027-01-02']);
  assert.deepEqual(tanggalAntara('2026-12-25').tanggal, ['2026-12-25']);
  assert.match(tanggalAntara('2026-12-25', '2026-12-24').galat, /sebelum/);
  assert.match(tanggalAntara('2026-02-30').galat, /tidak sah/);
  assert.equal(tanggalAntara('2026-01-01', '2026-01-31').tanggal.length, RENTANG_MAKS);
  assert.match(tanggalAntara('2026-01-01', '2026-02-01').galat, /paling lama/);
});

test('teks tanggal dan jenis', () => {
  assert.equal(isoDariTeks('25/12/2026'), '2026-12-25');
  assert.equal(isoDariTeks('1-5-2027'), '2027-05-01');
  assert.equal(isoDariTeks('2027-5-1'), '2027-05-01');
  assert.equal(isoDariTeks('31/02/2027'), '');
  assert.equal(jenisDariTeks(''), 'nasional');
  assert.equal(jenisDariTeks('Cuti Bersama'), 'cuti_bersama');
  assert.equal(jenisDariTeks('libur_kampus'), 'kampus');
  assert.equal(jenisDariTeks('bebas'), '');
});

test('CSV: judul dilewati, ; atau , , kutip, galat per baris, tanggal ganda = terakhir, bolak-balik', () => {
  const r = bacaCsvLibur('﻿tanggal;nama;jenis\r\n25/12/2026;Hari Raya Natal;nasional\n2026-12-24;"Cuti; Natal";cuti bersama\n'
    + '2026-13-01;Salah;\n2026-12-31;X;\n2026-12-30;Coba;bebas\n2026-12-25;Natal;');
  assert.deepEqual(r.baris, [{ tanggal: '2026-12-24', nama: 'Cuti; Natal', jenis: 'cuti_bersama' }, { tanggal: '2026-12-25', nama: 'Natal', jenis: 'nasional' }]);
  assert.equal(r.galat.length, 3);
  assert.match(r.galat[0], /^baris 4: tanggal/);
  assert.match(r.galat[1], /^baris 5: nama/);
  assert.match(r.galat[2], /^baris 6: jenis/);
  assert.deepEqual(bacaCsvLibur('2027-01-01,Tahun Baru Masehi,nasional').baris, [{ tanggal: '2027-01-01', nama: 'Tahun Baru Masehi', jenis: 'nasional' }]);
  const t = csvLibur(r.baris);
  assert.equal(t, 'tanggal;nama;jenis\r\n2026-12-24;"Cuti; Natal";cuti_bersama\r\n2026-12-25;Natal;nasional\r\n');
  assert.deepEqual(bacaCsvLibur(t).baris, r.baris);
  assert.deepEqual(bacaCsvLibur('').galat, ['Berkas kosong.']);
});

test('kalender: hari libur tampil untuk semua dan masuk .ics sepanjang hari', () => {
  const a = kumpulkanAcara({ libur: [{ tanggal: '2026-12-25', nama: 'Hari Raya Natal', jenis: 'nasional' }] }, { id: 'x', peran: 'dosen' });
  assert.deepEqual(a.map(x => [x.uid, x.sumber, x.judul, x.mulai, x.selesai, x.ket]),
    [['libur-2026-12-25', 'libur', 'Hari Raya Natal', '2026-12-25', '2026-12-25', 'Libur nasional']]);
  const ics = keIcs(a, { kini: new Date('2026-11-21T00:00:00Z') });
  assert.match(ics, /DTSTART;VALUE=DATE:20261225\r\nDTEND;VALUE=DATE:20261226/);
  assert.match(ics, /CATEGORIES:Hari libur/);
});
