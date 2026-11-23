// Jadwal berhalangan dosen (instal-lengkap.sql, pemilik 2026-11-20).
import test from 'node:test';
import assert from 'node:assert/strict';
import { hariISO, cekSlot, perSel, cariSlotKosong, labelSlot, namaJenis, cekRentang, labelRentang, rentangPadaTanggal, buatSlot,
  tambahHari, mingguDari, slotAntara, blokBaru, isiKalender, barisEkspor, ringkasBlok }
  from '../../site/jadwal-berhalangan.js';

const SLOT = [{ id: 1, label: 'Jam 1', mulai: '07:30:00', selesai: '09:10:00' }, { id: 2, label: 'Jam 2', mulai: '09:20:00', selesai: '11:00:00' }];

test('hariISO, labelSlot, namaJenis', () => {
  assert.equal(hariISO('2026-11-23'), 1);   // Senin
  assert.equal(hariISO('2026-11-22'), 7);   // Minggu
  assert.equal(hariISO('salah'), null);
  assert.equal(labelSlot(SLOT[0]), 'Jam 1 (07:30–09:10)');
  assert.equal(labelSlot(null), 'Sepanjang hari');
  assert.equal(namaJenis('prodi_lain'), 'Mengajar/tugas di prodi lain');
});

test('cekSlot: empty label, wrong order, overlap among active slots', () => {
  assert.deepEqual(cekSlot([{ label: 'Jam 1', mulai: '07.30', selesai: '09.10' }, { label: 'Jam 2', mulai: '09:20', selesai: '11:00' }]), []);
  assert.deepEqual(cekSlot([{ label: '', mulai: '10:00', selesai: '09:00' }]), ['Slot 1: label kosong.', 'Slot 1: jam selesai harus setelah jam mulai.']);
  assert.deepEqual(cekSlot([{ label: 'A', mulai: '07:30', selesai: '09:10' }, { label: 'B', mulai: '09:00', selesai: '10:00' }]), ['Slot 1 dan 2 tumpang-tindih.']);
  assert.deepEqual(cekSlot([{ label: 'A', mulai: '07:30', selesai: '09:10' }, { label: 'B', mulai: '09:00', selesai: '10:00', aktif: false }]), []);
});

test('cariSlotKosong: weekly for chosen lecturers, date adds date-specific (all-day) entries', () => {
  const mingguan = [{ dosen_id: 'a', hari: 1, slot_id: 1, jenis: 'prodi_lain' }, { dosen_id: 'c', hari: 1, slot_id: 2, jenis: 'luar' },
    { dosen_id: 'b', hari: 2, slot_id: 2, jenis: 'institusi', alasan: 'Rapat universitas' }];
  const r = cariSlotKosong({ slot: SLOT, hari: [1, 2], mingguan, dosen: ['a', 'b'] });
  assert.deepEqual(r.get('1|1').map(x => x.dosen_id), ['a']);
  assert.deepEqual(r.get('1|2'), []);                        // c tidak dipilih
  assert.equal(r.get('2|2')[0].alasan, 'Rapat universitas');
  assert.equal(r.size, 4);
  const t = cariSlotKosong({ slot: SLOT, hari: [1, 2], mingguan, dosen: ['a', 'b'], tanggal: '2026-11-23',
    tanggalan: [{ dosen_id: 'b', tanggal: '2026-11-23', slot_id: null, jenis: 'luar' }, { dosen_id: 'b', tanggal: '2026-11-24', slot_id: 1 }] });
  assert.deepEqual([...t.keys()], ['1|1', '1|2']);           // hanya Senin
  assert.deepEqual(t.get('1|1').map(x => `${x.dosen_id}:${x.sumber}`), ['a:mingguan', 'b:tanggal']);
  assert.deepEqual(t.get('1|2').map(x => x.dosen_id), ['b']);
  assert.equal(cariSlotKosong({ slot: SLOT, hari: [1, 2], tanggal: '2026-11-22' }).size, 0);   // Minggu bukan hari kuliah
  assert.deepEqual([...perSel(mingguan).keys()], ['1|1', '1|2', '2|2']);
});

