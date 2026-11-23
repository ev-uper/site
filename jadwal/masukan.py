"""Input file of run_jadwal.py, written by the site page jadwal-kuliah.html (format "jadwal-masukan-1").

{
  "format": "jadwal-masukan-1", "dibuat": ISO time, "tahun_akademik": "2026/2027", "semester": "Genap",
  "masa_kuliah": [{"mulai": "2027-02-01", "selesai": "2027-05-28"}, ...],   lecture weeks (may be empty)
  "libur": ["2027-03-29", ...],                                              holidays inside the lecture weeks
  "hari": [1, 2, 3, 4, 5],                                                   teaching days, 1 = Monday
  "slot": [{"id": 21, "mulai": "07:00", "selesai": "07:30"}, ...],           active time slots (same length, ordered)
  "dosen": [{"id": uuid, "nama": "..."}],
  "kelas": [{"id": 12, "kurikulum": "K26", "kode_mk": "SI201", "nama_mk": "...", "sks": 3, "semester_paket": 4 | null,
             "pilihan": false, "kelas": "A", "dosen": [uuid, ...], "penyelenggara": "prodi" | "universitas" | "fakultas",
             "jadwal": {"hari": 1, "mulai": "07:00", "selesai": "09:30", "kunci": true} | null}],
  "berhalangan": [{"dosen": uuid, "hari": 1, "slot": 21}],                   weekly (always respected)
  "berhalangan_tanggal": [{"dosen": uuid, "tanggal": "2027-02-03", "slot": 21 | null}]   dated (null = whole day)
}
Only a class whose "jadwal" has kunci = true is kept; other existing times are ignored (the solver plans afresh).
Classes run by the university (MKU) or the faculty have times set before the prodi plans (owner 2026-11-22): with a time
on the site they are always kept; without one they are left out of the run (warning), never placed by the solver.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .aturan import menit

FORMAT = "jadwal-masukan-1"


@dataclass(frozen=True)
class Slot:
    id: int
    mulai: int
    selesai: int


@dataclass(frozen=True)
class Kelas:
    id: int
    kurikulum: str
    kode: str
    nama: str
    sks: float
    paket: int | None
    pilihan: bool
    label: str
    dosen: tuple[str, ...]
    tetap: tuple[int, int, int] | None      # (hari, mulai, selesai) when locked on the site
    penyelenggara: str = "prodi"            # prodi | universitas | fakultas (ref_mata_kuliah.unit_penyelenggara)

    def teks(self) -> str:
        return f"{self.kode} {self.label}"


@dataclass
class Masukan:
    tahun_akademik: str
    semester: str
    hari: list[int]
    slot: list[Slot]
    dosen: dict[str, str]
    kelas: list[Kelas]
    berhalangan: set[tuple[str, int, int]]         # (dosen, hari, slot id)
    bertanggal: dict[tuple[str, int, int | None], int]   # (dosen, hari, slot id | None) -> number of lecture dates hit
    pertemuan: dict[int, int]                      # weekday -> number of lecture dates (masa kuliah minus libur)

    def nama_dosen(self, d: str) -> str:
        return self.dosen.get(d, d)


def _tanggal_kuliah(masa: list[dict], libur: set[str]) -> list[date]:
    out = set()
    for r in masa:
        a, b = date.fromisoformat(r["mulai"]), date.fromisoformat(r["selesai"])
        while a <= b:
            if a.isoformat() not in libur:
                out.add(a)
            a += timedelta(days=1)
    return sorted(out)


def baca_masukan(path: Path) -> tuple[Masukan | None, list[str]]:
    """(Masukan, warnings) or (None, errors). Every message names the field or the class."""
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        return None, [f"{Path(path).name}: tidak bisa dibaca sebagai JSON ({e})"]
    if not isinstance(d, dict) or d.get("format") != FORMAT:
        return None, [f"{Path(path).name}: bukan berkas masukan penjadwalan (format {FORMAT}); unduh ulang dari situs"]
    err, peringatan = [], []
    hari = d.get("hari") or []
    if not hari or any(not isinstance(h, int) or not 1 <= h <= 7 for h in hari):
        err.append(f"hari: daftar 1-7 (hari kuliah di situs), didapat {hari!r}")
    slot = []
    for i, s in enumerate(d.get("slot") or []):
        try:
            slot.append(Slot(int(s["id"]), menit(s["mulai"]), menit(s["selesai"])))
        except (KeyError, TypeError, ValueError):
            err.append(f"slot[{i}]: butuh id, mulai, selesai; didapat {s!r}")
    slot.sort(key=lambda s: s.mulai)
    if not slot:
        err.append("slot: kosong; admin mengatur slot jam kuliah di halaman Jadwal berhalangan")
    elif len({s.selesai - s.mulai for s in slot}) > 1:
        err.append("slot: panjang slot berbeda-beda (" + ", ".join(sorted({f'{s.selesai - s.mulai} menit' for s in slot}))
                   + "); penjalan butuh slot sama panjang")
    dosen = {str(x["id"]): str(x.get("nama") or x["id"]) for x in d.get("dosen") or [] if x.get("id")}
    kelas = []
    for i, k in enumerate(d.get("kelas") or []):
        try:
            j = k.get("jadwal") or None
            unit = str(k.get("penyelenggara") or "prodi")
            luar = unit in ("universitas", "fakultas")
            tetap = (int(j["hari"]), menit(j["mulai"]), menit(j["selesai"])) if j and (j.get("kunci") or luar) else None
            if luar and not tetap:
                peringatan.append(f"kelas {k['kode_mk']} {k['kelas']}: MK {unit} belum berjadwal di situs; dilewati "
                                  "(isi jam yang ditetapkan {unit} di Jadwal kuliah, lalu unduh masukan lagi)")
                continue
            paket = k.get("semester_paket")
            kelas.append(Kelas(int(k["id"]), str(k["kurikulum"]), str(k["kode_mk"]), str(k.get("nama_mk") or ""),
                               float(k["sks"]), int(paket) if paket not in (None, "") else None, bool(k.get("pilihan")),
                               str(k["kelas"]), tuple(str(x) for x in k.get("dosen") or []), tetap, unit))
        except (KeyError, TypeError, ValueError):
            err.append(f"kelas[{i}]: butuh id, kurikulum, kode_mk, sks, kelas; didapat {k!r}")
            continue
        if kelas[-1].sks <= 0:
            err.append(f"kelas {kelas[-1].teks()}: sks harus lebih dari 0 (isi sks MK di Data prodi)")
        if not kelas[-1].dosen and kelas[-1].penyelenggara == "prodi":
            peringatan.append(f"kelas {kelas[-1].teks()}: belum ada dosen; hanya aturan kelas yang dipakai")
        if kelas[-1].paket is None and not kelas[-1].pilihan:
            peringatan.append(f"kelas {kelas[-1].teks()}: MK wajib tanpa semester paket; aturan label sama tidak dipakai")
    if not kelas:
        err.append("kelas: kosong; susun kelas dulu di halaman Penyusunan kelas")
    if err:
        return None, err
    ada = {s.id for s in slot}
    berhalangan = {(str(b["dosen"]), int(b["hari"]), int(b["slot"])) for b in d.get("berhalangan") or []
                   if int(b["slot"]) in ada}
    tanggal = _tanggal_kuliah(d.get("masa_kuliah") or [], set(d.get("libur") or []))
    if not tanggal:
        peringatan.append("masa_kuliah: kosong; berhalangan bertanggal tidak diperhitungkan (isi Kalender akademik, "
                          "kategori perkuliahan, atau tanggal masa kuliah saat mengunduh)")
    kuliah = {t.isoformat(): t.isoweekday() for t in tanggal}
    pertemuan = {h: sum(1 for t in tanggal if t.isoweekday() == h) for h in range(1, 8)}
    bertanggal: dict[tuple[str, int, int | None], int] = {}
    for b in d.get("berhalangan_tanggal") or []:
        h = kuliah.get(str(b.get("tanggal")))
        if h is None:
            continue     # outside the lecture weeks or on a holiday
        s = b.get("slot")
        kunci = (str(b["dosen"]), h, None if s in (None, "") else int(s))
        bertanggal[kunci] = bertanggal.get(kunci, 0) + 1
    m = Masukan(str(d.get("tahun_akademik")), str(d.get("semester")), sorted(set(hari)), slot, dosen, kelas,
                berhalangan, bertanggal, pertemuan)
    return m, peringatan
