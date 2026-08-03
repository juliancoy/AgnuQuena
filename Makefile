.PHONY: bambu-studio-setup case-single-export quena-generate quena-check quena-test quena-validate quena-export print-export print-slice

bambu-studio-setup:
	python3 tools/setup_bambu_studio.py

case-single-export:
	python3 tools/build_case_3mf.py --mode single

quena-generate:
	python3 tools/generate_quena.py

quena-check:
	python3 tools/generate_quena.py --check

quena-test:
	PYTHONPATH=. pytest -q tests

quena-validate: quena-check quena-test
	@tmp=$$(mktemp --suffix=.stl); \
	trap 'rm -f "$$tmp"' EXIT; \
	tools/openscad -o "$$tmp" Quena.scad

quena-export: quena-generate
	python3 tools/export_quena.py

print-export:
	python3 tools/export_all_stl_assets.py

print-slice:
	python3 tools/slice_print_jobs.py
