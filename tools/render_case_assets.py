#!/usr/bin/env python3
"""Render AgnuQuena case STLs and nine-view review sheets."""

from __future__ import annotations

import argparse
import filecmp
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SCAD = ROOT / "QuenaCase.scad"
RENDERER = Path(__file__).resolve()

STL_PARTS = [
    # Canonical production export: both exterior backs on the bed, with the
    # captive hinge already assembled at 180 degrees.
    ("print_in_place", ROOT / "QuenaCasePrintInPlace.stl", True),
    # Everything below is auxiliary validation/coupon output. The complete
    # printable case itself remains the single STL above. Browser mechanics
    # uses model-space meshes so rendering and collision share the exact hinge
    # coordinates without undoing print transforms.
    ("bottom", ROOT / "QuenaCaseBottomViewer.stl", True),
    ("lid", ROOT / "QuenaCaseLidViewer.stl", True),
    ("lid_logo_print", ROOT / "QuenaCaseLidLogo.stl", True),
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


def render_stl(part: str, output: Path, *, force: bool = False) -> None:
    logo_inputs = (
        ROOT / "EurasianSynergyFlute_logo_2color.png",
        ROOT / "generated" / "case_logo_title.svg",
        ROOT / "generated" / "case_logo_map.svg",
    )
    dependencies = (SCAD, RENDERER) + (logo_inputs if "logo" in part or part in {"lid", "print_in_place", "assembly"} else ())
    if not force and is_current(output, dependencies):
        print(f"Skipping current STL: {output.relative_to(ROOT)}")
        return
    run([
        "openscad",
        "--export-format",
        "asciistl",
        "-D",
        f'part="{part}"',
        "-o",
        str(output),
        str(SCAD),
    ])


def render_png(part: str, output: Path, camera: str) -> None:
    run([
        "openscad",
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
        "openscad",
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
        for part, output, _ in STL_PARTS:
            render_stl(part, output, force=args.force)
        copy_site_assets()

    if render_views:
        for part, output in VIEW_SHEETS:
            render_view_sheet(part, output, force=args.force)


if __name__ == "__main__":
    main()
