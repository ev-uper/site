// Jadwal kuliah (instal-lengkap.sql, pemilik 2026-11-22).
import test from 'node:test';
import assert from 'node:assert/strict';
import { durasiMenit, masaDariKalender, masukanPenjadwalan, bacaCsvHasil, periksaJadwal, csvJadwal } from '../../site/jadwal-kuliah.js';

const ATURAN = { minutes_per_sks: 50, same_label_break_minutes: 30, electives_no_overlap: true,
  blocked: [{ day: 5, start: '11:30', end: '13:00' }], avoid: [{ day: 'all', start: '12:00', end: '13:00' }], lecturer_daily_max_hours: 6 };
const MK = [
  { kurikulum: 'K26', kode: 'SI201', nama: 'Statika', sks: 3, semester: 2, sifat: 'wajib' },
  { kurikulum: 'K26', kode: 'SI202', nama: 'Hidrologi', sks: 2, semester: 2, sifat: 'wajib' },
  { kurikulum: 'K26', kode: 'SP01', nama: 'Pilihan Satu', sks: 2, semester: null, sifat: 'pilihan' },
  { kurikulum: 'K26', kode: 'SP02', nama: 'Pilihan Dua', sks: 2, semester: null, sifat: 'pilihan' },
];
const KELAS = [
  { id: 1, kurikulum: 'K26', kode_mk: 'SI201', kelas: 'A' }, { id: 2, kurikulum: 'K26', kode_mk: 'SI202', kelas: 'A' },
  { id: 3, kurikulum: 'K26', kode_mk: 'SP01', kelas: 'A' }, { id: 4, kurikulum: 'K26', kode_mk: 'SP02', kelas: 'A' },
  { id: 5, kurikulum: 'K26', kode_mk: 'SI201', kelas: 'B' },
];
const KD = [{ kelas_id: 1, dosen_id: 'd1', urutan: 0 }, { kelas_id: 2, dosen_id: 'd2', urutan: 0 }, { kelas_id: 3, dosen_id: 'd3', urutan: 0 },
  { kelas_id: 4, dosen_id: 'd4', urutan: 0 }, { kelas_id: 5, dosen_id: 'd1', urutan: 0 }, { kelas_id: 5, dosen_id: 'd2', urutan: 1 }];
const SLOT = Array.from({ length: 19 }, (_, i) => ({ id: 100 + i, mulai: `${String(7 + Math.floor(i / 2)).padStart(2, '0')}:${i % 2 ? '30' : '00'}:00`,
  selesai: `${String(7 + Math.floor((i + 1) / 2)).padStart(2, '0')}:${(i + 1) % 2 ? '30' : '00'}:00`, aktif: true }));
const nama = id => ({ d1: 'Dosen Satu', d2: 'Dosen Dua' }[id] || id);

test('duration: sks x 50 minutes rounded up to 30-minute slots (owner 2026-11-22)', () => {
  assert.equal(durasiMenit(2, ATURAN), 120);
  assert.equal(durasiMenit(3, ATURAN), 150);
  assert.equal(durasiMenit(1, ATURAN), 60);
});

test('lecture weeks come from Kalender akademik, kategori perkuliahan, matching semester text', () => {
  const rows = [{ semester: 'Genap  2026/2027', kategori: 'perkuliahan', mulai: '2027-04-05', selesai: '2027-05-28' },
    { semester: 'genap 2026/2027', kategori: 'perkuliahan', mulai: '2027-02-01', selesai: '2027-03-26' },
    { semester: 'Genap 2026/2027', kategori: 'ujian', mulai: '2027-03-29', selesai: '2027-04-02' },
    { semester: 'Ganjil 2026/2027', kategori: 'perkuliahan', mulai: '2026-09-01', selesai: '2026-12-11' }];
  assert.deepEqual(masaDariKalender(rows, '2026/2027', 'Genap'),
    [{ mulai: '2027-02-01', selesai: '2027-03-26' }, { mulai: '2027-04-05', selesai: '2027-05-28' }]);
});

