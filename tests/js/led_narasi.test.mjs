// site/led-narasi.js: stored LED narrative (owner 2026-11-05). Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { terapkanIsian, pisahKalimat, bagianNarasi, kalimatButir, kalimatCapaian, komponenButir, ambilNarasi, kunciTambahan,
         KRITERIA, judulCocok, bagianSaya, pilihanAwal, bentrok, ambilPenugasan, penulisNarasi, calonTim, kalimatUmum, geserTim, ISIAN_IDENTITAS, nilaiIdentitas } from '../../site/led-narasi.js';
import { faktaNarasi } from '../../site/led-isi.js';
import { petaDaftar } from '../../site/lkps.js';

const C = { ts: 2026, ta: '2025/2026', ta2: '2023/2024', dokumen: [], daftar: {}, manual: new Set(['1', '2']), judulButir: { 6: 'Kerja sama (Tabel 2.a LKPS)' } };
C.P = { ps: 'Program Studi Uji', pt: 'Univ Uji', ...faktaNarasi(C) };

test('every section has a unique id for filter and assignment', () => {
  const g = bagianNarasi(C);
  assert.deepEqual(g.map(x => x.id), ['identitas', 'awal', 'A', 'B', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'akhir']);
  assert.ok(g.every(x => x.pendek));
});

test('judulCocok: empty search matches, case does not matter', () => {
  assert.ok(judulCocok('Butir 23. Penelitian'));
  assert.ok(judulCocok('Butir 23. Penelitian', ' butir 23 '));
  assert.ok(!judulCocok('Butir 23. Penelitian', 'butir 24'));
});

test('bagianSaya: email ignores case; no assignment gives none', () => {
  assert.deepEqual(bagianSaya({ C1: 'A@x.id', C2: 'b@x.id' }, 'a@x.id'), ['C1']);
  assert.deepEqual(bagianSaya(null, 'a@x.id'), []);
});

test('pilihanAwal: remembered choice wins, empty means all, first visit uses own sections', () => {
  assert.deepEqual(pilihanAwal(['C1', 'C2'], ['C2', 'lama'], ['C1']), ['C2']);
  assert.deepEqual(pilihanAwal(['C1', 'C2'], [], ['C1']), []);
  assert.deepEqual(pilihanAwal(['C1', 'C2'], null, ['C1']), ['C1']);
});

test('bentrok: only a different change by someone else', () => {
  assert.ok(bentrok('lama', 'kata admin lain', 'kata saya'));
  assert.ok(bentrok('lama', undefined, 'kata saya'), 'emptied by someone else');
  assert.ok(bentrok(undefined, 'baru diisi', 'kata saya'));
  assert.ok(!bentrok('lama', 'lama', 'kata saya'), 'nobody else changed it');
  assert.ok(!bentrok('lama', 'sama', 'sama'), 'same text');
  assert.ok(!bentrok(undefined, undefined, 'kata saya'));
});

test('ambilPenugasan: map of rows; missing table gives null', async () => {
  const sb = hasil => ({ from: () => ({ select: async () => hasil }) });
  assert.deepEqual(await ambilPenugasan(sb({ data: [{ kelompok: 'C1', email: 'a@x.id' }] })), { C1: 'a@x.id' });
  assert.equal(await ambilPenugasan(sb({ error: { message: 'x' } })), null);
});

test('terapkanIsian: saved value by label and occurrence; missing stays [isi]', () => {
  const t = 'A [isi: x], B [isi: x], C [isi: y].';
  assert.equal(terapkanIsian(t, 'b1', 'n0', { 'b1|n0|x|2': 'dua' }), 'A [isi: x], B ⟪dua⟫, C [isi: y].');
  assert.equal(terapkanIsian(t, 'b1', 'n0'), t);
  assert.equal(terapkanIsian('Isi [isi: x].', 'b1', 'n0', { 'b1|n0|x|1': 'Selesai.' }), 'Isi ⟪Selesai.⟫', 'no double full stop');
});

