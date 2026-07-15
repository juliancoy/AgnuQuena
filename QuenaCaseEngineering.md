# Quena Case Engineering Notes

## Snap-Fit Hinge

The case now uses an integrated snap-fit hinge instead of a removable filament
pin. Critical dimensions:

- Hinge axis: `y=-32.65 mm`, `z=15.8 mm`, centered on the case seam
- Rear-shell inset: `1.8 mm`; resulting rear projection: `5.4 mm`
- Lid pin bearing diameter: `3.6 mm`
- Rounded pin nose: `0.4 mm` spherical radius blended over `0.8 mm`
- Bottom socket diameter: `3.95 mm`
- Diametral socket clearance: `0.35 mm`
- Pin length: `3.0 mm`
- Blind socket depth: `4.2 mm`
- Effective pin engagement: `2.0 mm`
- Full-diameter bearing engagement: `1.3 mm`
- Axial bottoming reserve: `2.2 mm`
- Minimum socket wall: `1.625 mm`
- Lid closed Z offset: `15.95 mm`

Both shell bodies are exactly `15.65 mm` high. Their meeting faces are flat;
the former projecting bottom rim and matching lid socket have been removed.
All hinge barrels use fully rounded capsule ends so adjacent knuckles cannot
catch on sharp end edges during the lid swing. The barrels overlap the rear
shell by `1.8 mm`, turning the attachment into a continuous integrated boss
instead of a tangent-mounted appendage. This reduces projection without
thinning the closed socket wall or hiding the rotation envelope inside the
case.

The lid middle knuckle carries two outward-pointing pins with tapered insertion
tips. The bottom half outer knuckles carry uninterrupted blind sockets. This
design eliminates the long continuous axle previously printed in mid-air and
keeps the entire outer stator free of slots, relief cuts, and radial breaks.
The old pin STL is legacy and is not part of the active assembly.

Install one pin first, bow the ABS lid/hinge carrier axially, and seat the
second pin. Do not attempt to force either pin radially through the stator.


## Nub-and-Knuckle Clasp

The latch is integral to the two case halves; there is no separately printed
latch. It follows the simplest molded harmonica-case pattern: two lid tongues
carry pronounced inward nubs, and the bottom front wall carries two matching
recesses. Pulling at the centered textured thumb zone releases the two points
progressively as the lid is opened.
Critical dimensions:

- Two `16 x 1.6 x 11 mm` lid cantilever tongues at `x=-72, +72 mm`,
  with widened tapered root shoulders blended into the lid wall.
- `1.2 mm` nub/dimple radius and `1.00 mm` nub projection.
- `0.65 mm` bottom-wall recess depth.
- `0.35 mm` required release travel.
- Five low rounded grip ribs in a centered `30 mm` thumb zone.

Print `QuenaCaseLatchCoupon.stl` before relying on the full case latch. Its two
components are representative fragments of the production lid and bottom,
not a third latch part. It checks button entry, cup opening, seated fit,
retention, and release force.

Run `python3 tools/model_latch_snap.py --material all` to screen actuation. For
ABS, each tongue moves `0.35 mm`; the cantilever model predicts `0.69%` root
strain, `7.8-15.5 N` release force per point, and `4.32x` strain margin. The
conservative simultaneous two-point bound is `15.5-31.0 N`, though normal
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
- Raised land between the two channel rows: `2.5 mm`.
- Raised perimeter land around the channel field: `2.5 mm` minimum.
- A single continuous `12.85 mm` bed forms the recesses and terminates `0.8 mm`
  beyond the nominal tube equator. The flute centerline is depressed another
  `0.5 mm`, so the bottom insert edges wrap over and grip it. There are no
  separate cradles or cantilever clips.

## Validation

Run:

```sh
python3 tools/render_case_assets.py --stls
python3 tools/test_case_stls.py
```

This checks:

- STL bounds and connected-component counts.
- Hinge clearance, socket wall, effective engagement, bearing length, body
  inset, and bottoming reserve directly from the OpenSCAD parameters.
- Closed clamshell solid overlap using OpenSCAD CSG intersection.
- Empty-case hinge sweep from `0` to `180` degrees around the actual hinge axis.
- Loaded hinge sweep over the same range using solid envelopes for all three
  flute parts, including connector bulges and transitions. The test repeats at
  18 combinations of the permitted axial, lateral, and lidward clearances.

The OpenSCAD overlap test is required because Bullet/pybullet can miss static
concave mesh penetration and does not detect coplanar Z-fighting.
The loaded sweep is a deterministic rigid-envelope interference screen. It does
not model flute bounce, elastic deformation, friction, wear, or latch failure;
inverted and shock retention remain separate engineering checks.

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

`QuenaCaseBottom.stl` and `QuenaCaseLid.stl` are the single canonical half
exports and are already oriented for the Bambu Lab P1S. The compact `249.2 mm` case length is still too large when
aligned to one bed axis. These exports rotate each half `45 degrees`, producing
a `214.04 x 214.04 mm` XY footprint. The bottom remains interior-up with its
full floor on Z=0; the lid is flipped exterior-down so its full roof, rather
than the latch tips, contacts Z=0. Both fit inside the nominal `256 x 256 mm`
P1S build area, and also stays within a conservative `220 x 220 mm` usable
square with about `3.0 mm` clearance per side when centered.

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
`219.2 mm` hinge span and knuckle layout as the case: two outer case-side
sockets, and one middle lid knuckle carrying the two outward pins. The latest validated
readings are:

- `QuenaCaseHingeCoupon.stl`: `5800` triangles, `116.0 x 55.2 x 13.8 mm`,
  `2` connected components.
- `QuenaCaseFullHingeCoupon.stl`: `2116` triangles,
  `231.2 x 57.2 x 13.8 mm`, `2` connected components.
- `QuenaCaseFullHingeCoupon_9views.png`: `1500 x 1101 px`.
- `QuenaCaseBottom.stl`: `8536` triangles, `249.2 x 65.1 x 22.6 mm`,
  `1` connected component.
- `QuenaCaseLid.stl`: `6780` triangles, `249.2 x 65.8 x 20.1 mm`,
  `1` connected component.
- `QuenaCaseLatch.stl`: `56.0 x 8.3 x 11.6 mm`.
- `QuenaCaseLatchCoupon.stl`: `180.0 x 34.0 x 14.0 mm`.
- `QuenaCaseAssembly.stl`: `249.2 x 65.8 x 33.2 mm`.
- Closed overlap check: `0.003 mm^3`, below the `0.1 mm^3` tolerance.
- Hinge sweep check: passes from `0` to `140` degrees around
  `(0.00, -30.85, 19.05)`.
- Loaded hinge sweep: passes all `18` clearance-limit poses for all `3` stored
  part envelopes from `0` to `140` degrees.

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
