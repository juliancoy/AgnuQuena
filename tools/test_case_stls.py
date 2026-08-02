#!/usr/bin/env python3
"""Validate rendered AgnuQuena case STL files.

These tests intentionally inspect the exported meshes, not only the OpenSCAD
source, so they catch render regressions before slicing.
"""

from __future__ import annotations

import math
import json
import re
import struct
import subprocess
import tempfile
import zipfile
from collections import defaultdict, deque
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import trimesh


ROOT = Path(__file__).resolve().parents[1]

OBSOLETE_SPLIT_EXPORTS = (
    "QuenaCaseBottom.stl",
    "QuenaCaseLid.stl",
    "QuenaCaseLidLogo.stl",
    "website/assets/QuenaCaseBottom.stl",
    "website/assets/QuenaCaseLid.stl",
    "website/assets/QuenaCaseLidLogo.stl",
    "site-hosting/public/assets/QuenaCaseBottom.stl",
    "site-hosting/public/assets/QuenaCaseLid.stl",
    "site-hosting/public/assets/QuenaCaseLidLogo.stl",
)

EXPECTED = {
    "QuenaCasePrintInPlace.stl": {
        "size": (245.994, 113.948, 19.4),
        "min_triangles": 18000,
        "components": 2,
    },
    "QuenaCaseBottomViewer.stl": {
        "size": (245.994, 61.3, 19.4),
        "min_triangles": 2200,
        "components": 1,
    },
    "QuenaCaseLidViewer.stl": {
        "size": (245.994, 62.448, 19.3),
        "min_triangles": 1200,
        "components": 1,
    },
    "QuenaCaseArtwork.stl": {
        "size": (236.894, 105.654, 0.6),
        "min_triangles": 35000,
        "components": 29,
    },
    "QuenaCaseHingeCoupon.stl": {
        "size": (46.0, 28.0, 19.4),
        "min_triangles": 900,
        "components": 2,
    },
    "QuenaCaseFullHingeCoupon.stl": {
        "size": (243.5, 28.0, 19.4),
        "min_triangles": 4500,
        "components": 2,
    },
    "QuenaCaseLatchCoupon.stl": {
        "size": (182.0, 34.0, 18.9),
        "min_triangles": 1600,
        "components": 7,
    },
    "QuenaCaseAssembly.stl": {
        "size": (245.994, 62.448, 28.8),
        "min_triangles": 18000,
        "components": 2,
    },
}

LID_SWEEP_MAX_DEG = 180
CONTACT_TOLERANCE_MM = 0.05
CLOSED_OVERLAP_VOLUME_TOLERANCE_MM3 = 0.1
# Canonical 32 mm mouthpiece pocket, 8 mm short-row gaps, 1.5 mm bed-edge
# rounding, retention border, engraved back, and enclosed round hinge ends.
EXPECTED_CASE_VOLUME_MM3 = 255_083.18
CASE_VOLUME_TOLERANCE_MM3 = 10.0
# OpenSCAD's ASCII STL coordinate quantization accumulates a sub-voxel volume
# difference after the rigid 180-degree print-pose transform of rounded shells.
PRINT_POSE_VOLUME_TOLERANCE_MM3 = 0.2


def scad_scalar(name: str) -> float:
    for source_path in (
        ROOT / "QuenaCase.scad",
        ROOT / "generated" / "quena_parameters.scad",
    ):
        source = source_path.read_text(encoding="utf-8")
        match = re.search(
            rf"^\s*{re.escape(name)}\s*=\s*([-+]?\d+(?:\.\d+)?)\s*;",
            source,
            flags=re.MULTILINE,
        )
        if match:
            return float(match.group(1))
    with tempfile.TemporaryDirectory(prefix="quena_case_scalar_") as temp_dir:
        temp_path = Path(temp_dir)
        probe_scad = temp_path / "scalar.scad"
        probe_stl = temp_path / "scalar.stl"
        probe_scad.write_text(
            f'include <{ROOT / "QuenaCase.scad"}>;\n'
            f'echo("SCAD_SCALAR", {name});\n'
            "cube(1);\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            ["openscad", "-D", 'part="none"', "-o", str(probe_stl), str(probe_scad)],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    evaluated = re.search(
        r'ECHO:\s*"SCAD_SCALAR",\s*([-+\d.eE]+)',
        result.stdout,
    )
    if not evaluated:
        raise AssertionError(f"OpenSCAD sources: could not evaluate parameter {name}")
    return float(evaluated.group(1))


def evaluated_hinge_pose() -> tuple[float, float, float]:
    with tempfile.TemporaryDirectory(prefix="quena_case_values_") as temp_dir:
        temp_path = Path(temp_dir)
        probe_scad = temp_path / "values.scad"
        probe_stl = temp_path / "values.stl"
        probe_scad.write_text(
            f'include <{ROOT / "QuenaCase.scad"}>;\n'
            'echo("HINGE_POSE", hinge_axis_y, hinge_axis_z, lid_closed_z);\n'
            "cube(1);\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            ["openscad", '-D', 'part="none"', "-o", str(probe_stl), str(probe_scad)],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    match = re.search(
        r'ECHO:\s*"HINGE_POSE",\s*([-+\d.eE]+),\s*([-+\d.eE]+),\s*([-+\d.eE]+)',
        result.stdout,
    )
    if not match:
        raise AssertionError("OpenSCAD did not report the evaluated hinge pose")
    return tuple(float(match.group(i)) for i in range(1, 4))


