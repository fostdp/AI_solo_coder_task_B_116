"""
纤维参数优化模块测试用例
覆盖正常、边界、异常场景
"""
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.fiber_optimization import (
    FiberDatabase,
    SpinningParameterOptimizer,
    FiberProperties
)


VALID_FIBERS = ["cotton", "hemp", "flax", "silk", "wool"]
INVALID_FIBERS = ["nylon", "polyester", "", None, "cotton_", 123]


class TestFiberDatabase:
    """纤维特性数据库测试"""

    def test_get_all_fibers_returns_five(self):
        """正常场景：数据库应返回5种纤维"""
        fibers = FiberDatabase.get_all_fibers()
        assert isinstance(fibers, dict)
        assert len(fibers) == 5
        for ft in VALID_FIBERS:
            assert ft in fibers
            assert isinstance(fibers[ft], FiberProperties)

    def test_fiber_data_standardization(self):
        """数据标准化验证：所有纤维参数在合理物理范围内"""
        fibers = FiberDatabase.get_all_fibers()
        for ft, f in fibers.items():
            assert 5.0 <= f.fiber_length_mm_avg <= 5000.0
            assert f.fiber_length_mm_min <= f.fiber_length_mm_avg <= f.fiber_length_mm_max
            assert 0.1 <= f.fiber_diameter_um <= 200.0
            assert 0.1 <= f.fineness_dtex <= 50.0
            assert 0.5 <= f.density_g_cm3 <= 5.0
            assert 0.1 <= f.breaking_tenacity_cn_dtex <= 20.0
            assert 0.5 <= f.elongation_at_break_percent <= 100.0
            assert 0.0 <= f.moisture_regain_percent <= 50.0
            assert 0.1 <= f.modulus_gpa <= 100.0
            assert 0.05 <= f.friction_coefficient <= 1.0
            assert 0.0 <= f.crimp_percent <= 100.0
            assert f.typical_count_tex_range[0] < f.typical_count_tex_range[1]
            assert f.recommended_twist_factor_range[0] < f.recommended_twist_factor_range[1]
            assert f.recommended_draft_range[0] < f.recommended_draft_range[1]
            assert 100 <= f.max_spindle_speed_rpm <= 10000

    def test_fiber_physical_differences(self):
        """纤维特性差异验证：蚕丝应最长，羊毛卷曲最高"""
        fibers = FiberDatabase.get_all_fibers()
        silk = fibers["silk"]
        wool = fibers["wool"]
        assert silk.fiber_length_mm_avg > 500, "蚕丝平均长度应超过500mm"
        assert wool.crimp_percent > 20, "羊毛卷曲度应超过20%"
        assert silk.crimp_percent < 1, "蚕丝卷曲度应接近0"

    @pytest.mark.parametrize("fiber_type", VALID_FIBERS)
    def test_get_fiber_valid(self, fiber_type):
        """正常场景：获取有效纤维"""
        f = FiberDatabase.get_fiber(fiber_type)
        assert f is not None
        assert f.fiber_type == fiber_type

    @pytest.mark.parametrize("invalid", INVALID_FIBERS)
    def test_get_fiber_invalid_returns_none(self, invalid):
        """异常场景：无效纤维类型返回None"""
        if isinstance(invalid, str) and invalid != "":
            assert FiberDatabase.get_fiber(invalid) is None


