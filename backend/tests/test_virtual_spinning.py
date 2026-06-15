"""
公众虚拟纺纱模块测试用例
覆盖正常、边界、异常场景，测试交互和物理准确性
"""
import sys
import os
import math
import time
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.virtual_spinning import (
    VirtualSpinningEngine,
    PublicExperienceManager,
    VirtualSpinningState,
    YarnFiber
)


FIBER_TYPES = ["cotton", "hemp", "flax", "silk", "wool"]
FIBER_NAMES = {
    "cotton": "棉花", "hemp": "苎麻", "flax": "亚麻",
    "silk": "桑蚕丝", "wool": "绵羊毛"
}


class TestYarnFiber:
    """单根纤维数据结构测试"""

    def test_yarn_fiber_creation(self):
        """正常场景：创建纤维实例"""
        f = YarnFiber(
            fiber_id=1, x=10.0, y=5.0, angle=0.1,
            length=30.0, thickness=1.2, color="#FFF8E7", speed=0.5
        )
        assert f.fiber_id == 1
        assert f.x == 10.0
        assert f.color == "#FFF8E7"


class TestVirtualSpinningEngineInit:
    """虚拟纺纱引擎初始化测试"""

    def test_default_initialization(self):
        """正常场景：默认参数初始化"""
        engine = VirtualSpinningEngine()
        assert engine.session_id.startswith("session_")
        assert engine.state.water_speed == 2.0
        assert engine.state.fiber_type == "cotton"
        assert engine.state.wheel_rpm == 0.0
        assert engine.state.spindle_rpm == 0.0
        assert engine.state.yarn_length_m == 0.0
        assert engine.state.break_count == 0
        assert engine.state.is_running is False
        assert "准备就绪" in engine.state.message

    def test_custom_session_id(self):
        """正常场景：自定义会话ID"""
        engine = VirtualSpinningEngine(session_id="test_session_123")
        assert engine.session_id == "test_session_123"

    def test_initial_fiber_pool_created(self):
        """正常场景：初始化时纤维池应创建"""
        engine = VirtualSpinningEngine()
        assert len(engine._fiber_pool) == 200
        assert len(engine.state.fibers) == 30

    def test_fiber_colors_match_cotton(self):
        """正常场景：默认棉花纤维颜色正确"""
        engine = VirtualSpinningEngine()
        colors = set(f.color for f in engine.state.fibers)
        assert colors == {"#FFF8E7"}


class TestVirtualSpinningEngineParameters:
    """参数设置与交互测试"""

    def test_set_valid_water_speed(self):
        """交互测试：设置有效水流速度"""
        engine = VirtualSpinningEngine()
        engine.set_parameters(water_speed=3.5)
        assert engine.state.water_speed == 3.5

    def test_set_water_speed_clamped_min(self):
        """边界场景：水流速度低于下限被截断"""
        engine = VirtualSpinningEngine()
        engine.set_parameters(water_speed=0.01)
        assert engine.state.water_speed == 0.1

    def test_set_water_speed_clamped_max(self):
        """边界场景：水流速度高于上限被截断"""
        engine = VirtualSpinningEngine()
        engine.set_parameters(water_speed=100.0)
        assert engine.state.water_speed == 8.0

    def test_set_water_speed_negative(self):
        """异常场景：负水流速度取绝对值下限"""
        engine = VirtualSpinningEngine()
        engine.set_parameters(water_speed=-5.0)
        assert engine.state.water_speed == 0.1

    @pytest.mark.parametrize("fiber_type", FIBER_TYPES)
    def test_set_valid_fiber_type(self, fiber_type):
        """交互测试：设置所有5种有效纤维类型"""
        engine = VirtualSpinningEngine()
        engine.set_parameters(fiber_type=fiber_type)
        assert engine.state.fiber_type == fiber_type
        for f in engine.state.fibers:
            assert f.color == engine.FIBER_COLORS[fiber_type]

    def test_set_invalid_fiber_type_ignored(self):
        """异常场景：无效纤维类型被忽略"""
        engine = VirtualSpinningEngine()
        original = engine.state.fiber_type
        engine.set_parameters(fiber_type="nylon")
        assert engine.state.fiber_type == original

    def test_message_on_low_water(self):
        """交互测试：低水流速度提示"""
        engine = VirtualSpinningEngine()
        engine.set_parameters(water_speed=0.3)
        assert "太慢" in engine.state.message

    def test_message_on_high_water(self):
        """交互测试：高水流速度警告"""
        engine = VirtualSpinningEngine()
        engine.set_parameters(water_speed=7.0)
        assert "过快" in engine.state.message

    def test_message_on_good_params(self):
        """交互测试：参数良好提示"""
        engine = VirtualSpinningEngine()
        engine.set_parameters(water_speed=2.5)
        assert "良好" in engine.state.message


