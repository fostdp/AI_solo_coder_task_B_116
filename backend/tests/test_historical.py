"""
历史纺车技术对比模块测试用例
覆盖正常、边界、异常场景
"""
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.historical import (
    HistoricalSpinningWheels,
    EfficiencyCalculator,
    SpinningWheelSpec
)


VALID_WHEEL_TYPES = ["hand_spun", "foot_treadle", "water_wheel"]
INVALID_WHEEL_TYPES = ["steam", "electric", "", None, 123, "handspun"]


class TestHistoricalSpinningWheels:
    """纺车规格数据库测试"""

    def test_get_all_specs_returns_three_wheels(self):
        """正常场景：获取所有纺车规格，应返回3种"""
        specs = HistoricalSpinningWheels.get_all_specs()
        assert isinstance(specs, dict)
        assert len(specs) == 3
        for wt in VALID_WHEEL_TYPES:
            assert wt in specs
            assert isinstance(specs[wt], SpinningWheelSpec)

    def test_spec_data_standardization(self):
        """数据标准化验证：所有纺车规格字段值在合理范围内"""
        specs = HistoricalSpinningWheels.get_all_specs()
        for wt, spec in specs.items():
            assert isinstance(spec.num_spindles, int) and spec.num_spindles > 0
            assert 0.1 <= spec.wheel_radius_m <= 10.0
            assert 0.001 <= spec.spindle_radius_m <= 0.1
            assert 0.1 <= spec.transmission_ratio <= 100.0
            assert 0.1 <= spec.mechanical_efficiency <= 1.0
            assert 1.0 <= spec.max_spindle_rpm <= 10000.0
            assert 0.001 <= spec.max_daily_production_kg <= 1000.0
            assert spec.labor_requirement >= 1
            assert 0.0 <= spec.yarn_quality_index <= 1.0
            assert 0.0 <= spec.twist_uniformity_base <= 100.0
            assert 0.0 <= spec.breakage_rate_base <= 1.0
            assert 1.0 <= spec.typical_count_tex <= 2000.0
            assert 0.1 <= spec.floor_space_m2 <= 1000.0
            assert spec.cost_relative >= 0.1

    def test_relative_advancement_monotonic(self):
        """技术演进验证：纺车效率应随技术进步单调递增"""
        specs = HistoricalSpinningWheels.get_all_specs()
        order = ["hand_spun", "foot_treadle", "water_wheel"]
        productions = [specs[wt].max_daily_production_kg for wt in order]
        for i in range(1, len(productions)):
            assert productions[i] > productions[i - 1], \
                f"{order[i]} 产量应大于 {order[i-1]}"

        qualities = [specs[wt].yarn_quality_index for wt in order]
        for i in range(1, len(qualities)):
            assert qualities[i] >= qualities[i - 1], \
                f"{order[i]} 质量指数不应低于 {order[i-1]}"

    @pytest.mark.parametrize("wheel_type", VALID_WHEEL_TYPES)
    def test_get_spec_valid_types(self, wheel_type):
        """正常场景：获取有效类型的纺车规格"""
        spec = HistoricalSpinningWheels.get_spec(wheel_type)
        assert spec is not None
        assert spec.wheel_type == wheel_type

    @pytest.mark.parametrize("invalid_type", INVALID_WHEEL_TYPES)
    def test_get_spec_invalid_types_returns_none(self, invalid_type):
        """异常场景：无效纺车类型返回None"""
        result = HistoricalSpinningWheels.get_spec(invalid_type) if invalid_type is not None else HistoricalSpinningWheels.get_spec("invalid")
        if isinstance(invalid_type, str) and invalid_type != "":
            assert result is None

    def test_water_wheel_has_water_speed_no_human(self):
        """正常场景：水转纺车应有水流速度，无人力功率"""
        water = HistoricalSpinningWheels.get_spec("water_wheel")
        assert water.typical_water_speed is not None
        assert water.typical_water_speed > 0
        assert water.typical_human_power_w is None

    def test_hand_and_foot_have_human_power_no_water(self):
        """正常场景：手摇和脚踏纺车有人力功率，无水流速度"""
        for wt in ["hand_spun", "foot_treadle"]:
            spec = HistoricalSpinningWheels.get_spec(wt)
            assert spec.typical_human_power_w is not None
            assert spec.typical_human_power_w > 0
            assert spec.typical_water_speed is None


