# Quena Case Engineering Notes

## Captive Print-in-Place Hinge

The complete case prints as two already-assembled moving bodies. Both shell
exteriors lie flat on the bed with the case opened exactly 180 degrees. The lid
carries a continuous axle captured inside seven closed bottom bearings, while
eight interleaved lid webs support the axle and limit axial travel. No pin
insertion, snap assembly, support material, or post-print joining is required.

Critical dimensions:

- Hinge axis: centered on the case seam
- Integral axle diameter: `4.6 mm`
- Axle print flat: `0.60 mm`
- Bearing exterior: fully round with a `0.40 mm` body-side starter web
- Outer axle ends: enclosed by solid, fully round `9.8 mm` lid barrels with
  `1.2 mm` clean-face overhangs
- Bearing bore: `5.20 mm`
- Radial print-in-place clearance: `0.30 mm`
- Bearing outside diameter: `9.8 mm`
- Minimum concentric bearing wall: `2.30 mm`
- Circular bore bridge span: `5.20 mm`
- Independent bearing width: `14.5 mm`
- Gap between alternating features: `1.0 mm`
- Rear-shell inset: `4.6 mm`
- Rear projection: `5.2 mm`
- Shell-edge gap in the print pose: `0.60 mm`

The axle retains its printer-facing flat inside the running bearings, while the
bearing exterior and both visible end barrels are fully round. Each stator
intersects the rear shell directly, without a rectangular backer that could
break its circular silhouette. The solid end barrels replace the exposed
D-flat axle stubs and tie directly into the outer
lid webs. A shallow tangent web connects the bearing's first layers back to the
body without entering the running bore. Each unsupported axle interval is only
one segment pitch (`15.5 mm`). The fully circular `5.20 mm` bore closes over a
short bridge span that remains below the validated `6.0 mm` support-free limit.
The radial clearance is deliberately larger than an assembled running fit
because the first motion must break minor extrusion wisps without welding the
joint.
Twist the two shell strips gently in opposite directions after cooling, then
exercise the hinge through its full travel before operating the latch.


## Nub-and-Knuckle Clasp

The latch is integral to the two case halves; there is no separately printed
latch. It follows the simplest molded harmonica-case pattern: two lid tongues
carry pronounced inward nubs, and the bottom front wall carries two matching
recesses. Pulling at the centered textured thumb zone releases the two points
progressively as the lid is opened.
Critical dimensions:

- Two `18 x 1.6 x 15.9 mm` lid cantilever tongues at `x=-72, +72 mm`,
  with `4.4 mm` widened bonded root haunches continuing toward the bed-facing
  lid back and an `11.5 mm` free flex span below them.
- `2.0 mm` nub/dimple radius and `1.25 mm` nub projection.
- `0.85 mm` bottom-wall recess depth.
- `0.40 mm` required release travel.
- Five low rounded grip ribs in a centered `30 mm` thumb zone.

Print `QuenaCaseLatchCoupon.stl` before relying on the full case latch. Its two
components are representative fragments of the production lid and bottom,
not a third latch part. It checks button entry, cup opening, seated fit,
retention, and release force.

Run `python3 tools/model_latch_snap.py --material all` to screen actuation. For
ABS, each tongue moves `0.40 mm`; the cantilever model predicts `0.73%` root
strain, `8.7-17.5 N` release force per point, and `4.13x` strain margin. The
conservative simultaneous two-point bound is `17.5-34.9 N`, though normal
opening should unzip the points progressively. All screened materials pass. The coupon
remains useful because it includes the complete flex length and root, but the
full case remains the final check for closing alignment and user access.

## Retention Features

Tube retention is built into five short curved sections of the bottom channel
border: two on Tube 1, two on Tube 2, and one on the mouthpiece. Each section
is `14 mm` long, rises `3.0 mm` above the stored-part centerline, and overlaps
the continuous bed by `0.4 mm` so it exports as one structural body. The
resulting normal-tube aperture has `0.34 mm` diametral interference: enough for
a light positive snap without forcing the entire channel length over the part.

