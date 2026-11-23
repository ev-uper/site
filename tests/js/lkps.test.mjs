// site/lkps.js: LKPS cell map and XML cell writer (owner 2026-11-04).
// Fictitious data. Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { petaLKPS, tulisSel, hitungUlangSaatBuka, petaLembar, serialTS, indeksKolom }
  from '../../site/lkps.js';

const TS = 2026;
const D = {
  akreditasi: {
    sumber_dana: [
      { tahun: 2024, kategori: 'penelitian', luar_negeri: 1, dalam_negeri: 2, pt_mandiri: 3 },
      { tahun: 2026, kategori: 'penelitian', luar_negeri: 0, dalam_negeri: 4, pt_mandiri: 5 },
      { tahun: 2026, kategori: 'pkm', luar_negeri: 0, dalam_negeri: 1, pt_mandiri: 6 },
      { tahun: 2023, kategori: 'penelitian', luar_negeri: 9, dalam_negeri: 9, pt_mandiri: 9 },
    ],
    publikasi_dtps: [{ tahun: 2025, na1: 1, na2: 2, na3: 0, na4: 3, nb1: 0, nb2: 1, nb3: 4 }],
    publikasi_mhs: [{ tahun: 2026, na2: 2 }],
    ta: [{ tahun_ts: 2026, mahasiswa_aktif: 259, mahasiswa_asing: 1, lulusan: 40, rerata_ipk: 3.21 },
         { tahun_ts: 2024, mahasiswa_aktif: 230, mahasiswa_asing: 0, lulusan: 0, rerata_ipk: 0 }],
    kepuasan: [{ tahun_ts: 2026, aspek: 'etika', sangat_baik: 50, baik: 30, cukup: 20, kurang: 0 },
               { tahun_ts: 2026, aspek: 'pengembangan_diri', sangat_baik: 40, baik: 40, cukup: 10, kurang: 10 },
               { tahun_ts: 2025, aspek: 'etika', sangat_baik: 1, baik: 1, cukup: 1, kurang: 97 }],
  },
  tracer: [{ tahun_lulus: 2024, lulusan: 30, terlacak: 12, kerja_wilayah: 2, kerja_nasional: 8, kerja_internasional: 1 },
           { tahun_lulus: 2026, lulusan: 99, terlacak: 99 }],                     // TS itself: not in window
};
const P = petaLKPS({ D, ts: TS, prodi: 'Teknik Contoh', institusi: 'Universitas Contoh',
                     rencanaKepuasan: { etika: 'Pelatihan etika profesi' } });

test('Menu: identity, programme, TS date 31/08/TS', () => {
  assert.equal(P.Menu.H7, 'Universitas Contoh');
  assert.equal(P.Menu.H11, 'Sarjana');
  assert.equal(P.Menu.H23, 'Teknik Contoh');
  assert.deepEqual(P.Menu.S73, { tanggal: serialTS(2026) });
  assert.equal(serialTS(2026), 46265);                 // 31 Aug 2026 in Excel's 1900 system
});

test('3b / 3c: rows PT+mandiri, domestic, foreign; columns TS-2..TS', () => {
  assert.deepEqual([P['3b'].C9, P['3b'].C10, P['3b'].C11], [3, 2, 1]);   // 2024 = TS-2
  assert.deepEqual([P['3b'].D9, P['3b'].D10, P['3b'].D11], [0, 0, 0]);   // 2025 empty
  assert.deepEqual([P['3b'].E9, P['3b'].E10, P['3b'].E11], [5, 4, 0]);
  assert.deepEqual([P['3c'].E10, P['3c'].E11, P['3c'].E12], [6, 1, 0]);  // 3c starts one row lower
});

test('4d / 6e1: NA1..NB3 on rows 7..13', () => {
  assert.deepEqual([7, 8, 9, 10, 11, 12, 13].map(b => P['4d'][`D${b}`]), [1, 2, 0, 3, 0, 1, 4]);
  assert.equal(P['6e1'].E8, 2);
  assert.equal(P['6e1'].C8, 0);
});

