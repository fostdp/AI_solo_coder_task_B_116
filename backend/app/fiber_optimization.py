"""
棉麻丝纤维特性与纺纱参数优化模块
基于不同纤维的物理特性，智能调整牵伸倍数、加捻参数等工艺参数
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class FiberProperties:
    """纤维物理特性"""
    fiber_type: str
    fiber_name: str
    scientific_name: str
    origin: str
    color: str
    fiber_length_mm_avg: float
    fiber_length_mm_min: float
    fiber_length_mm_max: float
    fiber_diameter_um: float
    fineness_dtex: float
    density_g_cm3: float
    breaking_tenacity_cn_dtex: float
    elongation_at_break_percent: float
    moisture_regain_percent: float
    modulus_gpa: float
    friction_coefficient: float
    crimp_percent: float
    typical_count_tex_range: Tuple[float, float]
    recommended_twist_factor_range: Tuple[float, float]
    recommended_draft_range: Tuple[float, float]
    max_spindle_speed_rpm: float
    description: str


class FiberDatabase:
    """纤维特性数据库"""

    @staticmethod
    def get_all_fibers() -> Dict[str, FiberProperties]:
        """获取所有纤维特性"""
        return {
            "cotton": FiberProperties(
                fiber_type="cotton",
                fiber_name="棉花",
                scientific_name="Gossypium",
                origin="植物种子纤维",
                color="本白/乳白",
                fiber_length_mm_avg=28.0,
                fiber_length_mm_min=22.0,
                fiber_length_mm_max=38.0,
                fiber_diameter_um=16.0,
                fineness_dtex=1.6,
                density_g_cm3=1.54,
                breaking_tenacity_cn_dtex=2.8,
                elongation_at_break_percent=7.0,
                moisture_regain_percent=8.5,
                modulus_gpa=8.5,
                friction_coefficient=0.28,
                crimp_percent=5.0,
                typical_count_tex_range=(30.0, 400.0),
                recommended_twist_factor_range=(320.0, 420.0),
                recommended_draft_range=(15.0, 40.0),
                max_spindle_speed_rpm=450.0,
                description="最常见的纺织纤维，柔软舒适，吸湿性好，适合织造各类服装面料和家纺产品。"
            ),
            "hemp": FiberProperties(
                fiber_type="hemp",
                fiber_name="苎麻",
                scientific_name="Boehmeria nivea",
                origin="植物韧皮纤维",
                color="本白/黄白",
                fiber_length_mm_avg=60.0,
                fiber_length_mm_min=40.0,
                fiber_length_mm_max=120.0,
                fiber_diameter_um=30.0,
                fineness_dtex=6.5,
                density_g_cm3=1.50,
                breaking_tenacity_cn_dtex=4.2,
                elongation_at_break_percent=3.5,
                moisture_regain_percent=12.0,
                modulus_gpa=22.0,
                friction_coefficient=0.35,
                crimp_percent=1.0,
                typical_count_tex_range=(100.0, 600.0),
                recommended_twist_factor_range=(280.0, 380.0),
                recommended_draft_range=(8.0, 20.0),
                max_spindle_speed_rpm=350.0,
                description="中国传统特色纤维，强度高，凉爽透气，抗菌防霉，适合夏季服装和高档家纺。"
            ),
            "flax": FiberProperties(
                fiber_type="flax",
                fiber_name="亚麻",
                scientific_name="Linum usitatissimum",
                origin="植物韧皮纤维",
                color="本白/浅黄",
                fiber_length_mm_avg=50.0,
                fiber_length_mm_min=30.0,
                fiber_length_mm_max=90.0,
                fiber_diameter_um=22.0,
                fineness_dtex=3.8,
                density_g_cm3=1.49,
                breaking_tenacity_cn_dtex=3.8,
                elongation_at_break_percent=3.0,
                moisture_regain_percent=10.0,
                modulus_gpa=18.0,
                friction_coefficient=0.33,
                crimp_percent=1.5,
                typical_count_tex_range=(80.0, 500.0),
                recommended_twist_factor_range=(260.0, 360.0),
                recommended_draft_range=(10.0, 22.0),
                max_spindle_speed_rpm=380.0,
                description="欧洲传统高档纤维，光泽优雅，吸湿透气，挺括有型，适合高端服装面料。"
            ),
            "silk": FiberProperties(
                fiber_type="silk",
                fiber_name="桑蚕丝",
                scientific_name="Bombyx mori",
                origin="动物蛋白纤维",
                color="珍珠白/乳黄",
                fiber_length_mm_avg=1200.0,
                fiber_length_mm_min=800.0,
                fiber_length_mm_max=1500.0,
                fiber_diameter_um=12.0,
                fineness_dtex=3.0,
                density_g_cm3=1.34,
                breaking_tenacity_cn_dtex=3.8,
                elongation_at_break_percent=20.0,
                moisture_regain_percent=11.0,
                modulus_gpa=10.0,
                friction_coefficient=0.22,
                crimp_percent=0.0,
                typical_count_tex_range=(10.0, 200.0),
                recommended_twist_factor_range=(350.0, 480.0),
                recommended_draft_range=(1.5, 5.0),
                max_spindle_speed_rpm=500.0,
                description="纤维皇后，光泽华贵，触感柔滑，穿着舒适，自古以来就是高档纺织品的首选原料。"
            ),
            "wool": FiberProperties(
                fiber_type="wool",
                fiber_name="绵羊毛",
                scientific_name="Ovis aries",
                origin="动物蛋白纤维",
                color="本白/米白",
                fiber_length_mm_avg=80.0,
                fiber_length_mm_min=50.0,
                fiber_length_mm_max=150.0,
                fiber_diameter_um=25.0,
                fineness_dtex=4.0,
                density_g_cm3=1.31,
                breaking_tenacity_cn_dtex=1.8,
                elongation_at_break_percent=35.0,
                moisture_regain_percent=15.0,
                modulus_gpa=3.5,
                friction_coefficient=0.30,
                crimp_percent=25.0,
                typical_count_tex_range=(50.0, 400.0),
                recommended_twist_factor_range=(300.0, 400.0),
                recommended_draft_range=(12.0, 28.0),
                max_spindle_speed_rpm=400.0,
                description="天然保暖纤维，弹性好，吸湿排汗，是毛纺和针织产品的主要原料。"
            )
        }

    @staticmethod
    def get_fiber(fiber_type: str) -> Optional[FiberProperties]:
        """获取指定纤维特性"""
        fibers = FiberDatabase.get_all_fibers()
        return fibers.get(fiber_type)


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


@dataclass
class SpinningObservation:
    """单条在线纺纱实测观测值"""
    timestamp: float
    yarn_count_tex: float
    actual_twist_per_meter: float
    twist_cv_percent: float
    breakage_count: int
    spindle_rpm: float
    draft_ratio: float
    yarn_strength_cn: float
    running_minutes: float


@dataclass
class IdentifiedParameters:
    """辨识得到的校正参数"""
    effective_twist_factor_correction: float
    effective_draft_efficiency_correction: float
    effective_friction_coefficient: float
    effective_break_sensitivity: float
    confidence_percent: float
    converged: bool


class OnlineParameterIdentifier:
    """
    基于递推最小二乘(RLS)+指数滑动平均(EMA)的在线纤维参数辨识器
    通过积累实测纺纱数据反向校正名义参数，实现"实验校准"
    """

    CALIBRATED_KEYS = [
        "effective_twist_factor_correction",
        "effective_draft_efficiency_correction",
        "effective_friction_coefficient",
        "effective_break_sensitivity"
    ]

    def __init__(self, fiber_type: str, window_size: int = 200, rls_forget_factor: float = 0.985):
        self.fiber_type = fiber_type
        self.window_size = window_size
        self.lambda_ = rls_forget_factor
        self.observations: List[SpinningObservation] = []
        self._theta = [1.0, 1.0, 1.0, 1.0]
        self._P = [[1000.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
        self._sample_count = 0
        self._converged = False
        self.nominal_twist_factor = 1.0
        self.nominal_draft_efficiency = 1.0
        self.nominal_friction_coefficient = 0.3
        self.nominal_break_sensitivity = 1.0
        self._init_nominals()

    def _init_nominals(self):
        fiber = FiberDatabase.get_fiber(self.fiber_type)
        if fiber:
            tmin, tmax = fiber.recommended_twist_factor_range
            self.nominal_twist_factor = (tmin + tmax) / 2
            dmin, dmax = fiber.recommended_draft_range
            self.nominal_draft_efficiency = 1.0 - (1.0 / ((dmin + dmax) / 2 + 1))
            self.nominal_friction_coefficient = fiber.friction_coefficient

    def add_observation(self, obs: SpinningObservation) -> IdentifiedParameters:
        """
        新增一条观测，运行RLS一步递推
        :return: 更新后的辨识参数
        """
        self.observations.append(obs)
        if len(self.observations) > self.window_size:
            self.observations.pop(0)
        self._sample_count += 1

        y = self._build_measurement(obs)
        phi = self._build_regressor(obs)
        self._rls_step(phi, y)

        if self._sample_count > 30:
            delta = sum(abs(t - 1.0) for t in self._theta) / 4.0
            self._converged = delta < 0.2
        return self.get_identified_params()

    @staticmethod
    def _build_measurement(obs: SpinningObservation) -> float:
        """构造观测标量：归一化的质量加权指标"""
        quality_term = max(0.5, 100.0 / max(obs.twist_cv_percent, 1.0))
        breakage_term = max(0.5, 1.0 / (obs.breakage_count + 0.5))
        strength_term = max(0.5, obs.yarn_strength_cn / 300.0)
        return math.log(max(quality_term * breakage_term * strength_term, 0.1))

    @staticmethod
    def _build_regressor(obs: SpinningObservation) -> List[float]:
        """构造4维回归向量 [捻度比, 牵伸效率比, 摩擦因子, 断头敏感度]"""
        target_twist = math.sqrt(max(obs.yarn_count_tex, 1.0)) * 380
        twist_ratio = obs.actual_twist_per_meter / max(target_twist, 1.0)
        draft_term = 1.0 / max(obs.draft_ratio, 1.0)
        rpm_term = obs.spindle_rpm / 400.0
        break_term = min(obs.breakage_count, 10) / 10.0
        return [twist_ratio, draft_term, rpm_term, break_term]

    def _rls_step(self, phi: List[float], y: float):
        """RLS核心递推：θ(k) = θ(k-1) + K·(y - φᵀθ)，含数值稳定与参数夹紧"""
        lam = self.lambda_
        P = self._P
        theta = self._theta

        Pphi = [sum(P[i][j] * phi[j] for j in range(4)) for i in range(4)]
        phiT_Pphi = sum(phi[i] * Pphi[i] for i in range(4))
        denom = lam + phiT_Pphi
        if abs(denom) < 1e-12:
            return
        K = [Pphi[i] / denom for i in range(4)]
        y_hat = sum(theta[i] * phi[i] for i in range(4))
        error = y - y_hat
        if math.isnan(error) or math.isinf(error):
            return
        for i in range(4):
            delta = K[i] * error
            if math.isnan(delta) or math.isinf(delta):
                continue
            theta[i] = theta[i] + delta
            theta[i] = max(0.01, min(5.0, theta[i]))

        KH = [[K[i] * sum(phi[k] * P[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
        for i in range(4):
            for j in range(4):
                new_val = (P[i][j] - KH[i][j]) / lam
                P[i][j] = max(-1e6, min(1e6, new_val)) if not math.isnan(new_val) else P[i][j]

    def get_identified_params(self) -> IdentifiedParameters:
        """获取辨识得到的校正参数"""
        samples = max(self._sample_count, 1)
        confidence = min(99.0, 30.0 + (samples / self.window_size) * 60.0 + (10.0 if self._converged else 0.0))
        return IdentifiedParameters(
            effective_twist_factor_correction=round(self._theta[0], 4),
            effective_draft_efficiency_correction=round(self._theta[1], 4),
            effective_friction_coefficient=round(self.nominal_friction_coefficient * (0.5 + 0.5 * self._theta[2]), 4),
            effective_break_sensitivity=round(self._theta[3], 4),
            confidence_percent=round(confidence, 2),
            converged=self._converged
        )

    def apply_correction_to_optimization(self, base_opt_result: Dict) -> Dict:
        """把辨识出的校正参数应用到标准优化结果，产生"自校准版"参数"""
        if "error" in base_opt_result:
            return base_opt_result
        if not self._converged and self._sample_count < 10:
            base_opt_result["online_identification"] = {
                "note": "样本不足，暂未校准（至少需要10条观测）",
                "samples_collected": self._sample_count
            }
            return base_opt_result
        ident = self.get_identified_params()
        twist = base_opt_result["twist_parameters"]
        twist["twist_factor_identified"] = round(
            twist["twist_factor"] * ident.effective_twist_factor_correction, 2
        )
        twist["twist_per_meter_identified"] = round(
            twist["twist_factor_identified"] / math.sqrt(max(base_opt_result["input_parameters"]["yarn_count_tex"], 1.0)), 2
        )
        draft = base_opt_result["draft_parameters"]
        draft["draft_efficiency_identified"] = round(
            min(0.99, draft["draft_efficiency"] * ident.effective_draft_efficiency_correction), 4
        )
        draft["breakage_risk_identified_percent"] = round(
            draft["breakage_risk_percent"] * ident.effective_break_sensitivity, 3
        )
        spindle = base_opt_result["spindle_parameters"]
        friction_adj = ident.effective_friction_coefficient / max(self.nominal_friction_coefficient, 1e-4)
        spindle["traveler_mass_mg_identified"] = round(
            spindle["traveler_mass_mg"] * friction_adj, 2
        )
        base_opt_result["online_identification"] = {
            "samples_used": len(self.observations),
            "window_size": self.window_size,
            "rls_forget_factor": self.lambda_,
            "identified_parameters": {
                "twist_factor_correction": ident.effective_twist_factor_correction,
                "draft_efficiency_correction": ident.effective_draft_efficiency_correction,
                "friction_coefficient": ident.effective_friction_coefficient,
                "break_sensitivity": ident.effective_break_sensitivity
            },
            "converged": ident.converged,
            "confidence_percent": ident.confidence_percent
        }
        return base_opt_result

    def get_convergence_report(self) -> Dict:
        """获取收敛诊断报告"""
        ident = self.get_identified_params()
        return {
            "fiber_type": self.fiber_type,
            "samples_collected": self._sample_count,
            "window_fill_percent": round(100.0 * len(self.observations) / self.window_size, 2),
            "converged": ident.converged,
            "confidence_percent": ident.confidence_percent,
            "parameter_deviation_percent": {
                k: round(100.0 * abs(v - 1.0), 2) for k, v in zip(
                    self.CALIBRATED_KEYS, self._theta
                )
            }
        }
