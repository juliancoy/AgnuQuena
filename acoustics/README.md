# Vulkan Acoustic Simulation

This folder contains acoustic simulation tools for the quena geometry.

## Calibrated 1D Model

`quena_1d.py` reads the generated production manifest by default (with an
OpenSCAD fallback for historical work), applies calibrated per-hole corrections
where available, and writes pitch estimates that can be compared with
tune-check measurements.

Run the current worktree model:

```sh
python3 acoustics/quena_1d.py
```

To bypass the generated manifest and inspect a standalone SCAD file:

```sh
python3 acoustics/quena_1d.py --manifest "" --scad Quena.scad
```

Run a measured historical geometry and fit its correction from the saved
tune-check note:

```sh
python3 acoustics/quena_1d.py --commit a36f6253471d --fit-correction
```

Outputs:

- `acoustics/out/quena_1d_simulation_worktree.csv`
- `acoustics/out/quena_1d_simulation_worktree.json`

Use `--label current` or another label to choose a different output suffix.

This is the practical pitch estimator. It is calibrated and one-dimensional, so
it should be treated as an engineering model rather than a full fluid/acoustic
solver.

## Printable Materials

All acoustic runners accept `--material`. Available defaults:

```sh
python3 acoustics/quena_3d.py --list-materials
```

Supported built-in profiles include `pla`, `abs`, `petg`, `tpu`, `cf-pla`,
`cf-petg`, and `nylon`; `carbon-fiber` aliases to `cf-pla`. The material model
changes the simulated print result:
length scale, bore and tone-hole dimensional bias, end/tone-hole corrections,
and FDTD damping. It does not pretend the air column is made of plastic; for
stiff printed flutes the plastic mainly matters through geometry, edge finish,
wall loss, and compliance.

Example:

```sh
python3 acoustics/quena_3d.py --material petg --label petg_current
```

## Assembled Printed Shape

Export the fitted-together print shape and the matching internal air volume:

```sh
python3 acoustics/export_assembled.py
```

This writes ignored generated artifacts:

- `acoustics/out/assembled_quena.stl`
- `acoustics/out/assembled_air.stl`
- `acoustics/out/assembled_validation.json`

Use the air STL for the closest current simulation of the fitted print:

```sh
python3 acoustics/quena_3d.py --material abs --air-stl acoustics/out/assembled_air.stl --steps 4096 --label abs_air_stl_generated
```

The air STL is the acoustic domain. The plastic STL is useful for inspection and
validation, but simulating the plastic shell as the fluid domain would be wrong.

Current ABS assembled-air validation:

| note | predicted hz | predicted cents | measured cents |
| --- | ---: | ---: | ---: |
| G4 | 418.0214 | +111.27 | -1.3 |
| A4 | 422.4296 | -70.55 | -1.3 |
| B4 | 477.7188 | -57.6 | -41.3 |
| C5 | 513.1936 | -33.6 | -21.3 |
| D5 | 592.3994 | +14.88 | -11.3 |
| E5 | 675.0935 | +41.09 | -1.3 |
| F#5 | 771.279 | +71.7 | -21.3 |
| G5 | 751.0543 | -74.3 | -1.3 |

The assembled-air run currently has median absolute prediction error of
`55.8 cents` and RMS error of `65.5 cents` against the saved tune-check
measurements. Treat it as the current 3D fluid baseline for ABS in the exact
printed air shape, not yet as a final tuning oracle.

## 2D FDTD Cross-Section

`quena_2d.py` runs a scalar-pressure finite-difference simulation on a
longitudinal bore cross-section. The distal end and the active tone-hole opening
are pressure-release boundaries; the bore walls are reflective.

Run all notes:

```sh
python3 acoustics/quena_2d.py --label current
```

Run a single note while tuning model parameters:

```sh
python3 acoustics/quena_2d.py --note B4 --steps 32768
```

Outputs:

- `acoustics/out/quena_2d_simulation_current.csv`
- `acoustics/out/quena_2d_simulation_current.json`

This is a real time-domain simulation, but still a 2D approximation. It ignores
azimuthal tone-hole shape and external radiation impedance, so use it for
directional checks before treating it as a final tuning authority.

## 3D FDTD Bore Model

`quena_3d.py` is the CPU reference 3D fluid/acoustic simulation. It creates a
cylindrical bore air mask from the SCAD dimensions, uses reflective bore walls,
applies pressure-release openings for the distal end or active fingering hole,
injects an impulse, records receiver pressure, and reports FFT peaks.

Run all notes with the default coarse grid:

```sh
python3 acoustics/quena_3d.py --label current
```

Run a single note for faster iteration:

```sh
python3 acoustics/quena_3d.py --note B4 --steps 8192 --label b4_smoke
```

Outputs:

- `acoustics/out/quena_3d_simulation_current.csv`
- `acoustics/out/quena_3d_simulation_current.json`

The default grid is intentionally coarse enough to run on CPU. Reduce
`--cell-mm` only after validating runtime and memory use; 3D FDTD must keep
`--courant` below `1/sqrt(3)`.

### Breath source and environmental inputs

The 3D runner accepts physical breath parameters rather than an arbitrary
"soft/hard" label. Flow and jet area determine velocity and dynamic pressure;
vertical/lateral angles and lip distance determine source coupling. Air
temperature and relative humidity alter sound speed and therefore resonance.

```sh
python3 acoustics/quena_3d.py --note A4 --steps 8192 \
  --flow-l-min 12 --jet-width-mm 8 --jet-thickness-mm 1.2 \
  --vertical-angle-deg 15 --lateral-angle-deg 5 --lip-distance-mm 8 \
  --temperature-c 22 --relative-humidity-pct 50 --label a4_breath
```

This remains a linear scalar-pressure source-coupling model. It is appropriate
for resonance and sensitivity screening: breath quantity changes amplitude and
angle changes coupling, while temperature/humidity change frequency through
sound speed. It does **not** resolve the turbulent lip jet, vortex shedding,
self-sustained oscillation, pitch bending, or register selection. Those require
a transient compressible CFD model with the exterior mouthpiece/lip geometry;
do not interpret this source model as that CFD calculation.

Current coarse-grid validation:

```sh
python3 acoustics/quena_3d.py --steps 8192 --label current_coarse
```

This run completes on CPU and writes per-note pitch estimates. At the current
coarse resolution it is useful as a real 3D reference simulation, not a final
tuning oracle: the July 2026 comparison run had median absolute error around
`45 cents` and RMS error around `63 cents` for the idealized cylinder. The
assembled-air STL run above is the better baseline when checking the fitted
printed shape.

## Vulkan FDTD Setup

The Vulkan path is still a setup path for a future 3D FDTD simulation.

The compute kernel is `shaders/fdtd.comp`. It updates a scalar pressure field on
a 3D grid with a solid mask for printed material boundaries. Boundary neighbors
inside the solid mask mirror the center cell pressure, which approximates a hard
reflective wall.

Run the setup pass:

```sh
python3 acoustics/vulkan_fdtd.py --stl Quena.stl
```

That compiles the Vulkan shader with `glslc`, reads the STL bounds, checks the
3D Courant stability condition, and writes
`acoustics/out/simulation_manifest.json`.

Next implementation steps:

1. Voxelize the STL into the shader's `SolidMask` buffer.
2. Allocate Vulkan storage buffers for previous/current/next pressure fields.
3. Dispatch the compute shader for each timestep and record receiver samples.
4. FFT the receiver impulse response and compare peaks with measured notes.
