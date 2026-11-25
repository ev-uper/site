// LKPS LAMDEPILAR (site/lkps-lamdepilar.js, 2026-11-24): official template filled directly.
// Owner 2026-11-24: every fictitious sample in the template is removed.
// Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { petaLembar } from '../../site/lkps.js';
import { petaLKPSLamdepilar, isiLembar, kosongkanSel, sisipKolom, geserRujukan, sisipBaris, geserRujukanBaris } from '../../site/lkps-lamdepilar.js';
import { bacaZip } from './baca_zip.mjs';

const LDP = new URL('../../site/instrumen/lamdepilar-magister/', import.meta.url);
const zip = bacaZip(readFileSync(new URL('lkps-template.xlsx', LDP)));
const contoh = JSON.parse(readFileSync(new URL('lkps-contoh.json', LDP), 'utf8'));
const lembar = petaLembar(zip['xl/workbook.xml'](), zip['xl/_rels/workbook.xml.rels']());
const ss = [...zip['xl/sharedStrings.xml']().matchAll(/<si>([\s\S]*?)<\/si>/g)]
  .map(m => [...m[1].matchAll(/<t[^>]*>([^<]*)<\/t>/g)].map(t => t[1]).join(''));

// Text of every value cell in a sheet: { ref: text }
function nilaiSel(xml){
  const out = {};
  for (const m of xml.matchAll(/<c r="([A-Z]+\d+)"([^>]*?)(?:\/>|>([\s\S]*?)<\/c>)/g)) {
    const isi = m[3] || '';
    if (/<f[\s>]/.test(isi)) continue;
    const v = /<v>([^<]*)<\/v>/.exec(isi)?.[1], is = /<is>[\s\S]*?<t[^>]*>([^<]*)<\/t>/.exec(isi)?.[1];
    if (is != null) out[m[1]] = is;
    else if (v != null) out[m[1]] = /t="s"/.test(m[2]) ? ss[+v] : v;
  }
  return out;
}
const rumus = xml => (xml.match(/<f[\s>]/g) || []).length;
// Formulas the fill map writes on purpose (P.1.2 analysis, per-row averages) minus sample formulas it removes.
const ditulis = (peta, nama) => Object.values(peta[nama] || {}).filter(v => v && typeof v === 'object' && 'rumus' in v).length
  - ((peta.hapusRumus || {})[nama] || []).length;   // sample-row formulas removed on purpose (P.1.2 G/K/L 24-27)
const CONTOH = /Rakaka|Riki Riki|Ruku Ruku|Roko Roko|Satrep|Memorum of Understanding|BRIN 2025|Desain Produk|Dana dana|Mitra Dana|Fundrise|Mandiri Sejahtera|Pemerintah Kota AA|^tautan$|^tulis nama$|^tulis angka$|lomba desain|Kemenkraf|Nama Tendik|Meja dan kursi|Konstruksi Bangu/i;

const C = {
  ts: 2026, prodi: 'Keberlanjutan', jenjang: 'Magister', institusi: 'Universitas Uji', kini: new Date('2026-11-24'),
  daftar: {
    prodiUpps: [], dokumen: [], ampu: {},
    mk: [{ nama: 'Metodologi Riset', kode: 'KB501', semester: 1, sks: 3, rps_url: 'https://contoh.uji/rps', pengampu: ['0001'] }],
    dosen: [{ id: 'a', nidn: '0001', nama: 'Dr. Uji', kategori: 'tetap', dtps: true, peran: 'dosen', aktif: true,
              pendidikan: 'S3', jabatan: 'lektor_kepala', bidang_keahlian: 'Keberlanjutan', sesuai_kompetensi_inti: true }],
    kerjasama: [{ mitra: 'Mitra Uji', tingkat: 'nasional', kegiatan: 'Riset bersama', tahun_mulai: 2025, tahun_selesai: 2027,
                  tanggal_mulai: '2025-01-02', tautan_bukti: 'https://contoh.uji/ks' }],
    // TS 2026 = 2025/2026; prestasi bulan >= 9 masuk TS berikutnya. Window TS-4..TS = TS 2022..2026.
    prestasi: [
      { nama_mahasiswa: 'Ani', nim: 'M01', nama_kegiatan: 'Lomba Esai Keberlanjutan', penyelenggara: 'Kementerian X',
        tingkat: 'internasional', capaian: 'Juara 1', tahun: 2025, bulan: 3 },
      { nama_mahasiswa: 'Budi', nim: 'M02', nama_kegiatan: 'Terlalu baru', tingkat: 'nasional', tahun: 2026, bulan: 10 },
      { nama_mahasiswa: 'Cici', nim: 'M03', nama_kegiatan: 'Terlalu lama', tingkat: 'nasional', tahun: 2021, bulan: 8 },
    ],
    tracer: [{ tahun_lulus: 2025, jumlah_lulusan: 12, jumlah_terlacak: 9, wt_kurang_3: 4, wt_3_18: 5 }],
    mhs: [{ tahun_akademik: '2025/2026', jumlah_mahasiswa_aktif: 40 }],
  },
};

test('kosongkanSel keeps style and never touches formulas', () => {
  const x = '<row r="8"><c r="C8" s="5" t="s"><v>3</v></c><c r="D8" s="6"><f>SUM(A1)</f><v>2</v></c></row>';
  assert.equal(kosongkanSel(x, 'C8'), '<row r="8"><c r="C8" s="5"/><c r="D8" s="6"><f>SUM(A1)</f><v>2</v></c></row>');
  assert.equal(kosongkanSel(x, 'D8'), x);
  assert.equal(kosongkanSel(x, 'Z9'), x);
});

test('sample list and fill map only name sheets that exist in the template', () => {
  const peta = petaLKPSLamdepilar(C);
  for (const n of [...Object.keys(contoh), ...Object.keys(peta)]) assert.ok(lembar[n], `lembar '${n}'`);
});