test('input file: format, lecture-week filter, ranges expanded to dates on chosen weekdays, locked times kept', () => {
  const m = masukanPenjadwalan({ ta: '2026/2027', sm: 'Genap', kelas: KELAS, kd: KD, mk: MK,
    dosen: [{ id: 'd1', nama: 'Dosen Satu', nama_gelar: 'Dr. Dosen Satu' }, { id: 'd9', nama: 'Tidak mengajar' }],
    jadwal: [{ kelas_id: 1, hari: 2, mulai: '07:00:00', selesai: '09:30:00', kunci: true }],
    slot: [...SLOT].reverse(), hari: [5, 1, 2, 3, 4],
    berhalangan: [{ dosen_id: 'd1', hari: 1, slot_id: 100 }, { dosen_id: 'd9', hari: 1, slot_id: 100 }],
    tgl: [{ dosen_id: 'd2', tanggal: '2027-02-03', slot_id: null }, { dosen_id: 'd2', tanggal: '2027-06-30', slot_id: 101 }],
    rentang: [{ dosen_id: 'd1', mulai: '2027-01-25', selesai: '2027-02-12', hari: [2], slot_ids: [100, 101] }],
    libur: ['2027-02-09', '2026-12-25'], masa: [{ mulai: '2027-02-01', selesai: '2027-02-28' }], dibuat: 'x' });
  assert.equal(m.format, 'jadwal-masukan-1');
  assert.deepEqual(m.hari, [1, 2, 3, 4, 5]);
  assert.equal(m.slot[0].mulai, '07:00');
  assert.deepEqual(m.dosen, [{ id: 'd1', nama: 'Dr. Dosen Satu' }]);              // hanya dosen yang mengajar
  assert.deepEqual(m.libur, ['2027-02-09']);
  assert.deepEqual(m.berhalangan, [{ dosen: 'd1', hari: 1, slot: 100 }]);
  // rentang Selasa 25 Jan-12 Feb: di masa kuliah hanya 2 dan 9 Feb (libur tetap dicatat, penjalan yang membuangnya)
  assert.deepEqual(m.berhalangan_tanggal.filter(x => x.dosen === 'd1').map(x => `${x.tanggal}/${x.slot}`),
    ['2027-02-02/100', '2027-02-02/101', '2027-02-09/100', '2027-02-09/101']);
  assert.deepEqual(m.berhalangan_tanggal.filter(x => x.dosen === 'd2'), [{ dosen: 'd2', tanggal: '2027-02-03', slot: null }]);
  const k1 = m.kelas.find(k => k.id === 1), k3 = m.kelas.find(k => k.id === 3), k5 = m.kelas.find(k => k.id === 5);
  assert.deepEqual(k1.jadwal, { hari: 2, mulai: '07:00', selesai: '09:30', kunci: true });
  assert.equal(k1.semester_paket, 2);
  assert.equal(k3.pilihan, true);
  assert.equal(k3.semester_paket, null);
  assert.deepEqual(k5.dosen, ['d1', 'd2']);
});

test('import CSV from run_jadwal.py: needed columns, bad rows reported', () => {
  const ok = bacaCsvHasil('﻿kelas_id;hari;mulai;selesai;nama_hari;kode_mk\n1;2;07:00;09:30;Selasa;SI201\n2;9;07:00;08:00;x;y\n3;1;10:00;09:00;;\n');
  assert.deepEqual(ok.baris, [{ kelas_id: 1, hari: 2, mulai: '07:00', selesai: '09:30' }]);
  assert.equal(ok.galat.length, 2);
  assert.match(bacaCsvHasil('kode;kelas\nA;B').galat[0], /Kolom tidak ada: kelas_id, hari, mulai, selesai/);
});

test('check: lecturer, same label + break, electives, room, blocked, weekly unavailability, missing schedule', () => {
  const jadwal = [
    { kelas_id: 1, hari: 1, mulai: '07:00', selesai: '09:30', ruang: 'R101' },
    { kelas_id: 2, hari: 1, mulai: '09:30', selesai: '11:30', ruang: 'r101 ' },      // A sem 2, tanpa jeda
    { kelas_id: 3, hari: 5, mulai: '11:00', selesai: '13:00' },                         // Jumat siang + jam dihindari
    { kelas_id: 4, hari: 5, mulai: '12:00', selesai: '14:00' },                         // pilihan bentrok dengan 3
  ];
  const r = periksaJadwal({ kelas: KELAS, kd: KD, mk: MK, jadwal, slot: SLOT, aturan: ATURAN, nama,
    berhalangan: [{ dosen_id: 'd2', hari: 1, slot_id: 106 }] });                       // d2 Senin 10:00-10:30
  const w = r.wajib.join('\n');
  assert.match(w, /SI201 B: belum berjadwal/);
  assert.match(w, /SI201 A dan SI202 A \(Senin\): kelas A semester 2 hanya berjeda 0 menit \(minimal 30\)/);
  assert.match(w, /SP01 A Jumat 11:00–13:00: kena jam wajib kosong Jumat 11:30–13:00/);
  assert.match(w, /SP01 A dan SP02 A \(Jumat\): MK pilihan K26 bentrok/);
  assert.match(w, /SI202 A Senin 09:30–11:30: Dosen Dua berhalangan mingguan/);
  assert.doesNotMatch(w, /ruang/);                                                     // tidak tumpang: ruang sama boleh
  assert.match(r.anjuran.join('\n'), /SP01 A Jumat 11:00–13:00: memakai jam yang dihindari setiap hari 12:00–13:00/);
  assert.ok(r.perKelas.get(3).length >= 2);
  // ruang ganda dan dosen bentrok
  const r2 = periksaJadwal({ kelas: KELAS.slice(0, 2).concat(KELAS[4]), kd: KD, mk: MK, slot: SLOT, aturan: ATURAN, nama,
    jadwal: [{ kelas_id: 1, hari: 3, mulai: '07:00', selesai: '09:30', ruang: 'Lab A' },
             { kelas_id: 5, hari: 3, mulai: '08:00', selesai: '10:30', ruang: 'lab a' },
             { kelas_id: 2, hari: 4, mulai: '07:00', selesai: '09:00' }] });
  assert.match(r2.wajib.join('\n'), /SI201 A dan SI201 B \(Rabu\): dosen bentrok \(Dosen Satu\)/);
  assert.match(r2.wajib.join('\n'), /ruang Lab A dipakai dua kelas/);
  assert.equal(r2.anjuran.length, 0);
});

