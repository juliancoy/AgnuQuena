# Quena Case Engineering Notes

## Segmented Snap-Over Hinge

The lid carries its own continuous printed axle. Seven short C-shaped bearings
on the bottom snap radially over that axle, while eight interleaved lid webs
support it. This replaces both the earlier short end nubs, which separated too
easily, and the later filament pin, which required feeding, trimming, and heat
staking a separate piece.

Critical dimensions:

- Hinge axis: centered on the case seam
- Integral axle diameter: `4.6 mm`
- Axle print flat: `0.60 mm`
- Bearing bore: `4.95 mm`
- Nominal diametral running clearance: `0.35 mm`
- Bearing outside diameter: `8.4 mm`
- Minimum bearing wall: `1.725 mm`
- Snap throat: `3.8 mm` (`0.8 mm` diametral capture)
- Independent bearing width: `14.5 mm`
- Gap between alternating features: `1.0 mm`
- Rear-shell inset: `4.1 mm`
- Rear projection: `4.3 mm`

For assembly, open the two halves, align the axle with the rear-facing bearing
mouths, and press progressively from one end to the other until all seven
bearings click home. The short clips flex independently, so assembly zips
across the hinge instead of forcing one full-width socket open at once. The
neighboring lid webs limit axial motion after installation.

Both canonical halves remain support-free. The lid is exported exterior-down;
the shallow D-flat therefore becomes the printer-facing bottom of the axle.
Each unsupported axle interval is only one segment pitch (`15.5 mm`) and begins
as a conventional bridge. The D-shaped axle remains entirely inside the round
bearing bore throughout rotation.


## Nub-and-Knuckle Clasp

The latch is integral to the two case halves; there is no separately printed
latch. It follows the simplest molded harmonica-case pattern: two lid tongues
carry pronounced inward nubs, and the bottom front wall carries two matching
recesses. Pulling at the centered textured thumb zone releases the two points
progressively as the lid is opened.
Critical dimensions:

- Two `16 x 1.6 x 11 mm` lid cantilever tongues at `x=-72, +72 mm`,
  with widened tapered root shoulders blended into the lid wall.
- `1.3 mm` nub/dimple radius and `1.10 mm` nub projection.
- `0.70 mm` bottom-wall recess depth.
- `0.40 mm` required release travel.
- Five low rounded grip ribs in a centered `30 mm` thumb zone.

Print `QuenaCaseLatchCoupon.stl` before relying on the full case latch. Its two
components are representative fragments of the production lid and bottom,
not a third latch part. It checks button entry, cup opening, seated fit,
retention, and release force.

Run `python3 tools/model_latch_snap.py --material all` to screen actuation. For
ABS, each tongue moves `0.40 mm`; the cantilever model predicts `0.79%` root
strain, `8.9-17.7 N` release force per point, and `3.78x` strain margin. The
conservative simultaneous two-point bound is `17.7-35.5 N`, though normal
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
python3 tools/test_case_browser.py
```

This checks:

- STL bounds and connected-component counts.
- Axle/bore clearance, bearing wall, snap capture, independent segment width,
  rear projection, axial web capture, and support-free axle flat directly from
  the OpenSCAD parameters.
- Closed clamshell solid overlap using OpenSCAD CSG intersection.
- Empty-case hinge sweep from `0` to `180` degrees around the actual hinge axis.
- Loaded hinge sweep over the same range using solid envelopes for all three
  flute parts, including connector bulges and transitions. The test repeats at
  18 combinations of the permitted axial, lateral, and lidward clearances.
- Chrome renders untransformed model-space STLs and checks their exact triangle
  BVHs at every whole-degree pose from `0` to `180`. A deliberate `4 mm`
  penetration must also register, proving that the detector is active.

The OpenSCAD and browser checks are required because Bullet/pybullet can miss
static concave mesh penetration and does not detect coplanar Z-fighting. The
browser regression caught a real seven-point bearing-backer collision at
`25 degrees`; the lid relief now covers each backer's complete swept radius.
The loaded sweep is a deterministic rigid-envelope interference screen. It does
not model flute bounce, elastic deformation, friction, wear, or latch failure;
inverted and shock retention remain separate engineering checks.

## Print Practice

`QuenaCaseBottom.stl` and `QuenaCaseLid.stl` are the single canonical half
exports and are already oriented for the Bambu Lab P1S. The compact `251.5 mm` case length is still too large when
aligned to one bed axis. These exports rotate each half `45 degrees`, producing
a `211.70 x 211.70 mm` XY footprint. The bottom remains interior-up with its
full floor on Z=0; the lid is flipped exterior-down so its full roof, rather
than the latch tips, contacts Z=0. Both fit inside the nominal `256 x 256 mm`
P1S build area, and also stays within a conservative `220 x 220 mm` usable
square with about `4.1 mm` clearance per side when centered.

Print `QuenaCaseHingeCoupon.stl` before printing the full case. The coupon is a
compact two-piece flat-on-bed test with the production axle profile, one
C-bearing bracketed by two axle webs, bore clearance, wall thickness, snap
throat, and lead-in. It requires no supports. Use it to confirm progressive snap
installation, retention, free rotation, and removal force before printing the
complete case.

`QuenaCaseFullHingeCoupon.stl` is the full-width hinge coupon. It uses the same
alternating seven-bearing/eight-web layout and axial capture as the case.

- `QuenaCaseHingeCoupon.stl`: `6188` triangles, `72.0 x 54.1 x 15.4 mm`,
  `2` connected components.
- `QuenaCaseFullHingeCoupon.stl`: `3876` triangles,
  `243.5 x 57.2 x 15.4 mm`, `2` connected components.
- `QuenaCaseFullHingeCoupon_9views.png`: `1500 x 1101 px`.
- `QuenaCaseBottom.stl`: `6900` triangles, `211.7 x 211.7 x 18.7 mm`,
  `1` connected component.
- `QuenaCaseLid.stl`: `22680` triangles, `211.7 x 211.7 x 17.2 mm`,
  `1` connected component.
- `QuenaCaseBottomViewer.stl`: `6900` triangles,
  `251.5 x 59.6 x 18.7 mm`, `1` connected component.
- `QuenaCaseLidViewer.stl`: `22680` triangles,
  `251.5 x 59.2 x 17.2 mm`, `1` connected component.
- `QuenaCaseLatch.stl`: `56.0 x 8.3 x 11.6 mm`.
- `QuenaCaseLatchCoupon.stl`: `180.0 x 34.0 x 14.0 mm`.
- `QuenaCaseAssembly.stl`: `251.5 x 60.2 x 28.8 mm`.
- Closed overlap check: empty intersection.
- Hinge sweep check: passes from `0` to `180` degrees around
  `(0.00, -28.45, 14.40)`.
- Loaded hinge sweep: passes all `18` clearance-limit poses for all `3` stored
  part envelopes from `0` to `180` degrees.

Use the coupon to verify free rotation, low play, progressive installation,
and positive radial retention. Do not enlarge the bearing mouths before
testing the coupon; adjust the canonical throat or clearance instead of
hand-fitting the production case.

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

The lid-hinge close-up sheet targets the integral axle, alternating support
webs, D-flat, and both axle ends without whole-part auto-framing.
