#!/usr/bin/env python3
"""Force-export and validate every source-backed AgnuQuena STL asset."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from export_quena import validate_stl


ROOT = Path(__file__).resolve().parents[1]
ROOT_STL_ALIASES = {
    ROOT / "build" / "quena" / "QuenaMouthpiece.stl": ROOT / "QuenaPart1.stl",
    ROOT / "build" / "quena" / "QuenaTube1.stl": ROOT / "QuenaPart2.stl",
    ROOT / "build" / "quena" / "QuenaTube2.stl": ROOT / "QuenaPart3.stl",
    ROOT / "build" / "quena-layout" / "QuenaLayout.stl": ROOT / "Quena.stl",
}
SITE_STL_ASSETS = {
    ROOT / "build" / "quena" / "QuenaMouthpiece.stl": "QuenaMouthpiece.stl",
    ROOT / "build" / "quena" / "QuenaTube1.stl": "QuenaTube1.stl",
    ROOT / "build" / "quena" / "QuenaTube2.stl": "QuenaTube2.stl",
}
SITE_ASSET_DIRECTORIES = (
    ROOT / "website" / "assets",
    ROOT / "site-hosting" / "public" / "assets",
)


def run(*args: str) -> None:
    command = [sys.executable, *args]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def update_root_stl_aliases() -> None:
    for source, destination in ROOT_STL_ALIASES.items():
        shutil.copy2(source, destination)
        expected_components = 3 if destination.name == "Quena.stl" else 1
        validate_stl(destination, expected_components)
        print(f"updated and validated {destination.relative_to(ROOT)}", flush=True)


def update_site_stl_assets() -> None:
    for source, name in SITE_STL_ASSETS.items():
        for directory in SITE_ASSET_DIRECTORIES:
            destination = directory / name
            shutil.copy2(source, destination)
            validate_stl(destination, 1)
            print(f"updated and validated {destination.relative_to(ROOT)}", flush=True)


def main() -> None:
    run("tools/generate_quena.py")
    run("tools/export_quena.py")
    run(
        "tools/export_quena.py",
        "--part",
        "layout",
        "--output-dir",
        "build/quena-layout",
    )
    update_root_stl_aliases()
    update_site_stl_assets()
    run("tools/build_quena_3mf.py")
    run("tools/render_case_assets.py", "--all-meshes", "--force")
    run("tools/build_case_3mf.py")
    run("tools/test_case_stls.py")
    run("acoustics/export_assembled.py")
    print("All source-backed STL assets exported and validated.")


if __name__ == "__main__":
    main()
