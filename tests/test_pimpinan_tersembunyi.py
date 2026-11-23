"""Nama pimpinan bukan DTPS (mis. Dekan) tidak masuk situs umum (pemilik 2026-11-21).

aktif/dtps berbentuk 'ya'/'tidak' seperti keluaran bangun.dosen_dari_supabase."""
import bangun


def test_only_non_dtps_pimpinan_is_hidden():
    assert bangun.pimpinan_tersembunyi({"nama": "Dekan", "peran": "pimpinan", "aktif": "ya", "dtps": "tidak"})
    assert not bangun.pimpinan_tersembunyi({"nama": "Dekan DTPS", "peran": "pimpinan", "aktif": "ya", "dtps": "ya"})
    assert not bangun.pimpinan_tersembunyi({"nama": "Dosen pindah", "peran": "dosen", "aktif": "tidak", "dtps": "tidak"})
    assert not bangun.pimpinan_tersembunyi({"nama": "Admin staf", "peran": "admin", "aktif": "ya", "dtps": "tidak"})


def test_hidden_names_include_titled_name():
    dosen = [{"nama": "Rina Dekan", "peran": "pimpinan", "aktif": "ya", "dtps": "tidak"},
             {"nama": "Budi Dosen", "peran": "dosen", "aktif": "ya", "dtps": "ya"}]
    assert bangun.nama_tersembunyi(dosen, {"Rina Dekan": "Prof. Dr. Rina Dekan, M.T."}) == {
        "Rina Dekan", "Prof. Dr. Rina Dekan, M.T."}


def test_equivalence_table_keeps_dean_date_not_name():
    terbit = {"kurikulum_lama": "K21", "kurikulum_baru": "K26", "revisi": 1, "mk_lama": [], "mk_baru": [], "padanan": [],
              "disahkan": {"nama": "Kaprodi", "pada": "2026-11-21"}, "ditetapkan": {"nama": "Rina Dekan", "pada": "2026-11-22"}}
    out = bangun.ekuivalensi_publik([{"kurikulum_lama": "K21", "kurikulum_baru": "K26", "revisi": 1, "terbit": terbit},
                                     {"kurikulum_lama": "K16", "kurikulum_baru": "K21", "revisi": 0, "terbit": None}])
    assert len(out) == 1
    assert out[0]["ditetapkan"] == {"pada": "2026-11-22"}
    assert "Rina Dekan" not in repr(out)
