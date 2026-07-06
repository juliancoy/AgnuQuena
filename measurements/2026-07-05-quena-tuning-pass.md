# 2026-07-05 quena tuning pass

Source reading: tune check from `20260705.wav`.

## Current readings pasted before this pass

| detected note | frames | median Hz | target Hz | median cents | meaning |
| --- | ---: | ---: | ---: | ---: | --- |
| G4 | 202 | 392.86 | 392.00 | +3.8 | in tune |
| A4 | 188 | 438.43 | 440.00 | -6.2 | flat |
| A#4 | 87 | 478.11 | 466.16 | +43.8 | sharp |
| B4 | 63 | 480.88 | 493.88 | -46.2 | flat |
| C5 | 170 | 518.38 | 523.25 | -16.2 | flat |
| C#5 | 2 | 552.47 | 554.37 | -6.2 | flat |
| D5 | 138 | 585.24 | 587.33 | -6.2 | flat |
| E5 | 170 | 656.91 | 659.26 | -6.2 | flat |
| F#5 | 132 | 733.11 | 739.99 | -16.2 | flat |
| G5 | 391 | 781.20 | 783.99 | -6.2 | flat |
| G#4 | 8 | 407.89 | 415.30 | -31.2 | flat |

## Local rerun with current script

Command: `python3 tunecheck.py 20260705.wav`

| detected note | frames | median Hz | target Hz | median cents | meaning |
| --- | ---: | ---: | ---: | ---: | --- |
| G4 | 202 | 391.70 | 392.00 | -1.3 | in tune |
| A4 | 188 | 439.67 | 440.00 | -1.3 | in tune |
| A#4 | 116 | 479.46 | 466.16 | +48.7 | sharp |
| B4 | 34 | 482.24 | 493.88 | -41.3 | flat |
| C5 | 170 | 516.85 | 523.25 | -21.3 | flat |
| C#5 | 2 | 550.84 | 554.37 | -11.3 | flat |
| D5 | 138 | 583.50 | 587.33 | -11.3 | flat |
| E5 | 170 | 658.75 | 659.26 | -1.3 | in tune |
| F#5 | 132 | 730.93 | 739.99 | -21.3 | flat |
| G5 | 392 | 783.39 | 783.99 | -1.3 | in tune |
| G#4 | 9 | 407.86 | 415.30 | -31.3 | flat |

## Interpretation

G4 is the all-closed/open-end reference and is already in tune enough, so the overall acoustic length was left unchanged. The two accidental detections, A#4 and C#5, had either ambiguous pitch identity or very few frames, so they were not treated as target notes for geometry.

B4 was the outlier. The A#4 cluster is very close to the B4 frequency, so the B correction is intentionally larger than the other holes but still conservative enough to avoid a likely overshoot.

## Geometry changes

All hole positions below are the acoustic values inside `tuned_length(...)`, not the final OpenSCAD z coordinate. Lower values move the hole closer to the blowing edge and raise pitch.

| hole | before position | after position | before diameter | after diameter | reason |
| --- | ---: | ---: | ---: | ---: | --- |
| A | 342.00 | 341.00 | 10.00 | 10.10 | A4 was 6.2 cents flat |
| B | 307.25 | 302.75 | 10.00 | 10.35 | B4 was 46.2 cents flat; conservative revision from the first larger move |
| C | 281.75 | 279.25 | 9.50 | 9.75 | C5 was 16.2 cents flat |
| D | 246.50 | 245.50 | 11.00 | 11.10 | D5 was 6.2 cents flat |
| E | 215.00 | 214.15 | 11.00 | 11.10 | E5 was 6.2 cents flat |
| F# | 188.00 | 186.20 | 10.88 | 11.13 | F#5 was 16.2 cents flat |

## Next comparison

After the next print, run the same tune check and compare the new median cents against the table above. The main pass/fail questions are:

- Does B4 move substantially upward without becoming sharp?
- Do the A#4 frames collapse into a stable B4 detection?
- Do C5 and F#5 move closer to center without making G4 drift?
