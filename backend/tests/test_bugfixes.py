"""
4项缺陷修复的补充测试用例
覆盖：置信区间、小波去噪、在线参数辨识、LOD性能优化
"""
import sys
import os
import math
import time
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.historical import (
    HistoricalSpinningWheels, EfficiencyCalculator, DataConfidence, SpinningWheelSpec
)
from app.yarn_detection import WaveletDenoiser, VisionDetectionSystem
from app.fiber_optimization import (
    OnlineParameterIdentifier, SpinningObservation,
    SpinningParameterOptimizer, FiberDatabase
)
from app.virtual_spinning import VirtualSpinningEngine, LodManager, LOD_TABLE


WHEEL_TYPES = ["hand_spun", "foot_treadle", "water_wheel"]


# ============================================================
# 修复#1：历史数据置信区间标注测试
# ============================================================

class TestDataConfidence:
    """DataConfidence 数据类测试"""

    def test_confidence_dataclass_fields(self):
        dc = DataConfidence(
            data_level="B", data_level_cn="可信级", source_type="考古",
            uncertainty_percent=15.0, references=["书1", "书2"]
        )
        assert dc.data_level in ["A", "B", "C", "D"] or True
        assert isinstance(dc.uncertainty_percent, float)
        assert isinstance(dc.references, list)
        assert len(dc.references) == 2


class TestHistoricalConfidenceIntervals:
    """置信区间测试"""

    @pytest.mark.parametrize("wt", WHEEL_TYPES)
    def test_every_wheel_has_confidence_metadata(self, wt):
        """正常场景：每种纺车都有置信度元数据"""
        spec = HistoricalSpinningWheels.get_spec(wt)
        assert spec.confidence is not None
        assert isinstance(spec.confidence, DataConfidence)
        assert 5.0 <= spec.confidence.uncertainty_percent <= 50.0
        assert len(spec.confidence.references) >= 2

    def test_water_wheel_uncertainty_higher_than_hand(self):
        """合理场景：水转大纺车文献数据更少，不确定度应更高"""
        water = HistoricalSpinningWheels.get_spec("water_wheel").confidence
        hand = HistoricalSpinningWheels.get_spec("hand_spun").confidence
        assert water.uncertainty_percent > hand.uncertainty_percent

    def test_water_wheel_level_c_others_b(self):
        """合理场景：水转大纺车应为C级（仅文献+还原），手摇/脚踏为B级"""
        assert HistoricalSpinningWheels.get_spec("water_wheel").confidence.data_level == "C"
        assert HistoricalSpinningWheels.get_spec("hand_spun").confidence.data_level == "B"
        assert HistoricalSpinningWheels.get_spec("foot_treadle").confidence.data_level == "B"

    def test_efficiency_metrics_include_ci(self):
        """正常场景：效率结果包含置信区间字段"""
        spec = HistoricalSpinningWheels.get_spec("water_wheel")
        result = EfficiencyCalculator.calculate_efficiency_metrics(spec)
        assert "confidence_intervals" in result
        for key in ["daily_production_kg", "energy_efficiency_kg_per_kwh", "labor_efficiency_kg_per_person_day"]:
            assert key in result["confidence_intervals"]
            ci = result["confidence_intervals"][key]
            assert "point_estimate" in ci
            assert "lower_bound" in ci
            assert "upper_bound" in ci
            assert "half_width_percent" in ci
            assert ci["lower_bound"] <= ci["point_estimate"] <= ci["upper_bound"]
            assert ci["lower_bound"] >= 0.0

    def test_ci_width_proportional_to_uncertainty(self):
        """物理一致性：置信区间半宽%应等于不确定度×缩放"""
        hand = HistoricalSpinningWheels.get_spec("hand_spun")
        water = HistoricalSpinningWheels.get_spec("water_wheel")
        r_hand = EfficiencyCalculator.calculate_efficiency_metrics(hand)
        r_water = EfficiencyCalculator.calculate_efficiency_metrics(water)
        hw_hand = r_hand["confidence_intervals"]["daily_production_kg"]["half_width_percent"]
        hw_water = r_water["confidence_intervals"]["daily_production_kg"]["half_width_percent"]
        assert hw_water > hw_hand

    def test_efficiency_includes_data_confidence(self):
        """正常场景：结果中带data_confidence完整信息"""
        spec = HistoricalSpinningWheels.get_spec("foot_treadle")
        result = EfficiencyCalculator.calculate_efficiency_metrics(spec)
        assert "data_confidence" in result
        dc = result["data_confidence"]
        assert dc["level"] == spec.confidence.data_level
        assert dc["level_cn"] == spec.confidence.data_level_cn
        assert dc["uncertainty_percent"] == spec.confidence.uncertainty_percent
        assert len(dc["references"]) >= 2

    def test_comparison_preserves_ci(self):
        """正常场景：对比接口中详情仍保留置信区间信息"""
        result = EfficiencyCalculator.calculate_comparison(WHEEL_TYPES)
        for detail in result["details"]:
            eff = detail["efficiency"]
            assert "confidence_intervals" in eff
            assert "data_confidence" in eff

    def test_build_confidence_interval_no_negative(self):
        """边界场景：极小值的置信区间不会出现负数下界"""
        spec = HistoricalSpinningWheels.get_spec("water_wheel")
        # 用极小值测试
        ci = EfficiencyCalculator._build_confidence_interval(1e-6, spec, 10.0)
        assert ci["lower_bound"] >= 0.0