test('filled template: no sample left, formulas intact, site data written', () => {
  const peta = petaLKPSLamdepilar(C);
  const semua = Object.fromEntries(Object.values(lembar).map(p => [p, zip[p]()]));
  const h = isiLembar(semua, lembar, contoh, peta);
  assert.equal(h.kosong, Object.values(contoh).flat().length);
  for (const [nama, path] of Object.entries(lembar)) {
    assert.equal(rumus(h.xml[path]), rumus(semua[path]) + ditulis(peta, nama), `rumus ${nama}`);
    const v = nilaiSel(h.xml[path]);
    for (const [ref, t] of Object.entries(v)) assert.ok(!CONTOH.test(t.trim()), `contoh tersisa ${nama}!${ref}: ${t}`);
    for (const ref of contoh[nama] || []) if (!(peta[nama] || {})[ref]) assert.equal(v[ref], undefined, `${nama}!${ref} belum kosong`);
  }
  const v = n => nilaiSel(h.xml[lembar[n]]);
  assert.match(v('Cover').B23, /Magister Keberlanjutan/);
  assert.deepEqual([v('D.1').C8, v('D.1').D8], ['Magister', 'Keberlanjutan']);
  assert.deepEqual([v('E.2').B7, v('E.2').C7, v('E.2').E7, v('E.2').I7], ['Metodologi Riset', 'KB501', '3', 'https://contoh.uji/rps']);
  assert.deepEqual([v('P.1').C8, v('P.1').F8, v('P.1').E8, v('P.1').I8, v('P.1').L8], ['Dr. Uji', 'V', undefined, 'Lektor Kepala', 'Metodologi Riset']);
  assert.deepEqual([v('A.1').C8, v('A.1').E8, v('A.1').I8, v('A.1').M8], ['Mitra Uji', '1', '02/01/2025', 'https://contoh.uji/ks']);
  assert.equal(v('A.1').C9, undefined, 'baris contoh kedua A.1 kosong');
  // E.4.3: only the prize inside TS-4..TS; tingkat as V in its column
  assert.deepEqual([v('E.4').T8, v('E.4').U8, v('E.4').V8, v('E.4').W8, v('E.4').Z8, v('E.4').AA8],
    ['Ani', 'M01', 'Lomba Esai Keberlanjutan', 'Kementerian X', 'V', 'Juara 1']);
  assert.equal(v('E.4').T9, undefined, 'prestasi di luar TS-4..TS tidak masuk');
  // L.4.1: TS-1 row (tahun lulus 2025) = row 9; only <3 months band, 3-6/>6 left for the prodi
  assert.deepEqual([v('L.4').C9, v('L.4').D9, v('L.4').F9, v('L.4').G9, v('L.4').H9], ['12', '9', '4', undefined, undefined]);
  // E.1 per angkatan: not filled from per-TA totals
  for (const ref of ['I8', 'I12', 'K12', 'T12']) assert.equal(v('E.1')[ref], undefined, `E.1!${ref}`);
});

// E.4.1-E.4.2 (owner 2026-11-24): newest curriculum, weight per CPL column (sums to 1),
// CPL > 5 -> extra columns after O, Keterangan and E.4.3 shift right.
test('sisipKolom shifts cells, merges, widths; new cells take column O style', () => {
  const x = '<worksheet><dimension ref="B2:AC21"/><cols><col min="11" max="15" width="9"/><col min="16" max="16" width="20"/>' +
    '<col min="20" max="20" width="30"/></cols><sheetData><row r="5"><c r="K5" s="7" t="s"><v>1</v></c><c r="O5" s="7"/>' +
    '<c r="P5" s="8" t="s"><v>2</v></c><c r="T5" s="9"/></row></sheetData><mergeCells count="3"><mergeCell ref="K5:O5"/>' +
    '<mergeCell ref="P5:P6"/><mergeCell ref="B5:B6"/></mergeCells></worksheet>';
  const y = sisipKolom(x, 15, 2);
  assert.match(y, /<dimension ref="B2:AE21"\/>/);
  assert.match(y, /<col min="11" max="17" width="9"\/><col min="18" max="18" width="20"\/><col min="22" max="22" width="30"\/>/);
  assert.match(y, /<c r="O5" s="7"\/><c r="P5" s="7"\/><c r="Q5" s="7"\/><c r="R5" s="8" t="s"><v>2<\/v><\/c><c r="V5" s="9"\/>/);
  assert.match(y, /<mergeCell ref="K5:Q5"\/><mergeCell ref="R5:R6"\/><mergeCell ref="B5:B6"\/>/);
  assert.equal(sisipKolom(x, 15, 0), x);
  assert.equal(geserRujukan('<c r="C13"><f>E.4!T4</f></c><c r="C12"><f>E.4!$I$4</f></c><c><f>D.1!T4</f></c>', 'E.4', 15, 2),
    '<c r="C13"><f>E.4!V4</f></c><c r="C12"><f>E.4!$I$4</f></c><c><f>D.1!T4</f></c>');
});