// 135: rentang tanggal + hari + slot (pemilik 2026-11-21). 2026-12-01 = Selasa.
test('cekRentang: tanggal wajib, urutan, batas 366 hari, hari harus ada di rentang', () => {
  assert.deepEqual(cekRentang({ mulai: '2026-12-01', selesai: '2027-01-15', hari: [2, 4], slot: [1] }), []);
  assert.deepEqual(cekRentang({ mulai: '2026-12-01' }), []);                                   // satu tanggal
  assert.deepEqual(cekRentang({ mulai: '' }), ['Isi tanggal mulai.']);
  assert.match(cekRentang({ mulai: '2026-12-05', selesai: '2026-12-01' })[0], /setelah tanggal mulai/);
  assert.match(cekRentang({ mulai: '2026-01-01', selesai: '2027-02-01' })[0], /366 hari/);
  assert.match(cekRentang({ mulai: '2026-12-01', selesai: '2026-12-02', hari: [5] })[0], /tidak ada di dalam rentang/);   // Selasa-Rabu, pilih Jumat
  assert.deepEqual(cekRentang({ mulai: '2026-12-01', selesai: '2026-12-02', hari: [3] }), []);
});

test('labelRentang: rentang, satu tanggal, tanpa hari/slot', () => {
  const S = [{ id: 1, label: 'Jam 1' }, { id: 2, label: 'Jam 2' }];
  assert.equal(labelRentang({ mulai: '2026-12-01', selesai: '2027-01-15', hari: [2, 4], slot_ids: [1, 2] }, S), '1/12/2026–15/1/2027 · Selasa, Kamis · Jam 1, Jam 2');
  assert.equal(labelRentang({ mulai: '2026-12-01', selesai: '2026-12-01', slot_ids: null }, S), '1/12/2026 · Selasa · sepanjang hari');
  assert.equal(labelRentang({ mulai: '2026-12-01', selesai: '2026-12-10', hari: null, slot_ids: [9] }, S), '1/12/2026–10/12/2026 · setiap hari · slot 9');
});

test('rentangPadaTanggal: hari dan slot dari rentang ikut di Cari slot kosong', () => {
  const R = [{ id: 7, dosen_id: 'b', mulai: '2026-12-01', selesai: '2027-01-15', hari: [2, 4], slot_ids: [2], jenis: 'luar', alasan: 'Dinas' },
             { id: 8, dosen_id: 'a', mulai: '2026-12-03', selesai: '2026-12-03', hari: null, slot_ids: null, jenis: 'institusi' }];
  assert.deepEqual(rentangPadaTanggal(R, '2026-12-08').map(x => [x.dosen_id, x.slot_id]), [['b', 2]]);          // Selasa
  assert.deepEqual(rentangPadaTanggal(R, '2026-12-09'), []);                                                 // Rabu
  assert.deepEqual(rentangPadaTanggal(R, '2026-12-03').map(x => [x.dosen_id, x.slot_id]), [['b', 2], ['a', null]]);
  assert.deepEqual(rentangPadaTanggal(R, '2027-01-19'), []);                                                 // setelah selesai
  const t = cariSlotKosong({ slot: SLOT, hari: [1, 2], dosen: ['a', 'b'], tanggal: '2026-12-08', tanggalan: rentangPadaTanggal(R, '2026-12-08') });
  assert.deepEqual(t.get('2|1'), []);
  assert.deepEqual(t.get('2|2').map(x => `${x.dosen_id}:${x.alasan}`), ['b:Dinas']);
});

test('buatSlot: jam awal-akhir tiap n menit, tanpa tumpang-tindih (pemilik 2026-11-21: 07-17 per jam)', () => {
  const s = buatSlot('07:00', '17:00', 60);
  assert.equal(s.length, 10);
  assert.deepEqual(s[0], { label: 'Jam 07', mulai: '07:00', selesai: '08:00', aktif: true });
  assert.deepEqual(s[9], { label: 'Jam 16', mulai: '16:00', selesai: '17:00', aktif: true });
  assert.deepEqual(cekSlot(s), []);
  assert.equal(buatSlot('07:30', '09:10', 50).map(x => x.label).join(','), 'Jam 07.30,Jam 08.20');
  assert.match(buatSlot('', '17:00', 60).galat, /jam awal/);
  assert.match(buatSlot('07:00', '07:30', 60).galat, /setelah jam awal/);
  assert.match(buatSlot('07:00', '17:00', 5).galat, /15–240/);
});

// Kalender bertanggal (pemilik 2026-11-21): slot 30 menit 07-17, seret untuk blok, judul wajib, ulangi tiap minggu.
const S30 = buatSlot('07:00', '17:00', 30).map((s, i) => ({ ...s, id: i + 1 }));
test('mingguDari, tambahHari, slotAntara', () => {
  assert.equal(S30.length, 20);
  assert.deepEqual(mingguDari('2026-11-26'), ['2026-11-23', '2026-11-24', '2026-11-25', '2026-11-26', '2026-11-27', '2026-11-28', '2026-11-29']);
  assert.equal(tambahHari('2026-12-30', 3), '2027-01-02');
  assert.deepEqual(slotAntara(S30, 5, 2), [2, 3, 4, 5]);                 // seret ke atas juga
  assert.deepEqual(slotAntara(S30, 7, 7), [7]);
  assert.deepEqual(slotAntara(S30, 7, 99), []);
});

