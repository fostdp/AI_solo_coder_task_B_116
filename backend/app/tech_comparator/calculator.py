from __future__ import annotations

import math
from typing import Dict, List

from .models import SpinningWheelSpec
from .database import HistoricalSpinningWheels


class EfficiencyCalculator:
    """纺车效率与质量计算对比器"""

    @staticmethod
    def _build_confidence_interval(
        value: float, spec: SpinningWheelSpec, uncertainty_scale: float = 1.0
    ) -> Dict:
        if spec.confidence:
            unc = spec.confidence.uncertainty_percent / 100.0
        else:
            unc = 0.15
        half_width = value * unc * uncertainty_scale
        return {
            "point_estimate": round(value, 4),
            "lower_bound": round(max(value - half_width, 0.0), 6),
            "upper_bound": round(value + half_width, 6),
            "half_width_percent": round(unc * uncertainty_scale * 100, 2),
        }

    @staticmethod
    def calculate_efficiency_metrics(
        spec: SpinningWheelSpec,
        operating_hours: float = 10.0,
        utilization_rate: float = 0.8,
    ) -> Dict:
        effective_hours = operating_hours * utilization_rate
        daily_production = spec.max_daily_production_kg * utilization_rate

        if spec.typical_human_power_w:
            energy_input_kwh = spec.typical_human_power_w * effective_hours / 1000
        elif spec.typical_water_speed is not None:
            water_power = (
                0.5
                * 1000
                * math.pi
                * spec.wheel_radius_m ** 2
                * spec.typical_water_speed ** 3
                * 0.3
            )
            energy_input_kwh = water_power * effective_hours / 1000
        else:
            energy_input_kwh = spec.power_consumption_w * effective_hours / 1000

        energy_efficiency = daily_production / max(energy_input_kwh, 0.001)
        labor_efficiency = daily_production / spec.labor_requirement
        space_efficiency = daily_production / spec.floor_space_m2
        cost_efficiency = daily_production / spec.cost_relative

        result = {
            "wheel_type": spec.wheel_type,
            "daily_production_kg": round(daily_production, 4),
            "energy_input_kwh": round(energy_input_kwh, 4),
            "energy_efficiency_kg_per_kwh": round(energy_efficiency, 4),
            "labor_efficiency_kg_per_person_day": round(labor_efficiency, 4),
            "space_efficiency_kg_per_m2_day": round(space_efficiency, 4),
            "cost_efficiency_kg_per_cost_unit": round(cost_efficiency, 6),
            "utilization_rate": utilization_rate,
            "operating_hours": operating_hours,
            "confidence_intervals": {
                "daily_production_kg": EfficiencyCalculator._build_confidence_interval(
                    daily_production, spec, 1.0
                ),
                "energy_efficiency_kg_per_kwh": EfficiencyCalculator._build_confidence_interval(
                    energy_efficiency, spec, 1.3
                ),
                "labor_efficiency_kg_per_person_day": EfficiencyCalculator._build_confidence_interval(
                    labor_efficiency, spec, 1.0
                ),
            },
        }
        if spec.confidence:
            result["data_confidence"] = {
                "level": spec.confidence.data_level,
                "level_cn": spec.confidence.data_level_cn,
                "source": spec.confidence.source_type,
                "uncertainty_percent": spec.confidence.uncertainty_percent,
                "references": spec.confidence.references,
            }
        return result

    @staticmethod
    def calculate_quality_metrics(
        spec: SpinningWheelSpec,
        yarn_count_tex: float = None,
        target_twist_per_m: float = None,
    ) -> Dict:
        actual_count = yarn_count_tex or spec.typical_count_tex
        twist_cv = spec.twist_uniformity_base
        if actual_count < spec.typical_count_tex:
            twist_cv *= 1 + 0.3 * (spec.typical_count_tex - actual_count) / spec.typical_count_tex
        elif actual_count > spec.typical_count_tex:
            twist_cv *= 1 - 0.15 * (actual_count - spec.typical_count_tex) / actual_count

        breakage_rate = spec.breakage_rate_base
        if target_twist_per_m:
            optimal_twist = math.sqrt(actual_count) * 40
            twist_deviation = abs(target_twist_per_m - optimal_twist) / optimal_twist
            breakage_rate *= 1 + twist_deviation * 2

        evenness_cv = twist_cv * 1.5
        strength_cv = twist_cv * 1.2

        return {
            "wheel_type": spec.wheel_type,
            "yarn_count_tex": round(actual_count, 2),
            "twist_uniformity_cv_percent": round(twist_cv, 2),
            "breakage_rate_percent": round(breakage_rate * 100, 3),
            "yarn_evenness_cv_percent": round(evenness_cv, 2),
            "yarn_strength_cv_percent": round(strength_cv, 2),
            "overall_quality_index": round(
                spec.yarn_quality_index * (1 - twist_cv / 30), 4
            ),
            "yarn_grade": EfficiencyCalculator._determine_grade(twist_cv, breakage_rate),
        }

    @staticmethod
    def _determine_grade(twist_cv: float, breakage_rate: float) -> str:
        score = (1 - twist_cv / 30) * 0.6 + (1 - breakage_rate * 10) * 0.4
        if score >= 0.85:
            return "特等"
        elif score >= 0.75:
            return "一等"
        elif score >= 0.65:
            return "二等"
        elif score >= 0.55:
            return "三等"
        else:
            return "等外"

    @staticmethod
    def calculate_comparison(
        wheel_types: List[str] = None,
        operating_hours: float = 10.0,
        utilization_rate: float = 0.8,
    ) -> Dict:
        if wheel_types is None or len(wheel_types) == 0:
            wheel_types = ["hand_spun", "foot_treadle", "water_wheel"]

        specs = HistoricalSpinningWheels.get_all_specs()
        results = {"summary": {}, "details": [], "metrics": {}}

        for wt in wheel_types:
            if wt not in specs:
                continue
            spec = specs[wt]
            efficiency = EfficiencyCalculator.calculate_efficiency_metrics(
                spec, operating_hours, utilization_rate
            )
            quality = EfficiencyCalculator.calculate_quality_metrics(spec)

            detail = {
                "spec": {
                    "wheel_type": spec.wheel_type,
                    "wheel_name": spec.wheel_name,
                    "era": spec.era,
                    "dynasty": spec.dynasty,
                    "year_range": spec.year_range,
                    "power_source": spec.power_source,
                    "num_spindles": spec.num_spindles,
                    "max_daily_production_kg": spec.max_daily_production_kg,
                    "labor_requirement": spec.labor_requirement,
                    "description": spec.description,
                },
                "efficiency": efficiency,
                "quality": quality,
            }
            results["details"].append(detail)

        if results["details"]:
            water = next(
                (d for d in results["details"] if d["spec"]["wheel_type"] == "water_wheel"),
                None,
            )
            if water:
                for d in results["details"]:
                    wt = d["spec"]["wheel_type"]
                    results["metrics"][f"{wt}_vs_water_production_ratio"] = round(
                        water["efficiency"]["daily_production_kg"]
                        / max(d["efficiency"]["daily_production_kg"], 0.0001),
                        2,
                    )
                    results["metrics"][f"{wt}_vs_water_labor_ratio"] = round(
                        water["efficiency"]["labor_efficiency_kg_per_person_day"]
                        / max(d["efficiency"]["labor_efficiency_kg_per_person_day"], 0.0001),
                        2,
                    )

            results["summary"] = {
                "total_wheel_types": len(results["details"]),
                "best_production": max(
                    d["efficiency"]["daily_production_kg"] for d in results["details"]
                ),
                "best_labor_efficiency": max(
                    d["efficiency"]["labor_efficiency_kg_per_person_day"]
                    for d in results["details"]
                ),
                "best_quality": max(
                    d["quality"]["overall_quality_index"] for d in results["details"]
                ),
                "operating_hours": operating_hours,
                "utilization_rate": utilization_rate,
            }

        return results
