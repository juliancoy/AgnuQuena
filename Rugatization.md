# Rugatization

## Goal

Raise the quality of AgnuQuena measurements by adding two connected systems:

1. A Vulkan-powered 3D acoustic simulation pipeline.
2. A Git-history measurement analysis pipeline that compares design dimensions with noted output pitches.

The simulation does not count as solved until it can produce testable pitch estimates from actual model geometry and compare those estimates with printed/measured results.

## Acceptance Criteria

- The tool can take `Quena.stl` or another generated STL as input.
- The STL is converted into a 3D solid/air simulation grid.
- A Vulkan compute shader runs a time-domain acoustic simulation over that grid.
- The simulation exports pressure samples from one or more receiver points.
- FFT or equivalent spectral analysis identifies candidate resonant frequencies.
- Simulated frequencies are compared against measured pitches from commit history and tuning files.
- Results are reproducible from scripts checked into the repo.

## Implementation Plan

1. Define simulation acceptance criteria and expected outputs.

   The pipeline should take an STL, simulate an impulse, output receiver pressure data, estimate resonance peaks, and compare those peaks against measured notes/history data.

2. Implement STL voxelization.

   Convert STL triangles into a 3D grid with a `solid_mask` buffer. This is the next hard blocker: without it, the shader has no real flute geometry.

3. Build Vulkan compute dispatch.

   Allocate `previous_pressure`, `current_pressure`, `next_pressure`, and `solid_mask` buffers. Dispatch the FDTD compute shader for many timesteps and ping-pong pressure buffers.

4. Add acoustic source and receiver modeling.

   Place a source near the mouthpiece or active edge. Place receivers near the bore end and optionally near tone holes. Export pressure samples as CSV first.

5. Analyze simulated response.

   Run FFT and peak detection over receiver impulse responses. Report candidate resonances in Hz and cents from expected notes.

6. Tie simulation results to Git-history measurements.

   Extend the measurement-history tooling so each commit/configuration can be associated with simulated pitch estimates and printed pitch measurements.

7. Validate against known measured pitches.

   Use pitch notes already present in `Quena.scad` and `Fife/tuning.csv` as the first benchmark. The first useful win condition is directional accuracy: geometry changes should move predicted resonances the same way measured prints do.

## Current State

- `tools/compare_measurements.py` extracts geometry, hole positions, pitch comments, and tuning CSV measurements across Git history.
- `measurements/history/*.csv` contains generated history-analysis outputs.
- `acoustics/quena_1d.py` provides a calibrated 1D bore model that reads SCAD/history geometry, emits pitch estimates, and compares them with tune-check measurements.
- `acoustics/quena_2d.py` runs a numpy-based 2D FDTD cross-section and exports FFT-derived pitch estimates for each fingering.
- `acoustics/quena_3d.py` runs a CPU 3D FDTD cylindrical-bore fluid/acoustic simulation and exports FFT-derived pitch estimates.
- `acoustics/materials.py` provides PLA, ABS, PETG, TPU, nylon, and carbon-fiber composite print profiles for dimensional bias, edge correction, wall loss, and damping.
- `acoustics/export_assembled.py` exports and validates fitted assembled plastic and internal-air STL files for exact-shape acoustic runs.
- `acoustics/quena_3d.py --air-stl acoustics/out/assembled_air.stl` voxelizes the fitted internal-air STL and runs the 3D fluid simulation on that exact air shape.
- `acoustics/shaders/fdtd.comp` contains a Vulkan compute shader for 3D scalar-pressure FDTD.
- `acoustics/vulkan_fdtd.py` compiles the shader, probes Vulkan devices, reads STL bounds, checks Courant stability, and writes a simulation manifest.
- Important geometry caveat: the current `Quena.stl` is a printable layout with separated parts, not a single assembled acoustic air column. Use `acoustics/export_assembled.py` to generate the fitted-together plastic and internal-air STLs for simulation.

## Latest ABS Exact-Shape Run

Command:

```sh
python3 acoustics/export_assembled.py
python3 acoustics/quena_3d.py --material abs --air-stl acoustics/out/assembled_air.stl --steps 4096 --label abs_air_stl_generated
```

Validation:

- Plastic STL: watertight, one component, 7188 faces.
- Internal-air STL: watertight, one component, 4406 faces.
- ABS assembled-air 3D FDTD: median absolute prediction error `55.8 cents`, RMS error `65.5 cents`.

Readings:

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

This is a real 3D fluid run over the fitted internal air volume. It is still a
coarse CPU model, so the result should guide the next simulation improvements
rather than directly drive hole changes.

## Progress Checklist

- [x] Define simulation acceptance criteria and expected outputs.
- [x] Add CPU 1D, 2D, and 3D reference simulations that export pitch estimates.
- [x] Export fitted assembled plastic and internal-air STLs.
- [x] Voxelize the assembled internal-air STL for CPU 3D FDTD.
- [x] Add acoustic source/receiver modeling and pressure sample export in CPU 2D/3D simulations.
- [x] Analyze simulated response into resonant pitch estimates.
- [x] Tie simulation results to Git-history and saved measurement CSVs.
- [x] Validate against known recorded pitch measurements.
- [ ] Implement STL voxelization into the Vulkan shader's `SolidMask` grid.
- [ ] Build Vulkan compute dispatch and pressure-buffer ping-pong.
