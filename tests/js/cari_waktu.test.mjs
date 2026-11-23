// Cari waktu rapat (instal-lengkap.sql, pemilik 2026-11-21).
import test from 'node:test';
import assert from 'node:assert/strict';
import { durasiDari, usulanWaktu, petaSibuk } from '../../site/cari-waktu.js';

// Slot 30 menit 07:00-12:00 (id 1..10).
const SLOT = Array.from({ length: 10 }, (_, i) => ({ id: i + 1, mulai: `${String(7 + Math.floor(i / 2)).padStart(2, '0')}:${i % 2 ? '30' : '00'}`,
  selesai: `${String(7 + Math.floor((i + 1) / 2)).padStart(2, '0')}:${(i + 1) % 2 ? '30' : '00'}` }));

test('durasi dari jam formulir, bawaan 60', () => {
  assert.equal(durasiDari('09:00', '10:30'), 90);
  assert.equal(durasiDari('', ''), 60);
  assert.equal(durasiDari('10:00', '09:00', 45), 45);
});

test('usulan: slot bersambung cukup untuk durasi; paling sedikit tidak bisa dulu; nama untuk pengatur', () => {
  const sibuk = [{ tanggal: '2026-11-23', slot_id: 1, n: 2, dosen: ['a', 'b'] }, { tanggal: '2026-11-23', slot_id: 2, n: 1, dosen: ['a'] },
                 { tanggal: '2026-11-24', slot_id: 3, n: 1, dosen: ['c'] }];
  const u = usulanWaktu({ tanggal: ['2026-11-23', '2026-11-24'], slot: SLOT, sibuk, durasi: 60, maks: 4 });
  assert.deepEqual(u.map(x => [x.tanggal, x.mulai, x.selesai, x.n]),
    [['2026-11-23', '08:00', '09:00', 0], ['2026-11-23', '08:30', '09:30', 0], ['2026-11-24', '07:00', '08:00', 0], ['2026-11-24', '08:30', '09:30', 0]]);
  // 24/11 08:00-09:00 bentrok dengan c (n 1): kalah dari waktu tanpa bentrok.
  assert.equal(usulanWaktu({ tanggal: ['2026-11-24'], slot: SLOT, sibuk, durasi: 60, maks: 50 }).some(x => x.mulai === '08:00'), false);
  const semua = usulanWaktu({ tanggal: ['2026-11-23'], slot: SLOT, sibuk, durasi: 90, maks: 50 });
  const awal = semua.find(x => x.mulai === '07:00');
  assert.equal(awal, undefined);                                         // maks 2 per tanggal; yang bentrok tidak terpilih
  const satu = usulanWaktu({ tanggal: ['2026-11-23'], slot: SLOT.slice(0, 3), sibuk, durasi: 90, maks: 5 });
  assert.deepEqual(satu.map(x => [x.mulai, x.n, x.dosen]), [['07:00', 2, ['a', 'b']]]);   // gabungan a,b (bukan jumlah 3)
});

test('tanpa nama (dosen biasa): jumlah terbesar per slot; waktu lewat dilewati; slot tidak bersambung tidak digabung', () => {
  const sibuk = [{ tanggal: '2026-11-23', slot_id: 1, n: 2 }, { tanggal: '2026-11-23', slot_id: 2, n: 3 }];
  const u = usulanWaktu({ tanggal: ['2026-11-23'], slot: SLOT.slice(0, 2), sibuk, durasi: 60 });
  assert.deepEqual(u.map(x => [x.mulai, x.n, x.dosen]), [['07:00', 3, null]]);
  const lewat = usulanWaktu({ tanggal: ['2026-11-22', '2026-11-23'], slot: SLOT, durasi: 30, kini: { tanggal: '2026-11-23', menit: 10 * 60 }, maks: 50 });
  assert.ok(lewat.every(x => x.tanggal === '2026-11-23' && x.mulai >= '10:00'));
  const putus = [{ id: 1, mulai: '07:00', selesai: '08:00' }, { id: 2, mulai: '09:00', selesai: '10:00' }];
  assert.deepEqual(usulanWaktu({ tanggal: ['2026-11-23'], slot: putus, durasi: 90 }), []);
  assert.equal(petaSibuk([{ tanggal: 't', slot_id: 1, n: 1 }]).get('t|1').dosen, null);
});
