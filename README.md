This is an OpenScad design of a Quena Andian flute. Is is parametric and split into 3 parts to allow to fit any 3d printer size.

![GitHub Logo](/AgnuQuena.JPG)

## Production generation

The production flute is generated deterministically from
`designs/quena.json`. See [QUENA_GENERATION.md](QUENA_GENERATION.md) for the
rapid-iteration, validation, and STL export workflow.

```sh
make quena-generate
make quena-validate
make quena-export
```

To regenerate, validate, and slice the complete quena layout plus two-color and
single-filament print-in-place case variants for the Bambu Lab P1S, run:

```sh
make print-slice
```

The retained projects and G-code are named `Quena`, `QuenaCase`, and
`QuenaCaseSingleFilament` under `bambu-slice-output/`, alongside job-specific
slicer results and SHA-256 manifests. The single-filament case preserves the
recessed logo and mandala/flourish engraving but omits the separate inlay mesh,
second filament, and prime tower. It is the unattended option for a printer
equipped with one AMS HT: assigning the two-color project's other filament to
the unpowered external spool requires a manual load or unload at each prompted
transition. The source is pinned in the `BambuStudio` submodule and the scripts
invoke its official native Linux CLI directly; run `make bambu-studio-setup`
once after cloning. `make print-export` performs the same canonical geometry and
project generation without slicing, while `make case-single-export` rebuilds
only the single-filament case project.

## Browser CFD lab

`run.py` starts the lab and its automated Chrome test environment as two
Docker containers. Running it without arguments is equivalent to `up`.

```sh
python3 run.py
python3 run.py status
python3 run.py test --require-webgpu
python3 run.py down
```

The lab is served at <http://127.0.0.1:4173/acoustics.html>. Selenium listens
on port 4444, and its noVNC browser is available at <http://127.0.0.1:7900>.
The startup smoke test loads the lab through the Docker network, verifies its
CFD controls, advances the WebGPU clock when available, and writes a screenshot
to `build/selenium/acoustic-lab.png`.
