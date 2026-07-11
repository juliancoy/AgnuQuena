#!/usr/bin/env python3
"""Validate rendered AgnuQuena case STL files.

These tests intentionally inspect the exported meshes, not only the OpenSCAD
source, so they catch render regressions before slicing.
"""

from __future__ import annotations

import math
import re
import struct
import subprocess
import tempfile
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import trimesh


ROOT = Path(__file__).resolve().parents[1]

EXPECTED = {
    "QuenaCaseBottom.stl": {
        "size": (260.6, 76.8, 26.05),
        "min_triangles": 2200,
        "components": 1,
    },
    "QuenaCaseLid.stl": {
        "size": (260.6, 76.8, 20.2),
        "min_triangles": 1200,
        "components": 1,
    },
    "QuenaCaseHingeCoupon.stl": {
        "size": (116.0, 55.2, 13.8),
        "min_triangles": 3000,
        "components": 2,
    },
    "QuenaCaseFullHingeCoupon.stl": {
        "size": (242.6, 57.2, 13.8),
        "min_triangles": 2000,
        "components": 2,
    },
    "QuenaCaseLatchCoupon.stl": {
        "size": (200.0, 34.0, 12.0),
        "min_triangles": 1600,
        "components": 2,
    },
    "QuenaCaseAssembly.stl": {
        "size": (260.6, 76.8, 37.0),
        "min_triangles": 4500,
        "components": 2,
    },
}

LID_SWEEP_MAX_DEG = 140
CONTACT_TOLERANCE_MM = 0.05
CLOSED_OVERLAP_VOLUME_TOLERANCE_MM3 = 0.1


def scad_scalar(name: str) -> float:
    source = (ROOT / "QuenaCase.scad").read_text(encoding="utf-8")
    match = re.search(
        rf"^\s*{re.escape(name)}\s*=\s*([-+]?\d+(?:\.\d+)?)\s*;",
        source,
        flags=re.MULTILINE,
    )
    if not match:
        raise AssertionError(f"QuenaCase.scad: missing numeric parameter {name}")
    return float(match.group(1))


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
    socket_clearance = scad_scalar("hinge_socket_clearance")
    outer_d = scad_scalar("hinge_outer_d")
    nub_l = scad_scalar("hinge_nub_l")
    tip_l = scad_scalar("hinge_pin_tip_l")
    tip_r = scad_scalar("hinge_pin_tip_r")
    socket_depth = scad_scalar("hinge_socket_depth")
    knuckle_gap = scad_scalar("hinge_gap")
    stator_closed = scad_scalar("hinge_stator_closed")
    backer_extension = scad_scalar("hinge_backer_extension")
    nub_support_y = scad_scalar("hinge_nub_support_y")
    nub_support_gap = scad_scalar("hinge_nub_support_gap")
    nub_support_overlap = scad_scalar("hinge_nub_support_base_overlap")

    socket_d = axle_d + socket_clearance
    socket_wall = (outer_d - socket_d) / 2
    pin_engagement = nub_l - knuckle_gap
    full_diameter_engagement = pin_engagement - tip_l
    axial_reserve = socket_depth - pin_engagement

    if not 0.25 <= socket_clearance <= 0.55:
        raise AssertionError(
            f"hinge diametral clearance {socket_clearance:.2f} mm is outside 0.25-0.55 mm"
        )
    if socket_wall < 1.5:
        raise AssertionError(f"hinge socket wall is only {socket_wall:.2f} mm")
    if axial_reserve < 1.0:
        raise AssertionError(f"hinge axial reserve is only {axial_reserve:.2f} mm")
    if pin_engagement < 1.8:
        raise AssertionError(f"hinge pin engagement is only {pin_engagement:.2f} mm")
    if full_diameter_engagement + 1e-9 < 1.2:
        raise AssertionError(
            "hinge full-diameter bearing engagement is only "
            f"{full_diameter_engagement:.2f} mm"
        )
    if not 0 < tip_l < nub_l:
        raise AssertionError("hinge pin taper length must be shorter than the pin")
    if not 0 < tip_r <= tip_l / 2:
        raise AssertionError("hinge pin nose radius must fit within the lead-in length")
    if stator_closed != 1:
        raise AssertionError("hinge outer stator must remain closed")
    if not 0.8 <= backer_extension <= 1.5:
        raise AssertionError("hinge rectangular backer extension is out of range")
    if not 0.8 <= nub_support_y <= 1.2:
        raise AssertionError("hinge nub support blade width is out of range")
    if not 0.15 <= nub_support_gap <= 0.3:
        raise AssertionError("hinge nub support gap must be about one layer")
    if nub_support_overlap < 0.1:
        raise AssertionError("hinge nub support blades lack base overlap")

    print(
        "QuenaCase hinge design: ok, "
        f"{socket_clearance:.2f} mm diametral clearance, "
        f"{socket_wall:.2f} mm socket wall, "
        f"{pin_engagement:.2f} mm pin engagement, "
        f"{full_diameter_engagement:.2f} mm full-diameter bearing, "
        f"{axial_reserve:.2f} mm axial reserve, closed stator, "
        f"{backer_extension:.1f} mm backer extension, nub breakaway blades"
    )


