#!/usr/bin/env python3
"""Build browser assets from the validated production flute STLs."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

import numpy as np
import trimesh


ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = ROOT / "build" / "quena"
ASSET_DIR = ROOT / "website" / "assets"
EXPORT_MANIFEST = EXPORT_DIR / "production_export.json"

PARTS = (
    ("QuenaMouthpiece.stl", 0.0, 0.0),
    ("QuenaTube1.stl", 30.0, 90.0),
    ("QuenaTube2.stl", 252.0, -90.0),
)

CELL_MM = 1.0
NX = 48
NY = 48
NZ = 424
Z_ORIGIN_MM = -12.0
SAMPLES_PER_SQUARE_MM = 60
RANDOM_SEED = 0xA6_4E_51


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_parts() -> list[tuple[Path, float, float, trimesh.Trimesh]]:
    manifest = json.loads(EXPORT_MANIFEST.read_text(encoding="utf-8"))
    expected = {part["file"]: part["sha256"] for part in manifest["parts"]}
    result: list[tuple[Path, float, float, trimesh.Trimesh]] = []
    for filename, z_offset, rotation_z_degrees in PARTS:
        path = EXPORT_DIR / filename
        digest = sha256(path)
        if digest != expected.get(filename):
            raise RuntimeError(f"{filename} does not match production_export.json")
        mesh = trimesh.load(path, force="mesh")
        if not mesh.is_watertight:
            raise RuntimeError(f"{filename} is not watertight")
        mesh.apply_transform(
            trimesh.transformations.rotation_matrix(
                math.radians(rotation_z_degrees),
                (0.0, 0.0, 1.0),
            )
        )
        mesh.apply_translation((0.0, 0.0, z_offset))
        result.append((path, z_offset, rotation_z_degrees, mesh))
    return result


def mark_surface(mask: np.ndarray, points: np.ndarray) -> None:
    x = np.rint(points[:, 0] / CELL_MM + (NX - 1) / 2).astype(np.int32)
    y = np.rint(points[:, 1] / CELL_MM + (NY - 1) / 2).astype(np.int32)
    z = np.rint((points[:, 2] - Z_ORIGIN_MM) / CELL_MM - 0.5).astype(np.int32)
    valid = (x >= 0) & (x < NX) & (y >= 0) & (y < NY) & (z >= 0) & (z < NZ)
    mask[x[valid] + NX * (y[valid] + NY * z[valid])] = 1


def build_surface_mask(meshes: list[trimesh.Trimesh]) -> np.ndarray:
    np.random.seed(RANDOM_SEED)
    mask = np.zeros(NX * NY * NZ, dtype=np.uint8)
    for mesh in meshes:
        sample_count = max(50_000, math.ceil(mesh.area * SAMPLES_PER_SQUARE_MM))
        points, _ = trimesh.sample.sample_surface(mesh, sample_count)
        mark_surface(mask, points)
        mark_surface(mask, mesh.vertices)

    volume = mask.reshape((NZ, NY, NX))
    occupied_per_slice = np.count_nonzero(volume, axis=(1, 2))
    flute_slices = occupied_per_slice[12:417]
    if np.any(flute_slices == 0):
        missing = np.flatnonzero(flute_slices == 0) + 12
        raise RuntimeError(f"STL surface mask has empty axial slices: {missing.tolist()}")
    if np.any(volume[:, NY // 2, NX // 2]):
        raise RuntimeError("STL surface mask incorrectly blocks the bore centerline")
    return mask


def main() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    parts = checked_parts()
    meshes = [mesh for _, _, _, mesh in parts]
    assembly = trimesh.util.concatenate(meshes)
    assembly_path = ASSET_DIR / "QuenaProductionAssembly.stl"
    assembly.export(assembly_path)

    for source, _, _, _ in parts:
        shutil.copy2(source, ASSET_DIR / source.name)

    mask = build_surface_mask(meshes)
    mask_path = ASSET_DIR / "QuenaProductionSolidMask.u8"
    mask_path.write_bytes(mask.tobytes())

    source_manifest = json.loads(EXPORT_MANIFEST.read_text(encoding="utf-8"))
    metadata = {
        "schema_version": 1,
        "design_id": source_manifest["design_id"],
        "spec_sha256": source_manifest["spec_sha256"],
        "assembly": {
            "file": assembly_path.name,
            "sha256": sha256(assembly_path),
            "bounds_mm": assembly.bounds.tolist(),
            "faces": int(len(assembly.faces)),
            "vertices": int(len(assembly.vertices)),
        },
        "parts": [
            {
                "file": source.name,
                "sha256": sha256(source),
                "z_offset_mm": z_offset,
                "assembly_rotation_z_degrees": rotation_z_degrees,
            }
            for source, z_offset, rotation_z_degrees, _ in parts
        ],
        "solver_mask": {
            "file": mask_path.name,
            "sha256": sha256(mask_path),
            "grid": [NX, NY, NZ],
            "cell_mm": CELL_MM,
            "z_origin_mm": Z_ORIGIN_MM,
            "solid_cells": int(np.count_nonzero(mask)),
            "derivation": "production STL triangle-surface sampling",
            "samples_per_square_mm": SAMPLES_PER_SQUARE_MM,
            "random_seed": RANDOM_SEED,
        },
    }
    metadata_path = ASSET_DIR / "QuenaProductionCFD.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
