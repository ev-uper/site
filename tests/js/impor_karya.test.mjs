// Impor publikasi ke draf (site/impor-karya.js, pemilik 2026-11-10).
// Data sintetis berbentuk jawaban OpenAlex /works (nama dan ORCID contoh).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { rapiDoi, daftarDoi, jenisDari, centangBawaan, sitasi3, tsDari, peranDari, drafDari, sitasiTahunan,
  rencanaTerbitan, halamanDari, rapiHalaman } from '../../site/impor-karya.js';

const W = {
  id: 'https://openalex.org/W1', doi: 'https://doi.org/10.1016/J.CONTOH.2023.100302',
  title: 'Contoh indeks bahaya banjir', publication_year: 2023, publication_date: '2023-11-03', type: 'article',
  primary_location: { landing_page_url: 'https://doi.org/10.1016/j.contoh.2023.100302',
    source: { display_name: 'Jurnal Contoh Bencana', type: 'journal' } },
  counts_by_year: [{ year: 2026, cited_by_count: 7 }, { year: 2025, cited_by_count: 16 },
                   { year: 2024, cited_by_count: 6 }, { year: 2023, cited_by_count: 2 }],
  authorships: [
    { author_position: 'first', author: { display_name: 'Penulis Satu', orcid: 'https://orcid.org/0000-0001-0000-0001' } },
    { author_position: 'middle', is_corresponding: true,
      author: { display_name: 'Dosen Contoh', orcid: 'https://orcid.org/0000-0002-0000-000X' } }],
};

test('DOI dirapikan dari berbagai bentuk tempelan', () => {
  assert.equal(rapiDoi(' https://doi.org/10.1016/J.X.1 '), '10.1016/j.x.1');
  assert.equal(rapiDoi('doi: 10.5555/abc'), '10.5555/abc');
  assert.deepEqual(daftarDoi('10.1/a\nhttps://doi.org/10.1016/j.x.1, bukan-doi 10.1016/J.X.1'), ['10.1016/j.x.1']);
});

test('jenis dan centang bawaan mengikuti tipe OpenAlex', () => {
  assert.equal(jenisDari(W), 'jurnal');
  assert.equal(jenisDari({ type: 'conference-paper' }), 'prosiding');
  assert.equal(jenisDari({ type: 'article', primary_location: { source: { type: 'conference' } } }), 'prosiding');
  assert.equal(jenisDari({ type: 'book-chapter' }), 'bab_buku');
  assert.equal(jenisDari({ type: 'dataset' }), 'lainnya');
  assert.equal(centangBawaan(W), true);
  for (const t of ['dataset', 'dissertation', 'software']) assert.equal(centangBawaan({ ...W, type: t }), false, t);
  assert.equal(centangBawaan({ ...W, publication_year: null }), false);
});

test('sitasi: tahun kalender yang beririsan dengan TS-2 s.d. TS (empat tahun)', () => {
  assert.equal(tsDari('2026-11-10'), 2027);   // TS 2026/2027
  assert.equal(tsDari('2026-08-31'), 2026);   // TS 2025/2026
  assert.equal(sitasi3(W, 2026), 31);         // 2023-2026
  assert.equal(sitasi3(W, 2025), 24);         // 2022-2025
  assert.equal(sitasi3(W, 2027), 29);         // 2024-2027
  assert.equal(sitasi3({}, 2026), 0);
});

test('peran dosen dikenali dari ORCID', () => {
  assert.deepEqual(peranDari(W, '0000-0002-0000-000x'), { peran: 'anggota', korespondensi: true, dikenali: true });
  assert.deepEqual(peranDari(W, 'https://orcid.org/0000-0001-0000-0001'), { peran: 'penulis_pertama', korespondensi: false, dikenali: true });
  assert.deepEqual(peranDari(W, ''), { peran: 'anggota', korespondensi: false, dikenali: false });
});

