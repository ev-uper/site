// verifikasi.html modules (pemilik 2026-11-08): counts per tab, shared karya
// display moved out of karya.html, and the change table for ajuan ubah karya.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { hitungVerifikasi, TAB_VERIFIKASI } from '../../site/verifikasi-hitung.js';
import { barisKarya, daftarBuktiKarya, berkasMilikKarya, htmlDaftarBukti } from '../../site/karya-tampil.js';
import { tabelBeda } from '../../site/verifikasi-karya.js';
import { labelKolom, FORM } from '../../site/form-karya.js';

// Minimal Supabase stub: select(..., {count, head}) followed by .eq filters.
function sbHitung(baris, gagal = []){
  return { from: tabel => {
    const f = [];
    const q = { eq: (k, v) => { f.push([k, v]); return q; },
      then: (ok, no) => Promise.resolve(gagal.includes(tabel) ? { count: null, error: { message: 'x' } }
        : { count: (baris[tabel] || []).filter(r => f.every(([k, v]) => r[k] === v)).length, error: null }).then(ok, no) };
    return { select: (_, o) => { assert.deepEqual(o, { count: 'exact', head: true }); return q; } };
  } };
}

test('hitungVerifikasi: counts pending rows per tab with the same filters as the panels', async () => {
  const sb = sbHitung({
    karya: [{ status: 'diajukan' }, { status: 'terverifikasi' }, { status: 'diajukan' }],
    ajuan_hapus: [{}],
    ajuan_ubah: [{ jenis: 'karya', status: 'menunggu' }, { jenis: 'profil', status: 'menunggu' },
      { jenis: 'profil', status: 'ditolak' }, { jenis: 'karya', status: 'disetujui' }],
    lkps_bkd: [{ verifikasi: 'diajukan' }, { verifikasi: 'ditolak' }],
    ajuan_bkd: [{ status: 'menunggu' }, { status: 'menunggu' }],
    lkps_prestasi_mahasiswa: [{ status: 'terverifikasi' }],
  }, ['ajuan_prestasi']);
  const n = await hitungVerifikasi(sb);
  assert.deepEqual(TAB_VERIFIKASI, ['karya', 'profil', 'bkd', 'prestasi']);
  assert.deepEqual(n, { total: 8, karya: 4, profil: 1, bkd: 3, prestasi: 0 });
});

test('karya bukti: own files vs inherited parent files', () => {
  const st = { KB: new Map([[1, [{ id: 10, jenis: 'sk', judul: 'SK', url: 'https://b/10', oleh: 'u1' }]],
      [9, [{ id: 90, jenis: 'laporan', url: 'https://b/90', oleh: 'u2' }]]]),
    INDUK: new Map([[9, { id: 9, judul: 'Riset', kategori: 'penelitian', bukti_url: 'https://b/9' }]]) };
  const k = { id: 1, bukti_url: 'https://b/awal', induk_id: 9, status: 'diajukan', judul: 'Artikel' };
  const xs = daftarBuktiKarya(k, st, 'u1');
  assert.deepEqual(xs.map(x => x.url), ['https://b/awal', 'https://b/10', 'https://b/9', 'https://b/90']);
  assert.equal(xs[1].milik, true);
  assert.match(xs[2].label, /^dari penelitian "Riset": /);
  // Deleting the karya must not trash the parent's files.
  assert.deepEqual(berkasMilikKarya(k, st), ['https://b/awal', 'https://b/10']);
  const h = htmlDaftarBukti(k, st, true);
  assert.equal((h.match(/data-adm-hapus/g) || []).length, 2);
  assert.equal(htmlDaftarBukti({ id: 2 }, st), '');
});

test('barisKarya: meta, authors, butir links, and skema name', () => {
  const h = barisKarya({ id: 1, status: 'diajukan', judul: 'A & B', tahun: 2025, bulan: 3, kategori: 'penelitian',
    skema_kode: 'S1', karya_penulis: [{ peran: 'ketua', dosen: { nama: 'Dewi' } }] },
    '<button>v</button>', '', kode => kode === 'S1' ? 'Hibah internal' : '');
  assert.match(h, /A &amp; B/);
  assert.match(h, /Hibah internal/);
  assert.match(h, /Dewi \(ketua\)/);
  assert.match(h, /Masuk setelah diverifikasi:/);
  assert.match(h, /<button>v<\/button>/);
  assert.doesNotMatch(barisKarya({ status: 'ditolak', judul: 'x' }), /ke-butir-data/);
});

test('tabelBeda: labels from FORM, names for ids, author lists', () => {
  const f = Object.values(FORM).flatMap(F => F.f).find(x => x.n === 'nama_terbitan');
  assert.ok(f?.l);
  assert.equal(labelKolom('nama_terbitan'), f.l);
  assert.equal(labelKolom('skema_kode'), 'Skema');
  assert.equal(labelKolom('kolom_baru'), 'kolom baru');
  const a = { data: { karya: { nama_terbitan: 'J Baru', skema_kode: 'S1', kerjasama_id: 5 },
      penulis: [{ dosen_id: 'd1', peran: 'penulis_pertama', korespondensi: true }] },
    lama: { karya: { nama_terbitan: 'J Lama' }, penulis: [] } };
  const h = tabelBeda(a, { nama: new Map([['d1', 'Dewi']]), karya: new Map(), namaKS: { 5: 'PT X — Survei' },
    namaSkema: k => k === 'S1' ? 'Hibah internal' : '' });
  assert.match(h, /J Lama<\/td><td>J Baru/);
  assert.match(h, /Hibah internal/);
  assert.match(h, /PT X — Survei/);
  assert.match(h, /Dewi \(penulis pertama, korespondensi\)/);
});
