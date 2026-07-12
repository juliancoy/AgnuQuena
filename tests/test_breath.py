import pytest

from acoustics.breath import BreathProfile


def test_breath_physics_and_directional_coupling():
    nominal = BreathProfile()
    angled = BreathProfile(vertical_angle_deg=30, lateral_angle_deg=20)
    stronger = BreathProfile(flow_l_min=24)
    assert nominal.jet_velocity_m_s == pytest.approx(20.8333333)
    assert nominal.dynamic_pressure_pa > 200
    assert angled.directional_coupling < nominal.directional_coupling
    assert stronger.dynamic_pressure_pa == pytest.approx(4 * nominal.dynamic_pressure_pa)


def test_warm_humid_air_changes_sound_speed():
    cold = BreathProfile(temperature_c=10, relative_humidity_pct=20)
    warm = BreathProfile(temperature_c=30, relative_humidity_pct=80)
    assert warm.sound_speed_m_s > cold.sound_speed_m_s


def test_invalid_breath_inputs_are_rejected():
    with pytest.raises(ValueError):
        BreathProfile(flow_l_min=0).validate()
