#!/usr/bin/env python3
"""Build the canonical single-material P1S project for the complete quena layout."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import trimesh

from bambu_studio import PROFILE_ROOT, command, environment, require


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "Quena.3mf"
LAYOUT_STL = ROOT / "Quena.stl"
SETTINGS_TEMPLATE = ROOT / "config" / "bambu_p1s_abs_project_settings.json"
MACHINE_PROFILE = PROFILE_ROOT / "machine" / "Bambu Lab P1S 0.4 nozzle.json"
PROCESS_PROFILE = PROFILE_ROOT / "process" / "0.20mm Strength @BBL X1C.json"
FILAMENT_PROFILE = PROFILE_ROOT / "filament" / "PolyLite ABS @BBL X1C.json"


def require_bambu_studio() -> None:
    require()


def build_skeleton(output: Path) -> None:
    invocation = command(
        "--debug",
        "1",
        "--assemble",
        "--arrange",
        "0",
        "--orient",
        "0",
        "--skip-useless-pick",
        "--load-settings",
        f"{MACHINE_PROFILE};{PROCESS_PROFILE}",
        "--load-filaments",
        FILAMENT_PROFILE,
        "--load-filament-ids",
        "1",
        "--export-3mf",
        output,
        LAYOUT_STL,
    )
    completed = subprocess.run(
        invocation,
        cwd=output.parent,
        env=environment(),
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0 or not output.exists():
        raise SystemExit(
            "Bambu Studio could not build the quena project:\n"
            f"{completed.stdout}{completed.stderr}"
        )


def production_settings(settings: dict[str, object]) -> dict[str, object]:
    settings.update(
        {
            "name": "AgnuQuena production layout",
            "printer_model": "Bambu Lab P1S",
            "printer_settings_id": "Bambu Lab P1S 0.4 nozzle",
            "print_settings_id": "0.20mm Strength @BBL X1C",
            "printable_area": ["0x0", "256x0", "256x256", "0x256"],
            "nozzle_diameter": ["0.4"],
            "layer_height": "0.2",
            "initial_layer_print_height": "0.2",
            "wall_loops": "6",
            "sparse_infill_density": "25%",
            "sparse_infill_pattern": "grid",
            "enable_support": "0",
            "enforce_support_layers": "0",
            "brim_type": "auto_brim",
            "brim_width": "5",
            "skirt_loops": "0",
            "single_extruder_multi_material": "0",
            "enable_prime_tower": "0",
            "filament_colour": ["#FFF144"],
            "filament_type": ["ABS"],
            "filament_settings_id": ["PolyLite ABS @BBL X1C"],
            "filament_map": ["1"],
        }
    )
    return settings


def placement_transform() -> str:
    mesh = trimesh.load(LAYOUT_STL, force="mesh")
    center_z = float((mesh.bounds[0][2] + mesh.bounds[1][2]) / 2)
    return f"1 0 0 0 1 0 0 0 1 128 128 {center_z:.6f}"


def patched_model_xml(data: bytes, transform: str) -> bytes:
    source = data.decode("utf-8")
    source, component_count = re.subn(
        r'(<component\b[^>]*\btransform=")[^"]+("/>)',
        r"\g<1>1 0 0 0 1 0 0 0 1 0 0 0\2",
        source,
    )
    source, item_count = re.subn(
        r'(<item\b[^>]*\btransform=")[^"]+("[^>]*\bprintable="1")',
        rf"\g<1>{transform}\2",
        source,
        count=1,
    )
    if component_count != 1 or item_count != 1:
        raise ValueError("Bambu project does not contain one printable quena layout")
    return source.encode("utf-8")


def patched_model_settings(data: bytes, transform: str) -> bytes:
    root = ET.fromstring(data)
    obj = root.find("object")
    if obj is None:
        raise ValueError("Bambu project has no quena object")
    object_id = obj.attrib["id"]
    for metadata in obj.findall("metadata"):
        if metadata.attrib.get("key") == "name":
            metadata.set("value", LAYOUT_STL.name)
    parts = obj.findall("part")
    if len(parts) != 1:
        raise ValueError("Bambu project must contain one quena layout part")
    for metadata in parts[0].findall("metadata"):
        if metadata.attrib.get("key") == "name":
            metadata.set("value", LAYOUT_STL.name)
        elif metadata.attrib.get("key") == "matrix":
            metadata.set("value", "1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1")

    plate = root.find("plate")
    if plate is None:
        plate = ET.SubElement(root, "plate")
    for node in plate.findall("model_instance"):
        plate.remove(node)
    instance = ET.SubElement(plate, "model_instance")
    ET.SubElement(instance, "metadata", {"key": "object_id", "value": object_id})
    ET.SubElement(instance, "metadata", {"key": "instance_id", "value": "0"})

    assemble = root.find("assemble")
    if assemble is None:
        assemble = ET.SubElement(root, "assemble")
    for node in assemble.findall("assemble_item"):
        assemble.remove(node)
    ET.SubElement(
        assemble,
        "assemble_item",
        {
            "object_id": object_id,
            "instance_id": "0",
            "transform": transform,
            "offset": "0 0 0",
        },
    )
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def publish_project(skeleton: Path) -> None:
    with zipfile.ZipFile(skeleton) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    settings_path = "Metadata/project_settings.config"
    settings = json.loads(SETTINGS_TEMPLATE.read_text(encoding="utf-8"))
    files[settings_path] = (
        json.dumps(production_settings(settings), indent=2, sort_keys=True).encode("utf-8")
        + b"\n"
    )
    transform = placement_transform()
    files["3D/3dmodel.model"] = patched_model_xml(
        files["3D/3dmodel.model"], transform
    )
    files["Metadata/model_settings.config"] = patched_model_settings(
        files["Metadata/model_settings.config"], transform
    )

    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=ROOT, prefix=".Quena.", suffix=".3mf"
    )
    os.close(file_descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for name in sorted(files):
                info = zipfile.ZipInfo(name, (2026, 8, 2, 12, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, files[name])
        os.replace(temporary, OUTPUT)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    for path in (LAYOUT_STL, SETTINGS_TEMPLATE):
        if not path.exists():
            raise SystemExit(f"missing {path.name}; export the print projects first")
    require_bambu_studio()
    with tempfile.TemporaryDirectory(prefix=".bambu_quena_", dir=ROOT) as temp_dir:
        skeleton = Path(temp_dir) / "Quena.3mf"
        build_skeleton(skeleton)
        publish_project(skeleton)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
