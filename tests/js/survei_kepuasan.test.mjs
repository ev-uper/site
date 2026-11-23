// Survei kepuasan daring (owner 2026-11-11; instal-lengkap.sql).
import test from 'node:test';
import assert from 'node:assert/strict';
import { KELOMPOK_SURVEI, templatSurvei, cekPertanyaan, hitungDariJawaban, rekapSurvei, komentarSurvei,
  keTabel62, csvJawaban, htmlRekap } from '../../site/survei-kepuasan.js';
import { ASPEK_KEPUASAN } from '../../site/butir-manual.js';

test('every group has a valid template; employer survey uses the seven 6.g.2 aspects', () => {
  for (const [k] of KELOMPOK_SURVEI) assert.equal(cekPertanyaan(templatSurvei(k)), '', k);
  assert.deepEqual(KELOMPOK_SURVEI.map(x => x[0]), ['mahasiswa', 'dosen', 'tendik', 'mitra', 'pengguna', 'alumni']);
  // The seven 6.g.2 aspects keep their codes and order; other scale items (e.g. VMTS) are ignored by keTabel62.
  const p = templatSurvei('pengguna').filter(q => q.jenis === 'skala').map(q => q.id);
  assert.deepEqual(p.filter(id => ASPEK_KEPUASAN.some(a => a[0] === id)), ASPEK_KEPUASAN.map(a => a[0]));
  assert.equal(keTabel62({ uv1: [0, 0, 1, 0] }, 2027).length, 0);
  const t = templatSurvei('mahasiswa'); t[0].teks = 'ubah';
  assert.notEqual(templatSurvei('mahasiswa')[0].teks, 'ubah');   // copies, not shared objects
});

test('question checks', () => {
  assert.match(cekPertanyaan([]), /paling sedikit/i);
  assert.match(cekPertanyaan([{ id: 'A', teks: 'x', jenis: 'skala' }]), /kode/);
  assert.match(cekPertanyaan([{ id: 'a', teks: 'x', jenis: 'skala' }, { id: 'a', teks: 'y', jenis: 'skala' }]), /dua kali/);
  assert.match(cekPertanyaan([{ id: 'a', teks: ' ', jenis: 'skala' }]), /teks kosong/);
  assert.equal(cekPertanyaan([{ id: 'a', teks: 'x', jenis: 'teks' }]), '');          // general form, no scale needed
  assert.match(cekPertanyaan([{ id: 'a', teks: 'x', jenis: 'pilihan', opsi: ['y'] }]), /dua opsi/);
  assert.match(cekPertanyaan([{ id: 'a', teks: 'x', jenis: 'angka', min: 5, max: 1 }]), /batas bawah/);
  const st = { id: 'st', teks: 'Status', jenis: 'pilihan', opsi: ['bekerja', 'studi'] };
  assert.equal(cekPertanyaan([st, { id: 'b', teks: 'Bulan', jenis: 'angka', syarat: { q: 'st', nilai: ['bekerja'] } }]), '');
  assert.match(cekPertanyaan([st, { id: 'b', teks: 'Bulan', jenis: 'angka', syarat: { q: 'st', nilai: ['pensiun'] } }]), /nilai syarat/);
  assert.match(cekPertanyaan([{ id: 'b', teks: 'Bulan', jenis: 'angka', syarat: { q: 'st', nilai: ['bekerja'] } }, st]), /sebelumnya/);
});

const PQ = [{ id: 'q1', aspek: 'keandalan', teks: 'A', jenis: 'skala' }, { id: 'q2', aspek: 'keandalan', teks: 'B', jenis: 'skala' },
  { id: 'q3', aspek: 'empati', teks: 'C', jenis: 'skala' }, { id: 'saran', aspek: 'saran', teks: 'Saran', jenis: 'teks' }];
const ROWS = [{ jawaban: { q1: 4, q2: 3, q3: 2, saran: 'Perbanyak <praktikum>' } }, { jawaban: { q1: 2, q2: 3, q3: 1 } },
  { jawaban: { q1: 4, q2: 4, q3: 3, saran: ' ' } }, { jawaban: { q1: 9, q2: '3' } }];