The same border geometry, expanded by `0.25 mm`, is removed from the lid. This
keeps the closed outside envelope unchanged and prevents the raised bottom
features from loading the lid. Relative to the prior meshes, the bottom gains
`667.8 mm3` while the lid loses `686.8 mm3`; at `1.04 g/cm3` ABS density the
complete case changes by only `-0.02 g`.

The later round hinge-end enclosure adds about `1.05 g` net relative to that
pre-retention reference, keeping the complete case within `0.4%` of its former
mass while eliminating the exposed axle ends.

Run `python3 tools/simulate_case_inversion.py` for the inverted load screen.
At the default `42 g` stored mass, the closed case passes a `10 g` load with a
`7.4x` conservative latch-force margin. Physical insertion force, release
force, layer bonding, and fatigue still require a printed fit check.

## Channel Layout

Channel placement is based on the complete recess extents, including end and
connector clearance, rather than the nominal flute-part centers. This keeps
the recesses optically centered even though connector-bearing profiles are
asymmetric.

- The long tube recess is centered horizontally by its finished cut bounds.
- The short tube and mouthpiece recesses use equal `8 mm` left, middle, and
  right distribution gaps.
- Raised land between the two channel rows: `2.5 mm`.
- Raised perimeter land around the channel field: `2.5 mm` minimum.
- A single continuous `11.45 mm` bed forms the recesses and terminates `0.8 mm`
  beyond the nominal tube equator. The five localized snap-border sections
  extend that wrap to `3.0 mm`; there are no separate cantilever parts.

## Validation

Run:

```sh
python3 tools/render_case_assets.py --stls
python3 tools/test_case_stls.py
python3 tools/test_case_browser.py
python3 tools/test_case_bambu.py
```

This checks:

- STL bounds and connected-component counts.
- Axle/bore clearance, concentric bearing wall, circular bridge span, alternating
  segment width, shell-edge bed gap, rear projection, axial web capture, and
  axle print flat, concentric bearing wall, starter web, and bed contact from the
  OpenSCAD parameters.
- The production STL contains exactly two watertight moving components, both
  touch `Z=0`, and the complete footprint stays inside `256 x 256 mm`.
- The bottom exterior retains a `12 mm` plan-view corner radius, `1.5 mm`
  bed-facing edge rounds, a border exactly `5 mm` inward, and three rendered
  mandalas with printable strokes and a two-layer recess floor.
- Closed clamshell solid overlap using OpenSCAD CSG intersection.
- Empty-case hinge sweep from `0` to `180` degrees around the actual hinge axis.
- Loaded hinge sweep over the same range using solid envelopes for all three
  flute parts, including connector bulges and transitions. The test repeats at
  18 combinations of the permitted axial, lateral, and lidward clearances.
- Chrome renders untransformed model-space STLs and checks their exact triangle
  BVHs at every whole-degree pose from `0` to `180`. A deliberate `4 mm`
  penetration must also register, proving that the detector is active.
- The installed Bambu Studio Flatpak opens and slices the native project with
  the P1S profile, two ABS filaments, three colour changes, and no generated
  support, brim, or skirt toolpaths. It checks that black is used only in the
  first three `0.20 mm` layers and that the compact prime tower ends at `Z=0.6`.

The OpenSCAD and browser checks are required because Bullet/pybullet can miss
static concave mesh penetration and does not detect coplanar Z-fighting. The
browser regression caught a real seven-point hinge collision at `25 degrees`;
the lid relief now follows each stator's complete circular envelope.
The loaded sweep is a deterministic rigid-envelope interference screen. It does
not model flute bounce, elastic deformation, friction, wear, or latch failure;
inverted and shock retention remain separate engineering checks.

## Procedural Bottom Ornament

