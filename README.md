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

The retained source projects, printable `.gcode.3mf` files, and plain G-code
are named `Quena`, `QuenaCase`, `QuenaCaseEli`, `QuenaCaseLoafBoof`, and
`QuenaCaseSingleFilament` under `bambu-slice-output/`, alongside job-specific
slicer results and SHA-256 manifests. The printable 3MF files already contain
the validated slice for printer upload, but this Bambu Studio build only opens
files ending in `.gcode` directly in the G-code preview. Open the source `.3mf`
to inspect/edit geometry in Prepare, or open the retained `.gcode` to inspect
the validated toolpath without slicing.
The stock, Eli, and Loaf Boof two-color cases confine all artwork to the first
`0.20 mm` layer and print black before yellow, reducing each job to one
material change. The single-filament case preserves the
recessed logo and mandala/flourish engraving but omits the separate inlay mesh,
second filament, and prime tower. It is the unattended option for a printer
equipped with one AMS HT. Bambu Studio 2.8's mixed external/AMS mapping supports
assigning black filament 2 to External and yellow filament 1 to the AMS HT.
The printer prompts for the one manual external-path handoff before continuing
from the AMS. The source is pinned in the `BambuStudio` submodule and the scripts
invoke the native Linux CLI built directly from that revision. Run
`make bambu-studio-setup` once after cloning; its Ubuntu 24.04 Docker builder
keeps the large incremental build cache inside the ignored submodule build
directory, installs a project-local runtime, and installs the pinned official
Bambu networking plugin under the user's BambuStudio data directory. Existing
plugin files are retained in a timestamped backup. `make print-export` performs
the same canonical geometry and project generation without slicing, while
`make case-single-export` rebuilds only the single-filament case project.

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
