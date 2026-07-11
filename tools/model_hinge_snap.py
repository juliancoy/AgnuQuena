#!/usr/bin/env python3
"""Reduced-order deformation model for the AgnuQuena closed-stator hinge.

The outer sockets are uninterrupted blind cylinders. To install the second
short pin, the ABS lid/hinge carrier is bowed enough to shorten its projected
span by the effective pin engagement. The model brackets the carrier between:

* simply supported: compliant lower-bound force and strain;
* constrained: 4x force and 2x surface-strain upper bound.

This is not nonlinear shell/contact FEA; it is an auditable kinematic and beam
screen whose assumptions and dimensions are printed with every result.
"""

from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAD = ROOT / "QuenaCase.scad"


@dataclass(frozen=True)
class Material:
    name: str
    modulus_mpa: float
    allowable_strain: float


# Effective printed-part screening properties, not bulk-resin datasheet values.
# Allowable strain intentionally includes a print-direction/process knockdown.
MATERIALS = {
    "pla": Material("PLA", 2800.0, 0.020),
    "petg": Material("PETG", 1700.0, 0.035),
    "abs": Material("ABS", 1800.0, 0.030),
    "nylon": Material("Nylon", 900.0, 0.060),
}


def scad_scalar(name: str) -> float:
    source = SCAD.read_text(encoding="utf-8")
    match = re.search(
        rf"^\s*{re.escape(name)}\s*=\s*([-+]?\d+(?:\.\d+)?)\s*;",
        source,
        flags=re.MULTILINE,
    )
    if not match:
        raise ValueError(f"missing numeric OpenSCAD parameter: {name}")
    return float(match.group(1))


def geometry() -> dict[str, float]:
    axle_d = scad_scalar("hinge_axle_d")
    socket_d = axle_d + scad_scalar("hinge_socket_clearance")
    outer_d = scad_scalar("hinge_outer_d")
    return {
        "pin_d": axle_d,
        "socket_d": socket_d,
        "outer_d": outer_d,
        "wall": (outer_d - socket_d) / 2,
        "socket_width": scad_scalar("hinge_socket_depth"),
        "pin_length": scad_scalar("hinge_nub_l"),
        "tip_length": scad_scalar("hinge_pin_tip_l"),
        "knuckle_gap": scad_scalar("hinge_gap"),
        "flex_span": scad_scalar("hinge_install_flex_span"),
        "flex_thickness": scad_scalar("hinge_tab_t"),
        "stator_closed": scad_scalar("hinge_stator_closed"),
    }


def evaluate(material: Material, g: dict[str, float]) -> dict[str, float]:
    e = material.modulus_mpa
    span = g["flex_span"]
    shortening = g["pin_length"] - g["knuckle_gap"]
    bow = math.sqrt(4 * span * shortening) / math.pi
    thickness = g["flex_thickness"]
    width = g["outer_d"]
    inertia = width * thickness**3 / 12

    force_low = 48 * e * inertia * bow / span**3
    force_high = 4 * force_low
    strain_low = thickness * math.pi**2 * bow / (2 * span**2)
    strain_high = 2 * strain_low
    governing_strain = strain_high

    return {
        "shortening": shortening,
        "bow": bow,
        "force_low": force_low,
        "force_high": force_high,
        "strain_low": strain_low,
        "strain_high": strain_high,
        "governing_strain": governing_strain,
        "strain_margin": material.allowable_strain / governing_strain,
    }


def percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--material",
        choices=[*MATERIALS, "all"],
        default="abs",
        help="printed material assumption (default: all)",
    )
    parser.add_argument("--modulus-mpa", type=float, help="override elastic modulus")
    parser.add_argument(
        "--allowable-strain",
        type=float,
        help="override allowable engineering strain as a fraction, e.g. 0.03",
    )
    args = parser.parse_args()

    g = geometry()
    if g["stator_closed"] != 1:
        raise SystemExit("model requires an uninterrupted outer stator")
    if g["pin_length"] <= g["knuckle_gap"]:
        raise SystemExit("pin has no positive engagement; no installation flex required")

    keys = list(MATERIALS) if args.material == "all" else [args.material]
    print("AgnuQuena hinge snap deformation model")
    print(
        "geometry: "
        f"pin {g['pin_d']:.2f} x {g['pin_length']:.2f} mm, "
        f"socket {g['socket_d']:.2f} x {g['socket_width']:.2f} mm, "
        f"wall {g['wall']:.3f} mm, uninterrupted stator"
    )
    print(
        "installation mode: insert one pin, bow the ABS carrier, insert second pin"
    )
    print(
        "material  E(MPa)  allowable  shortening  center bow  "
        "carrier strain  insertion force  margin"
    )
    for key in keys:
        base = MATERIALS[key]
        material = Material(
            base.name,
            args.modulus_mpa if args.modulus_mpa is not None else base.modulus_mpa,
            args.allowable_strain
            if args.allowable_strain is not None
            else base.allowable_strain,
        )
        r = evaluate(material, g)
        print(
            f"{material.name:<9} {material.modulus_mpa:>6.0f}  "
            f"{percent(material.allowable_strain):>9}  "
            f"{r['shortening']:>7.2f} mm  {r['bow']:>6.2f} mm  "
            f"{percent(r['strain_low']):>6}-{percent(r['strain_high']):<6}  "
            f"{r['force_low']:>5.1f}-{r['force_high']:<5.1f} N  "
            f"{r['strain_margin']:.2f}x"
        )

    print("limits: sinusoidal bow, linear beam stiffness, ideal layer bonding, no creep")
    print("use: screen geometry and compare variants; calibrate force with a coupon print")


if __name__ == "__main__":
    main()