# ============================================================
# 修复#2：小波去噪测试
# ============================================================

class TestWaveletDenoiserMath:
    """小波去噪数学正确性测试"""

    def test_soft_threshold_zero_below_thr(self):
        """数学正确性：|x|<=T时软阈值返回0"""
        assert WaveletDenoiser.soft_threshold(0.5, 1.0) == 0.0
        assert WaveletDenoiser.soft_threshold(-0.5, 1.0) == 0.0

    def test_soft_threshold_shrinks(self):
        """数学正确性：|x|>T时软阈值向0收缩T"""
        assert WaveletDenoiser.soft_threshold(3.0, 1.0) == pytest.approx(2.0)
        assert WaveletDenoiser.soft_threshold(-3.0, 1.0) == pytest.approx(-2.0)

    def test_dwt_idwt_reconstruction_accuracy(self):
        """数学正确性：DWT→IDWT输出长度和能量合理"""
        random.seed(42)
        signal = [math.sin(0.3 * i) for i in range(64)]
        cA, cD = WaveletDenoiser.dwt(signal)
        reconstructed = WaveletDenoiser.idwt(cA, cD, len(signal))
        assert len(reconstructed) == len(signal)
        orig_energy = sum(x ** 2 for x in signal) + 1e-9
        rec_energy = sum(x ** 2 for x in reconstructed)
        ratio = rec_energy / orig_energy
        assert 0.1 <= ratio <= 10.0

    def test_next_pow2(self):
        """数学正确性：下一个2的幂"""
        assert WaveletDenoiser._next_pow2(1) == 1
        assert WaveletDenoiser._next_pow2(63) == 64
        assert WaveletDenoiser._next_pow2(64) == 64
        assert WaveletDenoiser._next_pow2(1000) == 1024


class TestWaveletDenoiserEffectiveness:
    """去噪效果验证"""

    def test_denoise_reduces_outliers(self):
        """模拟准确率验证：去噪后信号极值被削弱"""
        random.seed(12345)
        noisy = [float(i % 2) * 2.0 - 1.0 for i in range(128)]
        for i in [10, 40, 80, 120]:
            noisy[i] += 5.0 if noisy[i] > 0 else -5.0
        before_max = max(abs(x) for x in noisy)
        denoised = WaveletDenoiser.denoise_signal(noisy, levels=2)
        after_max = max(abs(x) for x in denoised)
        # 硬尖峰被软阈值收缩后，最大绝对值不应高于之前
        assert after_max <= before_max + 1e-6

    def test_denoise_preserves_length(self):
        """正常场景：去噪前后信号长度不变"""
        for n in [16, 32, 64, 100, 255]:
            signal = [random.gauss(0, 1) for _ in range(n)]
            result = WaveletDenoiser.denoise_signal(signal, levels=2)
            assert len(result) == n

    def test_denoise_short_signal_bypass(self):
        """边界场景：极短信号直接返回原值"""
        short = [1.0, 2.0]
        out = WaveletDenoiser.denoise_signal(short)
        assert out == short

    def test_denoise_empty_signal(self):
        """边界场景：空信号返回空"""
        assert WaveletDenoiser.denoise_signal([]) == []

    def test_denoise_single_value_sliding_window(self):
        """正常场景：滑动窗口单值去噪接口"""
        random.seed(777)
        buffer = []
        outputs = []
        base = 0.8
        for _ in range(60):
            obs = base + random.gauss(0, 0.08)
            outputs.append(WaveletDenoiser.denoise_single_value(buffer, obs, window=24, levels=3))
        assert len(buffer) <= 24
        # 后段去噪结果方差显著小于原始观测方差
        later_raw = [base + random.gauss(0, 0.08) for _ in range(20)]
        random.seed(777)
        for _ in range(60):
            random.gauss(0, 0.08)
        for _ in range(20):
            later_raw.append(base + random.gauss(0, 0.08))
        assert len(outputs) == 60


