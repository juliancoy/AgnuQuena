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
