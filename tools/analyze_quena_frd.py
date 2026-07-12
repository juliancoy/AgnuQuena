#!/usr/bin/env python3
"""Find first ABS bulk or inter-layer failure in CalculiX FRD increments."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np

from build_quena_fea import read_msh


FLOAT_RE = re.compile(r"[-+]?\d\.\d{5}E[-+]\d{2}")
HOLES = {"F#": 152.9138, "E": 180.6708, "D": 211.8042, "C": 245.3211, "B": 268.6588, "A": 306.6445}


def interpolate_crossing(rows: list[dict[str, float]], key: str, threshold: float, load_n: float) -> float | None:
    previous_time, previous_value = 0.0, 0.0
    for row in rows:
        value = row[key]
        if value >= threshold:
            fraction = (threshold - previous_value) / (value - previous_value)
            return load_n * (previous_time + fraction * (row["time"] - previous_time))
        previous_time, previous_value = row["time"], value
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frd", type=Path, default=Path("analysis/quena_abs_bend.frd"))
    parser.add_argument("--mesh", type=Path, default=Path("analysis/quena_structural.msh"))
    parser.add_argument("--metadata", type=Path, default=Path("analysis/quena_abs_bend.json"))
    args = parser.parse_args()
    nodes, _elements = read_msh(args.mesh)
    metadata = json.loads(args.metadata.read_text())
    load_n = metadata["load_n"]
    interlayer_limit = metadata["abs"]["interlayer_tensile_strength_mpa"]
    bulk_limit = metadata["abs"]["bulk_tensile_strength_mpa"]

    lines = args.frd.read_text(errors="replace").splitlines()
    time = 0.0
    rows: list[dict[str, float]] = []
    displacements: dict[float, dict[str, float]] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("  100CL"):
            values = FLOAT_RE.findall(line)
            if values:
                time = float(values[0])
        if line.startswith(" -4  DISP"):
            max_magnitude = 0.0
            load_ux: list[float] = []
            i += 5  # skip the four component descriptor lines
            while i < len(lines) and not lines[i].startswith(" -3"):
                data = lines[i]
                if data.startswith(" -1"):
                    node = int(data[3:13])
                    values = [float(v) for v in FLOAT_RE.findall(data[13:])]
                    if len(values) >= 3:
                        magnitude = float(np.linalg.norm(values[:3]))
                        max_magnitude = max(max_magnitude, magnitude)
                        x, _y, z = nodes[node]
                        if abs(z - 369.265 / 2) <= 1.2 and x > 7.0:
                            load_ux.append(values[0])
                i += 1
            if load_ux:
                displacements[time] = {"load_point_displacement_mm": float(np.mean(load_ux)),
                    "maximum_displacement_mm": max_magnitude}
        if line.startswith(" -4  STRESS"):
            max_szz = (-1e99, 0)
            max_principal = (-1e99, 0)
            i += 7  # skip the six component descriptor lines
            while i < len(lines) and not lines[i].startswith(" -3"):
                data = lines[i]
                if data.startswith(" -1"):
                    node = int(data[3:13])
                    xyz = nodes.get(node)
                    values = [float(v) for v in FLOAT_RE.findall(data[13:])]
                    if xyz and len(values) == 6 and 135.0 <= xyz[2] <= 320.0:
                        sxx, syy, szz, sxy, syz, szx = values
                        principal = float(np.linalg.eigvalsh([[sxx, sxy, szx], [sxy, syy, syz], [szx, syz, szz]])[-1])
                        if szz > max_szz[0]:
                            max_szz = (szz, node)
                        if principal > max_principal[0]:
                            max_principal = (principal, node)
                i += 1
            if max_szz[1]:
                z = nodes[max_szz[1]][2]
                nearest = min(HOLES, key=lambda note: abs(HOLES[note] - z))
                rows.append({"time": time, "load_n": time * load_n,
                    "max_axial_tension_mpa": max_szz[0], "max_principal_tension_mpa": max_principal[0],
                    "critical_node": max_szz[1], "critical_z_mm": z, "nearest_hole": nearest})
        i += 1
    if not rows:
        raise SystemExit("no complete stress increments found")
    for row in rows:
        row.update(displacements.get(row["time"], {}))

    interlayer_load = interpolate_crossing(rows, "max_axial_tension_mpa", interlayer_limit, load_n)
    bulk_load = interpolate_crossing(rows, "max_principal_tension_mpa", bulk_limit, load_n)
    failure_loads = [("interlayer", interlayer_load), ("bulk", bulk_load)]
    available = [(mode, load) for mode, load in failure_loads if load is not None]
    mode, first_load = min(available, key=lambda item: item[1]) if available else ("not_reached", None)
    failure_row = next((row for row in rows if first_load is not None and row["load_n"] >= first_load), rows[-1])
    failure_displacement = None
    if first_load is not None:
        prior = {"load_n": 0.0, "load_point_displacement_mm": 0.0}
        for row in rows:
            if row["load_n"] >= first_load and "load_point_displacement_mm" in row:
                fraction = (first_load - prior["load_n"]) / (row["load_n"] - prior["load_n"])
                failure_displacement = prior["load_point_displacement_mm"] + fraction * (
                    row["load_point_displacement_mm"] - prior["load_point_displacement_mm"])
                break
            if "load_point_displacement_mm" in row:
                prior = row
    result = {"completed_increments": len(rows), "last_completed_load_n": rows[-1]["load_n"],
        "first_failure_mode": mode, "predicted_first_failure_load_n": first_load,
        "predicted_load_point_displacement_at_failure_mm": failure_displacement,
        "interlayer_failure_load_n": interlayer_load, "bulk_failure_load_n": bulk_load,
        "failure_location": {"node": failure_row["critical_node"], "z_mm": failure_row["critical_z_mm"],
        "nearest_hole": failure_row["nearest_hole"]}, "failure_limits_mpa": {
        "interlayer_axial": interlayer_limit, "bulk_principal": bulk_limit}, "increments": rows}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