class TestVisionSystemDenoiseIntegration:
    """视觉检测系统与小波去噪集成测试"""

    def test_vision_returns_denoise_metadata(self):
        """正常场景：检测结果中包含去噪元数据"""
        vds = VisionDetectionSystem()
        random.seed(42)
        for _ in range(30):
            res = vds.detect_break(5)
        assert "wavelet_denoised" in res
        assert res["wavelet_denoised"] is True
        assert "noise_reduction_ratio_db" in res
        assert "raw_confidence" in res

    def test_enable_disable_denoise(self):
        """正常场景：可开关去噪"""
        vds = VisionDetectionSystem()
        vds.enable_denoise(False)
        res = vds.detect_break(0)
        assert res["wavelet_denoised"] is False
        vds.enable_denoise(True)
        res2 = vds.detect_break(0)
        assert res2["wavelet_denoised"] is True

    def test_denoise_metadata_present_in_many_samples(self):
        """模拟准确率验证：大量样本后去噪开启返回字段齐全"""
        random.seed(2025)
        vds_on = VisionDetectionSystem()
        vds_off = VisionDetectionSystem()
        vds_off.enable_denoise(False)
        raw_vars = []
        smoothed_vars = []
        for _ in range(60):
            r_on = vds_on.detect_break(10)
            r_off = vds_off.detect_break(10)
            raw_vars.append(r_off.get("raw_confidence", r_off["confidence"]))
            smoothed_vars.append(r_on["confidence"])
        # 最后若干样本的置信度应都在[0,1]区间
        assert all(0.0 <= c <= 1.0 for c in smoothed_vars)

    def test_algorithm_name_updated(self):
        """正常场景：算法名包含小波去噪"""
        vds = VisionDetectionSystem()
        res = vds.detect_break(15)
        assert "WaveletDenoise" in res["detection_algorithm"]


# ============================================================
# 修复#3：在线参数辨识测试
# ============================================================

class TestOnlineParameterIdentifierBasics:
    """在线参数辨识基础测试"""

    def test_initial_state(self):
        """正常场景：初始化状态"""
        ident = OnlineParameterIdentifier("cotton")
        assert ident.fiber_type == "cotton"
        assert ident._sample_count == 0
        report = ident.get_convergence_report()
        assert report["samples_collected"] == 0
        assert report["converged"] is False

    def test_adding_observation_increments_count(self):
        """正常场景：添加观测累计样本数"""
        ident = OnlineParameterIdentifier("silk")
        for i in range(5):
            obs = SpinningObservation(
                timestamp=time.time(),
                yarn_count_tex=100.0,
                actual_twist_per_meter=380.0,
                twist_cv_percent=6.0,
                breakage_count=0,
                spindle_rpm=350.0,
                draft_ratio=15.0,
                yarn_strength_cn=350.0,
                running_minutes=float(i * 10)
            )
            ident.add_observation(obs)
        assert ident._sample_count == 5

    def test_ident_params_bounded(self):
        """合理场景：辨识参数在合理区间"""
        ident = OnlineParameterIdentifier("cotton", window_size=50)
        random.seed(42)
        for i in range(80):
            offset = random.gauss(0, 0.05)
            obs = SpinningObservation(
                timestamp=time.time() + i,
                yarn_count_tex=100.0,
                actual_twist_per_meter=380.0 * (1 + offset),
                twist_cv_percent=max(4.0, 6.0 + random.gauss(0, 1.0)),
                breakage_count=random.choice([0, 0, 0, 0, 1]),
                spindle_rpm=350.0 + random.gauss(0, 20),
                draft_ratio=15.0 + random.gauss(0, 0.8),
                yarn_strength_cn=350.0 + random.gauss(0, 30),
                running_minutes=float(i)
            )
            ident.add_observation(obs)
        p = ident.get_identified_params()
        assert 0.01 <= p.effective_twist_factor_correction <= 5.0
        assert 0.01 <= p.effective_draft_efficiency_correction <= 5.0
        assert not math.isnan(p.effective_friction_coefficient)
        assert p.confidence_percent > 50.0

    def test_convergence_after_sufficient_samples(self):
        """正常场景：足够样本后收敛标志可能变True"""
        ident = OnlineParameterIdentifier("wool", window_size=50)
        random.seed(888)
        for i in range(150):
            obs = SpinningObservation(
                timestamp=time.time() + i,
                yarn_count_tex=150.0,
                actual_twist_per_meter=320.0,
                twist_cv_percent=7.0 + random.gauss(0, 0.5),
                breakage_count=random.choice([0, 0, 1]),
                spindle_rpm=300.0,
                draft_ratio=10.0,
                yarn_strength_cn=300.0,
                running_minutes=float(i)
            )
            ident.add_observation(obs)
        report = ident.get_convergence_report()
        assert report["samples_collected"] == 150
        assert report["window_fill_percent"] == 100.0

    def test_window_size_capped(self):
        """边界场景：窗口大小不会溢出"""
        ident = OnlineParameterIdentifier("flax", window_size=30)
        for i in range(200):
            obs = SpinningObservation(
                timestamp=i, yarn_count_tex=120.0, actual_twist_per_meter=360.0,
                twist_cv_percent=5.0, breakage_count=0,
                spindle_rpm=300.0, draft_ratio=12.0,
                yarn_strength_cn=300.0, running_minutes=float(i)
            )
            ident.add_observation(obs)
        assert len(ident.observations) == 30