test('key does not depend on the facts around it', () => {
  const k = t => pisahKalimat(t, 'b53', 'k0.0').filter(p => p.kunci).map(p => p.kunci);
  assert.deepEqual(k('SK [isi: nomor SK]; auditor [isi: dasar].'), ['b53|k0.0|nomor SK|1', 'b53|k0.0|dasar|1']);
  assert.deepEqual(k('SK ⟦u|SK 12⟧; auditor [isi: dasar].'), ['b53|k0.0|dasar|1'], 'doc arrives: other blank keeps its key');
});

test('pisahKalimat: text, link, blank', () => {
  assert.deepEqual(pisahKalimat('Lihat ⟦http://a|Dok⟧ dan [isi: y]', 'umum', 'p'),
    [{ t: 'Lihat ' }, { url: 'http://a', t: 'Dok' }, { t: ' dan ' }, { kunci: 'umum|p|y|1', label: 'y' }]);
});

test('page and LED share keys for every item', () => {
  const G = bagianNarasi(C);
  const bag = G.flatMap(g => g.bagian);
  const butir = bag.filter(b => /^b\d+$/.test(b.lingkup)).map(b => +b.lingkup.slice(1));
  assert.deepEqual(butir.filter((b, i) => butir.indexOf(b) !== i), [58], 'only butir 58 is split: B and Bab III');
  assert.ok(butir.includes(1) && butir.includes(57) && butir.includes(60));
  assert.equal(G.length, 12, 'identity, opening, A, B, seven criteria, closing');
  // Same key the draft asks for, with data or not.
  const idLED = kalimatButir('6', 0, C, true)[0];
  const idPage = kalimatButir('6', 0, C, false)[0];
  const k = x => pisahKalimat(x.teks, 'b6', x.id).find(p => p.kunci).kunci;
  assert.equal(k(idLED), k(idPage));
  const kc = ada => pisahKalimat(kalimatCapaian(C, ada).teks, 'b6', 'capaian').filter(p => p.kunci).map(p => p.kunci);
  assert.ok(kc(false).includes(kc(true)[0]));
});

test('two-part items list both parts', () => {
  assert.deepEqual(komponenButir('4'), [0, 1]);
  assert.deepEqual(komponenButir('1'), [0]);
  assert.deepEqual(komponenButir('6'), [0]);
  assert.equal(KRITERIA.C1.kode, 'C1');
  assert.equal(kunciTambahan('b1'), 'b1|tambahan');
});

test('ambilNarasi: rows to a map; missing table gives empty', async () => {
  const q = hasil => { const f = { select: () => f, order: () => f, range: async () => hasil }; return { from: () => f }; };
  assert.deepEqual(await ambilNarasi(q({ data: [{ kunci: 'a', nilai: '1' }], error: null })), { a: '1' });
  assert.deepEqual(await ambilNarasi(q({ data: null, error: { message: 'x' } })), {});
});

test('PS: accredited programme always appears; rank not guessed', () => {
  const L = petaDaftar({ ts: 2026, prodi: 'Teknik Contoh', D: { akreditasi: {} }, daftar: { karya: [], dosen: [],
    mhs: [{ tahun_akademik: '2025/2026', jumlah_mahasiswa_aktif: 205 }],
    dokumen: [{ jenis: 'sk_akreditasi_prodi', tahun: 2022, judul: 'SK LAM', nomor: '123/SK', tanggal: '2022-05-10', url: 'u' }] } });
  assert.deepEqual([L.PS.B17, L.PS.C17, L.PS.D17, L.PS.E17, L.PS.G17], ['Sarjana', 'Teknik Contoh', undefined, '123/SK, 10/05/2022', 205]);
  const M = petaDaftar({ ts: 2026, prodi: 'Teknik Contoh', D: { akreditasi: {} }, daftar: { karya: [], dosen: [],
    prodiUpps: [{ jenis_program: 'Sarjana', nama_prodi: 'Teknik Contoh', diakreditasi: true }, { jenis_program: 'Sarjana', nama_prodi: 'Lain' }] } });
  assert.equal(M.PS.C19, undefined, 'tab filled: no extra row');
});

