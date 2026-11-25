"""Cálculos demostrativos de integridad mecánica, sin dependencias de interfaz.

Las fórmulas se limitan expresamente a los casos descritos en sus docstrings.
No reemplazan el texto normativo vigente ni una evaluación aprobada de ingeniería.
"""

from __future__ import annotations

from datetime import date
from math import isfinite
from typing import Any, Mapping, Sequence


def _positive(name: str, value: float, *, allow_zero: bool = False) -> float:
    """Valida magnitudes reales finitas; los factores adimensionales se validan aparte."""
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} debe ser un número.") from exc
    if not isfinite(numeric) or numeric < 0 or (numeric == 0 and not allow_zero):
        qualifier = "no negativo" if allow_zero else "positivo"
        raise ValueError(f"{name} debe ser finito y {qualifier}.")
    return numeric


def _fraction(name: str, value: float, *, allow_zero: bool = False) -> float:
    numeric = _positive(name, value, allow_zero=allow_zero)
    if numeric > 1:
        raise ValueError(f"{name} debe estar entre 0 y 1.")
    return numeric


def _result(
    formula: str,
    reference: str,
    inputs: Mapping[str, float],
    required: float,
    nominal: float,
    tolerance: float,
    corrosion_allowance: float,
    measured: float | None,
    corrosion_rate: float,
    intervention_years: float,
) -> dict[str, Any]:
    t_min = required
    result: dict[str, Any] = {
        "formula": formula,
        "reference": reference,
        "inputs": dict(inputs),
        "t_required_mm": required,
        "t_min_mm": t_min,
        "t_nominal_mm": nominal,
        "mill_tolerance_fraction": tolerance,
        "corrosion_allowance_mm": corrosion_allowance,
        "nominal_required_mm": (required + corrosion_allowance) / (1 - tolerance),
        "t_alert_mm": t_min + max(0.0, corrosion_rate) * intervention_years,
        "intervention_horizon_years": intervention_years,
    }
    if measured is not None:
        result["t_measured_mm"] = measured
        if measured < t_min:
            result["condition"] = "critical"
            result["condition_text"] = "Espesor bajo el mínimo - Acción inmediata"
        elif measured <= result["t_alert_mm"]:
            result["condition"] = "alert"
            result["condition_text"] = "Alerta: revisar antes de la intervención"
        else:
            result["condition"] = "normal"
            result["condition_text"] = "Normal"
    else:
        result["condition"] = "insufficient"
        result["condition_text"] = "Datos insuficientes"
    return result


def calculate_pipe(
    pressure_mpa: float,
    outside_diameter_mm: float,
    allowable_stress_mpa: float,
    weld_efficiency: float,
    weld_strength_reduction: float,
    coefficient_y: float,
    nominal_thickness_mm: float,
    mill_tolerance_fraction: float = 0.125,
    corrosion_allowance_mm: float = 0.0,
    measured_thickness_mm: float | None = None,
    corrosion_rate_mm_per_year: float = 0.0,
    intervention_years: float = 2.0,
) -> dict[str, Any]:
    """Tramo recto de tubería: t=P·D/[2(S·E·W+P·Y)].

    Diseño según el caso indicado de ASME B31.3; evaluación en servicio según
    API 570. La ecuación no cubre ramales, accesorios, cargas externas ni otros
    casos de presión. El espesor mínimo de servicio se toma igual al requerido
    por presión; CA se añade por separado al espesor nominal de diseño.
    """
    p = _positive("pressure_mpa", pressure_mpa)
    diameter = _positive("outside_diameter_mm", outside_diameter_mm)
    stress = _positive("allowable_stress_mpa", allowable_stress_mpa)
    efficiency = _fraction("weld_efficiency", weld_efficiency)
    weld_factor = _fraction("weld_strength_reduction", weld_strength_reduction)
    y = _positive("coefficient_y", coefficient_y, allow_zero=True)
    nominal = _positive("nominal_thickness_mm", nominal_thickness_mm)
    tolerance = _fraction("mill_tolerance_fraction", mill_tolerance_fraction, allow_zero=True)
    if tolerance >= 1:
        raise ValueError("mill_tolerance_fraction debe ser menor que 1.")
    allowance = _positive("corrosion_allowance_mm", corrosion_allowance_mm, allow_zero=True)
    rate = _positive("corrosion_rate_mm_per_year", corrosion_rate_mm_per_year, allow_zero=True)
    horizon = _positive("intervention_years", intervention_years, allow_zero=True)
    measured = None if measured_thickness_mm is None else _positive(
        "measured_thickness_mm", measured_thickness_mm
    )
    denominator = 2 * (stress * efficiency * weld_factor + p * y)
    if denominator <= 0:
        raise ValueError("El denominador de espesor para tubería debe ser positivo.")
    required = p * diameter / denominator
    return _result(
        "t = P·D / [2·(S·E·W + P·Y)]",
        "ASME B31.3 (diseño, caso indicado); API 570 (servicio, tramo recto).",
        {
            "P_MPa": p, "D_mm": diameter, "S_MPa": stress, "E": efficiency,
            "W": weld_factor, "Y": y,
        },
        required, nominal, tolerance, allowance, measured, rate, horizon,
    )


