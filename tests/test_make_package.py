"""The template build must keep working when code moves between files.

Skipped inside the template itself, which does not carry make_package.py.
"""
import importlib.util
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

AKAR = Path(__file__).resolve().parents[1]
SKRIP = AKAR / "tools" / "make_package.py"

pytestmark = pytest.mark.skipif(not SKRIP.exists(), reason="hanya di repo sumber")


@pytest.fixture(scope="module")
def templat(tmp_path_factory):
    pytest.importorskip("PIL")
    if not (AKAR / "tools" / "node_modules").is_dir():
        pytest.skip("butuh: npm install --prefix tools")
    spec = importlib.util.spec_from_file_location("make_package", SKRIP)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.KELUAR = tmp_path_factory.mktemp("paket")
    m.main()
    return m.KELUAR / "templat"


def alur(templat, nama):
    return (templat / ".github" / "workflows" / f"{nama}.yml").read_text(encoding="utf-8")


def test_cpl_settings_of_this_prodi_stay_out(templat):
    """config.yaml in the package: no Sipil NIM prefix or MK name aliases, still valid (2026-11-13)."""
    import yaml
    t = (templat / "config.yaml").read_text(encoding="utf-8")
    fg = yaml.safe_load(t)["final_grades"]
    assert fg["student_id_prefixes"] == [] and fg["course_aliases"] == {}
    assert "Gamtek" not in t and '"1041"]' not in t.replace('mis. ["1041"]', '')
    from cpl.config import validate_config
    cfg = yaml.safe_load(t)
    cfg["paths"] = {"final_grades_dir": str(templat)}
    assert not [e for e in validate_config(cfg, AKAR) if e.startswith("final_grades")]


def test_one_clean_install_file(templat):
    sql = sorted(f.name for f in (templat / "supabase").glob("*.sql"))
    assert sql == ["contoh-kata-visi.sql", "instal-lengkap.sql"]
    gabung = (templat / "supabase" / "instal-lengkap.sql").read_text(encoding="utf-8")
    assert not re.search(r"\bdrop\s+table\b", gabung, re.I)
    assert "transaction_timeout" not in gabung and not re.search(r"^\\\\", gabung, re.M)
    for tabel in ("dosen", "karya", "led_tim", "led_narasi", "lkps_target_kinerja"):
        assert f"CREATE TABLE public.{tabel} " in gabung


def test_service_key_is_made_in_each_database_not_shipped(templat):
    """layanan_kunci opens the anon mhs_* functions: the public repo must not carry a value (2026-11-23)."""
    gabung = (templat / "supabase" / "instal-lengkap.sql").read_text(encoding="utf-8")
    assert "INSERT INTO public.layanan_kunci (id) VALUES (1);" in gabung
    assert not re.search(r"layanan_kunci \(id, kunci\) VALUES", gabung)
    assert "kunci text DEFAULT encode(extensions.gen_random_bytes(24), 'hex'::text) NOT NULL" in gabung


def test_function_restrictions_survive_supabase_defaults(templat):
    """Supabase grants new functions to anon: each restriction must be written out."""
    gabung = (templat / "supabase" / "instal-lengkap.sql").read_text(encoding="utf-8")
    assert "revoke all on function public._terapkan_karya(uuid,jsonb) from public, anon, authenticated;" in gabung
    assert "revoke all on function public.ubah_karya(uuid,jsonb) from public, anon;" in gabung


def test_no_reference_to_missing_patch_files(templat):
    pola = re.compile(r"\b\d\d[a-z]?-(?:patch|skema|isi|lengkapi)[a-z0-9-]*\.sql")
    for f in ("site/data-prodi.html", "site/karya.html", "bangun.py", "README.md", "docs/panduan-pemasangan.md"):
        assert not pola.search((templat / f).read_text(encoding="utf-8")), f


def test_workflows_wait_for_variables_and_stay_valid(templat):
    for nama in ("bangun-situs", "pemeliharaan"):
        for job in yaml.safe_load(alur(templat, nama))["jobs"].values():
            assert job["if"].startswith("vars.NAMA_PRODI != ''")
            assert job["if"].count("(") == job["if"].count(")")


def test_site_is_published_from_the_same_repository(templat):
    teks = alur(templat, "bangun-situs")
    assert "actions/deploy-pages" in teks and "path: situs" in teks
    assert "repository:" not in teks and "ssh-key" not in teks and "git push" not in teks


def test_data_never_enters_the_public_repository(templat):
    teks = alur(templat, "pemeliharaan")
    assert "send cadangan" in teks and "send arsip" in teks
    assert "git add cadangan" not in teks and "git add arsip" not in teks
    assert "upload-artifact" not in teks
    aturan = (templat / ".gitignore").read_text(encoding="utf-8").splitlines()
    for wajib in ("/cadangan/", "/arsip/", "/pasang-tercatat.json", "/isian.ini"):
        assert wajib in aturan
    assert not (templat / "cadangan").exists() and not (templat / "arsip").exists()


def test_scheduled_workflows_leave_a_commit(templat):
    """GitHub stops schedules in a public repository after 60 days without activity."""
    langkah = yaml.safe_load(alur(templat, "pemeliharaan"))["jobs"]["cadangkan"]["steps"]
    # By name: the health report (125) runs after it since 2026-11-23.
    akhir = next(x for x in langkah if x.get("name") == "Tulis tanda aktif")
    assert akhir["if"] == "always()" and "aktivitas.txt" in akhir["run"] and "git push" in akhir["run"]


