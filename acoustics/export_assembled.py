#!/usr/bin/env python3
"""Export assembled AgnuQuena plastic and internal-air STL files."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import trimesh


REPO_ROOT = Path(__file__).resolve().parents[1]


def render(scad: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["openscad", "-o", str(output), str(scad)], cwd=REPO_ROOT, check=True)


def validate(path: Path) -> dict[str, object]:
    mesh = trimesh.load(path, force="mesh")
    components = mesh.split(only_watertight=False)
    return {
        "path": str(path),
        "watertight": bool(mesh.is_watertight),
        "components": len(components),
        "faces": int(len(mesh.faces)),
        "vertices": int(len(mesh.vertices)),
        "bounds_mm": mesh.bounds.tolist(),
        "volume_mm3": float(mesh.volume),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="acoustics/out")
    args = parser.parse_args()

    out_dir = REPO_ROOT / args.out_dir
    plastic_stl = out_dir / "assembled_quena.stl"
    air_stl = out_dir / "assembled_air.stl"

    render(REPO_ROOT / "acoustics" / "assembled_quena.scad", plastic_stl)
    render(REPO_ROOT / "acoustics" / "assembled_air.scad", air_stl)

    manifest = {
        "plastic": validate(plastic_stl),
        "air": validate(air_stl),
    }
    manifest_path = out_dir / "assembled_validation.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    for key, result in manifest.items():
        print(
            f"{key}: watertight={result['watertight']} "
            f"components={result['components']} faces={result['faces']}"
        )
    print(f"wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
