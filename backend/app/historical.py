"""
历史纺车技术对比模块
实现手摇纺车、脚踏纺车、水转大纺车的技术参数与效率质量对比分析
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class DataConfidence:
    """数据可信度标注（文献来源级别）"""
    data_level: str
    data_level_cn: str
    source_type: str
    uncertainty_percent: float
    references: List[str]


@dataclass
class SpinningWheelSpec:
    """纺车技术规格"""
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


class HistoricalSpinningWheels:
    """历史纺车数据库"""

    @staticmethod
    def get_all_specs() -> Dict[str, SpinningWheelSpec]:
        """获取所有历史纺车规格"""
        return {
            "hand_spun": SpinningWheelSpec(
                wheel_type="hand_spun",
                wheel_name="手摇纺车",
                era="古代",
                dynasty="新石器时代 - 宋元",
                year_range="约公元前5000年 - 公元1300年",
                power_source="人力手摇",
                num_spindles=1,
                wheel_radius_m=0.25,
                spindle_radius_m=0.01,
                transmission_ratio=1.0,
                mechanical_efficiency=0.45,
                max_spindle_rpm=120.0,
                typical_water_speed=None,
                typical_human_power_w=30.0,
                max_daily_production_kg=0.15,
                labor_requirement=1,
                material="竹、木、陶",
                description="最原始的纺纱工具，通过手摇纺轮带动锭子旋转。一人一锭，效率极低，但结构简单，家家可制。",
                yarn_quality_index=0.55,
                twist_uniformity_base=22.0,
                breakage_rate_base=0.08,
                typical_count_tex=200.0,
                power_consumption_w=30.0,
                floor_space_m2=0.5,
                cost_relative=1.0,
                confidence=DataConfidence(
                    data_level="B",
                    data_level_cn="可信级（实物遗存+文献互证）",
                    source_type="考古实物 + 农书文献记载",
                    uncertainty_percent=15.0,
                    references=[
                        "《天工开物·乃服》卷",
                        "浙江余姚河姆渡遗址纺轮出土报告",
                        "中国纺织科技史（1984）"
                    ]
                )
            ),
            "foot_treadle": SpinningWheelSpec(
                wheel_type="foot_treadle",
                wheel_name="脚踏纺车",
                era="中古",
                dynasty="宋元 - 明清",
                year_range="约公元1000年 - 1900年",
                power_source="人力脚踏",
                num_spindles=3,
                wheel_radius_m=0.45,
                spindle_radius_m=0.012,
                transmission_ratio=3.5,
                mechanical_efficiency=0.60,
                max_spindle_rpm=250.0,
                typical_water_speed=None,
                typical_human_power_w=60.0,
                max_daily_production_kg=0.8,
                labor_requirement=1,
                material="木、铁件",
                description="通过脚踏板和偏心轮驱动大绳轮，可同时带动3锭。解放双手用于喂棉，产量提高3-5倍。",
                yarn_quality_index=0.70,
                twist_uniformity_base=15.0,
                breakage_rate_base=0.04,
                typical_count_tex=140.0,
                power_consumption_w=60.0,
                floor_space_m2=1.5,
                cost_relative=5.0,
                confidence=DataConfidence(
                    data_level="B",
                    data_level_cn="可信级（实物遗存+文献互证）",
                    source_type="传世实物 + 王祯《农书》等农书图解",
                    uncertainty_percent=12.0,
                    references=[
                        "王祯《农书·农器图谱·织纴门》",
                        "黄道婆纺织技术考证（上海纺织博物馆）",
                        "清代江南织造局档案残卷"
                    ]
                )
            ),
            "water_wheel": SpinningWheelSpec(
                wheel_type="water_wheel",
                wheel_name="水转大纺车",
                era="前近代",
                dynasty="宋元 - 清",
                year_range="约公元1200年 - 1900年",
                power_source="水力驱动",
                num_spindles=32,
                wheel_radius_m=2.5,
                spindle_radius_m=0.015,
                transmission_ratio=12.0,
                mechanical_efficiency=0.72,
                max_spindle_rpm=400.0,
                typical_water_speed=2.5,
                typical_human_power_w=None,
                max_daily_production_kg=25.0,
                labor_requirement=4,
                material="木架、铁轴、竹篾",
                description="古代水力纺纱机械巅峰之作。大水轮通过皮带传动带动三十二锭同时运转，日夜不息，产量为脚踏纺车的30倍以上。",
                yarn_quality_index=0.82,
                twist_uniformity_base=8.0,
                breakage_rate_base=0.02,
                typical_count_tex=100.0,
                power_consumption_w=3500.0,
                floor_space_m2=20.0,
                cost_relative=100.0,
                confidence=DataConfidence(
                    data_level="C",
                    data_level_cn="参考级（文献记述+工艺还原）",
                    source_type="农书记载 + 考古推测 + 现代工艺还原实验",
                    uncertainty_percent=25.0,
                    references=[
                        "王祯《农书·水转大纺车》图文",
                        "《梓人遗制》中原图复原研究",
                        "2018年中国丝绸博物馆水转大纺车复原实验报告",
                        "元代松江府棉纺业遗址发掘报告（2009）"
                    ]
                )
            )
        }

    @staticmethod
    def get_spec(wheel_type: str) -> Optional[SpinningWheelSpec]:
        """获取指定纺车规格"""
        specs = HistoricalSpinningWheels.get_all_specs()
        return specs.get(wheel_type)


class EfficiencyCalculator:
    """纺车效率计算器"""

    @staticmethod
    def _build_confidence_interval(value: float, spec: SpinningWheelSpec, uncertainty_scale: float = 1.0) -> Dict:
        """基于文献可信度构造置信区间"""
        if spec.confidence:
            unc = spec.confidence.uncertainty_percent / 100.0
        else:
            unc = 0.15
        half_width = value * unc * uncertainty_scale
        return {
            "point_estimate": round(value, 4),
            "lower_bound": round(max(value - half_width, 0.0), 6),
            "upper_bound": round(value + half_width, 6),
            "half_width_percent": round(unc * uncertainty_scale * 100, 2)
        }

    @staticmethod
    def calculate_efficiency_metrics(
        spec: SpinningWheelSpec,
        operating_hours: float = 10.0,
        utilization_rate: float = 0.8
    ) -> Dict:
        """计算效率指标"""
        effective_hours = operating_hours * utilization_rate
        daily_production = spec.max_daily_production_kg * utilization_rate

        if spec.typical_human_power_w:
            energy_input_kwh = spec.typical_human_power_w * effective_hours / 1000
        elif spec.typical_water_speed is not None:
            water_power = 0.5 * 1000 * math.pi * spec.wheel_radius_m ** 2 * spec.typical_water_speed ** 3 * 0.3
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
                "daily_production_kg": EfficiencyCalculator._build_confidence_interval(daily_production, spec, 1.0),
                "energy_efficiency_kg_per_kwh": EfficiencyCalculator._build_confidence_interval(energy_efficiency, spec, 1.3),
                "labor_efficiency_kg_per_person_day": EfficiencyCalculator._build_confidence_interval(labor_efficiency, spec, 1.0)
            }
        }
        if spec.confidence:
            result["data_confidence"] = {
                "level": spec.confidence.data_level,
                "level_cn": spec.confidence.data_level_cn,
                "source": spec.confidence.source_type,
                "uncertainty_percent": spec.confidence.uncertainty_percent,
                "references": spec.confidence.references
            }
        return result

    @staticmethod
    def calculate_quality_metrics(
        spec: SpinningWheelSpec,
        yarn_count_tex: float = None,
        target_twist_per_m: float = None
    ) -> Dict:
        """计算纱线质量指标"""
        actual_count = yarn_count_tex or spec.typical_count_tex
        twist_cv = spec.twist_uniformity_base
        if actual_count < spec.typical_count_tex:
            twist_cv *= (1 + 0.3 * (spec.typical_count_tex - actual_count) / spec.typical_count_tex)
        elif actual_count > spec.typical_count_tex:
            twist_cv *= (1 - 0.15 * (actual_count - spec.typical_count_tex) / actual_count)

        breakage_rate = spec.breakage_rate_base
        if target_twist_per_m:
            optimal_twist = math.sqrt(actual_count) * 40
            twist_deviation = abs(target_twist_per_m - optimal_twist) / optimal_twist
            breakage_rate *= (1 + twist_deviation * 2)

        evenness_cv = twist_cv * 1.5
        strength_cv = twist_cv * 1.2

        return {
            "wheel_type": spec.wheel_type,
            "yarn_count_tex": round(actual_count, 2),
            "twist_uniformity_cv_percent": round(twist_cv, 2),
            "breakage_rate_percent": round(breakage_rate * 100, 3),
            "yarn_evenness_cv_percent": round(evenness_cv, 2),
            "yarn_strength_cv_percent": round(strength_cv, 2),
            "overall_quality_index": round(spec.yarn_quality_index * (1 - twist_cv / 30), 4),
            "yarn_grade": EfficiencyCalculator._determine_grade(twist_cv, breakage_rate)
        }

    @staticmethod
    def _determine_grade(twist_cv: float, breakage_rate: float) -> str:
        """评定纱线等级"""
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
        utilization_rate: float = 0.8
    ) -> Dict:
        """计算多种纺车对比结果"""
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
                    "description": spec.description
                },
                "efficiency": efficiency,
                "quality": quality
            }
            results["details"].append(detail)

        if results["details"]:
            water = next((d for d in results["details"] if d["spec"]["wheel_type"] == "water_wheel"), None)
            if water:
                for d in results["details"]:
                    wt = d["spec"]["wheel_type"]
                    results["metrics"][f"{wt}_vs_water_production_ratio"] = round(
                        water["efficiency"]["daily_production_kg"] / max(d["efficiency"]["daily_production_kg"], 0.0001), 2
                    )
                    results["metrics"][f"{wt}_vs_water_labor_ratio"] = round(
                        water["efficiency"]["labor_efficiency_kg_per_person_day"] / max(d["efficiency"]["labor_efficiency_kg_per_person_day"], 0.0001), 2
                    )

            results["summary"] = {
                "total_wheel_types": len(results["details"]),
                "best_production": max(d["efficiency"]["daily_production_kg"] for d in results["details"]),
                "best_labor_efficiency": max(d["efficiency"]["labor_efficiency_kg_per_person_day"] for d in results["details"]),
                "best_quality": max(d["quality"]["overall_quality_index"] for d in results["details"]),
                "operating_hours": operating_hours,
                "utilization_rate": utilization_rate
            }

        return results
