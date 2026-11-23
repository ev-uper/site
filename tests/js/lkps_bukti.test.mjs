// site/lkps-bukti.js: index of LKPS evidence, table number / item / link (owner 2026-11-05).
// Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { indeksBukti, bagianDocx } from '../../site/lkps-bukti.js';
import { petaDaftar } from '../../site/lkps.js';

const { wajib } = JSON.parse(readFileSync(new URL('../../site/lkps-outline.json', import.meta.url), 'utf8'));
const C = { ts: 2026, prodi: 'Teknik Uji', daftar: {
  dokumen: [{ id: 1, jenis: 'sk_vmts', tahun: 2024, judul: '', url: 'https://d/vmts' },
            { id: 2, jenis: 'rps', tahun: 2025, judul: 'SI301 Hidrologi', url: 'https://d/rps' },
            { id: 3, jenis: 'kebijakan_spmi', tahun: 2024, judul: '', url: 'https://d/keb' },
            { id: 4, jenis: 'laporan_tracer', tahun: 2025, judul: '', url: 'https://d/tracer' }],
  vmts: [{ id: 5, jenis: 'ps', nomor_sk: 'SK-1', tautan: 'https://d/visi' }],
  mk: [{ id: 7, kode: 'SI301', nama: 'Hidrologi', semester: 5 }, { id: 8, kode: 'SI302', nama: 'Hidrolika', semester: 5 }],
  karya: [{ id: 'a', kategori: 'publikasi', jenis: 'jurnal', indeksasi: 'scopus_q2', judul: 'Model', tahun: 2025, doi: '10.1/x', jumlah_sitasi: 4 },
          { id: 'b', kategori: 'penelitian', judul: 'Banjir & air', tahun: 2025, karya_mahasiswa: [{ nama: 'M' }] },
          { id: 'c', kategori: 'penelitian', judul: 'Lama', tahun: 2020 },
          { id: 'd', kategori: 'rekognisi', sub_jenis: 'editor', judul: 'Editor', tahun: 2025, karya_penulis: [] }],
  buktiKarya: [{ karya_id: 'b', judul: 'Laporan', url: 'https://d/lap' }, { karya_id: 'd', judul: 'SK', url: 'https://d/sk' }],
  buktiBaris: [{ tabel: 'lkps_tracer_lulusan', baris_id: 1, judul: 'Rekap', url: 'https://d/rekap' },
               { tabel: 'ref_mata_kuliah', baris_id: 8, judul: 'RPS 2', url: 'https://d/rps2' }],
  ppepp: [{ tahap: 'penetapan', dokumen_id: 3 }],
} };
const I = indeksBukti(C, wajib);
const per = n => I.find(x => x.nama === n);
const urls = n => per(n).items.flatMap(i => i.tautan.map(l => l.url));

test('all 44 tables in order, empty ones stay empty', () => {
  assert.equal(I.length, 44);
  assert.deepEqual([I[0].nama, I[43].nama], ['PS', '7b']);
  assert.deepEqual(per('4a').items, []);
  assert.deepEqual(per('5c').items, []);
});

test('links: library, row evidence, karya, DOI, PPEPP', () => {
  assert.deepEqual(urls('1'), ['https://d/vmts', 'https://d/visi']);
  assert.deepEqual(per('3a1').items.map(i => i.item), ['SI301 Hidrologi', 'SI302 Hidrolika']);
  assert.deepEqual(per('3a1').items[0].tautan, [{ t: 'RPS', url: 'https://d/rps' }]);
  assert.deepEqual(per('3a1').items[1].tautan, [{ t: 'RPS 2', url: 'https://d/rps2' }]);
  assert.deepEqual(urls('4d'), ['https://doi.org/10.1/x']);
  assert.deepEqual(urls('6f1'), ['https://d/tracer', 'https://d/rekap']);
  assert.deepEqual(urls('7a'), ['https://d/keb']);
  assert.deepEqual(per('7b').items, [{ item: 'Penetapan', tautan: [{ t: 'Dokumen', url: 'https://d/keb' }] }]);
});

test('rows follow the LKPS window; item without proof is listed with an empty link', () => {
  assert.deepEqual(per('3b').items.map(i => i.item), ['Banjir & air (2025)'], '2020 outside TS-2..TS');
  assert.deepEqual(urls('6h1'), ['https://d/lap']);
  assert.deepEqual(per('3a4').items, []);
});

test('docx: escaped, hyperlinks related, empty table keeps a row', () => {
  const { bagian, tautan } = bagianDocx(I, C);
  const x = bagian['word/document.xml'], r = bagian['word/_rels/document.xml.rels'];
  assert.match(x, /Banjir &amp; air/);
  assert.equal((x.match(/<w:hyperlink /g) || []).length, tautan);
  assert.equal((r.match(/TargetMode="External"/g) || []).length, tautan);
  assert.ok((x.match(/<w:tr>/g) || []).length >= 44);
  assert.match(x, /tabel wajib Sarjana LAM Teknik memiliki tautan bukti/);
});

test('4j Bukti Pendukung carries the link', () => {
  const X = { ...C.daftar, dosen: [] };
  const L = petaDaftar({ ts: 2026, daftar: { ...X, karya: X.karya.map(k => ({ ...k, status: 'terverifikasi' })) }, D: { akreditasi: {} } });
  assert.equal(L['4j'].E12, 'Editor (https://d/sk)');
});

test('4c: private LKD through lkd.html, password only when typed at download', () => {
  const id = 'abcdefghijklmnopqrstuvwxyz';
  const daftar = { dosen: [{ nidn: '1', nama: 'Adi' }], bkd: [
    { nidn: '1', tahun_akademik: '2025/2026', semester: 'genap', bukti_url: `https://drive.google.com/file/d/${id}/view` },
    { nidn: '1', tahun_akademik: '2025/2026', semester: 'ganjil', bukti_url: null },
    { nidn: '1', tahun_akademik: '2024/2025', semester: 'genap', bukti_url: `https://drive.google.com/file/d/${id}x/view` }] };
  const satu = o => indeksBukti({ ts: 2026, daftar, basisUrl: 'https://s/', ...o }, [{ nama: '4c', judul: '4.c' }]);
  const [x] = satu({ sandiLkd: 'rahasia-uji' });
  assert.equal(x.items.length, 1);
  assert.equal(x.items[0].item, 'Adi, 2025/2026 genap');
  assert.equal(x.items[0].tautan[0].url, `https://s/lkd.html?f=${id}`);
  assert.match(x.items[0].catatan, /rahasia-uji/);
  assert.match(satu({})[0].items[0].catatan, /diberikan terpisah/);
  assert.match(bagianDocx([x], { ts: 2026 }).bagian['word/document.xml'], /rahasia-uji/);
});
