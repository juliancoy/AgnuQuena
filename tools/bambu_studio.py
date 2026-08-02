"""Project-local access to the native BambuStudio CLI runtime."""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "BambuStudio"
RUNTIME_ROOT = SOURCE_ROOT / "build-direct" / "appdir"
BINARY = RUNTIME_ROOT / "bin" / "bambu-studio"
PROFILE_ROOT = RUNTIME_ROOT / "resources" / "profiles" / "BBL"
VERSION = "02.07.01.62"
RUNTIME_SHA256 = "fa98b608532dfbbbb2b0931483aac41e57fb19c175a2cc7bd7d528d5e0fbb287"


def require() -> None:
    if not BINARY.is_file() or not os.access(BINARY, os.X_OK):
        raise SystemExit(
            "The project-local BambuStudio CLI is not built; "
            "run `make bambu-studio-setup` first"
        )
    marker = RUNTIME_ROOT / ".source-sha256"
    if not marker.is_file() or marker.read_text(encoding="utf-8").strip() != RUNTIME_SHA256:
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
    return VERSION
