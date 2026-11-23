"""SDGs per karya ke data.json (instal-lengkap.sql, pemilik 2026-11-11)."""
import bangun


def test_sdgs_dari_bersih_urut_unik():
    assert bangun.sdgs_dari({"sdgs": [11, 6, 6, 18, 0]}) == [6, 11]
    assert bangun.sdgs_dari({"sdgs": "{3,13}"}) == [3, 13]
    assert bangun.sdgs_dari({"sdgs": None}) == []
    assert bangun.sdgs_dari({}) == []