test('E.4.1-E.4.2 from CPL data with 7 CPL and 13 MK', () => {
  const mkK26 = Array.from({ length: 13 }, (_, i) => ({ nama: `MK ${i + 1}`, kode: `KB${String(i + 1).padStart(2, '0')}`,
    semester: 1 + (i % 3), sks: 3, kurikulum: 'K26' }));
  const cpl = Array.from({ length: 7 }, (_, j) => ({ kurikulum: 'K26', kode: `CPL${j + 1}`, rumusan: `Rumusan ${j + 1}`,
    indikator: `Indikator ${j + 1}`, urutan: j }));
  const mkCpl = [
    { kurikulum: 'K26', kode_mk: 'KB01', cpl: 'CPL1', bobot: 2 }, { kurikulum: 'K26', kode_mk: 'KB02', cpl: 'CPL1', bobot: 2 },
    { kurikulum: 'K26', kode_mk: 'KB03', cpl: 'CPL1', bobot: null },
    ...cpl.slice(1).map((c, j) => ({ kurikulum: 'K26', kode_mk: `KB${String(j + 4).padStart(2, '0')}`, cpl: c.kode, bobot: 5 })),
    { kurikulum: 'K21', kode_mk: 'LAMA1', cpl: 'CPL1', bobot: 9 },
  ];
  const C2 = { ...C, daftar: { ...C.daftar, mk: [...mkK26, { nama: 'MK Lama', kode: 'LAMA1', semester: 1, sks: 2, kurikulum: 'K21' }],
    cpl: [...cpl, { kurikulum: 'K21', kode: 'X1', rumusan: 'CPL lama' }], mkCpl } };
  const peta = petaLKPSLamdepilar(C2);
  assert.deepEqual(peta.sisip, [{ lembar: 'E.4', setelah: 15, n: 2 }]);
  const semua = Object.fromEntries(Object.values(lembar).map(p => [p, zip[p]()]));
  const h = isiLembar(semua, lembar, contoh, peta);
  const e4 = h.xml[lembar['E.4']], v = nilaiSel(e4), di = h.xml[lembar['Daftar Isi']];
  // E.4.1: one CPL per two merged rows
  assert.deepEqual([v.B8, v.C8, v.D8, v.C10, v.C20], ['Rumusan 1', 'CPL1', 'Indikator 1', 'CPL2', 'CPL7']);
  // E.4.2 header: CPL codes K..Q, Keterangan moved from P5 to R5, merge widened
  assert.deepEqual(['K6', 'O6', 'P6', 'Q6'].map(r => v[r]), ['CPL1', 'CPL5', 'CPL6', 'CPL7']);
  assert.match(v.R5, /Keterangan/);
  assert.match(e4, /<mergeCell ref="K5:Q5"\/>/);
  assert.deepEqual(['K7', 'Q7', 'R7'].map(r => v[r]), ['3', '9', '10']);
  // weights per CPL column: 2, 2, empty(=1) -> 0.4, 0.4, 0.2 (MK rows sorted by semester, as E.2: find row by code in J)
  const baris = kode => Object.keys(v).find(r => /^J\d+$/.test(r) && v[r] === kode).slice(1);
  assert.deepEqual(['KB01', 'KB02', 'KB03'].map(k => v[`K${baris(k)}`]), ['0.4', '0.4', '0.2']);
  assert.equal(v[`I${baris('KB02')}`], 'MK 2');
  assert.equal(Object.keys(v).filter(r => /^J\d+$/.test(r) && /^KB/.test(v[r])).length, 13);
  assert.match(v.I19, /^MK \d+$/, 'baris 19 berisi MK, bukan rekapitulasi');
  assert.ok(!Object.values(v).includes('MK Lama'), 'MK kurikulum lama tidak masuk');
  // recap moved below the last MK (row 21) with sum 1 per CPL; note two rows below
  assert.equal(v.I21, 'Rekapitulasi Bobot CPL');
  assert.deepEqual(['K21', 'L21', 'Q21'].map(r => v[r]), ['1', '1', '1']);
  assert.match(v.I23, /Jumlah dari gabungan/);
  // E.4.3 shifted two columns (T -> V); Daftar Isi formula follows
  assert.deepEqual([v.V8, v.W8, v.AB8], ['Ani', 'M01', 'V']);
  assert.match(di, /<f>E\.4!V4<\/f>/);
  assert.ok(!/<f>E\.4!T4<\/f>/.test(di));
  for (const [nama, path] of Object.entries(lembar)) {
    assert.equal(rumus(h.xml[path]), rumus(semua[path]) + ditulis(peta, nama), `rumus ${nama}`);
    for (const [ref, t] of Object.entries(nilaiSel(h.xml[path]))) assert.ok(!CONTOH.test(t.trim()), `contoh tersisa ${nama}!${ref}: ${t}`);
  }
});

test('E.4 with 3 CPL: no extra columns, unused CPL labels cleared', () => {
  const C3 = { ...C, daftar: { ...C.daftar, mk: [{ nama: 'A', kode: 'A1', kurikulum: 'K26' }],
    cpl: [1, 2, 3].map(j => ({ kurikulum: 'K26', kode: `C${j}`, rumusan: `R${j}` })),
    mkCpl: [{ kurikulum: 'K26', kode_mk: 'A1', cpl: 'C1', bobot: 1 }] } };
  const peta = petaLKPSLamdepilar(C3);
  assert.deepEqual(peta.sisip, []);
  const semua = Object.fromEntries(Object.values(lembar).map(p => [p, zip[p]()]));
  const v = nilaiSel(isiLembar(semua, lembar, contoh, peta).xml[lembar['E.4']]);
  assert.deepEqual(['K6', 'M6', 'N6', 'O6'].map(r => v[r]), ['C1', 'C3', undefined, undefined]);
  assert.match(v.P5, /Keterangan/);
  assert.deepEqual([v.K8, v.K19, v.I19], ['1', '1', 'Rekapitulasi Bobot CPL']);
});

