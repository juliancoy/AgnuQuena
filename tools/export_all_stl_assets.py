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
    run("tools/render_case_assets.py", "--stls", "--force")
    run("tools/test_case_stls.py")
    run("acoustics/export_assembled.py")
    print("All source-backed STL assets exported and validated.")


if __name__ == "__main__":
    main()
