// Evaluasi pembelajaran (pemilik 2026-11-12; instal-lengkap.sql).
import test from 'node:test';
import assert from 'node:assert/strict';
import { bacaTempelEDOM, cplPerMK, statusEvaluasi, rekapSemester, tugasEvaluasi, semesterKini, urutSemester, tsDariTA, angka,
  penerimaRefleksi, penerimaTindakEval }
  from '../../site/evaluasi-pembelajaran.js';

const DOSEN = [{ id: 'a', nama: 'Ani Contoh, S.T., M.T.', email: 'ani@contoh.ac.id', nidn: '0011' },
               { id: 'b', nama: 'Budi Contoh', email: 'budi@contoh.ac.id', nidn: '0022' }];

test('tempel dari Excel: judul kolom dikenali dalam urutan apa pun; email, NIDN, nama', () => {
  const teks = 'Nama Dosen\tKode MK\tMata Kuliah\tNilai EDOM\tJumlah responden\n'
    + 'ani@contoh.ac.id\tsi 2101\tHidrologi\t2,75\t40\n0022\tSI2102\tStatika\t3.6\t38\nBudi Contoh\tSI2103\tBeton\t3,9\t';
  const r = bacaTempelEDOM(teks, DOSEN);
  assert.deepEqual(r.map(x => [x.baris, x.kode_mk, x.nama_mk, x.dosen_id, x.edom, x.responden, x.galat.length]),
    [[2, 'SI2101', 'Hidrologi', 'a', 2.75, 40, 0], [3, 'SI2102', 'Statika', 'b', 3.6, 38, 0], [4, 'SI2103', 'Beton', 'b', 3.9, null, 0]]);
});

test('tempel tanpa judul: urutan kode, dosen, nilai; galat per baris', () => {
  const r = bacaTempelEDOM('SI2101;ani@contoh.ac.id;3,10\nSI2101;ANI@contoh.ac.id;3,2\nSI2104;zaki@x.id;3\nSI2105;0011;4,5\n;0022;3', DOSEN);
  assert.equal(r[0].edom, 3.1);
  assert.match(r[1].galat[0], /sudah ada di atas/);
  assert.match(r[2].galat[0], /tidak dikenal/);
  assert.match(r[3].galat[0], /harus 0–4/);
  assert.match(r[4].galat[0], /kode MK kosong/);
  assert.deepEqual(bacaTempelEDOM('', DOSEN), []);
});

const RINGKAS = { kelas: [
  { term: '2025/2026 Ganjil', course_code: 'si2101', class_name: 'A', cpl: 'CPL3', share: 0.4, status: 'BELUM' },
  { term: '2025/2026 Ganjil', course_code: 'SI2101', class_name: 'B', cpl: 'CPL3', share: 0.7, status: 'TERCAPAI' },
  { term: '2025/2026 Genap', course_code: 'SI2101', class_name: 'A', cpl: 'CPL3', share: 0.1, status: 'BELUM' },
  { term: '2025/2026 Ganjil', course_code: 'SI2102', class_name: 'A', cpl: 'CPL1', share: 0.9, status: 'TERCAPAI' }] };

test('CPL kelas per MK hanya untuk semester itu', () => {
  const m = cplPerMK(RINGKAS, '2025/2026', 'Ganjil');
  assert.deepEqual(m.get('SI2101').belum, ['CPL3 kelas A']);
  assert.equal(m.get('SI2101').terendah, 0.4);
  assert.deepEqual(m.get('SI2102').belum, []);
  assert.equal(cplPerMK(null, '2025/2026', 'Ganjil').size, 0);
});

test('status: alasan perlu tindak lanjut dan keadaan tindak lanjutnya', () => {
  const m = cplPerMK(RINGKAS, '2025/2026', 'Ganjil');
  const a = statusEvaluasi({ kode_mk: 'SI2101', edom: 2.75, rps_sesuai: 'tidak' }, m.get('SI2101'), 3);
  assert.deepEqual(a.alasan, ['EDOM 2,75 di bawah 3,00', 'CPL belum tercapai: CPL3 kelas A', 'pelaksanaan tidak sesuai RPS']);
  assert.equal(a.tl, 'belum');
  assert.equal(statusEvaluasi({ edom: 3.5 }, null, 3).tl, 'tidak_perlu');
  assert.equal(statusEvaluasi({ edom: 3 }, null, 3).perlu, false);          // tepat di ambang = tidak perlu
  assert.equal(statusEvaluasi({ edom: 2 }, null, 3, [{ status: 'selesai' }, { status: 'proses' }]).tl, 'proses');
  assert.equal(statusEvaluasi({ edom: 2 }, null, 3, [{ status: 'selesai' }]).tl, 'selesai');
});