test('check: lecturer above daily maximum is a recommendation, wrong length vs sks too', () => {
  const kelas = [1, 2, 3].map(i => ({ id: i, kurikulum: 'K26', kode_mk: 'SI201', kelas: String.fromCharCode(64 + i) }));
  const kd = kelas.map(k => ({ kelas_id: k.id, dosen_id: 'd1', urutan: 0 }));
  const jadwal = [{ kelas_id: 1, hari: 2, mulai: '07:00', selesai: '09:30' }, { kelas_id: 2, hari: 2, mulai: '10:00', selesai: '12:30' },
    { kelas_id: 3, hari: 2, mulai: '13:00', selesai: '15:00' }];
  const r = periksaJadwal({ kelas, kd, mk: MK, jadwal, slot: SLOT, aturan: ATURAN, nama });
  assert.deepEqual(r.wajib, []);
  assert.match(r.anjuran.join('\n'), /Dosen Satu Selasa: mengajar 7 jam \(anjuran maks 6\)/);
  assert.match(r.anjuran.join('\n'), /SI201 C Selasa 13:00–15:00: lama 120 menit, menurut sks 150 menit/);
});

test('share CSV is ordered by day and time with lecturers and room', () => {
  const t = csvJadwal({ kelas: KELAS, kd: KD, mk: MK, nama, jadwal: [
    { kelas_id: 5, hari: 2, mulai: '07:00:00', selesai: '09:30:00', ruang: 'R; 2' }, { kelas_id: 1, hari: 1, mulai: '10:00', selesai: '12:30' }] });
  const b = t.split('\n');
  assert.equal(b[0], 'hari;nama_hari;mulai;selesai;kurikulum;kode_mk;nama_mk;kelas;sks;semester_paket;dosen;ruang');
  assert.equal(b[1], '1;Senin;10:00;12:30;K26;SI201;Statika;A;3;2;Dosen Satu;');
  assert.equal(b[2], '2;Selasa;07:00;09:30;K26;SI201;Statika;B;3;2;Dosen Satu | Dosen Dua;"R; 2"');
});

test('MKU and faculty courses: kept with their time, may have no prodi lecturer, no length check (owner 2026-11-22)', async () => {
  const { usulanKelasAwal, bacaCsvKelas } = await import('../../site/kelas.js');
  const mk = [...MK, { kurikulum: 'K26', kode: 'MKU1', nama: 'Bahasa Inggris', sks: 2, semester: 2, sifat: 'wajib', unit_penyelenggara: 'universitas', pengampu: [] },
    { kurikulum: 'K26', kode: 'FAK1', nama: 'Fisika', sks: 3, semester: 2, sifat: 'wajib', unit_penyelenggara: 'fakultas' }];
  const u = usulanKelasAwal(mk.filter(m => ['MKU1', 'FAK1', 'SI202'].includes(m.kode)), [], []);
  assert.deepEqual(u.baris.map(b => [b.kode_mk, b.dosen.length]), [['MKU1', 0], ['FAK1', 0]]);
  assert.deepEqual(u.tanpaPengampu, ['SI202']);
  const c = bacaCsvKelas('kode_mk;kelas;dosen\nMKU1;A;\nSI202;A;\n', { mk, kurikulumBawaan: 'K26' });
  assert.deepEqual(c.baris.map(b => b.kode_mk), ['MKU1']);
  assert.match(c.galat[0], /Baris 3: dosen kosong/);
  const kelas = [{ id: 7, kurikulum: 'K26', kode_mk: 'MKU1', kelas: 'A' }, { id: 1, kurikulum: 'K26', kode_mk: 'SI201', kelas: 'A' }];
  const jadwal = [{ kelas_id: 7, hari: 1, mulai: '07:00', selesai: '08:40' }, { kelas_id: 1, hari: 1, mulai: '09:00', selesai: '11:30' }];
  const m = masukanPenjadwalan({ ta: '2026/2027', sm: 'Genap', kelas, kd: KD, mk, jadwal, slot: SLOT, hari: [1] });
  assert.equal(m.kelas[0].penyelenggara, 'universitas');
  assert.deepEqual(m.kelas[0].dosen, []);
  // Kelas prodi berlabel sama menghindari MKU dan memberi jeda 30 menit: 08:40 -> 09:00 kurang, 08:40 -> 09:10 cukup.
  const r = periksaJadwal({ kelas, kd: KD, mk, jadwal, slot: SLOT, aturan: ATURAN, nama });
  assert.deepEqual(r.wajib, ['MKU1 A dan SI201 A (Senin): kelas A semester 2 hanya berjeda 20 menit (minimal 30)']);
  jadwal[1] = { kelas_id: 1, hari: 1, mulai: '09:10', selesai: '11:40' };
  const r2 = periksaJadwal({ kelas, kd: KD, mk, jadwal, slot: SLOT, aturan: ATURAN, nama });
  assert.deepEqual(r2.wajib, []);
  assert.doesNotMatch(r2.anjuran.join('\n'), /MKU1 A .*lama/);        // lama MKU (100 menit) tidak dicocokkan dengan sks
});

