"""Physical breath/source parameters shared by acoustic simulation runners."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class BreathProfile:
    flow_l_min: float = 12.0
    jet_width_mm: float = 8.0
    jet_thickness_mm: float = 1.2
    vertical_angle_deg: float = 0.0
    lateral_angle_deg: float = 0.0
    lip_distance_mm: float = 8.0
    temperature_c: float = 22.0
    relative_humidity_pct: float = 50.0

    def validate(self) -> None:
        if not 0.1 <= self.flow_l_min <= 80.0:
            raise ValueError("flow must be between 0.1 and 80 L/min")
        if self.jet_width_mm <= 0 or self.jet_thickness_mm <= 0:
            raise ValueError("jet dimensions must be positive")
        if abs(self.vertical_angle_deg) > 60 or abs(self.lateral_angle_deg) > 60:
            raise ValueError("breath angles must remain within +/-60 degrees")
        if not 0 <= self.relative_humidity_pct <= 100:
            raise ValueError("relative humidity must be between 0 and 100 percent")
        if not -10 <= self.temperature_c <= 50:
            raise ValueError("air temperature must be between -10 and 50 C")

    @property
    def area_m2(self) -> float:
        return self.jet_width_mm * self.jet_thickness_mm * 1e-6

    @property
    def flow_m3_s(self) -> float:
        return self.flow_l_min / 60_000.0

    @property
    def jet_velocity_m_s(self) -> float:
        return self.flow_m3_s / self.area_m2

    @property
    def air_density_kg_m3(self) -> float:
        # Ideal-gas dry-air baseline with a small water-vapor density correction.
        dry = 1.225 * 273.15 / (273.15 + self.temperature_c)
        return dry * (1.0 - 0.00378 * self.relative_humidity_pct / 100.0)

    @property
    def dynamic_pressure_pa(self) -> float:
        return 0.5 * self.air_density_kg_m3 * self.jet_velocity_m_s**2

    @property
    def sound_speed_m_s(self) -> float:
        # Engineering approximation over the validated temperature/humidity range.
        return 331.3 + 0.606 * self.temperature_c + 0.0124 * self.relative_humidity_pct

    @property
    def directional_coupling(self) -> float:
        vertical = math.cos(math.radians(self.vertical_angle_deg))
        lateral = math.cos(math.radians(self.lateral_angle_deg))
        distance = math.exp(-((self.lip_distance_mm - 8.0) / 8.0) ** 2)
        return max(0.0, vertical * lateral * distance)

    @property
    def source_amplitude(self) -> float:
        # Linear acoustics only needs relative amplitude. Normalize near a typical
        # 12 L/min jet while retaining the physical pressure in output metadata.
        return self.directional_coupling * self.dynamic_pressure_pa / 250.0

    def to_json(self) -> dict[str, float]:
        result = asdict(self)
        result.update({
            "jet_velocity_m_s": self.jet_velocity_m_s,
            "dynamic_pressure_pa": self.dynamic_pressure_pa,
            "sound_speed_m_s": self.sound_speed_m_s,
            "directional_coupling": self.directional_coupling,
            "source_amplitude": self.source_amplitude,
        })
        return result
