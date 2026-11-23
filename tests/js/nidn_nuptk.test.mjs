// NIP dan NUPTK dosen (instal-lengkap.sql, owner 2026-11-20) in LKPS 4.a, LED, and CV.
import test from 'node:test';
import assert from 'node:assert/strict';
import { nidnNuptk, nidnSah } from '../../site/profil-dosen.js';
import { isiCV, isiBiodataHibah } from '../../site/cv-dosen.js';
import { anggotaTim } from '../../site/led-isi.js';

test('nidnNuptk: both when both exist, staff codes replaced, blanks ignored', () => {
  assert.equal(nidnNuptk({ nidn: '0012345678', nuptk: '1234567890123456' }), '0012345678 / 1234567890123456');
  assert.equal(nidnNuptk({ nidn: '0012345678', nuptk: '' }), '0012345678');
  assert.equal(nidnNuptk({ nidn: '0012345678' }), '0012345678');
  assert.equal(nidnNuptk({ nidn: 'STAF-001', nuptk: '1234567890123456' }), '1234567890123456');
  assert.equal(nidnNuptk({ nidn: 'STAF-001' }), 'STAF-001');
  assert.equal(nidnNuptk({ nidn: '', nuptk: ' 99 ' }), '99');
  assert.equal(nidnNuptk({ nidn: '0012345678', nuptk: '0012345678' }), '0012345678');
  assert.equal(nidnNuptk(null), '');
  assert.ok(nidnSah('0012345678') && !nidnSah('STAF-001') && !nidnSah('12345'));
});

const D = { prodi: 'Teknik Contoh', institusi: 'Universitas Contoh', dosen: [], publikasi: [], kegiatan: [], luaran_dosen: [], rekognisi: [] };
const teks = x => x.replace(/<[^>]+>/g, '|');

test('CV identity lists NIP and NUPTK only when filled', () => {
  const ada = teks(isiCV({ nama: 'Ani', nidn: '0012345678', nip: '19800101 200501 1 001', nuptk: '1234567890123456' }, D, {}));
  assert.ok(ada.includes('|NIP|') && ada.includes('19800101 200501 1 001') && ada.includes('|NUPTK|') && ada.includes('1234567890123456'));
  const kosong = teks(isiCV({ nama: 'Ani', nidn: '0012345678' }, D, {}));
  assert.ok(!kosong.includes('|NIP|') && !kosong.includes('|NUPTK|'));
});

test('grant biodata fills NIP/NIK/identitas lainnya from NIP and NUPTK', () => {
  const x = teks(isiBiodataHibah({ nama: 'Ani', nidn: '0012345678', nip: '1980', nuptk: '1234567890123456' }, D, {}));
  assert.ok(x.includes('NIP 1980; NUPTK 1234567890123456'));
  const y = teks(isiBiodataHibah({ nama: 'Ani', nidn: '0012345678', nuptk: '1234567890123456' }, D, {}));
  assert.ok(y.includes('NUPTK 1234567890123456') && !y.includes('NIP 1980'));
});

test('LED team table uses NIDN / NUPTK for registered lecturers, row number for outsiders', () => {
  const dosen = [{ id: 'a', nama: 'Ani', nidn: '0012345678', nuptk: '1234567890123456', jabatan: 'lektor', aktif: true, peran: 'dosen' }];
  const t = anggotaTim([{ id: 1, urutan: 1, dosen_id: 'a' }, { id: 2, urutan: 2, nama: 'Tamu', nomor: 'NIP 9' }], dosen);
  assert.deepEqual(t.map(x => x.nomor), ['0012345678 / 1234567890123456', 'NIP 9']);
});