def run_hinge_design_checks() -> None:
    axle_d = scad_scalar("hinge_axle_d")
    bore_clearance = scad_scalar("hinge_bearing_clearance")
    bore_d = axle_d + bore_clearance
    outer_d = scad_scalar("hinge_bearing_outer_d")
    segment_w = scad_scalar("hinge_segment_w")
    segment_gap = scad_scalar("hinge_segment_gap")
    print_flat = scad_scalar("hinge_axle_print_flat")
    bearing_starter_h = scad_scalar("hinge_bearing_starter_h")
    print_shell_gap = scad_scalar("hinge_print_shell_gap")
    body_inset = scad_scalar("hinge_body_inset")
    end_barrel_d = scad_scalar("hinge_end_barrel_d")
    end_barrel_overhang = scad_scalar("hinge_end_barrel_overhang")

    bearing_wall = (outer_d - bore_d) / 2
    rear_projection = outer_d - body_inset
    evaluated_shell_gap = outer_d - 2 * body_inset

    if not 4.2 <= axle_d <= 5.0:
        raise AssertionError("integral hinge axle diameter is unsuitable")
    if not 0.50 <= bore_clearance <= 0.70:
        raise AssertionError(
            f"hinge bore clearance {bore_clearance:.2f} mm is outside 0.50-0.70 mm"
        )
    if bearing_wall < 1.5:
        raise AssertionError(f"hinge bearing wall is only {bearing_wall:.2f} mm")
    if bore_d > 6.0:
        raise AssertionError("circular hinge bore exceeds the support-free bridge limit")
    if not 10.0 <= segment_w <= 18.0:
        raise AssertionError("hinge bearing segments are not independently compliant")
    if not 0.8 <= segment_gap <= 1.4:
        raise AssertionError("hinge segment gap is unsuitable for FDM assembly")
    if not 0.5 <= print_flat <= 0.8:
        raise AssertionError("hinge axle D-flat is unsuitable for support-free printing")
    if not 0.3 <= bearing_starter_h <= 0.5:
        raise AssertionError("hinge bearing starter web is unsuitable")
    if not 0.50 <= print_shell_gap <= 0.80:
        raise AssertionError("print-in-place shell gap is unsuitable")
    if not math.isclose(evaluated_shell_gap, print_shell_gap, abs_tol=0.01):
        raise AssertionError("hinge axis does not produce the specified print shell gap")
    if not 4.4 <= body_inset <= 4.8:
        raise AssertionError("hinge body inset must retain rotational clearance")
    if rear_projection > 5.5:
        raise AssertionError(f"hinge rear projection is {rear_projection:.2f} mm")
    if not math.isclose(end_barrel_d, outer_d, abs_tol=0.01):
        raise AssertionError("outer hinge barrels do not match the round bearing diameter")
    if end_barrel_overhang < 1.0:
        raise AssertionError("outer hinge barrels do not cover the axle end faces")

    print(
        "QuenaCase hinge design: ok, "
        f"{axle_d:.2f} mm integral D-flat axle, {bore_d:.2f} mm bearing bore, "
        f"{bearing_wall:.2f} mm concentric bearing wall, "
        f"{bore_clearance / 2:.2f} mm "
        f"radial print clearance, {segment_w:.1f} mm closed bearings, "
        f"{print_shell_gap:.2f} mm bed gap, fully round bearing with starter web, "
        f"{end_barrel_d:.2f} mm round outer end barrels, "
        f"{rear_projection:.2f} mm rear projection, web-captured ends, "
        "support-free exports"
    )


def run_hinge_end_roundness_check() -> None:
    with tempfile.TemporaryDirectory(prefix="quena_hinge_end_roundness_") as temp_dir:
        temp_path = Path(temp_dir)
        probe_scad = temp_path / "round_end.scad"
        probe_stl = temp_path / "round_end.stl"
        probe_scad.write_text(
            f'include <{ROOT / "QuenaCase.scad"}>;\n'
            "lid_outer_end_barrels();\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                "openscad",
                "-D",
                'part="none"',
                "-o",
                str(probe_stl),
                str(probe_scad),
            ],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        mesh = trimesh.load(probe_stl, force="mesh")

    end_d = scad_scalar("hinge_end_barrel_d")
    overhang = scad_scalar("hinge_end_barrel_overhang")
    x2 = scad_scalar("hinge_axle_x2")
    section = mesh.section(
        plane_origin=[x2 + overhang - 0.2, 0, 0],
        plane_normal=[1, 0, 0],
    )
    if section is None:
        raise AssertionError("outer hinge end has no round cross-section")
    y_values = section.vertices[:, 1]
    z_values = section.vertices[:, 2]
    y_span = float(y_values.max() - y_values.min())
    z_span = float(z_values.max() - z_values.min())
    if not math.isclose(y_span, end_d, abs_tol=0.02):
        raise AssertionError(f"outer hinge end Y diameter is {y_span:.3f} mm")
    if not math.isclose(z_span, end_d, abs_tol=0.02):
        raise AssertionError(f"outer hinge end Z diameter is {z_span:.3f} mm")
    section_path, _ = section.to_2D()
    if sum(entity.closed for entity in section_path.entities) != 1:
        raise AssertionError("outer hinge end cross-section is not one closed circle")
    print(f"QuenaCase outer hinge ends: ok, closed round {end_d:.2f} mm sections")