test('counts ignore invalid values; summary per question, aspect and overall', () => {
  const h = hitungDariJawaban(PQ, ROWS);
  assert.deepEqual(h, { q1: [0, 1, 0, 2], q2: [0, 0, 2, 1], q3: [1, 1, 1, 0] });
  const r = rekapSurvei(PQ, h);
  assert.equal(r.per.length, 3);
  assert.equal(r.per[0].rerata, 3.33);
  assert.equal(r.per[0].puas, 66.67);
  assert.equal(r.aspek.find(a => a.aspek === 'keandalan').rerata, 3.33);   // (3.33 + 3.33) / 2
  assert.equal(r.aspek.find(a => a.aspek === 'empati').puas, 33.33);
  assert.equal(rekapSurvei(PQ, {}).rerata, null);
});

test('comments only from text questions, blanks dropped; CSV has one line per response', () => {
  const k = komentarSurvei(PQ, ROWS);
  assert.deepEqual(k.map(x => x.isi), [['Perbanyak <praktikum>']]);
  const csv = csvJawaban(PQ, ROWS);
  assert.equal(csv.charCodeAt(0), 0xFEFF);
  assert.equal(csv.split('\r\n').length, ROWS.length + 1);
});

test('Tabel 6.g.2 rows: percentages per aspect add up to exactly 100', () => {
  const h = { etika: [1, 1, 1, 0], komunikasi: [0, 0, 1, 2] };
  const rows = keTabel62(h, 2027);
  assert.equal(rows.length, 2);
  for (const r of rows) {
    assert.equal(r.tahun_akademik, '2026/2027');
    assert.equal(Math.round((r.sangat_baik + r.baik + r.cukup + r.kurang) * 100), 10000);
  }
  assert.deepEqual(rows.find(r => r.aspek === 'komunikasi'), { tahun_akademik: '2026/2027', aspek: 'komunikasi', kurang: 0, cukup: 0, baik: 33.33, sangat_baik: 66.67 });
});

test('rendered summary escapes question text and handles no respondents', () => {
  const html = htmlRekap(rekapSurvei([{ id: 'q', aspek: 'x', teks: '<b>', jenis: 'skala' }], { q: [0, 0, 1, 1] }), 2);
  assert.match(html, /&lt;b&gt;/);
  assert.match(html, /2 responden/);
  assert.match(htmlRekap(rekapSurvei(PQ, {}), 0), /Belum ada responden/);
});

import { cekJawaban, aktifQ, bacaOpsi, bacaSyarat, teksSyarat, ringkasLain, aspekTindakLanjut, temuanDariAspek,
  masukanKurikulum, csvKurikulum } from '../../site/survei-kepuasan.js';

const F = [{ id: 'st', teks: 'Status', jenis: 'pilihan', opsi: ['bekerja', 'studi'] },
  { id: 'bln', teks: 'Bulan', jenis: 'angka', min: 0, max: 60, wajib: true, syarat: { q: 'st', nilai: ['bekerja'] } },
  { id: 'bd', teks: 'Bidang', jenis: 'centang', opsi: ['air', 'struktur'] },
  { id: 'ktr', teks: 'Kantor', jenis: 'singkat' }];

test('answer checks mirror the SQL rules, including conditions', () => {
  assert.equal(cekJawaban(F, { st: 'bekerja', bln: 3, bd: ['air'] }), '');
  assert.match(cekJawaban(F, { st: 'bekerja' }), /wajib/);
  assert.match(cekJawaban(F, { st: 'studi', bln: 3 }), /tidak berlaku/);
  assert.equal(cekJawaban(F, { st: 'studi', bd: [] }), '');
  assert.match(cekJawaban(F, { st: 'bekerja', bln: 99 }), /rentang/);
  assert.match(cekJawaban(F, { st: 'x' }), /tidak dikenal/);
  assert.match(cekJawaban(F, { st: 'studi', ktr: 'x'.repeat(201) }), /200/);
  assert.equal(aktifQ(F[1], { st: 'studi' }), false);
});

test('editor text formats', () => {
  assert.deepEqual(bacaOpsi(' a; b ;; a; c '), ['a', 'b', 'c']);
  assert.deepEqual(bacaSyarat('st = bekerja|studi lanjut'), { q: 'st', nilai: ['bekerja', 'studi lanjut'] });
  assert.equal(bacaSyarat('salah'), null);
  assert.equal(teksSyarat({ q: 'st', nilai: ['a', 'b'] }), 'st=a|b');
});

test('option and number summaries match the public rekap shape', () => {
  const r = ringkasLain(F, [{ jawaban: { st: 'bekerja', bln: 2, bd: ['air', 'struktur'] } }, { jawaban: { st: 'studi', bd: ['air'] } }, { jawaban: { st: 'bekerja', bln: 5 } }]);
  assert.deepEqual(r.opsi.st, { bekerja: 2, studi: 1 });
  assert.deepEqual(r.opsi.bd, { air: 2, struktur: 1 });
  assert.deepEqual(r.angka.bln, [2, 3.5]);
});

