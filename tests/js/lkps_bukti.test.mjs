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

// LAMDEPILAR Magister (owner 2026-11-24): own table list, same evidence sources as lkps-lamdepilar.js.
import { TABEL_LAMDEPILAR } from '../../site/lkps-bukti.js';
const C2 = { ts: 2026, prodi: 'Magister Uji', daftar: { ...C.daftar,
  dokumen: [...C.daftar.dokumen, { id: 9, jenis: 'laporan_keuangan', tahun: 2025, judul: '', url: 'https://d/lra' },
            { id: 10, jenis: 'pedoman_sarpras', tahun: 2024, judul: '', url: 'https://d/sarpras' }],
  karya: [...C.daftar.karya, { id: 'e', kategori: 'pkm', judul: 'Desa air', tahun: 2026, url: 'https://d/pkm' }],
  angkatan: [{ id: 11, tahun_akademik: '2022/2023', asing_penuh_waktu: 1 }, { id: 12, tahun_akademik: '2025/2026', asing_penuh_waktu: 0 }],
  saranaStd: [{ id: 21, jenis: 'belajar', nama: 'Ruang kelas', lokasi: 'Gedung A' }, { id: 22, jenis: 'kerja', nama: 'Lab hidro' }],
  keuangan: [{ id: 31, tahun_akademik: '2025/2026', pos: 'ukt_bergelar' }, { id: 32, tahun_akademik: '2025/2026', pos: 'biaya_pkm' },
             { id: 33, tahun_akademik: '2021/2022', pos: 'ukt_bergelar' }],
  buktiBaris: [...C.daftar.buktiBaris, { tabel: 'lkps_mahasiswa_angkatan', baris_id: 11, judul: 'Rekap PMB', url: 'https://d/pmb' },
    { tabel: 'lkps_sarana_standar', baris_id: 21, judul: 'Foto', url: 'https://d/foto' },
    { tabel: 'lkps_keuangan', baris_id: 31, judul: 'RKAT', url: 'https://d/rkat' },
    { tabel: 'lkps_keuangan', baris_id: 33, judul: 'RKAT lama', url: 'https://d/rkat-lama' }],
} };
const I2 = indeksBukti(C2, TABEL_LAMDEPILAR);
const per2 = n => I2.find(x => x.nama === n);
const urls2 = n => per2(n).items.flatMap(i => i.tautan.map(l => l.url));

test('LAMDEPILAR: Magister tables in template order, Terapan and formula-only tables left out', () => {
  assert.equal(I2.length, 25);
  assert.deepEqual([I2[0].nama, I2[24].nama], ['D.1', 'R.6.1']);
  for (const n of ['E.1.3', 'A.5.3', 'L.4.2', 'R.3.2', 'R.6.2']) assert.equal(per2(n), undefined, n);
  assert.deepEqual(per2('P.1.4').items, []);
});

test('LAMDEPILAR: cohort, facilities per kind, finance with proof in TS-2..TS, karya for R.3.1/R.6.1', () => {
  assert.deepEqual(urls2('E.1.1'), ['https://d/pmb']);
  assert.deepEqual(per2('E.1.2').items, [{ item: 'Angkatan 2022/2023', tautan: [{ t: 'Rekap PMB', url: 'https://d/pmb' }] }]);
  assert.deepEqual(urls2('L.1.1'), ['https://d/sarpras', 'https://d/foto']);
  assert.deepEqual(per2('L.1.1').items.at(-1), { item: 'Ruang kelas (Gedung A)', tautan: [{ t: 'Foto', url: 'https://d/foto' }] });
  assert.equal(per2('L.1.1').items.length, 2, 'library document + one facility');
  assert.deepEqual(per2('L.1.2').items, [{ item: 'Lab hidro', tautan: [] }]);
  assert.deepEqual(urls2('A.5.1'), ['https://d/lra', 'https://d/rkat']);
  assert.ok(per2('A.5.1').items.some(i => /^2025\/2026 Pemasukan: UKT — UKT bergelar$/.test(i.item)));
  assert.deepEqual(urls2('A.5.2'), ['https://d/lra'], 'pos without proof not listed');
  assert.deepEqual(per2('R.3.1').items.map(i => i.item).sort(), ['Banjir & air (2025)', 'Model (2025)'], '2020 outside TS-2..TS');
  assert.deepEqual(per2('R.6.1').items, [{ item: 'Desa air (2026)', tautan: [{ t: 'Tautan', url: 'https://d/pkm' }] }]);
  assert.deepEqual(per2('P.1.6').items.map(i => i.item), ['Editor (2025)']);
});

test('docx intro names the instrument tables', () => {
  assert.match(bagianDocx(I2, { ...C2, namaTabel: 'tabel LKPS LAMDEPILAR (Magister)' }).bagian['word/document.xml'], /dari 25 tabel LKPS LAMDEPILAR \(Magister\)/);
  assert.match(bagianDocx(I, C).bagian['word/document.xml'], /dari 44 tabel wajib Sarjana LAM Teknik/);
});
