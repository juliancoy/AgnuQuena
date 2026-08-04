#!/usr/bin/env python3
"""Render selected AgnuQuena case meshes and optional review sheets."""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image
import trimesh


ROOT = Path(__file__).resolve().parents[1]
OPENSCAD = Path(os.environ.get("AGNUQUENA_OPENSCAD", ROOT / "tools" / "openscad"))
OPENSCAD_DOCKERFILE = ROOT / "tools" / "openscad.Dockerfile"
OPENSCAD_SOURCE = ROOT / "openscad" / "CMakeLists.txt"
SCAD = ROOT / "QuenaCase.scad"
RENDERER = Path(__file__).resolve()
LOGO_VECTORIZER = ROOT / "tools" / "vectorize_case_logo.py"
STL_WORKERS = 4

MESHES = [
    # Canonical production export: both exterior backs on the bed, with the
    # captive hinge already assembled at 180 degrees.
    ("print_in_place", ROOT / "QuenaCasePrintInPlace.stl", True),
    # Two-color body with one 0.2 mm decoration recess. The deeper canonical
    # body above remains the single-filament engraved export.
    (
        "print_in_place_two_color",
        ROOT / "QuenaCaseTwoColorPrintInPlace.stl",
        True,
    ),
    # Canonical model-space components are shared by engineering validation
    # and the browser. A separate print-pose STL is unavoidable because its
    # lid is rigidly rotated 180 degrees onto the build plate.
    ("bottom", ROOT / "QuenaCaseBottom.stl", True),
    ("lid", ROOT / "QuenaCaseLid.stl", True),
    ("case_logo", ROOT / "QuenaCaseLogo.stl", True),
    ("case_engraving", ROOT / "QuenaCaseEngraving.stl", True),
    ("case_artwork_print", ROOT / "QuenaCaseArtwork.stl", True),
    ("assembly", ROOT / "QuenaCaseAssembly.stl", True),
]

VIEWS = [
    ("assembly", ROOT / "QuenaCaseAssembly_9views.png"),
    ("print_in_place", ROOT / "QuenaCasePrintInPlace_9views.png"),
    ("lid_hinge_closeup", ROOT / "QuenaCaseLidHingeCloseup_9views.png"),
]

DEFAULT_MESH = "print_in_place"
MESH_BY_NAME = {part: (output, copy_to_site) for part, output, copy_to_site in MESHES}
VIEW_BY_NAME = {part: output for part, output in VIEWS}

CAMERAS = [
    "0,0,0,65,0,25,360",
    "0,0,0,90,0,0,360",
    "0,0,0,90,0,90,360",
    "0,0,0,90,0,180,360",
    "0,0,0,90,0,270,360",
    "0,0,0,0,0,0,360",
    "0,0,0,55,0,135,360",
    "0,0,0,55,0,225,360",
    "0,0,0,55,0,315,360",
]

LID_HINGE_CLOSEUP_CAMERAS = [
    "-40,-28.35,1.0,65,0,25,95",
    "-40,-28.35,1.0,90,0,0,95",
    "-40,-28.35,1.0,90,0,90,95",
    "0,-28.35,1.0,65,0,25,210",
    "0,-28.35,1.0,90,0,0,210",
    "0,-28.35,1.0,0,0,0,210",
    "40,-28.35,1.0,65,0,335,95",
    "40,-28.35,1.0,90,0,180,95",
    "40,-28.35,1.0,90,0,270,95",
]


def is_current(output: Path, dependencies: tuple[Path, ...]) -> bool:
    """Return whether output is at least as new as all of its inputs."""
    if not output.exists():
        return False
    output_mtime = output.stat().st_mtime_ns
    return all(output_mtime >= dependency.stat().st_mtime_ns
               for dependency in dependencies)


def run(command: list[str]) -> None:
    print(" ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def remove_triangulation_debris(path: Path) -> int:
    """Remove triangulation debris while preserving every printable solid."""
    mesh = trimesh.load(path, force="mesh")
    components = mesh.split(only_watertight=False)
    solids = []
    debris = []
    for component in components:
        if (
            component.is_watertight
            and len(component.faces) >= 4
            and abs(component.volume) > 1e-6
        ):
            solids.append(component)
        else:
            debris.append(component)
    removed = len(debris)
    if not solids:
        raise RuntimeError(f"{path.name}: OpenSCAD export contains no solid components")
    invalid = [
        component
        for component in debris
        if not (
            len(component.faces) <= 2
            or (
                component.is_watertight
                and len(component.faces) <= 4
                and abs(component.volume) <= 1e-6
            )
        )
    ]
    if invalid:
        raise RuntimeError(f"{path.name}: OpenSCAD export contains an open solid")
    if removed:
        cleaned = trimesh.util.concatenate(solids)
        ascii_stl = trimesh.exchange.stl.export_stl_ascii(cleaned)
        ascii_stl = ascii_stl.replace("solid \n", "solid mesh\n", 1)
        ascii_stl = ascii_stl.replace("endsolid \n", "endsolid mesh\n", 1)
        path.write_text(
            ascii_stl,
            encoding="ascii",
        )
    return removed


def render_stl(part: str, output: Path, *, force: bool = False) -> None:
    logo_inputs = (
        ROOT / "EurasianSynergyFlute_logo_2color.png",
        ROOT / "generated" / "case_logo_title.svg",
        ROOT / "generated" / "case_logo_map.svg",
        ROOT / "generated" / "case_logo_dimensions.scad",
    )
    artwork_parts = {
        "bottom",
        "case_artwork_print",
        "lid",
        "print_in_place",
        "print_in_place_two_color",
        "assembly",
    }
    dependencies = (
        SCAD,
        RENDERER,
        OPENSCAD,
        OPENSCAD_DOCKERFILE,
        OPENSCAD_SOURCE,
    ) + (
        logo_inputs if "logo" in part or part in artwork_parts else ()
    )
    if not force and is_current(output, dependencies):
        print(f"Skipping current STL: {output.relative_to(ROOT)}")
        return
    started = time.perf_counter()
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=output.parent,
        prefix=f".{output.stem}.",
        suffix=".stl",
    )
    os.close(file_descriptor)
    temporary = Path(temporary_name)
    try:
        run([
            str(OPENSCAD),
            "--backend=Manifold",
            "--export-format",
            "asciistl",
            "-D",
            f'part="{part}"',
            "-o",
            str(temporary),
            str(SCAD),
        ])
        removed = remove_triangulation_debris(temporary)
        if removed:
            print(f"Removed {removed} non-solid triangulation shells")
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    elapsed = time.perf_counter() - started
    print(f"Rendered {output.relative_to(ROOT)} in {elapsed:.1f}s")