class TestOptimalTwist:
    """最优捻度计算测试"""

    def test_twist_normal_cotton(self):
        """正常场景：棉花默认支数的最优捻度"""
        fiber = FiberDatabase.get_fiber("cotton")
        result = SpinningParameterOptimizer.calculate_optimal_twist(fiber, 100.0)

        assert result["fiber_type"] == "cotton"
        assert result["yarn_count_tex"] == 100.0
        assert result["twist_direction"] == "Z"
        tf_min, tf_max = fiber.recommended_twist_factor_range
        assert tf_min <= result["twist_factor"] <= tf_max
        assert result["twist_per_meter"] > 0
        assert result["twist_per_inch"] > 0
        assert 0 < result["twist_angle_deg"] < 90
        assert len(result["twist_range_per_meter"]) == 2
        assert result["twist_range_per_meter"][0] < result["twist_range_per_meter"][1]

    def test_twist_formula_correctness(self):
        """物理准确性：捻度公式 T = α / √Ntex 验证"""
        fiber = FiberDatabase.get_fiber("cotton")
        result = SpinningParameterOptimizer.calculate_optimal_twist(fiber, 100.0)
        expected_twist = result["twist_factor"] / math.sqrt(100.0)
        assert abs(result["twist_per_meter"] - expected_twist) < 0.01

    def test_twist_finer_yarn_higher_twist(self):
        """参数合理性：纱支越细，捻度应越高"""
        fiber = FiberDatabase.get_fiber("cotton")
        r_fine = SpinningParameterOptimizer.calculate_optimal_twist(fiber, 30.0)
        r_coarse = SpinningParameterOptimizer.calculate_optimal_twist(fiber, 300.0)
        assert r_fine["twist_per_meter"] > r_coarse["twist_per_meter"]

    def test_silk_needs_higher_twist_factor(self):
        """参数合理性：蚕丝捻系数应高于棉麻"""
        silk = FiberDatabase.get_fiber("silk")
        cotton = FiberDatabase.get_fiber("cotton")
        r_silk = SpinningParameterOptimizer.calculate_optimal_twist(silk, 100.0)
        r_cotton = SpinningParameterOptimizer.calculate_optimal_twist(cotton, 100.0)
        assert r_silk["twist_factor"] > r_cotton["twist_factor"]

    @pytest.mark.parametrize("count", [10.0, 30.0, 100.0, 300.0, 800.0])
    def test_twist_boundary_counts(self, count):
        """边界场景：不同纱线支数计算"""
        fiber = FiberDatabase.get_fiber("hemp")
        result = SpinningParameterOptimizer.calculate_optimal_twist(fiber, count)
        assert result["yarn_count_tex"] == count
        assert result["twist_per_meter"] > 0

    @pytest.mark.parametrize("direction", ["Z", "S", "z", "s"])
    def test_twist_direction_preserved(self, direction):
        """正常场景：捻向参数正确传递"""
        fiber = FiberDatabase.get_fiber("silk")
        result = SpinningParameterOptimizer.calculate_optimal_twist(fiber, 50.0, twist_direction=direction)
        assert result["twist_direction"] == direction


class TestOptimalDraft:
    """最优牵伸计算测试"""

    def test_draft_normal_cotton(self):
        """正常场景：棉花默认牵伸计算"""
        fiber = FiberDatabase.get_fiber("cotton")
        result = SpinningParameterOptimizer.calculate_optimal_draft(fiber, 3000.0, 100.0)

        assert result["fiber_type"] == "cotton"
        assert result["roving_count_tex"] == 3000.0
        assert result["yarn_count_tex"] == 100.0
        actual_draft = 3000.0 / 100.0
        assert abs(result["actual_draft_ratio"] - actual_draft) < 0.01
        d_min, d_max = fiber.recommended_draft_range
        assert d_min <= result["optimal_draft_ratio"] <= d_max
        assert 0.5 <= result["draft_efficiency"] <= 1.0
        assert 0.0 <= result["breakage_risk_percent"] <= 20.0
        assert result["roller_pressure_n"] > 0
        assert isinstance(result["advice"], str)
        assert len(result["advice"]) > 0

    def test_draft_ratio_formula(self):
        """物理准确性：牵伸倍数 = 粗纱定量 / 细纱定量"""
        fiber = FiberDatabase.get_fiber("flax")
        result = SpinningParameterOptimizer.calculate_optimal_draft(fiber, 2000.0, 100.0)
        assert abs(result["actual_draft_ratio"] - 20.0) < 0.01

    def test_high_draft_increases_breakage_risk(self):
        """参数合理性：牵伸倍数越大，断头风险越高"""
        fiber = FiberDatabase.get_fiber("cotton")
        r_low = SpinningParameterOptimizer.calculate_optimal_draft(fiber, 1500.0, 100.0)
        r_high = SpinningParameterOptimizer.calculate_optimal_draft(fiber, 4000.0, 100.0)
        assert r_high["breakage_risk_percent"] > r_low["breakage_risk_percent"]

    def test_low_draft_triggers_pre_drawing_advice(self):
        """参数合理性：牵伸过低应给出预并条建议"""
        fiber = FiberDatabase.get_fiber("cotton")
        result = SpinningParameterOptimizer.calculate_optimal_draft(fiber, 500.0, 100.0)
        assert "预并条" in result["advice"]

    def test_high_draft_triggers_warning(self):
        """参数合理性：牵伸过高应给出减少粗纱定量建议"""
        fiber = FiberDatabase.get_fiber("cotton")
        result = SpinningParameterOptimizer.calculate_optimal_draft(fiber, 10000.0, 100.0)
        assert ("减少" in result["advice"]) or ("牵伸区" in result["advice"])

    @pytest.mark.parametrize("roving,yarn", [
        (500.0, 50.0), (2000.0, 100.0), (5000.0, 200.0), (0.1, 0.01)
    ])
    def test_draft_boundary_values(self, roving, yarn):
        """边界场景：极端粗细纱组合"""
        fiber = FiberDatabase.get_fiber("wool")
        result = SpinningParameterOptimizer.calculate_optimal_draft(fiber, roving, yarn)
        assert result["actual_draft_ratio"] > 0
        assert not math.isnan(result["draft_efficiency"])


