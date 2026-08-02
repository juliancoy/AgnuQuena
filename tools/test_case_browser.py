#!/usr/bin/env python3
"""Run the case viewer's exact-triangle clearance regression in Chrome."""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import subprocess
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "website"
CASE_SCAD = ROOT / "QuenaCase.scad"
SLOT_ASSETS = ("QuenaTube1.stl", "QuenaTube2.stl", "QuenaMouthpiece.stl")
NUMBER = r"[-+]?\d+(?:\.\d+)?"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_viewer_assets() -> None:
    for name in (
        "QuenaCaseBottomViewer.stl",
        "QuenaCaseLidViewer.stl",
        "QuenaTube1.stl",
        "QuenaTube2.stl",
        "QuenaMouthpiece.stl",
    ):
        canonical_dir = ROOT if name.startswith("QuenaCase") else ROOT / "build" / "quena"
        paths = (
            canonical_dir / name,
            ROOT / "website" / "assets" / name,
            ROOT / "site-hosting" / "public" / "assets" / name,
        )
        hashes = {sha256(path) for path in paths}
        if len(hashes) != 1:
            raise AssertionError(f"{name}: canonical and site assets differ")
    if (WEB_ROOT / "sim.js").read_bytes() != (
        ROOT / "site-hosting" / "public" / "sim.js"
    ).read_bytes():
        raise AssertionError("website and production simulation sources differ")


def evaluated_case_slots() -> dict[str, tuple[float, ...]]:
    with tempfile.TemporaryDirectory(prefix="quena_case_browser_slots_") as temp_dir:
        temp_path = Path(temp_dir)
        probe_scad = temp_path / "slots.scad"
        probe_stl = temp_path / "slots.stl"
        probe_scad.write_text(
            f"include <{CASE_SCAD}>;\n"
            "for (i = [0:2]) echo(\"CASE_SLOT\", i, slot_x(i), slot_y(i), "
            "slot_z, body_x0(i), slot_rot_z(i));\n"
            "cube(1);\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            ["openscad", "-D", 'part="none"', "-o", str(probe_stl), str(probe_scad)],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    matches = re.findall(
        rf'ECHO:\s*"CASE_SLOT",\s*(\d+),\s*({NUMBER}),\s*({NUMBER}),\s*'
        rf'({NUMBER}),\s*({NUMBER}),\s*({NUMBER})',
        result.stdout,
    )
    if len(matches) != 3:
        raise AssertionError("OpenSCAD did not report all three case slots")
    return {
        SLOT_ASSETS[int(index)]: tuple(float(value) for value in values)
        for index, *values in matches
    }


def verify_browser_slot_alignment() -> None:
    source = (WEB_ROOT / "sim.js").read_text(encoding="utf-8")
    matches = re.findall(
        rf'asset:\s*"([^"]+)",\s*x:\s*({NUMBER}),\s*y:\s*({NUMBER}),\s*'
        rf'z:\s*({NUMBER}),\s*bodyX0:\s*({NUMBER}),\s*rotationZ:\s*({NUMBER})',
        source,
    )
    browser = {
        asset: tuple(float(value) for value in values)
        for asset, *values in matches
        if asset in SLOT_ASSETS
    }
    case = evaluated_case_slots()
    if browser.keys() != case.keys():
        raise AssertionError("browser simulation does not define all OpenSCAD case slots")
    for asset in SLOT_ASSETS:
        for actual, expected in zip(browser[asset], case[asset]):
            if abs(actual - expected) > 0.001:
                raise AssertionError(
                    f"{asset}: browser slot {browser[asset]} differs from case {case[asset]}"
                )


def chrome_binary() -> str:
    for candidate in ("google-chrome", "google-chrome-stable", "chromium"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise AssertionError("case browser test requires Chrome or Chromium")


def run_browser_self_test() -> dict[str, object]:
    handler = partial(QuietHandler, directory=str(WEB_ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="agnuquena_case_chrome_") as profile:
            result = subprocess.run(
                [
                    chrome_binary(),
                    "--headless=new",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--enable-unsafe-swiftshader",
                    f"--user-data-dir={profile}",
                    "--virtual-time-budget=20000",
                    "--dump-dom",
                    f"http://127.0.0.1:{server.server_port}/index.html?selftest=1",
                ],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=40,
            )
    finally:
        server.shutdown()
        server.server_close()

    match = re.search(r'data-case-sweep-result="([^"]+)"', result.stdout)
    if not match:
        raise AssertionError(
            "case browser self-test did not publish a result\n" + result.stderr[-2000:]
        )
    return json.loads(html.unescape(match.group(1)))


def main() -> None:
    verify_viewer_assets()
    verify_browser_slot_alignment()
    result = run_browser_self_test()
    if result.get("firstSweepCollision") is not None:
        raise AssertionError(
            f"case browser sweep collides at {result['firstSweepCollision']} degrees"
        )
    probe_contacts = int(result.get("detectorProbeContacts", 0))
    if probe_contacts <= 0:
        raise AssertionError("clearance detector missed the penetration probe")
    if result.get("quenaWithinCasePlan") is not True:
        raise AssertionError("one or more quena sections extend outside the case plan")
    if result.get("quenaHolesFaceOutward") is not True:
        raise AssertionError("one or more quena sections have holes facing into the case")
    if result.get("pass") is not True:
        raise AssertionError(f"case browser self-test failed: {result}")
    print(
        "QuenaCase browser sweep: ok, 0-180 deg exact-triangle clearance; "
        f"penetration probe contacts={probe_contacts}; quena sections within case plan "
        "with holes facing outward"
    )


if __name__ == "__main__":
    main()