test('teaching occurrences for the calendar: approved only, own classes, lecture weeks, no holidays (owner 2026-11-22)', async () => {
  const { pertemuanKuliah, rentangSemester } = await import('../../site/jadwal-kuliah.js');
  const { kumpulkanAcara } = await import('../../site/kalender.js');
  assert.deepEqual(rentangSemester('2026/2027', 'Genap'), { mulai: '2027-03-01', selesai: '2027-08-31' });
  assert.deepEqual(rentangSemester('2027/2028', 'Ganjil'), { mulai: '2027-09-01', selesai: '2028-02-29' });
  const kelas = [{ id: 1, tahun_akademik: '2026/2027', semester: 'Genap', kurikulum: 'K26', kode_mk: 'SI201', kelas: 'A' },
    { id: 5, tahun_akademik: '2026/2027', semester: 'Genap', kurikulum: 'K26', kode_mk: 'SI201', kelas: 'B' },
    { id: 9, tahun_akademik: '2027/2028', semester: 'Ganjil', kurikulum: 'K26', kode_mk: 'SI202', kelas: 'A' }];
  const kd = [{ kelas_id: 1, dosen_id: 'd1' }, { kelas_id: 5, dosen_id: 'd2' }, { kelas_id: 9, dosen_id: 'd1' }];
  const jadwal = [{ kelas_id: 1, hari: 1, mulai: '07:00:00', selesai: '09:30:00', ruang: 'R1' }, { kelas_id: 5, hari: 2, mulai: '07:00', selesai: '09:30' },
    { kelas_id: 9, hari: 3, mulai: '07:00', selesai: '09:00' }];
  const sah = [{ tahun_akademik: '2026/2027', semester: 'Genap' }];                 // Ganjil 2027/2028 masih draf
  const kalender = [{ semester: 'Genap 2026/2027', kategori: 'perkuliahan', mulai: '2027-03-01', selesai: '2027-03-21' }];
  const p = pertemuanKuliah({ kelas, kd, mk: MK, jadwal, sah, kalender, libur: [{ tanggal: '2027-03-08' }], dosenId: 'd1' });
  // Senin di 1-21 Maret 2027: 1, 8 (libur), 15
  assert.deepEqual(p.map(x => x.tanggal), ['2027-03-01', '2027-03-15']);
  assert.equal(p[0].judul, 'SI201 Statika (kelas A)');
  assert.equal(p[0].mulai, '07:00');
  assert.equal(p[0].ruang, 'R1');
  // tanpa masa kuliah di Kalender akademik: seluruh semester Genap (Maret-Agustus)
  const semua = pertemuanKuliah({ kelas, kd, mk: MK, jadwal, sah, dosenId: 'd1' });
  assert.equal(semua[0].tanggal, '2027-03-01');
  assert.equal(semua.at(-1).tanggal, '2027-08-30');
  assert.match(semua[0].ket, /masa kuliah belum diisi/);
  const a = kumpulkanAcara({ kuliah: p }, { id: 'd1', peran: 'dosen' }).filter(x => x.sumber === 'kuliah');
  assert.equal(a.length, 2);
  assert.deepEqual([a[0].jamMulai, a[0].jamSelesai, a[0].tempat, a[0].href], ['07:00', '09:30', 'R1', 'jadwal-kuliah.html']);
});