// P.1.3-P.1.7 (2026-11-24). P.1.2 left empty: beban_bimbingan counts advisors 1 and 2, template asks main advisor.
test('P.1.3-P.1.7 from site data; overflow never overwrites the next table', () => {
  const dosen = [
    { id: 'a', nidn: '0001', nama: 'Dr. Uji', kategori: 'tetap', dtps: true, peran: 'dosen', aktif: true, pendidikan: 'S3' },
    { id: 'b', nidn: '0002', nama: 'A Tamu', kategori: 'tidak_tetap', peran: 'dosen', aktif: true, pendidikan: 'S2',
      bidang_keahlian: 'Hidrologi', jabatan: 'lektor', sesuai_keahlian_mk: true },
    { id: 'c', nidn: '0003', nama: 'Praktisi', kategori: 'industri', peran: 'dosen', aktif: true, pendidikan: 'S2',
      perusahaan: 'PT Air', bidang_keahlian: 'Air' },
    ...Array.from({ length: 9 }, (_, i) => ({ id: `t${i}`, nidn: `9${i}`, nama: `DTT ${i}`, kategori: 'tidak_tetap',
      peran: 'dosen', aktif: true })),
  ];
  const mk = [{ nama: 'Hidrologi Lanjut', kode: 'KB10', sks: 3, pengampu: ['0002', '0003'], kurikulum: 'K26' }];
  const bkd = [
    { nidn: '0001', tahun_akademik: '2025/2026', sks_pendidikan: 6, sks_penelitian: 3, sks_pkm: 1, sks_penunjang: 2 },
    { nidn: '0001', tahun_akademik: '2025/2026', sks_pendidikan: 4, sks_penelitian: 2 },
    { nidn: '0001', tahun_akademik: '2023/2024', sks_pendidikan: 12 },
    { nidn: '0001', tahun_akademik: '2020/2021', sks_pendidikan: 99 },
  ];
  const karya = [{ id: 7, kategori: 'rekognisi', sub_jenis: 'invited_speaker', judul: 'Seminar Air', tingkat: 'internasional',
    tahun: 2025, bulan: 5, karya_penulis: [{ peran: 'ketua', dosen: { nama: 'Dr. Uji' } }] }];
  const buktiKarya = [{ karya_id: 7, jenis: 'sk', url: 'https://contoh.uji/st' }, { karya_id: 7, jenis: 'foto', url: 'https://contoh.uji/f' }];
  const tendik = [{ nama: 'Laboran A', pendidikan: 'd3', jabatan: 'laboran', unit_kerja: 'prodi', sertifikat: 'K3' },
    { nama: 'Lama', aktif: false }];
  const C4 = { ...C, daftar: { ...C.daftar, dosen, mk, bkd, karya, buktiKarya, tendik } };
  const peta = petaLKPSLamdepilar(C4);
  const semua = Object.fromEntries(Object.values(lembar).map(p => [p, zip[p]()]));
  const h = isiLembar(semua, lembar, contoh, peta);
  const p1 = h.xml[lembar['P.1']], v = nilaiSel(p1);
  // P.1.3 EWMP: TS sums (10, 0, 0, 5, 1, 2); L = all sks TS-2..TS / 3 rows = (12 + 6 + 12) / 3 = 10; K stays a formula
  assert.deepEqual(['C45', 'D45', 'E45', 'H45', 'I45', 'J45', 'L45'].map(r => v[r]), ['Dr. Uji', 'V', '10', '5', '1', '2', '10']);
  assert.match(p1, /<c r="K45"[^>]*><f>SUM\(E45:J45\)<\/f>/);
  // P.1.3 analysis (owner 2026-11-25): K/2 (per semester in TS) against 12 and 20; Jumlah Dosen = table rows
  const f = ref => (new RegExp(`<c r="${ref}"[^>]*>\s*<f[^>]*>([^<]*)</f>`).exec(p1) || [])[1]
    ?.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&');
  assert.deepEqual(['R42', 'R43', 'U42', 'U43', 'R44', 'U44'].map(f), ['SUMPRODUCT((C45:C51<>"")*(K45:K51/2<12))',
    'COUNTA(C45:C51)', 'SUMPRODUCT((C45:C51<>"")*(K45:K51/2>20))', 'COUNTA(C45:C51)', 'R42/R43', 'U42/U43']);
  assert.deepEqual(['R42', 'R43', 'U42', 'U43'].map(r => v[r]), [undefined, undefined, undefined, undefined], 'sample 0/4 gone');
  // P.1.4: 10 non-permanent lecturers, 7 template rows -> 3 rows inserted before row 61; all 10 written
  assert.deepEqual(peta.sisipBaris, [{ lembar: 'P.1', baris: 61, n: 3 }]);
  assert.deepEqual(peta.peringatan, []);
  assert.deepEqual(['C55', 'C61', 'C64'].map(r => v[r]), ['A Tamu', 'DTT 5', 'DTT 8']);
  assert.deepEqual(['E', 'F', 'G', 'J', 'K'].map(c => v[c + 55]), ['Magister', 'Hidrologi', 'Lektor', 'Hidrologi Lanjut', 'V']);
  // P.1.4 analysis (owner 2026-11-25): rows of P.1.4 over (P.1.1 + P.1.4); the range covers the 3 inserted rows
  assert.deepEqual(['R55', 'R56', 'R57'].map(f), ['COUNTA(C55:C64)', 'COUNTA(C8:C18)+R55', 'R55/R56']);
  assert.deepEqual([v.R55, v.R56], [undefined, undefined], 'sample 0/4 gone');
  // tables below moved down 3 rows: titles, data, analysis formulas, Daftar Isi links
  assert.match(v.B65, /Tabel P\.1\.5/); assert.match(v.B76, /Tabel P\.1\.6/); assert.match(v.B87, /Tabel P\.1\.7/);
  // P.1.5 is for Diploma/Sarjana Terapan: Magister leaves its rows empty, analysis still a formula (owner 2026-11-25)
  assert.deepEqual(['C69', 'E69', 'I69', 'J69'].map(r => v[r]), [undefined, undefined, undefined, undefined]);
  assert.deepEqual(['R69', 'R70', 'R71'].map(f), ['COUNTA(C69:C75)', 'COUNTA(C8:C18)+R55+R69', 'R69/R70']);
  // P.1.6 analysis: distinct lecturers per level over the shifted rows, Jumlah Dosen = P.1.1 rows
  const unik = c => `SUMPRODUCT((C80:C86<>"")*(${c}80:${c}86="V")/COUNTIFS(C80:C86,C80:C86&"",${c}80:${c}86,${c}80:${c}86&""))`;
  assert.deepEqual(['R80', 'R81', 'R82', 'R83'].map(f), [unik('I'), unik('J'), unik('K'), 'COUNTA(C8:C18)']);
  // P.1.7 analysis: V per education column over the tendik rows (7 template rows); DIV/S1 = I + J
  const n = c => `COUNTIF(${c}91:${c}97,"V")`;
  assert.deepEqual(['R91', 'R92', 'R93', 'R94', 'R95', 'R96'].map(f), [n('E'), n('F'), n('G'), n('H'), `${n('I')}+${n('J')}`, n('K')]);
  assert.deepEqual(['C80', 'E80', 'F80', 'H80', 'K80', 'L80'].map(r => v[r]),
    ['Dr. Uji', 'Keynote/invited speaker: Seminar Air', undefined, 'https://contoh.uji/st', 'V', '2025']);
  assert.deepEqual(['C91', 'H91', 'L91', 'M91', 'N91', 'C92'].map(r => v[r]), ['Laboran A', 'V', 'K3', 'Laboran', 'Program Studi', undefined]);
  assert.match(p1, /<c r="S80"[^>]*><f>R80\/R83<\/f>/);
  assert.match(p1, /<c r="S91"[^>]*><f>R91\/\$R\$97<\/f>/);
  assert.match(p1, /<c r="R97"[^>]*><f>SUM\(R91:R96\)<\/f>/);
  assert.match(p1, /<f t="shared" ref="S92:S96" si="4">R92\/\$R\$97<\/f>/);
  const di = h.xml[lembar['Daftar Isi']];
  for (const r of ['B4', 'B19', 'B40', 'B52', 'B65', 'B76', 'B87']) assert.match(di, new RegExp(`<f>P\\.1!${r}</f>`), r);
  // P.1.2 not filled: sample-row averages removed (no #DIV/0!, owner 2026-11-25)
  for (const r of ['C24', 'D24', 'F24']) assert.equal(v[r], undefined, `P.1!${r}`);
  assert.match(p1, /<c r="G24"( s="\d+")?\/>/);
  // rows stay in ascending order and unique
  const nomor = [...p1.matchAll(/<row r="(\d+)"/g)].map(m => +m[1]);
  assert.deepEqual(nomor, [...nomor].sort((a, b) => a - b)); assert.equal(new Set(nomor).size, nomor.length);
});

