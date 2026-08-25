import json
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = REPO_ROOT / "config" / "quena_print_settings.json"
PROJECT_PATH = REPO_ROOT / "Quena.3mf"


def test_quena_bridge_settings_are_small_and_explicit():
    assert json.loads(SETTINGS_PATH.read_text(encoding="utf-8")) == {
        "bridge_flow": "0.9",
        "bridge_speed": ["25", "25"],
        "overhang_fan_speed": ["95", "95"],
        "seam_placement_away_from_overhangs": "1",
    }


def test_quena_3mf_embeds_the_canonical_bridge_settings():
    with zipfile.ZipFile(PROJECT_PATH) as archive:
        settings = json.loads(archive.read("Metadata/project_settings.config"))

    expected = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    for key, value in expected.items():
        assert settings[key] == value
    assert settings["printer_settings_id"] == "Bambu Lab P1S 0.4 nozzle"
    assert settings["curr_bed_type"] == "Textured PEI Plate"
    assert settings["filament_settings_id"] == ["PolyLite ABS @BBL X1C"]
    assert settings["filament_diameter"] == ["1.75"]
    assert settings["filament_type"] == ["ABS"]
    assert len(settings["inherits_group"]) == 3
    assert all(settings["filament_settings_id"])