test('follow-up flags use either threshold; curriculum aspects map to butir 12', () => {
  const rk = { aspek: [{ aspek: 'a', label: 'A', rerata: 3.2, puas: 70 }, { aspek: 'b', label: 'B', rerata: 2.9, puas: 80 },
    { aspek: 'c', label: 'C', rerata: 3.5, puas: 90 }, { aspek: 'kurikulum', label: 'Kurikulum', rerata: 2.5, puas: 50 }] };
  const t = aspekTindakLanjut(rk, { ambang_puas: 75, ambang_rerata: 3 });
  assert.deepEqual(t.map(a => a.aspek), ['a', 'b', 'kurikulum']);
  assert.equal(t[2].alasan.length, 2);
  const s = { id: 7, judul: 'Survei mhs', tahun_ts: 2027, kelompok: 'mahasiswa' };
  assert.equal(temuanDariAspek(s, t[0], 40).butir, 57);
  const k = temuanDariAspek(s, t[2], 40);
  assert.deepEqual([k.butir, k.standar, k.kode, k.kategori], [12, 'Kurikulum', 'SV7-kurikulum', 'peluang']);
  assert.equal(temuanDariAspek({ ...s, kelompok: 'mitra' }, t[0], 5).butir, 7);
});

test('curriculum input is gathered across surveys and split internal/external', () => {
  const sv = [{ id: 1, judul: 'Mhs', kelompok: 'mahasiswa', tahun_ts: 2027, pertanyaan: templatSurvei('mahasiswa') },
    { id: 2, judul: 'Pengguna', kelompok: 'pengguna', tahun_ts: 2027, pertanyaan: templatSurvei('pengguna') },
    { id: 3, judul: 'Tendik', kelompok: 'tendik', tahun_ts: 2027, pertanyaan: templatSurvei('tendik') }];
  const jw = new Map([[1, [{ jawaban: { mk1: 4, mk2: 'Tambah BIM' } }, { jawaban: { mk1: 2 } }]], [2, [{ jawaban: { pk1: 'Komunikasi teknis', etika: 4 } }]]]);
  const m = masukanKurikulum(sv, jw);
  assert.deepEqual(m.map(x => [x.s.id, x.internal]), [[1, true], [2, false]]);   // tendik template has no curriculum items
  assert.equal(m[0].skala[0].rerata, 3);
  assert.deepEqual(m[0].isian[0].isi, ['Tambah BIM']);
  const csv = csvKurikulum(m);
  assert.match(csv, /Komunikasi teknis/);
  assert.match(csv, /eksternal/);
});

// Tracer pendukung (owner 2026-11-11; instal-lengkap.sql).
import { keTabelTracer, undanganPengguna, identitasBawaan, TINGKAT_KERJA } from '../../site/survei-kepuasan.js';

test('alumni template: conditional questions follow the work status; default identity required', () => {
  const t = templatSurvei('alumni');
  assert.equal(cekPertanyaan(t), '');
  // Owner 2026-11-14: tracer identity (name + NIM) required; income (DIKTI f505) required when working.
  assert.equal(identitasBawaan('alumni'), 'wajib');
  assert.equal(identitasBawaan('mahasiswa'), 'tidak');
  const gaji = t.find(q => q.id === 'pendapatan');
  assert.equal(gaji.wajib, true);
  assert.deepEqual(gaji.syarat.q, 'status');
  // DIKTI 2021 core (owner 2026-11-13): every respondent answers the seven competencies at graduation.
  const lulus = Object.fromEntries(t.filter(q => /^f17_.*_a$/.test(q.id)).map(q => [q.id, '4']));
  assert.equal(Object.keys(lulus).length, 7);
  const dasar = { tahun_lulus: 2025, sumber_dana: 'Biaya sendiri/keluarga', av1: 3, ...lulus };
  assert.equal(cekJawaban(t, { ...dasar, status: 'Belum memungkinkan bekerja' }), '');
  assert.match(cekJawaban(t, { ...dasar, status: 'Bekerja (full time/part time)' }), /wajib/);
  const kerja = { ...dasar, status: 'Bekerja (full time/part time)', kerja_6bulan: 'Ya', bulan: 2, pendapatan: 8000000, provinsi: 'DKI Jakarta', kabkota: 'Jakarta Selatan',
    jenis_instansi: 'BUMN/BUMD', tingkat: TINGKAT_KERJA.nasional, kesesuaian: 'Erat', tingkat_pendidikan: 'Tingkat yang sama', ak1: 4,
    ...Object.fromEntries(t.filter(q => /^f17_.*_b$/.test(q.id)).map(q => [q.id, '5'])) };
  assert.equal(cekJawaban(t, kerja), '');
  assert.match(cekJawaban(t, { ...kerja, izin_atasan: 'ya' }), /Email atasan/);
  assert.match(cekJawaban(t, { ...dasar, status: 'Melanjutkan pendidikan' }), /Sumber biaya studi lanjut/);
  assert.match(cekJawaban(t, { ...dasar, status: 'bekerja' }), /tidak dikenal/);          // old values are no longer offered
  const st = t.find(q => q.id === 'status');
  st.opsi.push('x');
  assert.notEqual(templatSurvei('alumni').find(q => q.id === 'status').opsi.length, st.opsi.length);   // deep copy
});

