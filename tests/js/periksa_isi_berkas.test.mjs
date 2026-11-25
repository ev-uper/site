// Isi berkas harus cocok dengan ekstensinya (pemilik 2026-11-20): apps-script/Code.gs periksaIsi_ dijalankan di Node dengan
// byte bertanda (-128..127) seperti hasil Utilities.base64Decode di Apps Script.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { deflateRawSync } from 'node:zlib';

const gs = readFileSync(new URL('../../apps-script/Code.gs', import.meta.url), 'utf8');
const sumber = gs.match(/function periksaIsi_\(ext, bytes\) \{[\s\S]*?\n\}/)?.[0] || assert.fail('periksaIsi_ tidak ditemukan');
const periksaIsi_ = new Function(sumber + '\nreturn periksaIsi_;')();
const bertanda = buf => Array.from(new Int8Array(buf.buffer, buf.byteOffset, buf.byteLength));
const cek = (ext, buf) => periksaIsi_(ext, bertanda(Buffer.from(buf)));

// ZIP minimal (satu entri per nama) supaya DOCX uji punya struktur ZIP sungguhan.
function zip(nama){
  const lokal = [], pusat = []; let ofs = 0;
  for (const n of nama) {
    const isi = deflateRawSync(Buffer.from('isi ' + n)), nb = Buffer.from(n);
    const h = Buffer.alloc(30); h.writeUInt32LE(0x04034b50, 0); h.writeUInt16LE(20, 4); h.writeUInt16LE(8, 8);
    h.writeUInt32LE(isi.length, 18); h.writeUInt32LE(n.length + 4, 22); h.writeUInt16LE(nb.length, 26);
    lokal.push(h, nb, isi);
    const c = Buffer.alloc(46); c.writeUInt32LE(0x02014b50, 0); c.writeUInt16LE(20, 6); c.writeUInt16LE(8, 10);
    c.writeUInt32LE(isi.length, 20); c.writeUInt32LE(n.length + 4, 24); c.writeUInt16LE(nb.length, 28); c.writeUInt32LE(ofs, 42);
    pusat.push(c, nb); ofs += 30 + nb.length + isi.length;
  }
  const cd = Buffer.concat(pusat), e = Buffer.alloc(22); e.writeUInt32LE(0x06054b50, 0);
  e.writeUInt16LE(nama.length, 8); e.writeUInt16LE(nama.length, 10); e.writeUInt32LE(cd.length, 12); e.writeUInt32LE(ofs, 16);
  return Buffer.concat([...lokal, cd, e]);
}
const exe = Buffer.concat([Buffer.from('MZ'), Buffer.alloc(200, 0x90)]);

test('berkas sungguhan lolos: templat Excel CPL, PDF panduan, logo PNG', () => {
  const xlsx = new URL('../../templates/Template_Input_Data_CPL.xlsx', import.meta.url);
  assert.equal(cek('xlsx', readFileSync(xlsx)), '');
  assert.equal(cek('pdf', Buffer.from('%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF')), '');
  assert.equal(cek('pdf', Buffer.concat([Buffer.alloc(300, 0x20), Buffer.from('%PDF-1.4')])), '');   // awalan sebelum %PDF (<= 1 KB)
  assert.equal(cek('pdf', readFileSync(new URL('../../docs/panduan-pemasangan.pdf', import.meta.url))), '');
  assert.equal(cek('png', readFileSync(new URL('../../site/logo.png', import.meta.url))), '');
});

test('gambar dan Office: cocok lolos, tidak cocok ditolak', () => {
  assert.equal(cek('png', Buffer.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0, 0, 0, 13])), '');
  assert.equal(cek('jpg', Buffer.from([0xFF, 0xD8, 0xFF, 0xE0, 0, 16])), '');
  assert.equal(cek('jpeg', Buffer.from([0xFF, 0xD8, 0xFF, 0xE1])), '');
  assert.equal(cek('docx', zip(['[Content_Types].xml', 'word/document.xml'])), '');
  assert.match(cek('png', Buffer.from([0xFF, 0xD8, 0xFF])), /tidak sesuai dengan jenisnya \(\.png\)/);   // JPG dinamai .png
});

test('program yang diganti namanya, makro, dan Office terkunci ditolak', () => {
  assert.match(cek('pdf', exe), /Isi berkas tidak sesuai dengan jenisnya \(\.pdf\)/);
  assert.match(cek('docx', exe), /bukan berkas DOCX sungguhan/);
  assert.match(cek('jpg', exe), /tidak sesuai/);
  assert.match(cek('pdf', Buffer.concat([Buffer.alloc(1100, 0x20), Buffer.from('%PDF')])), /tidak sesuai/);   // lewat 1 KB
  assert.match(cek('docx', zip(['[Content_Types].xml', 'word/document.xml', 'word/vbaProject.bin'])), /memuat makro/);
  assert.match(cek('xlsx', zip(['xl/workbook.xml', 'xl/vbaProject.bin'])), /memuat makro/);
  assert.match(cek('docx', Buffer.from([0xD0, 0xCF, 0x11, 0xE0, 0xA1, 0xB1, 0x1A, 0xE1])), /terkunci kata sandi atau berformat lama/);
  assert.match(cek('pdf', Buffer.alloc(0)), /tidak sesuai/);
});

test('jenis lain di ALLOWED_EXT tidak diperiksa; kedua jalur unggah memanggil periksaIsi_', () => {
  assert.equal(cek('csv', exe), '');
  assert.match(gs, /function makeBlob_[\s\S]*?periksaIsi_\(ext, bytes\)[\s\S]*?newBlob/);
  assert.match(gs, /function blobCpl_[\s\S]*?periksaIsi_\('xlsx', bytes\)/);
});

test('mahasiswa hanya PDF dan gambar (pemilik 2026-11-20): Apps Script dan halaman pengajuan', () => {
  assert.match(gs, /var MHS_EXT = \['pdf', 'jpg', 'jpeg', 'png'\];/);
  assert.match(gs, /function mhsUnggah_[\s\S]*?MHS_EXT\.indexOf\(ext\) < 0[\s\S]*?mhsSimpan_/);
  const h = readFileSync(new URL('../../site/pengajuan.html', import.meta.url), 'utf8');
  assert.ok(!/accept="[^"]*docx/.test(h), 'halaman pengajuan tidak menawarkan DOCX');
  assert.equal((h.match(/accept="\.pdf,\.jpg,\.jpeg,\.png"/g) || []).length, 3);   // 179: + lampiran catatan bimbingan
});
