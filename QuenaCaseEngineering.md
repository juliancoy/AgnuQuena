# Quena Case Engineering Notes

## Snap-Fit Hinge

The case now uses an integrated snap-fit hinge instead of a removable filament
pin. Critical dimensions:

- Hinge axis: `y=-36.7 mm`, `z=22.55 mm`
- Lid pin bearing diameter: `3.2 mm`
- Rounded pin nose: `0.4 mm` spherical radius blended over `0.8 mm`
- Bottom socket diameter: `3.55 mm`
- Diametral socket clearance: `0.35 mm`
- Pin length: `3.0 mm`
- Blind socket depth: `4.2 mm`
- Effective pin engagement: `2.0 mm`
- Full-diameter bearing engagement: `1.3 mm`
- Axial bottoming reserve: `2.2 mm`
- Minimum socket wall: `1.625 mm`
- Lid closed Z offset: `19.45 mm`

The lid middle knuckle carries two outward-pointing pins with tapered insertion
tips. The bottom half outer knuckles carry uninterrupted blind sockets. This
design eliminates the long continuous axle previously printed in mid-air and
keeps the entire outer stator free of slots, relief cuts, and radial breaks.
The old pin STL is legacy and is not part of the active assembly.

Install one pin first, bow the ABS lid/hinge carrier axially, and seat the
second pin. Do not attempt to force either pin radially through the stator.


## Nub-and-Knuckle Clasp

The latch is integral to the two case halves; there is no separately printed
latch. It follows the simplest molded harmonica-case pattern: three lid
tongues carry shallow inward nubs, and the bottom front wall carries three
matching shallow recesses. Pulling a tongue outward clears its recess; the
three points normally release progressively as the lid is opened.
Critical dimensions:

- Three `16 x 1.6 x 9 mm` lid cantilever tongues at `x=-82, 0, +82 mm`,
  with widened tapered root shoulders blended into the lid wall.
- `1.0 mm` nub/dimple radius and `0.80 mm` nub projection.
- `0.55 mm` bottom-wall recess depth, centered `0.45 mm` lower than the
  previous revision.
- `0.25 mm` required release travel.

Print `QuenaCaseLatchCoupon.stl` before relying on the full case latch. Its two
components are representative fragments of the production lid and bottom,
not a third latch part. It checks button entry, cup opening, seated fit,
retention, and release force.

Run `python3 tools/model_latch_snap.py --material all` to screen actuation. For
ABS, each tongue moves `0.25 mm`; the cantilever model predicts `0.74%` root
strain, `10.1-20.2 N` release force per point, and `4.05x` strain margin. The
conservative simultaneous three-point bound is `30.3-60.7 N`, though normal
opening should unzip the points progressively. All screened materials pass. The coupon
remains useful because it includes the complete flex length and root, but the
full case remains the final check for closing alignment and user access.

## Retention Features

Tube retention uses localized ABS cantilever clips:

- Each `10 x 1.2 x 15 mm` finger has a relieved back side, rounded root, and
  shallow ramped hook with `0.35 mm` radial interference.
- Clips are placed only on normal-radius tube sections.
- Connector/sleeve bulges are left clear and should not be compressed.
- Clip stations cannot overlap: Tube 1 uses four clips, Tube 2 uses three,
  and the mouthpiece uses one centered clip on its
  short normal-diameter section.
- The lid channel is aligned to the same closed-position channel center as the
bottom, reducing vertical dead space around the quena parts.

Run `python3 tools/simulate_case_inversion.py` for the inverted load screen.
At the default `42 g` stored mass, the closed case passes a `10 g` load with a
`7.4x` conservative latch-force margin. The tube can move `0.60 mm` before it
contacts the lid channel. The cantilever model screens the ABS clips for open,
inverted retention using their production interference, strain, and release
force; physical performance still depends on layer bonding and print quality.

## Channel Layout

Channel placement is based on the complete recess extents, including end and
connector clearance, rather than the nominal flute-part centers. This keeps
the recesses optically centered even though connector-bearing profiles are
asymmetric.

- The long tube recess is centered horizontally by its finished cut bounds.
- The short tube and mouthpiece recesses use equal left, middle, and right
  distribution gaps. At the current case length, each gap is about `18.9 mm`.
- Raised land between the two channel rows: `8 mm`.
- Raised perimeter land around the channel field: `5 mm` minimum.
- A continuous `9.5 mm` raised bed covers the exposed bottom around the
  recesses. Its top remains about `2.85 mm` below the channel centerline, so
  the normal channel is still wider than the `20.5 mm` tube at the bed edge.
  This is the highest conservative solid-bed treatment that does not turn the
  entire recess into an over-center snap or obstruct vertical insertion.

## Validation

Run:

```sh
python3 tools/render_case_assets.py --stls
python3 tools/test_case_stls.py
```

This checks:

- STL bounds and connected-component counts.
- Hinge clearance, socket wall, effective engagement, bearing length, and
  bottoming reserve directly from the OpenSCAD parameters.
- Closed clamshell solid overlap using OpenSCAD CSG intersection.
- Hinge sweep from `0` to `140` degrees around the actual hinge axis.

The OpenSCAD overlap test is required because Bullet/pybullet can miss static
concave mesh penetration and does not detect coplanar Z-fighting.

### Snap Deformation Model

Run:

