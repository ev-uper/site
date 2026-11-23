// apps-script/Code.gs: grade files for CPL (owner 2026-11-11, option 2; instal-lengkap.sql).
// Files under berkas-privat/cpl/ hold NIM: admin only, never via temporary link, assessor or password;
// run_cpl.py downloads them with the CPL_KUNCI key.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const KUNCI = 'k'.repeat(40);

// Small Drive tree: ROOT/berkas-privat/cpl/<sem>/<kelas>/{file, riwayat/{old}} and ROOT/berkas-privat/karya/x.
function pohon(){
  const map = new Map();
  const folder = (id, nama, induk) => {
    const f = { id, nama, induk, anak: [], berkas: [],
      getId: () => id, getName: () => nama,
      getParents: () => { let d = !!induk; return { hasNext: () => d, next: () => { d = false; return induk; } }; },
      getFolders: () => { const xs = [...f.anak]; return { hasNext: () => xs.length > 0, next: () => xs.shift() }; },
      getFiles: () => { const xs = [...f.berkas]; return { hasNext: () => xs.length > 0, next: () => xs.shift() }; },
      getFoldersByName: n => { const xs = f.anak.filter(a => a.nama === n); return { hasNext: () => xs.length > 0, next: () => xs.shift() }; },
      createFolder: n => folder(`${id}/${n}`, n, f) };
    if (induk) induk.anak.push(f);
    map.set(id, f);
    return f;
  };
  const berkas = (id, nama, induk) => {
    const b = { id, nama, getId: () => id, getName: () => nama, getSize: () => 3, getLastUpdated: () => new Date('2026-11-11T08:00:00Z'),
      getParents: () => { let d = true; return { hasNext: () => d, next: () => { d = false; return induk; } }; },
      getBlob: () => ({ getBytes: () => [1, 2, 3] }) };
    induk.berkas.push(b); map.set(id, b);
    return b;
  };
  const root = folder('ROOT', 'data-lkps', null);
  const priv = folder('P', 'berkas-privat', root);
  const cpl = folder('C', 'cpl', priv);
  const sem = folder('S', '2026-2027 Ganjil', cpl);
  const kls = folder('K', '41214-A', sem);
  const rw = folder('R', 'riwayat', kls);
  berkas('BARU', 'baru.xlsx', kls);
  berkas('LAMA', 'lama.xlsx', rw);
  berkas('LAIN', 'x.pdf', folder('KA', 'karya', priv));
  return map;
}

function muat(sifat = { CPL_KUNCI: KUNCI }){
  const map = pohon(), cache = new Map();
  const ctx = {
    PropertiesService: { getScriptProperties: () => ({ getProperty: k => sifat[k] ?? null }) },
    CacheService: { getScriptCache: () => ({ get: k => cache.get(k) ?? null, put: (k, v) => cache.set(k, v) }) },
    LockService: { getScriptLock: () => ({ waitLock() {}, releaseLock() {} }) },
    Utilities: { base64Encode: b => Buffer.from(b).toString('base64') },
    DriveApp: { getFolderById: id => map.get(id), getFileById: id => map.get(id) },
  };
  vm.createContext(ctx);
  vm.runInContext(readFileSync(new URL('../../apps-script/Code.gs', import.meta.url), 'utf8'), ctx);
  return { ctx, map, cfg: { folderId: 'ROOT' } };
}

test('grade files are admin-only and never pass the assessor, password, token or temporary-link paths', () => {
  const { ctx, map, cfg } = muat();
  assert.equal(ctx.nilaiCpl_(cfg, map.get('BARU')), true);
  assert.equal(ctx.nilaiCpl_(cfg, map.get('LAMA')), true);
  assert.equal(ctx.nilaiCpl_(cfg, map.get('LAIN')), false);
  assert.throws(() => ctx.tolakNilaiCpl_(cfg, map.get('BARU'), null), /hanya bisa dibuka admin/);
  assert.throws(() => ctx.tolakNilaiCpl_(cfg, map.get('BARU'), { peran: 'dosen' }), /hanya bisa dibuka admin/);
  assert.doesNotThrow(() => ctx.tolakNilaiCpl_(cfg, map.get('BARU'), { peran: 'admin' }));
  assert.doesNotThrow(() => ctx.tolakNilaiCpl_(cfg, map.get('LAIN'), null));
  // Every public-ish opener calls the refusal (source check, so a future edit cannot drop it silently).
  const src = readFileSync(new URL('../../apps-script/Code.gs', import.meta.url), 'utf8');
  for (const f of ['bukaLkdToken_', 'bukaLkdAsesor_', 'bukaLkdSandi_', 'bagikanSementara_', 'berkasBoleh_']) {
    const badan = src.match(new RegExp(`\\nfunction ${f}\\([\\s\\S]*?\\n}\\n`))[0];
    assert.match(badan, /tolakNilaiCpl_\(cfg, file, (null|lecturer)\)/, f);
  }
});

test('keyed download: missing, short or wrong key is refused, 20 failures lock it for an hour', () => {
  assert.throws(() => muat({}).ctx.cplUnduh_({ folderId: 'ROOT' }, { kunci: '', aksi: 'daftar' }), /belum diisi/);
  assert.throws(() => muat({ CPL_KUNCI: 'pendek' }).ctx.cplUnduh_({ folderId: 'ROOT' }, { kunci: 'pendek', aksi: 'daftar' }), /belum diisi/);
  const { ctx, cfg } = muat();
  for (let i = 0; i < 20; i++) assert.throws(() => ctx.cplUnduh_(cfg, { kunci: 'salah', aksi: 'daftar' }), /Kunci salah/);
  assert.throws(() => ctx.cplUnduh_(cfg, { kunci: KUNCI, aksi: 'daftar' }), /Terlalu banyak/);
});

test('list returns only the latest file per class; fetch serves only those', () => {
  const { ctx, cfg } = muat();
  const d = ctx.cplUnduh_(cfg, { kunci: KUNCI, aksi: 'daftar' });
  assert.deepEqual(JSON.parse(JSON.stringify(d.berkas.map(b => [b.id, b.semester, b.kelas]))), [['BARU', '2026-2027 Ganjil', '41214-A']]);
  const a = ctx.cplUnduh_(cfg, { kunci: KUNCI, aksi: 'ambil', id: 'BARU' });
  assert.equal(a.data, Buffer.from([1, 2, 3]).toString('base64'));
  assert.throws(() => ctx.cplUnduh_(cfg, { kunci: KUNCI, aksi: 'ambil', id: 'LAMA' }), /terbaru/);
  assert.throws(() => ctx.cplUnduh_(cfg, { kunci: KUNCI, aksi: 'ambil', id: 'LAIN' }), /terbaru/);
  assert.throws(() => ctx.cplUnduh_(cfg, { kunci: KUNCI, aksi: 'hapus' }), /tidak dikenal/);
});
