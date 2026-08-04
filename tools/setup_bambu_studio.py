#!/usr/bin/env python3
"""Build and install BambuStudio directly from the pinned source submodule."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import urllib.request
import zipfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "BambuStudio"
BUILD_ROOT = Path(
    os.environ.get("BAMBU_STUDIO_BUILD_ROOT", SOURCE_ROOT / "build-agnuquena")
).resolve()
DEPS_BUILD = BUILD_ROOT / "deps"
STUDIO_BUILD = BUILD_ROOT / "studio"
NODE_CACHE = BUILD_ROOT / "node-cache"
BUILD_MARKER = STUDIO_BUILD / ".agnuquena-source-commit"
RUNTIME_ROOT = SOURCE_ROOT / "build-direct"
STAGING_RUNTIME = SOURCE_ROOT / "build-direct.next"
BUILDER_IMAGE = "agnuquena-bambu-studio-builder:ubuntu24.04"
DOCKERFILE = ROOT / "tools" / "bambu_studio_builder.Dockerfile"
DATA_ROOT = Path(
    os.environ.get(
        "BAMBU_STUDIO_DATA_DIR",
        Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        / "BambuStudio",
    )
).expanduser().resolve()
NETWORK_PLUGIN_VERSION = "02.08.01.53"
NETWORK_PLUGIN_URL = (
    "https://public-cdn.bblmw.com/upgrade/studio/plugins/02.08.01.53/"
    "f3e6f57c37/linux_02.08.01.53.zip"
)
NETWORK_PLUGIN_SHA256 = (
    "9b567b4fb137ee6b2b1ed5f8c8967193a9418b271eceb409f5c43be1662761e1"
)
NETWORK_PLUGIN_FILES = {
    "libBambuSource.so",
    "libagora-fdkaac.so",
    "libagora_rtc_sdk.so",
    "libbambu_networking.so",
    "liblive555.so",
}


def run(arguments: list[str], **kwargs: object) -> None:
    print("+", " ".join(arguments), flush=True)
    subprocess.run(arguments, check=True, **kwargs)


def output(arguments: list[str]) -> str:
    return subprocess.check_output(arguments, text=True).strip()


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def install_network_plugin() -> None:
    plugin_root = DATA_ROOT / "plugins"
    marker = plugin_root / ".agnuquena-network-plugin"
    expected_marker = f"{NETWORK_PLUGIN_VERSION} {NETWORK_PLUGIN_SHA256}"
    if (
        marker.is_file()
        and marker.read_text(encoding="utf-8").strip() == expected_marker
        and all((plugin_root / name).is_file() for name in NETWORK_PLUGIN_FILES)
    ):
        print(f"Bambu networking plugin {NETWORK_PLUGIN_VERSION} is already installed")
        return

    download_root = BUILD_ROOT / "downloads"
    download_root.mkdir(parents=True, exist_ok=True)
    archive_path = download_root / f"network-plugin-{NETWORK_PLUGIN_VERSION}.zip"
    if not archive_path.is_file() or file_sha256(archive_path) != NETWORK_PLUGIN_SHA256:
        temporary_archive = archive_path.with_suffix(".download")
        temporary_archive.unlink(missing_ok=True)
        print(f"Downloading Bambu networking plugin {NETWORK_PLUGIN_VERSION}", flush=True)
        urllib.request.urlretrieve(NETWORK_PLUGIN_URL, temporary_archive)
        actual_sha256 = file_sha256(temporary_archive)
        if actual_sha256 != NETWORK_PLUGIN_SHA256:
            temporary_archive.unlink(missing_ok=True)
            raise SystemExit(
                "Bambu networking plugin checksum mismatch: "
                f"{actual_sha256}"
            )
        os.replace(temporary_archive, archive_path)

    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    staging = DATA_ROOT / ".plugins.agnuquena.next"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    with zipfile.ZipFile(archive_path) as archive:
        members = {entry.filename for entry in archive.infolist() if not entry.is_dir()}
        if members != NETWORK_PLUGIN_FILES:
            raise SystemExit(
                "Unexpected files in Bambu networking plugin: "
                f"{sorted(members)}"
            )
        archive.extractall(staging)
    (staging / ".agnuquena-network-plugin").write_text(
        f"{expected_marker}\n", encoding="utf-8"
    )

    backup: Path | None = None
    if plugin_root.exists():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = DATA_ROOT / f"plugins.before-agnuquena-{timestamp}-{os.getpid()}"
        os.replace(plugin_root, backup)
    try:
        os.replace(staging, plugin_root)
    except BaseException:
        if backup is not None and backup.exists() and not plugin_root.exists():
            os.replace(backup, plugin_root)
        raise

    message = f"Bambu networking plugin {NETWORK_PLUGIN_VERSION} installed in {plugin_root}"
    if backup is not None:
        message += f"; previous plugin retained at {backup}"
    print(message)


def main() -> None:
    if not (SOURCE_ROOT / ".git").exists():
        raise SystemExit(
            "BambuStudio submodule is not initialized; run "
            "`git submodule update --init --recursive BambuStudio`"
        )
    if not shutil.which("docker"):
        raise SystemExit("Docker is required to build BambuStudio from source")

    source_commit = output(["git", "-C", str(SOURCE_ROOT), "rev-parse", "HEAD"])
    version_text = (SOURCE_ROOT / "version.inc").read_text(encoding="utf-8")
    version_match = re.search(r'set\(SLIC3R_VERSION "([^"]+)"\)', version_text)
    if not version_match:
        raise SystemExit("Unable to determine BambuStudio version from version.inc")
    version = version_match.group(1)
    marker = RUNTIME_ROOT / ".source-commit"
    binary = RUNTIME_ROOT / "bin" / "bambu-studio"
    if (
        binary.is_file()
        and os.access(binary, os.X_OK)
        and marker.is_file()
        and marker.read_text(encoding="utf-8").strip() == source_commit
    ):
        print(f"BambuStudio {version} is already built from {source_commit[:12]}")
        print("Launch the validated runtime with `./bambu-studio`.")
        shutil.rmtree(STAGING_RUNTIME, ignore_errors=True)
        install_network_plugin()
        return

    run(
        [
            "docker",
            "build",
            "--tag",
            BUILDER_IMAGE,
            "--file",
            str(DOCKERFILE),
            str(ROOT),
        ]
    )
    DEPS_BUILD.mkdir(parents=True, exist_ok=True)
    STUDIO_BUILD.mkdir(parents=True, exist_ok=True)
    NODE_CACHE.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(STAGING_RUNTIME, ignore_errors=True)
    STAGING_RUNTIME.mkdir()
    uid_gid = f"{os.getuid()}:{os.getgid()}"
    docker_run = [
        "docker",
        "run",
        "--rm",
        "--user",
        uid_gid,
        "--volume",
        f"{SOURCE_ROOT}:/src",
        "--volume",
        f"{ROOT / '.git'}:/.git:ro",
        "--volume",
        f"{DEPS_BUILD}:/src/deps/build",
        "--volume",
        f"{STUDIO_BUILD}:/src/build",
        "--volume",
        f"{NODE_CACHE}:/node-cache",
        "--workdir",
        "/src",
        BUILDER_IMAGE,
    ]
    if not (
        BUILD_MARKER.is_file()
        and BUILD_MARKER.read_text(encoding="utf-8").strip() == source_commit
    ):
        run([*docker_run, "bash", "-lc", "./BuildLinux.sh -rds"])
        BUILD_MARKER.write_text(f"{source_commit}\n", encoding="utf-8")
    run(
        [
            *docker_run,
            "bash",
            "-lc",
            "DESTDIR=/src/build-direct.next cmake --install build --strip",
        ]
    )
    installed_prefix = STAGING_RUNTIME / "usr" / "local"
    installed_binary = installed_prefix / "bin" / "bambu-studio"
    if not installed_binary.is_file():
        raise SystemExit(f"BambuStudio install did not produce {installed_binary}")
    for installed_item in installed_prefix.iterdir():
        os.replace(installed_item, STAGING_RUNTIME / installed_item.name)
    shutil.rmtree(STAGING_RUNTIME / "usr")
    (STAGING_RUNTIME / ".source-commit").write_text(
        f"{source_commit}\n", encoding="utf-8"
    )
    (STAGING_RUNTIME / ".source-version").write_text(f"{version}\n", encoding="utf-8")

    previous = SOURCE_ROOT / "build-direct.previous"
    shutil.rmtree(previous, ignore_errors=True)
    if RUNTIME_ROOT.exists():
        os.replace(RUNTIME_ROOT, previous)
    os.replace(STAGING_RUNTIME, RUNTIME_ROOT)
    shutil.rmtree(previous, ignore_errors=True)
    print(
        f"BambuStudio {version} built from {source_commit[:12]}: "
        f"{binary.relative_to(ROOT)}"
    )
    print("Launch the validated runtime with `./bambu-studio`.")
    install_network_plugin()


if __name__ == "__main__":
    main()
