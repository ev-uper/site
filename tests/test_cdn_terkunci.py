"""Pustaka dari CDN dikunci ke versi pasti (pemilik 2026-11-16, saran keamanan).

Alamat seperti @supabase/supabase-js@2 mengikuti rilis terbaru tanpa diuji; versi pasti
(x.y.z) di jsDelivr tidak berubah isinya. Tools/coba_lokal.py harus tetap mengenali
alamat Supabase yang dikunci agar diganti dengan Supabase tiruan."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CDN = re.compile(r"https://(?:cdn\.jsdelivr\.net/npm|unpkg\.com|esm\.sh)/((?:@[\w.-]+/)?[\w.-]+)@([^/'\"`\s]+)")


def test_every_cdn_library_has_exact_version():
    longgar = []
    for p in sorted((ROOT / "site").glob("*.*")):
        if p.suffix not in {".html", ".js", ".mjs"}:
            continue
        for m in CDN.finditer(p.read_text(encoding="utf-8")):
            if not re.fullmatch(r"\d+\.\d+\.\d+", m.group(2)):
                longgar.append(f"{p.name}: {m.group(1)}@{m.group(2)}")
    assert not longgar, "Kunci ke versi pasti (x.y.z): " + ", ".join(longgar)


def test_one_supabase_version_everywhere():
    versi = set()
    for p in (ROOT / "site").glob("*.html"):
        versi |= set(re.findall(r"@supabase/supabase-js@([\d.]+)/\+esm", p.read_text(encoding="utf-8")))
    assert len(versi) == 1, f"Versi supabase-js berbeda antar halaman: {sorted(versi)}"


def test_coba_lokal_still_replaces_pinned_supabase():
    import importlib.util
    # Repo sumber: tools/coba_lokal.py; repo prodi (templat): coba_lokal.py di akar repo.
    berkas = next(p for p in (ROOT / "tools" / "coba_lokal.py", ROOT / "coba_lokal.py") if p.is_file())
    spec = importlib.util.spec_from_file_location("coba_lokal", berkas)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.CDN.search("import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.119.0/+esm';")
    assert mod.CDN.search("https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm")
