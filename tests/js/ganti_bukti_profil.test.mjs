// Bukti profil yang diganti ikut dibuang (owner 2026-11-13): which links are released, the guard that keeps
// shared files, and the Apps Script path that lets an owner trash only their own profile evidence.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { urlBukti, berkasLepas } from '../../site/profil-dosen.js';
import { buangBuktiLepas } from '../../site/hapus-berkas.js';

const SEKARANG = { riwayat_pendidikan: [{ jenjang: 'S3', url: 'U-IJAZAH-LAMA' }, { jenjang: 'S2', url: 'U-S2' }],
  sertifikat: [{ jenis: 'profesi', url: 'U-SERT' }], nama: 'X' };
const DIAJUKAN = { riwayat_pendidikan: [{ jenjang: 'S3', url: 'U-IJAZAH-BARU' }, { jenjang: 'S2', url: 'U-S2' }] };

test('released links: approve drops the replaced file, reject/cancel drops the new one; untouched fields stay', () => {
  assert.deepEqual([...urlBukti(SEKARANG)].sort(), ['U-IJAZAH-LAMA', 'U-S2', 'U-SERT']);
  assert.deepEqual(berkasLepas(SEKARANG, DIAJUKAN, Object.keys(DIAJUKAN)), ['U-IJAZAH-LAMA']);   // setuju
  assert.deepEqual(berkasLepas(DIAJUKAN, SEKARANG, Object.keys(DIAJUKAN)), ['U-IJAZAH-BARU']);   // tolak/batal
  assert.deepEqual(berkasLepas(SEKARANG, { nama: 'Y' }, ['nama']), []);                          // sertifikat not in the change
});

test('buangBuktiLepas trashes only files with no other reference; unknown count keeps the file', async () => {
  const dikirim = [];
  globalThis.window = { UPLOAD_URL: 'https://script.example/exec' };
  globalThis.fetch = async (u, o) => { dikirim.push(JSON.parse(o.body)); return { json: async () => ({ ok: true, dibuang: true }) }; };
  const rujukan = { 'U-BEBAS': 0, 'U-DIPAKAI': 1, 'U-TAKTAHU': null };
  const sb = { auth: { getSession: async () => ({ data: { session: { access_token: 'T' } } }) },
    rpc: async (_, { u }) => rujukan[u] === null ? { error: { message: 'x' } } : { data: rujukan[u] } };
  assert.equal(await buangBuktiLepas(sb, ['U-BEBAS', 'U-DIPAKAI', 'U-TAKTAHU', 'U-BEBAS', '']), 1);
  assert.deepEqual(dikirim, [{ token: 'T', kind: 'hapus', url: 'U-BEBAS' }]);
  dikirim.length = 0;
  await buangBuktiLepas(sb, ['U-BEBAS'], { milik: true });
  assert.equal(dikirim[0].kind, 'buang_milik');
});

test('Apps Script buang_milik: owner trashes own profile evidence only; admin may; other paths refused', () => {
  const map = new Map();
  const folder = (id, nama, induk) => { const f = { id, nama, getId: () => id, getName: () => nama,
    getParents: () => { let d = !!induk; return { hasNext: () => d, next: () => { d = false; return induk; } }; } };
    map.set(id, f); return f; };
  const berkas = (id, induk) => { const b = { id, dibuang: false, getId: () => id, getName: () => id,
    getParents: () => { let d = true; return { hasNext: () => d, next: () => { d = false; return induk; } }; },
    setTrashed(v) { this.dibuang = v; } }; map.set(id, b); return b; };
  const root = folder('ROOT', 'data-lkps', null), priv = folder('P', 'berkas-privat', root);
  const karya = folder('KA', 'karya', priv), th = folder('TH', '2026', karya);
  const milikA = berkas('FA', folder('DA', 'Dosen A', th)), milikB = berkas('FB', folder('DB', 'Dosen B', th));
  const lkd = berkas('FL', folder('LA', 'Dosen A', folder('LT', '2025-2026', folder('BK', 'bkd-privat', root))));
  const ctx = { PropertiesService: { getScriptProperties: () => ({ getProperty: () => null }) },
    LockService: { getScriptLock: () => ({ waitLock() {}, releaseLock() {} }) },
    DriveApp: { getFolderById: id => map.get(id), getFileById: id => map.get(id) } };
  vm.createContext(ctx);
  const src = readFileSync(new URL('../../apps-script/Code.gs', import.meta.url), 'utf8');
  vm.runInContext(src, ctx);
  const cfg = { folderId: 'ROOT' }, url = id => `https://drive.google.com/file/d/${id}xxxxxxxxxxxxxxxxxxxx/view`;
  // ids in links are >= 20 chars; map the long id back to the short test id
  ctx.DriveApp.getFileById = id => map.get(id.replace(/x+$/, ''));
  const A = { nama: 'Dosen A', peran: 'dosen' };
  assert.deepEqual(JSON.parse(JSON.stringify(ctx.buangMilik_(cfg, A, url('FA')))), { ok: true, dibuang: true });
  assert.equal(milikA.dibuang, true);
  assert.throws(() => ctx.buangMilik_(cfg, A, url('FB')), /hanya bisa dibuka pemiliknya/);
  assert.throws(() => ctx.buangMilik_(cfg, A, url('FL')), /Bukan berkas bukti profil/);
  assert.deepEqual(JSON.parse(JSON.stringify(ctx.buangMilik_(cfg, { nama: 'Admin', peran: 'admin' }, url('FB')))), { ok: true, dibuang: true });
  assert.match(src, /kind === 'buang_milik'\) return json_\(buangMilik_\(cfg, lecturer, req\.url\)\)/);
  assert.match(src, /versi: '2026-11-25-lampiran-bimbingan'/);   // versi terakhir; buang_milik ikut sejak 2026-11-13
});
