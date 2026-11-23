"""bangun.dosen_dari_supabase and the retired Excel commands (owner 2026-11-04).

Fictitious data, no network. Rules under test: the `dosen` table is the only
source of the roster, sorted by name; an empty table or a missing patch-18
column stops the build; the old Excel commands only say where data is
entered now, before any secret is read.
"""
import sys

import pytest

import bangun


class FakeSb:
    def __init__(self, rows):
        self.rows = rows

    def ambil_opsional(self, tabel, pilih="*"):
        return self.rows


def baris(email, nama, **lain):
    r = {"nidn": email[:3], "nama": nama, "email": email, "peran": "dosen", "pendidikan": None,
         "jabatan": None, "sinta_id": None, "scopus_id": None, "orcid": None,
         "aktif": True, "dtps": True}
    r.update(lain)
    return r


def test_daftar_dari_tabel_urut_nama():
    rows = [baris("z@contoh.ac.id", "Zahra Uji", pendidikan="S3", jabatan="lektor"),
            baris("b@contoh.ac.id", "Budi Baru", aktif=False, dtps=False),
            baris("a@contoh.ac.id", "Adi Uji", peran="admin", pendidikan="S2")]
    d = bangun.dosen_dari_supabase(FakeSb(rows))
    assert list(d["nama"]) == ["Adi Uji", "Budi Baru", "Zahra Uji"]
    assert list(d.columns) == list(bangun.KOLOM_DOSEN)
    budi = d.iloc[1].to_dict()
    assert (budi["aktif"], budi["dtps"], budi["pendidikan"]) == ("tidak", "tidak", "")
    assert not bangun.masuk_dtps(budi) and bangun.masuk_dtps(d.iloc[2].to_dict())


@pytest.mark.parametrize("rows", [None, []], ids=["patch-18-belum", "tabel-kosong"])
def test_tanpa_daftar_dosen_build_berhenti(rows):
    with pytest.raises(SystemExit):
        bangun.dosen_dari_supabase(FakeSb(rows))


@pytest.mark.parametrize("perintah", ["--template", "--sinkron-dosen", "--sinkron-pengaturan",
                                      "--tambah-lembar", "--impor-lkps"])
def test_perintah_excel_dipensiunkan(perintah, monkeypatch, capsys):
    # Must stop before reading rahasia.env or touching Supabase.
    monkeypatch.setattr(bangun, "baca_env", lambda: pytest.fail("baca_env dipanggil"))
    monkeypatch.setattr(sys, "argv", ["bangun.py", perintah])
    with pytest.raises(SystemExit):
        bangun.main()
    assert "dipensiunkan" in capsys.readouterr().err