test('draf berisi isian karya dan sitasi per tahun dari OpenAlex', () => {
  const d = drafDari(W, { orcid: '0000-0002-0000-000X', hariIni: '2026-11-10' });
  assert.deepEqual(d.karya, {
    kategori: 'publikasi', status: 'draf', judul: 'Contoh indeks bahaya banjir', jenis: 'jurnal',
    tahun: 2023, bulan: 11, nama_terbitan: 'Jurnal Contoh Bencana', doi: '10.1016/j.contoh.2023.100302',
    url: 'https://doi.org/10.1016/j.contoh.2023.100302', openalex_id: 'W1' });
  assert.deepEqual(d.sitasi.map(r => [r.tahun, r.jumlah, r.sumber, r.diambil]),
    [[2023, 2, 'openalex', '2026-11-10'], [2024, 6, 'openalex', '2026-11-10'],
     [2025, 16, 'openalex', '2026-11-10'], [2026, 7, 'openalex', '2026-11-10']]);
  assert.equal(d.sitasiTS, 29);   // TS 2026/2027: 2024-2027
  assert.equal(d.centang, true);
  assert.equal(d.penulis.korespondensi, true);
});

test('volume, nomor, halaman dari biblio OpenAlex; kunci tidak ada bila kosong (instal-lengkap.sql)', () => {
  const d = drafDari({ ...W, biblio: { volume: '49', issue: '2', first_page: '101', last_page: '115' } }, { hariIni: '2026-11-14' });
  assert.deepEqual([d.karya.volume, d.karya.nomor, d.karya.halaman], ['49', '2', '101–115']);
  const tanpa = drafDari({ ...W, biblio: { volume: null, issue: ' ' } }, { hariIni: '2026-11-14' });
  assert.ok(!('volume' in tanpa.karya) && !('nomor' in tanpa.karya) && !('halaman' in tanpa.karya));
});

test('halaman: rentang, satu halaman, nomor artikel, tanda hubung dirapikan', () => {
  assert.equal(halamanDari({ first_page: '7', last_page: '7' }), '7');
  assert.equal(halamanDari({ first_page: 'e0123', last_page: null }), 'e0123');
  assert.equal(halamanDari(undefined), '');
  assert.equal(rapiHalaman('401--415'), '401–415');
  assert.equal(rapiHalaman(' 401 - 415 '), '401–415');
});

test('tombol OpenAlex: hanya kolom kosong yang diisi, isian dosen dibiarkan', () => {
  const oa = (doi, biblio) => [doi, { doi: 'https://doi.org/' + doi, biblio }];
  const works = new Map([oa('10.1/a', { volume: '9', issue: '1', first_page: '1', last_page: '9' }),
    oa('10.1/b', { volume: '5', issue: null, first_page: null }), oa('10.1/c', { volume: null, issue: null })]);
  const r = rencanaTerbitan([
    { id: 'a', doi: '10.1/A', volume: '8 (isian dosen)', nomor: null, halaman: '' },
    { id: 'b', doi: 'https://doi.org/10.1/b', volume: '5', nomor: null, halaman: null },
    { id: 'c', doi: '10.1/c', volume: null, nomor: null, halaman: null },
    { id: 'd', doi: '10.1/d', volume: null, nomor: null, halaman: null },
    { id: 'e', doi: '10.1/e', volume: '1', nomor: '2', halaman: '3–4' }], works);
  assert.deepEqual(r.baris, [{ id: 'a', nomor: '1', halaman: '1–9' }]);
  assert.equal(r.lengkap, 1);                         // e
  assert.equal(r.tanpaData, 2);                       // b (OpenAlex tanpa nomor/halaman), c
  assert.deepEqual(r.tidakDitemukan.map(k => k.id), ['d']);
});