def test_install_file_is_not_ignored_by_git(templat):
    aturan = (templat / ".gitignore").read_text(encoding="utf-8")
    assert not re.search(r"^/?(supabase/)?instal-lengkap\.sql$", aturan, re.M)


def test_workbook_lecturers_receive_is_neutral(templat):
    with zipfile.ZipFile(templat / "templates" / "Template_Input_Data_CPL.xlsx") as z:
        teks = " ".join(z.read(n).decode("utf-8", "replace") for n in z.namelist() if n.endswith(".xml"))
    assert not re.search(r"teknik sipil", teks, re.I) and "bidang prodi" in teks
    # The download copy on the site (nilai-cpl.html, 2026-11-11) is neutralised the same way and stays identical.
    assert (templat / "site" / "Template_Input_Data_CPL.xlsx").read_bytes() ==         (templat / "templates" / "Template_Input_Data_CPL.xlsx").read_bytes()


def test_no_private_folder_named(templat):
    for f in ("templates/README.md", "run_site_check.py"):
        teks = (templat / f).read_text(encoding="utf-8")
        assert "OneDrive" not in teks and "99_Inbox" not in teks and "heslab-dev" not in teks, f


def test_no_placeholder_admin(templat):
    assert "Nama Anda" not in (templat / "supabase" / "instal-lengkap.sql").read_text(encoding="utf-8")


def test_no_two_repo_leftovers(templat):
    assert not (templat / "bangun-dan-push.bat").exists()
    for f in ("README.md", "docs/panduan-prodi-baru.md", "docs/bangun-otomatis.md",
              "apps-script/README.md", "site/panduan.html"):
        teks = (templat / f).read_text(encoding="utf-8")
        assert "bangun-dan-push" not in teks and "cv-data" not in teks, f


def test_installer_fills_the_site_and_writes_no_personal_file(templat, tmp_path):
    isian = tmp_path / "isian.ini"
    isian.write_text("""[prodi]
nama_prodi = Teknik Contoh
nama_institusi = Universitas Contoh
github_org = Prodi-Contoh
supabase_url = https://abcdefghijklmnopqrst.supabase.co
supabase_key = sb_publishable_contoh
upload_url =
admin_email = rahasia.admin@contoh.ac.id
admin_nidn = 0099887766
admin_nama = Admin Contoh
logo =
warna_utama = #0C2A4D
warna_aksen = #C8102E
""", encoding="utf-8")
    r = subprocess.run([sys.executable, "install.py", "--ini", str(isian)], cwd=templat,
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    assert "rahasia.admin@contoh.ac.id" in r.stdout
    config = (templat / "site" / "config.js").read_text(encoding="utf-8")
    assert "sb_publishable_contoh" in config and "GANTI_DENGAN" not in config
    assert "https://prodi-contoh.github.io/cv-site" in (templat / "config.yaml").read_text(encoding="utf-8")
    # Ignored by git, and this test itself, which holds the sample address.
    lewati = {"pasang-tercatat.json", Path(__file__).name}
    for f in templat.rglob("*"):
        if f.is_file() and f.name not in lewati and f.suffix not in (".png", ".docx", ".xlsx", ".pyc"):
            assert "rahasia.admin@contoh.ac.id" not in f.read_text(encoding="utf-8", errors="ignore"), f


def test_install_guide_uper_here_neutral_in_template(templat):
    """cv-data's guide uses the real Teknik Sipil UPer values; the template gets
    neutral examples and its own PDF (owner 2026-11-09). The values are read
    from make_package.py: this file is copied to the template and is scanned."""
    spec = importlib.util.spec_from_file_location("make_package_nilai", SKRIP)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    sumber = (AKAR / "docs" / "panduan-pemasangan.md").read_text(encoding="utf-8")
    teks = (templat / "docs" / "panduan-pemasangan.md").read_text(encoding="utf-8")
    for uper, netral in m.PANDUAN_UPER:
        assert uper.strip() in sumber and uper.strip() not in teks, uper
        assert netral.strip() in teks, netral
    assert not m.LUNAK.search(teks) and not any(k.lower() in teks.lower() for k in m.KERAS)
    pdf = (templat / "docs" / "panduan-pemasangan.pdf").read_bytes()
    assert pdf.startswith(b"%PDF") and pdf != (AKAR / "docs" / "panduan-pemasangan.pdf").read_bytes()


# Data orang Sipil (pemilik 2026-11-23): nama dan nomor identitas dosen tidak boleh ada di paket.
def test_lecturer_names_and_ids_are_caught_as_whole_words(monkeypatch):
    spec = importlib.util.spec_from_file_location("make_package_orang", SKRIP)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    monkeypatch.setattr(m, "kunci_orang", lambda: ["Dosen Fiktif Satu", "0312345678"])
    isi = {"a.js": "const x = 'Dosen Fiktif Satu';".encode(), "b.py": b"nidn = '0312345678'",
           "c.json": b'{"angka": "103123456789"}', "d.png": b"Dosen Fiktif Satu"}
    assert sorted(m.orang_tertemu(isi)) == [("a.js", "Dosen Fiktif Satu"), ("b.py", "0312345678")]
