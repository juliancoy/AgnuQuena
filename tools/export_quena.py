#!/usr/bin/env python3
"""Export and validate production Quena STL components."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import trimesh


REPO_ROOT = Path(__file__).resolve().parents[1]
OPENSCAD = REPO_ROOT / "tools" / "openscad"
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
                str(OPENSCAD),
                "--backend=Manifold",
                "-D",
                f'export_part="{export_part}"',
                "-o",
                str(temporary),
                str(SCAD_SOURCE),
            ],
            cwd=REPO_ROOT,
            check=True,
        )
        removed = remove_triangulation_debris(temporary)
        if removed:
            print(f"removed {removed} non-solid triangulation shells")
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


def validate_tube_joint_owner(
    results: list[dict[str, object]],
    generated_manifest: dict[str, object],
    output_dir: Path,
) -> None:
    by_part = {str(result["part"]): result for result in results}
    if not {"tube1", "tube2"} <= by_part.keys():
        return
    connector = generated_manifest["connectors"]
    if connector["tube_joint_connector_part"] != 2:
        raise RuntimeError("production tube-joint sleeve must belong to P2")
    parts = {part["name"]: part for part in generated_manifest["parts"]}
    overlap = float(connector["tube_joint_overlap_mm"])
    tip_transition = float(connector["tube_joint_tip_transition_mm"])
    connector_extra = overlap + tip_transition
    tube1_bounds = by_part["tube1"]["bounds_mm"]
    tube2_bounds = by_part["tube2"]["bounds_mm"]
    if not math.isclose(float(tube1_bounds[0][2]), 0.0, abs_tol=0.01):
        raise RuntimeError("P1 unexpectedly owns geometry below its body origin")
    if not math.isclose(
        float(tube1_bounds[1][2]),
        float(parts["tube_1"]["length_mm"]),
        abs_tol=0.01,
    ):
        raise RuntimeError("P1 still carries the tube-joint sleeve")
    if not math.isclose(float(tube2_bounds[0][2]), -connector_extra, abs_tol=0.01):
        raise RuntimeError("P2 lower sleeve does not span the required joint overlap")
    if not math.isclose(
        float(tube2_bounds[1][2]),
        float(parts["tube_2"]["length_mm"]),
        abs_tol=0.01,
    ):
        raise RuntimeError("P2 body origin or free end moved unexpectedly")

    tube1 = trimesh.load(output_dir / PARTS["tube1"][1], force="mesh")
    tube2 = trimesh.load(output_dir / PARTS["tube2"][1], force="mesh")
    tube_outer_diameter = float(
        generated_manifest["geometry"]["outer_diameter_mm"]
    )
    tube1_xy_extents = np.asarray(tube1.extents[:2], dtype=float)
    if np.max(np.abs(tube1_xy_extents - tube_outer_diameter)) > 0.01:
        raise RuntimeError("P1 tube radius changed outside the overlap socket")
    by_part["tube1"]["unchanged_tube_outer_diameter_mm"] = tube_outer_diameter
    tube1_length = float(parts["tube_1"]["length_mm"])
    expected_clearance = float(connector["tube_joint_radial_clearance_mm"])
    measured_clearances = []
    # Sample the complete socket away from its two boundary faces. P1's
    # outside radius must follow P2's inside radius for the full overlap.
    for fraction in np.linspace(0.05, 0.95, 10):
        insertion = overlap * float(fraction)
        p1_section = tube1.section(
            plane_origin=[0, 0, tube1_length - overlap + insertion],
            plane_normal=[0, 0, 1],
        )
        p2_section = tube2.section(
            plane_origin=[0, 0, -overlap + insertion],
            plane_normal=[0, 0, 1],
        )
        if p1_section is None or p2_section is None:
            raise RuntimeError("tube-joint fit section is missing from an export")
        p1_outer_radius = float(
            np.max(np.linalg.norm(p1_section.vertices[:, :2], axis=1))
        )
        p2_inner_radius = float(
            np.min(np.linalg.norm(p2_section.vertices[:, :2], axis=1))
        )
        measured_clearances.append(p2_inner_radius - p1_outer_radius)

    if max(abs(value - expected_clearance) for value in measured_clearances) > 0.03:
        raise RuntimeError(
            "P1/P2 cylindrical fit does not span the complete tube-joint overlap"
        )
    by_part["tube2"]["tube_joint_cylindrical_engagement_mm"] = overlap
    by_part["tube2"]["tube_joint_max_measured_radial_clearance_mm"] = max(
        measured_clearances
    )

    if "mouthpiece" in by_part:
        mouthpiece = trimesh.load(
            output_dir / PARTS["mouthpiece"][1], force="mesh"
        )
        mouthpiece_overlap = float(connector["mouthpiece_overlap_mm"])
        mouthpiece_length = float(parts["mouthpiece"]["length_mm"])
        expected_interference = float(
            connector["mouthpiece_radial_interference_mm"]
        )
        mouthpiece_fit = []
        for fraction in np.linspace(0.1, 0.9, 9):
            insertion = mouthpiece_overlap * float(fraction)
            mouth_section = mouthpiece.section(
                plane_origin=[0, 0, mouthpiece_length + insertion],
                plane_normal=[0, 0, 1],
            )
            tube1_section = tube1.section(
                plane_origin=[0, 0, insertion],
                plane_normal=[0, 0, 1],
            )
            if mouth_section is None or tube1_section is None:
                raise RuntimeError("mouthpiece fit section is missing from an export")
            mouth_inner_radius = float(
                np.min(np.linalg.norm(mouth_section.vertices[:, :2], axis=1))
            )
            tube1_outer_radius = float(
                np.max(np.linalg.norm(tube1_section.vertices[:, :2], axis=1))
            )
            mouthpiece_fit.append(tube1_outer_radius - mouth_inner_radius)
        if max(
            abs(value - expected_interference) for value in mouthpiece_fit
        ) > 0.03:
            raise RuntimeError(
                "mouthpiece interference does not span the complete overlap"
            )
        by_part["mouthpiece"]["cylindrical_engagement_mm"] = mouthpiece_overlap
        by_part["mouthpiece"]["max_measured_radial_interference_mm"] = max(
            mouthpiece_fit
        )

        transition = float(connector["tube_joint_tip_transition_mm"])
        tip_errors = []
        for fraction in np.linspace(0.1, 0.9, 9):
            distance = transition * float(fraction)
            mouth_section = mouthpiece.section(
                plane_origin=[0, 0, float(mouthpiece.bounds[1][2]) - distance],
                plane_normal=[0, 0, 1],
            )
            tube2_section = tube2.section(
                plane_origin=[0, 0, float(tube2.bounds[0][2]) + distance],
                plane_normal=[0, 0, 1],
            )
            if mouth_section is None or tube2_section is None:
                raise RuntimeError("connector-tip transition is missing from an export")
            mouth_radii = np.linalg.norm(mouth_section.vertices[:, :2], axis=1)
            tube2_radii = np.linalg.norm(tube2_section.vertices[:, :2], axis=1)
            tip_errors.extend(
                [
                    abs(float(np.min(mouth_radii)) - float(np.min(tube2_radii))),
                    abs(float(np.max(mouth_radii)) - float(np.max(tube2_radii))),
                ]
            )
        if max(tip_errors) > 0.03:
            raise RuntimeError("P2 connector tip does not match the mouthpiece transition")
        by_part["tube2"]["mouthpiece_matching_tip_transition_mm"] = transition
        by_part["tube2"]["tip_transition_max_profile_error_mm"] = max(tip_errors)


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

    validate_tube_joint_owner(results, generated_manifest, args.output_dir)

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
