// Tautan Monitoring untuk bukti AMI (owner 2026-11-11; instal-lengkap.sql).
import test from 'node:test';
import assert from 'node:assert/strict';
import { tambahBulan, tglID, urlAMI, statusAMI, labelPeriode, MASA_BAWAAN } from '../../site/ami-tautan.js';

test('default validity is two months', () => assert.equal(MASA_BAWAAN, 2));

test('adding months clamps to the end of a shorter month', () => {
  assert.equal(tglID(tambahBulan(new Date(2026, 10, 11), 2)), '11/01/2027');
  assert.equal(tglID(tambahBulan(new Date(2026, 11, 31), 2)), '28/02/2027');
  assert.equal(tglID(tambahBulan(new Date(2027, 7, 31), 1)), '30/09/2027');
});

test('status: revoked beats date, then expiry', () => {
  const kini = new Date('2026-11-11T00:00:00Z');
  assert.equal(statusAMI({ sampai: '2027-01-01T00:00:00Z' }, kini), 'berlaku');
  assert.equal(statusAMI({ sampai: '2026-11-10T00:00:00Z' }, kini), 'kedaluwarsa');
  assert.equal(statusAMI({ sampai: '2027-01-01T00:00:00Z', dicabut: true }, kini), 'dicabut');
});

test('locked period labels', () => {
  assert.equal(labelPeriode({ mode: 'ts', periode: 'ts3', akhir: 2026 }), '3 TS terakhir (2023/2024–2025/2026)');
  assert.equal(labelPeriode({ mode: 'kal', periode: 'ts3', akhir: 2026 }), '3 tahun terakhir (2024–2026)');
  assert.equal(labelPeriode({ mode: 'ts', periode: '2025' }), 'TS 2024/2025');
  assert.equal(labelPeriode({ mode: 'kal', periode: 'semua' }), 'Semua tahun');
});

test('link points at monitoring.html next to the current page', () => {
  assert.equal(urlAMI('abc', 'https://x.github.io/cv-site/data-prodi.html?tab=1'),
    'https://x.github.io/cv-site/monitoring.html?ami=abc');
});