def run_stator_roundness_check() -> None:
    with tempfile.TemporaryDirectory(prefix="quena_stator_roundness_") as temp_dir:
        temp_path = Path(temp_dir)
        probe_scad = temp_path / "round_stator.scad"
        probe_stl = temp_path / "round_stator.stl"
        probe_scad.write_text(
            f'include <{ROOT / "QuenaCase.scad"}>;\n'
            "bottom_hinge();\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                "openscad",
                "-D",
                'part="none"',
                "-o",
                str(probe_stl),
                str(probe_scad),
            ],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        mesh = trimesh.load(probe_stl, force="mesh")

    section = mesh.section(plane_origin=[0, 0, 0], plane_normal=[1, 0, 0])
    if section is None:
        raise AssertionError("central stator cross-section is missing")

    axis_y, axis_z, _ = evaluated_hinge_pose()
    outer_r = scad_scalar("hinge_bearing_outer_d") / 2
    radial_distances = [
        math.hypot(float(vertex[1]) - axis_y, float(vertex[2]) - axis_z)
        for vertex in section.vertices
    ]
    max_radius = max(radial_distances)
    # The 0.40 mm body-side starter web may project a fraction beyond the
    # faceted cylinder at its tangent. It must not become a visible backer.
    if max_radius > outer_r + 0.12:
        raise AssertionError(
            "hinge stator has a sharp backer outside its round envelope: "
            f"radius {max_radius:.3f} mm, expected {outer_r:.3f} mm"
        )
    print(
        "QuenaCase stators: ok, circular outer envelope, "
        f"{outer_r * 2:.2f} mm diameter"
    )


def run_latch_design_checks() -> None:
    protrusion = scad_scalar("latch_nub_protrusion")
    indent = scad_scalar("latch_indent_depth")
    nub_r = scad_scalar("latch_nub_r")
    tongue_w = scad_scalar("latch_tongue_w")
    tongue_t = scad_scalar("latch_tongue_t")
    flex_l = scad_scalar("latch_tongue_flex_l")
    root_blend = scad_scalar("latch_tongue_root_blend_h")
    free_l = flex_l - root_blend
    travel = protrusion - indent
    if not 0.20 <= travel <= 0.55:
        raise AssertionError(f"latch release travel {travel:.2f} mm is unsuitable")
    if nub_r < 1.95 or indent < 0.80:
        raise AssertionError("latch nub or receiving depth is undersized")
    if tongue_w < 17.5 or tongue_t < 1.2 or flex_l < 15.8:
        raise AssertionError("latch tongue is too thin or too short")
    if root_blend < 4.3 or free_l < 11.4:
        raise AssertionError("latch root attachment or free flex span is unsuitable")
    print(f"QuenaCase latch design: ok, {nub_r:.2f} mm nub radius, "
          f"{protrusion:.2f} mm nub projection, "
          f"{indent:.2f} mm recess, {travel:.2f} mm release travel, "
          f"{tongue_w:.2f} x {tongue_t:.2f} x {flex_l:.2f} mm tongue, "
          f"{root_blend:.2f} mm bonded root, {free_l:.2f} mm free span")


def run_channel_layout_checks() -> None:
    horizontal_land = scad_scalar("short_row_min_gap")
    vertical_land = scad_scalar("row_gap")
    edge_land = scad_scalar("channel_edge_land")
    deck_h = scad_scalar("channel_deck_h")
    tube_d = scad_scalar("id") + 2 * scad_scalar("shell_width")
    channel_d = tube_d + 2 * scad_scalar("part_clearance")
    connector_d = tube_d + 2 * (
        scad_scalar("shell_width") + scad_scalar("connector_radial_clearance")
    )
    max_channel_d = connector_d + 2 * scad_scalar("part_clearance")
    equator_pass = scad_scalar("equator_pass")
    axial_clearance = scad_scalar("axial_clearance")
    radial_clearance = scad_scalar("part_clearance")
    retention_overrun = scad_scalar("retention_lip_overrun")
    retention_clip_w = scad_scalar("retention_clip_w")
    retention_root_overlap = scad_scalar("retention_clip_root_overlap")
    retention_lid_clearance = scad_scalar("retention_lid_clearance")
    slot_xs = [scad_scalar(f"slot_xs[{i}]") for i in range(3)]
    profile_lengths = [scad_scalar(f"profile_lengths[{i}]") for i in range(3)]

    source = (ROOT / "QuenaCase.scad").read_text(encoding="utf-8")
    if "module cantilever_retainer" in source:
        raise AssertionError("obsolete cantilever retainers remain in the case")
    if not math.isclose(deck_h, max_channel_d / 2 + equator_pass, abs_tol=0.01):
        raise AssertionError("channel bed does not terminate at its equator target")
    if not 0.3 <= equator_pass <= 1.2:
        raise AssertionError(f"equator overrun {equator_pass:.2f} mm is unsuitable")
    if axial_clearance > 1.0:
        raise AssertionError(f"axial clearance {axial_clearance:.2f} mm is too loose")
    if radial_clearance > 0.4:
        raise AssertionError(f"radial clearance {radial_clearance:.2f} mm is too loose")

    channel_r = channel_d / 2
    part_r = tube_d / 2
    opening_half_w = math.sqrt(channel_r**2 - retention_overrun**2)
    snap_interference = 2 * (part_r - opening_half_w)
    if not 0.15 <= snap_interference <= 0.40:
        raise AssertionError(
            f"retention border diametral interference {snap_interference:.2f} mm "
            "is outside the light-snap range"
        )
    if retention_clip_w > 16:
        raise AssertionError("retention clips are too long for a low-force snap fit")
    if retention_root_overlap < 0.3:
        raise AssertionError("retention clips lack a fused root overlap")
    if retention_lid_clearance < 0.2:
        raise AssertionError("lid retention relief lacks printable clearance")
    if "lid_retention_relief();" not in source:
        raise AssertionError("lid does not remove the transferred retention border")

    if horizontal_land < 8.0:
        raise AssertionError(
            f"horizontal channel land is only {horizontal_land:.2f} mm"
        )
    if vertical_land < 2.5:
        raise AssertionError(f"vertical channel land is only {vertical_land:.2f} mm")
    if edge_land < 2.5:
        raise AssertionError(f"channel perimeter land is only {edge_land:.2f} mm")

    p1_left = slot_xs[0] - profile_lengths[0] / 2
    p1_right = slot_xs[0] + profile_lengths[0] / 2
    p2_left = slot_xs[1] - profile_lengths[1] / 2
    mouth_right = slot_xs[2] + profile_lengths[2] / 2
    if not math.isclose(p2_left, p1_left, abs_tol=0.01):
        raise AssertionError("P2 and P1 left profile edges are not aligned")
    if not math.isclose(mouth_right, p1_right, abs_tol=0.01):
        raise AssertionError("mouthpiece and P1 right profile edges are not aligned")
    print(
        "QuenaCase channel layout: ok, "
        f"{horizontal_land:.1f} mm minimum horizontal distribution gap, "
        f"{vertical_land:.1f} mm vertical land, "
        f"{edge_land:.1f} mm perimeter land, "
        f"{deck_h:.2f} mm single raised bed, "
        f"{equator_pass:.2f} mm past equator, "
        f"{snap_interference:.2f} mm diametral snap interference across "
        f"{retention_clip_w:.1f} mm clips, aligned P2/P1/mouthpiece outer edges, "
        f"{axial_clearance:.2f} mm axial and {radial_clearance:.2f} mm radial clearance"
    )


