#!/usr/bin/env python3
"""Reduced-order bending screen for circular and oval quena tone holes.

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

import numpy as np


@dataclass(frozen=True)
class Hole:
    note: str
    z_mm: float
    diameter_mm: float


ID_MM = 17.5
OD_MM = 20.5
LENGTH_MM = 369.265
HOLES = (
    Hole("A", 306.6445, 10.10),
    Hole("B", 268.6588, 10.35),
    Hole("C", 245.3211, 9.75),
    Hole("D", 211.8042, 11.10),
    Hole("E", 180.6708, 11.10),
    Hole("F#", 152.9138, 11.13),
)


def section_properties(z_mm: float, axial_scale: float, grid_mm: float) -> tuple[float, float, float]:
    """Return area and section moduli for bending toward/away from the holes."""
    radius = OD_MM / 2
    coords = np.arange(-radius, radius + grid_mm / 2, grid_mm)
    x, y = np.meshgrid(coords, coords, indexing="xy")
    solid = (x * x + y * y <= radius * radius) & (x * x + y * y >= (ID_MM / 2) ** 2)

    # Holes are radial on the +X face. Their equal-area oval lies in Y-Z:
    # axial semi-axis a and circumferential semi-axis b.
    for hole in HOLES:
        a = hole.diameter_mm * axial_scale / 2
        b = hole.diameter_mm / axial_scale / 2
        if abs(z_mm - hole.z_mm) <= a:
            y_limit = b * math.sqrt(max(0.0, 1 - ((z_mm - hole.z_mm) / a) ** 2))
            solid &= ~((x >= 0) & (np.abs(y) <= y_limit))

    pixel_area = grid_mm * grid_mm
    xs = x[solid]
    area = xs.size * pixel_area
    centroid_x = float(xs.mean())
    iy = float(np.sum((xs - centroid_x) ** 2) * pixel_area)
    c_positive = radius - centroid_x
    c_negative = radius + centroid_x
    return area, iy / c_positive, iy / c_negative


def analyze(axial_scale: float, load_n: float, grid_mm: float, dz_mm: float) -> dict[str, object]:
    zs = np.arange(0, LENGTH_MM + dz_mm / 2, dz_mm)
    # Simply supported beam with a center point load (three-point bending).
    reactions = load_n / 2
    moments = reactions * np.minimum(zs, LENGTH_MM - zs)
    rows = []
    for z, moment in zip(zs, moments):
        area, section_modulus_positive, section_modulus_negative = section_properties(z, axial_scale, grid_mm)
        # Report the worse face because the direction of an accidental bend is unknown.
        stress = moment / min(section_modulus_positive, section_modulus_negative)
        rows.append((stress, z, moment, area, section_modulus_positive, section_modulus_negative))
    stress, z, moment, area, s_pos, s_neg = max(rows)
    nearest = min(HOLES, key=lambda h: abs(h.z_mm - z))
    return {
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
    # The long axis follows the flute.  Narrowing the opening circumferentially
    # preserves more material at the extreme bending fibers; reciprocal scaling
    # keeps the nominal opening area unchanged.
    oval = analyze(1.25, args.load_n, args.grid_mm, args.dz_mm)
    result = {
        "model": "simply_supported_three_point_bending",
        "limitations": "linear beam section screen; excludes 3D notch stress, print anisotropy, impact, connectors, and crack growth",
        "circular": circular,
        "oval": oval,
        "oval_to_circular_peak_stress_ratio": oval["peak_stress_mpa"] / circular["peak_stress_mpa"],
        "estimated_strength_gain_percent": (circular["peak_stress_mpa"] / oval["peak_stress_mpa"] - 1) * 100,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
