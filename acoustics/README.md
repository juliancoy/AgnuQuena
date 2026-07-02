# Vulkan Acoustic Simulation

This folder contains the start of a 3D acoustic FDTD simulation path for the
quena geometry.

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
