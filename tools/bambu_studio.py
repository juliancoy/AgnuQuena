"""Project-local access to the native BambuStudio CLI runtime."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "BambuStudio"
RUNTIME_ROOT = SOURCE_ROOT / "build-direct"
BINARY = RUNTIME_ROOT / "bin" / "bambu-studio"
PROFILE_ROOT = RUNTIME_ROOT / "resources" / "profiles" / "BBL"


def source_commit() -> str:
    git_file = SOURCE_ROOT / ".git"
    if not git_file.exists():
        raise SystemExit("BambuStudio submodule is not initialized")
    return subprocess.check_output(
        ["git", "-C", str(SOURCE_ROOT), "rev-parse", "HEAD"], text=True
    ).strip()


def require() -> None:
    if not BINARY.is_file() or not os.access(BINARY, os.X_OK):
        raise SystemExit(
            "The project-local BambuStudio CLI is not built; "
            "run `make bambu-studio-setup` first"
        )
    marker = RUNTIME_ROOT / ".source-commit"
    if (
        not marker.is_file()
        or marker.read_text(encoding="utf-8").strip() != source_commit()
    ):
        raise SystemExit(
            "The project-local BambuStudio runtime is stale; "
            "run `make bambu-studio-setup`"
        )
    if not PROFILE_ROOT.is_dir():
        raise SystemExit("BambuStudio profile resources are missing from the submodule")


def environment() -> dict[str, str]:
    env = os.environ.copy()
    dependency_lib = RUNTIME_ROOT / "bin"
    existing = env.get("LD_LIBRARY_PATH")
    env["LD_LIBRARY_PATH"] = (
        f"{dependency_lib}{os.pathsep}{existing}" if existing else str(dependency_lib)
    )
    env["LC_ALL"] = "C"
    return env


def command(*arguments: str | Path) -> list[str]:
    require()
    return [str(BINARY), *(str(argument) for argument in arguments)]


def version() -> str:
    marker = RUNTIME_ROOT / ".source-version"
    if not marker.is_file():
        raise SystemExit("BambuStudio source version marker is missing")
    return marker.read_text(encoding="utf-8").strip()