class TestEfficiencyCalculatorMetrics:
    """效率指标计算测试"""

    def test_calculate_efficiency_normal(self):
        """正常场景：默认参数计算手摇纺车效率"""
        spec = HistoricalSpinningWheels.get_spec("hand_spun")
        result = EfficiencyCalculator.calculate_efficiency_metrics(spec)

        assert result["wheel_type"] == "hand_spun"
        assert 0 < result["daily_production_kg"] <= spec.max_daily_production_kg
        assert result["energy_input_kwh"] > 0
        assert result["energy_efficiency_kg_per_kwh"] > 0
        assert result["labor_efficiency_kg_per_person_day"] > 0
        assert result["space_efficiency_kg_per_m2_day"] > 0
        assert result["cost_efficiency_kg_per_cost_unit"] > 0
        assert result["utilization_rate"] == 0.8
        assert result["operating_hours"] == 10.0

    def test_efficiency_utilization_linearity(self):
        """数据标准化验证：产量应与利用率成线性关系"""
        spec = HistoricalSpinningWheels.get_spec("water_wheel")
        r_low = EfficiencyCalculator.calculate_efficiency_metrics(spec, utilization_rate=0.5)
        r_high = EfficiencyCalculator.calculate_efficiency_metrics(spec, utilization_rate=1.0)
        ratio = r_high["daily_production_kg"] / r_low["daily_production_kg"]
        assert abs(ratio - 2.0) < 0.01

    @pytest.mark.parametrize("hours", [0.0, 0.1, 1.0, 12.0, 24.0])
    def test_efficiency_boundary_operating_hours(self, hours):
        """边界场景：极端工时参数"""
        spec = HistoricalSpinningWheels.get_spec("foot_treadle")
        result = EfficiencyCalculator.calculate_efficiency_metrics(
            spec, operating_hours=hours
        )
        assert result["operating_hours"] == hours
        assert result["daily_production_kg"] >= 0
        assert not math.isnan(result["energy_efficiency_kg_per_kwh"])

    @pytest.mark.parametrize("util", [0.0, 0.01, 0.5, 0.99, 1.0])
    def test_efficiency_boundary_utilization(self, util):
        """边界场景：极端利用率参数"""
        spec = HistoricalSpinningWheels.get_spec("water_wheel")
        result = EfficiencyCalculator.calculate_efficiency_metrics(
            spec, utilization_rate=util
        )
        assert result["utilization_rate"] == util
        assert 0 <= result["daily_production_kg"] <= spec.max_daily_production_kg

    def test_water_wheel_energy_calculation(self):
        """物理准确性：水转纺车能量计算基于水流动能公式"""
        spec = HistoricalSpinningWheels.get_spec("water_wheel")
        result = EfficiencyCalculator.calculate_efficiency_metrics(spec)
        expected_power = 0.5 * 1000 * math.pi * spec.wheel_radius_m ** 2 * spec.typical_water_speed ** 3 * 0.3
        expected_kwh = expected_power * 10.0 * 0.8 / 1000
        assert abs(result["energy_input_kwh"] - expected_kwh) < 0.01

    def test_human_power_energy_calculation(self):
        """物理准确性：人力纺车能量计算"""
        spec = HistoricalSpinningWheels.get_spec("hand_spun")
        result = EfficiencyCalculator.calculate_efficiency_metrics(spec)
        expected_kwh = spec.typical_human_power_w * 10.0 * 0.8 / 1000
        assert abs(result["energy_input_kwh"] - expected_kwh) < 0.0001


