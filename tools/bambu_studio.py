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


def gui_environment() -> dict[str, str]:
    """Return the runtime environment for the Linux desktop application."""
    env = environment()
    # WebKitGTK's DMA-BUF renderer corrupts memory on this NVIDIA/X11 display.
    # This leaves Bambu Studio's OpenGL model canvas hardware accelerated.
    env["WEBKIT_DISABLE_DMABUF_RENDERER"] = "1"
    return env


def command(*arguments: str | Path) -> list[str]:
    require()
    return [str(BINARY), *(str(argument) for argument in arguments)]


def absolute_existing_paths(
    arguments: list[str], *, cwd: Path | None = None
) -> list[str]:
    """Resolve existing relative inputs before Bambu Studio changes directory."""
    base = cwd or Path.cwd()
    resolved: list[str] = []
    for argument in arguments:
        candidate = base / argument
        resolved.append(str(candidate.resolve()) if candidate.exists() else argument)
    return resolved


def version() -> str:
    marker = RUNTIME_ROOT / ".source-version"
    if not marker.is_file():
        raise SystemExit("BambuStudio source version marker is missing")
    return marker.read_text(encoding="utf-8").strip()
