// site/sidik-berkas.js + site/rapikan-berkas.js: one stored file per document,
// detected by content hash (owner 2026-11-04, supabase/instal-lengkap.sql).
// Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { sidikBerkas, periksaBerkas, kolomSidik, teksTemuan } from '../../site/sidik-berkas.js';
import { berkasDrive, judulDariBerkas, tahunUsulan, kelompokKembar } from '../../site/rapikan-berkas.js';

// SHA-256("abc"), FIPS 180-2 test vector.
const ABC = 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad';

const sbDengan = (hasil, error = null) => ({ rpc: async (nama, arg) => ({ data: hasil(nama, arg), error }) });

test('sidikBerkas: SHA-256 hex of the file content, name ignored', async () => {
  assert.equal(await sidikBerkas(new Blob(['abc'])), ABC);
  assert.equal(await sidikBerkas(new File(['abc'], 'lain.pdf')), ABC);
  assert.equal(await sidikBerkas(null), null);
});

test('periksaBerkas: library record preferred over other evidence', async () => {
  const sb = sbDengan((nama, { h }) => {
    assert.equal(nama, 'cari_sha256'); assert.equal(h, ABC);
    return [{ sumber: 'karya_bukti', id: 9, url: 'k', keterangan: 'Artikel' },
            { sumber: 'dokumen', id: 3, url: 'd', keterangan: 'sk 2025', dokumen_id: 3 }];
  });
  const s = await periksaBerkas(sb, new Blob(['abc']));
  assert.equal(s.sha256, ABC);
  assert.equal(s.temuan.sumber, 'dokumen');
  assert.equal(teksTemuan(s.temuan), 'sudah tersimpan di pustaka dokumen (sk 2025)');
});

test('periksaBerkas: no match -> temuan null, hash kept', async () => {
  const s = await periksaBerkas(sbDengan(() => []), new Blob(['abc']));
  assert.deepEqual(s, { sha256: ABC, temuan: null });
});

test('periksaBerkas: patch 31 missing -> no hash sent, upload proceeds', async () => {
  const s = await periksaBerkas(sbDengan(() => null, { message: 'function cari_sha256 does not exist' }), new Blob(['abc']));
  assert.deepEqual(s, { sha256: null, temuan: null });
  assert.deepEqual(kolomSidik(s.sha256), {});
  assert.deepEqual(kolomSidik(ABC), { sha256: ABC });
});

test('berkasDrive: Drive file links only (same rule as Code.gs idBerkas_)', () => {
  assert.ok(berkasDrive('https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz/view'));
  assert.ok(berkasDrive('https://drive.google.com/open?id=1AbCdEfGhIjKlMnOpQrStUvWxYz'));
  assert.ok(!berkasDrive('https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz'));
  assert.ok(!berkasDrive('https://doi.org/10.1/x'));
});

test('judulDariBerkas / tahunUsulan: upload stamp and extension removed; year from Drive path', () => {
  assert.equal(judulDariBerkas('20251103-101500_SK_Dekan_12.pdf'), 'SK Dekan 12');
  assert.equal(judulDariBerkas('Laporan AMI.docx'), 'Laporan AMI');
  assert.equal(tahunUsulan('dokumen/lkps_vmts/2024/Visi/', '2026-01-02T00:00:00Z'), 2024);
  assert.equal(tahunUsulan('', '2025-05-01T00:00:00Z'), 2025);
});

test('kelompokKembar: same hash in several links, or library recorded twice', () => {
  const H1 = 'a'.repeat(64), H2 = 'b'.repeat(64), H3 = 'c'.repeat(64);
  const g = kelompokKembar([
    { sumber: 'butir_bukti', id: 1, url: 'u-butir', sha256: H1 },
    { sumber: 'dokumen', id: 2, url: 'u-dok', sha256: H1 },
    { sumber: 'lkps_bukti', id: 3, url: 'u-butir', sha256: H1 },
    { sumber: 'karya_bukti', id: 4, url: 'u-k', sha256: H2 },                 // single: not a twin
    { sumber: 'karya_bukti', id: 5, url: 'u-k', sha256: H2 },                 // same link reused: fine
    { sumber: 'dokumen', id: 6, url: 'u-x', sha256: H3 },
    { sumber: 'dokumen', id: 7, url: 'u-x', sha256: H3 },                     // library twice
    { sumber: 'lkps_bukti', id: 8, url: 'u-luar', sha256: null },
  ]);
  assert.equal(g.length, 2);
  const g1 = g.find(x => x.sha256 === H1);
  assert.deepEqual(g1.urls.sort(), ['u-butir', 'u-dok']);
  assert.equal(g1.usul, 'u-dok', 'library link is kept');
  assert.deepEqual(g.find(x => x.sha256 === H3).urls, ['u-x']);
});

// unggahKePustaka with a file whose content is already stored: nothing uploaded.
import { unggahKePustaka } from '../../site/pustaka-dokumen.js';

function sbPustaka(temuan){
  const ditulis = [];
  return { ditulis, auth: { getSession: async () => ({ data: { session: { access_token: 't' } } }) },
    rpc: async () => ({ data: temuan, error: null }),
    from: () => {
      const q = { select: () => q, eq: () => q,
        single: async () => ({ data: ditulis.length ? { id: 950, ...ditulis.at(-1) } : { id: 3, jenis: 'sk_vmts', tahun: 2024, judul: '', url: 'd' }, error: null }),
        upsert: x => { ditulis.push(x); return q; } };
      return q;
    } };
}
const UNGGAH = { url: 'https://script.test', ext: ['pdf'], maxMb: 10 };

test('unggahKePustaka: same file already in library -> that record, no upload', async () => {
  const asli = globalThis.fetch;
  globalThis.fetch = () => { throw new Error('tidak boleh mengunggah'); };
  try {
    const sb = sbPustaka([{ sumber: 'dokumen', id: 3, url: 'd', dokumen_id: 3 }]);
    const d = await unggahKePustaka(sb, UNGGAH, { jenis: 'rps', tahun: 2025, judul: 'SI301', berkas: [new File(['abc'], 'x.pdf')] });
    assert.equal(d._ada, 'pustaka'); assert.equal(d.id, 3); assert.equal(sb.ditulis.length, 0);
  } finally { globalThis.fetch = asli; }
});

test('unggahKePustaka: same file stored as other evidence -> library row with that link, no upload', async () => {
  const asli = globalThis.fetch;
  globalThis.fetch = () => { throw new Error('tidak boleh mengunggah'); };
  try {
    const sb = sbPustaka([{ sumber: 'butir_bukti', id: 72, url: 'https://drive.google.com/file/d/lama/view', dokumen_id: null }]);
    const d = await unggahKePustaka(sb, UNGGAH, { jenis: 'rps', tahun: 2025, judul: 'SI301', berkas: [new File(['abc'], 'x.pdf')] });
    assert.equal(d._ada, 'bukti');
    assert.equal(sb.ditulis[0].url, 'https://drive.google.com/file/d/lama/view');
    assert.equal(sb.ditulis[0].sha256, ABC);
  } finally { globalThis.fetch = asli; }
});

test('unggahKePustaka: several files, one already stored -> refused with its name', async () => {
  const sb = sbPustaka([{ sumber: 'karya_bukti', id: 9, url: 'k', keterangan: 'Artikel' }]);
  await assert.rejects(unggahKePustaka(sb, UNGGAH, { jenis: 'rps', tahun: 2025, judul: 'SI301',
    berkas: [new File(['abc'], 'a.pdf'), new File(['abc'], 'b.pdf')] }), /a\.pdf sudah tersimpan di bukti karya/);
});