test('blokBaru: judul wajib; satu tanggal, atau jam yang sama pada hari terpilih dalam rentang tanggal', () => {
  assert.deepEqual(blokBaru({ tanggal: '2026-11-24', slot_ids: [3, 4], judul: ' Mengajar TL ', jenis: 'prodi_lain' }).baris,
    { mulai: '2026-11-24', selesai: '2026-11-24', hari: null, slot_ids: [3, 4], jenis: 'prodi_lain', alasan: 'Mengajar TL' });
  // Rutin tiap Selasa sampai akhir semester.
  assert.deepEqual(blokBaru({ tanggal: '2026-11-24', sampai: '2027-03-02', hari: [2], slot_ids: [3], judul: 'Ajar' }).baris.hari, [2]);
  // 1-15 Des, Senin-Jumat, jam yang sama (pemilik 2026-11-21).
  const r = blokBaru({ tanggal: '2026-12-01', sampai: '2026-12-15', hari: [5, 1, 2, 3, 4, 4], slot_ids: [13, 14], judul: 'Pelatihan', jenis: 'institusi' }).baris;
  assert.deepEqual([r.mulai, r.selesai, r.hari], ['2026-12-01', '2026-12-15', [1, 2, 3, 4, 5]]);
  assert.match(blokBaru({ tanggal: '2026-11-24', slot_ids: [3], judul: '  ' }).galat[0], /Isi judul/);
  assert.match(blokBaru({ tanggal: '2026-11-24', slot_ids: [], judul: 'x' }).galat[0], /menyeret/);
  assert.match(blokBaru({ tanggal: '2026-11-24', sampai: '2026-11-20', slot_ids: [3], judul: 'x', hari: [2] }).galat.join(' '), /setelah tanggal mulai/);
  assert.match(blokBaru({ tanggal: '2026-12-01', sampai: '2026-12-02', slot_ids: [3], judul: 'x', hari: [] }).galat[0], /minimal satu hari/);
  assert.match(blokBaru({ tanggal: '2026-12-01', sampai: '2026-12-02', slot_ids: [3], judul: 'x', hari: [5] }).galat[0], /tidak ada di dalam rentang/);
  assert.match(blokBaru({ tanggal: '2026-01-01', sampai: '2027-02-01', slot_ids: [3], judul: 'x', hari: [1] }).galat[0], /366 hari; pecah/);
  assert.match(blokBaru({ tanggal: '2026-11-24', slot_ids: [3], judul: 'x', jenis: 'asal' }).galat[0], /Jenis/);
});

test('isiKalender: blok, berulang, isian tanggal, mingguan semester sesuai semester tanggalnya', () => {
  const rentang = [{ id: 1, mulai: '2026-11-24', selesai: '2026-11-24', hari: null, slot_ids: [3, 4], jenis: 'luar', alasan: 'Rapat' },
                   { id: 2, mulai: '2026-11-24', selesai: '2027-03-02', hari: [2], slot_ids: [10], jenis: 'prodi_lain', alasan: 'Ajar TL' }];
  const tanggalan = [{ id: 5, tanggal: '2026-11-25', slot_id: null, jenis: 'institusi', alasan: 'Senat' }];
  const mingguan = [{ id: 9, tahun_akademik: '2026/2027', semester: 'Ganjil', hari: 4, slot_id: 1, jenis: 'lainnya', alasan: 'Kuliah S2' }];
  const sem = t => (t < '2027-03-01' ? { ta: '2026/2027', sm: 'Ganjil' } : { ta: '2026/2027', sm: 'Genap' });
  const k = isiKalender({ tanggal: ['2026-11-24', '2026-11-25', '2026-11-26', '2026-12-01'], slot: S30, rentang, tanggalan, mingguan, semesterDari: sem });
  assert.deepEqual(k.get('2026-11-24|3').map(x => x.judul), ['Rapat']);
  assert.equal(k.get('2026-11-24|10')[0].ulang, true);
  assert.equal(k.get('2026-12-01|10')[0].judul, 'Ajar TL');               // Selasa berikutnya
  assert.equal(k.get('2026-11-25|10')[0].sumber, 'tanggal');              // sepanjang hari: semua slot
  assert.equal(k.get('2026-11-25|1')[0].judul, 'Senat');
  assert.equal(k.get('2026-11-26|1')[0].sumber, 'mingguan');              // Kamis, semester Ganjil
  assert.equal(k.has('2026-11-26|2'), false);
  assert.equal(isiKalender({ tanggal: ['2027-03-04'], slot: S30, mingguan, semesterDari: sem }).size, 0);   // semester lain
});