test('sisipBaris: Excel-style shift of rows, formulas, shared formulas, merges, validations', () => {
  const x = '<worksheet><dimension ref="A1:D9"/><sheetViews><sheetView><selection activeCell="B8" sqref="B8"/></sheetView></sheetViews>' +
    '<sheetData><row r="5" ht="15"><c r="B5" s="3"><v>1</v></c><c r="C5" s="4"><f>SUM(A5:B5)</f></c>' +
    '<c r="D5" s="4"><f t="shared" ref="D5:D6" si="0">B5*2</f></c></row>' +
    '<row r="6"><c r="B6" s="3"/><c r="D6" s="4"><f t="shared" si="0"/></c></row>' +
    '<row r="8"><c r="B8"><f>SUM(B5:B7)+$B$9+LOG10(B5)</f></c></row><row r="9"><c r="B9"><v>2</v></c></row></sheetData>' +
    '<mergeCells count="1"><mergeCell ref="B8:C9"/></mergeCells>' +
    '<dataValidations count="1"><dataValidation type="list" sqref="B5:B8 D9"><formula1>$B$5:$B$9</formula1></dataValidation></dataValidations></worksheet>';
  const y = sisipBaris(x, 'P.1', 7, 2);
  assert.match(y, /<dimension ref="A1:D11"\/>/);
  assert.match(y, /<selection activeCell="B10" sqref="B10"\/>/);
  // new rows 7, 8 copy row 6 (style; shared formula from master D5 translated); row 7 was absent, so old row 8 -> 10
  assert.match(y, /<row r="6">.*?<\/row><row r="7"><c r="B7" s="3"\/><c r="D7" s="4"><f>B7\*2<\/f><\/c><\/row><row r="8"><c r="B8" s="3"\/><c r="D8" s="4"><f>B8\*2<\/f><\/c><\/row><row r="10">/);
  assert.match(y, /<row r="10"><c r="B10"><f>SUM\(B5:B9\)\+\$B\$11\+LOG10\(B5\)<\/f><\/c><\/row><row r="11"><c r="B11"><v>2<\/v>/);
  assert.match(y, /<mergeCell ref="B10:C11"\/>/);
  assert.match(y, /sqref="B5:B10 D11"><formula1>\$B\$5:\$B\$11<\/formula1>/);
  assert.equal(sisipBaris(x, 'P.1', 7, 0), x);
  assert.equal(geserRujukanBaris('<f>P.1!B19</f><f>\'P.1\'!$B$4</f><f>E.4!B19</f>', 'P.1', 10, 3),
    '<f>P.1!B22</f><f>\'P.1\'!$B$4</f><f>E.4!B19</f>');
});