def calculate_vessel(
    pressure_mpa: float,
    inside_radius_mm: float,
    allowable_stress_mpa: float,
    weld_efficiency: float,
    nominal_thickness_mm: float,
    mill_tolerance_fraction: float = 0.0,
    corrosion_allowance_mm: float = 0.0,
    measured_thickness_mm: float | None = None,
    corrosion_rate_mm_per_year: float = 0.0,
    intervention_years: float = 2.0,
) -> dict[str, Any]:
    """Cilindro de pared delgada: t=P·R/(S·E−0.6·P).

    Caso de envolvente cilíndrica bajo presión interna según ASME VIII-1,
    con tensión admisible de ASME II-D; en servicio, evaluación API 510.
    No incluye cabezales, cargas externas, ni todas las condiciones de diseño.
    """
    p = _positive("pressure_mpa", pressure_mpa)
    radius = _positive("inside_radius_mm", inside_radius_mm)
    stress = _positive("allowable_stress_mpa", allowable_stress_mpa)
    efficiency = _fraction("weld_efficiency", weld_efficiency)
    nominal = _positive("nominal_thickness_mm", nominal_thickness_mm)
    tolerance = _fraction("mill_tolerance_fraction", mill_tolerance_fraction, allow_zero=True)
    if tolerance >= 1:
        raise ValueError("mill_tolerance_fraction debe ser menor que 1.")
    allowance = _positive("corrosion_allowance_mm", corrosion_allowance_mm, allow_zero=True)
    rate = _positive("corrosion_rate_mm_per_year", corrosion_rate_mm_per_year, allow_zero=True)
    horizon = _positive("intervention_years", intervention_years, allow_zero=True)
    measured = None if measured_thickness_mm is None else _positive(
        "measured_thickness_mm", measured_thickness_mm
    )
    denominator = stress * efficiency - 0.6 * p
    if denominator <= 0:
        raise ValueError("S·E − 0.6·P debe ser positivo para calcular espesor.")
    required = p * radius / denominator
    return _result(
        "t = P·R / (S·E − 0.6·P)",
        "ASME VIII Div. 1; ASME II-D (S); API 510 (servicio, envolvente cilíndrica).",
        {"P_MPa": p, "R_mm": radius, "S_MPa": stress, "E": efficiency},
        required, nominal, tolerance, allowance, measured, rate, horizon,
    )


def calculate_tank(
    diameter_m: float,
    liquid_height_m: float,
    specific_gravity: float,
    allowable_stress_mpa: float,
    nominal_thickness_mm: float,
    measured_thickness_mm: float | None = None,
    corrosion_rate_mm_per_year: float | None = None,
    remaining_life_years: float | None = None,
) -> dict[str, Any]:
    """Manto de tanque por método de 1 pie: t=4.9·D·(H−0.3)·G/S (mm).

    D y H se expresan en m, S en MPa y t en mm; caso simplificado API 650,
    evaluado en servicio bajo API 653. Solo representa virolas del manto,
    no fondo, techo, asentamiento, cargas ni los límites completos del método.
    """
    diameter = _positive("diameter_m", diameter_m)
    height = _positive("liquid_height_m", liquid_height_m)
    gravity = _positive("specific_gravity", specific_gravity)
    stress = _positive("allowable_stress_mpa", allowable_stress_mpa)
    nominal = _positive("nominal_thickness_mm", nominal_thickness_mm)
    if height <= 0.3:
        raise ValueError("liquid_height_m debe ser mayor que 0.3 m para esta ecuación.")
    rate = None if corrosion_rate_mm_per_year is None else _positive(
        "corrosion_rate_mm_per_year", corrosion_rate_mm_per_year, allow_zero=True
    )
    remaining = None if remaining_life_years is None else _positive(
        "remaining_life_years", remaining_life_years, allow_zero=True
    )
    measured = None if measured_thickness_mm is None else _positive(
        "measured_thickness_mm", measured_thickness_mm
    )
    required = 4.9 * diameter * (height - 0.3) * gravity / stress
    result = _result(
        "t_min = 4.9·D·(H−0.3)·G / S  [mm]",
        "API 650 (método de 1 pie); API 653 (servicio, virolas del manto).",
        {"D_m": diameter, "H_m": height, "G": gravity, "S_MPa": stress},
        required, nominal, 0.0, 0.0, measured, rate or 0.0, 2.0,
    )
    if rate is None:
        result["inspection_interval_years"] = 5.0
        result["inspection_interval_basis"] = "API 653: 5 años si se desconoce la velocidad de corrosión (criterio solicitado)."
    elif remaining is None:
        result["inspection_interval_years"] = None
        result["inspection_interval_basis"] = "RL requerida para min(0.5·RL, 15 años)."
    else:
        result["inspection_interval_years"] = min(0.5 * remaining, 15.0)
        result["inspection_interval_basis"] = "min(0.5·RL, 15 años), según criterio simplificado solicitado."
    return result


