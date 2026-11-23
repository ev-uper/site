"""Course timetabling for run_jadwal.py (owner plan 2026-11-21, rules 2026-11-22).

aturan.py    config.yaml schedule section -> Aturan, with validation messages naming each key
masukan.py   input file downloaded from the site (Jadwal kuliah > Unduh masukan penjadwalan)
model.py     integer program solved with highspy: day and time per class (rooms are filled in on the site)
keluaran.py  import CSV for the site, Excel workbook, text report
"""
