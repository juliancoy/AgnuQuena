#!/usr/bin/env python3
"""Export and validate every active Quena case asset."""

from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> None:
    command = [sys.executable, *args]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def render_and_validate_stls() -> None:
    """Render STLs before validating the newly generated meshes."""
    run("tools/render_case_assets.py", "--all-meshes")
    run("tools/build_case_3mf.py")
    run("tools/test_case_stls.py")
    run("tools/test_case_browser.py")


def main() -> None:
    jobs: tuple[Callable[[], None], ...] = (
        render_and_validate_stls,
        lambda: run("tools/render_case_assets.py", "--all-views"),
        lambda: run("tools/model_latch_snap.py", "--material", "all"),
        lambda: run("tools/simulate_case_inversion.py"),
    )

    with ThreadPoolExecutor(max_workers=len(jobs)) as executor:
        futures = [executor.submit(job) for job in jobs]
        for future in futures:
            future.result()

    print("All Quena case assets exported and validated.")


if __name__ == "__main__":
    main()
