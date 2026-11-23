#!/usr/bin/env python3
"""Walk the published site with Selenium, check each page, record a video.

    python run_site_check.py                 (VS Code run button: no arguments needed)

Choices are in config.yaml under site_check; machine paths in config.local.yaml
under paths (contoh: config.local.yaml.contoh). Output: site_check.mp4 and
site_check.csv in paths.site_check_dir, outside the repo, because a logged-in
video can show personal data.

Pages behind login: the first run opens the browser and waits; paste the login
link from your email into that window. The session stays in
paths.site_check_profile. The script never types an account or password.

Optional overrides: --url, --output, --no-login. --demo writes site_demo.mp4
with the page notes instead of check results, for showing the system to others:
run it against a copy with sample data, never against a logged-in session.
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from cpl.config import load_config

ROOT = Path(__file__).resolve().parent
BROKEN_TEXT = ("undefined", "NaN", "[object Object]", "Invalid Date")
NEED_LOGIN = ("Perlu masuk", "Kirim tautan masuk")
PAGE_FAILED = "Halaman gagal dimuat"
FAILED, WARNING, OK, LOCKED = "GAGAL", "PERINGATAN", "OK", "PERLU MASUK"
COLOUR = {FAILED: (200, 16, 46), WARNING: (184, 134, 11), OK: (0, 149, 78), LOCKED: (93, 107, 120)}

# Facts read from the open page in one call.
PROBE = """
const main = document.querySelector('main') || document.body;
const clean = main.cloneNode(true);
clean.querySelectorAll('script,style,textarea,select,input').forEach(x => x.remove());
return {
  title: document.title,
  text: clean.innerText || clean.textContent || '',
  banner: !!document.getElementById('galat-muat'),
  needLogin: [...document.querySelectorAll('button')].some(b => b.textContent.includes('Kirim tautan masuk')),
  brokenImages: [...document.images].filter(i => i.complete && !i.naturalWidth).map(i => i.getAttribute('src')),
  overflow: document.documentElement.scrollWidth - window.innerWidth,
  height: document.documentElement.scrollHeight,
};
"""


def validate(cfg: dict, output: str | None, need_profile: bool) -> list[str]:
    """Error messages naming their key; empty = valid."""
    err = []
    sc = cfg.get("site_check")
    if not isinstance(sc, dict):
        return ["site_check: bagian ini tidak ada di config.yaml"]
    if not str(sc.get("url", "")).startswith("http"):
        err.append("site_check.url harus diawali http")
    if sc.get("browser") not in ("edge", "chrome"):
        err.append("site_check.browser harus edge atau chrome")
    for key, lo, hi in (("width", 800, 3840), ("height", 600, 2160), ("max_screens", 1, 30)):
        if not isinstance(sc.get(key), int) or not lo <= sc[key] <= hi:
            err.append(f"site_check.{key} harus bilangan bulat {lo}-{hi}")
    for key in ("seconds_per_screen", "demo_seconds_per_screen"):
        if not isinstance(sc.get(key), (int, float)) or not 0.5 <= sc[key] <= 10:
            err.append(f"site_check.{key} harus angka 0,5-10")
    pages = sc.get("pages")
    if not isinstance(pages, list) or not pages:
        err.append("site_check.pages harus daftar yang tidak kosong")
    else:
        for i, p in enumerate(pages):
            if not isinstance(p, dict) or not p.get("path") or not p.get("title"):
                err.append(f"site_check.pages[{i}] perlu path dan title")
    paths = cfg.get("paths") or {}
    if not output and not paths.get("site_check_dir"):
        err.append("paths.site_check_dir belum diisi di config.local.yaml")
    if need_profile and not paths.get("site_check_profile"):
        err.append("paths.site_check_profile belum diisi di config.local.yaml")
    return err


def judge(page: dict, info: dict, logs: list[str]) -> tuple[str, list[str]]:
    """Status and findings of one page. Pure, so it can be tested without a browser."""
    text = info.get("text", "")
    if info.get("needLogin"):                # the button, not the words: the guide quotes them
        return LOCKED, ["halaman perlu login"]
    failed, warned = [], []
    if info.get("banner") or PAGE_FAILED in text:
        failed.append("kotak galat muat tampil")
    if logs:
        failed.append(f"{len(logs)} galat konsol: {logs[0][:140]}")
    if len(text.strip()) < 40:
        failed.append("isi halaman nyaris kosong")
    for word in page.get("must_contain") or []:
        if word not in text:
            failed.append(f"teks wajib tidak ada: {word}")
    for word in BROKEN_TEXT:
        n = len(re.findall(rf"(?<![A-Za-z]){re.escape(word)}(?![A-Za-z])", text))
        if n:
            warned.append(f"teks rusak '{word}' {n} kali")
    if info.get("brokenImages"):
        warned.append(f"{len(info['brokenImages'])} gambar rusak: {info['brokenImages'][0]}")
    if info.get("overflow", 0) > 2:
        warned.append(f"lebar melebihi layar {info['overflow']} px")
    return (FAILED if failed else WARNING if warned else OK), failed + warned


def open_browser(sc: dict, profile: Path | None):
    from selenium import webdriver
    edge = sc["browser"] == "edge"
    options = webdriver.EdgeOptions() if edge else webdriver.ChromeOptions()
    options.add_argument(f"--window-size={sc['width']},{sc['height']}")
    if sc.get("headless") and profile is None:
        options.add_argument("--headless=new")
    if profile is not None:
        options.add_argument(f"--user-data-dir={profile}")
    options.set_capability("ms:loggingPrefs" if edge else "goog:loggingPrefs", {"browser": "SEVERE"})
    return webdriver.Edge(options=options) if edge else webdriver.Chrome(options=options)


def console_errors(driver) -> list[str]:
    try:
        # favicon.ico: browsers ask the domain root, which is not part of this site.
        return [e["message"] for e in driver.get_log("browser")
                if e.get("level") == "SEVERE" and "favicon.ico" not in e["message"]]
    except Exception:                        # the driver does not offer the log
        return []


def caption(path: Path, line: str, status: str | None) -> None:
    """Strip at the bottom of a screenshot: page and result."""
    img = Image.open(path).convert("RGB")
    h = 44
    d = ImageDraw.Draw(img)
    d.rectangle([0, img.height - h, img.width, img.height], fill=COLOUR[status] if status else (12, 42, 77))
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    d.text((14, img.height - h + 9), f"{status}  |  {line}" if status else line, fill="white", font=font)
    if img.width % 2 or img.height % 2:      # H.264 needs even sizes
        img = img.crop((0, 0, img.width - img.width % 2, img.height - img.height % 2))
    img.save(path)


def capture(driver, folder: Path, n: int, sc: dict, line: str, status: str | None, height: int) -> list[Path]:
    """Screens of one page, scrolling down."""
    shots = []
    view = driver.execute_script("return window.innerHeight")
    for i in range(min(sc["max_screens"], max(1, -(-height // max(view, 1))))):
        driver.execute_script("window.scrollTo(0, arguments[0])", i * view)
        time.sleep(0.3)
        p = folder / f"{n:03d}_{i:02d}.png"
        driver.save_screenshot(str(p))
        caption(p, line if status is None else f"{line}  (layar {i + 1})", status)
        shots.append(p)
    return shots


def make_video(shots: list[Path], seconds: float, target: Path, folder: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        sys.exit("ffmpeg tidak ditemukan. Pasang: conda install ffmpeg")
    lst = folder / "list.txt"
    body = "".join(f"file '{p.as_posix()}'\nduration {seconds}\n" for p in shots)
    lst.write_text(body + f"file '{shots[-1].as_posix()}'\n", encoding="utf-8")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-vf", "fps=10,pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(target)],
                   check=True)


def wait_for_login(driver, url: str) -> None:
    driver.get(url.rstrip("/") + "/ruang-kerja.html")
    time.sleep(3)
    text = driver.execute_script("return document.body.innerText")
    if any(t in text for t in NEED_LOGIN) and sys.stdin.isatty():
        print("Belum masuk. Di jendela browser ini: minta tautan masuk, lalu TEMPEL tautan dari email ke alamat browser ini.")
        input("Setelah masuk, tekan Enter di sini... ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--url", help="menimpa site_check.url sementara")
    ap.add_argument("--output", help="menimpa paths.site_check_dir sementara")
    ap.add_argument("--no-login", action="store_true", help="tanpa profil login; halaman admin tercatat PERLU MASUK")
    ap.add_argument("--demo", action="store_true", help="video pengenalan dengan keterangan halaman; pakai salinan berdata contoh")
    a = ap.parse_args()

    cfg = load_config(ROOT / "config.yaml")
    if a.demo:
        a.no_login = True
    errors = validate(cfg, a.output, not a.no_login)
    if errors:
        sys.exit("Config belum benar:\n  " + "\n  ".join(errors))
    sc, paths = cfg["site_check"], cfg.get("paths") or {}
    url = (a.url or sc["url"]).rstrip("/")
    out = Path(a.output or paths["site_check_dir"])
    out.mkdir(parents=True, exist_ok=True)
    profile = None if a.no_login else Path(paths["site_check_profile"])
    print(f"Situs: {url}\nBrowser: {sc['browser']} {sc['width']}x{sc['height']}\nKeluaran: {out}\n"
          f"Login: {'tidak' if profile is None else profile}\nHalaman: {len(sc['pages'])}")

    rows, shots = [], []
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        driver = open_browser(sc, profile)
        try:
            driver.set_window_size(sc["width"], sc["height"])
            if profile is not None:
                wait_for_login(driver, url)
            for n, page in enumerate(sc["pages"], 1):
                driver.get(f"{url}/{page['path']}")
                time.sleep(sc.get("wait_seconds", 3))
                info = driver.execute_script(PROBE)
                status, notes = judge(page, info, console_errors(driver))
                print(f"[{n:2d}/{len(sc['pages'])}] {status:11} {page['title']}" + (f": {'; '.join(notes)}" if notes else ""))
                rows.append([n, page["title"], page["path"], status, "; ".join(notes)])
                line = f"{page['title']}: {page.get('note', '')}" if a.demo else f"{n}. {page['title']}"
                shots += capture(driver, folder, n, sc, line, None if a.demo else status, info["height"])
        finally:
            driver.quit()
        seconds = sc["demo_seconds_per_screen"] if a.demo else sc["seconds_per_screen"]
        make_video(shots, seconds, out / ("site_demo.mp4" if a.demo else "site_check.mp4"), folder)
    with open(out / "site_check.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["No", "Halaman", "Alamat", "Status", "Temuan"])
        w.writerows(rows)
    hitung = {s: sum(r[3] == s for r in rows) for s in (OK, WARNING, FAILED, LOCKED)}
    print(f"Selesai: {hitung}. Video dan laporan: {out}")
    return 1 if hitung[FAILED] else 0


if __name__ == "__main__":
    sys.exit(main())
