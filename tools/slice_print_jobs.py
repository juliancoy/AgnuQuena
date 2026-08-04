#!/usr/bin/env python3
"""Regenerate, slice, validate, and retain all AgnuQuena P1S print jobs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import trimesh

from bambu_studio import command, environment, require, version


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "bambu-slice-output"


@dataclass(frozen=True)
class PrintJob:
    name: str
    project: Path
    geometry: Path
    gcode_name: str
    expected_objects: tuple[str, ...]
    wall_loops: int
    infill_percent: float
    expected_filaments: tuple[int, ...]
    multi_material: bool
    expected_filament_changes: int


JOBS = (
    PrintJob(
        "Quena",
        ROOT / "Quena.3mf",
        ROOT / "Quena.stl",
        "Quena.gcode",
        ("Quena.stl",),
        6,
        25.0,
        (1,),
        False,
        0,
    ),
    PrintJob(
        "QuenaCase",
        ROOT / "QuenaCase.3mf",
        ROOT / "QuenaCaseTwoColorPrintInPlace.stl",
        "QuenaCase.gcode",
        ("Assembly",),
        3,
        10.0,
        (1, 2),
        True,
        1,
    ),
    PrintJob(
        "QuenaCaseSingleFilament",
        ROOT / "QuenaCaseSingleFilament.3mf",
        ROOT / "QuenaCasePrintInPlace.stl",
        "QuenaCaseSingleFilament.gcode",
        ("Assembly",),
        3,
        10.0,
        (1,),
        False,
        0,
    ),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_python(script: str) -> None:
    command = [sys.executable, script]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def require_bambu_studio() -> str:
    require()
    return version()


def header_value(gcode: str, key: str) -> str:
    match = re.search(rf"^; {re.escape(key)}\s*(?:=|:)\s*(.+)$", gcode, re.MULTILINE)
    if not match:
        raise RuntimeError(f"sliced G-code is missing {key!r}")
    return match.group(1).strip()


def validate_slice(job: PrintJob, result: dict[str, object], gcode: str) -> dict[str, object]:
    if result.get("return_code") != 0 or result.get("error_string") != "Success.":
        raise RuntimeError(f"{job.name}: Bambu Studio reported a failed slice: {result}")
    plates = result.get("sliced_plates")
    if not isinstance(plates, list) or len(plates) != 1:
        raise RuntimeError(f"{job.name}: expected exactly one sliced plate")
    plate = plates[0]
    objects = tuple(item["name"] for item in plate["objects"])
    if objects != job.expected_objects:
        raise RuntimeError(f"{job.name}: unexpected sliced objects {objects}")
    bbox = plate["objects"][0]["bbox"]
    source_mesh = trimesh.load(job.geometry, force="mesh")
    if not source_mesh.is_watertight:
        raise RuntimeError(f"{job.name}: source geometry is not watertight")
    expected_height_mm = float(source_mesh.extents[2])
    if abs(float(bbox["height"]) - expected_height_mm) > 0.05:
        raise RuntimeError(f"{job.name}: unexpected sliced height {bbox['height']} mm")
    if float(bbox["x"]) < 0 or float(bbox["y"]) < 0:
        raise RuntimeError(f"{job.name}: sliced job extends below the build-plate origin")
    if float(bbox["x"]) + float(bbox["width"]) > 256.01 or float(bbox["y"]) + float(
        bbox["depth"]
    ) > 256.01:
        raise RuntimeError(f"{job.name}: sliced job exceeds the P1S build plate")
    filament_ids = tuple(item["id"] for item in plate["filaments"])
    if filament_ids != job.expected_filaments:
        raise RuntimeError(f"{job.name}: unexpected filament assignment {filament_ids}")
    filament_change_times = int(plate.get("filament_change_times", -1))
    if filament_change_times != job.expected_filament_changes:
        raise RuntimeError(
            f"{job.name}: expected {job.expected_filament_changes} filament changes, "
            f"got {filament_change_times}"
        )
    if int(result.get("wall_loops", -1)) != job.wall_loops:
        raise RuntimeError(f"{job.name}: slicer did not retain {job.wall_loops} walls")
    if abs(float(result.get("sparse_infill_density", -1)) - job.infill_percent) > 0.01:
        raise RuntimeError(f"{job.name}: slicer did not retain {job.infill_percent}% infill")
    if header_value(gcode, "printer_model") != "Bambu Lab P1S":
        raise RuntimeError(f"{job.name}: G-code is not targeted at the Bambu Lab P1S")
    if header_value(gcode, "enable_support") != "0":
        raise RuntimeError(f"{job.name}: support generation must remain disabled")
    expected_filament_header = ",".join(str(value) for value in job.expected_filaments)
    if header_value(gcode, "filament") != expected_filament_header:
        raise RuntimeError(f"{job.name}: G-code has an unexpected filament map")
    expected_multi_material = "1" if job.multi_material else "0"
    if header_value(gcode, "single_extruder_multi_material") != expected_multi_material:
        raise RuntimeError(f"{job.name}: G-code has the wrong material mode")
    if header_value(gcode, "enable_prime_tower") != expected_multi_material:
        raise RuntimeError(f"{job.name}: G-code has the wrong prime-tower mode")
    if not job.multi_material and re.search(r"^(?:T1|M620 S1A)$", gcode, re.MULTILINE):
        raise RuntimeError(f"{job.name}: single-filament G-code requests a second tool")
    layer_match = re.search(r"^; total layer number:\s*(\d+)$", gcode, re.MULTILINE)
    if not layer_match:
        raise RuntimeError(f"{job.name}: G-code does not report a layer count")
    return {
        "bbox_mm": bbox,
        "filaments": plate["filaments"],
        "filament_change_times": filament_change_times,
        "layers": int(layer_match.group(1)),
        "wall_loops": job.wall_loops,
        "sparse_infill_density_percent": job.infill_percent,
        "supports": False,
        "multi_material": job.multi_material,
        "prime_tower": job.multi_material,
    }


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def slice_job(job: PrintJob, bambu_version: str) -> None:
    if not job.project.exists():
        raise RuntimeError(f"missing generated project: {job.project.name}")
    with tempfile.TemporaryDirectory(prefix=f".{job.name}_slice_", dir=ROOT) as temp_dir:
        staging = Path(temp_dir)
        sliced_project_path = staging / f"{job.name}.gcode.3mf"
        invocation = command(
            "--debug",
            "1",
            "--slice",
            "0",
            "--outputdir",
            staging,
            "--export-3mf",
            sliced_project_path.name,
            job.project,
        )
        print("+", " ".join(invocation), flush=True)
        completed = subprocess.run(
            invocation,
            cwd=staging,
            env=environment(),
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"{job.name}: Bambu Studio failed:\n{completed.stdout}{completed.stderr}"
            )
        result_path = staging / "result.json"
        gcode_path = staging / "plate_1.gcode"
        if (
            not result_path.exists()
            or not gcode_path.exists()
            or not sliced_project_path.exists()
        ):
            raise RuntimeError(f"{job.name}: Bambu Studio did not produce slice artifacts")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        gcode = gcode_path.read_text(encoding="utf-8")
        summary = validate_slice(job, result, gcode)
        with zipfile.ZipFile(sliced_project_path) as archive:
            embedded_gcode = archive.read("Metadata/plate_1.gcode")
        if embedded_gcode != gcode_path.read_bytes():
            raise RuntimeError(
                f"{job.name}: pre-sliced 3MF does not contain the validated G-code"
            )

        output = OUTPUT_ROOT
        project_output = output / job.project.name
        gcode_output = output / job.gcode_name
        sliced_project_output = output / sliced_project_path.name
        result_output = output / f"{job.name}.result.json"
        atomic_copy(job.project, project_output)
        atomic_copy(gcode_path, gcode_output)
        atomic_copy(sliced_project_path, sliced_project_output)
        atomic_copy(result_path, result_output)
        manifest = {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "job": job.name,
            "slicer": {"application": "Bambu Studio", "version": bambu_version},
            "project": {"file": project_output.name, "sha256": sha256(project_output)},
            "printable_3mf": {
                "file": sliced_project_output.name,
                "sha256": sha256(sliced_project_output),
            },
            "gcode": {"file": gcode_output.name, "sha256": sha256(gcode_output)},
            "validation": summary,
        }
        manifest_path = output / f"{job.name}.slice.json"
        temporary_manifest = output / f".{job.name}.slice.json.tmp"
        temporary_manifest.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(temporary_manifest, manifest_path)
        print(
            f"{job.name}: {sliced_project_output.relative_to(ROOT)}; "
            f"{summary['layers']} layers; SHA-256 {manifest['gcode']['sha256']}",
            flush=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--slice-only",
        action="store_true",
        help="slice existing projects without regenerating canonical geometry",
    )
    args = parser.parse_args()
    bambu_version = require_bambu_studio()
    if not args.slice_only:
        run_python("tools/export_all_stl_assets.py")
    for job in JOBS:
        slice_job(job, bambu_version)
    for obsolete in (OUTPUT_ROOT / "plate_1.gcode", OUTPUT_ROOT / "result.json"):
        obsolete.unlink(missing_ok=True)
    print(f"All production print jobs written under {OUTPUT_ROOT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
