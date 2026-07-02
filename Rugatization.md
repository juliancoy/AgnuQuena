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
- `acoustics/shaders/fdtd.comp` contains a Vulkan compute shader for 3D scalar-pressure FDTD.
- `acoustics/vulkan_fdtd.py` compiles the shader, probes Vulkan devices, reads STL bounds, checks Courant stability, and writes a simulation manifest.
- Important geometry caveat: the current `Quena.stl` is a printable layout with separated parts, not a single assembled acoustic air column. The simulation pipeline still needs to run end to end on an STL, but meaningful acoustic validation will require an assembled simulation STL or a SCAD export mode that emits assembled geometry.

## Progress Checklist

- [x] Define simulation acceptance criteria and expected outputs.
- [ ] Implement STL voxelization into the shader's `SolidMask` grid.
- [ ] Build Vulkan compute dispatch and pressure-buffer ping-pong.
- [ ] Add acoustic source/receiver modeling and pressure sample export.
- [ ] Analyze simulated response into resonant pitch estimates.
- [ ] Tie simulation results to Git-history measurement CSVs.
- [ ] Validate against known recorded pitch measurements.