```sh
python3 tools/model_hinge_snap.py
```

This reduced-order structural model reads the production dimensions directly
from `QuenaCase.scad` and assumes printed ABS. Because the stator is sealed,
installation deformation is assigned to an `80 mm` span of the lid/hinge
carrier. The second pin requires `2.0 mm` of projected axial shortening. A
sinusoidal-bow model predicts:

- Required center bow: `8.05 mm`.
- ABS carrier strain: `1.37-2.73%`.
- Sequential insertion force: `8.2-32.8 N`.
- Conservative ABS strain margin: `1.10x` against the `3%` screening limit.

The upper bound is close to the screening limit, so the compact coupon remains
mandatory. Install the pins sequentially and inspect the ABS for whitening,
cracks, or residual bow. The model does not predict nonlinear shell behavior,
creep, fatigue, or crack propagation.

## Print Practice

For a Bambu Lab P1S, use `QuenaCaseBottom_P1S.stl` and
`QuenaCaseLid_P1S.stl`. The original `260.6 mm` case length is too large when
aligned to one bed axis. These exports rotate each half `45 degrees`, producing
a `230.37 x 230.37 mm` XY footprint. The bottom remains interior-up with its
full floor on Z=0; the lid is flipped exterior-down so its full roof, rather
than the latch tips, contacts Z=0. Both fit inside the nominal `256 x 256 mm`
P1S build area with about `12.8 mm` clearance per side when centered.

Print `QuenaCaseHingeCoupon.stl` before printing the full case. The coupon is a
compact two-piece flat-on-bed test: one half carries the same central knuckle
and tapered outward pins as the lid, while the other carries the same two blind
sockets as the bottom case. It uses the production pin length,
taper, socket depth, clearance, wall thickness, and sealed stator. Its embossed
socket label overlaps its base; assembly instructions remain in this document
to avoid fragile text islands in the qualification mesh.
The pin roots are separated by the same `80 mm` effective flex span used by the
ABS installation model. Install one pin first as described below.

`QuenaCaseFullHingeCoupon.stl` is the full-width hinge coupon. It uses the same
`230.6 mm` hinge span and knuckle layout as the case: two outer case-side
sockets, and one middle lid knuckle carrying the two outward pins. The latest validated
readings are:

- `QuenaCaseHingeCoupon.stl`: `5800` triangles, `116.0 x 55.2 x 13.8 mm`,
  `2` connected components.
- `QuenaCaseFullHingeCoupon.stl`: `2116` triangles,
  `242.6 x 57.2 x 13.8 mm`, `2` connected components.
- `QuenaCaseFullHingeCoupon_9views.png`: `1500 x 1101 px`.
- `QuenaCaseBottom.stl`: `3660` triangles, `260.6 x 80.0 x 26.1 mm`,
  `1` connected component.
- `QuenaCaseLid.stl`: `1816` triangles, `260.6 x 80.0 x 17.8 mm`,
  `1` connected component.
- `QuenaCaseLatch.stl`: `56.0 x 8.3 x 11.6 mm`.
- `QuenaCaseLatchCoupon.stl`: `74.0 x 9.6 x 12.2 mm`.
- `QuenaCaseAssembly.stl`: `260.6 x 83.2 x 37.0 mm`.
- Closed overlap check: empty OpenSCAD intersection.
- Hinge sweep check: passes from `0` to `140` degrees around
  `(0.00, -36.70, 22.55)`.

Use the coupon to record:

- Whether the socket snaps over the axle without cracking.
- Whether rotation is free after snap-in.
- Whether the socket holds the axle when lightly pulled apart.
- Any material-specific adjustment needed for `hinge_socket_clearance` or
  `hinge_snap_slot_h`.

The coupon barrels use the original narrow rectangular backer plus a simple
`1.2 mm`-wide rectangular foot that rises from the base and overlaps the bottom
of each cylinder by `0.35 mm`. There are no separate ribs, rails, wedges, or
barrel-length breakaway structures. Each outward nub has one `0.9 mm`-wide
rectangular blade continuing from the barrel backer beneath the nub's straight
section. Each blade is anchored into the base by `0.15 mm` and stops `0.2 mm`
below the nub. This removes the isolated cage-like posts while retaining a
one-layer breakaway gap below the pin. Clip the two blades after printing and lightly deburr the
rounded noses; do not sand away the bearing diameter.

## Nine-View Review

Run:

```sh
python3 tools/render_case_assets.py --views
```

This regenerates:

- `QuenaCaseAssembly_9views.png`
- `QuenaCaseBottom_9views.png`
- `QuenaCaseLidHingeCloseup_9views.png`
- `QuenaCaseHingeCoupon_9views.png`
- `QuenaCaseFullHingeCoupon_9views.png`
- `QuenaCaseLatchCoupon_9views.png`

Each sheet is a 3x3 camera sweep at `1500 x 1101 px`. Use these views to catch
framing, hinge, latch, and coupon regressions before slicing.

The lid-hinge close-up sheet targets the left pin, center carrier, right pin,
underside, and both axial ends without whole-part auto-framing. It currently
shows that the nominal `80 mm` carrier is joined to the lid by a continuous
full-length backer. That backer makes the real carrier substantially stiffer
than the simplified ABS bow model, so the reported deformation margin must not
be treated as qualification until the carrier compliance is redesigned or
measured from a representative print.
