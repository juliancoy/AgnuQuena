# Quena Case Engineering Notes

## Captured-Pin Hinge

The case uses three interleaved printed knuckles and a continuous piece of
ordinary `1.75 mm` filament as the hinge pin. This replaces the former opposing
snap nubs, whose short bearing engagement allowed the halves to separate.
Critical dimensions:

- Hinge axis: centered on the case seam
- Knuckle outside diameter: `5.6 mm`
- Pin bore: `2.0 mm`
- Nominal diametral running clearance: `0.25 mm`
- Minimum barrel wall: `1.8 mm`
- Axial gap between knuckles: `0.6 mm`
- Rear-shell inset: `2.4 mm`
- Rear projection: `3.2 mm`
- Pin cut length: `220.4 mm` (`219.2 mm` hinge span plus `1.2 mm`)

Both shell bodies have equal height and flat meeting faces. The capsule-ended
knuckles overlap the rear shell, and the smaller barrel sits farther inward
than the previous snap hinge while retaining clearance through the full lid
sweep.

To assemble, align the three bores, feed straight `1.75 mm` filament through
the complete hinge, trim it to leave approximately `0.6 mm` at each end, and
flatten both ends with a clean heated tool. The mushroomed ends positively
capture the pin without depending on friction or elastic preload.


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
- Pin/bore clearance, barrel wall, knuckle gaps, rear projection, and pin-end
  staking allowance directly from the OpenSCAD parameters.
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
compact two-piece flat-on-bed test with the same central lid knuckle, paired
case knuckles, bore clearance, wall thickness, and axial gaps as production.
Use it to confirm that the printer produces a free-running `2.0 mm` bore around
the selected filament before printing the complete case.

`QuenaCaseFullHingeCoupon.stl` is the full-width hinge coupon. It uses the same
hinge span and interleaved-knuckle layout as the case.

- `QuenaCaseHingeCoupon.stl`: `14108` triangles, `72.0 x 54.6 x 12.6 mm`,
  `2` connected components.
- `QuenaCaseFullHingeCoupon.stl`: `8208` triangles,
  `231.2 x 56.6 x 12.6 mm`, `2` connected components.
- `QuenaCaseFullHingeCoupon_9views.png`: `1500 x 1101 px`.
- `QuenaCaseBottom.stl`: `9864` triangles, `214.0 x 214.0 x 18.7 mm`,
  `1` connected component.
- `QuenaCaseLid.stl`: `9356` triangles, `214.0 x 214.0 x 18.6 mm`,
  `1` connected component.
- `QuenaCaseLatch.stl`: `56.0 x 8.3 x 11.6 mm`.
- `QuenaCaseLatchCoupon.stl`: `180.0 x 34.0 x 14.0 mm`.
- `QuenaCaseAssembly.stl`: `249.2 x 65.6 x 31.6 mm`.
- Closed overlap check: empty intersection.
- Hinge sweep check: passes from `0` to `180` degrees around
  `(0.00, -31.25, 15.80)`.
- Loaded hinge sweep: passes all `18` clearance-limit poses for all `3` stored
  part envelopes from `0` to `180` degrees.

Use the coupon to verify free rotation, low play, bore continuity, and secure
heat-staked end retention. Ream only if necessary; do not enlarge the bore
until the test filament has been measured.

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

The lid-hinge close-up sheet targets the central lid knuckle, its through bore,
underside, and both axial ends without whole-part auto-framing.
