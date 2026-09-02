#!/usr/bin/env python3
"""Build two-color and single-filament P1S case projects with BambuStudio."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from bambu_studio import PROFILE_ROOT, command, environment, require


ROOT = Path(__file__).resolve().parents[1]
TWO_COLOR_OUTPUT = ROOT / "QuenaCase.3mf"
ELI_TWO_COLOR_OUTPUT = ROOT / "QuenaCaseEli.3mf"
LOAF_BOOF_TWO_COLOR_OUTPUT = ROOT / "QuenaCaseLoafBoof.3mf"
SINGLE_FILAMENT_OUTPUT = ROOT / "QuenaCaseSingleFilament.3mf"
SETTINGS_TEMPLATE = ROOT / "config" / "bambu_p1s_abs_project_settings.json"
SINGLE_FILAMENT_CASE_STL = ROOT / "QuenaCasePrintInPlace.stl"
TWO_COLOR_CASE_STL = ROOT / "QuenaCaseTwoColorPrintInPlace.stl"
ARTWORK_STL = ROOT / "QuenaCaseArtwork.stl"
ELI_TWO_COLOR_CASE_STL = ROOT / "QuenaCaseEliTwoColorPrintInPlace.stl"
ELI_ARTWORK_STL = ROOT / "QuenaCaseEliArtwork.stl"
LOAF_BOOF_TWO_COLOR_CASE_STL = ROOT / "QuenaCaseLoafBoofTwoColorPrintInPlace.stl"
LOAF_BOOF_ARTWORK_STL = ROOT / "QuenaCaseLoafBoofArtwork.stl"
MACHINE_PROFILE = PROFILE_ROOT / "machine" / "Bambu Lab P1S 0.4 nozzle.json"
PROCESS_PROFILE = PROFILE_ROOT / "process" / "0.20mm Strength @BBL X1C.json"
FILAMENT_PROFILE = PROFILE_ROOT / "filament" / "PolyLite ABS @BBL X1C.json"
PLATE_TRANSFORM = "1 0 0 0 1 0 0 0 1 128 156.685 0"


def project_settings(
    *,
    two_color: bool,
    name: str | None = None,
    first_layer_print_sequence: tuple[int, ...] | None = None,
) -> dict[str, object]:
    settings = json.loads(SETTINGS_TEMPLATE.read_text(encoding="utf-8"))
    settings.update(
        {
            "name": name or (
                "AgnuQuena two-color print-in-place case"
                if two_color
                else "AgnuQuena single-filament print-in-place case"
            ),
            "printer_model": "Bambu Lab P1S",
            "printer_settings_id": "Bambu Lab P1S 0.4 nozzle",
            "print_settings_id": "0.20mm Strength @BBL X1C",
            "printable_area": ["0x0", "256x0", "256x256", "0x256"],
            "nozzle_diameter": ["0.4"],
            "layer_height": "0.2",
            "initial_layer_print_height": "0.2",
            "wall_loops": "2",
            "top_shell_layers": "2",
            "bottom_shell_layers": "2",
            "only_one_wall_top": "1",
            # The P1S standard profile uses 200 mm/s. Use a conservative
            # 120 mm/s for broad cosmetic walls while its existing 50% small-
            # perimeter rule keeps hinge and latch details at 60 mm/s.
            "outer_wall_speed": ["120", "120"],
            "sparse_infill_density": "10%",
            # Bambu Studio's internal enum name for Rectilinear is "zig-zag".
            "sparse_infill_pattern": "zig-zag",
            "infill_combination": "1",
            "elefant_foot_compensation": "0.15",
            "enable_support": "0",
            "enforce_support_layers": "0",
            "brim_type": "no_brim",
            "brim_width": "0",
            "skirt_loops": "0",
            "single_extruder_multi_material": "1" if two_color else "0",
            "enable_prime_tower": "1" if two_color else "0",
            "prime_tower_width": "20",
            "prime_tower_brim_width": "1",
            "wipe_tower_no_sparse_layers": "1" if two_color else "0",
            "filament_colour": ["#FFF144", "#000000"] if two_color else ["#FFF144"],
            "filament_type": ["ABS", "ABS"] if two_color else ["ABS"],
            "filament_settings_id": (
                ["PolyLite ABS @BBL X1C", "PolyLite ABS @BBL X1C"]
                if two_color
                else ["PolyLite ABS @BBL X1C"]
            ),
            "filament_map": ["1", "2"] if two_color else ["1"],
        }
    )
    if first_layer_print_sequence is not None:
        settings["first_layer_print_sequence"] = [
            str(value) for value in first_layer_print_sequence
        ]
    return settings


def bambu_skeleton(
    output: Path,
    *,
    two_color: bool,
    case_stl: Path = TWO_COLOR_CASE_STL,
    artwork_stl: Path = ARTWORK_STL,
) -> None:
    require()
    models = (
        (case_stl, artwork_stl)
        if two_color
        else (SINGLE_FILAMENT_CASE_STL,)
    )
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
        f"{FILAMENT_PROFILE};{FILAMENT_PROFILE}" if two_color else FILAMENT_PROFILE,
        "--load-filament-ids",
        "1,2" if two_color else "1",
        "--export-3mf",
        output,
        *models,
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


def patched_model_settings(
    data: bytes,
    *,
    two_color: bool,
    case_stl: Path = TWO_COLOR_CASE_STL,
    artwork_stl: Path = ARTWORK_STL,
    first_layer_print_sequence: tuple[int, ...] | None = None,
) -> bytes:
    root = ET.fromstring(data)
    obj = root.find("object")
    if obj is None:
        raise ValueError("Bambu project has no assembled object")
    object_id = obj.attrib["id"]
    parts = obj.findall("part")
    expected_parts = 2 if two_color else 1
    if len(parts) != expected_parts:
        raise ValueError(
            f"Bambu project must contain exactly {expected_parts} case part(s)"
        )
    names = (
        (case_stl.name, artwork_stl.name)
        if two_color
        else (SINGLE_FILAMENT_CASE_STL.name,)
    )
    extruders = ("1", "2") if two_color else ("1",)
    for part, name, extruder in zip(
        parts,
        names,
        extruders,
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
        "filament_maps": "1 2" if two_color else "1",
    }
    if first_layer_print_sequence is not None:
        desired["first_layer_print_sequence"] = " ".join(
            str(value) for value in first_layer_print_sequence
        )
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


def write_project(
    skeleton: Path,
    output: Path,
    *,
    two_color: bool,
    case_stl: Path = TWO_COLOR_CASE_STL,
    artwork_stl: Path = ARTWORK_STL,
    project_name: str | None = None,
    first_layer_print_sequence: tuple[int, ...] | None = None,
) -> None:
    with zipfile.ZipFile(skeleton) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    files["3D/3dmodel.model"] = patched_model_xml(files["3D/3dmodel.model"])
    files["Metadata/model_settings.config"] = patched_model_settings(
        files["Metadata/model_settings.config"],
        two_color=two_color,
        case_stl=case_stl,
        artwork_stl=artwork_stl,
        first_layer_print_sequence=first_layer_print_sequence,
    )
    files["Metadata/project_settings.config"] = (
        json.dumps(
            project_settings(
                two_color=two_color,
                name=project_name,
                first_layer_print_sequence=first_layer_print_sequence,
            ),
            indent=2,
            sort_keys=True,
        ).encode(
            "utf-8"
        )
        + b"\n"
    )
    temporary = output.with_suffix(".3mf.tmp")
    with zipfile.ZipFile(
        temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, (2026, 8, 2, 12, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, files[name])
    temporary.replace(output)


def build_project(
    output: Path,
    *,
    two_color: bool,
    case_stl: Path = TWO_COLOR_CASE_STL,
    artwork_stl: Path = ARTWORK_STL,
    project_name: str | None = None,
    first_layer_print_sequence: tuple[int, ...] | None = None,
) -> None:
    label = "two_color" if two_color else "single_filament"
    with tempfile.TemporaryDirectory(prefix=f".bambu_case_{label}_", dir=ROOT) as temp_dir:
        skeleton = Path(temp_dir) / output.name
        bambu_skeleton(
            skeleton,
            two_color=two_color,
            case_stl=case_stl,
            artwork_stl=artwork_stl,
        )
        write_project(
            skeleton,
            output,
            two_color=two_color,
            case_stl=case_stl,
            artwork_stl=artwork_stl,
            project_name=project_name,
            first_layer_print_sequence=first_layer_print_sequence,
        )
    print(output.relative_to(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("all", "two-color", "eli", "loaf-boof", "single"),
        default="all",
        help="select which case project variant to export",
    )
    args = parser.parse_args()
    required = [SETTINGS_TEMPLATE]
    if args.mode in ("all", "two-color"):
        required.extend((TWO_COLOR_CASE_STL, ARTWORK_STL))
    if args.mode in ("all", "eli"):
        required.extend((ELI_TWO_COLOR_CASE_STL, ELI_ARTWORK_STL))
    if args.mode in ("all", "loaf-boof"):
        required.extend((LOAF_BOOF_TWO_COLOR_CASE_STL, LOAF_BOOF_ARTWORK_STL))
    if args.mode in ("all", "single"):
        required.append(SINGLE_FILAMENT_CASE_STL)
    for path in required:
        if not path.exists():
            raise SystemExit(f"missing {path.name}; render case assets first")
    if args.mode in ("all", "two-color"):
        build_project(TWO_COLOR_OUTPUT, two_color=True)
    if args.mode in ("all", "eli"):
        build_project(
            ELI_TWO_COLOR_OUTPUT,
            two_color=True,
            case_stl=ELI_TWO_COLOR_CASE_STL,
            artwork_stl=ELI_ARTWORK_STL,
            project_name="AgnuQuena ELI 2026 two-color print-in-place case",
        )
    if args.mode in ("all", "loaf-boof"):
        build_project(
            LOAF_BOOF_TWO_COLOR_OUTPUT,
            two_color=True,
            case_stl=LOAF_BOOF_TWO_COLOR_CASE_STL,
            artwork_stl=LOAF_BOOF_ARTWORK_STL,
            project_name="AgnuQuena Loaf Boof 26 two-color print-in-place case",
            first_layer_print_sequence=(2, 1),
        )
    if args.mode in ("all", "single"):
        build_project(SINGLE_FILAMENT_OUTPUT, two_color=False)


if __name__ == "__main__":
    main()
