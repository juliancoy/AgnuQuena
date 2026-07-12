#!/usr/bin/env python3
"""Convert the Gmsh quena mesh to a CalculiX ABS three-point bend model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def adhesion_factor(args: argparse.Namespace) -> tuple[float, dict[str, float]]:
    """Transparent engineering heuristic for FDM ABS inter-layer strength.

    The penalties are deliberately capped because these process inputs are not
    a substitute for tensile coupons printed on the actual machine.
    """
    penalties = {
        "ambient_humidity": min(0.18, max(0.0, args.humidity_pct - 40.0) * 0.003),
        "cool_enclosure": min(0.25, max(0.0, 40.0 - args.enclosure_c) * 0.008),
        "part_cooling_fan": min(0.25, max(0.0, args.fan_pct) * 0.003),
        "low_nozzle_temperature": min(0.25, max(0.0, 240.0 - args.nozzle_c) * 0.006),
        "thick_layers": min(0.15, max(0.0, args.layer_height_mm / args.nozzle_mm - 0.5) * 0.30),
        "surface_contamination": 0.15 if args.contaminated else 0.0,
    }
    return max(0.40, 1.0 - sum(penalties.values())), penalties


def read_msh(path: Path) -> tuple[dict[int, tuple[float, float, float]], list[tuple[int, list[int]]]]:
    lines = path.read_text().splitlines()
    nodes: dict[int, tuple[float, float, float]] = {}
    elements: list[tuple[int, list[int]]] = []
    i = 0
    while i < len(lines):
        if lines[i] == "$Nodes":
            count = int(lines[i + 1])
            for line in lines[i + 2 : i + 2 + count]:
                fields = line.split()
                nodes[int(fields[0])] = tuple(map(float, fields[1:4]))
            i += count + 2
        elif lines[i] == "$Elements":
            count = int(lines[i + 1])
            for line in lines[i + 2 : i + 2 + count]:
                fields = list(map(int, line.split()))
                element_id, element_type, tag_count = fields[:3]
                connectivity = fields[3 + tag_count :]
                if element_type == 4:  # four-node tetrahedron
                    elements.append((element_id, connectivity))
            i += count + 2
        i += 1
    if not nodes or not elements:
        raise ValueError("mesh has no tetrahedral volume")
    return nodes, elements


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=Path, default=Path("analysis/quena_structural.msh"))
    parser.add_argument("--output", type=Path, default=Path("analysis/quena_abs_bend.inp"))
    parser.add_argument("--load-n", type=float, default=60.0)
    parser.add_argument("--humidity-pct", type=float, default=50.0)
    parser.add_argument("--enclosure-c", type=float, default=45.0)
    parser.add_argument("--fan-pct", type=float, default=0.0)
    parser.add_argument("--nozzle-c", type=float, default=245.0)
    parser.add_argument("--layer-height-mm", type=float, default=0.20)
    parser.add_argument("--nozzle-mm", type=float, default=0.40)
    parser.add_argument("--contaminated", action="store_true")
    args = parser.parse_args()

    nodes, elements = read_msh(args.mesh)
    zs = [xyz[2] for xyz in nodes.values()]
    z_min, z_max = min(zs), max(zs)
    mid = (z_min + z_max) / 2
    # Contact patches approximately 2.4 mm axially by 90 degrees around tube.
    left = [n for n, (x, _y, z) in nodes.items() if z <= z_min + 1.2 and x < -7.0]
    right = [n for n, (x, _y, z) in nodes.items() if z >= z_max - 1.2 and x < -7.0]
    load = [n for n, (x, _y, z) in nodes.items() if abs(z - mid) <= 1.2 and x > 7.0]
    if min(map(len, (left, right, load))) == 0:
        raise ValueError("failed to identify fixture contact nodes")

    # Stabilizers remove rigid-body Y/Z motion without over-constraining bending.
    left_anchor = min(left, key=lambda n: abs(nodes[n][1]))
    right_anchor = min(right, key=lambda n: abs(nodes[n][1]))
    factor, penalties = adhesion_factor(args)
    bulk_tensile_mpa = 38.0
    interlayer_tensile_mpa = bulk_tensile_mpa * factor

    out: list[str] = ["*HEADING", "AgnuQuena ABS three-point bending"]
    out.append("*NODE")
    out.extend(f"{n},{x:.8g},{y:.8g},{z:.8g}" for n, (x, y, z) in nodes.items())
    out.append("*ELEMENT,TYPE=C3D4,ELSET=EALL")
    out.extend(f"{eid}," + ",".join(map(str, conn)) for eid, conn in elements)
    for name, ids in (("LEFT", left), ("RIGHT", right), ("LOAD", load)):
        out.append(f"*NSET,NSET={name}")
        out.extend(",".join(map(str, ids[i : i + 16])) for i in range(0, len(ids), 16))
    out.extend([
        "*NSET,NSET=LEFTANCHOR", str(left_anchor),
        "*NSET,NSET=RIGHTANCHOR", str(right_anchor),
        "*MATERIAL,NAME=ABS",
        "*ELASTIC", "2000.,0.35",
        "*SOLID SECTION,ELSET=EALL,MATERIAL=ABS", "",
        "*BOUNDARY", "LEFT,1,1,0.", "RIGHT,1,1,0.",
        "LEFTANCHOR,2,3,0.", "RIGHTANCHOR,2,2,0.",
        "*STEP,NLGEOM", "*STATIC", "0.02,1.0,1.e-6,0.05",
        "*CLOAD", f"LOAD,1,{args.load_n / len(load):.10g}",
        "*NODE FILE", "U",
        "*EL FILE", "S,E",
        "*END STEP",
    ])
    args.output.write_text("\n".join(out) + "\n")
    metadata = {
        "nodes": len(nodes), "tetrahedra": len(elements),
        "fixture_nodes": {"left": len(left), "right": len(right), "load": len(load)},
        "load_n": args.load_n, "abs": {"elastic_modulus_mpa": 2000.0, "poisson": 0.35,
        "bulk_tensile_strength_mpa": bulk_tensile_mpa,
        "adhesion_factor": factor, "interlayer_tensile_strength_mpa": interlayer_tensile_mpa},
        "adhesion_penalties": penalties,
    }
    args.output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