test('sitasi per tahun: tahun nol diisi 0, lebih dari sepuluh tahun lalu tidak diketahui', () => {
  const lama = { publication_year: 2010, counts_by_year: [{ year: 2020, cited_by_count: 3 }] };
  const r = sitasiTahunan(lama, 2026);
  assert.equal(r[0].tahun, 2017);                       // 2026-9
  assert.equal(r.length, 10);
  assert.equal(r.find(x => x.tahun === 2020).jumlah, 3);
  assert.equal(r.find(x => x.tahun === 2021).jumlah, 0);
  assert.deepEqual(sitasiTahunan({ publication_year: 2026 }, 2026), [{ tahun: 2026, jumlah: 0 }]);
});

test('manual publication form: DOI fills only empty bibliographic fields (owner 2026-11-22)', async () => {
  const { isianFormDari } = await import('../../site/impor-karya.js');
  const w = { id: 'https://openalex.org/W1', doi: 'https://doi.org/10.1016/j.jhydrol.2025.132000', title: ' Banjir Jakarta ',
    publication_year: 2025, publication_date: '2025-10-03', type: 'article',
    primary_location: { landing_page_url: 'https://www.sciencedirect.com/x', source: { display_name: 'Journal of Hydrology', type: 'journal' } },
    biblio: { volume: '651', issue: '2', first_page: '132000', last_page: '132015' }, counts_by_year: [], authorships: [] };
  assert.deepEqual(isianFormDari(w, {}, '2026-11-22'), { judul: 'Banjir Jakarta', jenis: 'jurnal', tahun: '2025', bulan: '10',
    nama_terbitan: 'Journal of Hydrology', volume: '651', nomor: '2', halaman: '132000–132015', url: 'https://www.sciencedirect.com/x' });
  // isian dosen tidak ditimpa; kolom kosong saja yang diisi
  assert.deepEqual(isianFormDari(w, { judul: 'Judul saya', volume: '12', jenis: 'prosiding', tahun: '2025', bulan: '9', url: 'https://x' }, '2026-11-22'),
    { nama_terbitan: 'Journal of Hydrology', nomor: '2', halaman: '132000–132015' });
  // data yang tidak ada di OpenAlex dilewati
  const kosong = isianFormDari({ ...w, biblio: { volume: null, issue: '', first_page: null, last_page: null }, publication_date: null }, {}, '2026-11-22');
  assert.ok(!('volume' in kosong) && !('nomor' in kosong) && !('halaman' in kosong) && !('bulan' in kosong));
});

test('publication year options reach back to 1980 (karya.tahun check); other forms keep 12 years (owner 2026-11-22)', async () => {
  const { TAHUN, TAHUN_PUBLIKASI, FORM } = await import('../../site/form-karya.js');
  assert.equal(TAHUN_PUBLIKASI.at(-1), '1980');
  assert.equal(TAHUN_PUBLIKASI[0], TAHUN[0]);
  assert.equal(TAHUN.length, 12);
  if (FORM) {
    assert.equal(FORM.publikasi.f.find(f => f.n === 'tahun').o.length, TAHUN_PUBLIKASI.length);
    assert.equal(FORM.kegiatan.f.find(f => f.n === 'tahun').o.length, 12);
  }
});

test('Scopus without quartile: form option, counted as reputable in 4.i and targets (owner 2026-11-22, patch 153)', async () => {
  const { FORM } = await import('../../site/form-karya.js');
  const { karya4i } = await import('../../site/sitasi.js');
  const { INDIKATOR } = await import('../../site/target-kinerja.js');
  assert.ok(FORM.publikasi.f.find(f => f.n === 'indeksasi').o.some(([v, l]) => v === 'scopus' && /tanpa kuartil/.test(l)));
  const k = { kategori: 'publikasi', jenis: 'prosiding', indeksasi: 'scopus', tahun: 2025, judul: 'X', jumlah_sitasi: 3 };
  assert.equal(karya4i([k], 2026).length, 1);
  const rep = INDIKATOR.find(i => i.kode === 'publikasi_bereputasi');
  assert.equal(rep.karya(k), true);
  assert.equal(rep.karya({ ...k, indeksasi: 'sinta_1_2' }), false);
});
