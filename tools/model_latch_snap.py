#!/usr/bin/env python3
"""Reduced-order actuation model for the simple integral latch tongue."""

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

MATERIALS = {
    "pla": Material("PLA", 2800.0, 0.020),
    "petg": Material("PETG", 1700.0, 0.035),
    "abs": Material("ABS", 1800.0, 0.030),
    "nylon": Material("Nylon", 900.0, 0.060),
}

def scalar(name: str) -> float:
    source = SCAD.read_text(encoding="utf-8")
    match = re.search(rf"^\s*{re.escape(name)}\s*=\s*([-+]?\d+(?:\.\d+)?)\s*;", source, re.M)
    if not match:
        raise ValueError(f"missing numeric OpenSCAD parameter: {name}")
    return float(match.group(1))

def geometry() -> dict[str, float]:
    return {
        "protrusion": scalar("latch_nub_protrusion"),
        "indent": scalar("latch_indent_depth"),
        "length": scalar("latch_tongue_flex_l"),
        "thickness": scalar("latch_tongue_t"),
        "width": scalar("latch_tongue_w"),
        "count": scalar("latch_point_count"),
    }

def evaluate(m: Material, g: dict[str, float]) -> dict[str, float]:
    deflection = g["protrusion"] - g["indent"]
    strain = 1.5 * g["thickness"] * deflection / g["length"] ** 2
    force_low = (m.modulus_mpa * g["width"] * g["thickness"] ** 3
                 * deflection / (4 * g["length"] ** 3))
    return {"opening": deflection, "strain": strain, "force_low": force_low,
            "force_high": 2 * force_low, "total_low": g["count"] * force_low,
            "total_high": g["count"] * 2 * force_low,
            "margin": m.allowable_strain / strain}

def pct(v: float) -> str:
    return f"{100*v:.2f}%"

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--material", choices=[*MATERIALS, "all"], default="abs")
    args = p.parse_args()
    g = geometry()
    if g["protrusion"] <= g["indent"]:
        raise SystemExit("nub has no positive retaining interference")
    print("AgnuQuena simple latch-tongue deformation model")
    print(f"geometry: nub projection {g['protrusion']:.2f} mm, recess {g['indent']:.2f} mm, "
          f"tongue {g['width']:.2f} x {g['thickness']:.2f} x {g['length']:.2f} mm")
    print("actuation: pull the single lid tongue outward until its nub clears the recess")
    print("material  allowable  travel  strain  force/point  worst all-three  margin")
    keys = MATERIALS if args.material == "all" else [args.material]
    for key in keys:
        m = MATERIALS[key]
        r = evaluate(m, g)
        print(f"{m.name:<9} {pct(m.allowable_strain):>9}  {r['opening']:>7.3f} mm  "
              f"{pct(r['strain']):>8}  "
              f"{r['force_low']:.1f}-{r['force_high']:.1f} N  "
              f"{r['total_low']:.1f}-{r['total_high']:.1f} N  {r['margin']:.2f}x")
    print("limits: rectangular cantilever, linear elasticity, ideal layers, no friction/creep")

if __name__ == "__main__":
    main()