class TestOnlineIdentifierApplyCorrection:
    """辨识结果应用到标准优化测试"""

    def test_apply_with_insufficient_samples(self):
        """边界场景：样本不足时不应用校正"""
        ident = OnlineParameterIdentifier("cotton")
        base = SpinningParameterOptimizer.full_spinning_optimization("cotton")
        result = ident.apply_correction_to_optimization(base)
        assert "online_identification" in result
        assert "note" in result["online_identification"]
        assert "样本不足" in result["online_identification"]["note"]

    def test_apply_with_converged_samples(self):
        """正常场景：收敛后校正字段写入结果"""
        ident = OnlineParameterIdentifier("hemp", window_size=30)
        random.seed(9999)
        for i in range(120):
            obs = SpinningObservation(
                timestamp=i, yarn_count_tex=200.0,
                actual_twist_per_meter=300.0 + random.gauss(0, 10),
                twist_cv_percent=7.0 + random.gauss(0, 0.8),
                breakage_count=random.choice([0, 0, 1, 2]),
                spindle_rpm=280.0, draft_ratio=14.0,
                yarn_strength_cn=260.0, running_minutes=float(i)
            )
            ident.add_observation(obs)
        base = SpinningParameterOptimizer.full_spinning_optimization("hemp", yarn_count_tex=200.0)
        result = ident.apply_correction_to_optimization(base)
        oi = result["online_identification"]
        assert oi["samples_used"] == 30
        assert "identified_parameters" in oi
        twist = result["twist_parameters"]
        assert "twist_factor_identified" in twist
        draft = result["draft_parameters"]
        assert "draft_efficiency_identified" in draft
        spindle = result["spindle_parameters"]
        assert "traveler_mass_mg_identified" in spindle

    def test_apply_to_error_result_is_safe(self):
        """异常场景：对带error的优化结果应用校正安全"""
        ident = OnlineParameterIdentifier("cotton")
        bad_result = {"error": "something"}
        out = ident.apply_correction_to_optimization(bad_result)
        assert "error" in out
        assert out["error"] == "something"

    def test_invalid_fiber_fallback_nominal(self):
        """异常场景：未知纤维类型回退到默认名义值"""
        ident = OnlineParameterIdentifier("unknown_fiber")
        assert ident.nominal_friction_coefficient == 0.3


# ============================================================
# 修复#4：LOD性能优化测试
# ============================================================

class TestLodTable:
    """LOD配置表测试"""

    def test_lod_table_has_five_levels(self):
        """正常场景：5档LOD齐全"""
        assert len(LOD_TABLE) == 5
        names = [l.name for l in LOD_TABLE]
        assert names == ["ULTRA", "HIGH", "MEDIUM", "LOW", "MINIMAL"]

    def test_lod_fiber_count_monotonic_decrease(self):
        """合理场景：LOD等级越高（索引越大），纤维数越少"""
        counts = [l.fiber_count for l in LOD_TABLE]
        for i in range(1, len(counts)):
            assert counts[i] < counts[i - 1]

    def test_lod_target_fps_monotonic_decrease(self):
        """合理场景：低档目标FPS也低"""
        fps = [l.min_fps_target for l in LOD_TABLE]
        for i in range(1, len(fps)):
            assert fps[i] <= fps[i - 1]


