#!/usr/bin/env python3
"""Render AgnuQuena case STLs and nine-view review sheets."""

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
PROJECT_BUILDER = ROOT / "tools" / "build_case_3mf.py"
STL_WORKERS = 4

STL_PARTS = [
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
    # Everything below is auxiliary validation/coupon output. The complete
    # printable case itself remains the single STL above. Browser mechanics
    # uses model-space meshes so rendering and collision share the exact hinge
    # coordinates without undoing print transforms.
    ("bottom", ROOT / "QuenaCaseBottomViewer.stl", True),
    ("lid", ROOT / "QuenaCaseLidViewer.stl", True),
    ("case_logo", ROOT / "QuenaCaseLogoViewer.stl", True),
    ("case_engraving_viewer", ROOT / "QuenaCaseEngravingViewer.stl", True),
    ("case_artwork_print", ROOT / "QuenaCaseArtwork.stl", True),
    ("hinge_coupon", ROOT / "QuenaCaseHingeCoupon.stl", False),
    ("full_hinge_coupon", ROOT / "QuenaCaseFullHingeCoupon.stl", False),
    ("latch_coupon", ROOT / "QuenaCaseLatchCoupon.stl", False),
    ("assembly", ROOT / "QuenaCaseAssembly.stl", True),
]

VIEW_SHEETS = [
    ("assembly", ROOT / "QuenaCaseAssembly_9views.png"),
    ("print_in_place", ROOT / "QuenaCasePrintInPlace_9views.png"),
    ("lid_hinge_closeup", ROOT / "QuenaCaseLidHingeCloseup_9views.png"),
    ("hinge_coupon", ROOT / "QuenaCaseHingeCoupon_9views.png"),
    ("full_hinge_coupon", ROOT / "QuenaCaseFullHingeCoupon_9views.png"),
    ("latch_coupon", ROOT / "QuenaCaseLatchCoupon_9views.png"),
]

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


def render_all_stls(*, force: bool = False) -> None:
    worker_count = min(STL_WORKERS, len(STL_PARTS))
    print(f"Rendering {len(STL_PARTS)} STLs with {worker_count} workers")
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(render_stl, part, output, force=force)
            for part, output, _ in STL_PARTS
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


def copy_site_assets() -> None:
    for asset_dir in (
        ROOT / "website" / "assets",
        ROOT / "site-hosting" / "public" / "assets",
    ):
        asset_dir.mkdir(parents=True, exist_ok=True)
        for _, output, copy_to_site in STL_PARTS:
            if copy_to_site:
                target = asset_dir / output.name
                if not target.exists() or not filecmp.cmp(
                    output, target, shallow=False
                ):
                    shutil.copy2(output, target)
                    print(target.relative_to(ROOT))
                else:
                    print(f"Skipping identical site asset: {target.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stls", action="store_true", help="render STL files")
    parser.add_argument("--views", action="store_true", help="render nine-view PNG sheets")
    parser.add_argument("--force", action="store_true", help="regenerate current outputs")
    args = parser.parse_args()

    render_stls = args.stls or not args.views
    render_views = args.views or not args.stls

    if render_stls:
        run(["python3", str(LOGO_VECTORIZER)])
        render_all_stls(force=args.force)
        copy_site_assets()
        run(["python3", str(PROJECT_BUILDER)])

    if render_views:
        for part, output in VIEW_SHEETS:
            render_view_sheet(part, output, force=args.force)


if __name__ == "__main__":
    main()
