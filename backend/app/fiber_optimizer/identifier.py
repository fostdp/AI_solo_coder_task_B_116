"""
棉麻丝纤维特性与纺纱参数优化模块
基于不同纤维的物理特性，智能调整牵伸倍数、加捻参数等工艺参数
"""
from __future__ import annotations

import math
from typing import Dict, List

from .database import FiberDatabase
from .models import IdentifiedParameters, SpinningObservation


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