def render_meshes(parts: list[str], *, force: bool = False) -> None:
    worker_count = min(STL_WORKERS, len(parts))
    print(f"Rendering {len(parts)} STL(s) with {worker_count} worker(s)")
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(
                render_stl, part, MESH_BY_NAME[part][0], force=force
            )
            for part in parts
        ]
        for future in futures:
            future.result()


def render_png(part: str, output: Path, camera: str) -> None:
    run([
        str(OPENSCAD),
        "-D",
        f'part="{part}"',
        "--colorscheme",
        "Cornfield",
        "--projection",
        "o",
        "--viewall",
        "--autocenter",
        "--imgsize",
        "500,367",
        "--camera",
        camera,
        "-o",
        str(output),
        str(SCAD),
    ])


def render_closeup_png(part: str, output: Path, camera: str) -> None:
    run([
        str(OPENSCAD),
        "-D",
        f'part="{part}"',
        "--colorscheme",
        "Cornfield",
        "--projection",
        "o",
        "--imgsize",
        "500,367",
        "--camera",
        camera,
        "-o",
        str(output),
        str(SCAD),
    ])


def render_view_sheet(part: str, output: Path, *, force: bool = False) -> None:
    if not force and is_current(output, (SCAD, RENDERER)):
        print(f"Skipping current view sheet: {output.relative_to(ROOT)}")
        return
    with tempfile.TemporaryDirectory(prefix=f"quena_{part}_views_") as temp_dir:
        temp_path = Path(temp_dir)
        frames = []
        closeup = part == "lid_hinge_closeup"
        cameras = LID_HINGE_CLOSEUP_CAMERAS if closeup else CAMERAS
        render_part = "lid" if closeup else part
        for index, camera in enumerate(cameras):
            frame = temp_path / f"{index:02d}.png"
            if closeup:
                render_closeup_png(render_part, frame, camera)
            else:
                render_png(render_part, frame, camera)
            frames.append(Image.open(frame).convert("RGB"))

        sheet = Image.new("RGB", (1500, 1101), (243, 243, 239))
        for index, frame in enumerate(frames):
            x = (index % 3) * 500
            y = (index // 3) * 367
            sheet.paste(frame, (x, y))
        sheet.save(output)
        print(output.relative_to(ROOT))


def copy_site_assets(parts: list[str]) -> None:
    for asset_dir in (
        ROOT / "website" / "assets",
        ROOT / "site-hosting" / "public" / "assets",
    ):
        asset_dir.mkdir(parents=True, exist_ok=True)
        for part in parts:
            output, copy_to_site = MESH_BY_NAME[part]
            if copy_to_site:
                target = asset_dir / output.name
                if not target.exists() or not filecmp.cmp(
                    output, target, shallow=False
                ):
                    shutil.copy2(output, target)
                    print(target.relative_to(ROOT))
                else:
                    print(f"Skipping identical site asset: {target.relative_to(ROOT)}")


def list_outputs() -> None:
    print("Meshes (select with --mesh NAME; repeat as needed):")
    for part, output, _ in MESHES:
        default = " [default]" if part == DEFAULT_MESH else " [optional]"
        print(f"  {part:<24} {output.name}{default}")
    print("Review sheets (all optional; select with --view NAME):")
    for part, output in VIEWS:
        print(f"  {part:<24} {output.name} [optional]")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mesh",
        action="append",
        choices=MESH_BY_NAME,
        help="render one mesh; may be repeated",
    )
    parser.add_argument(
        "--view",
        action="append",
        choices=VIEW_BY_NAME,
        help="render one nine-view PNG sheet; may be repeated",
    )
    parser.add_argument("--all-meshes", action="store_true", help="render every mesh")
    parser.add_argument("--all-views", action="store_true", help="render every review sheet")
    parser.add_argument("--list", action="store_true", help="list selectable outputs and exit")
    parser.add_argument("--force", action="store_true", help="regenerate current outputs")
    args = parser.parse_args()

    if args.list:
        list_outputs()
        return

    mesh_parts = list(MESH_BY_NAME) if args.all_meshes else (args.mesh or [])
    view_parts = list(VIEW_BY_NAME) if args.all_views else (args.view or [])
    if not mesh_parts and not view_parts:
        mesh_parts = [DEFAULT_MESH]

    if mesh_parts:
        run(["python3", str(LOGO_VECTORIZER)])
        render_meshes(mesh_parts, force=args.force)
        copy_site_assets(mesh_parts)

    if view_parts:
        for part in view_parts:
            output = VIEW_BY_NAME[part]
            render_view_sheet(part, output, force=args.force)


if __name__ == "__main__":
    main()
