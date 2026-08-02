#!/usr/bin/env python3
"""Export and validate production Quena STL components."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import trimesh


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = REPO_ROOT / "tools" / "generate_quena.py"
SCAD_SOURCE = REPO_ROOT / "Quena.scad"
GENERATED_MANIFEST = REPO_ROOT / "generated" / "quena_manifest.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "build" / "quena"
PARTS = {
    "mouthpiece": ("part1", "QuenaMouthpiece.stl"),
    "tube1": ("part2", "QuenaTube1.stl"),
    "tube2": ("part3", "QuenaTube2.stl"),
    "layout": ("layout", "QuenaLayout.stl"),
}


def ensure_generated_files_are_current() -> None:
    subprocess.run(
        [sys.executable, str(GENERATOR), "--check"],
        cwd=REPO_ROOT,
        check=True,
    )


def export_stl(export_part: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.stem}.",
        suffix=".stl",
    )
    os.close(file_descriptor)
    temporary = Path(temporary_name)
    try:
        subprocess.run(
            [
                "openscad",
                "-D",
                f'export_part="{export_part}"',
                "-o",
                str(temporary),
                str(SCAD_SOURCE),
            ],
            cwd=REPO_ROOT,
            check=True,
        )
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def validate_stl(path: Path, expected_components: int) -> dict[str, object]:
    mesh = trimesh.load(path, force="mesh")
    components = mesh.split(only_watertight=False)
    if not mesh.is_watertight:
        raise RuntimeError(f"{path.name} is not watertight")
    if len(components) != expected_components:
        raise RuntimeError(
            f"{path.name} has {len(components)} components; expected {expected_components}"
        )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "file": path.name,
        "sha256": digest,
        "watertight": True,
        "components": len(components),
        "vertices": int(len(mesh.vertices)),
        "faces": int(len(mesh.faces)),
        "bounds_mm": [[float(value) for value in row] for row in mesh.bounds],
        "extents_mm": [float(value) for value in mesh.extents],
        "volume_mm3": float(mesh.volume),
    }


def validate_rounded_mouthpiece_lip(
    path: Path,
    bore_diameter_mm: float,
    outer_diameter_mm: float,
) -> float:
    mesh = trimesh.load(path, force="mesh")
    lip_vertices = mesh.vertices[np.abs(mesh.vertices[:, 2] - mesh.bounds[0, 2]) < 0.001]
    if len(lip_vertices) < 16:
        raise RuntimeError("mouthpiece blowing lip has too few terminal vertices")
    radial = np.linalg.norm(lip_vertices[:, :2], axis=1)
    expected_mid_radius = (bore_diameter_mm + outer_diameter_mm) / 4.0
    # The angled notch creates a narrow band of tessellated terminal vertices;
    # a flat annular rim would span the full 0.8 mm wall instead.
    if np.ptp(radial) > 0.10 or abs(float(np.mean(radial)) - expected_mid_radius) > 0.03:
        raise RuntimeError("mouthpiece blowing lip is not a continuous rounded wall")
    return (outer_diameter_mm - bore_diameter_mm) / 4.0


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--part",
        choices=["all", *PARTS],
        default="all",
        help="component to export; all exports the three printable pieces",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    ensure_generated_files_are_current()
    generated_manifest = json.loads(GENERATED_MANIFEST.read_text(encoding="utf-8"))
    selected = ["mouthpiece", "tube1", "tube2"] if args.part == "all" else [args.part]

    results: list[dict[str, object]] = []
    for name in selected:
        export_part, filename = PARTS[name]
        destination = args.output_dir / filename
        print(f"exporting {name}: {destination}")
        export_stl(export_part, destination)
        expected_components = 3 if name == "layout" else 1
        result = validate_stl(destination, expected_components)
        if name == "mouthpiece":
            geometry = generated_manifest["geometry"]
            result["blowing_lip_rounding_radius_mm"] = validate_rounded_mouthpiece_lip(
                destination,
                float(geometry["bore_id_mm"]),
                float(geometry["outer_diameter_mm"]),
            )
        result["part"] = name
        results.append(result)
        print(
            f"validated {filename}: watertight, "
            f"height={result['extents_mm'][2]:.3f} mm"
        )

    export_manifest = {
        "schema_version": 1,
        "design_id": generated_manifest["design_id"],
        "spec_sha256": generated_manifest["spec_sha256"],
        "source": "Quena.scad",
        "parts": results,
    }
    manifest_path = args.output_dir / "production_export.json"
    atomic_write_text(
        manifest_path,
        json.dumps(export_manifest, indent=2, sort_keys=True) + "\n",
    )
    print(f"wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
