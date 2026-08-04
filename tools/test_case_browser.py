#!/usr/bin/env python3
"""Run the case viewer's exact-triangle clearance regression in Chrome."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPENSCAD = Path(os.environ.get("AGNUQUENA_OPENSCAD", ROOT / "tools" / "openscad"))
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
        "QuenaCaseBottom.stl",
        "QuenaCaseEngraving.stl",
        "QuenaCaseLogo.stl",
        "QuenaCaseLid.stl",
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


def evaluated_case_geometry() -> tuple[
    dict[str, tuple[float, ...]], tuple[float, ...]
]:
    with tempfile.TemporaryDirectory(prefix="quena_case_browser_slots_") as temp_dir:
        temp_path = Path(temp_dir)
        probe_scad = temp_path / "slots.scad"
        probe_stl = temp_path / "slots.stl"
        probe_scad.write_text(
            f"include <{CASE_SCAD}>;\n"
            "for (i = [0:2]) echo(\"CASE_SLOT\", i, slot_x(i), slot_y(i), "
            "slot_z, body_x0(i), slot_rot_z(i));\n"
            "echo(\"CASE_LATCH\", latch_point_xs[0], latch_point_xs[1], "
            "latch_tongue_y - latch_tongue_t / 2 + latch_nub_r "
            "- latch_nub_protrusion, latch_nub_z - lid_closed_z, latch_nub_r);\n"
            "cube(1);\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [str(OPENSCAD), "-D", 'part="none"', "-o", str(probe_stl), str(probe_scad)],
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
    latch_match = re.search(
        rf'ECHO:\s*"CASE_LATCH",\s*({NUMBER}),\s*({NUMBER}),\s*'
        rf'({NUMBER}),\s*({NUMBER}),\s*({NUMBER})',
        result.stdout,
    )
    if not latch_match:
        raise AssertionError("OpenSCAD did not report the friction-fit latch geometry")
    slots = {
        SLOT_ASSETS[int(index)]: tuple(float(value) for value in values)
        for index, *values in matches
    }
    return slots, tuple(float(value) for value in latch_match.groups())


def verify_browser_slot_alignment() -> None:
    source = (WEB_ROOT / "sim.js").read_text(encoding="utf-8")
    if "camera.up.set(0, 0, 1);" not in source:
        raise AssertionError("case browser must present positive Z at the top")
    if "const INITIAL_ANGLE_DEG = 180;" not in source:
        raise AssertionError("case browser must open on the exterior artwork view")
    if "const contacts = updateContactHighlight();" not in source:
        raise AssertionError("case browser contact readout must include latch highlights")
    if '"./assets/QuenaCaseEngraving.stl"' not in source:
        raise AssertionError("case browser does not load the canonical engraving mesh")
    for token in (
        "meshAppearances",
        "setMeshAppearance",
        "MeshPhongMaterial",
        "MeshToonMaterial",
        "MeshPhysicalMaterial",
        "ShaderMaterial",
        '"brushed-metal"',
        '"hologram"',
        "RoomEnvironment",
        "ACESFilmicToneMapping",
        "ShadowMaterial",
        "Studio shadow catcher",
    ):
        if token not in source:
            raise AssertionError(
                f"case browser lacks per-mesh appearance support: {token}"
            )
    if "Studio reflection floor" in source:
        raise AssertionError("case browser must not render a visible studio floor")
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
    case, case_latch = evaluated_case_geometry()
    if browser.keys() != case.keys():
        raise AssertionError("browser simulation does not define all OpenSCAD case slots")
    for asset in SLOT_ASSETS:
        for actual, expected in zip(browser[asset], case[asset]):
            if abs(actual - expected) > 0.001:
                raise AssertionError(
                    f"{asset}: browser slot {browser[asset]} differs from case {case[asset]}"
                )
    latch_match = re.search(
        rf'latch:\s*{{\s*xs:\s*\[\s*({NUMBER})\s*,\s*({NUMBER})\s*\],\s*'
        rf'y:\s*({NUMBER}),\s*localZ:\s*({NUMBER}),\s*radius:\s*({NUMBER})',
        source,
    )
    if not latch_match:
        raise AssertionError("browser simulation does not define latch contact geometry")
    browser_latch = tuple(float(value) for value in latch_match.groups())
    for actual, expected in zip(browser_latch, case_latch):
        if abs(actual - expected) > 0.001:
            raise AssertionError(
                f"browser latch {browser_latch} differs from case latch {case_latch}"
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
                    "--virtual-time-budget=30000",
                    "--dump-dom",
                    f"http://127.0.0.1:{server.server_port}/index.html?selftest=1",
                ],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=45,
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
    if result.get("closedLatchContact") is not True:
        raise AssertionError("case browser missed the intended closed latch contact")
    release_angle = result.get("latchReleaseAngle")
    if not isinstance(release_angle, (int, float)) or not 0 < release_angle <= 20:
        raise AssertionError(
            f"case latch did not release in the expected opening range: {release_angle}"
        )
    first_surface_contact = result.get("firstSurfaceContactAfterRelease")
    closed_highlights = int(result.get("closedHighlightPoints", 0))
    if closed_highlights <= 0 or int(result.get("releasedHighlightPoints", -1)) != 0:
        raise AssertionError(
            "collision highlight does not track latch engagement and release: "
            f"{result}"
        )
    probe_contacts = int(result.get("detectorProbeContacts", 0))
    if probe_contacts <= 0:
        raise AssertionError("clearance detector missed the penetration probe")
    if result.get("quenaWithinCasePlan") is not True:
        raise AssertionError("one or more quena sections extend outside the case plan")
    if result.get("quenaHolesFaceOutward") is not True:
        raise AssertionError("one or more quena sections have holes facing into the case")
    if result.get("engravingVisible") is not True or result.get("logoVisible") is not True:
        raise AssertionError("browser did not load both case decoration meshes")
    if result.get("decorationsHaveDistinctColors") is not True:
        raise AssertionError("browser logo and mandala decorations do not have distinct colors")
    if result.get("engravingContrastsWithLid") is not True:
        raise AssertionError("case engraving color does not contrast with the lid")
    if int(result.get("appearanceControlCount", 0)) != 7:
        raise AssertionError("browser does not expose one appearance control per mesh")
    if result.get("appearanceSelectionWorks") is not True:
        raise AssertionError("browser shader and color selection did not update a mesh")
    if result.get("studioLightingConfigured") is not True:
        raise AssertionError("browser studio environment or soft-shadow rig is incomplete")
    if result.get("studioSurfaceConfigured") is not True:
        raise AssertionError("browser transparent shadow catcher is incomplete")
    if result.get("sweepControlsWork") is not True:
        raise AssertionError("browser Run Sweep control does not start from zero")
    if result.get("pauseControlWorks") is not True:
        raise AssertionError("browser Pause control does not stop the sweep")
    if result.get("animationLoopAdvanced") is not True:
        raise AssertionError("browser animation loop did not advance after initial render")
    if result.get("pass") is not True:
        raise AssertionError(f"case browser self-test failed: {result}")
    print(
        "QuenaCase browser sweep: ok, intended latch contact at 0 deg, "
        f"release by {release_angle:g} deg; first post-release surface contact="
        f"{first_surface_contact}; "
        f"contact highlight points={closed_highlights}; penetration probe "
        f"contacts={probe_contacts}; quena sections within case plan "
        "with holes facing outward; coral logo and gold mandala/flourish "
        "meshes follow their case halves"
    )


if __name__ == "__main__":
    main()
