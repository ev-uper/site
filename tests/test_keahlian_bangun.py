"""Peta keahlian di data.json (bangun.py, pemilik 2026-11-11, patch 60)."""
import bangun


def test_keahlian_publik_only_filled_keys():
    assert bangun.keahlian_publik(None) == {}
    assert bangun.keahlian_publik({"kata_kunci": None, "bidang_keahlian": "  "}) == {}
    assert bangun.keahlian_publik({"kata_kunci": [" Banjir ", "", "GSMaP"], "bidang_keahlian": " Hidrologi "}) == {
        "kata_kunci": ["Banjir", "GSMaP"], "bidang_keahlian": "Hidrologi"}


def test_topik_publik_topic_and_subfield_at_most_three():
    topik = [{"t": "Flood Risk", "s": "Water Science", "f": "Environmental Science", "n": 0.9},
             {"k": "open access", "n": 0.8}, {"t": " "}, "rusak",
             {"t": "B"}, {"t": "C", "s": ""}, {"t": "D"}]
    assert bangun.topik_publik(topik) == [{"t": "Flood Risk", "s": "Water Science"}, {"t": "B"}, {"t": "C"}]
    assert bangun.topik_publik(None) == [] and bangun.topik_publik({"t": "x"}) == []


def test_arsipkan_skips_non_tables_and_stores_lists_as_json(tmp_path):
    """Regression 2026-11-12: lembar["keahlian"] (a dict) stopped the Actions build in the archive step."""
    import sqlite3
    import pandas as pd
    db = tmp_path / "prodi.sqlite"
    lembar = {"dosen": pd.DataFrame([{"nama": "Ani"}]), "keahlian": {"Ani": {"kata_kunci": ["Banjir"]}},
              "kosong": pd.DataFrame()}
    bangun.arsipkan(db, lembar, {"karya": [{"id": "k1", "sdgs": [6, 13], "topik": [{"t": "Flood"}]}],
                                 "karya_mitra": []})
    with sqlite3.connect(db) as kon:
        tabel = {r[0] for r in kon.execute("select name from sqlite_master where type = 'table'")}
        assert tabel == {"dosen", "karya"}
        assert kon.execute("select sdgs, topik from karya").fetchone() == ("[6, 13]", '[{"t": "Flood"}]')


def test_keahlian_publik_includes_chosen_topics():
    assert bangun.keahlian_publik({"topik_keahlian": ["AIR02", " ", "MAT04"]}) == {"topik_keahlian": ["AIR02", "MAT04"]}


def test_keahlian_baku_publik_active_sorted_and_split():
    bidang = [{"kode": "TRN", "nama": "Transportasi", "nama_en": "Transport", "urutan": 2, "aktif": True},
              {"kode": "AIR", "nama": "Air", "nama_en": "Water", "urutan": 1, "aktif": True, "cakupan": "Hidrologi"},
              {"kode": "OLD", "nama": "Lama", "nama_en": "Old", "urutan": 3, "aktif": False}]
    topik = [{"kode": "AIR02", "bidang": "AIR", "nama": "Banjir", "nama_en": "Floods", "urutan": 2,
              "sinonim": "genangan; flood ;", "padanan": "flood; banjir", "aktif": True},
             {"kode": "AIR01", "bidang": "AIR", "nama": "Hidrologi", "nama_en": "Hydrology", "urutan": 1, "aktif": True},
             {"kode": "AIR03", "bidang": "AIR", "nama": "Nonaktif", "nama_en": "x", "urutan": 3, "aktif": False},
             {"kode": "OLD01", "bidang": "OLD", "nama": "Bidang nonaktif", "nama_en": "x", "urutan": 1, "aktif": True}]
    out = bangun.keahlian_baku_publik(bidang, topik)
    assert [b["kode"] for b in out["bidang"]] == ["AIR", "TRN"]
    assert [t["kode"] for t in out["topik"]] == ["AIR01", "AIR02"]
    assert out["topik"][1]["sinonim"] == ["genangan", "flood"] and out["topik"][0]["padanan"] == []
    assert bangun.keahlian_baku_publik([], []) is None