test('rekap semester', () => {
  const rows = [{ id: 1, kode_mk: 'SI2101', edom: 2.75, rps_sesuai: 'sebagian' }, { id: 2, kode_mk: 'SI2102', edom: 3.6 }, { id: 3, kode_mk: 'SI2103', edom: null }];
  const r = rekapSemester(rows, cplPerMK(RINGKAS, '2025/2026', 'Ganjil'), 3, new Map([[1, [{ status: 'proses' }]]]));
  assert.deepEqual({ ...r, rerata: Math.round(r.rerata * 1000) / 1000 },
    { jumlah: 3, berEdom: 2, rerata: 3.175, bawah: 1, rpsTerisi: 1, perlu: 1, perluBelumTL: 0, tlSelesai: 0 });
});

test('Tugas saya: refleksi semester terbaru yang kosong dan tindak lanjut ber-PJ saya', () => {
  const saya = { id: 'a' };
  const evaluasi = [{ dosen_id: 'a', tahun_akademik: '2025/2026', semester: 'Ganjil', kode_mk: 'SI2101' },
    { dosen_id: 'a', tahun_akademik: '2025/2026', semester: 'Ganjil', kode_mk: 'SI2105', rps_sesuai: 'sesuai' },
    { dosen_id: 'a', tahun_akademik: '2024/2025', semester: 'Genap', kode_mk: 'SI1101' }];
  const tindakEval = [{ pj_id: 'a', status: 'terbuka', rencana: 'Revisi RPS', masalah: 'EDOM rendah', tenggat: '2026-11-10',
    evaluasi_mk: { kode_mk: 'SI2101', tahun_akademik: '2025/2026', semester: 'Ganjil' } },
    { pj_id: 'a', status: 'selesai', rencana: 'x', masalah: 'y' }, { pj_id: 'b', status: 'terbuka', rencana: 'x', masalah: 'y' },
    { pj_id: 'a', status: 'proses', rencana: 'Pendampingan', masalah: 'CPL rendah', evaluasi_mk: null }];
  const t = tugasEvaluasi({ saya, evaluasi, tindakEval }, new Date(2026, 10, 12));
  assert.equal(t.length, 3);
  assert.equal(t[2].judul, 'Tindak lanjut evaluasi pembelajaran: Pendampingan');   // PJ bukan pengampu: tanpa kode MK
  assert.equal(t[2].href, 'evaluasi-pembelajaran.html');
  assert.equal(t[0].judul, 'Evaluasi pembelajaran 2025/2026 Ganjil: 1 mata kuliah belum diisi');
  assert.equal(t[0].href, 'evaluasi-pembelajaran.html?ta=2025%2F2026&sm=Ganjil');
  assert.equal(t[1].judul, 'Tindak lanjut SI2101: Revisi RPS');
  assert.equal(t[1].hari, -2);
});

test('semester berjalan, urutan semester, TS, angka', () => {
  assert.deepEqual(semesterKini(new Date(2026, 10, 12)), { ta: '2026/2027', sm: 'Ganjil' });
  assert.deepEqual(semesterKini(new Date(2027, 1, 20)), { ta: '2026/2027', sm: 'Ganjil' });
  assert.deepEqual(semesterKini(new Date(2027, 2, 1)), { ta: '2026/2027', sm: 'Genap' });
  const xs = [{ ta: '2024/2025', sm: 'Genap' }, { ta: '2025/2026', sm: 'Ganjil' }, { ta: '2025/2026', sm: 'Genap' }].sort(urutSemester);
  assert.deepEqual(xs.map(x => `${x.ta} ${x.sm}`), ['2025/2026 Genap', '2025/2026 Ganjil', '2024/2025 Genap']);
  assert.equal(tsDariTA('2025/2026'), 2026);
  assert.equal(angka(3), '3,00');
});

