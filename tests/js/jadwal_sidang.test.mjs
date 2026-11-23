// Pemeriksaan jadwal seminar/sidang TA (pemilik 2026-11-22).
import test from 'node:test';
import assert from 'node:assert/strict';
import { bacaJam, formatJam, sibukSidang, gabungSibuk, periksaWaktu } from '../../site/jadwal-sidang.js';

const SLOT = [{ id: 1, mulai: '07:00:00', selesai: '08:40:00' }, { id: 2, mulai: '08:50:00', selesai: '10:30:00' },
  { id: 3, mulai: '10:40:00', selesai: '12:20:00' }, { id: 4, mulai: '13:00:00', selesai: '14:40:00' }];
const DOSEN = [{ id: 'a', nidn: '001', nama: 'Dosen A' }, { id: 'b', nidn: '002', nama: 'Dosen B' }, { id: 'c', nidn: '003', nama: 'Dosen C' }];
const nama = id => DOSEN.find(d => d.id === id)?.nama || id;
const JADWAL = [
  { pengajuan_id: 10, tahap: 'seminar_proposal', tanggal: '2027-03-02', jam: '09.00–10.30', status: 'terjadwal', pembimbing: ['001'], penguji: ['002'] },
  { pengajuan_id: 11, tahap: 'sidang_akhir', tanggal: '2027-03-02', jam: '13:00', status: 'batal', pembimbing: ['003'], penguji: [] },
  { pengajuan_id: 12, tahap: 'sidang_akhir', tanggal: '2027-03-02', jam: 'pagi', status: 'terjadwal', pembimbing: ['003'], penguji: [] },
  { pengajuan_id: 99, tahap: 'sidang_akhir', tanggal: '2027-03-02', jam: '07.00-08.00', status: 'terjadwal', pembimbing: ['001'], penguji: [] },
];

test('free-text times are read in the common forms', () => {
  assert.deepEqual(bacaJam('09.00–10.30'), { mulai: 540, selesai: 630 });
  assert.deepEqual(bacaJam('9:00 - 10:30 WIB'), { mulai: 540, selesai: 630 });
  assert.deepEqual(bacaJam('09.00 s.d. 10.30'), { mulai: 540, selesai: 630 });
  assert.deepEqual(bacaJam('13.00', 90), { mulai: 780, selesai: 870 });
  assert.equal(bacaJam('pagi'), null);
  assert.equal(formatJam(540, 630), '09.00–10.30');
});

test('other TA sessions become busy slots; cancelled ones and the session being scheduled are skipped', () => {
  const s = sibukSidang({ jadwal: JADWAL, slot: SLOT, dosen: DOSEN, tanggal: ['2027-03-02'], kecuali: 99 });
  // 09.00-10.30 kena slot 2 (08.50-10.30) saja; sidang 11 batal; 12 jam tak terbaca; 99 = pengajuan yang dijadwalkan
  assert.deepEqual(s, [{ tanggal: '2027-03-02', slot_id: 2, n: 2, dosen: ['a', 'b'] }]);
  const g = gabungSibuk([{ tanggal: '2027-03-02', slot_id: 2, n: 1, dosen: ['c'] }, { tanggal: '2027-03-02', slot_id: 3, n: 1, dosen: ['a'] }], s);
  assert.deepEqual(g.find(x => x.slot_id === 2), { tanggal: '2027-03-02', slot_id: 2, n: 3, dosen: ['c', 'a', 'b'] });
  assert.equal(gabungSibuk([{ tanggal: 't', slot_id: 1, n: 2, dosen: null }], [{ tanggal: 't', slot_id: 1, n: 1, dosen: ['a'] }])[0].n, 2);
});

test('check at a chosen time: who clashes and why', () => {
  const r = periksaWaktu({ tanggal: '2027-03-02', mulai: 600, selesai: 690, slot: SLOT, jadwal: JADWAL, dosen: DOSEN, nama,
    peserta: ['a', 'c'], kecuali: 99, sibukRapat: [{ tanggal: '2027-03-02', slot_id: 3, n: 1, dosen: ['c'] }] });
  assert.deepEqual(r.bentrok, [{ id: 'a', nama: 'Dosen A', sebab: ['seminar proposal lain 09.00–10.30'] },
    { id: 'c', nama: 'Dosen C', sebab: ['berhalangan, mengajar, atau rapat'] }]);
  assert.match(r.tidakTerbaca[0], /jam "pagi" tidak terbaca/);
  const bebas = periksaWaktu({ tanggal: '2027-03-02', mulai: 780, selesai: 870, slot: SLOT, jadwal: JADWAL, dosen: DOSEN, nama, peserta: ['a', 'b'],
    sibukRapat: [] });
  assert.deepEqual(bebas.bentrok, []);
  // pengguna bukan pengatur jadwal: hanya jumlah
  const anonim = periksaWaktu({ tanggal: '2027-03-02', mulai: 780, selesai: 870, slot: SLOT, jadwal: [], dosen: DOSEN, peserta: ['a'],
    sibukRapat: [{ tanggal: '2027-03-02', slot_id: 4, n: 2 }] });
  assert.equal(anonim.tanpaNama, 2);
});