// L.1 from lkps_sarana_standar (165-patch, owner 2026-11-24); P.1.7 excludes interns (164-patch).
test('L.1 sarana by standard: category blocks, row insertion, Daftar Isi; P.1.7 without interns', () => {
  const s = (jenis, kategori, nama, extra = {}) => ({ jenis, kategori, nama, ...extra });
  const saranaStd = [
    ...Array.from({ length: 6 }, (_, i) => s('belajar', 'perabot', `Meja ${i + 1}`, { urutan: i })),
    s('belajar', 'media', 'Proyektor', { lokasi: 'Gd. A R.101', ukuran: '3000 lumen', nama_standar: 'SNI X', occupancy: '1 per kelas',
      standar_ditetapkan: '1 unit', ukuran_eksisting: '1 unit' }),
    s('belajar', 'k3', 'APAR'), s('kerja', null, 'Studio Desain'), s('diseminasi', null, 'Ruang Pamer'),
    s('kesejahteraan', null, 'Ruang Konseling'),
  ];
  const tendik = [{ nama: 'Admin A', jabatan: 'admin_prodi', pendidikan: 's1' },
    { nama: 'Aslab Magang', jabatan: 'asisten_lab', status_kerja: 'magang' }];
  const C5 = { ...C, daftar: { ...C.daftar, saranaStd, tendik } };
  const peta = petaLKPSLamdepilar(C5);
  assert.deepEqual(peta.sisipBaris, [{ lembar: 'L.1', baris: 11, n: 2 }]);
  const semua = Object.fromEntries(Object.values(lembar).map(p => [p, zip[p]()]));
  const h = isiLembar(semua, lembar, contoh, peta);
  const v = nilaiSel(h.xml[lembar['L.1']]);
  assert.deepEqual(['C8', 'C13'].map(r => v[r]), ['1. Meja 1', '6. Meja 6']);
  assert.match(v.C14, /Peralatan dan Media Pembelajaran/);
  assert.deepEqual(['C15', 'D15', 'E15', 'F15', 'G15', 'H15', 'I15'].map(r => v[r]),
    ['1. Proyektor', 'Gd. A R.101', '3000 lumen', 'SNI X', '1 per kelas', '1 unit', '1 unit']);
  assert.match(v.C29, /Keamanan dan Keselamatan/); assert.equal(v.C30, '1. APAR');
  assert.match(v.B36, /Tabel L\.1\.2/); assert.deepEqual([v.B40, v.C40], ['1', 'Studio Desain']);
  assert.match(v.B57, /Tabel L\.1\.3/); assert.deepEqual([v.B61, v.C61], ['1', 'Ruang Pamer']);
  assert.match(v.B78, /Tabel L\.1\.4/); assert.deepEqual([v.B82, v.C82], ['1', 'Ruang Konseling']);
  const di = h.xml[lembar['Daftar Isi']];
  const tautL1 = [...di.matchAll(/<f>L\.1!B(\d+)<\/f>/g)].map(m => +m[1]);
  assert.ok(tautL1.length > 0, 'Daftar Isi merujuk L.1');
  // Daftar Isi points at the criterion heading (B1, above the insertion) or a table title (shifted)
  for (const r of tautL1) assert.match(v[`B${r}`] || '', /^(Tabel L\.1|L\. Lingkungan)/, `Daftar Isi -> L.1!B${r}`);
  assert.ok(tautL1.some(r => r > 30), 'rujukan judul tabel di bawah sisipan ikut bergeser');
  for (const [nama, path] of Object.entries(lembar)) {
    for (const [ref, t] of Object.entries(nilaiSel(h.xml[path]))) assert.ok(!CONTOH.test(t.trim()), `contoh tersisa ${nama}!${ref}: ${t}`);
  }
  const p1 = nilaiSel(h.xml[lembar['P.1']]);
  assert.deepEqual([p1.C88, p1.M88, p1.C89], ['Admin A', 'Admin prodi', undefined]);
});

// P.1.2 from lkps_bimbingan_utama (167-patch, owner 2026-11-24): TS-2..TS, row insertion past 12 rows, formulas per row.
test('P.1.2 main supervisors: window TS-2..TS, zero rows skipped, insertion and formulas', () => {
  const b = (nidn, tahun_akademik, jumlah_ps, jumlah_ps_lain = 0) => ({ nidn, tahun_akademik, jumlah_ps, jumlah_ps_lain });
  const bimbinganUtama = [
    b('0001', '2023/2024', 2), b('0001', '2025/2026', 3, 1),
    ...Array.from({ length: 13 }, (_, i) => b(`B${String(i + 1).padStart(2, '0')}`, '2024/2025', 1)),
    b('Z99', '2025/2026', 0, 0),          // zero: not listed
    b('Y98', '2022/2023', 5),             // before TS-2: not listed
  ];
  const peta = petaLKPSLamdepilar({ ...C, daftar: { ...C.daftar, bimbinganUtama } });
  assert.deepEqual(peta.sisipBaris, [{ lembar: 'P.1', baris: 35, n: 2 }]);
  const semua = Object.fromEntries(Object.values(lembar).map(p => [p, zip[p]()]));
  const h = isiLembar(semua, lembar, contoh, peta);
  const x = h.xml[lembar['P.1']], v = nilaiSel(x);
  assert.deepEqual([v.B24, v.C24, v.E24, v.D24, v.F24], ['1', 'B01', '1', '0', '0']);   // unknown NIDN shown as is
  assert.deepEqual([v.B37, v.C37], ['14', 'Dr. Uji']);
  assert.deepEqual(['D37', 'E37', 'F37', 'H37', 'I37', 'J37'].map(r => v[r]), ['2', '0', '3', '0', '0', '1']);
  const f = ref => (new RegExp(`<c r="${ref}"[^>]*>\s*<f[^>]*>([^<]*)</f>`).exec(x) || [])[1]
    ?.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&');   // XML text -> formula
  assert.deepEqual(['G37', 'K37', 'L37'].map(f), ['AVERAGE(D37:F37)', 'AVERAGE(H37:J37)', 'AVERAGE(D37:K37)']);
  assert.equal(f('G30'), 'AVERAGE(D30:F30)');
  assert.match(v.B39 || '', /^Pada PS Lain/);
  assert.ok(!Object.values(v).includes('Z99') && !Object.values(v).includes('Y98'));
  // Analysis (owner 2026-11-25): formulas over the filled table, sample 4s gone, template ratios kept.
  const avg = 'D24:D37+E24:E37+F24:F37+H24:H37+I24:I37+J24:J37';
  assert.deepEqual(['R21', 'R22', 'U21', 'U22', 'R23', 'U23'].map(f),
    ['COUNTA(C24:C37)', 'COUNTA(C8:C18)', `SUMPRODUCT(--((${avg})/3>6))`, 'COUNTA(C8:C18)', 'R21/R22', 'U21/U22']);
  assert.deepEqual(['R21', 'R22', 'U21', 'U22'].map(r => v[r]), [undefined, undefined, undefined, undefined]);
  // P.1.1 analysis (owner 2026-11-25): counts over Table P.1.1; sample formulas X6 (=1) and X9 (=2/4) replaced.
  assert.deepEqual(['R6', 'R7', 'R8', 'U6', 'U7', 'U8', 'U9', 'U10', 'X6', 'X7', 'X8', 'X9'].map(f), [
    'COUNTIFS(C8:C18,"<>",L8:L18,"<>",M8:M18,"<>V")', 'COUNTA(C8:C18)', 'R6/R7',
    'COUNTIFS(C8:C18,"<>",J8:J18,"<>")', 'COUNTIFS(C8:C18,"<>",K8:K18,"<>")', 'COUNTA(C8:C18)', 'U6/U8', 'U7/U8',
    'COUNTIF(I8:I18,"Profesor")', 'COUNTIF(I8:I18,"Lektor Kepala")', 'COUNTA(C8:C18)', '(X6+X7)/X8']);
  assert.ok(!/<f>1<\/f>|<f>2\/4<\/f>/.test(x), 'no sample formula left');
  assert.ok(x.includes('<f>COUNTIFS(C8:C18,"&lt;&gt;",') && !x.includes('"<>"'), 'formula text escaped in XML');
});

