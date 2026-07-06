"""Material profiles for printed acoustic simulations.

These profiles model the print-result effects that matter most for a flute-like
air column: dimensional bias, edge/end correction, wall loss, and surface loss.
They are intentionally conservative defaults; printer, slicer, filament brand,
temperature, and annealing can easily dominate the profile values.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace


@dataclass(frozen=True)
class MaterialProfile:
    key: str
    label: str
    density_g_cm3: float
    youngs_modulus_gpa: float
    length_scale: float = 1.0
    bore_diameter_delta_mm: float = 0.0
    hole_diameter_delta_mm: float = 0.0
    open_end_correction_delta_mm: float = 0.0
    tonehole_correction_delta_mm: float = 0.0
    fdtd_damping_multiplier: float = 1.0
    notes: str = ""

    def to_json(self) -> dict[str, object]:
        return asdict(self)


MATERIALS = {
    "pla": MaterialProfile(
        key="pla",
        label="PLA",
        density_g_cm3=1.24,
        youngs_modulus_gpa=3.5,
        notes="Stiff baseline profile; wall compliance is assumed negligible.",
    ),
    "abs": MaterialProfile(
        key="abs",
        label="ABS",
        density_g_cm3=1.04,
        youngs_modulus_gpa=2.1,
        length_scale=0.997,
        bore_diameter_delta_mm=-0.05,
        hole_diameter_delta_mm=-0.03,
        fdtd_damping_multiplier=0.9998,
        notes="More shrink-prone than PLA; slight dimensional contraction and loss.",
    ),
    "petg": MaterialProfile(
        key="petg",
        label="PETG",
        density_g_cm3=1.27,
        youngs_modulus_gpa=2.1,
        length_scale=1.0015,
        bore_diameter_delta_mm=-0.08,
        hole_diameter_delta_mm=-0.06,
        tonehole_correction_delta_mm=2.0,
        fdtd_damping_multiplier=0.9997,
        notes="Often slightly softer/stringier with more hole-edge rounding than PLA.",
    ),
    "tpu": MaterialProfile(
        key="tpu",
        label="TPU",
        density_g_cm3=1.20,
        youngs_modulus_gpa=0.05,
        length_scale=1.003,
        bore_diameter_delta_mm=-0.15,
        hole_diameter_delta_mm=-0.12,
        open_end_correction_delta_mm=3.0,
        tonehole_correction_delta_mm=8.0,
        fdtd_damping_multiplier=0.9985,
        notes="Flexible walls and rougher holes add damping and effective length.",
    ),
    "cf-pla": MaterialProfile(
        key="cf-pla",
        label="Carbon fiber PLA",
        density_g_cm3=1.28,
        youngs_modulus_gpa=5.5,
        length_scale=0.9995,
        bore_diameter_delta_mm=-0.05,
        hole_diameter_delta_mm=-0.04,
        tonehole_correction_delta_mm=1.0,
        fdtd_damping_multiplier=0.9996,
        notes="Stiffer than PLA but usually rougher/abrasive at hole edges.",
    ),
    "cf-petg": MaterialProfile(
        key="cf-petg",
        label="Carbon fiber PETG",
        density_g_cm3=1.30,
        youngs_modulus_gpa=4.5,
        length_scale=1.0005,
        bore_diameter_delta_mm=-0.08,
        hole_diameter_delta_mm=-0.06,
        tonehole_correction_delta_mm=2.5,
        fdtd_damping_multiplier=0.9995,
        notes="Composite PETG profile: stiffer than PETG, rougher than plain polymer.",
    ),
    "nylon": MaterialProfile(
        key="nylon",
        label="Nylon",
        density_g_cm3=1.14,
        youngs_modulus_gpa=1.4,
        length_scale=1.002,
        bore_diameter_delta_mm=-0.10,
        hole_diameter_delta_mm=-0.08,
        tonehole_correction_delta_mm=4.0,
        fdtd_damping_multiplier=0.9992,
        notes="Tough, somewhat compliant, and moisture-sensitive.",
    ),
}

MATERIAL_ALIASES = {
    "carbon": "cf-pla",
    "carbon-fiber": "cf-pla",
    "carbon_fiber": "cf-pla",
    "cf": "cf-pla",
    "cfpla": "cf-pla",
    "cfpetg": "cf-petg",
}


def material_keys() -> list[str]:
    return sorted(set(MATERIALS) | set(MATERIAL_ALIASES))


def canonical_material_keys() -> list[str]:
    return sorted(MATERIALS)


def material_profile(key: str) -> MaterialProfile:
    normalized = key.lower()
    normalized = MATERIAL_ALIASES.get(normalized, normalized)
    if normalized not in MATERIALS:
        options = ", ".join(material_keys())
        raise KeyError(f"unknown material {key!r}; choose one of: {options}")
    return MATERIALS[normalized]


def apply_material_to_geometry(geometry, profile: MaterialProfile):
    """Return a geometry-like object with printed-material dimensional bias."""

    holes = [
        replace(
            hole,
            acoustic_mm=hole.acoustic_mm * profile.length_scale,
            diameter_mm=max(0.1, hole.diameter_mm + profile.hole_diameter_delta_mm),
        )
        for hole in geometry.holes
    ]
    return replace(
        geometry,
        source=f"{geometry.source} [{profile.key}]",
        acoustic_length_mm=geometry.acoustic_length_mm * profile.length_scale,
        holes=holes,
    )
