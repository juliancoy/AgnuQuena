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


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_viewer_assets() -> None:
    for name in ("QuenaCaseBottomViewer.stl", "QuenaCaseLidViewer.stl"):
        paths = (
            ROOT / name,
            ROOT / "website" / "assets" / name,
            ROOT / "site-hosting" / "public" / "assets" / name,
        )
        hashes = {sha256(path) for path in paths}
        if len(hashes) != 1:
            raise AssertionError(f"{name}: canonical and site assets differ")


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
    result = run_browser_self_test()
    if result.get("firstSweepCollision") is not None:
        raise AssertionError(
            f"case browser sweep collides at {result['firstSweepCollision']} degrees"
        )
    probe_contacts = int(result.get("detectorProbeContacts", 0))
    if probe_contacts <= 0:
        raise AssertionError("clearance detector missed the penetration probe")
    if result.get("pass") is not True:
        raise AssertionError(f"case browser self-test failed: {result}")
    print(
        "QuenaCase browser sweep: ok, 0-180 deg exact-triangle clearance; "
        f"penetration probe contacts={probe_contacts}"
    )


if __name__ == "__main__":
    main()