const ORANG = [
  { nama: 'A', peran: 'admin', aktif: true },
  { nama: 'B', peran: 'dosen', aktif: true, tim_penyusun: true },
  { nama: 'C', peran: 'dosen', aktif: true, tim_penyusun: false },
  { nama: 'D', peran: 'dosen', aktif: false, tim_penyusun: true },
  { nama: 'E', peran: 'asesor', aktif: true, tim_penyusun: true },
  { nama: 'F', peran: 'pimpinan', aktif: true, tim_penyusun: true },
];
const nama = xs => xs.map(x => x.nama).join('');

test('penulis narasi: admin dan tim aktif, asesor tidak pernah', () => {
  assert.equal(nama(penulisNarasi(ORANG)), 'ABF');
});

test('penulis narasi tanpa kolom tim (patch 36 belum jalan): hanya admin', () => {
  assert.equal(nama(penulisNarasi(ORANG.map(({ tim_penyusun, ...x }) => x))), 'A');
});

test('calon tim: semua yang aktif kecuali asesor, admin bisa dicentang', () => {
  assert.equal(nama(calonTim(ORANG)), 'ABCF');
});

test('nama tim masuk kalimat tersendiri; kunci isian tim yang tersimpan tetap', () => {
  const k = kalimatUmum('tim', { P: { ps: 'Program Studi X', timPenyusun: 'A dan B' } });
  assert.equal(k.find(x => x.id === 'timAnggota').teks, 'Anggota tim penyusun: A dan B.');
  assert.deepEqual(k.filter(x => x.id !== 'timAnggota').map(x => x.id), ['tim0', 'tim1', 'tim2']);
  assert.ok(k.find(x => x.id === 'tim0').teks.includes('[isi: nomor dan tanggal SK tim]'));
});

test('geserTim: tukar dengan tetangga; di ujung tidak berubah', () => {
  assert.deepEqual(geserTim([1, 2, 3], 3, -1), [1, 3, 2]);
  assert.deepEqual(geserTim([1, 2, 3], 1, 1), [2, 1, 3]);
  assert.deepEqual(geserTim([1, 2, 3], 1, -1), [1, 2, 3]);
  assert.deepEqual(geserTim([1, 2, 3], 3, 1), [1, 2, 3]);
});

test('butir 58: Komponen I di bagian B, SWOT di Bab III, kuncinya tidak berubah', () => {
  const G = bagianNarasi(C), kunci = g => G.find(x => x.id === g).bagian.filter(b => b.lingkup === 'b58')
    .flatMap(b => b.kalimat.flatMap(x => pisahKalimat(x.teks, b.lingkup, x.id).filter(p => p.kunci).map(p => p.kunci)));
  assert.ok(kunci('B').length && kunci('B').every(k => /^b58\|(k0|capaian|[^|]*)/.test(k) && !k.includes('|k1.')));
  assert.ok(kunci('akhir').length && kunci('akhir').every(k => k.includes('|k1.')));
  const k0 = kalimatButir('58', 0, C, true)[0];
  assert.ok(kunci('B').includes(pisahKalimat(k0.teks, 'b58', k0.id).find(p => p.kunci).kunci));
});

test('identitas: tiap isian punya kotak, dan LED membaca kunci yang sama', () => {
  const k = bagianNarasi(C).find(g => g.id === 'identitas').bagian.flatMap(b => b.kalimat.flatMap(x =>
    pisahKalimat(x.teks, b.lingkup, x.id).filter(p => p.kunci)));
  for (const l of ISIAN_IDENTITAS) {
    const p = k.find(x => x.label === l);
    assert.ok(p, l);
    assert.equal(nilaiIdentitas({ [p.kunci]: 'nilai' }, l), 'nilai');
  }
});
