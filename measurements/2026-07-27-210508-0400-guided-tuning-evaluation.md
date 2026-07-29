# 2026-07-27 guided tuning evaluation

Source: `2026-07-27-210508-0400-guided-tuning.csv`

The run contains 24 accepted 250 ms blocks per note and two pitch estimates per
block. The calibration frequency below is the median of all 48 accepted
frequency estimates for each note. Loiacono and librosa agree on the direction
and approximate size of every error.

| Note | Calibration Hz | Target Hz | Error |
|---|---:|---:|---:|
| G4 | 397.41 | 392.00 | +23.7 cents |
| A4 | 455.58 | 440.00 | +60.3 cents |
| B4 | 499.31 | 493.88 | +18.9 cents |
| C5 | 541.78 | 523.25 | +60.3 cents |
| D5 | 614.29 | 587.33 | +77.7 cents |
| E5 | 687.98 | 659.26 | +73.8 cents |
| F#5 | 776.02 | 739.99 | +82.3 cents |
| G5 | 810.74 | 783.99 | +57.8 cents |

The preceding, incomplete 21:04 run independently showed the same sharp
direction from G4 through E5. The complete run is used for calibration.

## Applied correction

G4 is the closed-hole body-length reference. Its +23.7-cent error changes
`pitch_raise_cents` from +12.00 to -11.74, increasing acoustic length from
393.265 mm to 398.695 mm.

Each first-register tone hole is calibrated from the printed prototype's actual
acoustic position, opening diameter, and measured median frequency. The
generator now solves that opening directly against its explicit 12-TET
`target_note`.

| Hole | Printed diameter | Corrected diameter | Printed physical z | Corrected physical z |
|---|---:|---:|---:|---:|
| A | 9.03 mm | 7.90 mm | 298.000 mm | 302.000 mm |
| B | 10.26 mm | 10.30 mm | 268.000 mm | 272.000 mm |
| C | 8.86 mm | 7.98 mm | 238.000 mm | 242.000 mm |
| D | 10.00 mm | 8.95 mm | 201.933 mm | 207.163 mm |
| E | 10.00 mm | 9.42 mm | 170.918 mm | 177.719 mm |
| F# | 10.00 mm | 9.37 mm | 143.604 mm | 150.029 mm |

The holes were moved down-axis, away from the mouthpiece, to recover comfortable
opening sizes without raising their modeled pitch. The lower-hand holes move
4 mm, while the upper-hand holes move 5.23–6.80 mm. The break remains at 222 mm.
The rounded production openings remain within 0.14 cent of their modeled
targets. Manufacturing validation passes with 19.07 mm minimum axial ligament,
10.73 mm minimum part-end ligament, and 229.60 mm maximum print height.

## Remaining physical acceptance

G5 is 34.1 cents sharper relative to G4 than a pure octave. Body length and
first-register tone-hole corrections do not establish whether this is
mouthpiece geometry or the breath/tilt operating point. No mouthpiece change is
justified from one upper-register note. Print the corrected geometry, repeat the
one-octave run for first-register confirmation, and then record a controlled
two-octave run before changing the notch or blowing edge.
