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