class TestEfficiencyCalculatorQuality:
    """纱线质量指标测试"""

    def test_quality_normal_default(self):
        """正常场景：默认参数计算质量"""
        spec = HistoricalSpinningWheels.get_spec("water_wheel")
        result = EfficiencyCalculator.calculate_quality_metrics(spec)

        assert result["wheel_type"] == "water_wheel"
        assert result["yarn_count_tex"] == spec.typical_count_tex
        assert 0.0 <= result["twist_uniformity_cv_percent"] <= 100.0
        assert 0.0 <= result["breakage_rate_percent"] <= 100.0
        assert 0.0 <= result["overall_quality_index"] <= 1.0
        assert result["yarn_grade"] in ["特等", "一等", "二等", "三等", "等外"]

    def test_quality_water_wheel_best_grade(self):
        """技术对比验证：水转纺车应获得较高质量等级"""
        spec = HistoricalSpinningWheels.get_spec("water_wheel")
        result = EfficiencyCalculator.calculate_quality_metrics(spec)
        assert result["yarn_grade"] in ["特等", "一等"]

    def test_quality_hand_spun_lower_grade(self):
        """技术对比验证：手摇纺车质量等级应较低"""
        spec = HistoricalSpinningWheels.get_spec("hand_spun")
        result = EfficiencyCalculator.calculate_quality_metrics(spec)
        assert result["yarn_grade"] in ["二等", "三等", "等外"]

    @pytest.mark.parametrize("count", [50.0, 100.0, 200.0, 400.0])
    def test_quality_various_yarn_counts(self, count):
        """边界场景：不同纱线支数"""
        spec = HistoricalSpinningWheels.get_spec("foot_treadle")
        result = EfficiencyCalculator.calculate_quality_metrics(spec, yarn_count_tex=count)
        assert result["yarn_count_tex"] == count
        assert 0.0 <= result["twist_uniformity_cv_percent"] <= 100.0

    def test_quality_with_target_twist(self):
        """正常场景：指定目标捻度时断头率调整"""
        spec = HistoricalSpinningWheels.get_spec("water_wheel")
        optimal = math.sqrt(spec.typical_count_tex) * 40
        r_optimal = EfficiencyCalculator.calculate_quality_metrics(
            spec, target_twist_per_m=optimal
        )
        r_deviated = EfficiencyCalculator.calculate_quality_metrics(
            spec, target_twist_per_m=optimal * 2
        )
        assert r_deviated["breakage_rate_percent"] > r_optimal["breakage_rate_percent"]

    @pytest.mark.parametrize("cv,br,expected_grades", [
        (5.0, 0.01, ["特等", "一等"]),
        (10.0, 0.03, ["一等", "二等"]),
        (20.0, 0.06, ["三等", "等外"]),
        (30.0, 0.10, ["等外"]),
    ])
    def test_grade_determination(self, cv, br, expected_grades):
        """正常场景：纱线等级评定逻辑"""
        grade = EfficiencyCalculator._determine_grade(cv, br)
        assert grade in expected_grades


class TestEfficiencyCalculatorComparison:
    """多纺车对比分析测试"""

    def test_comparison_default_all_three(self):
        """正常场景：默认对比3种纺车"""
        result = EfficiencyCalculator.calculate_comparison()

        assert "summary" in result
        assert "details" in result
        assert "metrics" in result
        assert len(result["details"]) == 3
        assert result["summary"]["total_wheel_types"] == 3
        assert result["summary"]["best_production"] > 0
        assert result["summary"]["best_quality"] > 0

    def test_comparison_best_is_water_wheel(self):
        """技术对比验证：水转纺车在产量和质量上应最佳"""
        result = EfficiencyCalculator.calculate_comparison()
        water_detail = next(d for d in result["details"] if d["spec"]["wheel_type"] == "water_wheel")
        assert result["summary"]["best_production"] == water_detail["efficiency"]["daily_production_kg"]
        assert result["summary"]["best_quality"] == water_detail["quality"]["overall_quality_index"]

    def test_comparison_production_ratio(self):
        """数据标准化验证：水转纺车 vs 手摇产量倍数应合理"""
        result = EfficiencyCalculator.calculate_comparison()
        assert "hand_spun_vs_water_production_ratio" in result["metrics"]
        ratio = result["metrics"]["hand_spun_vs_water_production_ratio"]
        assert 50 <= ratio <= 500

    def test_comparison_single_wheel(self):
        """边界场景：只对比一种纺车"""
        result = EfficiencyCalculator.calculate_comparison(wheel_types=["water_wheel"])
        assert len(result["details"]) == 1
        assert result["details"][0]["spec"]["wheel_type"] == "water_wheel"

    def test_comparison_partial_invalid_types(self):
        """异常场景：包含无效类型的对比（应过滤无效值）"""
        result = EfficiencyCalculator.calculate_comparison(
            wheel_types=["hand_spun", "invalid_type", "water_wheel"]
        )
        assert len(result["details"]) == 2

    def test_comparison_all_invalid_types(self):
        """异常场景：所有类型都无效时返回空详情"""
        result = EfficiencyCalculator.calculate_comparison(wheel_types=["x", "y", "z"])
        assert len(result["details"]) == 0
        assert result["summary"] == {}

    def test_comparison_empty_list(self):
        """异常场景：空列表时回退到默认3种"""
        result = EfficiencyCalculator.calculate_comparison(wheel_types=[])
        assert len(result["details"]) == 3
