// Jam kerja email pemeriksa (pemilik 2026-11-20): Senin-Jumat 09.00-16.00 WIB; apps-script/Code.gs jamKerja_.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const gs = readFileSync(new URL('../../apps-script/Code.gs', import.meta.url), 'utf8');
const ambil = re => gs.match(re)?.[0] || assert.fail('tidak ditemukan: ' + re);
// Tiruan Utilities.formatDate untuk pola 'u' (1 = Senin) dan 'H' (jam 0-23) di zona yang diminta.
const Utilities = { formatDate: (d, zona, pola) => {
  const b = Object.fromEntries(new Intl.DateTimeFormat('en-GB', { timeZone: zona, weekday: 'short', hour: '2-digit', hourCycle: 'h23' })
    .formatToParts(d).map(x => [x.type, x.value]));
  return pola === 'u' ? String(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].indexOf(b.weekday) + 1) : String(+b.hour);
} };
const jamKerja_ = new Function('Utilities', [ambil(/var KABAR_PEMERIKSA_JAM = .*/), ambil(/var KABAR_PEMERIKSA_ZONA = .*/),
  ambil(/function jamKerja_\(kini\) \{[\s\S]*?\n\}/), 'return jamKerja_;'].join('\n'))(Utilities);

test('jamKerja_: Senin-Jumat 09.00 sampai sebelum 16.00 WIB', () => {
  const w = s => new Date(s);
  assert.equal(jamKerja_(w('2026-11-23T08:59:00+07:00')), false);   // Senin sebelum 9
  assert.equal(jamKerja_(w('2026-11-23T09:00:00+07:00')), true);
  assert.equal(jamKerja_(w('2026-11-23T15:59:00+07:00')), true);
  assert.equal(jamKerja_(w('2026-11-23T16:00:00+07:00')), false);
  assert.equal(jamKerja_(w('2026-11-27T13:00:00+07:00')), true);    // Jumat
  assert.equal(jamKerja_(w('2026-11-28T10:00:00+07:00')), false);   // Sabtu
  assert.equal(jamKerja_(w('2026-11-23T02:30:00Z')), true);         // 09.30 WIB walau 02.30 UTC
  assert.equal(jamKerja_(w('2026-11-22T23:30:00Z')), false);        // Senin 06.30 WIB
});

// Hari libur (139, pemilik 2026-11-21): liburMingguIni_ (Senin-Minggu minggu itu, WIB) dan hariKerjaPertama_.
const Utilities2 = { formatDate: (d, zona, pola) => pola === 'yyyy-MM-dd'
  ? new Intl.DateTimeFormat('en-CA', { timeZone: zona, year: 'numeric', month: '2-digit', day: '2-digit' }).format(d)
  : Utilities.formatDate(d, zona, pola) };
const muatLibur = (rpc_, Logger = { log(){} }) => new Function('Utilities', 'rpc_', 'Logger', [ambil(/var KABAR_PEMERIKSA_ZONA = .*/),
  ambil(/function tanggalWib_\(d\) \{.*\}/), ambil(/function liburMingguIni_\(cfg, kini\) \{[\s\S]*?\n\}/),
  ambil(/function hariKerjaPertama_\(kini, libur\) \{[\s\S]*?\n\}/), 'return { liburMingguIni_, hariKerjaPertama_ };'].join('\n'))(Utilities2, rpc_, Logger);

test('liburMingguIni_: rentang Senin-Minggu WIB; galat = tidak ada libur', () => {
  let minta = null;
  const { liburMingguIni_ } = muatLibur((cfg, nama, a) => { minta = [nama, a]; return [{ tanggal: '2026-12-25', nama: 'Natal' }]; });
  assert.deepEqual(liburMingguIni_({}, new Date('2026-12-24T17:30:00Z')), { '2026-12-25': 'Natal' });   // Jumat 00.30 WIB
  assert.deepEqual(minta, ['hari_libur_antara', { p_dari: '2026-12-21', p_sampai: '2026-12-27' }]);
  const log = [];
  const gagal = muatLibur(() => { throw new Error('function does not exist'); }, { log: s => log.push(s) });
  assert.deepEqual(gagal.liburMingguIni_({}, new Date('2026-12-24T03:00:00Z')), {});
  assert.match(log[0], /139-patch-hari-libur|instal-lengkap\.sql/);   // repo prodi: satu berkas instal-lengkap.sql
});

test('hariKerjaPertama_: Senin biasa; Senin libur -> Selasa; akhir pekan dan hari libur tidak', () => {
  const { hariKerjaPertama_ } = muatLibur(() => []);
  const w = s => new Date(s + 'T10:00:00+07:00');
  assert.equal(hariKerjaPertama_(w('2026-11-23'), {}), true);                       // Senin
  assert.equal(hariKerjaPertama_(w('2026-11-24'), {}), false);                      // Selasa, Senin bukan libur
  const lb = { '2026-11-23': 'Libur' };
  assert.equal(hariKerjaPertama_(w('2026-11-23'), lb), false);                      // Senin libur
  assert.equal(hariKerjaPertama_(w('2026-11-24'), lb), true);                       // Selasa = hari kerja pertama
  assert.equal(hariKerjaPertama_(w('2026-11-25'), lb), false);
  assert.equal(hariKerjaPertama_(w('2026-11-28'), {}), false);                      // Sabtu
  assert.equal(hariKerjaPertama_(w('2026-11-23'), undefined), true);
});
