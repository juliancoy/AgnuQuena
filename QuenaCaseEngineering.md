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

The two nub spheres are added after all tongue, hinge, and ornament relief
booleans. No subtractive operation is allowed to flatten or hollow either nub.

Run `python3 tools/model_latch_snap.py --material all` to screen actuation. For
ABS, each tongue moves `0.40 mm`; the cantilever model predicts `0.73%` root
strain, `8.7-17.5 N` release force per point, and `4.13x` strain margin. The
conservative simultaneous two-point bound is `17.5-34.9 N`, though normal
opening should unzip the points progressively. All screened materials pass.
The full case is the physical check for closing alignment, user access, and
release force; no separate coupon meshes are maintained.

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
python3 tools/render_case_assets.py --all-meshes
python3 tools/build_case_3mf.py
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
- The bottom exterior retains a `14 mm` plan-view corner radius, `1.5 mm`
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
- The browser keeps positive Z at the top of the view, lights both intentional
  friction-fit nub contacts while the case is closed, and removes those latch
  markers once the nubs release at `3 degrees`. Exact surface intersections
  elsewhere remain highlighted as line segments on the model.
- The browser loads the logo/title and mandala/flourish inlays as separate
  model-space meshes, using contrasting coral and gold materials rather than
  flattening either decoration into the blue shell material.
- The checksum-verified native Bambu Studio CLI opens and slices the project
  directly with the P1S profile, two ABS filaments, one colour change, and
  no generated support, brim, or skirt toolpaths. It checks that black is used
  only in the first `0.20 mm` layer and that the compact prime tower ends at
  `Z=0.2`.

The OpenSCAD and browser checks are required because Bullet/pybullet can miss
static concave mesh penetration and does not detect coplanar Z-fighting. The
browser therefore displays exact triangle contact separately from the two
intentional closed latch interferences. The browser regression caught a real
seven-point hinge collision at `25 degrees`; the lid relief now follows each
stator's complete circular envelope. A zero-depth hinge surface contact can be
visible without failing the rigid-envelope sweep; the failure threshold remains
`0.05 mm` of actual penetration.
The loaded sweep is a deterministic rigid-envelope interference screen. It does
not model flute bounce, elastic deformation, friction, wear, or latch failure;
inverted and shock retention remain separate engineering checks.

The larger shell's plan-view corner radius is `14 mm`. The alternating
axle-support tabs carry the same radius-to-width ratio into their shorter
visible profiles, producing an approximately `0.83 mm` base radius instead of
square shoulders. This proportional rounding does not expand the shallow
radial attachment land or alter the concentric bearing, bore, or
print-in-place clearance.

## Procedural Mandala and Flourish Panel

The lower panel in the open print pose carries three twelve-fold mandala
rosettes inside a rounded frame. Two symmetric vine-knot flourishes fill the
spaces between the rosettes. The design is generated entirely in
`QuenaCase.scad` from concentric rings, radial strokes, orbiting halos, curved
tendrils, and broad leaves, so it remains deterministic and scales with the
case rather than depending on another image asset. The frame centerline follows
the case outline exactly `5 mm` inward.

The single-filament body engraves the ornament `0.40 mm`, or two project
layers. The two-colour body instead uses a `0.20 mm` recess filled by the black
`QuenaCaseArtwork.stl` inlay. This preserves the case's face-down production
pose, reduces the two-colour job to one material change, and leaves at least
`2.40 mm` of solid roof. All
nominal strokes are `0.90 mm` wide, exceeding two line widths for the `0.4 mm`
nozzle. The recesses close without slicer-generated support, and the inlay
meets their floors exactly. The outside plan-view corner radius is `14 mm`,
and `1.5 mm` rounds soften both exposed bed-facing shell edges while retaining
flat first-layer contact. Internal fit, hinge, and latch geometry are unchanged.

## Two-Colour Case Artwork

`EurasianSynergyFlute_logo_2color.png` is the artwork source of truth. Running
`python3 tools/vectorize_case_logo.py` separates its original title and Eurasian
silhouette, removes details narrower than a `0.4 mm` nozzle, and deterministically
generates `generated/case_logo_title.svg`, `generated/case_logo_map.svg`, and
their measured source dimensions. The upper open-pose panel uses those traced
vectors rather than a substituted font or a hand-redrawn map.

