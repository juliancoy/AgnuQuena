# Axial retune from the 2026-08-03 guided measurement

The headstock was pulled out slightly for this run. The two detector medians put
G4 at **+9.79 cents**, so that value is treated as the global headstock/tube
offset. Hole corrections use each note's interval error relative to G4; applying
the full absolute error would incorrectly tune the adjustable base length into
every tone-hole position.

Detector consensus is the geometric mean of the Loiacono and librosa median
frequencies. With effective length `L = 343000 / (2f)`, the requested distal
shift is:

`target effective length * (1 - 2^(-interval error cents / 1200))`.

| Hole | Consensus error | Error relative to G4 | Requested distal shift | Generated physical Z |
|---|---:|---:|---:|---:|
| A | +60.93 c | +51.14 c | +7.437 mm | 309.437 mm |
| B | +15.49 c | +5.70 c | +1.142 mm | 275.000 mm |
| C | +69.84 c | +60.05 c | +11.174 mm | 253.174 mm |
| D | +69.81 c | +60.01 c | +9.949 mm | 217.112 mm |
| E | +76.00 c | +66.21 c | +9.761 mm | 187.481 mm |
| F# | +73.41 c | +63.62 c | +8.362 mm | 158.391 mm |

B is placed 0.704 mm farther toward the foot than its unconstrained acoustic
solution so the rounded-square B/C cuts retain the required 12 mm axial
ligament. Its solved diameter therefore increases slightly from 10.50 to
10.63 mm to preserve the pitch target.

The A hole was subsequently reduced from 10.10 to 9.50 mm and moved 3.908 mm
toward the mouthpiece. The paired diameter/position change preserves its fitted
pitch while making the lowest hole smaller and easier to reach.

The tube-1/tube-2 break moves from 222.50 to 232.25 mm. This is required to keep
the shifted D hole on tube 1 with a 10 mm part-end ligament while retaining a
sub-240 mm print height. The resulting generated limits are 12.10 mm minimum
axial ligament, 10.13 mm minimum part-end ligament, and 239.85 mm maximum print
height.

The saved calibration records the measured frequency and the +9.79-cent global
offset separately. The generator removes that offset before fitting each hole,
so future body-length changes do not erase the distinction between adjustable
global tuning and note-specific interval tuning.

The G5/G4 octave remains about 15.5 cents wide. Tone-hole relocation cannot
correct that open-fingering register error; verify it again on the new print
before changing the notch or blowing edge.
