#!/usr/bin/env python3
"""Build the aligned two-material P1S project with Bambu Studio itself."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from bambu_studio import PROFILE_ROOT, command, environment, require


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "QuenaCase.3mf"
SETTINGS_TEMPLATE = ROOT / "config" / "bambu_p1s_abs_project_settings.json"
CASE_STL = ROOT / "QuenaCasePrintInPlace.stl"
ARTWORK_STL = ROOT / "QuenaCaseArtwork.stl"
MACHINE_PROFILE = PROFILE_ROOT / "machine" / "Bambu Lab P1S 0.4 nozzle.json"
PROCESS_PROFILE = PROFILE_ROOT / "process" / "0.20mm Strength @BBL X1C.json"
FILAMENT_PROFILE = PROFILE_ROOT / "filament" / "PolyLite ABS @BBL X1C.json"
PLATE_TRANSFORM = "1 0 0 0 1 0 0 0 1 128 156.685 0"


def project_settings() -> dict[str, object]:
    settings = json.loads(SETTINGS_TEMPLATE.read_text(encoding="utf-8"))
    settings.update(
        {
            "name": "AgnuQuena two-colour print-in-place case",
            "printer_model": "Bambu Lab P1S",
            "printer_settings_id": "Bambu Lab P1S 0.4 nozzle",
            "print_settings_id": "0.20mm Strength @BBL X1C",
            "printable_area": ["0x0", "256x0", "256x256", "0x256"],
            "nozzle_diameter": ["0.4"],
            "layer_height": "0.2",
            "initial_layer_print_height": "0.2",
            "wall_loops": "3",
            "sparse_infill_density": "10%",
            "sparse_infill_pattern": "grid",
            "elefant_foot_compensation": "0.15",
            "enable_support": "0",
            "enforce_support_layers": "0",
            "brim_type": "no_brim",
            "brim_width": "0",
            "skirt_loops": "0",
            "single_extruder_multi_material": "1",
            "enable_prime_tower": "1",
            "prime_tower_width": "20",
            "prime_tower_brim_width": "1",
            "wipe_tower_no_sparse_layers": "1",
            "filament_colour": ["#FFF144", "#000000"],
            "filament_type": ["ABS", "ABS"],
            "filament_settings_id": [
                "PolyLite ABS @BBL X1C",
                "PolyLite ABS @BBL X1C",
            ],
            "filament_map": ["1", "2"],
        }
    )
    return settings


def bambu_skeleton(output: Path) -> None:
    require()
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
        f"{FILAMENT_PROFILE};{FILAMENT_PROFILE}",
        "--load-filament-ids",
        "1,2",
        "--export-3mf",
        output,
        CASE_STL,
        ARTWORK_STL,
    )
    completed = subprocess.run(
        invocation,
        cwd=output.parent,
        env=environment(),
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise SystemExit(
            "Bambu Studio could not build the project skeleton:\n"
            f"{completed.stdout}{completed.stderr}"
        )
    if not output.exists():
        raise SystemExit("Bambu Studio did not produce the case project")


def patched_model_xml(data: bytes) -> bytes:
    source = data.decode("utf-8")
    source, count = re.subn(
        r'(<item\b[^>]*\btransform=")[^"]+("[^>]*\bprintable="1")',
        rf"\g<1>{PLATE_TRANSFORM}\2",
        source,
        count=1,
    )
    if count != 1:
        raise ValueError("Bambu project has no printable build item to position")
    return source.encode("utf-8")


def patched_model_settings(data: bytes) -> bytes:
    root = ET.fromstring(data)
    obj = root.find("object")
    if obj is None:
        raise ValueError("Bambu project has no assembled object")
    object_id = obj.attrib["id"]
    parts = obj.findall("part")
    if len(parts) != 2:
        raise ValueError("Bambu project must contain exactly the case and artwork parts")
    for part, name, extruder in zip(
        parts,
        (CASE_STL.name, ARTWORK_STL.name),
        ("1", "2"),
    ):
        for metadata in part.findall("metadata"):
            if metadata.attrib.get("key") == "name":
                metadata.set("value", name)
            elif metadata.attrib.get("key") == "extruder":
                metadata.set("value", extruder)

    plate = root.find("plate")
    if plate is None:
        plate = ET.SubElement(root, "plate")
    desired = {
        "plater_id": "1",
        "locked": "true",
        "filament_map_mode": "Manual",
        "filament_maps": "1 2",
    }
    existing = {
        node.attrib.get("key"): node for node in plate.findall("metadata")
    }
    for key, value in desired.items():
        node = existing.get(key)
        if node is None:
            node = ET.SubElement(plate, "metadata", {"key": key})
        node.set("value", value)
    for node in plate.findall("model_instance"):
        plate.remove(node)
    instance = ET.SubElement(plate, "model_instance")
    ET.SubElement(instance, "metadata", {"key": "object_id", "value": object_id})
    ET.SubElement(instance, "metadata", {"key": "instance_id", "value": "0"})
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def write_project(skeleton: Path) -> None:
    with zipfile.ZipFile(skeleton) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    files["3D/3dmodel.model"] = patched_model_xml(files["3D/3dmodel.model"])
    files["Metadata/model_settings.config"] = patched_model_settings(
        files["Metadata/model_settings.config"]
    )
    files["Metadata/project_settings.config"] = (
        json.dumps(project_settings(), indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    temporary = OUTPUT.with_suffix(".3mf.tmp")
    with zipfile.ZipFile(
        temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, (2026, 8, 2, 12, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, files[name])
    temporary.replace(OUTPUT)


def main() -> None:
    for path in (SETTINGS_TEMPLATE, CASE_STL, ARTWORK_STL):
        if not path.exists():
            raise SystemExit(f"missing {path.name}; render case assets first")
    with tempfile.TemporaryDirectory(prefix=".bambu_case_", dir=ROOT) as temp_dir:
        skeleton = Path(temp_dir) / "QuenaCase.3mf"
        bambu_skeleton(skeleton)
        write_project(skeleton)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