The title remains `190 mm` wide and the map `84 mm` wide. A `0.84` vertical
scale fits the composition inside the long upper face while retaining at least a
`2.0 mm` rounded-edge margin. The single-filament logo remains engraved
`0.60 mm` deep for visibility. In the two-colour body, both logo and ornament
inlays are exactly one `0.20 mm` layer deep. Their tops meet the recess floors
exactly, so the black and yellow ABS fuse across a full planar interface.

The traced logo is rotated 180 degrees in the CAD source so it reads normally
when viewed through the base shell's exterior face, while remaining upright on
the upper panel like the display of an open laptop. It is not reflected, which
would reverse both the title and continent. The mandala and flourish inlay
shares the lid's `lid_in_print_pose()` transform and occupies the lower panel.
`QuenaCaseArtwork.stl` combines both black inlays, so they are translated and
aligned with `QuenaCaseTwoColorPrintInPlace.stl`; no slicer positioning is
required.

`QuenaCase.3mf` is the canonical native Bambu Studio two-colour P1S project.
`tools/build_case_3mf.py` creates its archive through the checksum-verified
project-local Bambu Studio CLI, then applies the locked placement and reviewed
print contract. It contains one assembly with:

- `QuenaCaseTwoColorPrintInPlace.stl` assigned to yellow ABS / AMS slot 1.
- `QuenaCaseArtwork.stl` assigned to black ABS / AMS slot 2.
- `0.20 mm` layers, two `0.42-0.45 mm` wall lines, two-layer top and bottom
  skins, `10%` rectilinear infill combined across compatible layers, and
  `0.15 mm` elephant-foot compensation. This reduces repeated perimeter and
  sparse-infill travel without changing the one-layer artwork, hinge, latch,
  or print-in-place clearances.
- The straight OpenSCAD shell is `0.827 mm`, the deposited envelope of the
  `0.42 + 0.45 mm` perimeter pair after Bambu's rounded-extrusion overlap at a
  `0.20 mm` layer height. The original `3 mm` structural margin remains local
  to the hinge, rim, and both friction-fit latch receivers; the mating nubs and
  their intentional closed-case collision are unchanged.
- The bottom channel bed meets the shell's inner face with a `0.04 mm`
  modeling overlap. Its printed edge is aligned with the perimeter, removing
  the open moat that previously separated the two regions.
- A continuous `0.827 mm` lip rises locally to `3.0 mm` past each tube
  centerline while the main bed and shell retain their original height. Its
  opening provides the light snap without isolated clips; the lid is lowered
  locally with `0.25 mm` matching relief around the complete profile.
- Broad outer walls run at a conservative `120 mm/s`, below the P1S standard
  profile's `200 mm/s`; the inherited `50%` small-perimeter rule keeps hinge,
  latch, and ornament details at `60 mm/s`.
- Supports, brims, and skirts disabled; a compact `20 mm` prime tower with a
  `1 mm` brim is limited to the active colour layer and ends at `Z=0.2`.

The two-colour slice has one material transition. With only one AMS HT,
map black filament 2 to External and yellow filament 1 to the AMS HT in the
Bambu Studio 2.8 send dialog. Its mixed external/AMS workflow pauses for the
operator to unload the unpowered external path, then continues from the AMS.
It is still not an unattended two-colour configuration,
but the single-layer artwork minimizes the intervention and purge waste.

`bambu-slice-output/QuenaCase.gcode.3mf` contains the validated slice and opens
directly in Preview. Use it for printing so the desktop application does not
need to run the unstable Linux GUI Slice action.

`QuenaCaseSingleFilament.3mf` is the one-material alternative. It contains only
`QuenaCasePrintInPlace.stl` on filament 1, so the logo and mandala/flourish
remain visible as recessed engraving instead of flush black inlays. It retains
the same placement, layers, walls, infill, and support-free contract while
disabling multi-material mode and the prime tower. Its validated G-code must
contain no second-tool request.

