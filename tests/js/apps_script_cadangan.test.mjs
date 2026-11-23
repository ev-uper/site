// apps-script/Code.gs kind 'cadangan': backups from GitHub Actions (owner 2026-11-05).
// Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const TOKEN = 't'.repeat(40);

// lama: berkas yang sudah ada di folder cadangan [{nama, umurHari}] (pemangkasan harian, 2026-11-23).
function muat(sifat = { CADANGAN_TOKEN: TOKEN, CADANGAN_FOLDER_ID: 'F' }, lama = []) {
  const dibuat = [];
  const ada = lama.map(x => ({ nama: x.nama, sampah: false, getName: () => x.nama,
    getDateCreated: () => new Date(Date.now() - x.umurHari * 86400000), setTrashed(v) { this.sampah = v; } }));
  const ctx = {
    PropertiesService: { getScriptProperties: () => ({ getProperty: k => sifat[k] ?? null }) },
    Utilities: {
      base64Decode: s => [...Buffer.from(s, 'base64')],
      formatDate: () => '20261105-010203',
      newBlob: (isi, jenis, nama) => ({ isi, jenis, nama }),
    },
    Session: { getScriptTimeZone: () => 'Asia/Jakarta' },
    DriveApp: { getFolderById: id => ({ getFiles: () => { let i = 0; return { hasNext: () => i < ada.length, next: () => ada[i++] }; },
      createFile: b => {
      const f = { ...b, id, dibagikan: false, setDescription() {}, getName: () => b.nama,
                  setSharing() { f.dibagikan = true; } };
      dibuat.push(f); return f;
    } }) },
  };
  vm.createContext(ctx);
  vm.runInContext(readFileSync(new URL('../../apps-script/Code.gs', import.meta.url), 'utf8'), ctx);
  return { simpan: ctx.simpanCadangan_, dibuat, ada };
}
const req = (x = {}) => ({ cadangan_token: TOKEN, name: 'cadangan.zip',
                           data: Buffer.from('zip').toString('base64'), ...x });

test('valid backup lands in the backup folder and is not shared', () => {
  const { simpan, dibuat } = muat();
  const r = simpan(req());
  assert.equal(r.ok, true);
  assert.equal(r.name, '20261105-010203_cadangan.zip');
  assert.equal(dibuat[0].id, 'F');
  assert.equal(dibuat[0].dibagikan, false);
});

test('wrong or missing token is refused and nothing is written', () => {
  const { simpan, dibuat } = muat();
  assert.throws(() => simpan(req({ cadangan_token: 'x' })), /Token cadangan salah/);
  assert.throws(() => simpan(req({ cadangan_token: undefined })), /Token cadangan salah/);
  assert.equal(dibuat.length, 0);
});

test('without configured properties every backup is refused, even with an empty token', () => {
  assert.throws(() => muat({}).simpan(req({ cadangan_token: '' })), /belum diisi/);
  assert.throws(() => muat({ CADANGAN_TOKEN: 'pendek', CADANGAN_FOLDER_ID: 'F' }).simpan(req({ cadangan_token: 'pendek' })), /belum diisi/);
});

test('name must be a plain zip name and content must not be empty', () => {
  const { simpan } = muat();
  assert.throws(() => simpan(req({ name: '../x.zip' })), /Nama cadangan/);
  assert.throws(() => simpan(req({ name: 'x.exe' })), /Nama cadangan/);
  assert.throws(() => simpan(req({ data: '' })), /kosong/);
});

// Pemangkasan (2026-11-23): cadangan harian > 35 hari ke Sampah; tanggal 01, arsip, dan yang baru tetap.
test('daily backups older than 35 days go to the Drive trash, except the 1st of the month and archives', () => {
  const { simpan, ada } = muat(undefined, [
    { nama: '20260901-014000_cadangan.zip', umurHari: 80 }, { nama: '20260915-014000_cadangan.zip', umurHari: 70 },
    { nama: '20261101-014000_cadangan.zip', umurHari: 10 }, { nama: '20261110-014000_cadangan.zip', umurHari: 13 },
    { nama: '20260901-020000_2026-09-01.zip', umurHari: 80 }]);
  const r = simpan(req());
  assert.equal(r.dipangkas, 1);
  assert.deepEqual(ada.filter(f => f.sampah).map(f => f.nama), ['20260915-014000_cadangan.zip']);
  // arsip tahunan tidak memicu pemangkasan
  const b = muat(undefined, [{ nama: '20260915-014000_cadangan.zip', umurHari: 70 }]);
  assert.equal(b.simpan(req({ name: '2027-09-01.zip' })).dipangkas, 0);
  assert.equal(b.ada[0].sampah, false);
});