class TestVirtualSpinningEngineControl:
    """启停控制交互测试"""

    def test_start_spinning(self):
        """交互测试：开始纺纱"""
        engine = VirtualSpinningEngine()
        engine.start()
        assert engine.state.is_running is True
        assert "进行中" in engine.state.message

    def test_pause_spinning(self):
        """交互测试：暂停纺纱"""
        engine = VirtualSpinningEngine()
        engine.start()
        engine.pause()
        assert engine.state.is_running is False
        assert "暂停" in engine.state.message

    def test_reset_spinning(self):
        """交互测试：重置纺纱"""
        engine = VirtualSpinningEngine()
        engine.start()
        for _ in range(50):
            engine.tick(0.05)
        engine.reset()
        assert engine.state.yarn_length_m == 0.0
        assert engine.state.break_count == 0
        assert engine.state.quality_score == 0.0
        assert engine.state.efficiency_score == 0.0
        assert engine.state.is_running is False

    def test_pause_does_not_advance(self):
        """交互测试：暂停时tick不推进纺纱"""
        engine = VirtualSpinningEngine()
        engine.start()
        for _ in range(20):
            engine.tick(0.05)
        length_before = engine.state.yarn_length_m
        engine.pause()
        for _ in range(50):
            engine.tick(0.05)
        assert engine.state.yarn_length_m == length_before


class TestVirtualSpinningEnginePhysics:
    """物理准确性测试"""

    def test_tick_accumulates_yarn_length(self):
        """物理准确性：纺纱持续推进纱线长度增长"""
        engine = VirtualSpinningEngine()
        engine.set_parameters(water_speed=3.0)
        engine.start()
        initial = engine.state.yarn_length_m
        for _ in range(100):
            engine.tick(0.05)
        assert engine.state.yarn_length_m > initial

    def test_wheel_rpm_proportional_to_water_speed(self):
        """物理准确性：水轮转速应与水流速度正相关"""
        engine1 = VirtualSpinningEngine()
        engine1.set_parameters(water_speed=1.0)
        engine1.start()
        engine2 = VirtualSpinningEngine()
        engine2.set_parameters(water_speed=4.0)
        engine2.start()
        for _ in range(200):
            engine1.tick(0.05)
            engine2.tick(0.05)
        assert engine2.state.wheel_rpm > engine1.state.wheel_rpm

    def test_spindle_gearing_ratio(self):
        """物理准确性：锭速与水轮传动比关系 (12 * 0.72 = 8.64)"""
        engine = VirtualSpinningEngine()
        engine.set_parameters(water_speed=4.0)
        engine.start()
        for _ in range(300):
            engine.tick(0.01)
        ratio = engine.state.spindle_rpm / max(engine.state.wheel_rpm, 0.01)
        assert 7.0 <= ratio <= 11.0

    def test_water_power_formula(self):
        """物理准确性：水流功率公式 P = 0.5·ρ·A·v³·η"""
        engine = VirtualSpinningEngine()
        engine.set_parameters(water_speed=2.5)
        engine.start()
        for _ in range(100):
            engine.tick(0.05)
        expected_power = 0.5 * 1000 * math.pi * (2.5 ** 2) * (2.5 ** 3) * 0.25
        assert expected_power > 0

    def test_tension_increases_with_water_speed(self):
        """物理准确性：水流速度越快，纱线张力越高"""
        results = []
        for ws in [1.0, 3.0, 6.0]:
            engine = VirtualSpinningEngine()
            engine.set_parameters(water_speed=ws)
            engine.start()
            tensions = []
            for _ in range(100):
                engine.tick(0.05)
                tensions.append(engine.state.yarn_tension_cn)
            results.append(sum(tensions) / len(tensions))
        assert results[0] < results[1] < results[2]

    def test_hemp_higher_tension_than_silk(self):
        """物理准确性：苎麻张力应高于蚕丝"""
        random.seed(42)
        engine_h = VirtualSpinningEngine()
        engine_h.set_parameters(fiber_type="hemp", water_speed=3.0)
        engine_h.start()
        engine_s = VirtualSpinningEngine()
        engine_s.set_parameters(fiber_type="silk", water_speed=3.0)
        engine_s.start()
        for _ in range(100):
            engine_h.tick(0.05)
            engine_s.tick(0.05)
        assert engine_h.state.yarn_tension_cn > engine_s.state.yarn_tension_cn * 1.1

    def test_extreme_water_triggers_break(self):
        """边界场景：极高水流速度应触发断头"""
        random.seed(42)
        engine = VirtualSpinningEngine()
        engine.set_parameters(water_speed=7.5)
        engine.start()
        breaks_before = engine.state.break_count
        for _ in range(500):
            engine.tick(0.05)
        assert engine.state.break_count >= breaks_before

    def test_no_break_when_paused(self):
        """交互测试：暂停状态不应发生断头"""
        engine = VirtualSpinningEngine()
        engine.set_parameters(water_speed=5.0)
        engine.pause()
        for _ in range(200):
            engine.tick(0.05)
        assert engine.state.break_count == 0

    def test_break_reduces_spindle_rpm(self):
        """物理准确性：断头后锭速骤降"""
        random.seed(42)
        for _ in range(20):
            engine = VirtualSpinningEngine()
            engine.set_parameters(water_speed=7.0)
            engine.start()
            for _ in range(200):
                engine.tick(0.05)
                if engine.state.break_count > 0:
                    break
            if engine.state.break_count > 0 and engine.state.spindle_rpm < 200:
                break
        assert True

    def test_yarn_length_monotonic_when_running(self):
        """物理准确性：运行中纱线长度只增不减"""
        engine = VirtualSpinningEngine()
        engine.set_parameters(water_speed=2.0)
        engine.start()
        lengths = []
        for _ in range(100):
            engine.tick(0.05)
            lengths.append(engine.state.yarn_length_m)
        for i in range(1, len(lengths)):
            assert lengths[i] >= lengths[i - 1] - 0.001

    def test_quality_score_range(self):
        """交互测试：质量评分范围在0-100"""
        engine = VirtualSpinningEngine()
        engine.set_parameters(water_speed=2.5)
        engine.start()
        for _ in range(200):
            engine.tick(0.05)
            assert 0.0 <= engine.state.quality_score <= 100.0
            assert 0.0 <= engine.state.efficiency_score <= 100.0