class TestSpindleSpeed:
    """锭子转速计算测试"""

    def test_spindle_normal_balanced(self):
        """正常场景：balanced优先级的锭速计算"""
        fiber = FiberDatabase.get_fiber("cotton")
        result = SpinningParameterOptimizer.calculate_spindle_speed(fiber, 100.0, 350.0)

        assert result["quality_priority"] == "balanced"
        assert result["calculated_spindle_rpm"] > 0
        assert 0 < result["recommended_spindle_rpm"] <= fiber.max_spindle_speed_rpm
        assert result["delivery_speed_m_min"] > 0
        assert result["traveler_mass_mg"] > 0
        assert result["production_rate_g_per_hour_per_spindle"] > 0
        assert result["spinning_tension_cn"] > 0

    def test_speed_factor_quality_vs_speed(self):
        """参数合理性：speed优先级锭速应高于quality优先级"""
        fiber = FiberDatabase.get_fiber("silk")
        r_quality = SpinningParameterOptimizer.calculate_spindle_speed(fiber, 50.0, 800.0, "quality")
        r_speed = SpinningParameterOptimizer.calculate_spindle_speed(fiber, 50.0, 800.0, "speed")
        assert r_speed["recommended_spindle_rpm"] > r_quality["recommended_spindle_rpm"]

    def test_traveler_mass_scales_with_count(self):
        """参数合理性：纱越粗，钢丝圈越重"""
        fiber = FiberDatabase.get_fiber("cotton")
        r_fine = SpinningParameterOptimizer.calculate_spindle_speed(fiber, 30.0, 400.0)
        r_coarse = SpinningParameterOptimizer.calculate_spindle_speed(fiber, 300.0, 400.0)
        assert r_coarse["traveler_mass_mg"] > r_fine["traveler_mass_mg"]

    def test_silk_lighter_traveler(self):
        """参数合理性：蚕丝钢丝圈应轻于棉"""
        cotton = FiberDatabase.get_fiber("cotton")
        silk = FiberDatabase.get_fiber("silk")
        r_cotton = SpinningParameterOptimizer.calculate_spindle_speed(cotton, 100.0, 350.0)
        r_silk = SpinningParameterOptimizer.calculate_spindle_speed(silk, 100.0, 400.0)
        assert r_silk["traveler_mass_mg"] < r_cotton["traveler_mass_mg"]

    def test_hemp_heavier_traveler(self):
        """参数合理性：苎麻钢丝圈应重于棉"""
        cotton = FiberDatabase.get_fiber("cotton")
        hemp = FiberDatabase.get_fiber("hemp")
        r_cotton = SpinningParameterOptimizer.calculate_spindle_speed(cotton, 200.0, 350.0)
        r_hemp = SpinningParameterOptimizer.calculate_spindle_speed(hemp, 200.0, 350.0)
        assert r_hemp["traveler_mass_mg"] > r_cotton["traveler_mass_mg"]

    @pytest.mark.parametrize("priority", ["quality", "balanced", "speed"])
    def test_all_quality_priorities(self, priority):
        """正常场景：三种质量优先级均可计算"""
        fiber = FiberDatabase.get_fiber("wool")
        result = SpinningParameterOptimizer.calculate_spindle_speed(fiber, 150.0, 300.0, priority)
        assert result["quality_priority"] == priority
        assert result["recommended_spindle_rpm"] > 0


