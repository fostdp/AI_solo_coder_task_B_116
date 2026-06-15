from __future__ import annotations

from typing import Dict, Optional

from .models import DataConfidence, SpinningWheelSpec


class HistoricalSpinningWheels:
    """历史纺车数据库"""

    @staticmethod
    def get_all_specs() -> Dict[str, SpinningWheelSpec]:
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
        specs = HistoricalSpinningWheels.get_all_specs()
        return specs.get(wheel_type)