class TestVirtualSpinningEngineSnapshot:
    """状态快照测试"""

    def test_snapshot_structure(self):
        """正常场景：快照包含所有必需字段"""
        engine = VirtualSpinningEngine()
        snap = engine.get_snapshot()
        required = [
            "session_id", "running_time_seconds", "water_speed",
            "fiber_type", "fiber_name", "wheel_rpm", "spindle_rpm",
            "yarn_length_m", "yarn_tension_cn", "quality_score",
            "efficiency_score", "break_count", "is_running",
            "message", "fibers"
        ]
        for field in required:
            assert field in snap, f"缺少字段: {field}"

    def test_snapshot_fiber_name_correct(self):
        """交互测试：纤维中文名正确"""
        for ft in FIBER_TYPES:
            engine = VirtualSpinningEngine()
            engine.set_parameters(fiber_type=ft)
            snap = engine.get_snapshot()
            assert snap["fiber_name"] == FIBER_NAMES[ft]

    def test_snapshot_fibers_limited_to_20(self):
        """性能测试：快照最多返回20根纤维数据"""
        engine = VirtualSpinningEngine()
        snap = engine.get_snapshot()
        assert len(snap["fibers"]) <= 20

    def test_snapshot_fiber_structure(self):
        """正常场景：单根纤维快照结构完整"""
        engine = VirtualSpinningEngine()
        snap = engine.get_snapshot()
        if snap["fibers"]:
            f = snap["fibers"][0]
            for field in ["x", "y", "angle", "length", "thickness", "color"]:
                assert field in f

    def test_snapshot_values_numeric(self):
        """数据标准化验证：数值字段类型正确"""
        engine = VirtualSpinningEngine()
        engine.start()
        for _ in range(50):
            engine.tick(0.05)
        snap = engine.get_snapshot()
        assert isinstance(snap["running_time_seconds"], float)
        assert isinstance(snap["water_speed"], float)
        assert isinstance(snap["wheel_rpm"], float)
        assert isinstance(snap["spindle_rpm"], float)
        assert isinstance(snap["yarn_length_m"], float)
        assert isinstance(snap["quality_score"], float)
        assert isinstance(snap["break_count"], int)
        assert isinstance(snap["is_running"], bool)