The otherwise plain bottom exterior carries three twelve-fold mandala rosettes
inside a rounded frame. The design is generated entirely in `QuenaCase.scad`
from concentric rings, radial strokes, and orbiting halos, so it remains
deterministic and scales with the case rather than depending on another image
asset. The frame centerline follows the case outline exactly `5 mm` inward.

The ornament is engraved `0.40 mm`, or two project layers, and filled by the
black `QuenaCaseArtwork.stl` inlay instead of being embossed. This preserves
the case's face-down production pose and leaves `2.40 mm` of solid floor. All
nominal strokes are `0.90 mm` wide, exceeding two line widths for the `0.4 mm`
nozzle. The recesses close without slicer-generated support, and the inlay
meets their floors exactly. The outside plan-view corner radius is `12 mm`,
and `1.5 mm` rounds soften both exposed bed-facing shell edges while retaining
flat first-layer contact. Internal fit, hinge, and latch geometry are unchanged.

## Two-Colour Case Artwork

`EurasianSynergyFlute_logo_2color.png` is the artwork source of truth. Running
`python3 tools/vectorize_case_logo.py` separates its original title and Eurasian
silhouette, removes details narrower than a `0.4 mm` nozzle, and deterministically
generates `generated/case_logo_title.svg`, `generated/case_logo_map.svg`, and
their measured source dimensions. The lid uses those traced vectors rather than
a substituted font or a hand-redrawn map.

The title remains `190 mm` wide and the map `84 mm` wide. A `0.84` vertical
scale fits the composition inside the long lid face while retaining at least a
`2.0 mm` rounded-edge margin. The inlay is `0.60 mm` deep: exactly three layers
at the project's `0.20 mm` layer height. Its top meets the recess floor exactly,
so the black and yellow ABS fuse across a full planar interface.

The logo inlay and lid share the same `lid_in_print_pose()` transform, while
the bottom ornament is already in the bottom's face-down coordinates.
`QuenaCaseArtwork.stl` combines both black inlays, so they are mirrored,
translated, and aligned with `QuenaCasePrintInPlace.stl`; no slicer positioning
is required.

`QuenaCase.3mf` is the canonical native Bambu Studio two-colour P1S project.
`tools/build_case_3mf.py` creates its archive through the installed Bambu Studio
Flatpak, then applies the locked placement and reviewed print contract. It
contains one assembly with:

- `QuenaCasePrintInPlace.stl` assigned to yellow ABS / AMS slot 1.
- `QuenaCaseArtwork.stl` assigned to black ABS / AMS slot 2.
- `0.20 mm` layers, three walls, `10%` grid infill, and `0.15 mm`
  elephant-foot compensation.
- Supports, brims, and skirts disabled; a compact `20 mm` prime tower with a
  `1 mm` brim is limited to active colour layers and ends at `Z=0.6`.

The project places the complete assembly at `X=5.003..250.997 mm` and its
sliced paths at `Y=70.787..184.735 mm`, clear of the P1S front-left exclusion
region and with the prime-tower area behind it. Inspect the first three sliced
layers before printing: only the artwork should be black, every artwork island
must contact the yellow case at layer four, and the `0.60 mm` hinge shell gap must remain
open.

The automated Bambu slice produces `96` layers and three colour changes. Its
current estimate is about `109.5 g` of model ABS (`107.1 g` yellow and `2.4 g`
black), `111.1 g` including purge and prime-tower material, and `4 h 44 min`;
those estimates can vary with Bambu Studio releases and printer calibration.

## Print Practice

`QuenaCasePrintInPlace.stl` is the canonical production geometry for the Bambu
Lab P1S; use `QuenaCase.3mf` for the complete two-colour job. The STL is already
oriented with both exterior backs on `Z=0`, side by
side, and the hinge captured at 180 degrees. Its `246.0 x 113.9 mm` footprint
fits the nominal `256 x 256 mm` bed with about `5.0 mm` of X margin per
side when centered. Disable brims, skirts, and automatic support; confirm that
the slicer's printer-specific exclusion zones do not reduce usable X below
`246.0 mm` before starting the full print.