The project places the complete assembly at `X=2.275..253.725 mm` and its
sliced paths at `Y=70.787..184.735 mm`, clear of the P1S front-left exclusion
region and with the prime-tower area behind it. Inspect the first two sliced
layers before printing: only the first-layer artwork should be black, every
artwork island must bond to the yellow case at layer two, and the `0.60 mm`
hinge shell gap must remain open.

The automated Bambu slice produces `96` layers and one colour change. The
current estimate is about `111.39 g` of model ABS (`110.30 g` yellow and
`1.08 g` black), `112.06 g` including purge and prime-tower material, and
`4 h 30 min`; estimates can vary with Bambu Studio releases and printer
calibration.

## Print Practice

`QuenaCasePrintInPlace.stl` is the deeply engraved single-filament production
geometry. `QuenaCaseTwoColorPrintInPlace.stl` is the shallow-recess body for
`QuenaCase.3mf`; use `QuenaCaseSingleFilament.3mf` for a recessed one-material
finish. Both STLs are already oriented with both exterior backs on `Z=0`, side by
side, and the hinge captured at 180 degrees. Its `251.5 x 113.9 mm` footprint
fits the nominal `256 x 256 mm` bed with about `2.3 mm` of X margin per
side when centered. Disable brims, skirts, and automatic support; confirm the
retained P1S plate placement and printer-specific exclusion zones before
starting the full print.

`QuenaCaseBottom.stl` and `QuenaCaseLid.stl` are the canonical model-space
components used by both the browser and engineering validation. The combined
print-in-place STL remains separate because its lid must be rigidly rotated
180 degrees into the build-plate pose.

Use normal first-layer compensation rather than globally shrinking the hinge
gap. Avoid elephant-foot expansion into the 0.60 mm shell separation. After
the bed and part are fully cool, flex the two halves oppositely along the hinge
line to break any wisps, then rotate progressively from the center toward both
ends. Do not drive a blade or wire through the bearings.

- `QuenaCasePrintInPlace.stl`: `71624` triangles,
  `251.5 x 113.9 x 19.3 mm`, `2` connected components.
- `QuenaCaseTwoColorPrintInPlace.stl`: `71644` triangles,
  `251.5 x 113.9 x 19.3 mm`, `2` connected components.
- `QuenaCaseArtwork.stl`: `44492` triangles, `242.4 x 105.3 x 0.2 mm`,
  `31` connected artwork components.
- `QuenaCaseBottom.stl`: `17742` triangles,
  `251.5 x 61.3 x 19.3 mm`, `1` connected component.
- `QuenaCaseLid.stl`: `53882` triangles,
  `251.5 x 62.4 x 19.3 mm`, `1` connected component.
- `QuenaCaseLatch.stl`: `56.0 x 8.3 x 11.6 mm`.
- `QuenaCaseAssembly.stl`: `71626` triangles, `251.5 x 62.4 x 28.8 mm`.
- Closed overlap check: empty intersection.
- Hinge sweep check: passes from `0` to `180` degrees around
  `(0.00, -28.35, 14.40)`.
- Loaded hinge sweep: passes all `18` clearance-limit poses for all `3` stored
  part envelopes from `0` to `180` degrees.

Verify first-motion release, free rotation, and acceptable play on the full
print. If it fuses, adjust the canonical radial or axial clearance and
rerender; do not hand-fit the case or add a hidden slicer-only gap.

## Selective Output

Running `python3 tools/render_case_assets.py` produces only the primary
`QuenaCasePrintInPlace.stl`. Run it with `--list` to show every other mesh and
review sheet; those outputs are optional and selected with repeatable `--mesh`
and `--view` arguments. `--all-meshes` and `--all-views` are reserved for full
validation. Coupon outputs are not generated.

## Nine-View Review

Run:

```sh
python3 tools/render_case_assets.py --all-views
```

This regenerates:

- `QuenaCaseAssembly_9views.png`
- `QuenaCasePrintInPlace_9views.png`
- `QuenaCaseLidHingeCloseup_9views.png`

Each sheet is a 3x3 camera sweep at `1500 x 1101 px`. Use these views to catch
framing, hinge, and latch regressions before slicing.

The lid-hinge close-up sheet targets the integral axle, alternating support
webs, D-flat, and both axle ends without whole-part auto-framing.
