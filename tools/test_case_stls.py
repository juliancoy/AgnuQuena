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
        "size": (211.704, 211.704, 18.7),
        "min_triangles": 2200,
        "components": 1,
    },
    "QuenaCaseLid.stl": {
        "size": (211.704, 211.704, 17.198),
        "min_triangles": 1200,
        "components": 1,
    },
    "QuenaCaseBottomViewer.stl": {
        "size": (251.494, 59.553, 18.7),
        "min_triangles": 2200,
        "components": 1,
    },
    "QuenaCaseLidViewer.stl": {
        "size": (251.494, 59.17, 17.198),
        "min_triangles": 1200,
        "components": 1,
    },
    "QuenaCaseLidLogo.stl": {
        "size": (139.4049, 141.7288, 0.6),
        "min_triangles": 5000,
        "components": 21,
    },
    "QuenaCaseHingeCoupon.stl": {
        "size": (72.0, 54.1, 15.4),
        "min_triangles": 3000,
        "components": 2,
    },
    "QuenaCaseFullHingeCoupon.stl": {
        "size": (243.5, 57.153, 15.4),
        "min_triangles": 2000,
        "components": 2,
    },
    "QuenaCaseLatchCoupon.stl": {
        "size": (180.0, 34.0, 14.0),
        "min_triangles": 1600,
        "components": 7,
    },
    "QuenaCaseAssembly.stl": {
        "size": (251.494, 60.223, 28.8),
        "min_triangles": 4500,
        "components": 2,
    },
}

LID_SWEEP_MAX_DEG = 180
CONTACT_TOLERANCE_MM = 0.05
CLOSED_OVERLAP_VOLUME_TOLERANCE_MM3 = 0.1


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
    snap_throat = scad_scalar("hinge_snap_throat")
    segment_w = scad_scalar("hinge_segment_w")
    segment_gap = scad_scalar("hinge_segment_gap")
    print_flat = scad_scalar("hinge_axle_print_flat")
    body_inset = scad_scalar("hinge_body_inset")

    bearing_wall = (outer_d - bore_d) / 2
    snap_interference = axle_d - snap_throat
    rear_projection = outer_d - body_inset

    if not 4.2 <= axle_d <= 5.0:
        raise AssertionError("integral hinge axle diameter is unsuitable")
    if not 0.25 <= bore_clearance <= 0.45:
        raise AssertionError(
            f"hinge bore clearance {bore_clearance:.2f} mm is outside 0.25-0.45 mm"
        )
    if bearing_wall < 1.3:
        raise AssertionError(f"hinge bearing wall is only {bearing_wall:.2f} mm")
    if not 0.7 <= snap_interference <= 1.0:
        raise AssertionError("hinge snap throat does not provide positive capture")
    if not 10.0 <= segment_w <= 18.0:
        raise AssertionError("hinge bearing segments are not independently compliant")
    if not 0.8 <= segment_gap <= 1.4:
        raise AssertionError("hinge segment gap is unsuitable for FDM assembly")
    if not 0.5 <= print_flat <= 0.8:
        raise AssertionError("hinge axle D-flat is unsuitable for support-free printing")
    if not 4.0 <= body_inset <= 4.3:
        raise AssertionError("hinge body inset must retain rotational clearance")
    if rear_projection > 4.5:
        raise AssertionError(f"hinge rear projection is {rear_projection:.2f} mm")

    print(
        "QuenaCase hinge design: ok, "
        f"{axle_d:.2f} mm integral D-flat axle, {bore_d:.2f} mm bearing bore, "
        f"{bearing_wall:.2f} mm bearing wall, {snap_interference:.2f} mm "
        f"snap interference, {segment_w:.1f} mm independent clips, "
        f"{rear_projection:.2f} mm rear projection, web-captured ends, "
        "support-free exports"
    )


def run_latch_design_checks() -> None:
    protrusion = scad_scalar("latch_nub_protrusion")
    indent = scad_scalar("latch_indent_depth")
    tongue_t = scad_scalar("latch_tongue_t")
    flex_l = scad_scalar("latch_tongue_flex_l")
    travel = protrusion - indent
    if not 0.20 <= travel <= 0.45:
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
    connector_d = tube_d + 2 * (
        scad_scalar("shell_width") + scad_scalar("connector_radial_clearance")
    )
    max_channel_d = connector_d + 2 * scad_scalar("part_clearance")
    equator_pass = scad_scalar("equator_pass")
    axial_clearance = scad_scalar("axial_clearance")
    radial_clearance = scad_scalar("part_clearance")

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

    if horizontal_land < 8.0:
        raise AssertionError(
            f"horizontal channel land is only {horizontal_land:.2f} mm"
        )
    if vertical_land < 2.5:
        raise AssertionError(f"vertical channel land is only {vertical_land:.2f} mm")
    if edge_land < 2.5:
        raise AssertionError(f"channel perimeter land is only {edge_land:.2f} mm")
    print(
        "QuenaCase channel layout: ok, "
        f"{horizontal_land:.1f} mm minimum horizontal distribution gap, "
        f"{vertical_land:.1f} mm vertical land, "
        f"{edge_land:.1f} mm perimeter land, "
        f"{deck_h:.2f} mm single raised bed, "
        f"{equator_pass:.2f} mm past equator, "
        f"{axial_clearance:.2f} mm axial and {radial_clearance:.2f} mm radial clearance"
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
    run_latch_design_checks()
    run_channel_layout_checks()
    run_mesh_checks()
    run_closed_overlap_check()
    run_hinge_sweep_check()


if __name__ == "__main__":
    main()
