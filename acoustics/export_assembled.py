#!/usr/bin/env python3
"""Export assembled AgnuQuena plastic and internal-air STL files."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

import trimesh


REPO_ROOT = Path(__file__).resolve().parents[1]
OPENSCAD = REPO_ROOT / "tools" / "openscad"


def remove_triangulation_debris(path: Path) -> int:
    """Remove proven zero-volume triangulation debris from a Manifold export."""
    mesh = trimesh.load(path, force="mesh")
    components = mesh.split(only_watertight=False)
    solids = []
    debris = []
    for component in components:
        if (
            component.is_watertight
            and len(component.faces) >= 4
            and abs(component.volume) > 1e-6
        ):
            solids.append(component)
        else:
            debris.append(component)
    if not solids:
        raise RuntimeError(f"{path.name}: OpenSCAD export contains no solid components")
    invalid = [
        component
        for component in debris
        if not (
            len(component.faces) <= 2
            or (
                component.is_watertight
                and len(component.faces) <= 4
                and abs(component.volume) <= 1e-6
            )
        )
    ]
    if invalid:
        raise RuntimeError(f"{path.name}: OpenSCAD export contains an open solid")
    if debris:
        cleaned = trimesh.util.concatenate(solids)
        ascii_stl = trimesh.exchange.stl.export_stl_ascii(cleaned)
        ascii_stl = ascii_stl.replace("solid \n", "solid mesh\n", 1)
        ascii_stl = ascii_stl.replace("endsolid \n", "endsolid mesh\n", 1)
        path.write_text(
            ascii_stl,
            encoding="ascii",
        )
    return len(debris)


def render(scad: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=output.parent,
        prefix=f".{output.stem}.",
        suffix=".stl",
    )
    os.close(file_descriptor)
    temporary = Path(temporary_name)
    try:
        subprocess.run(
            [
                str(OPENSCAD),
                "--backend=Manifold",
                "-o",
                str(temporary),
                str(scad),
            ],
            cwd=REPO_ROOT,
            check=True,
        )
        remove_triangulation_debris(temporary)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


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
