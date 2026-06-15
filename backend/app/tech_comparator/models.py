from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DataConfidence:
    data_level: str
    data_level_cn: str
    source_type: str
    uncertainty_percent: float
    references: List[str]


@dataclass
class SpinningWheelSpec:
    wheel_type: str
    wheel_name: str
    era: str
    dynasty: str
    year_range: str
    power_source: str
    num_spindles: int
    wheel_radius_m: float
    spindle_radius_m: float
    transmission_ratio: float
    mechanical_efficiency: float
    max_spindle_rpm: float
    typical_water_speed: Optional[float]
    typical_human_power_w: Optional[float]
    max_daily_production_kg: float
    labor_requirement: int
    material: str
    description: str
    yarn_quality_index: float
    twist_uniformity_base: float
    breakage_rate_base: float
    typical_count_tex: float
    power_consumption_w: float
    floor_space_m2: float
    cost_relative: float
    confidence: Optional[DataConfidence] = None