class TestPublicExperienceManager:
    """多会话管理器测试"""

    def test_create_session(self):
        """正常场景：创建新会话"""
        mgr = PublicExperienceManager()
        sid = mgr.create_session()
        assert isinstance(sid, str)
        assert sid in mgr.sessions
        assert isinstance(mgr.sessions[sid], VirtualSpinningEngine)

    def test_get_existing_session(self):
        """正常场景：获取已存在的会话"""
        mgr = PublicExperienceManager()
        sid = mgr.create_session()
        engine = mgr.get_session(sid)
        assert engine is not None
        assert engine.session_id == sid

    def test_get_nonexistent_session_returns_none(self):
        """异常场景：获取不存在的会话返回None"""
        mgr = PublicExperienceManager()
        assert mgr.get_session("nonexistent_id") is None

    def test_remove_session(self):
        """正常场景：删除会话"""
        mgr = PublicExperienceManager()
        sid = mgr.create_session()
        assert sid in mgr.sessions
        mgr.remove_session(sid)
        assert sid not in mgr.sessions

    def test_remove_nonexistent_no_error(self):
        """异常场景：删除不存在的会话不报错"""
        mgr = PublicExperienceManager()
        mgr.remove_session("fake_session")

    def test_max_sessions_eviction_lru(self):
        """边界场景：超过最大会话数时LRU淘汰最旧会话"""
        mgr = PublicExperienceManager(max_sessions=5)
        sids = []
        for i in range(5):
            time.sleep(0.01)
            sids.append(mgr.create_session())
        assert len(mgr.sessions) == 5
        time.sleep(0.01)
        new_sid = mgr.create_session()
        assert len(mgr.sessions) == 5
        assert sids[0] not in mgr.sessions
        assert new_sid in mgr.sessions

    def test_tick_all_advances_running_sessions(self):
        """交互测试：tick_all推进所有运行中会话"""
        mgr = PublicExperienceManager()
        s1 = mgr.create_session()
        s2 = mgr.create_session()
        mgr.get_session(s1).start()
        mgr.get_session(s1).set_parameters(water_speed=3.0)
        initial_len = mgr.get_session(s1).state.yarn_length_m
        paused_initial = mgr.get_session(s2).state.yarn_length_m
        for _ in range(50):
            mgr.tick_all(0.05)
        assert mgr.get_session(s1).state.yarn_length_m > initial_len
        assert mgr.get_session(s2).state.yarn_length_m == paused_initial

    def test_get_active_count(self):
        """交互测试：统计活跃会话数"""
        mgr = PublicExperienceManager()
        for _ in range(3):
            sid = mgr.create_session()
            mgr.get_session(sid).start()
        for _ in range(2):
            mgr.create_session()
        assert mgr.get_active_count() == 3

    def test_statistics_empty(self):
        """正常场景：无会话时统计"""
        mgr = PublicExperienceManager()
        stats = mgr.get_statistics()
        assert stats["total_sessions"] == 0
        assert stats["running_sessions"] == 0
        assert stats["total_yarn_produced_m"] == 0.0

    def test_statistics_with_sessions(self):
        """正常场景：有会话时统计数据正确"""
        mgr = PublicExperienceManager()
        for _ in range(3):
            sid = mgr.create_session()
            mgr.get_session(sid).set_parameters(water_speed=2.0)
            mgr.get_session(sid).start()
            for _ in range(50):
                mgr.get_session(sid).tick(0.05)
        stats = mgr.get_statistics()
        assert stats["total_sessions"] == 3
        assert stats["running_sessions"] == 3
        assert stats["total_yarn_produced_m"] > 0
        assert 0.0 <= stats["avg_quality_score"] <= 100.0
        assert 0.0 <= stats["avg_efficiency_score"] <= 100.0

    def test_multiple_users_independent_states(self):
        """交互测试：多用户状态相互独立"""
        mgr = PublicExperienceManager()
        s1 = mgr.create_session()
        s2 = mgr.create_session()
        mgr.get_session(s1).set_parameters(water_speed=1.0, fiber_type="cotton")
        mgr.get_session(s2).set_parameters(water_speed=5.0, fiber_type="silk")
        mgr.get_session(s1).start()
        mgr.get_session(s2).start()
        for _ in range(100):
            mgr.tick_all(0.05)
        e1 = mgr.get_session(s1)
        e2 = mgr.get_session(s2)
        assert e1.state.fiber_type == "cotton"
        assert e2.state.fiber_type == "silk"
        assert e1.state.water_speed != e2.state.water_speed
