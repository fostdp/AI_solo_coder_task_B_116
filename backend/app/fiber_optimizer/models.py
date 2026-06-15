"""
棉麻丝纤维特性与纺纱参数优化模块
基于不同纤维的物理特性，智能调整牵伸倍数、加捻参数等工艺参数
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


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