// Tahap 1 penyusunan jadwal (pemilik 2026-11-21): sepanjang hari + ekspor Excel untuk pengatur jadwal.
test('blokBaru sepanjang hari: tanpa jam, slot_ids null', () => {
  assert.deepEqual(blokBaru({ tanggal: '2026-11-24', judul: 'Dinas', sepanjang: true }).baris.slot_ids, null);
  assert.deepEqual(blokBaru({ tanggal: '2026-11-24', sampai: '2026-11-27', hari: [2, 3, 4, 5], judul: 'Cuti', sepanjang: true, slot_ids: [3] }).baris,
    { mulai: '2026-11-24', selesai: '2026-11-27', hari: [2, 3, 4, 5], slot_ids: null, jenis: 'lainnya', alasan: 'Cuti' });
});

test('barisEkspor: mingguan per slot; tanggal digabung per isian bersambung, hanya hari kuliah, batas rentang', () => {
  const D = [{ id: 'b', nama: 'Budi' }, { id: 'a', nama: 'Ani' }];
  const mingguan = [{ dosen_id: 'b', hari: 1, slot_id: 2, jenis: 'prodi_lain', alasan: 'TL' }, { dosen_id: 'a', hari: 3, slot_id: 1, jenis: 'luar' }];
  const rentang = [{ id: 1, dosen_id: 'a', mulai: '2026-11-24', selesai: '2026-11-28', hari: [2, 6], slot_ids: [5, 6, 7], jenis: 'luar', alasan: 'Rapat' },
                   { id: 2, dosen_id: 'b', mulai: '2026-11-25', selesai: '2026-11-25', hari: null, slot_ids: null, jenis: 'institusi', alasan: 'Senat' }];
  const tanggalan = [{ id: 9, dosen_id: 'a', tanggal: '2026-11-24', slot_id: 20, jenis: 'lainnya', alasan: 'Ujian' }];
  const e = barisEkspor({ dosen: D, slot: S30, mingguan, tanggalan, rentang, dari: '2026-11-23', sampai: '2026-11-29', hariAktif: [1, 2, 3, 4, 5] });
  assert.equal(e.galat, '');
  assert.deepEqual(e.mingguan.slice(1).map(r => r.slice(0, 4)), [['Ani', 'Rabu', 'Jam 07', '07:00'], ['Budi', 'Senin', 'Jam 07.30', '07:30']]);
  assert.deepEqual(e.tanggal.slice(1).map(r => [r[0], r[1], r[3], r[4], r[6]]), [
    ['Ani', '2026-11-24', '09:00', '10:30', 'Rapat'], ['Ani', '2026-11-24', '16:30', '17:00', 'Ujian'],   // Sabtu 28 bukan hari kuliah
    ['Budi', '2026-11-25', '07:00', '17:00', 'Senat']]);
  assert.match(barisEkspor({ dari: '2026-01-01', sampai: '2026-12-31' }).galat, /200 hari/);
  assert.match(barisEkspor({ dari: '', sampai: '' }).galat, /Isi rentang/);
});

test('ringkasBlok: tiap Senin saja, satu tanggal, peringatan SETIAP HARI bila hari kosong', () => {
  assert.equal(ringkasBlok({ tanggal: '2026-11-30', sampai: '2027-01-18', hari: [1], slot_ids: [1, 2, 3] }, S30),
    'setiap Senin, 07:00–08:30, 30/11/2026 s.d. 18/1/2027 (8 kali)');
  assert.equal(ringkasBlok({ tanggal: '2026-11-30', slot_ids: [1, 2, 3] }, S30), 'Senin 30/11/2026, 07:00–08:30');
  assert.equal(ringkasBlok({ tanggal: '2026-12-01', sampai: '2026-12-15', hari: [2, 4], sepanjang: true }, S30),
    'setiap Selasa, Kamis, sepanjang hari, 1/12/2026 s.d. 15/12/2026 (5 kali)');
  assert.match(ringkasBlok({ tanggal: '2026-11-30', sampai: '2026-12-04', hari: [], slot_ids: [1] }, S30), /^SETIAP HARI/);
  assert.equal(ringkasBlok({ tanggal: '' }, S30), '');
});