def run_latch_design_checks() -> None:
    protrusion = scad_scalar("latch_nub_protrusion")
    indent = scad_scalar("latch_indent_depth")
    tongue_t = scad_scalar("latch_tongue_t")
    flex_l = scad_scalar("latch_tongue_flex_l")
    travel = protrusion - indent
    if not 0.15 <= travel <= 0.40:
        raise AssertionError(f"latch release travel {travel:.2f} mm is unsuitable")
    if tongue_t < 1.2 or flex_l < 7.0:
        raise AssertionError("latch tongue is too thin or too short")
    print(f"QuenaCase latch design: ok, {protrusion:.2f} mm nub projection, "
          f"{indent:.2f} mm recess, {travel:.2f} mm release travel, "
          f"{tongue_t:.2f} x {flex_l:.2f} mm flex section")


def run_channel_layout_checks() -> None:
    horizontal_land = scad_scalar("short_row_min_gap")
    vertical_land = scad_scalar("row_gap")
    edge_land = scad_scalar("channel_edge_land")
    deck_h = scad_scalar("channel_deck_h")
    tube_d = scad_scalar("id") + 2 * scad_scalar("shell_width")
    channel_d = tube_d + 2 * scad_scalar("part_clearance")
    connector_d = tube_d + 2 * scad_scalar("shell_width")
    max_channel_d = connector_d + 2 * scad_scalar("part_clearance")
    deck_below_center = max_channel_d / 2 - deck_h
    deck_opening = 2 * math.sqrt(
        max((channel_d / 2) ** 2 - deck_below_center**2, 0)
    )

    source = (ROOT / "QuenaCase.scad").read_text(encoding="utf-8")
    if "module cantilever_retainer(i, x_center, clip_w)" not in source:
        raise AssertionError("channels lack localized cantilever retainers")
    clip_t = scad_scalar("retainer_clip_t")
    clip_l = scad_scalar("retainer_clip_flex_l")
    clip_interference = scad_scalar("retainer_clip_interference")
    clip_strain = 1.5 * clip_t * clip_interference / clip_l**2
    if clip_strain > 0.015:
        raise AssertionError(
            f"ABS retainer clip strain is too high: {100*clip_strain:.2f}%"
        )

    if horizontal_land < 8.0:
        raise AssertionError(
            f"horizontal channel land is only {horizontal_land:.2f} mm"
        )
    if vertical_land < 6.0:
        raise AssertionError(f"vertical channel land is only {vertical_land:.2f} mm")
    if edge_land < 4.0:
        raise AssertionError(f"channel perimeter land is only {edge_land:.2f} mm")
    if deck_h < 0.8:
        raise AssertionError(f"channel filler deck is only {deck_h:.2f} mm thick")
    if deck_below_center <= 0 or deck_opening < tube_d + 0.3:
        raise AssertionError(
            f"raised bed obstructs insertion: {deck_opening:.2f} mm opening for "
            f"{tube_d:.2f} mm tube"
        )

    print(
        "QuenaCase channel layout: ok, "
        f"{horizontal_land:.1f} mm minimum horizontal distribution gap, "
        f"{vertical_land:.1f} mm vertical land, "
        f"{edge_land:.1f} mm perimeter land, "
        f"{deck_h:.1f} mm raised bed, "
        f"{deck_opening:.2f} mm opening at bed edge, "
        f"ABS cantilever clip strain {100*clip_strain:.2f}%"
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

        print(
            f"{name}: ok, {len(triangles)} triangles, "
            f"{size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm, "
            f"{components} components"
        )


def run_hinge_sweep_check() -> None:
    try:
        import pybullet as p
    except ImportError:
        print("QuenaCase hinge sweep: skipped, install pybullet to enable")
        return

    bottom_path = ROOT / "QuenaCaseBottom.stl"
    lid_path = ROOT / "QuenaCaseLid.stl"
    for path in (bottom_path, lid_path):
        if not path.exists():
            raise AssertionError(f"{path.name}: missing; render it with openscad first")

    bottom_triangles = read_stl_triangles(bottom_path)
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
            lid_triangles = read_stl_triangles(support_free_lid)
            bottom_obj = temp_path / "bottom.obj"
            lid_obj = temp_path / "lid.obj"
            write_obj(bottom_obj, bottom_triangles)
            write_obj(lid_obj, lid_triangles)

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

        print(
            "QuenaCase hinge sweep: ok, "
            f"0-{LID_SWEEP_MAX_DEG} deg around "
            f"({hinge_axis[0]:.2f}, {hinge_axis[1]:.2f}, {hinge_axis[2]:.2f})"
        )
    finally:
        p.disconnect(physics_client)


def main() -> None:
    run_hinge_design_checks()
    run_latch_design_checks()
    run_channel_layout_checks()
    run_mesh_checks()
    run_closed_overlap_check()
    run_hinge_sweep_check()


if __name__ == "__main__":
    main()