def run_exterior_design_checks() -> None:
    corner_r = scad_scalar("corner_r")
    inset = scad_scalar("mandala_inset")
    stroke = scad_scalar("mandala_stroke")
    depth = scad_scalar("mandala_depth")
    floor = scad_scalar("floor_thickness")
    edge_r = scad_scalar("bed_edge_r")
    case_l = scad_scalar("case_outer_l")
    source = (ROOT / "QuenaCase.scad").read_text(encoding="utf-8")

    if corner_r < 12:
        raise AssertionError("case outer corners are not broadly rounded")
    if not math.isclose(inset, 5.0, abs_tol=0.01):
        raise AssertionError("bottom ornament border is not 5 mm inside the edge")
    if stroke < 0.8:
        raise AssertionError("bottom ornament contains sub-two-line-width strokes")
    if not math.isclose(depth, 0.4, abs_tol=0.01):
        raise AssertionError("bottom ornament is not a two-layer engraving")
    if floor - depth < 2.4:
        raise AssertionError("bottom ornament leaves insufficient floor thickness")
    if not 1.0 <= edge_r <= floor - 1.0:
        raise AssertionError("bed-facing edge radius is not printable within the shell")
    if "for (x = mandala_centers)" not in source:
        raise AssertionError("bottom ornament is not procedurally repeated")
    if "bottom_ornament_recess();" not in source:
        raise AssertionError("bottom ornament is not cut into the production shell")
    if "round_bottom = true" not in source or "round_top = true" not in source:
        raise AssertionError("both bed-facing case backs are not edge-rounded")

    bottom = trimesh.load(ROOT / "QuenaCaseBottomViewer.stl", force="mesh")
    ornament_floor_vertices = int(
        (abs(bottom.vertices[:, 2] - depth) <= 0.01).sum()
    )
    if ornament_floor_vertices < 1000:
        raise AssertionError("rendered bottom lacks the detailed ornament floor")

    for name, use_max_z in (
        ("QuenaCaseBottomViewer.stl", False),
        ("QuenaCaseLidViewer.stl", True),
    ):
        mesh = trimesh.load(ROOT / name, force="mesh", process=False)
        bed_z = float(mesh.bounds[int(use_max_z)][2])
        bed_vertices = mesh.vertices[abs(mesh.vertices[:, 2] - bed_z) <= 0.01]
        contact_span = float(
            bed_vertices[:, 0].max() - bed_vertices[:, 0].min()
        )
        expected_span = case_l - 2 * edge_r
        if not math.isclose(contact_span, expected_span, abs_tol=0.3):
            raise AssertionError(f"{name} lacks the specified bed-edge rounding")

    print(
        "QuenaCase exterior: ok, "
        f"{corner_r:.0f} mm outer corner radius, three procedural mandalas, "
        f"{inset:.0f} mm inset rounded border, {stroke:.1f} mm minimum strokes, "
        f"{depth:.1f} mm support-free engraving, {floor - depth:.1f} mm floor, "
        f"{edge_r:.1f} mm bed-facing edge radius"
    )


def read_stl_triangles(path: Path) -> list[tuple[tuple[float, float, float], ...]]:
    data = path.read_bytes()
    if data.startswith(b"solid"):
        return read_ascii_stl(path)
    return read_binary_stl(data)


def read_ascii_stl(path: Path) -> list[tuple[tuple[float, float, float], ...]]:
    vertices: list[tuple[float, float, float]] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line.startswith("vertex "):
            continue
        _, x, y, z = line.split()
        vertices.append((float(x), float(y), float(z)))

    if len(vertices) % 3 != 0:
        raise AssertionError(f"{path.name}: vertex count is not divisible by 3")

    return [
        (vertices[i], vertices[i + 1], vertices[i + 2])
        for i in range(0, len(vertices), 3)
    ]


def read_binary_stl(data: bytes) -> list[tuple[tuple[float, float, float], ...]]:
    if len(data) < 84:
        raise AssertionError("binary STL is too small")

    triangle_count = struct.unpack("<I", data[80:84])[0]
    expected_size = 84 + triangle_count * 50
    if len(data) != expected_size:
        raise AssertionError(
            f"binary STL length mismatch: expected {expected_size}, got {len(data)}"
        )

    triangles = []
    offset = 84
    for _ in range(triangle_count):
        offset += 12
        tri = []
        for _ in range(3):
            tri.append(struct.unpack("<fff", data[offset : offset + 12]))
            offset += 12
        offset += 2
        triangles.append(tuple(tri))
    return triangles