test('P.1.2 sample-row averages removed whole: empty rows carry no #DIV/0! formula, filled rows keep theirs', () => {
  const bimbinganUtama = [{ nidn: '0001', tahun_akademik: '2025/2026', jumlah_ps: 3 }, { nidn: 'Q02', tahun_akademik: '2024/2025', jumlah_ps: 2 }];
  const peta = petaLKPSLamdepilar({ ...C, daftar: { ...C.daftar, bimbinganUtama } });
  const semua = Object.fromEntries(Object.values(lembar).map(p => [p, zip[p]()]));
  const x = isiLembar(semua, lembar, contoh, peta).xml[lembar['P.1']];
  const sel = ref => (new RegExp(`<c r="${ref}"(?=[\\s>/])[^>]*?(?:/>|>[\\s\\S]*?</c>)`).exec(x) || [''])[0];
  for (const r of [24, 25]) for (const c of 'GKL') assert.match(sel(`${c}${r}`), /<f>AVERAGE\(/, `${c}${r}`);
  for (const r of [26, 27]) for (const c of 'GKL') assert.match(sel(`${c}${r}`), /^<c r="[GKL]2[67]"( s="\d+")?\/>$/, `${c}${r} empty, style kept`);
  assert.ok(!/<f t="shared"[^>]*si="[012]"/.test(x), 'no shared group 0-2 left without its parent');
  assert.match(x, /<f t="shared" ref="K46:K48"/, 'other shared groups untouched');
});

test('P.1.2 and P.1.3 analysis follow rows inserted in Tables P.1.1 and P.1.3', () => {
  const dosen = Array.from({ length: 13 }, (_, i) => ({ id: `t${i}`, nidn: `T${String(i).padStart(2, '0')}`, nama: `Dosen ${String(i).padStart(2, '0')}`,
    kategori: 'tetap', dtps: true, peran: 'dosen', aktif: true }));
  const bimbinganUtama = [{ nidn: 'T00', tahun_akademik: '2025/2026', jumlah_ps: 9, jumlah_ps_lain: 12 }];
  const bkd = dosen.map((d, i) => ({ nidn: d.nidn, tahun_akademik: '2025/2026', sks_pendidikan: 2 * i }));
  const peta = petaLKPSLamdepilar({ ...C, daftar: { ...C.daftar, dosen, mk: [], bimbinganUtama, bkd } });
  const n11 = peta.sisipBaris.find(s => s.baris === 18)?.n;
  assert.equal(n11, 2, '13 lecturers in 11 rows');
  assert.equal(peta.sisipBaris.find(s => s.baris === 51)?.n, 6, '13 EWMP rows in 7');
  const semua = Object.fromEntries(Object.values(lembar).map(p => [p, zip[p]()]));
  const x = isiLembar(semua, lembar, contoh, peta).xml[lembar['P.1']], v = nilaiSel(x);
  const f = ref => (new RegExp(`<c r="${ref}"[^>]*>\s*<f[^>]*>([^<]*)</f>`).exec(x) || [])[1]
    ?.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&');   // XML text -> formula
  assert.deepEqual([v.C20, v.C26], ['Dosen 12', 'Dosen 00']);
  assert.deepEqual(['R23', 'R24', 'U23', 'U24', 'R25', 'U25'].map(f),
    ['COUNTA(C26:C37)', 'COUNTA(C8:C20)', 'SUMPRODUCT(--((D26:D37+E26:E37+F26:F37+H26:H37+I26:I37+J26:J37)/3>6))',
     'COUNTA(C8:C20)', 'R23/R24', 'U23/U24']);
  // P.1.1 analysis cells sit above the table: they stay put, their ranges widen.
  assert.deepEqual(['R6', 'R7', 'X6', 'X9'].map(f),
    ['COUNTIFS(C8:C20,"<>",L8:L20,"<>",M8:M20,"<>V")', 'COUNTA(C8:C20)', 'COUNTIF(I8:I20,"Profesor")', '(X6+X7)/X8']);
  // P.1.3 analysis moves down with P.1.1 (2 rows); its range covers the 13 rows incl. the 6 inserted.
  assert.deepEqual([v.C47, v.C59], ['Dosen 00', 'Dosen 12']);
  assert.deepEqual(['R44', 'R45', 'U44', 'U45', 'R46', 'U46'].map(f), ['SUMPRODUCT((C47:C59<>"")*(K47:K59/2<12))',
    'COUNTA(C47:C59)', 'SUMPRODUCT((C47:C59<>"")*(K47:K59/2>20))', 'COUNTA(C47:C59)', 'R44/R45', 'U44/U45']);
  // P.1.4 analysis moves down 2 + 6 rows; P.1.1 part of its denominator widens to row 20.
  assert.deepEqual(['R63', 'R64', 'R65'].map(f), ['COUNTA(C63:C69)', 'COUNTA(C8:C20)+R63', 'R63/R64']);
});

// A.5.1/A.5.2 from lkps_keuangan (169-patch, owner 2026-11-24): Magister block, rupiah -> million, A.5.3 formulas kept.
import { POS_A5 } from '../../site/keuangan-a5.js';
test('A.5 finance: Magister rows, million rupiah, empty years stay empty, neraca formulas intact', () => {
  const keuangan = [
    { tahun_akademik: '2023/2024', pos: 'ukt_bergelar', dana_upps: 1500000000, dana_ps: 250000000 },   // TS-2
    { tahun_akademik: '2025/2026', pos: 'ukt_bergelar', dana_upps: 1750000000, dana_ps: 300500000 },   // TS
    { tahun_akademik: '2024/2025', pos: 'biaya_bergelar_dosen', dana_ps: 120000000 },                  // TS-1, PS only
    { tahun_akademik: '2025/2026', pos: 'bantuan_investasi_prasarana', dana_upps: 0, dana_ps: 0 },
    { tahun_akademik: '2022/2023', pos: 'biaya_pkm', dana_ps: 999000000 },                             // before TS-2
  ];
  const peta = petaLKPSLamdepilar({ ...C, daftar: { ...C.daftar, keuangan } });
  assert.deepEqual(peta['A.5.1 '], { D118: 1500, H118: 250, F118: 1750, J118: 300.5, F161: 0, J161: 0 });
  assert.deepEqual(peta['A.5.2 '], { I66: 120 });
  const semua = Object.fromEntries(Object.values(lembar).map(p => [p, zip[p]()]));
  const h = isiLembar(semua, lembar, contoh, peta);
  const v1 = nilaiSel(h.xml[lembar['A.5.1 ']]), v2 = nilaiSel(h.xml[lembar['A.5.2 ']]);
  assert.deepEqual([v1.D118, v1.E118, v1.F118, v1.J118, v1.F161], ['1500', undefined, '1750', '300.5', '0']);
  assert.equal(v2.I66, '120');
  assert.equal(rumus(h.xml[lembar['A.5.3']]), rumus(zip[lembar['A.5.3']]()));   // neraca untouched
  assert.equal(rumus(h.xml[lembar['A.5.1 ']]), rumus(zip[lembar['A.5.1 ']]()));
  // every pos points at an input row (no formula there) in the Magister block
  for (const p of POS_A5) {
    const x = zip[lembar[p.lembar]]();
    for (const c of 'DEFHIJ') assert.ok(!new RegExp(`<c r="${c}${p.baris}"[^>]*>\s*<f`).test(x), `${p.kode} ${c}${p.baris} berumus`);
  }
  assert.equal(new Set(POS_A5.map(p => p.kode)).size, POS_A5.length);
});

// E.1.1/E.1.2 from lkps_mahasiswa_angkatan (171-patch, owner 2026-11-24): rows 8-12 = cohort TS-4..TS, formulas kept.
test('E.1 per cohort: TS-4..TS rows, foreign-student columns, older cohorts ignored, check formulas intact', () => {
  const angkatan = [
    { tahun_akademik: '2021/2022', daya_tampung: 30, pendaftar: 80, lulus_seleksi: 20, afirmasi: 2, transfer: 1, asing: 1,
      aktif: 3, tidak_aktif: 1, lulus: 19, gagal: 1, asing_penuh_waktu: 1, asing_satu_semester: 0 },          // TS-4
    { tahun_akademik: '2025/2026', daya_tampung: 30, pendaftar: 95, lulus_seleksi: 25, aktif: 25 },              // TS
    { tahun_akademik: '2020/2021', daya_tampung: 99, pendaftar: 999 },                                            // before TS-4
  ];
  const peta = petaLKPSLamdepilar({ ...C, daftar: { ...C.daftar, angkatan } });
  assert.deepEqual(peta['E.1'], { C8: 30, D8: 80, E8: 20, F8: 2, G8: 1, H8: 1, I8: 3, J8: 1, K8: 19, L8: 1, T8: 1, U8: 0,
    C12: 30, D12: 95, E12: 25, I12: 25 });
  const semua = Object.fromEntries(Object.values(lembar).map(p => [p, zip[p]()]));
  const h = isiLembar(semua, lembar, contoh, peta);
  const v = nilaiSel(h.xml[lembar['E.1']]);
  assert.deepEqual([v.C8, v.K8, v.U8, v.E12, v.F12, v.C9, v.T12], ['30', '19', '0', '25', undefined, undefined, undefined]);
  assert.equal(rumus(h.xml[lembar['E.1']]), rumus(zip[lembar['E.1']]()));   // N, S, Jumlah, E.1.3 untouched
});

// calcChain dropped from the download (2026-11-25): row insertion and removed sample formulas make it stale.
import { tanpaCalcChain } from '../../site/lkps-lamdepilar.js';
test('tanpaCalcChain removes only the calcChain relationship and content type', () => {
  const rels = zip['xl/_rels/workbook.xml.rels'](), types = zip['[Content_Types].xml']();
  const t = tanpaCalcChain(rels, types);
  assert.ok(/calcChain/.test(rels) && /calcChain/.test(types), 'template has calcChain');
  assert.ok(!/calcChain/.test(t.rels) && !/calcChain/.test(t.types));
  assert.equal((t.rels.match(/<Relationship\b/g) || []).length, (rels.match(/<Relationship\b/g) || []).length - 1);
  assert.equal((t.types.match(/<Override\b/g) || []).length, (types.match(/<Override\b/g) || []).length - 1);
});

test('P.1.5 practitioners are listed for non-Magister programmes (Diploma/Sarjana Terapan)', () => {
  const dosen = [{ id: 'c', nidn: '0003', nama: 'Praktisi', kategori: 'industri', peran: 'dosen', aktif: true, pendidikan: 'S2', perusahaan: 'PT Air' }];
  const peta = petaLKPSLamdepilar({ ...C, jenjang: 'Sarjana Terapan', daftar: { ...C.daftar, dosen, mk: [] } });
  assert.equal(peta['P.1'].C66, 'Praktisi');
  assert.equal(peta['P.1'].E66, 'PT Air');
  assert.equal(petaLKPSLamdepilar({ ...C, daftar: { ...C.daftar, dosen, mk: [] } })['P.1'].C66, undefined, 'Magister: empty');
});
