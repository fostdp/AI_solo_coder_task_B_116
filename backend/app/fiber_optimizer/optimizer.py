"""
棉麻丝纤维特性与纺纱参数优化模块
基于不同纤维的物理特性，智能调整牵伸倍数、加捻参数等工艺参数
"""
from __future__ import annotations

import math
from typing import Dict, List

from .database import FiberDatabase
from .models import FiberProperties


class SpinningParameterOptimizer:
    """纺纱参数智能优化器"""

    @staticmethod
    def calculate_optimal_twist(
        fiber: FiberProperties,
        yarn_count_tex: float,
        twist_direction: str = "Z"
    ) -> Dict:
        """计算最优捻度参数"""
        tf_min, tf_max = fiber.recommended_twist_factor_range
        tf_optimal = (tf_min + tf_max) / 2

        if yarn_count_tex < fiber.typical_count_tex_range[0]:
            tf_optimal *= 1.1
        elif yarn_count_tex > fiber.typical_count_tex_range[1]:
            tf_optimal *= 0.9

        twist_per_meter = tf_optimal / math.sqrt(yarn_count_tex)
        twist_per_inch = twist_per_meter * 0.0254

        min_twist_per_m = tf_min / math.sqrt(yarn_count_tex)
        max_twist_per_m = tf_max / math.sqrt(yarn_count_tex)

        twist_angle_deg = math.degrees(math.atan(twist_per_meter * math.pi * math.sqrt(yarn_count_tex / (fiber.density_g_cm3 * math.pi * 10000))))

        return {
            "fiber_type": fiber.fiber_type,
            "fiber_name": fiber.fiber_name,
            "yarn_count_tex": round(yarn_count_tex, 2),
            "twist_factor": round(tf_optimal, 1),
            "twist_factor_range": [round(tf_min, 1), round(tf_max, 1)],
            "twist_per_meter": round(twist_per_meter, 2),
            "twist_per_inch": round(twist_per_inch, 2),
            "twist_range_per_meter": [round(min_twist_per_m, 2), round(max_twist_per_m, 2)],
            "twist_direction": twist_direction,
            "twist_angle_deg": round(twist_angle_deg, 2)
        }

    @staticmethod
    def calculate_optimal_draft(
        fiber: FiberProperties,
        roving_count_tex: float,
        yarn_count_tex: float,
        delivery_speed_m_min: float = 10.0
    ) -> Dict:
        """计算最优牵伸参数"""
        actual_draft = roving_count_tex / max(yarn_count_tex, 0.001)
        draft_min, draft_max = fiber.recommended_draft_range

        optimal_draft = min(max(actual_draft, draft_min), draft_max)

        if actual_draft < draft_min:
            draft_advice = "实际牵伸倍数偏小，可考虑增加一道预并条工序"
        elif actual_draft > draft_max:
            draft_advice = "实际牵伸倍数偏大，建议减少粗纱定量或增加牵伸区数量"
        else:
            draft_advice = "牵伸倍数在推荐范围内"

        fiber_length_cv = (fiber.fiber_length_mm_max - fiber.fiber_length_mm_min) / (fiber.fiber_length_mm_avg * 2.33)
        draft_efficiency = 0.95 - fiber_length_cv * 0.2 - (actual_draft / draft_max) * 0.05

        breakage_risk = 0.01 + (actual_draft / draft_max) ** 2 * 0.05
        if fiber.friction_coefficient > 0.32:
            breakage_risk *= 1.3

        roller_pressure = 250 + actual_draft * 15 + fiber.breaking_tenacity_cn_dtex * 20

        return {
            "fiber_type": fiber.fiber_type,
            "fiber_name": fiber.fiber_name,
            "roving_count_tex": round(roving_count_tex, 2),
            "yarn_count_tex": round(yarn_count_tex, 2),
            "actual_draft_ratio": round(actual_draft, 2),
            "recommended_draft_range": [round(draft_min, 2), round(draft_max, 2)],
            "optimal_draft_ratio": round(optimal_draft, 2),
            "draft_efficiency": round(draft_efficiency, 4),
            "breakage_risk_percent": round(breakage_risk * 100, 3),
            "roller_pressure_n": round(roller_pressure, 1),
            "delivery_speed_m_min": delivery_speed_m_min,
            "front_roller_speed_rpm": round(delivery_speed_m_min * 1000 / (math.pi * 32), 1),
            "advice": draft_advice
        }

    @staticmethod
    def calculate_spindle_speed(
        fiber: FiberProperties,
        yarn_count_tex: float,
        twist_per_meter: float,
        quality_priority: str = "balanced"
    ) -> Dict:
        """计算最优锭子转速"""
        delivery_speed = 12.0

        if quality_priority == "quality":
            speed_factor = 0.7
        elif quality_priority == "speed":
            speed_factor = 1.15
        else:
            speed_factor = 1.0

        spindle_rpm = twist_per_meter * delivery_speed * 60 / 1000
        max_allowed_rpm = fiber.max_spindle_speed_rpm * speed_factor
        actual_spindle_rpm = min(spindle_rpm, max_allowed_rpm)

        adjusted_delivery = actual_spindle_rpm * 1000 / max(twist_per_meter, 0.001) / 60

        traveler_mass_mg = yarn_count_tex * 0.8
        if fiber.fiber_type == "silk":
            traveler_mass_mg *= 0.7
        elif fiber.fiber_type == "hemp":
            traveler_mass_mg *= 1.2

        production_rate_kg_hour = actual_spindle_rpm * 1000 / (twist_per_meter * 1000 * 1000) * yarn_count_tex / 60

        return {
            "fiber_type": fiber.fiber_type,
            "fiber_name": fiber.fiber_name,
            "quality_priority": quality_priority,
            "calculated_spindle_rpm": round(spindle_rpm, 1),
            "max_allowed_rpm": round(max_allowed_rpm, 1),
            "recommended_spindle_rpm": round(actual_spindle_rpm, 1),
            "delivery_speed_m_min": round(adjusted_delivery, 2),
            "traveler_mass_mg": round(traveler_mass_mg, 1),
            "production_rate_g_per_hour_per_spindle": round(production_rate_kg_hour * 1000, 2),
            "spinning_tension_cn": round(15 + yarn_count_tex * 0.1 + actual_spindle_rpm * 0.02, 2)
        }

    @staticmethod
    def full_spinning_optimization(
        fiber_type: str,
        yarn_count_tex: float = None,
        roving_count_tex: float = None,
        quality_priority: str = "balanced"
    ) -> Dict:
        """完整纺纱参数优化"""
        fiber = FiberDatabase.get_fiber(fiber_type)
        if not fiber:
            return {"error": f"Unknown fiber type: {fiber_type}"}

        actual_count = yarn_count_tex or fiber.typical_count_tex_range[0] * 1.5
        actual_roving = roving_count_tex or actual_count * fiber.recommended_draft_range[1] * 0.7

        twist_params = SpinningParameterOptimizer.calculate_optimal_twist(fiber, actual_count)
        draft_params = SpinningParameterOptimizer.calculate_optimal_draft(fiber, actual_roving, actual_count)
        spindle_params = SpinningParameterOptimizer.calculate_spindle_speed(
            fiber, actual_count, twist_params["twist_per_meter"], quality_priority
        )

        overall_score = (
            (1 - draft_params["breakage_risk_percent"] / 10) * 0.3 +
            (1 - abs(twist_params["twist_factor"] - sum(twist_params["twist_factor_range"]) / 2) / 100) * 0.3 +
            (spindle_params["recommended_spindle_rpm"] / fiber.max_spindle_speed_rpm) * 0.2 +
            draft_params["draft_efficiency"] * 0.2
        )

        return {
            "fiber_info": {
                "fiber_type": fiber.fiber_type,
                "fiber_name": fiber.fiber_name,
                "origin": fiber.origin,
                "fineness_dtex": fiber.fineness_dtex,
                "fiber_length_mm_avg": fiber.fiber_length_mm_avg,
                "breaking_tenacity_cn_dtex": fiber.breaking_tenacity_cn_dtex,
                "moisture_regain_percent": fiber.moisture_regain_percent,
                "description": fiber.description
            },
            "input_parameters": {
                "yarn_count_tex": round(actual_count, 2),
                "roving_count_tex": round(actual_roving, 2),
                "quality_priority": quality_priority
            },
            "twist_parameters": twist_params,
            "draft_parameters": draft_params,
            "spindle_parameters": spindle_params,
            "overall_optimization_score": round(overall_score, 4),
            "warnings": SpinningParameterOptimizer._generate_warnings(fiber, actual_count, twist_params, draft_params)
        }

    @staticmethod
    def _generate_warnings(fiber, count, twist, draft) -> List[str]:
        """生成工艺警告"""
        warnings = []
        if count < fiber.typical_count_tex_range[0]:
            warnings.append(f"纱线支数偏细，建议捻度系数提高10%")
        if count > fiber.typical_count_tex_range[1]:
            warnings.append(f"纱线支数偏粗，建议捻度系数降低10%")
        if draft["actual_draft_ratio"] > fiber.recommended_draft_range[1]:
            warnings.append(f"牵伸倍数过大，断头风险较高")
        if draft["breakage_risk_percent"] > 5:
            warnings.append(f"断头风险超过5%，请检查工艺参数")
        return warnings

    @staticmethod
    def compare_fibers(
        fiber_types: List[str],
        yarn_count_tex: float = 100.0,
        quality_priority: str = "balanced"
    ) -> Dict:
        """多纤维参数对比"""
        results = {"fibers": [], "comparison": {}}
        for ft in fiber_types:
            opt = SpinningParameterOptimizer.full_spinning_optimization(ft, yarn_count_tex, quality_priority=quality_priority)
            if "error" not in opt:
                results["fibers"].append(opt)

        if results["fibers"]:
            results["comparison"] = {
                "highest_production": max(
                    results["fibers"],
                    key=lambda x: x["spindle_parameters"]["production_rate_g_per_hour_per_spindle"]
                )["fiber_info"]["fiber_name"],
                "lowest_breakage": min(
                    results["fibers"],
                    key=lambda x: x["draft_parameters"]["breakage_risk_percent"]
                )["fiber_info"]["fiber_name"],
                "best_overall": max(
                    results["fibers"],
                    key=lambda x: x["overall_optimization_score"]
                )["fiber_info"]["fiber_name"]
            }
        return results