test('tracer reads the DIKTI status and f14 closeness as Tabel 6.f/6.g categories', () => {
  const R = j => ({ jawaban: { tahun_lulus: 2026, ...j } });
  const { baris } = keTabelTracer(templatSurvei('alumni'), [
    R({ status: 'Bekerja (full time/part time)', bulan: 1, kesesuaian: 'Sangat erat', tingkat: TINGKAT_KERJA.internasional }),
    R({ status: 'Wiraswasta', bulan: 4, kesesuaian: 'Cukup erat', tingkat: TINGKAT_KERJA.nasional }),
    R({ status: 'Bekerja (full time/part time)', bulan: 30, kesesuaian: 'Tidak sama sekali', tingkat: TINGKAT_KERJA.wilayah }),
    R({ status: 'Melanjutkan pendidikan' }),
    R({ status: 'Tidak kerja tetapi sedang mencari kerja' })]);
  assert.deepEqual(baris[0], { tahun_lulus: 2026, jumlah_terlacak: 5, rata_rata_waktu_tunggu_bulan: 11.67, wt_kurang_3: 1, wt_3_18: 1, wt_lebih_18: 1,
    kesesuaian_rendah: 1, kesesuaian_sedang: 1, kesesuaian_tinggi: 1, kerja_wilayah: 1, kerja_nasional: 1, kerja_internasional: 1 });
});

test('tracer rows per graduation year, wait-time bands and only working respondents', () => {
  const R = (j, nama) => ({ jawaban: j, nama });
  const rows = [
    R({ tahun_lulus: 2024, status: 'bekerja', bulan: 2, kesesuaian: 'tinggi', tingkat: TINGKAT_KERJA.nasional }),
    R({ tahun_lulus: 2024, status: 'wirausaha', bulan: 18, kesesuaian: 'sedang', tingkat: TINGKAT_KERJA.wilayah }),
    R({ tahun_lulus: 2024, status: 'studi lanjut' }),
    R({ tahun_lulus: 2025, status: 'bekerja', bulan: 20, kesesuaian: 'rendah', tingkat: TINGKAT_KERJA.internasional }),
    R({ status: 'bekerja', bulan: 1 })];
  const { baris, kurang } = keTabelTracer(templatSurvei('alumni'), rows);
  assert.deepEqual(kurang, []);
  assert.deepEqual(baris[0], { tahun_lulus: 2024, jumlah_terlacak: 3, rata_rata_waktu_tunggu_bulan: 10, wt_kurang_3: 1, wt_3_18: 1, wt_lebih_18: 0,
    kesesuaian_rendah: 0, kesesuaian_sedang: 1, kesesuaian_tinggi: 1, kerja_wilayah: 1, kerja_nasional: 1, kerja_internasional: 0 });
  assert.equal(baris[1].wt_lebih_18, 1);
  assert.equal(baris.length, 2);                                    // the row without a graduation year is skipped
  assert.ok(!('jumlah_lulusan' in baris[0]));                       // population stays with the prodi
  assert.deepEqual(keTabelTracer([{ id: 'status' }], rows).kurang, ['tahun_lulus', 'bulan', 'kesesuaian', 'tingkat']);
});

test('employer invitations need consent and a valid email, without duplicates', () => {
  const u = undanganPengguna([
    { jawaban: { izin_atasan: 'ya', email_atasan: 'Bos@PT.co.id', instansi: 'PT A' }, nama: 'Ani' },
    { jawaban: { izin_atasan: 'ya', email_atasan: 'bos@pt.co.id' } },
    { jawaban: { izin_atasan: 'tidak', email_atasan: 'lain@pt.co.id' } },
    { jawaban: { izin_atasan: 'ya', email_atasan: 'bukan-email' } }]);
  assert.deepEqual(u, [{ email: 'bos@pt.co.id', alumni: 'Ani', instansi: 'PT A' }]);
});

