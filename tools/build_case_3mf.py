#!/usr/bin/env python3
"""Build the aligned two-material P1S project for the print-in-place case."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import trimesh


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "QuenaCase.3mf"
CASE_STL = ROOT / "QuenaCasePrintInPlace.stl"
LOGO_STL = ROOT / "QuenaCaseLidLogo.stl"
CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT = "http://schemas.openxmlformats.org/package/2006/content-types"
ET.register_namespace("", CORE)


def project_settings() -> dict[str, object]:
    settings: dict[str, object] = {}
    if OUTPUT.exists():
        try:
            with zipfile.ZipFile(OUTPUT) as archive:
                settings = json.loads(
                    archive.read("Metadata/project_settings.config").decode("utf-8")
                )
        except (KeyError, json.JSONDecodeError, zipfile.BadZipFile):
            settings = {}
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


def add_mesh(resources: ET.Element, object_id: int, path: Path, material: int) -> None:
    mesh = trimesh.load(path, force="mesh", process=True)
    obj = ET.SubElement(
        resources,
        f"{{{CORE}}}object",
        {"id": str(object_id), "type": "model", "pid": "1", "pindex": str(material)},
    )
    geometry = ET.SubElement(obj, f"{{{CORE}}}mesh")
    vertices = ET.SubElement(geometry, f"{{{CORE}}}vertices")
    for x, y, z in mesh.vertices:
        ET.SubElement(
            vertices,
            f"{{{CORE}}}vertex",
            {"x": f"{x:.5f}", "y": f"{y:.5f}", "z": f"{z:.5f}"},
        )
    triangles = ET.SubElement(geometry, f"{{{CORE}}}triangles")
    for v1, v2, v3 in mesh.faces:
        ET.SubElement(
            triangles,
            f"{{{CORE}}}triangle",
            {"v1": str(v1), "v2": str(v2), "v3": str(v3)},
        )


def model_xml() -> bytes:
    model = ET.Element(f"{{{CORE}}}model", {"unit": "millimeter", "xml:lang": "en-US"})
    ET.SubElement(model, f"{{{CORE}}}metadata", {"name": "Application"}).text = (
        "AgnuQuena case project builder"
    )
    resources = ET.SubElement(model, f"{{{CORE}}}resources")
    materials = ET.SubElement(resources, f"{{{CORE}}}basematerials", {"id": "1"})
    ET.SubElement(materials, f"{{{CORE}}}base", {"name": "Yellow ABS case", "displaycolor": "#FFF144FF"})
    ET.SubElement(materials, f"{{{CORE}}}base", {"name": "Black ABS logo", "displaycolor": "#000000FF"})
    add_mesh(resources, 2, CASE_STL, 0)
    add_mesh(resources, 3, LOGO_STL, 1)
    assembly = ET.SubElement(resources, f"{{{CORE}}}object", {"id": "4", "type": "model"})
    components = ET.SubElement(assembly, f"{{{CORE}}}components")
    ET.SubElement(components, f"{{{CORE}}}component", {"objectid": "2"})
    ET.SubElement(components, f"{{{CORE}}}component", {"objectid": "3"})
    build = ET.SubElement(model, f"{{{CORE}}}build")
    ET.SubElement(
        build,
        f"{{{CORE}}}item",
        {
            "objectid": "4",
            "printable": "1",
            "transform": "1 0 0 0 1 0 0 0 1 128 156.685 0",
        },
    )
    return ET.tostring(model, encoding="utf-8", xml_declaration=True)


def model_settings_xml() -> bytes:
    config = ET.Element("config")
    obj = ET.SubElement(config, "object", {"id": "4"})
    ET.SubElement(obj, "metadata", {"key": "name", "value": "AgnuQuena two-colour case"})
    for part_id, name, extruder in (
        (2, CASE_STL.name, "1"),
        (3, LOGO_STL.name, "2"),
    ):
        part = ET.SubElement(obj, "part", {"id": str(part_id), "subtype": "normal_part"})
        ET.SubElement(part, "metadata", {"key": "name", "value": name})
        ET.SubElement(part, "metadata", {"key": "extruder", "value": extruder})
    plate = ET.SubElement(config, "plate")
    ET.SubElement(plate, "metadata", {"key": "plater_id", "value": "1"})
    ET.SubElement(plate, "metadata", {"key": "locked", "value": "true"})
    ET.SubElement(plate, "metadata", {"key": "filament_map_mode", "value": "Manual"})
    ET.SubElement(plate, "metadata", {"key": "filament_maps", "value": "1 2"})
    instance = ET.SubElement(plate, "model_instance")
    ET.SubElement(instance, "metadata", {"key": "object_id", "value": "4"})
    ET.SubElement(instance, "metadata", {"key": "instance_id", "value": "0"})
    return ET.tostring(config, encoding="utf-8", xml_declaration=True)


def package_files() -> dict[str, bytes]:
    content_types = ET.Element(f"{{{CONTENT}}}Types")
    ET.SubElement(content_types, f"{{{CONTENT}}}Default", {"Extension": "rels", "ContentType": "application/vnd.openxmlformats-package.relationships+xml"})
    ET.SubElement(content_types, f"{{{CONTENT}}}Default", {"Extension": "model", "ContentType": "application/vnd.ms-package.3dmanufacturing-3dmodel+xml"})
    relationships = ET.Element(f"{{{REL}}}Relationships")
    ET.SubElement(relationships, f"{{{REL}}}Relationship", {"Target": "/3D/3dmodel.model", "Id": "rel-1", "Type": "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"})
    return {
        "[Content_Types].xml": ET.tostring(content_types, encoding="utf-8", xml_declaration=True),
        "_rels/.rels": ET.tostring(relationships, encoding="utf-8", xml_declaration=True),
        "3D/3dmodel.model": model_xml(),
        "Metadata/model_settings.config": model_settings_xml(),
        "Metadata/project_settings.config": json.dumps(project_settings(), indent=2, sort_keys=True).encode("utf-8") + b"\n",
    }


def main() -> None:
    for path in (CASE_STL, LOGO_STL):
        if not path.exists():
            raise SystemExit(f"missing {path.name}; render case assets first")
    files = package_files()
    temporary = OUTPUT.with_suffix(".3mf.tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in files.items():
            info = zipfile.ZipInfo(name, (2026, 8, 2, 12, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    temporary.replace(OUTPUT)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
