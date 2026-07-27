#!/usr/bin/env python3
"""Screen flute retention when the closed or open case is inverted.

This is an auditable reduced-order mechanics model.  It reads production
dimensions from QuenaCase.scad, evaluates geometric escape, gravity/shock
loads, latch reserve, and the fitted closed-case envelope.
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAD = ROOT / "QuenaCase.scad"


def scalar(name: str) -> float:
    for source_path in (SCAD, ROOT / "generated" / "quena_parameters.scad"):
        text = source_path.read_text(encoding="utf-8")
        match = re.search(
            rf"^\s*{re.escape(name)}\s*=\s*([-+]?\d+(?:\.\d+)?)\s*;",
            text,
            re.MULTILINE,
        )
        if match:
            return float(match.group(1))
    raise ValueError(f"missing numeric OpenSCAD parameter: {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mass-g", type=float, default=42.0,
                        help="total stored flute-part mass (default: 42 g)")
    parser.add_argument("--shock-g", type=float, default=10.0,
                        help="inverted shock load factor (default: 10 g)")
    parser.add_argument("--abs-modulus-mpa", type=float, default=1800.0)
    args = parser.parse_args()

    tube_d = scalar("id") + 2 * scalar("shell_width")
    channel_d = tube_d + 2 * scalar("part_clearance")
    equator_pass = scalar("equator_pass")
    axial_clearance = scalar("axial_clearance")
    latch_count = scalar("latch_point_count")
    latch_travel = scalar("latch_nub_protrusion") - scalar("latch_indent_depth")
    latch_w = scalar("latch_tongue_w")
    latch_t = scalar("latch_tongue_t")
    latch_l = scalar("latch_tongue_flex_l")
    latch_release_low = (args.abs_modulus_mpa * latch_w * latch_t**3
                         * latch_travel / (4 * latch_l**3))

    closed_radial_travel = (channel_d - tube_d) / 2
    gravity_n = args.mass_g / 1000 * 9.80665
    shock_n = gravity_n * args.shock_g
    latch_low = latch_count * latch_release_low
    latch_sf = latch_low / shock_n

    print("AgnuQuena inverted-case retention screen")
    print(f"stored mass assumption: {args.mass_g:.1f} g")
    print(f"tube/channel: {tube_d:.2f} / {channel_d:.2f} mm")
    print(f"closed-case radial travel before lid contact: {closed_radial_travel:.2f} mm")
    print(f"bottom support height: {equator_pass:.2f} mm past tube equator")
    print(f"total axial end play: {axial_clearance:.2f} mm")
    print(f"loads: 1 g = {gravity_n:.3f} N; {args.shock_g:.1f} g = {shock_n:.3f} N")
    print(f"three-latch conservative release floor: {latch_low:.1f} N")
    print(f"latch safety factor against {args.shock_g:.1f} g inertial load: {latch_sf:.1f}x")
    if closed_radial_travel > 0.4 or axial_clearance > 1.0 or equator_pass <= 0:
        raise SystemExit("CLOSED + INVERTED: FAIL — fitted envelope is too loose")
    if latch_sf < 1:
        raise SystemExit("CLOSED + INVERTED: FAIL — latch reserve is below shock load")
    print("OPEN + INVERTED: not retained — intentional easy-lift cradle")
    print("CLOSED + INVERTED: PASS — matching channels enclose each part snugly")
    print("limits: rigid tube, quasi-static contacts, no print defects, creep, wear, or latch misalignment")


if __name__ == "__main__":
    main()