The former `QuenaCaseBottom.stl` and `QuenaCaseLid.stl` snap-assembly exports
are intentionally removed. They contained the obsolete open C-bearing and must
not be used for this design; the model-space `*Viewer.stl` files are collision
test inputs, not separately printable case halves.

Use normal first-layer compensation rather than globally shrinking the hinge
gap. Avoid elephant-foot expansion into the 0.60 mm shell separation. After
the bed and part are fully cool, flex the two halves oppositely along the hinge
line to break any wisps, then rotate progressively from the center toward both
ends. Do not drive a blade or wire through the bearings.

Print `QuenaCaseHingeCoupon.stl` before printing the full case. The coupon is a
`46 x 28 mm` crop of the actual production assembly, not a parallel hinge
approximation. It includes the same closed round bearing, axle flat,
radial and axial clearances, shell backs, and first-layer gap. It requires no
supports. Use it to confirm clean release and free rotation before committing
to the complete case.

`QuenaCaseFullHingeCoupon.stl` is the full-width hinge coupon. It uses the same
alternating seven-bearing/eight-web layout and axial capture as the case.

- `QuenaCasePrintInPlace.stl`: `66460` triangles,
  `246.0 x 113.9 x 19.3 mm`, `2` connected components.
- `QuenaCaseArtwork.stl`: `40692` triangles, `236.9 x 105.7 x 0.6 mm`,
  `29` connected artwork components.
- `QuenaCaseHingeCoupon.stl`: `2648` triangles, `46.0 x 28.0 x 19.3 mm`,
  `2` connected components.
- `QuenaCaseFullHingeCoupon.stl`: `14288` triangles,
  `243.5 x 28.0 x 19.3 mm`, `2` connected components.
- `QuenaCaseFullHingeCoupon_9views.png`: `1500 x 1101 px`.
- `QuenaCaseBottomViewer.stl`: `47392` triangles,
  `246.0 x 61.3 x 19.3 mm`, `1` connected component.
- `QuenaCaseLidViewer.stl`: `19068` triangles,
  `246.0 x 62.4 x 19.3 mm`, `1` connected component.
- `QuenaCaseLatch.stl`: `56.0 x 8.3 x 11.6 mm`.
- `QuenaCaseLatchCoupon.stl`: `182.0 x 34.0 x 18.9 mm`.
- `QuenaCaseAssembly.stl`: `66460` triangles, `246.0 x 62.4 x 28.8 mm`.
- Closed overlap check: empty intersection.
- Hinge sweep check: passes from `0` to `180` degrees around
  `(0.00, -28.35, 14.40)`.
- Loaded hinge sweep: passes all `18` clearance-limit poses for all `3` stored
  part envelopes from `0` to `180` degrees.

Use the coupon to verify first-motion release, free rotation, and acceptable
play. If it fuses, adjust the canonical radial or axial clearance and rerender;
do not hand-fit the full production case or add a hidden slicer-only gap.

## Nine-View Review

Run:

```sh
python3 tools/render_case_assets.py --views
```

This regenerates:

- `QuenaCaseAssembly_9views.png`
- `QuenaCasePrintInPlace_9views.png`
- `QuenaCaseLidHingeCloseup_9views.png`
- `QuenaCaseHingeCoupon_9views.png`
- `QuenaCaseFullHingeCoupon_9views.png`
- `QuenaCaseLatchCoupon_9views.png`

Each sheet is a 3x3 camera sweep at `1500 x 1101 px`. Use these views to catch
framing, hinge, latch, and coupon regressions before slicing.

The lid-hinge close-up sheet targets the integral axle, alternating support
webs, D-flat, and both axle ends without whole-part auto-framing.
