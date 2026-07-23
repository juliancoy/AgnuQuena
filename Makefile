.PHONY: quena-generate quena-check quena-test quena-validate quena-export

quena-generate:
	python3 tools/generate_quena.py

quena-check:
	python3 tools/generate_quena.py --check

quena-test:
	PYTHONPATH=. pytest -q

quena-validate: quena-check quena-test
	@tmp=$$(mktemp --suffix=.stl); \
	trap 'rm -f "$$tmp"' EXIT; \
	openscad -o "$$tmp" Quena.scad

quena-export: quena-generate
	python3 tools/export_quena.py
