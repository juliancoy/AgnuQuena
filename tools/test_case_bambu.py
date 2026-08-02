#!/usr/bin/env python3
"""Slice the two-colour case with the project-local BambuStudio CLI."""

from __future__ import annotations

import json
import math
import re
import subprocess
import tempfile
from pathlib import Path

from bambu_studio import BINARY, command, environment


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "QuenaCase.3mf"


def installed() -> bool:
    return BINARY.is_file() and BINARY.stat().st_mode & 0o111 != 0


def require_header(gcode: str, setting: str, value: str) -> None:
    pattern = rf"^; {re.escape(setting)}\s*(?:=|:)\s*{re.escape(value)}$"
    if not re.search(pattern, gcode, re.MULTILINE):
        raise AssertionError(f"Bambu G-code has {setting!r} set incorrectly")


def main() -> None:
    if not installed():
        print("QuenaCase Bambu slice: skipped, project-local BambuStudio is not built")
        return
    with tempfile.TemporaryDirectory(prefix=".bambu_case_slice_", dir=ROOT) as temp_dir:
        output = Path(temp_dir)
        completed = subprocess.run(
            command(
                "--debug",
                "1",
                "--slice",
                "0",
                "--outputdir",
                output,
                PROJECT,
            ),
            cwd=output,
            env=environment(),
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError(
                "Bambu Studio could not slice the project:\n"
                f"{completed.stdout}{completed.stderr}"
            )
        result = json.loads((output / "result.json").read_text(encoding="utf-8"))
        gcode = (output / "plate_1.gcode").read_text(encoding="utf-8")

    if result.get("return_code") != 0 or result.get("error_string") != "Success.":
        raise AssertionError(f"Bambu Studio slice failed: {result}")
    plate = result["sliced_plates"][0]
    filament_ids = [item["id"] for item in plate["filaments"]]
    if filament_ids != [1, 2] or plate.get("filament_change_times") != 3:
        raise AssertionError(
            "Bambu slice does not use both AMS filaments as expected: "
            f"ids={filament_ids}, changes={plate.get('filament_change_times')}"
        )
    if result.get("wall_loops") != 3 or not math.isclose(
        float(result.get("sparse_infill_density", -1)), 10.0, abs_tol=0.01
    ):
        raise AssertionError("Bambu slice did not retain the case strength profile")
    bbox = plate["objects"][0]["bbox"]
    expected_bbox = {
        "x": 5.003,
        "y": 70.787,
        "z": 0.0,
        "width": 245.994,
        "depth": 113.948,
        "height": 19.3,
    }
    for key, expected in expected_bbox.items():
        if not math.isclose(float(bbox[key]), expected, abs_tol=0.02):
            raise AssertionError(f"Bambu plate {key} differs from the validated pose")

    require_header(gcode, "filament", "1,2")
    require_header(gcode, "filament_colour", "#FFF144;#000000")
    require_header(gcode, "filament_type", "ABS;ABS")
    require_header(gcode, "enable_support", "0")
    require_header(gcode, "brim_type", "no_brim")
    require_header(gcode, "brim_width", "0")
    require_header(gcode, "skirt_loops", "0")
    require_header(gcode, "prime_tower_width", "20")
    require_header(gcode, "prime_tower_brim_width", "1")
    require_header(gcode, "wipe_tower_no_sparse_layers", "1")
    if re.search(r"^; FEATURE: .*Support", gcode, re.MULTILINE | re.IGNORECASE):
        raise AssertionError("Bambu generated support toolpaths for the support-free case")

    layer_four = gcode.index("; Z_HEIGHT: 0.8")
    layer_totals = {
        int(match.group(1))
        for match in re.finditer(
            r"^; layer num/total_layer_count: \d+/(\d+)$", gcode, re.MULTILINE
        )
    }
    if layer_totals != {96}:
        raise AssertionError(f"Bambu produced unexpected layer counts: {layer_totals}")
    black_tool_changes = [match.start() for match in re.finditer(r"^T1$", gcode, re.MULTILINE)]
    if len(black_tool_changes) != 1 or max(black_tool_changes) >= layer_four:
        raise AssertionError("black artwork is not confined to the first three layers")
    if any(match.start() > layer_four for match in re.finditer(r"^M620 S1A", gcode, re.MULTILINE)):
        raise AssertionError("Bambu requests black filament above the artwork layers")

    current_z = 0.0
    prime_tower_z: list[float] = []
    for line in gcode.splitlines():
        if match := re.match(r"; Z_HEIGHT: ([0-9.]+)", line):
            current_z = float(match.group(1))
        if re.match(r"; FEATURE: .*Prime tower", line, re.IGNORECASE):
            prime_tower_z.append(current_z)
    if not prime_tower_z or max(prime_tower_z) > 0.6 + 1e-6:
        raise AssertionError(
            f"prime tower extends beyond the colour layers: {prime_tower_z}"
        )

    print(
        "QuenaCase Bambu slice: ok, P1S plate, 96 layers, 2 ABS filaments, "
        "3 changes, black logo/mandala/flourish inlays, 20 mm tower ending at Z=0.6, "
        "no supports/brim/skirt"
    )


if __name__ == "__main__":
    main()
