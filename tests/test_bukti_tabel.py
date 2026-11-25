"""Every Data prodi tab that takes row evidence must be allowed by lkps_bukti_tabel_check (2026-11-24).

Patches 165 and 167 added tabs without extending the constraint, so uploads were rejected by the
database (fixed in 168). The newest patch that defines the constraint is the one in force.
"""
import re
from pathlib import Path

AKAR = Path(__file__).resolve().parents[1]


def _nomor(p: Path) -> tuple[int, str]:
    # Patch names start with a number and may carry a letter suffix (e.g. 12b-...).
    m = re.match(r"(\d+)([a-z]*)-", p.name)
    return (int(m.group(1)), m.group(2))


def daftar_izin() -> tuple[str, set[str]]:
    pola = re.compile(r"add constraint lkps_bukti_tabel_check\s+check \(tabel in \(([^)]*)\)\)", re.S)
    terakhir = None
    for p in sorted((AKAR / "supabase").glob("[0-9]*-*.sql"), key=_nomor):
        m = pola.search(p.read_text(encoding="utf-8"))
        if m:
            terakhir = (p.name, set(re.findall(r"'(\w+)'", m.group(1))))
    # Template repo (make_package.py): no numbered patches, one dumped instal-lengkap.sql where the constraint reads
    # CONSTRAINT lkps_bukti_tabel_check CHECK ((tabel = ANY (ARRAY['a'::text, ...]))).
    gabungan = AKAR / "supabase" / "instal-lengkap.sql"
    if terakhir is None and gabungan.exists():
        m = re.search(r"CONSTRAINT lkps_bukti_tabel_check CHECK \(\(tabel = ANY \(ARRAY\[([^\]]*)\]",
                      gabungan.read_text(encoding="utf-8"))
        if m:
            terakhir = (gabungan.name, set(re.findall(r"'(\w+)'::text", m.group(1))))
    assert terakhir, "lkps_bukti_tabel_check tidak ditemukan"
    return terakhir


def tab_berbukti() -> dict[str, str]:
    h = (AKAR / "site" / "data-prodi.html").read_text(encoding="utf-8")
    tanpa = set(re.findall(r"\{ id: '(\w+)',[^\n]*\n[^\n]*tanpaBukti: true", h))
    return {i: t for i, t in re.findall(r"^  \{ id: '(\w+)', tabel: '(\w+)'", h, re.M) if i not in tanpa}


def test_every_evidence_tab_allowed_by_constraint():
    nama, izin = daftar_izin()
    tab = tab_berbukti()
    assert len(tab) >= 20
    hilang = {i: t for i, t in tab.items() if t not in izin}
    assert not hilang, f"tabel tanpa izin bukti di {nama}: {hilang}"


def test_lamdepilar_tables_allowed():
    _, izin = daftar_izin()
    assert {"lkps_sarana_standar", "lkps_bimbingan_utama", "lkps_keuangan", "lkps_mahasiswa_angkatan"} <= izin
