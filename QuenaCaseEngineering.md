# Quena Case Engineering Notes

## Snap-Fit Hinge

The case now uses an integrated snap-fit hinge instead of a removable filament
pin. Critical dimensions:

- Hinge axis: `y=-31.7 mm`, `z=22.25 mm`
- Bottom axle diameter: `2.8 mm`
- Lid socket diameter: `3.15 mm`
- Radial socket clearance: `0.35 mm`
- Snap slot height: `2.25 mm`
- Lid closed Z offset: `19.45 mm`

The bottom half carries the continuous axle. The lid carries the socket and
snap slot. The old pin STL is legacy and is not part of the active assembly.

The continuous axle still needs case-side support, but that support cannot run
through the lid socket. The support web is split into the two outer hinge
knuckle zones, leaving the middle lid socket zone clear. The lid also has
matching relief pockets over those two case-side support zones so the closed
case has no hinge penetration.

The lid socket and both hinge coupons include chamfered snap-mouth lead-ins
controlled by `hinge_snap_lead_in_h`. These reduce the force spike when the
socket is pressed over the continuous axle without changing the axle/socket
clearance used for rotation.

## Latch

The active latch is a removable U-clip that bridges the front pulls on the
bottom and lid. The clip now has:

- Chamfered jaw entry relief controlled by `latch_clip_lead_in`.
- Three shallow grip ribs on the outer bridge.
- A printable `latch_coupon` part that carries the same pull spacing and clip
  geometry as the closed case.

Print `QuenaCaseLatchCoupon.stl` before relying on the full case latch. It
checks clip start, sliding fit, closed retention, and finger grip without
spending a full case print.

## Retention Features

The rectangular snap posts were removed. Tube retention now uses curved
over-center retainers:

- Retainers continue the normal tube curve `0.75 mm` past the meridian.
- Retainers are placed only on normal-radius tube sections.
- Connector/sleeve bulges are left clear and should not be compressed.
- The lid channel is aligned to the same closed-position channel center as the
bottom, reducing vertical dead space around the quena parts.

## Validation

Run:

```sh
python3 tools/render_case_assets.py --stls
python3 tools/test_case_stls.py
```

This checks:

- STL bounds and connected-component counts.
- Closed clamshell solid overlap using OpenSCAD CSG intersection.
- Hinge sweep from `0` to `140` degrees around the actual hinge axis.

The OpenSCAD overlap test is required because Bullet/pybullet can miss static
concave mesh penetration and does not detect coplanar Z-fighting.

## Print Practice

Print `QuenaCaseHingeCoupon.stl` before printing the full case. The coupon is a
two-piece flat-on-bed test: one half carries the supported axle and the other
half carries the socket and snap slot. It uses the same axle diameter, socket
diameter, socket clearance, and snap slot height as the full hinge.

`QuenaCaseFullHingeCoupon.stl` is the full-width hinge coupon. It uses the same
`227.6 mm` hinge span and knuckle layout as the case: a continuous case-side
axle, two outer support zones, and one middle lid socket. The latest validated
readings are:

- `QuenaCaseFullHingeCoupon.stl`: `5576` triangles, `239.6 x 56.0 x 13.2 mm`,
  `11` connected components.
- `QuenaCaseFullHingeCoupon_9views.png`: `1500 x 1101 px`.
- `QuenaCaseBottom.stl`: `2638` triangles, `257.6 x 68.0 x 23.8 mm`.
- `QuenaCaseLid.stl`: `1272` triangles, `257.6 x 69.1 x 17.8 mm`.
- `QuenaCaseLatch.stl`: `1352` triangles, `56.0 x 8.3 x 11.6 mm`.
- `QuenaCaseLatchCoupon.stl`: `1812` triangles, `74.0 x 9.6 x 12.2 mm`.
- `QuenaCaseAssembly.stl`: `4994` triangles, `257.6 x 72.2 x 37.0 mm`.
- Closed overlap check: empty OpenSCAD intersection.
- Hinge sweep check: passes from `0` to `140` degrees around
  `(0.00, -31.70, 22.25)`.

Use the coupon to record:

- Whether the socket snaps over the axle without cracking.
- Whether rotation is free after snap-in.
- Whether the socket holds the axle when lightly pulled apart.
- Any material-specific adjustment needed for `hinge_socket_clearance` or
  `hinge_snap_slot_h`.

## Nine-View Review

Run:

```sh
python3 tools/render_case_assets.py --views
```

This regenerates:

- `QuenaCaseAssembly_9views.png`
- `QuenaCaseHingeCoupon_9views.png`
- `QuenaCaseFullHingeCoupon_9views.png`
- `QuenaCaseLatchCoupon_9views.png`

Each sheet is a 3x3 camera sweep at `1500 x 1101 px`. Use these views to catch
framing, hinge, latch, and coupon regressions before slicing.