class TestFullOptimization:
    """完整纺纱参数优化测试"""

    def test_full_optimization_cotton_default(self):
        """正常场景：棉花完整优化"""
        result = SpinningParameterOptimizer.full_spinning_optimization("cotton")

        assert "error" not in result
        assert "fiber_info" in result
        assert "input_parameters" in result
        assert "twist_parameters" in result
        assert "draft_parameters" in result
        assert "spindle_parameters" in result
        assert "warnings" in result
        assert result["fiber_info"]["fiber_type"] == "cotton"
        assert 0.0 <= result["overall_optimization_score"] <= 1.0

    def test_optimization_silk(self):
        """正常场景：蚕丝完整优化（低牵伸、高捻系数）"""
        result = SpinningParameterOptimizer.full_spinning_optimization("silk")
        assert result["draft_parameters"]["optimal_draft_ratio"] <= 5.0
        assert result["twist_parameters"]["twist_factor"] >= 350.0

    @pytest.mark.parametrize("fiber_type", VALID_FIBERS)
    def test_all_fibers_optimize_successfully(self, fiber_type):
        """正常场景：5种纤维全部可成功优化"""
        result = SpinningParameterOptimizer.full_spinning_optimization(fiber_type)
        assert "error" not in result
        assert result["fiber_info"]["fiber_type"] == fiber_type

    def test_optimization_invalid_fiber_returns_error(self):
        """异常场景：无效纤维返回错误字典"""
        result = SpinningParameterOptimizer.full_spinning_optimization("unknown_fiber")
        assert "error" in result
        assert "Unknown fiber type" in result["error"]

    def test_explicit_count_and_roving(self):
        """正常场景：显式指定纱支和粗纱"""
        result = SpinningParameterOptimizer.full_spinning_optimization(
            "cotton", yarn_count_tex=50.0, roving_count_tex=1500.0
        )
        assert result["input_parameters"]["yarn_count_tex"] == 50.0
        assert result["input_parameters"]["roving_count_tex"] == 1500.0

    def test_too_fine_count_triggers_warning(self):
        """参数合理性：纱支偏细应触发警告"""
        result = SpinningParameterOptimizer.full_spinning_optimization("hemp", yarn_count_tex=20.0)
        has_fine_warning = any("细" in w for w in result["warnings"])
        assert has_fine_warning

    def test_too_coarse_count_triggers_warning(self):
        """参数合理性：纱支偏粗应触发警告"""
        result = SpinningParameterOptimizer.full_spinning_optimization("silk", yarn_count_tex=500.0)
        has_coarse_warning = any("粗" in w for w in result["warnings"])
        assert has_coarse_warning

    def test_high_draft_triggers_breakage_warning(self):
        """参数合理性：牵伸过大触发断头警告"""
        result = SpinningParameterOptimizer.full_spinning_optimization(
            "cotton", yarn_count_tex=20.0, roving_count_tex=5000.0
        )
        has_break_warning = any("断头" in w for w in result["warnings"])
        assert has_break_warning


class TestCompareFibers:
    """多纤维对比测试"""

    def test_compare_all_five(self):
        """正常场景：对比全部5种纤维"""
        result = SpinningParameterOptimizer.compare_fibers(VALID_FIBERS, yarn_count_tex=150.0)
        assert len(result["fibers"]) == 5
        assert "highest_production" in result["comparison"]
        assert "lowest_breakage" in result["comparison"]
        assert "best_overall" in result["comparison"]

    def test_compare_partial_invalid(self):
        """异常场景：包含无效纤维类型应被过滤"""
        result = SpinningParameterOptimizer.compare_fibers(
            ["cotton", "invalid", "silk", "xxx"]
        )
        assert len(result["fibers"]) == 2

    def test_compare_empty_list(self):
        """异常场景：空列表返回空结果"""
        result = SpinningParameterOptimizer.compare_fibers([])
        assert len(result["fibers"]) == 0
        assert result["comparison"] == {}

    def test_compare_best_overall_is_valid(self):
        """参数合理性：最佳综合分纤维应存在于结果中"""
        result = SpinningParameterOptimizer.compare_fibers(VALID_FIBERS)
        best = result["comparison"]["best_overall"]
        fiber_names = [f["fiber_info"]["fiber_name"] for f in result["fibers"]]
        assert best in fiber_names
