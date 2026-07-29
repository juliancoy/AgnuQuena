# Quena generation workflow

`designs/quena.json` is the canonical production specification for the flute.
Do not hand-edit generated dimensions in `Quena.scad`,
`generated/quena_parameters.scad`, or `generated/quena_manifest.json`.

## Rapid iteration

1. Edit `designs/quena.json`.
2. Regenerate and validate the derived parameters:

   ```sh
   make quena-generate
   make quena-validate
   ```

3. Inspect the geometry and tuning report.
4. Export the three production components:

   ```sh
   make quena-export
   ```

The STL files and their SHA-256 production manifest are written under
`build/quena/`.

Use this command in CI or before slicing to detect generated files that do not
match the specification:

```sh
python3 tools/generate_quena.py --check
```

## What the generator owns

The generator derives:

- tuned acoustic and printable tube lengths;
- component split locations and maximum print height;
- lower-hand hole positions from the layout policy;
- measured-compensation hole diameters;
- OpenSCAD parameters shared by the flute and case;
- ergonomic hole diameter and width limits;
- hole edge, inter-hole ligament, and print-height validation;
- a machine-readable geometry and validation manifest.

The compensation model uses the low-frequency open-tone-hole shunt fit identified
in the specification, calibrated independently for each hole from the saved
prototype measurements. Each calibrated opening is solved directly against its
12-TET `target_note`; no legacy reference geometry defines the tuning target.
Calibration stores the printed prototype's actual acoustic hole position, so a
later body-length correction cannot rescale and invalidate that measurement.
Diameter results are rounded to the configured production increment. The fit is
based on Antoine Lefebvre's *Computational
Acoustic Methods for the Design of Woodwind Instruments*, equations 2.3.1–2.3.2:
<https://escholarship.mcgill.ca/concern/theses/0z708w835>.

## Design boundaries

Generation is deterministic and constraint-driven; it is not a substitute for
prototype measurement. After changing bore dimensions, material, hole profile,
or the lower-hand layout:

1. print a prototype;
2. record a guided tuning sample;
3. update the calibration measurements in the specification;
4. regenerate and compare the complete fingering set.

Use the fast one-dimensional model during iteration. Reserve the slower 2D/3D
models and physical prints for shortlisted geometries.

The current generator performs constrained geometric derivation and
measurement-calibrated diameter compensation. It does not claim to be a global
optimizer of the full fingering lattice. A future optimizer should consume this
same specification and manifest, evaluate all fingerings with a validated
transfer-matrix model, and return candidate specifications through the same
manufacturing checks.