test('6a / 6b: students per TS, graduates only where present', () => {
  assert.deepEqual([P['6a'].B7, P['6a'].C7, P['6a'].D7, P['6a'].F7, P['6a'].I7],
                   ['Teknik Contoh', 'V', 230, 259, 1]);
  assert.equal(P['6a'].E7, undefined);                // no TA row for 2025
  assert.deepEqual([P['6b'].C8, P['6b'].E8], [40, 3.21]);
  assert.equal(P['6b'].C6, undefined);                // 2024 had no graduates
});

test('6f1 / 6f2 / 6g1: graduation years TS-2 and TS-1 only', () => {
  assert.deepEqual([P['6f1'].B31, P['6f1'].C31], [30, 12]);      // Sarjana block
  assert.deepEqual([P['6g1'].D7, P['6g1'].E7, P['6g1'].F7, P['6g1'].G7], [12, 2, 8, 1]);
  assert.equal(P['6f1'].B32, undefined);
});

test('6g2: aspects of TS in template order, with follow-up plan', () => {
  assert.deepEqual([P['6g2'].C7, P['6g2'].F7, P['6g2'].G7], [50, 0, 'Pelatihan etika profesi']);
  assert.deepEqual([P['6g2'].C13, P['6g2'].F13], [40, 10]);
  assert.equal(P['6g2'].C8, undefined);
});

// ----------------------------------------------------------------- writer
const XML = '<worksheet><sheetData>'
  + '<row r="7" spans="1:6"><c r="A7" s="3"><v>1</v></c><c r="C7" s="9"/><c r="F7" s="4"><f>SUM(C7:E7)</f><v>0</v></c></row>'
  + '<row r="9"/>'
  + '</sheetData></worksheet>';

test('tulisSel: replaces an existing cell and keeps its style', () => {
  const x = tulisSel(XML, 'C7', 12);
  assert.ok(x.includes('<c r="C7" s="9"><v>12</v></c>'));
  assert.ok(x.includes('<f>SUM(C7:E7)</f>'));
});

test('tulisSel: inserts a missing cell in column order', () => {
  const x = tulisSel(XML, 'D7', 'ab<c>');
  assert.ok(/<c r="C7" s="9"\/><c r="D7" t="inlineStr"><is><t xml:space="preserve">ab&lt;c&gt;<\/t><\/is><\/c><c r="F7"/.test(x));
});

test('tulisSel: fills an empty self-closing row and creates missing rows in order', () => {
  assert.ok(tulisSel(XML, 'B9', 5).includes('<row r="9"><c r="B9"><v>5</v></c></row>'));
  const x = tulisSel(XML, 'A8', 1);
  assert.ok(x.indexOf('<row r="8">') > x.indexOf('<row r="7"') && x.indexOf('<row r="8">') < x.indexOf('<row r="9"'));
  assert.ok(tulisSel(XML, 'A20', 1).includes('<row r="20"><c r="A20"><v>1</v></c></row></sheetData>'));
});

test('tulisSel: never overwrites a formula; row 7 is not row 70', () => {
  assert.throws(() => tulisSel(XML, 'F7', 1), /rumus/);
  const x = tulisSel('<sheetData><row r="70"><c r="C70"/></row></sheetData>', 'C7', 2);
  assert.ok(x.startsWith('<sheetData><row r="7">'));
});

test('helpers: column index, recalc flag, sheet map', () => {
  assert.deepEqual([indeksKolom('A1'), indeksKolom('Z9'), indeksKolom('AB3')], [1, 26, 28]);
  assert.equal(hitungUlangSaatBuka('<workbook><calcPr calcId="191029"/></workbook>'),
               '<workbook><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>');
  const wb = '<sheets><sheet name="Menu" sheetId="1" r:id="rId1"/><sheet name="3b" sheetId="2" r:id="rId7"/></sheets>';
  const rels = '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/><Relationship Id="rId7" Target="/xl/worksheets/sheet9.xml"/>';
  assert.deepEqual(petaLembar(wb, rels), { Menu: 'xl/worksheets/sheet1.xml', '3b': 'xl/worksheets/sheet9.xml' });
});
