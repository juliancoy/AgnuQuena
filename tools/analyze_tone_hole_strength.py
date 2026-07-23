#!/usr/bin/env python3
"""Reduced-order bending screen for circular and rounded-square tone holes.

The tube is treated as a linearly elastic beam.  Each axial cross-section is
integrated on a fine Cartesian grid after subtracting the radial tone-hole cut.
This captures the shifted neutral axis and reduced second moment of area.  It
does not capture 3D notch stress, layer adhesion, connectors, impact, or crack
growth, so the output is comparative rather than a certified failure load.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Hole:
    note: str
    z_mm: float
    diameter_mm: float


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "generated" / "quena_manifest.json"


def generated_geometry() -> tuple[float, float, float, tuple[Hole, ...]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    geometry = manifest["geometry"]
    holes = tuple(
        Hole(
            note=str(hole["name"]),
            z_mm=float(hole["physical_z_mm"]),
            diameter_mm=float(hole["diameter_mm"]),
        )
        for hole in manifest["holes"]
    )
    return (
        float(geometry["bore_id_mm"]),
        float(geometry["outer_diameter_mm"]),
        float(geometry["non_mouthpiece_length_mm"]),
        holes,
    )


ID_MM, OD_MM, LENGTH_MM, HOLES = generated_geometry()


def section_properties(
    z_mm: float,
    axial_scale: float,
    grid_mm: float,
    rounded_square: bool = False,
    corner_ratio: float = 0.28,
) -> tuple[float, float, float]:
    """Return area and section moduli for bending toward/away from the holes."""
    radius = OD_MM / 2
    coords = np.arange(-radius, radius + grid_mm / 2, grid_mm)
    x, y = np.meshgrid(coords, coords, indexing="xy")
    solid = (x * x + y * y <= radius * radius) & (x * x + y * y >= (ID_MM / 2) ** 2)

    # Holes are radial on the +X face and lie in Y-Z. Reciprocal axial and
    # circumferential scaling preserves area. The rounded-square dimensions
    # match Quena.scad's offset-square construction.
    for hole in HOLES:
        dz = abs(z_mm - hole.z_mm)
        if rounded_square:
            side = hole.diameter_mm * math.sqrt(
                (math.pi / 4) / (1 - (4 - math.pi) * corner_ratio**2)
            )
            width = side * axial_scale
            height = side / axial_scale
            rx = side * corner_ratio * axial_scale
            ry = side * corner_ratio / axial_scale
            straight_half_width = width / 2 - rx
            if dz <= width / 2:
                if dz <= straight_half_width:
                    y_limit = height / 2
                else:
                    corner_x = (dz - straight_half_width) / rx
                    y_limit = height / 2 - ry + ry * math.sqrt(max(0.0, 1 - corner_x**2))
                solid &= ~((x >= 0) & (np.abs(y) <= y_limit))
        else:
            hole_radius = hole.diameter_mm / 2
            if dz <= hole_radius:
                y_limit = hole_radius * math.sqrt(max(0.0, 1 - (dz / hole_radius) ** 2))
                solid &= ~((x >= 0) & (np.abs(y) <= y_limit))

    pixel_area = grid_mm * grid_mm
    xs = x[solid]
    area = xs.size * pixel_area
    centroid_x = float(xs.mean())
    iy = float(np.sum((xs - centroid_x) ** 2) * pixel_area)
    c_positive = radius - centroid_x
    c_negative = radius + centroid_x
    return area, iy / c_positive, iy / c_negative


def analyze(
    axial_scale: float,
    load_n: float,
    grid_mm: float,
    dz_mm: float,
    rounded_square: bool = False,
) -> dict[str, object]:
    zs = np.arange(0, LENGTH_MM + dz_mm / 2, dz_mm)
    # Simply supported beam with a center point load (three-point bending).
    reactions = load_n / 2
    moments = reactions * np.minimum(zs, LENGTH_MM - zs)
    rows = []
    for z, moment in zip(zs, moments):
        area, section_modulus_positive, section_modulus_negative = section_properties(
            z, axial_scale, grid_mm, rounded_square
        )
        # Report the worse face because the direction of an accidental bend is unknown.
        stress = moment / min(section_modulus_positive, section_modulus_negative)
        rows.append((stress, z, moment, area, section_modulus_positive, section_modulus_negative))
    stress, z, moment, area, s_pos, s_neg = max(rows)
    nearest = min(HOLES, key=lambda h: abs(h.z_mm - z))
    return {
        "shape": "rounded_square" if rounded_square else "circle",
        "axial_scale": axial_scale,
        "circumferential_scale": 1 / axial_scale,
        "load_n": load_n,
        "peak_stress_mpa": stress,
        "peak_z_mm": z,
        "nearest_hole": nearest.note,
        "nearest_hole_center_z_mm": nearest.z_mm,
        "moment_at_peak_n_mm": moment,
        "net_area_at_peak_mm2": area,
        "section_modulus_positive_mm3": s_pos,
        "section_modulus_negative_mm3": s_neg,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--load-n", type=float, default=10.0, help="center point load")
    parser.add_argument("--grid-mm", type=float, default=0.08)
    parser.add_argument("--dz-mm", type=float, default=0.2)
    args = parser.parse_args()
    circular = analyze(1.0, args.load_n, args.grid_mm, args.dz_mm)
    rounded = analyze(1.25, args.load_n, args.grid_mm, args.dz_mm, rounded_square=True)
    result = {
        "model": "simply_supported_three_point_bending",
        "limitations": "linear beam section screen; excludes 3D notch stress, print anisotropy, impact, connectors, and crack growth",
        "circular": circular,
        "rounded_square": rounded,
        "rounded_square_to_circular_peak_stress_ratio": rounded["peak_stress_mpa"] / circular["peak_stress_mpa"],
        "estimated_strength_gain_percent": (circular["peak_stress_mpa"] / rounded["peak_stress_mpa"] - 1) * 100,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