// Per-group questionnaires tagged with LAM butir, bilingual (owner 2026-11-13; instal-lengkap.sql).
import { teksQ, opsiQ, ketQ, ujungQ, labelBagian, butirSurvei, BAGIAN } from '../../site/survei-kepuasan.js';

test('every template question is bilingual, sectioned and tagged with LAM butir', () => {
  for (const [k] of KELOMPOK_SURVEI) {
    for (const q of templatSurvei(k)) {
      assert.ok(String(q.teks_en || '').trim(), `${k}.${q.id} teks_en`);
      assert.ok(BAGIAN[q.bagian], `${k}.${q.id} bagian`);
      assert.ok(q.butir?.length && q.butir.every(b => /^\d{1,2}$/.test(b)), `${k}.${q.id} butir`);
      if (q.opsi) assert.equal(q.opsi_en?.length, q.opsi.length, `${k}.${q.id} opsi_en`);
    }
  }
  const cakup = Object.fromEntries(KELOMPOK_SURVEI.map(([k]) => [k, butirSurvei(templatSurvei(k))]));
  for (const b of ['3', '5', '16', '21', '38', '39', '57']) assert.ok(cakup.mahasiswa.includes(b) || cakup.dosen.includes(b), b);
  assert.ok(['48', '49', '50', '51'].every(b => cakup.alumni.includes(b)));
  assert.ok(cakup.pengguna.includes('52') && cakup.mitra.includes('7') && cakup.mitra.includes('13'));
});

test('language helpers fall back to Indonesian; stored values stay Indonesian', () => {
  const q = { id: 'x', teks: 'Status', teks_en: 'Status (EN)', jenis: 'pilihan', opsi: ['ya', 'tidak'], opsi_en: ['yes', 'no'],
    ket: 'Petunjuk', ujung: ['rendah', 'tinggi'] };
  assert.equal(teksQ(q, true), 'Status (EN)');
  assert.equal(teksQ({ ...q, teks_en: ' ' }, true), 'Status');
  assert.deepEqual(opsiQ(q, true), [['ya', 'yes'], ['tidak', 'no']]);
  assert.deepEqual(opsiQ({ ...q, opsi_en: undefined }, true), [['ya', 'ya'], ['tidak', 'tidak']]);
  assert.equal(ketQ(q, true), 'Petunjuk');
  assert.deepEqual(ujungQ(q, true), ['rendah', 'tinggi']);
  assert.equal(labelBagian('vmts', true), 'Vision, mission, objectives and strategy');
  assert.equal(labelBagian('baru_sekali'), 'baru sekali');
  assert.match(cekJawaban([q], {}, true), /^Required question not answered: Status \(EN\)/);
  assert.match(cekJawaban([q], { x: 'yes' }, true), /Unknown option/);   // the English label is not a stored value
  assert.match(cekPertanyaan([{ ...q, opsi_en: ['yes'] }]), /bahasa Inggris harus 2/);
});

test('follow-up findings take the butir of the tagged questions', () => {
  const xs = [{ id: 'a', aspek: 'k3l', teks: 'K3', jenis: 'skala', butir: ['39'] }, { id: 'b', aspek: 'k3l', teks: 'K3 lagi', jenis: 'skala', butir: ['38', '39'] }];
  const rk = rekapSurvei(xs, { a: [3, 0, 0, 0], b: [3, 0, 0, 0] });
  assert.deepEqual(rk.aspek[0].butir, ['38', '39']);
  const [a] = aspekTindakLanjut(rk);
  assert.equal(temuanDariAspek({ id: 3, judul: 'S', tahun_ts: 2027, kelompok: 'mahasiswa' }, a, 3).butir, 38);
});

test('employer template asks organisation and graduate name (owner 2026-11-14), admin-only, not in Table 6.g.2', () => {
  const t = templatSurvei('pengguna');
  for (const id of ['nama_instansi', 'nama_lulusan']) {
    const q = t.find(x => x.id === id);
    assert.equal(q.jenis, 'singkat');                 // survei_rekap leaves short answers out of the public summary
    assert.equal(q.wajib, true);
    assert.ok(q.teks_en);
  }
  assert.match(cekJawaban(t, {}), /Nama institusi/);
});
