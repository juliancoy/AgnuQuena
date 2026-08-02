#!/usr/bin/env python3
"""Install the official native BambuStudio CLI beside its source submodule."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "BambuStudio" / "build-direct"
NAME = "BambuStudio_ubuntu24.04-v02.07.01.62-20260616195227.AppImage"
URL = f"https://github.com/bambulab/BambuStudio/releases/download/v02.07.01.62/{NAME}"
EXPECTED_SHA256 = "fa98b608532dfbbbb2b0931483aac41e57fb19c175a2cc7bd7d528d5e0fbb287"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    appimage = DESTINATION / NAME
    if not appimage.exists() or sha256(appimage) != EXPECTED_SHA256:
        temporary = DESTINATION / f".{NAME}.download"
        temporary.unlink(missing_ok=True)
        print(f"Downloading {URL}", flush=True)
        urllib.request.urlretrieve(URL, temporary)
        actual = sha256(temporary)
        if actual != EXPECTED_SHA256:
            temporary.unlink(missing_ok=True)
            raise SystemExit(f"BambuStudio download checksum mismatch: {actual}")
        os.replace(temporary, appimage)

    appimage.chmod(appimage.stat().st_mode | 0o111)
    appdir = DESTINATION / "appdir"
    binary = appdir / "bin" / "bambu-studio"
    marker = appdir / ".source-sha256"
    runtime_is_current = (
        binary.exists()
        and marker.exists()
        and marker.read_text(encoding="utf-8").strip() == EXPECTED_SHA256
    )
    if not runtime_is_current:
        extracted = DESTINATION / "squashfs-root"
        if extracted.exists():
            shutil.rmtree(extracted)
        subprocess.run(
            [str(appimage), "--appimage-extract"],
            cwd=DESTINATION,
            stdout=subprocess.DEVNULL,
            check=True,
        )
        if appdir.exists():
            shutil.rmtree(appdir)
        os.replace(extracted, appdir)
        marker.write_text(f"{EXPECTED_SHA256}\n", encoding="utf-8")
    print(f"BambuStudio CLI ready: {binary.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