def calculate_corrosion(
    measurements: Sequence[Mapping[str, Any]],
    minimum_thickness_mm: float,
) -> dict[str, Any]:
    """Calcula CR_ST, CR_LT, CR_gob y RL a partir de mediciones cronológicas.

    Las campañas deben estar ordenadas por fecha ISO, sin fechas repetidas.
    Una campaña marcada ``reset_baseline`` inicia una nueva línea base por
    cambio de punto, reparación o reemplazo; no se comparan datos anteriores.
    Si ambas tasas son no positivas, no se inventa una tasa: se devuelve una
    advertencia y una RL indeterminada.
    """
    minimum = _positive("minimum_thickness_mm", minimum_thickness_mm)
    if len(measurements) < 2:
        return {
            "status": "insufficient", "message": "Datos insuficientes: se requieren al menos 2 mediciones.",
            "cr_st_mm_per_year": None, "cr_lt_mm_per_year": None,
            "cr_governing_mm_per_year": None, "remaining_life_years": None,
        }

    parsed: list[tuple[date, float, bool]] = []
    try:
        for item in measurements:
            measurement_date = date.fromisoformat(str(item["date"]))
            thickness = _positive("thickness_mm", item["thickness_mm"])
            parsed.append((measurement_date, thickness, bool(item.get("reset_baseline", False))))
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "status": "date_error", "message": f"Error de fechas o mediciones: {exc}",
            "cr_st_mm_per_year": None, "cr_lt_mm_per_year": None,
            "cr_governing_mm_per_year": None, "remaining_life_years": None,
        }
    if any(current[0] <= previous[0] for previous, current in zip(parsed, parsed[1:])):
        return {
            "status": "date_error", "message": "Error de fechas: fechas duplicadas o invertidas.",
            "cr_st_mm_per_year": None, "cr_lt_mm_per_year": None,
            "cr_governing_mm_per_year": None, "remaining_life_years": None,
        }

    reset_indices = [index for index, row in enumerate(parsed) if row[2]]
    baseline = parsed[reset_indices[-1]:] if reset_indices else parsed
    if len(baseline) < 2:
        return {
            "status": "insufficient", "message": "Datos insuficientes tras reiniciar la línea base.",
            "cr_st_mm_per_year": None, "cr_lt_mm_per_year": None,
            "cr_governing_mm_per_year": None, "remaining_life_years": None,
            "baseline_reset": bool(reset_indices),
        }

    def years_between(start: date, end: date) -> float:
        return (end - start).days / 365.25

    first_date, first_thickness, _ = baseline[0]
    previous_date, previous_thickness, _ = baseline[-2]
    current_date, current_thickness, _ = baseline[-1]
    short_years = years_between(previous_date, current_date)
    total_years = years_between(first_date, current_date)
    cr_st = (previous_thickness - current_thickness) / short_years
    cr_lt = (first_thickness - current_thickness) / total_years
    governing = max(cr_st, cr_lt)
    result: dict[str, Any] = {
        "status": "ok",
        "message": "Se adopta la mayor tasa positiva como criterio conservador.",
        "cr_st_mm_per_year": cr_st,
        "cr_lt_mm_per_year": cr_lt,
        "cr_governing_mm_per_year": governing,
        "current_thickness_mm": current_thickness,
        "minimum_thickness_mm": minimum,
        "baseline_reset": bool(reset_indices),
    }
    if current_thickness < minimum:
        result.update(
            status="below_minimum",
            message="Espesor bajo el mínimo - Acción inmediata.",
            remaining_life_years=0.0,
        )
    elif governing <= 0:
        result.update(
            status="no_corrosion",
            message="CR ≤ 0: advertencia; sin tasa positiva no se estima una vida remanente finita.",
            cr_governing_mm_per_year=None,
            remaining_life_years=None,
        )
    else:
        result["remaining_life_years"] = (current_thickness - minimum) / governing
    return result


