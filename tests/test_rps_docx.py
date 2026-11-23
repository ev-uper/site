"""RPS K26 ke Word (pemilik 2026-11-18): berkas dari site/rps-docx.js dibuka python-docx seperti Word membukanya.

tools/uji_rps_docx.mjs membuat satu RPS contoh lengkap (logo, enam bagian A-F); di sini diperiksa halaman, header,
dan isi tiap tabel mengikuti Formulir RPS K26 (UP-SPMI/FR008/R05).
"""
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

docx = pytest.importorskip("docx")
ROOT = Path(__file__).resolve().parents[1]
ADA = shutil.which("node") and (ROOT / "tools" / "node_modules" / "jszip").is_dir()
pytestmark = pytest.mark.skipif(not ADA, reason="node atau tools/node_modules/jszip tidak ada")


@pytest.fixture(scope="module")
def berkas(tmp_path_factory):
    p = tmp_path_factory.mktemp("rps") / "rps.docx"
    r = subprocess.run(["node", str(ROOT / "tools" / "uji_rps_docx.mjs"), str(p)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-2000:]
    return p


def teks_sel(t):
    return [[c.text for c in row.cells] for row in t.rows]


def test_page_header_and_logo(berkas):
    d = docx.Document(str(berkas))
    s = d.sections[0]
    assert s.orientation == docx.enum.section.WD_ORIENT.LANDSCAPE
    assert (s.page_width, s.page_height) == (docx.shared.Twips(16838), docx.shared.Twips(11906))
    kepala = teks_sel(s.header.tables[0])[0]
    assert kepala[1:] == ["RENCANA PEMBELAJARAN SEMESTER", "UP-SPMI/FR008/R05"]
    z = zipfile.ZipFile(berkas)
    assert {"word/media/logo.png", "word/media/peta.png"} <= set(z.namelist())
    # Peta Analisis (tahap 3) tersisip di tabel B, diperkecil agar muat lebar halaman.
    doc = z.read("word/document.xml").decode("utf-8")
    assert 'r:embed="rIdPeta"' in doc and 'Target="media/peta.png"' in z.read("word/_rels/document.xml.rels").decode("utf-8")


def test_sections_and_tables(berkas):
    d = docx.Document(str(berkas))
    judul = [p.text for p in d.paragraphs if re.match(r"[A-F]\.\t", p.text)][:6]
    # 114: Kaprodi pemeriksa sekaligus penyusun -> catatan di bawah lembar pengesahan.
    assert any("juga penyusun RPS ini" in p.text for p in d.paragraphs)
    # Judul bagian bernomor A-F seperti formulir (gaya Heading1 formulir: penomoran huruf besar).
    assert judul == ["A.	Identitas Mata Kuliah dan Lembar Pengesahan", "B.	Capaian Pembelajaran", "C.	Tujuan dan Deskripsi Mata Kuliah",
                     "D.	Rencana Pembelajaran", "E.	EVALUASI PELAKSANAAN MATA KULIAH PADA PENYELENGGARAAN SEBELUMNYA", "F.	Daftar Revisi RPS"]
    A, B1, B2, C, D, E, F, L1, J18, L2, L3, L4 = d.tables
    # Butir 18 (Tabel 3.a.1 LKPS): JP = sks praktikum x 50, JB = sks x 50; T=2, P=1.
    assert teks_sel(J18) == [["Butir 18 LAM Teknik (Tabel 3.a.1 LKPS): sks praktikum/praktik lapangan/penugasan", "1,00 dari 3,00 sks"],
                             ["JP = sks praktikum/praktik × 50 menit;  JB = sks × 50 menit", "JP 50′ ; JB 150′ ; JP/JB = 33,33%"]]
    # Lampiran rekap (pemilik 2026-11-19): beban belajar per bentuk dari sks T=2, P=1 (1 sks = 45 jam).
    lb = teks_sel(L1)
    # Angka lampiran dua desimal, koma (pemilik 2026-11-19).
    assert lb[1] == ["Kuliah/Responsi/Tutorial", "2,00", "100′ PB + 120′ PT + 120′ KM", "26,47", "31,76", "31,76", "0,00", "90,00"]
    assert lb[2][:2] == ["Praktikum", "1,00"] and lb[2][-1] == "45,00" and lb[-1][-1] == "135,00"
    assert teks_sel(L4)[-2:] == [["Proporsi penilaian HOTS (Sub-CPMK berkode C4-C6)", "60,00"],
                                 ["Asesmen non-tes (tugas, proyek, laporan, presentasi, dan sejenisnya)", "30,00"]]
    a = teks_sel(A)
    assert a[1] == ["Mekanika Tanah", "13301", "MKPS", "T=2", "P=1", "PL=0", "S=0", "5", "18 November 2026"]
    assert a[5][1] == "Adi, S.T., M.T." and a[5][3] == "Dr. Budi, S.T., M.T." and a[6][1] == "NIP 199001012020"
    assert teks_sel(B1)[1] == ["CPL-C", "Mampu menganalisis rekayasa geoteknik"]
    b = teks_sel(B2)
    assert b[2][4:8] == ["Kuis", "Tugas", "UTS", "UAS"]
    assert b[3] == ["CPL-C", "CPMK-1", "Sub-CPMK-1-1", "Mahasiswa mampu menjelaskan klasifikasi tanah (C2)", "Kuis 1", "", "UTS", "", "40%"]
    assert b[5][0].startswith("TOTAL BOBOT PENILAIAN · HOTS = 60%") and b[5][4:] == ["20%", "30%", "20%", "30%", "100%"]
    c = teks_sel(C)
    assert c[1][2:] == ["Dosen Pengampu", "Adi, S.T., M.T."] and c[5][3] == "Ada - Case Method pekan 9-10"
    dd = teks_sel(D)
    assert dd[2] == [f"[{i}]" for i in range(1, 8)]
    assert dd[3][0] == "1-2" and dd[3][2] == "Kontrak kuliah\nKlasifikasi tanah\n[Pustaka: DAS Bab 2]" and dd[3][4] == "Sumatif: Kuis 1"
    assert any(r[1] == "Ujian Tengah Semester (UTS)" for r in dd) and dd[-1][1] == "Ujian Akhir Semester (UAS)"
    assert teks_sel(E)[1] == ["belum pernah diselenggarakan"] * 5
    assert teks_sel(F)[1][3] == "Belum ada revisi"