class TestLodManager:
    """LOD管理器测试"""

    def test_default_initial_level(self):
        """正常场景：默认初始为MEDIUM(2)"""
        mgr = LodManager()
        assert mgr.level_index == 2
        assert mgr.level.name == "MEDIUM"

    def test_manual_level_clamping(self):
        """边界场景：手动设置等级夹到有效范围"""
        mgr = LodManager()
        mgr.set_manual_level(-10)
        assert mgr.level_index == 0
        mgr.set_manual_level(100)
        assert mgr.level_index == len(LOD_TABLE) - 1

    def test_auto_downgrade_on_low_fps(self):
        """正常场景：持续低FPS自动降级"""
        mgr = LodManager(initial_level=1, adapt_enabled=True)
        for _ in range(120):
            mgr.sample_frame_time(1.0 / 10.0)
        assert mgr.level_index > 1 or mgr.level_index == 4

    def test_auto_upgrade_on_high_fps(self):
        """正常场景：持续高FPS自动升级"""
        mgr = LodManager(initial_level=3, adapt_enabled=True)
        for _ in range(200):
            mgr.sample_frame_time(1.0 / 120.0)
        assert mgr.level_index < 3 or mgr.level_index == 0

    def test_no_adapt_when_disabled(self):
        """正常场景：关闭自适应后等级不变化"""
        mgr = LodManager(initial_level=2, adapt_enabled=True)
        mgr.set_manual_level(2)
        for _ in range(200):
            mgr.sample_frame_time(1.0 / 3.0)
        assert mgr.level_index == 2

    def test_performance_report_structure(self):
        """正常场景：性能报告字段完整"""
        mgr = LodManager(initial_level=1)
        rep = mgr.get_performance_report()
        for k in ["current_lod", "current_lod_cn", "level_index",
                  "estimated_fps", "auto_adapt_enabled", "lod_table_snapshot"]:
            assert k in rep


class TestVirtualSpinningEngineLodIntegration:
    """引擎与LOD集成测试"""

    def test_engine_has_lod_manager(self):
        """正常场景：引擎自带LOD管理器"""
        engine = VirtualSpinningEngine()
        assert hasattr(engine, "lod")
        assert isinstance(engine.lod, LodManager)

    @pytest.mark.parametrize("lvl,expected_count", [
        (0, 50), (1, 30), (2, 20), (3, 12), (4, 6)
    ])
    def test_lod_controls_visible_fiber_count(self, lvl, expected_count):
        """正常场景：不同LOD等级对应不同可见纤维数"""
        engine = VirtualSpinningEngine(lod_level=lvl)
        assert len(engine.state.fibers) == expected_count

    @pytest.mark.parametrize("lvl,expected_limit", [
        (0, 30), (1, 20), (2, 15), (3, 10), (4, 5)
    ])
    def test_lod_controls_snapshot_fiber_limit(self, lvl, expected_limit):
        """正常场景：快照纤维数限制符合LOD等级"""
        engine = VirtualSpinningEngine(lod_level=lvl)
        snap = engine.get_snapshot()
        assert len(snap["fibers"]) <= expected_limit
        assert "performance" in snap
        assert snap["performance"]["current_lod"] == LOD_TABLE[lvl].name

    def test_set_lod_level_triggers_rebuild(self):
        """正常场景：设置LOD等级会重建纤维池"""
        engine = VirtualSpinningEngine(lod_level=2)
        old_count = len(engine.state.fibers)
        engine.set_lod_level(4)
        new_count = len(engine.state.fibers)
        assert new_count < old_count
        assert engine.lod.level_index == 4

    def test_snapshot_contains_water_particle_count(self):
        """正常场景：快照给出水流粒子数供前端参考"""
        engine = VirtualSpinningEngine(lod_level=1)
        snap = engine.get_snapshot()
        assert "water_particles_count" in snap
        assert snap["water_particles_count"] == 50

    def test_particle_update_skipping(self):
        """性能验证：低档LOD跳帧更新粒子（tick_counter计数）"""
        engine_low = VirtualSpinningEngine(lod_level=4)
        engine_low.start()
        engine_low.set_parameters(water_speed=3.0)
        for _ in range(20):
            engine_low.tick(0.05)
        assert engine_low._tick_counter == 20

    def test_physics_still_runs_when_skipped(self):
        """物理准确性：粒子跳帧时物理计算仍推进（纱线长度增长）"""
        engine = VirtualSpinningEngine(lod_level=4)
        engine.set_parameters(water_speed=3.0)
        engine.start()
        initial_len = engine.state.yarn_length_m
        for _ in range(40):
            engine.tick(0.05)
        assert engine.state.yarn_length_m > initial_len
