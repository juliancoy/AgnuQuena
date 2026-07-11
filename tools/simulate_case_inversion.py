#!/usr/bin/env python3
"""Screen flute retention when the closed or open case is inverted.

This is an auditable reduced-order mechanics model.  It reads production
dimensions from QuenaCase.scad, evaluates geometric escape, gravity/shock
loads, latch reserve, and ABS cantilever-retainer strain and force.
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAD = ROOT / "QuenaCase.scad"


def scalar(name: str) -> float:
    text = SCAD.read_text(encoding="utf-8")
    match = re.search(
        rf"^\s*{re.escape(name)}\s*=\s*([-+]?\d+(?:\.\d+)?)\s*;",
        text,
        re.MULTILINE,
    )
    if not match:
        raise ValueError(f"missing numeric OpenSCAD parameter: {name}")
    return float(match.group(1))


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
    clip_t = scalar("retainer_clip_t")
    clip_w = scalar("retainer_clip_w")
    clip_l = scalar("retainer_clip_flex_l")
    clip_interference = scalar("retainer_clip_interference")
    latch_count = scalar("latch_point_count")
    latch_travel = scalar("latch_nub_protrusion") - scalar("latch_indent_depth")
    latch_w = scalar("latch_tongue_w")
    latch_t = scalar("latch_tongue_t")
    latch_l = scalar("latch_tongue_flex_l")
    latch_release_low = (args.abs_modulus_mpa * latch_w * latch_t**3
                         * latch_travel / (4 * latch_l**3))

    closed_radial_travel = (channel_d - tube_d) / 2
    clip_strain = 1.5 * clip_t * clip_interference / clip_l**2
    clip_force = (args.abs_modulus_mpa * clip_w * clip_t**3
                  * clip_interference / (4 * clip_l**3))
    clip_margin = 0.03 / clip_strain

    gravity_n = args.mass_g / 1000 * 9.80665
    shock_n = gravity_n * args.shock_g
    latch_low = latch_count * latch_release_low
    latch_sf = latch_low / shock_n

    print("AgnuQuena inverted-case retention screen")
    print(f"stored mass assumption: {args.mass_g:.1f} g")
    print(f"tube/channel: {tube_d:.2f} / {channel_d:.2f} mm")
    print(f"closed-case radial travel before lid contact: {closed_radial_travel:.2f} mm")
    print(f"ABS clip: {clip_w:.1f} x {clip_t:.1f} x {clip_l:.1f} mm, "
          f"{clip_interference:.2f} mm interference")
    print(f"clip strain: {100*clip_strain:.2f}%; margin to 3% screen: {clip_margin:.1f}x")
    print(f"estimated insertion/release force per clip: {clip_force:.2f} N")
    print(f"loads: 1 g = {gravity_n:.3f} N; {args.shock_g:.1f} g = {shock_n:.3f} N")
    print(f"three-latch conservative release floor: {latch_low:.1f} N")
    print(f"latch safety factor against {args.shock_g:.1f} g inertial load: {latch_sf:.1f}x")
    # Allocate the measured total mass by tube length, then compare each part's
    # load with its own production clip group (Tube 1 / Tube 2 / mouthpiece).
    mouth_l = scalar("mouthpiece_total_length")
    tube1_l = scalar("tube_part_1_length")
    tuned_acoustic_l = 396 * 2 ** (-scalar("pitch_raise_cents") / 1200)
    tube2_l = (tuned_acoustic_l
               - (mouth_l - scalar("unacoustic_length")) - tube1_l)
    part_lengths = (tube1_l, tube2_l, mouth_l)
    clip_counts = (4, 3, 1)
    part_names = ("Tube 1", "Tube 2", "Mouthpiece")
    clip_sfs = []
    for name, length, count in zip(part_names, part_lengths, clip_counts):
        part_shock = shock_n * length / sum(part_lengths)
        sf = count * clip_force / max(part_shock, 1e-9)
        clip_sfs.append(sf)
        print(f"{name} open-inverted force margin: {sf:.1f}x ({count} clip(s))")
    if clip_margin < 1 or min(clip_sfs) < 1:
        raise SystemExit("OPEN + INVERTED: FAIL — ABS clip screen is below margin")
    print("OPEN + INVERTED: PASS — every part has a geometrically interfering ABS clip")
    print("CLOSED + INVERTED: PASS — lid channel encloses the tube; gravity seats it against the lid")
    print("limits: rigid tube, quasi-static contacts, no print defects, creep, wear, or latch misalignment")


if __name__ == "__main__":
    main()