test('pengingat refleksi: semester terbaru saja, dosen aktif bukan asesor', () => {
  const ds = [...DOSEN, { id: 'c', nama: 'Cici', email: 'cici@x.id', aktif: false }, { id: 'z', nama: 'Asesor', email: 'z@x.id', peran: 'asesor' }];
  const ev = [{ dosen_id: 'a', tahun_akademik: '2025/2026', semester: 'Genap', kode_mk: 'SI2201', nama_mk: 'Hidrolika' },
    { dosen_id: 'b', tahun_akademik: '2025/2026', semester: 'Genap', kode_mk: 'SI2202', rps_sesuai: 'sesuai' },
    { dosen_id: 'b', tahun_akademik: '2025/2026', semester: 'Ganjil', kode_mk: 'SI2102' },
    { dosen_id: 'c', tahun_akademik: '2025/2026', semester: 'Genap', kode_mk: 'SI2203' },
    { dosen_id: 'z', tahun_akademik: '2025/2026', semester: 'Genap', kode_mk: 'SI2204' }];
  const r = penerimaRefleksi(ds, ev);
  assert.deepEqual(r.semester, { ta: '2025/2026', sm: 'Genap' });
  assert.deepEqual(r.penerima, [{ nama: 'Ani Contoh, S.T., M.T.', email: 'ani@contoh.ac.id', rinci: '- SI2201 Hidrolika' }]);
  assert.deepEqual(penerimaRefleksi(ds, []), { semester: null, penerima: [] });
});

test('pengingat tindak lanjut evaluasi: 14 hari ke depan sampai setahun lewat, per PJ', () => {
  const kini = new Date(2026, 10, 12);
  const mk = { kode_mk: 'SI2201', tahun_akademik: '2025/2026', semester: 'Genap' };
  const t = [{ pj_id: 'b', status: 'terbuka', rencana: 'Studi kasus', tenggat: '2026-11-20', evaluasi_mk: mk },
    { pj_id: 'b', status: 'proses', rencana: 'Revisi RPS', tenggat: '2026-11-10', evaluasi_mk: null },
    { pj_id: 'b', status: 'terbuka', rencana: 'Jauh', tenggat: '2026-12-31' },
    { pj_id: 'b', status: 'terbuka', rencana: 'Lama', tenggat: '2025-10-01' },
    { pj_id: 'b', status: 'selesai', rencana: 'Beres', tenggat: '2026-11-12' },
    { pj_id: 'x', status: 'terbuka', rencana: 'Tanpa PJ', tenggat: '2026-11-12' }];
  const r = penerimaTindakEval(DOSEN, t, kini);
  assert.equal(r.penerima.length, 1);
  assert.equal(r.penerima[0].rinci, '- Studi kasus (SI2201 2025/2026 Genap); tenggat 20/11/2026, 8 hari lagi\n- Revisi RPS; tenggat 10/11/2026, lewat 2 hari');
  assert.deepEqual(r.tanpaPJ.map(x => x.rencana), ['Tanpa PJ']);
});

test('O1: tindak lanjut yang perlu tetapi belum ada masuk Tugas saya; GKM mendapat butir pantau', () => {
  const perluTL = [{ evaluasi_id: 1, dosen_id: 'a', tahun_akademik: '2026/2027', semester: 'Ganjil', kode_mk: 'SI101', nama_mk: 'Statika',
                     alasan: ['CPL belum tercapai: CPL1 kelas A'] },
                   { evaluasi_id: 2, dosen_id: 'b', tahun_akademik: '2026/2027', semester: 'Ganjil', kode_mk: 'SI103', alasan: ['EDOM 2,50 di bawah 3,00'] }];
  const dosen = tugasEvaluasi({ saya: { id: 'a' }, evaluasi: [], tindakEval: [], perluTL: [perluTL[0]] });
  assert.equal(dosen.length, 1);
  assert.match(dosen[0].judul, /Tindak lanjut evaluasi SI101 Statika \(2026\/2027 Ganjil\)/);
  assert.match(dosen[0].rinci, /CPL1 kelas A\. Isi masalah/);
  assert.equal(dosen[0].href, 'evaluasi-pembelajaran.html?ta=2026%2F2027&sm=Ganjil');
  const gkm = tugasEvaluasi({ saya: { id: 'g' }, evaluasi: [], tindakEval: [], perluTL, tanpaBaris: [{ kode_mk: 'SI102' }] });
  assert.equal(gkm.length, 1);
  assert.equal(gkm[0].judul, 'Pantau evaluasi pembelajaran');
  assert.match(gkm[0].rinci, /2 mata kuliah × dosen perlu tindak lanjut.*1 mata kuliah dengan CPL belum tercapai.*SI102/);
});
