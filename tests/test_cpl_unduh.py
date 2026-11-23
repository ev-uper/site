"""cpl/unduh.py: keyed download of grade files for run_cpl.py (owner 2026-11-11, option 2).

No network: a fake post() stands in for Apps Script (Code.gs kind 'cpl_unduh')."""
import base64
from pathlib import Path

import pytest

from cpl import unduh

ROOT = Path(__file__).resolve().parents[1]


def test_url_comes_from_site_config(tmp_path):
    (tmp_path / "site").mkdir()
    (tmp_path / "site" / "config.js").write_text("window.UPLOAD_URL    = 'https://script.google.com/macros/s/X/exec';\n", encoding="utf-8")
    assert unduh.baca_url(tmp_path) == "https://script.google.com/macros/s/X/exec"
    (tmp_path / "site" / "config.js").write_text("window.UPLOAD_URL = '';\n", encoding="utf-8")
    with pytest.raises(ValueError, match="kosong"):
        unduh.baca_url(tmp_path)


def test_key_from_env_or_rahasia_env(tmp_path, monkeypatch):
    monkeypatch.delenv(unduh.KUNCI_ENV, raising=False)
    with pytest.raises(ValueError, match="belum diisi"):
        unduh.baca_kunci(tmp_path)
    (tmp_path / "rahasia.env").write_text("LAIN=1\nCPL_KUNCI='" + "a" * 40 + "'\n", encoding="utf-8")
    assert unduh.baca_kunci(tmp_path) == "a" * 40
    monkeypatch.setenv(unduh.KUNCI_ENV, "b" * 40)
    assert unduh.baca_kunci(tmp_path) == "b" * 40
    monkeypatch.setenv(unduh.KUNCI_ENV, "pendek")
    (tmp_path / "rahasia.env").unlink()
    with pytest.raises(ValueError):
        unduh.baca_kunci(tmp_path)


def _palsu(berkas):
    panggil = []

    def post(url, isi):
        panggil.append(isi)
        if isi["aksi"] == "daftar":
            return {"ok": True, "berkas": [{"id": k, "semester": s, "kelas": c, "nama": n} for k, (s, c, n, _) in berkas.items()]}
        s, c, n, data = berkas[isi["id"]]
        return {"ok": True, "nama": n, "data": base64.b64encode(data).decode()}
    return post, panggil


def test_download_replaces_previous_files_and_keeps_names_safe(tmp_path):
    tujuan = tmp_path / unduh.SUBFOLDER
    (tujuan / "lama").mkdir(parents=True)
    (tujuan / "lama" / "basi.xlsx").write_bytes(b"x")
    post, panggil = _palsu({"F1": ("2026-2027 Ganjil", "41214-A", "../../jahat.xlsx", b"abc"),
                            "F2": ("2026-2027 Ganjil", "41299-B", "b.xlsx", b"de")})
    got = unduh.unduh_semua("u", "k" * 40, tujuan, post=post)
    assert not (tujuan / "lama").exists()                       # replaced files are not counted again
    assert sorted(p.read_bytes() for p in got) == [b"abc", b"de"]
    assert all(tujuan in p.parents for p in got)                 # no path escape
    assert all(c["kunci"] == "k" * 40 for c in panggil)


def test_refuses_to_clear_any_other_folder(tmp_path):
    post, _ = _palsu({})
    with pytest.raises(ValueError, match=unduh.SUBFOLDER):
        unduh.unduh_semua("u", "k" * 40, tmp_path / "berkas_nilai", post=post)


def test_run_cpl_site_source_uses_download(tmp_path, monkeypatch):
    import run_cpl
    from test_archive import make
    src, out = tmp_path / "in", tmp_path / "out"
    src.mkdir()

    def palsu(url, kunci, tujuan, post=None):
        make(Path(tujuan), "a.xlsx")
        return [Path(tujuan) / "a.xlsx"]
    monkeypatch.setattr(run_cpl, "baca_url", lambda root: "https://contoh/exec")
    monkeypatch.setattr(run_cpl, "baca_kunci", lambda root: "k" * 40)
    monkeypatch.setattr(run_cpl, "unduh_semua", palsu)
    assert run_cpl.main(["--input-dir", str(src), "--output-dir", str(out), "--source", "site"]) == 0
    log = (out / "run_cpl.log").read_text(encoding="utf-8")
    assert "unduhan   : 1 berkas" in log and "k" * 40 not in log    # key never logged
    assert (out / "ringkasan_cpl.json").is_file()


def test_run_cpl_site_source_reports_download_error(tmp_path, monkeypatch):
    import run_cpl
    src, out = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    monkeypatch.setattr(run_cpl, "baca_url", lambda root: (_ for _ in ()).throw(ValueError("UPLOAD_URL kosong")))
    assert run_cpl.main(["--input-dir", str(src), "--output-dir", str(out), "--source", "site"]) == 3
    assert "unduh dari situs gagal" in (out / "run_cpl.log").read_text(encoding="utf-8")


def test_config_source_values():
    from cpl.config import load_config, validate_config
    cfg = load_config(ROOT / "config.yaml")
    assert cfg["source"] == "site"
    bad = dict(cfg, source="ftp", paths={})
    assert any(e.startswith("source:") for e in validate_config(bad, ROOT))
