"""Scheduling rules from config.yaml `schedule` (owner decisions 2026-11-22; see the comments in config.yaml)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

HARI = {1: "Senin", 2: "Selasa", 3: "Rabu", 4: "Kamis", 5: "Jumat", 6: "Sabtu", 7: "Minggu"}
_JAM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def menit(jam: str) -> int:
    """'07:30' or '07:30:00' -> 450."""
    h, m = str(jam).split(":")[:2]
    return int(h) * 60 + int(m)


def jam(m: int) -> str:
    """450 -> '07:30'."""
    return f"{m // 60:02d}:{m % 60:02d}"


@dataclass(frozen=True)
class Jendela:
    """A time window on one weekday (1-7) or on every day (hari None), in minutes after midnight."""
    hari: int | None
    mulai: int
    selesai: int

    def kena(self, hari: int, mulai: int, selesai: int) -> bool:
        return (self.hari is None or self.hari == hari) and mulai < self.selesai and self.mulai < selesai

    def teks(self) -> str:
        return f"{'setiap hari' if self.hari is None else HARI[self.hari]} {jam(self.mulai)}-{jam(self.selesai)}"


@dataclass(frozen=True)
class Aturan:
    minutes_per_sks: int
    same_label_break_minutes: int
    electives_no_overlap: bool
    blocked: tuple[Jendela, ...]
    avoid: tuple[Jendela, ...]
    lecturer_daily_max_hours: float | None
    weights: dict = field(default_factory=dict)
    time_limit_seconds: int = 120


def _jendela(nama: str, xs, err: list[str]) -> tuple[Jendela, ...]:
    out = []
    if not isinstance(xs, list):
        err.append(f"schedule.{nama}: harus daftar {{day, start, end}}, didapat {xs!r}")
        return ()
    for i, x in enumerate(xs):
        kunci = f"schedule.{nama}[{i}]"
        if not isinstance(x, dict):
            err.append(f"{kunci}: harus {{day, start, end}}, didapat {x!r}")
            continue
        d, a, b = x.get("day"), str(x.get("start", "")), str(x.get("end", ""))
        if not (d == "all" or (isinstance(d, int) and not isinstance(d, bool) and 1 <= d <= 7)):
            err.append(f"{kunci}.day: 1 (Senin) ... 7 (Minggu) atau \"all\", didapat {d!r}")
            continue
        if not _JAM.match(a) or not _JAM.match(b) or menit(b) <= menit(a):
            err.append(f"{kunci}: start dan end \"HH:MM\" dengan end sesudah start, didapat {a!r}-{b!r}")
            continue
        out.append(Jendela(None if d == "all" else d, menit(a), menit(b)))
    return tuple(out)


def baca_aturan(cfg: dict) -> tuple[Aturan | None, list[str]]:
    """(Aturan, []) or (None, error messages each naming its key)."""
    s = cfg.get("schedule")
    if not isinstance(s, dict):
        return None, ["schedule: bagian belum ada di config.yaml"]
    err: list[str] = []

    def bulat(k, lo, hi):
        v = s.get(k)
        if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
            err.append(f"schedule.{k}: bilangan bulat {lo}-{hi}, didapat {v!r}")
        return v

    mps = bulat("minutes_per_sks", 10, 120)
    jeda = bulat("same_label_break_minutes", 0, 180)
    batas = bulat("time_limit_seconds", 10, 3600)
    pil = s.get("electives_no_overlap")
    if not isinstance(pil, bool):
        err.append(f"schedule.electives_no_overlap: true atau false, didapat {pil!r}")
    maks = s.get("lecturer_daily_max_hours")
    if maks is not None and (not isinstance(maks, (int, float)) or isinstance(maks, bool) or not 1 <= maks <= 12):
        err.append(f"schedule.lecturer_daily_max_hours: angka 1-12 atau null, didapat {maks!r}")
    w = s.get("weights")
    bobot = {}
    if not isinstance(w, dict):
        err.append(f"schedule.weights: harus pemetaan avoid, lecturer_overload, dated_unavailability, earlier_start; didapat {w!r}")
    else:
        for k in ("avoid", "lecturer_overload", "dated_unavailability", "earlier_start"):
            v = w.get(k)
            if not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0:
                err.append(f"schedule.weights.{k}: angka >= 0, didapat {v!r}")
            else:
                bobot[k] = float(v)
    blok = _jendela("blocked", s.get("blocked", []), err)
    hindar = _jendela("avoid", s.get("avoid", []), err)
    if err:
        return None, err
    return Aturan(mps, jeda, pil, blok, hindar, maks, bobot, batas), []


def ringkas(a: Aturan) -> list[str]:
    """The rules in force, one line each, for the screen and the log."""
    return [
        f"durasi      : {a.minutes_per_sks} menit per sks, dibulatkan ke atas ke slot",
        f"label sama  : tidak bentrok, jeda minimal {a.same_label_break_minutes} menit",
        f"MK pilihan  : {'tidak saling bentrok' if a.electives_no_overlap else 'hanya cek bentrok dosen'}",
        f"wajib kosong: {', '.join(j.teks() for j in a.blocked) or '-'}",
        f"dihindari   : {', '.join(j.teks() for j in a.avoid) or '-'}",
        f"dosen/hari  : {'tanpa batas' if a.lecturer_daily_max_hours is None else f'maks {a.lecturer_daily_max_hours:g} jam (anjuran)'}",
        f"bobot       : {', '.join(f'{k} {v:g}' for k, v in a.weights.items())}",
        f"batas waktu : {a.time_limit_seconds} detik",
    ]