def calculate_inspection_interval(
    family: str,
    remaining_life_years: float | None,
    *,
    pipe_class_max_years: float | None = None,
    corrosion_rate_known: bool = True,
) -> dict[str, Any]:
    """Aplica los límites de intervalo simplificados solicitados para cada familia."""
    if family == "tank" and not corrosion_rate_known:
        return {"interval_years": 5.0, "basis": "API 653: 5 años cuando se desconoce CR."}
    if remaining_life_years is None:
        return {"interval_years": None, "basis": "No calculable sin RL."}
    remaining = _positive("remaining_life_years", remaining_life_years, allow_zero=True)
    if family == "pipe":
        if pipe_class_max_years is None:
            raise ValueError("Se requiere pipe_class_max_years para tubería.")
        cap = _positive("pipe_class_max_years", pipe_class_max_years)
        return {"interval_years": min(0.5 * remaining, cap), "basis": "API 570: min(0.5·RL, máximo de clase)."}
    if family == "vessel":
        return {"interval_years": min(0.5 * remaining, 10.0), "basis": "API 510: min(0.5·RL, 10 años)."}
    if family == "tank":
        return {"interval_years": min(0.5 * remaining, 15.0), "basis": "API 653: min(0.5·RL, 15 años), criterio simplificado."}
    raise ValueError(f"Familia no soportada: {family}")


def _step_factor(area_ratio: float) -> tuple[float, str]:
    """Escalones didácticos del proyecto; no son tabla/curva oficial API 581."""
    bands = (
        (0.10, 1.0, "Ar ≤ 0.10"),
        (0.25, 2.0, "0.10 < Ar ≤ 0.25"),
        (0.50, 5.0, "0.25 < Ar ≤ 0.50"),
        (0.75, 10.0, "0.50 < Ar ≤ 0.75"),
        (1.00, 20.0, "0.75 < Ar ≤ 1.00"),
        (float("inf"), 50.0, "Ar > 1.00"),
    )
    for upper, factor, label in bands:
        if area_ratio <= upper:
            return factor, label
    raise AssertionError("Escalón RBI no alcanzable.")


def calculate_rbi(
    corrosion_rate_mm_per_year: float,
    service_age_years: float,
    nominal_thickness_mm: float,
    base_failure_frequency_per_year: float,
    management_factor: float,
    consequence_area_m2: float,
    economic_consequence: float,
) -> dict[str, Any]:
    """Cribado RBI por adelgazamiento, con Df ilustrativo y frecuencia explícita.

    API RP 580/581 proporciona el marco RBI, pero los Df escalonados aquí son
    una convención didáctica del aplicativo, no valores publicados por API ni
    una probabilidad de falla. La frecuencia se calcula como fF0·Df·FMS.
    """
    rate = _positive("corrosion_rate_mm_per_year", corrosion_rate_mm_per_year, allow_zero=True)
    age = _positive("service_age_years", service_age_years, allow_zero=True)
    nominal = _positive("nominal_thickness_mm", nominal_thickness_mm)
    base_frequency = _positive(
        "base_failure_frequency_per_year", base_failure_frequency_per_year, allow_zero=True
    )
    management = _positive("management_factor", management_factor, allow_zero=True)
    area = _positive("consequence_area_m2", consequence_area_m2, allow_zero=True)
    economic = _positive("economic_consequence", economic_consequence, allow_zero=True)
    area_ratio = rate * age / nominal
    damage_factor, damage_band = _step_factor(area_ratio)
    failure_frequency = base_frequency * damage_factor * management
    area_risk = failure_frequency * area
    economic_risk = failure_frequency * economic
    likelihood = (
        1 if failure_frequency <= 1e-6 else
        2 if failure_frequency <= 1e-5 else
        3 if failure_frequency <= 1e-4 else
        4 if failure_frequency <= 1e-3 else 5
    )
    consequence = (
        1 if area <= 1 else
        2 if area <= 10 else
        3 if area <= 100 else
        4 if area <= 1000 else 5
    )
    score = likelihood * consequence
    priority = "Baja" if score <= 4 else "Moderada" if score <= 9 else "Alta" if score <= 16 else "Muy alta"
    return {
        "area_ratio": area_ratio,
        "damage_factor": damage_factor,
        "damage_factor_band": damage_band,
        "damage_factor_is_official_api_curve": False,
        "base_failure_frequency_per_year": base_frequency,
        "management_factor": management,
        "failure_frequency_per_year": failure_frequency,
        "consequence_area_m2": area,
        "economic_consequence": economic,
        "area_risk_m2_per_year": area_risk,
        "economic_risk_per_year": economic_risk,
        "likelihood_level": likelihood,
        "consequence_level": consequence,
        "risk_score": score,
        "inspection_priority": priority,
        "reference": "API RP 580/581 como marco; Df y matriz son simplificaciones no normativas del aplicativo.",
    }