def bounds(
    triangles: list[tuple[tuple[float, float, float], ...]]
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    points = [point for triangle in triangles for point in triangle]
    mins = tuple(min(point[i] for point in points) for i in range(3))
    maxs = tuple(max(point[i] for point in points) for i in range(3))
    return mins, maxs


def component_count(
    triangles: list[tuple[tuple[float, float, float], ...]], tolerance: float = 0.001
) -> int:
    def key(point: tuple[float, float, float]) -> tuple[int, int, int]:
        return tuple(round(coord / tolerance) for coord in point)

    vertex_to_triangles: dict[tuple[int, int, int], list[int]] = defaultdict(list)
    for tri_index, triangle in enumerate(triangles):
        for point in triangle:
            vertex_to_triangles[key(point)].append(tri_index)

    neighbors: list[set[int]] = [set() for _ in triangles]
    for linked_triangles in vertex_to_triangles.values():
        for tri_index in linked_triangles:
            neighbors[tri_index].update(linked_triangles)

    remaining = set(range(len(triangles)))
    components = 0
    while remaining:
        components += 1
        queue = deque([remaining.pop()])
        while queue:
            current = queue.popleft()
            for neighbor in neighbors[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
    return components


def assert_close(actual: float, expected: float, label: str, tolerance: float = 0.15) -> None:
    if not math.isclose(actual, expected, abs_tol=tolerance):
        raise AssertionError(f"{label}: expected {expected:.2f}, got {actual:.2f}")


def rotate_x(point: tuple[float, float, float], radians: float) -> tuple[float, float, float]:
    x, y, z = point
    c = math.cos(radians)
    s = math.sin(radians)
    return (x, y * c - z * s, y * s + z * c)


def add_points(
    left: tuple[float, float, float], right: tuple[float, float, float]
) -> tuple[float, float, float]:
    return tuple(left[i] + right[i] for i in range(3))


def subtract_points(
    left: tuple[float, float, float], right: tuple[float, float, float]
) -> tuple[float, float, float]:
    return tuple(left[i] - right[i] for i in range(3))


def write_obj(
    path: Path, triangles: list[tuple[tuple[float, float, float], ...]]
) -> None:
    with path.open("w") as file:
        for triangle in triangles:
            for x, y, z in triangle:
                file.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
        for index in range(len(triangles)):
            first_vertex = index * 3 + 1
            file.write(
                f"f {first_vertex} {first_vertex + 1} {first_vertex + 2}\n"
            )


def run_closed_overlap_check() -> None:
    with tempfile.TemporaryDirectory(prefix="quena_case_overlap_") as temp_dir:
        temp_path = Path(temp_dir)
        scad_path = temp_path / "closed_overlap.scad"
        overlap_stl = temp_path / "closed_overlap.stl"
        scad_path.write_text(
            f"""
include <{ROOT / "QuenaCase.scad"}>;
intersection() {{
  bottom_assembly();
  translate([0, 0, lid_closed_z]) lid_assembly();
}}
""".lstrip(),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                "openscad",
                "-D",
                'part="none"',
                "-o",
                str(overlap_stl),
                str(scad_path),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if "Current top level object is empty" in result.stdout:
            print("QuenaCase closed overlap: ok, OpenSCAD intersection is empty")
            return
        if result.returncode:
            raise AssertionError(
                "QuenaCase closed overlap: OpenSCAD failed\n" + result.stdout
            )
        if not overlap_stl.exists() or overlap_stl.stat().st_size <= 84:
            print("QuenaCase closed overlap: ok, OpenSCAD intersection is empty")
            return

        overlap = trimesh.load(overlap_stl, force="mesh")
        volume = abs(float(overlap.volume))
        if volume > CLOSED_OVERLAP_VOLUME_TOLERANCE_MM3:
            raise AssertionError(
                "QuenaCase closed overlap: "
                f"{volume:.3f} mm^3 intersection, bounds={overlap.bounds.tolist()}"
            )

        print(f"QuenaCase closed overlap: ok, {volume:.3f} mm^3")


def run_mesh_checks() -> None:
    stale_exports = [name for name in OBSOLETE_SPLIT_EXPORTS if (ROOT / name).exists()]
    if stale_exports:
        raise AssertionError(
            "obsolete C-bearing half exports remain: " + ", ".join(stale_exports)
        )

    for name, expected in EXPECTED.items():
        path = ROOT / name
        if not path.exists():
            raise AssertionError(f"{name}: missing; render it with openscad first")
        if path.stat().st_size < 10_000:
            raise AssertionError(f"{name}: unexpectedly small STL")

        triangles = read_stl_triangles(path)
        if len(triangles) < expected["min_triangles"]:
            raise AssertionError(
                f"{name}: expected at least {expected['min_triangles']} triangles, "
                f"got {len(triangles)}"
            )

        mins, maxs = bounds(triangles)
        size = tuple(maxs[i] - mins[i] for i in range(3))
        for axis, actual, target in zip("xyz", size, expected["size"]):
            assert_close(actual, target, f"{name} {axis} size")

        components = component_count(triangles)
        if components != expected["components"]:
            raise AssertionError(
                f"{name}: expected {expected['components']} connected mesh components, "
                f"got {components}"
            )

        if name == "QuenaCasePrintInPlace.stl":
            print_mesh = trimesh.load(path, force="mesh")
            moving_halves = print_mesh.split(only_watertight=False)
            if len(moving_halves) != 2:
                raise AssertionError("print-in-place export must contain two moving bodies")
            if any(abs(float(half.bounds[0][2])) > 0.02 for half in moving_halves):
                raise AssertionError("both print-in-place shell backs must touch Z=0")
            if size[0] > 256 or size[1] > 256:
                raise AssertionError("print-in-place export exceeds the 256 mm target bed")

            # The production STL must contain both complete case halves, not a
            # hinge-only assembly or cropped coupon. Rigid print-pose transforms
            # preserve each source mesh's face count and enclosed volume.
            source_halves = [
                trimesh.load(ROOT / "QuenaCaseBottomViewer.stl", force="mesh"),
                trimesh.load(ROOT / "QuenaCaseLidViewer.stl", force="mesh"),
            ]
            production_halves = sorted(moving_halves, key=lambda half: len(half.faces))
            source_halves.sort(key=lambda half: len(half.faces))
            complete = all(
                len(production.faces) == len(source.faces)
                and math.isclose(
                    abs(float(production.volume)),
                    abs(float(source.volume)),
                    abs_tol=PRINT_POSE_VOLUME_TOLERANCE_MM3,
                )
                for production, source in zip(production_halves, source_halves)
            )
            if not complete:
                raise AssertionError(
                    "print-in-place STL does not contain both complete case halves"
                )

        if name == "QuenaCaseBottomViewer.stl":
            # At the center bearing, a complete print-in-place knuckle has an
            # outer closed section and a second closed loop around its bore. A
            # radial C-slot merges those loops and must never return.
            bearing_section = trimesh.load(path, force="mesh").section(
                plane_origin=[0, 0, 0], plane_normal=[1, 0, 0]
            )
            if bearing_section is None:
                raise AssertionError("central hinge bearing section is missing")
            bearing_path, _ = bearing_section.to_2D()
            closed_loops = sum(entity.closed for entity in bearing_path.entities)
            if closed_loops < 2:
                raise AssertionError("central hinge bearing is radially C-shaped")

        print(
            f"{name}: ok, {len(triangles)} triangles, "
            f"{size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm, "
            f"{components} components"
        )

    case_volume = sum(
        abs(float(trimesh.load(ROOT / name, force="mesh").volume))
        for name in ("QuenaCaseBottomViewer.stl", "QuenaCaseLidViewer.stl")
    )
    volume_delta = case_volume - EXPECTED_CASE_VOLUME_MM3
    if abs(volume_delta) > CASE_VOLUME_TOLERANCE_MM3:
        raise AssertionError(
            "total case volume differs from the canonical geometry by "
            f"{volume_delta:+.1f} mm^3"
        )
    print(
        "QuenaCase volume: ok, "
        f"{case_volume:.1f} mm^3 ({volume_delta:+.1f} mm^3 from reference)"
    )


def run_color_project_checks() -> None:
    subprocess.run(
        ["python3", str(ROOT / "tools" / "vectorize_case_logo.py"), "--check"],
        cwd=ROOT,
        check=True,
    )
    artwork = trimesh.load(ROOT / "QuenaCaseArtwork.stl", force="mesh")
    if not artwork.is_watertight or not artwork.is_winding_consistent:
        raise AssertionError("case artwork must be a watertight, consistently wound mesh")
    if not math.isclose(float(artwork.bounds[0][2]), 0.0, abs_tol=0.01):
        raise AssertionError("case artwork must start on the build plate")
    if not math.isclose(float(artwork.bounds[1][2]), 0.6, abs_tol=0.01):
        raise AssertionError("case logo must occupy exactly three 0.2 mm layers")
    logo_parts = [
        component
        for component in artwork.split(only_watertight=False)
        if float(component.bounds[1][2]) > 0.5
    ]
    logo = trimesh.util.concatenate(logo_parts)

    case_outer_l = scad_scalar("case_outer_l")
    case_outer_w = scad_scalar("case_outer_w")
    hinge_axis_y = scad_scalar("hinge_axis_y")
    shell_bounds = (
        (-case_outer_l / 2, 2 * hinge_axis_y - case_outer_w / 2),
        (case_outer_l / 2, 2 * hinge_axis_y + case_outer_w / 2),
    )
    edge_margin = scad_scalar("logo_edge_margin")
    for axis in range(2):
        low_margin = float(logo.bounds[0][axis]) - shell_bounds[0][axis]
        high_margin = shell_bounds[1][axis] - float(logo.bounds[1][axis])
        if min(low_margin, high_margin) < edge_margin - 0.05:
            raise AssertionError("case logo does not maintain its specified lid-edge margin")

    with tempfile.TemporaryDirectory(prefix="quena_logo_fit_") as temp_dir:
        temp_path = Path(temp_dir)
        solid_scad = temp_path / "solid_case.scad"
        solid_stl = temp_path / "solid_case.stl"
        solid_scad.write_text(
            f'include <{ROOT / "QuenaCase.scad"}>;\n'
            "bottom_assembly(false);\n"
            "lid_in_print_pose() lid_assembly(false);\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["openscad", "-D", 'part="none"', "-o", str(solid_stl), str(solid_scad)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        solid_case = trimesh.load(solid_stl, force="mesh")
    recessed_case = trimesh.load(ROOT / "QuenaCasePrintInPlace.stl", force="mesh")
    recess_volume = float(solid_case.volume - recessed_case.volume)
    # Independent curved-shell and artwork STL tessellations accumulate a
    # small volume-integration difference even though both are generated from
    # the same OpenSCAD recess modules. Keep the allowance below 0.5%.
    artwork_volume = float(artwork.volume)
    if not math.isclose(
        recess_volume,
        artwork_volume,
        abs_tol=max(0.2, artwork_volume * 0.005),
    ):
        raise AssertionError(
            "case artwork does not exactly fill the production recesses: "
            f"recess={recess_volume:.3f} mm^3, artwork={artwork_volume:.3f} mm^3"
        )

    project = ROOT / "QuenaCase.3mf"
    with zipfile.ZipFile(project) as archive:
        corrupt_member = archive.testzip()
        if corrupt_member is not None:
            raise AssertionError(f"case 3MF has a corrupt member: {corrupt_member}")
        names = set(archive.namelist())
        required = {
            "3D/3dmodel.model",
            "Metadata/model_settings.config",
            "Metadata/project_settings.config",
        }
        if not required <= names:
            raise AssertionError("case 3MF is missing model or slicer metadata")
        model = archive.read("3D/3dmodel.model").decode("utf-8")
        metadata = archive.read("Metadata/model_settings.config").decode("utf-8")
        settings = json.loads(archive.read("Metadata/project_settings.config"))
    if "BambuStudio:3mfVersion" not in model:
        raise AssertionError("case 3MF was not authored in Bambu Studio format")
    if "3D/Objects/object_1.model" not in names:
        raise AssertionError("case 3MF is missing its Bambu Studio object model")
    for current_name in ("QuenaCasePrintInPlace.stl", "QuenaCaseArtwork.stl"):
        if current_name not in metadata:
            raise AssertionError(f"case 3MF is missing {current_name}")
    for obsolete_name in ("QuenaCaseBottom.stl", "QuenaCaseLid.stl"):
        if obsolete_name in metadata or obsolete_name in model:
            raise AssertionError(f"case 3MF still contains obsolete {obsolete_name}")
    if 'key="extruder" value="1"' not in metadata or 'key="extruder" value="2"' not in metadata:
        raise AssertionError("case 3MF does not map its two parts to separate filaments")
    if settings.get("enable_support") != "0" or settings.get("brim_type") != "no_brim":
        raise AssertionError("case 3MF must disable supports and brims")
    if settings.get("filament_type") != ["ABS", "ABS"]:
        raise AssertionError("case 3MF materials must both be ABS")
    if settings.get("filament_colour") != ["#FFF144", "#000000"]:
        raise AssertionError("case 3MF materials must be yellow and black")
    if settings.get("prime_tower_width") != "20":
        raise AssertionError("case 3MF prime tower must use the compact 20 mm width")
    if settings.get("wipe_tower_no_sparse_layers") != "1":
        raise AssertionError("case 3MF prime tower must omit inactive upper layers")
    metadata_root = ET.fromstring(metadata)
    project_face_counts = sorted(
        int(node.attrib["face_count"])
        for node in metadata_root.findall("./object/part/mesh_stat")
    )
    source_face_counts = sorted(
        len(trimesh.load(ROOT / name, force="mesh").faces)
        for name in ("QuenaCasePrintInPlace.stl", "QuenaCaseArtwork.stl")
    )
    if project_face_counts != source_face_counts:
        raise AssertionError("case 3MF meshes differ from the canonical STL inputs")
    if 'transform="1 0 0 0 1 0 0 0 1 128 156.685 0"' not in model:
        raise AssertionError("case 3MF is not centered in the validated P1S plate pose")
    print(
        "QuenaCase colour project: ok, exact selected artwork traced for a 0.4 mm "
        "nozzle, black mandala and logo inlays, compact lower-layer prime tower"
    )

def run_hinge_sweep_check() -> None:
    try:
        import pybullet as p
    except ImportError:
        print("QuenaCase hinge sweep: skipped, install pybullet to enable")
        return

    hinge_axis_y, hinge_axis_z, lid_closed_z = evaluated_hinge_pose()
    hinge_axis = (0.0, hinge_axis_y, hinge_axis_z)
    closed_lid_position = (0.0, 0.0, lid_closed_z)

    physics_client = p.connect(p.DIRECT)
    try:
        p.setGravity(0, 0, -9.81)
        p.setPhysicsEngineParameter(
            contactBreakingThreshold=CONTACT_TOLERANCE_MM,
            deterministicOverlappingPairs=1,
        )

        with tempfile.TemporaryDirectory(prefix="quena_case_mesh_") as temp_dir:
            temp_path = Path(temp_dir)
            support_free_scad = temp_path / "support_free_lid.scad"
            support_free_lid = temp_path / "support_free_lid.stl"
            validation_bottom_scad = temp_path / "validation_bottom.scad"
            validation_bottom = temp_path / "validation_bottom.stl"
            stored_parts_scad = temp_path / "stored_parts.scad"
            stored_parts_stl = temp_path / "stored_parts.stl"
            support_free_scad.write_text(
                f'include <{ROOT / "QuenaCase.scad"}>;\nlid_assembly();\n',
                encoding="utf-8",
            )
            subprocess.run(
                [
                    "openscad",
                    "-D",
                    'part="none"',
                    "-o",
                    str(support_free_lid),
                    str(support_free_scad),
                ],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            validation_bottom_scad.write_text(
                f'include <{ROOT / "QuenaCase.scad"}>;\nbottom_assembly();\n',
                encoding="utf-8",
            )
            subprocess.run(
                [
                    "openscad",
                    "-D",
                    'part="none"',
                    "-o",
                    str(validation_bottom),
                    str(validation_bottom_scad),
                ],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            stored_parts_scad.write_text(
                f'include <{ROOT / "QuenaCase.scad"}>;\n'
                "stored_parts_proxy();\n",
                encoding="utf-8",
            )
            subprocess.run(
                [
                    "openscad",
                    "-D",
                    'part="none"',
                    "-o",
                    str(stored_parts_stl),
                    str(stored_parts_scad),
                ],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            bottom_triangles = read_stl_triangles(validation_bottom)
            lid_triangles = read_stl_triangles(support_free_lid)
            stored_parts_triangles = read_stl_triangles(stored_parts_stl)
            bottom_obj = temp_path / "bottom.obj"
            lid_obj = temp_path / "lid.obj"
            stored_parts_obj = temp_path / "stored_parts.obj"
            write_obj(bottom_obj, bottom_triangles)
            write_obj(lid_obj, lid_triangles)
            write_obj(stored_parts_obj, stored_parts_triangles)

            mesh_flags = p.GEOM_FORCE_CONCAVE_TRIMESH
            bottom_collision = p.createCollisionShape(
                p.GEOM_MESH,
                fileName=str(bottom_obj),
                flags=mesh_flags,
            )
            lid_collision = p.createCollisionShape(
                p.GEOM_MESH,
                fileName=str(lid_obj),
                flags=mesh_flags,
            )
            stored_parts_collision = p.createCollisionShape(
                p.GEOM_MESH,
                fileName=str(stored_parts_obj),
                flags=mesh_flags,
            )

            bottom_body = p.createMultiBody(
                baseMass=0,
                baseCollisionShapeIndex=bottom_collision,
                basePosition=[0, 0, 0],
            )
            lid_body = p.createMultiBody(
                baseMass=0,
                baseCollisionShapeIndex=lid_collision,
                basePosition=closed_lid_position,
            )
            stored_parts_body = p.createMultiBody(
                baseMass=0,
                baseCollisionShapeIndex=stored_parts_collision,
                basePosition=[0, 0, 0],
            )

            # First verify the case halves alone.  Then repeat the complete
            # sweep with the stored parts at every extreme of their permitted
            # axial, lateral, and lidward clearances.  Treating the parts as
            # fixed rigid envelopes makes this deterministic and conservative
            # for interference; inversion/drop behavior is tested separately.
            for deg in range(LID_SWEEP_MAX_DEG + 1):
                radians = math.radians(deg)
                hinge_to_lid = subtract_points(closed_lid_position, hinge_axis)
                lid_position = add_points(hinge_axis, rotate_x(hinge_to_lid, radians))
                lid_orientation = p.getQuaternionFromEuler([radians, 0, 0])

                p.resetBasePositionAndOrientation(lid_body, lid_position, lid_orientation)
                p.performCollisionDetection()

                penetrating_contacts: list[Any] = [
                    contact
                    for contact in p.getContactPoints(bottom_body, lid_body)
                    if contact[8] <= -CONTACT_TOLERANCE_MM
                ]
                if penetrating_contacts:
                    deepest = min(contact[8] for contact in penetrating_contacts)
                    raise AssertionError(
                        "QuenaCase hinge sweep: collision at "
                        f"{deg} deg, {len(penetrating_contacts)} contacts, "
                        f"deepest penetration {-deepest:.3f} mm"
                    )

            axial_limit = scad_scalar("axial_clearance") / 2
            radial_limit = scad_scalar("part_clearance")
            clearance_poses = [
                (x, y, z)
                for x in (-axial_limit, 0.0, axial_limit)
                for y in (-radial_limit, 0.0, radial_limit)
                for z in (0.0, radial_limit)
            ]
            for flute_position in clearance_poses:
                p.resetBasePositionAndOrientation(
                    stored_parts_body, flute_position, [0, 0, 0, 1]
                )
                for deg in range(LID_SWEEP_MAX_DEG + 1):
                    radians = math.radians(deg)
                    hinge_to_lid = subtract_points(closed_lid_position, hinge_axis)
                    lid_position = add_points(
                        hinge_axis, rotate_x(hinge_to_lid, radians)
                    )
                    lid_orientation = p.getQuaternionFromEuler([radians, 0, 0])
                    p.resetBasePositionAndOrientation(
                        lid_body, lid_position, lid_orientation
                    )
                    p.performCollisionDetection()
                    contacts = [
                        contact
                        for contact in p.getContactPoints(lid_body, stored_parts_body)
                        if contact[8] <= -CONTACT_TOLERANCE_MM
                    ]
                    if contacts:
                        deepest = min(contact[8] for contact in contacts)
                        raise AssertionError(
                            "QuenaCase loaded hinge sweep: flute/lid collision at "
                            f"{deg} deg with flute offset {flute_position}, "
                            f"{len(contacts)} contacts, deepest penetration "
                            f"{-deepest:.3f} mm"
                        )

        print(
            "QuenaCase hinge sweep: ok, "
            f"0-{LID_SWEEP_MAX_DEG} deg around "
            f"({hinge_axis[0]:.2f}, {hinge_axis[1]:.2f}, {hinge_axis[2]:.2f})"
        )
        print(
            "QuenaCase loaded hinge sweep: ok, 3 stored-part envelopes, "
            f"{len(clearance_poses)} clearance-limit poses, "
            f"0-{LID_SWEEP_MAX_DEG} deg"
        )
    finally:
        p.disconnect(physics_client)


def main() -> None:
    run_hinge_design_checks()
    run_hinge_end_roundness_check()
    run_stator_roundness_check()
    run_latch_design_checks()
    run_channel_layout_checks()
    run_exterior_design_checks()
    run_mesh_checks()
    run_color_project_checks()
    run_closed_overlap_check()
    run_hinge_sweep_check()


if __name__ == "__main__":
    main()
