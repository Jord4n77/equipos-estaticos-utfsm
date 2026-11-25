import pytest

from calculos import (
    calculate_corrosion,
    calculate_inspection_interval,
    calculate_pipe,
    calculate_rbi,
    calculate_tank,
    calculate_vessel,
)


def test_pipe_required_thickness_nominal_requirement_and_service_interval():
    result = calculate_pipe(
        pressure_mpa=1.6,
        outside_diameter_mm=114.3,
        allowable_stress_mpa=138,
        weld_efficiency=0.85,
        weld_strength_reduction=1,
        coefficient_y=0.4,
        nominal_thickness_mm=6.02,
        corrosion_allowance_mm=1.5,
        measured_thickness_mm=4.2,
    )
    expected = 1.6 * 114.3 / (2 * (138 * 0.85 + 1.6 * 0.4))
    assert result["t_required_mm"] == pytest.approx(expected)
    assert result["t_min_mm"] == pytest.approx(expected)
    assert result["nominal_required_mm"] == pytest.approx((expected + 1.5) / 0.875)
    assert result["condition"] == "normal"
    assert calculate_inspection_interval("pipe", 8, pipe_class_max_years=5)["interval_years"] == 4


def test_pipe_alert_threshold_accounts_for_expected_loss_before_intervention():
    result = calculate_pipe(
        pressure_mpa=1.6,
        outside_diameter_mm=114.3,
        allowable_stress_mpa=138,
        weld_efficiency=0.85,
        weld_strength_reduction=1,
        coefficient_y=0.4,
        nominal_thickness_mm=6.02,
        measured_thickness_mm=1.2,
        corrosion_rate_mm_per_year=0.3,
        intervention_years=2,
    )
    assert result["t_alert_mm"] == pytest.approx(result["t_min_mm"] + 0.6)
    assert result["condition"] == "alert"


def test_vessel_equation_and_ten_year_interval_cap():
    result = calculate_vessel(
        pressure_mpa=1.8,
        inside_radius_mm=750,
        allowable_stress_mpa=138,
        weld_efficiency=0.85,
        nominal_thickness_mm=16,
    )
    assert result["t_required_mm"] == pytest.approx(1.8 * 750 / (138 * 0.85 - 0.6 * 1.8))
    assert calculate_inspection_interval("vessel", 30)["interval_years"] == 10


def test_tank_one_foot_equation_and_unknown_rate_interval():
    result = calculate_tank(
        diameter_m=24,
        liquid_height_m=12,
        specific_gravity=0.85,
        allowable_stress_mpa=160,
        nominal_thickness_mm=10,
        measured_thickness_mm=6.6,
    )
    assert result["t_min_mm"] == pytest.approx(4.9 * 24 * (12 - 0.3) * 0.85 / 160)
    assert result["condition"] == "critical"
    interval = calculate_inspection_interval("tank", None, corrosion_rate_known=False)
    assert interval["interval_years"] == 5
    assert calculate_inspection_interval("tank", 20)["interval_years"] == 10


def test_corrosion_short_and_long_term_use_governing_rate():
    result = calculate_corrosion(
        [
            {"date": "2020-01-01", "thickness_mm": 10},
            {"date": "2023-01-01", "thickness_mm": 9},
            {"date": "2026-01-01", "thickness_mm": 7},
        ],
        minimum_thickness_mm=5,
    )
    assert result["cr_st_mm_per_year"] == pytest.approx(2 / (1096 / 365.25))
    assert result["cr_lt_mm_per_year"] == pytest.approx(3 / (2192 / 365.25))
    assert result["cr_governing_mm_per_year"] == pytest.approx(result["cr_st_mm_per_year"])
    assert result["remaining_life_years"] == pytest.approx(2 / result["cr_governing_mm_per_year"])


def test_corrosion_edge_conditions_and_reset_baseline():
    assert calculate_corrosion([], 4)["status"] == "insufficient"
    inverted = calculate_corrosion(
        [{"date": "2023-01-01", "thickness_mm": 8}, {"date": "2020-01-01", "thickness_mm": 9}], 4
    )
    assert inverted["status"] == "date_error"
    duplicate = calculate_corrosion(
        [{"date": "2023-01-01", "thickness_mm": 8}, {"date": "2023-01-01", "thickness_mm": 7}], 4
    )
    assert duplicate["status"] == "date_error"
    below = calculate_corrosion(
        [{"date": "2020-01-01", "thickness_mm": 5}, {"date": "2023-01-01", "thickness_mm": 3}], 4
    )
    assert below["status"] == "below_minimum"
    no_loss = calculate_corrosion(
        [{"date": "2020-01-01", "thickness_mm": 8}, {"date": "2023-01-01", "thickness_mm": 8}], 4
    )
    assert no_loss["status"] == "no_corrosion"
    reset = calculate_corrosion(
        [
            {"date": "2020-01-01", "thickness_mm": 5},
            {"date": "2023-01-01", "thickness_mm": 10, "reset_baseline": True},
            {"date": "2026-01-01", "thickness_mm": 9},
        ],
        4,
    )
    assert reset["baseline_reset"] is True
    assert reset["cr_governing_mm_per_year"] == pytest.approx(1 / (1096 / 365.25))


def test_invalid_pressure_denominators_are_rejected():
    with pytest.raises(ValueError, match="debe ser positivo"):
        calculate_vessel(200, 500, 100, 1, 10)
    with pytest.raises(ValueError, match="entre 0 y 1"):
        calculate_pipe(1, 100, 100, 1.1, 1, 0.4, 5)
    with pytest.raises(ValueError, match="mayor que 0.3"):
        calculate_tank(20, 0.3, 1, 150, 8)


def test_rbi_separates_damage_factor_failure_frequency_and_consequences():
    result = calculate_rbi(
        corrosion_rate_mm_per_year=0.5,
        service_age_years=10,
        nominal_thickness_mm=10,
        base_failure_frequency_per_year=1e-5,
        management_factor=2,
        consequence_area_m2=25,
        economic_consequence=100000,
    )
    assert result["area_ratio"] == pytest.approx(0.5)
    assert result["damage_factor"] == 5
    assert result["damage_factor_is_official_api_curve"] is False
    assert result["failure_frequency_per_year"] == pytest.approx(1e-4)
    assert result["area_risk_m2_per_year"] == pytest.approx(0.0025)
    assert result["economic_risk_per_year"] == pytest.approx(10)
    assert result["inspection_priority"] == "Moderada"
