"""Every table created by supabase/*.sql is in config.yaml supabase.tables (backup list).

config.yaml says: tables not listed are NOT backed up, add each new table. Tables 50-57
were missed on 2026-11-11 and found by hand; this guard catches the next one.
"""
import re
from pathlib import Path

from cpl.config import load_config

ROOT = Path(__file__).resolve().parents[1]
# Deliberately not backed up (config.yaml comment: no longer used since 2026-10-10).
SENGAJA_TIDAK = {"ref_kategori_publikasi",
                 # instal-lengkap.sql: audit log, grows with every change; kept 3 years in
                 # Supabase and pruned there (usulan Claude 2026-11-12, see docs/bangun-otomatis.md).
                 "jejak",
                 # instal-lengkap.sql: kunci layanan Apps Script (rahasia, tidak ke repo cadangan).
                 # Setelah pemulihan ke proyek baru: kunci baru dibuat patch 90, salin lagi ke MHS_KUNCI.
                 "layanan_kunci",
                 # instal-lengkap.sql: log kunjungan halaman per pengguna, dipangkas 180 hari di Supabase;
                 # tidak perlu dipulihkan dan tidak perlu ikut repo cadangan (pemilik 2026-11-20).
                 "pemakaian_halaman"}


def test_every_created_table_is_backed_up():
    dibuat = set()
    for p in sorted((ROOT / "supabase").glob("[0-9]*-*.sql")):   # termasuk patch tiga digit (100-*.sql)
        isi = p.read_text(encoding="utf-8")
        dibuat |= set(re.findall(r"create\s+table\s+(?:if\s+not\s+exists\s+)?public\.([a-z0-9_]+)", isi, re.I))
    cadangan = set(load_config(ROOT / "config.yaml")["supabase"]["tables"])
    hilang = sorted(dibuat - cadangan - SENGAJA_TIDAK)
    assert not hilang, f"Tambahkan ke config.yaml supabase.tables: {hilang}"


def test_published_cpl_template_is_the_official_one():
    """site/Template_Input_Data_CPL.xlsx (download link in nilai-cpl.html, owner 2026-11-11)
    must stay byte-identical to templates/, the official version read by cpl/."""
    resmi = (ROOT / "templates" / "Template_Input_Data_CPL.xlsx").read_bytes()
    terbit = (ROOT / "site" / "Template_Input_Data_CPL.xlsx").read_bytes()
    assert terbit == resmi, "Salin ulang templates/Template_Input_Data_CPL.xlsx ke site/"
