"""
断头检测与自动生头模块测试用例
覆盖正常、边界、异常场景
"""
import sys
import os
import math
import time
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.yarn_detection import (
    YarnBreakSimulator,
    VisionDetectionSystem,
    AutoPiecingRobot,
    BreakDetectionSystem,
    CameraConfig,
    YarnBreakEvent
)


random.seed(42)


class TestYarnBreakSimulator:
    """纱线断头仿真器测试"""

    def test_generate_break_event_basic(self):
        """正常场景：生成基本断头事件"""
        event = YarnBreakSimulator.generate_break_event(5, 300.0, 25.0)
        assert isinstance(event, YarnBreakEvent)
        assert event.spindle_id == 5
        assert event.event_id.startswith("break_")
        assert 50.0 <= event.break_position_mm <= 800.0
        assert event.tension_at_break_cn > 0
        assert event.speed_at_break_rpm > 0
        assert len(event.break_cause) > 0
        assert 0.0 <= event.confidence_score <= 1.0
        assert event.detected is True
        assert event.auto_piecing_success is False
        assert event.piecing_time_ms == 0.0

    def test_break_cause_distribution(self):
        """模拟准确率验证：断头原因分布应符合定义的概率"""
        causes = {}
        for _ in range(5000):
            event = YarnBreakSimulator.generate_break_event(0, 300.0, 25.0)
            causes[event.break_cause] = causes.get(event.break_cause, 0) + 1
        assert "tension_peak" in causes
        assert causes["tension_peak"] > causes.get("other", 0)
        assert "fiber_defect" in causes

    def test_tension_peak_causes_high_tension(self):
        """物理准确性：张力峰值断头的张力应显著偏高"""
        tension_peak_events = []
        normal_events = []
        for _ in range(2000):
            event = YarnBreakSimulator.generate_break_event(0, 300.0, 25.0)
            if event.break_cause == "tension_peak":
                tension_peak_events.append(event.tension_at_break_cn)
            else:
                normal_events.append(event.tension_at_break_cn)
        if tension_peak_events and normal_events:
            avg_peak = sum(tension_peak_events) / len(tension_peak_events)
            avg_normal = sum(normal_events) / len(normal_events)
            assert avg_peak > avg_normal * 1.3

    def test_break_probability_normal(self):
        """正常场景：正常工况断头概率应较低"""
        prob = YarnBreakSimulator.calculate_break_probability(
            speed_rpm=300.0,
            tension_cn=25.0,
            max_tension_cn=80.0,
            fiber_strength_cn_dtex=2.8,
            yarn_count_tex=100.0,
            twist_cv_percent=8.0
        )
        assert 0.0 <= prob <= 1.0
        assert prob < 0.1

    def test_break_probability_high_tension(self):
        """边界场景：张力接近极限时断头概率显著升高"""
        prob_normal = YarnBreakSimulator.calculate_break_probability(
            300.0, 25.0, 80.0, 2.8, 100.0, 8.0
        )
        prob_high = YarnBreakSimulator.calculate_break_probability(
            300.0, 79.0, 80.0, 2.8, 100.0, 8.0
        )
        assert prob_high > prob_normal * 2

    def test_break_probability_high_speed(self):
        """边界场景：锭速升高断头概率增加"""
        prob_low = YarnBreakSimulator.calculate_break_probability(
            100.0, 25.0, 80.0, 2.8, 100.0, 8.0
        )
        prob_high = YarnBreakSimulator.calculate_break_probability(
            600.0, 25.0, 80.0, 2.8, 100.0, 8.0
        )
        assert prob_high > prob_low

    def test_break_probability_capped(self):
        """边界场景：断头概率不超过50%"""
        prob = YarnBreakSimulator.calculate_break_probability(
            1000.0, 100.0, 80.0, 0.5, 10.0, 50.0, operating_hours=10000
        )
        assert prob <= 0.5

    @pytest.mark.parametrize("spindle_id", [0, 15, 31, 100, -1])
    def test_generate_event_all_spindle_ids(self, spindle_id):
        """边界场景：极端锭子ID"""
        event = YarnBreakSimulator.generate_break_event(spindle_id, 300.0, 25.0)
        assert event.spindle_id == spindle_id


class TestVisionDetectionSystem:
    """视觉检测系统测试"""

    def test_default_cameras_four_units(self):
        """正常场景：默认配置应有4台相机"""
        vds = VisionDetectionSystem()
        assert len(vds.cameras) == 4
        for i, cam in enumerate(vds.cameras):
            assert cam.camera_id == f"cam_{i}"
            assert cam.resolution_width == 1280
            assert cam.resolution_height == 720
            assert cam.fps == 30

    def test_camera_coverage_complete(self):
        """模拟准确率验证：4台相机应完整覆盖0-31号锭子"""
        vds = VisionDetectionSystem()
        covered = set()
        for cam in vds.cameras:
            start, end = cam.coverage_spindle_range
            covered.update(range(start, end + 1))
        assert covered == set(range(32))

    def test_detect_break_valid_spindle(self):
        """正常场景：有效锭子的断头检测"""
        vds = VisionDetectionSystem()
        random.seed(42)
        result = vds.detect_break(10)
        assert "detected" in result
        assert "confidence" in result
        assert "latency_ms" in result
        assert "camera_id" in result
        assert result["camera_id"] == "cam_1"
        assert 0.0 <= result["confidence"] <= 1.0
        assert result["latency_ms"] > 0
        assert result["detection_algorithm"] == "YOLOv8-BreakNet"

    def test_detect_break_updates_stats(self):
        """正常场景：检测后统计数据更新"""
        vds = VisionDetectionSystem()
        random.seed(42)
        initial = vds.detection_stats["total_scanned"]
        vds.detect_break(0)
        vds.detect_break(31)
        assert vds.detection_stats["total_scanned"] == initial + 2

    def test_detect_uncovered_spindle_returns_error(self):
        """异常场景：无相机覆盖的锭子返回错误"""
        vds = VisionDetectionSystem()
        result = vds.detect_break(999)
        assert result["detected"] is False
        assert result["confidence"] == 0.0
        assert "error" in result
        assert result["camera_id"] is None

    @pytest.mark.parametrize("spindle,expected_cam", [
        (0, "cam_0"), (7, "cam_0"),
        (8, "cam_1"), (15, "cam_1"),
        (16, "cam_2"), (23, "cam_2"),
        (24, "cam_3"), (31, "cam_3"),
    ])
    def test_camera_mapping_correct(self, spindle, expected_cam):
        """模拟准确率验证：锭子-相机映射关系正确"""
        vds = VisionDetectionSystem()
        random.seed(42)
        result = vds.detect_break(spindle)
        assert result["camera_id"] == expected_cam

    def test_detection_latency_reasonable(self):
        """模拟准确率验证：检测延迟应在合理范围(8-50ms)"""
        vds = VisionDetectionSystem()
        random.seed(42)
        latencies = [vds.detect_break(i)["latency_ms"] for i in range(32)]
        avg_latency = sum(latencies) / len(latencies)
        assert 8.0 <= avg_latency <= 50.0

    def test_detection_accuracy_statistical(self):
        """模拟准确率验证：大样本下检测率应高于90%"""
        vds = VisionDetectionSystem()
        random.seed(12345)
        detected = 0
        total = 500
        for i in range(total):
            spindle = i % 32
            result = vds.detect_break(spindle, "tension_peak")
            if result["detected"]:
                detected += 1
        detection_rate = detected / total
        assert detection_rate >= 0.90, f"检测率 {detection_rate:.2%} 低于预期"

    def test_confidence_distribution(self):
        """模拟准确率验证：检测置信度应集中在0.7-0.99区间"""
        vds = VisionDetectionSystem()
        random.seed(999)
        confidences = [vds.detect_break(i % 32)["confidence"] for i in range(200)]
        in_range = sum(1 for c in confidences if 0.7 <= c <= 0.99)
        assert in_range >= 160

    def test_get_system_status(self):
        """正常场景：获取系统状态"""
        vds = VisionDetectionSystem()
        vds.detect_break(5)
        status = vds.get_system_status()
        assert "cameras" in status
        assert "statistics" in status
        assert "algorithm" in status
        assert len(status["cameras"]) == 4
        assert status["statistics"]["total_frames_scanned"] >= 1
        assert status["algorithm"]["name"] == "YOLOv8-BreakNet"

    def test_custom_camera_config(self):
        """正常场景：自定义相机配置"""
        custom = [CameraConfig("test_cam", 640, 480, 15, (0, 15), 0.5, 0.05, 0.05)]
        vds = VisionDetectionSystem(configs=custom)
        assert len(vds.cameras) == 1
        assert vds.cameras[0].camera_id == "test_cam"


class TestAutoPiecingRobot:
    """自动生头机械手测试"""

    def test_perform_piecing_basic(self):
        """正常场景：执行自动生头"""
        robot = AutoPiecingRobot()
        event = YarnBreakSimulator.generate_break_event(5, 300.0, 25.0)
        result = robot.perform_piecing(event)
        assert "event_id" in result
        assert "success" in result
        assert result["success"] in [True, False]
        assert result["piecing_time_ms"] >= 2000.0
        assert len(result["steps"]) == 4
        step_names = [s["name"] for s in result["steps"]]
        assert step_names == ["寻位", "吸纱", "捻接", "检查"]

    def test_piecing_steps_time_sum(self):
        """物理准确性：4步耗时之和应等于总耗时"""
        robot = AutoPiecingRobot()
        random.seed(42)
        event = YarnBreakSimulator.generate_break_event(10, 300.0, 25.0)
        result = robot.perform_piecing(event)
        step_total = sum(s["time_ms"] for s in result["steps"])
        assert abs(step_total - result["piecing_time_ms"]) < 1.0

    def test_piecing_updates_statistics(self):
        """正常场景：生头后统计数据更新"""
        robot = AutoPiecingRobot(efficiency=1.0)
        random.seed(42)
        initial_attempts = robot.piecing_stats["total_attempts"]
        initial_success = robot.piecing_stats["successful"]
        event = YarnBreakSimulator.generate_break_event(0, 300.0, 25.0)
        robot.perform_piecing(event)
        assert robot.piecing_stats["total_attempts"] == initial_attempts + 1
        assert robot.piecing_stats["successful"] >= initial_success

    def test_piecing_success_rate_with_high_efficiency(self):
        """模拟准确率验证：高效率参数应对应高成功率"""
        robot = AutoPiecingRobot(efficiency=0.99)
        random.seed(123)
        successes = 0
        for i in range(200):
            event = YarnBreakSimulator.generate_break_event(i % 32, 300.0, 25.0)
            if robot.perform_piecing(event)["success"]:
                successes += 1
        rate = successes / 200
        assert rate >= 0.85

    def test_extreme_break_position_increases_time(self):
        """物理准确性：断头位置极端时接驳时间应更长"""
        robot = AutoPiecingRobot()
        random.seed(42)
        mid_events = []
        far_events = []
        for _ in range(100):
            e1 = YarnBreakEvent(
                "test1", 0, time.time(), 400.0, 25.0, 300.0,
                "tension_peak", 0.9, True, 20.0, False, 0.0, 0.0, 0.0
            )
            e2 = YarnBreakEvent(
                "test2", 0, time.time(), 750.0, 25.0, 300.0,
                "tension_peak", 0.9, True, 20.0, False, 0.0, 0.0, 0.0
            )
            mid_events.append(robot.perform_piecing(e1)["piecing_time_ms"])
            far_events.append(robot.perform_piecing(e2)["piecing_time_ms"])
        assert sum(far_events) / len(far_events) > sum(mid_events) / len(mid_events)

    def test_fiber_defect_lower_success(self):
        """模拟准确率验证：纤维缺陷断头接驳成功率应较低"""
        robot = AutoPiecingRobot(efficiency=1.0)
        random.seed(777)
        tension_success = 0
        defect_success = 0
        for _ in range(100):
            e_t = YarnBreakEvent(
                "t", 0, time.time(), 400.0, 40.0, 300.0,
                "tension_peak", 0.9, True, 20.0, False, 0.0, 0.0, 0.0
            )
            e_d = YarnBreakEvent(
                "d", 0, time.time(), 400.0, 25.0, 300.0,
                "fiber_defect", 0.9, True, 20.0, False, 0.0, 0.0, 0.0
            )
            if robot.perform_piecing(e_t)["success"]:
                tension_success += 1
            if robot.perform_piecing(e_d)["success"]:
                defect_success += 1
        assert tension_success >= defect_success

    def test_get_performance(self):
        """正常场景：获取机械手性能"""
        robot = AutoPiecingRobot()
        for _ in range(5):
            event = YarnBreakSimulator.generate_break_event(0, 300.0, 25.0)
            robot.perform_piecing(event)
        perf = robot.get_performance()
        assert perf["total_attempts"] == 5
        assert perf["successful"] + perf["failed"] == 5
        assert 0.0 <= perf["success_rate_percent"] <= 100.0
        assert perf["status"] == "idle"

    def test_piecing_time_boundary(self):
        """边界场景：接驳时间不应低于2秒"""
        robot = AutoPiecingRobot()
        random.seed(42)
        for _ in range(200):
            event = YarnBreakSimulator.generate_break_event(0, 300.0, 25.0)
            result = robot.perform_piecing(event)
            assert result["piecing_time_ms"] >= 2000.0


class TestBreakDetectionSystem:
    """完整断头检测系统集成测试"""

    def test_simulate_full_scenario(self):
        """正常场景：完整断-检-接流程模拟"""
        system = BreakDetectionSystem(num_spindles=32)
        random.seed(42)
        result = system.simulate_break_scenario(
            spindle_id=10,
            speed_rpm=350.0,
            tension_cn=28.0,
            fiber_type="cotton"
        )
        assert "break_event" in result
        assert "detection" in result
        assert "auto_piecing" in result
        assert "spindle_status" in result
        assert result["break_event"]["spindle_id"] == 10
        assert result["detection"]["camera_id"] in ["cam_0", "cam_1", "cam_2", "cam_3"]
        assert result["spindle_status"] in ["running", "needs_manual", "broken"]

    def test_status_transitions_on_success(self):
        """正常场景：成功接驳后锭子恢复running"""
        system = BreakDetectionSystem(num_spindles=4)
        robot = AutoPiecingRobot(efficiency=1.0)
        system.piecing_robot = robot
        random.seed(42)
        result = system.simulate_break_scenario(0, 300.0, 25.0)
        if result["detection"].get("camera_id") and result["break_event"].get("detected", True):
            assert result["spindle_status"] == "running"

    def test_initial_all_spindles_running(self):
        """正常场景：初始化所有锭子为running"""
        system = BreakDetectionSystem(num_spindles=32)
        statuses = system.get_spindle_status()
        assert len(statuses) == 32
        assert all(s["status"] == "running" for s in statuses)

    def test_get_statistics_empty(self):
        """正常场景：无断头时统计数据"""
        system = BreakDetectionSystem(num_spindles=8)
        stats = system.get_statistics()
        assert stats["total_breaks"] == 0
        assert stats["detection_rate_percent"] == 0.0
        assert stats["total_downtime_seconds"] == 0.0

    def test_statistics_after_multiple_breaks(self):
        """正常场景：多次断头后统计正确"""
        system = BreakDetectionSystem(num_spindles=32)
        random.seed(42)
        for i in range(10):
            system.simulate_break_scenario(i % 32, 300.0, 25.0)
        stats = system.get_statistics()
        assert stats["total_breaks"] == 10
        assert stats["breaks_detected"] <= 10
        assert stats["breaks_detected"] >= 0
        assert 0.0 <= stats["detection_rate_percent"] <= 100.0

    def test_statistics_time_window(self):
        """边界场景：时间窗口过滤功能"""
        system = BreakDetectionSystem(num_spindles=8)
        random.seed(42)
        system.simulate_break_scenario(0, 300.0, 25.0)
        time.sleep(0.1)
        stats_recent = system.get_statistics(window_seconds=1.0)
        stats_old = system.get_statistics(window_seconds=0.001)
        assert stats_recent["total_breaks"] == 1
        assert stats_old["total_breaks"] == 0

    def test_cause_distribution_in_stats(self):
        """模拟准确率验证：统计中应包含多种断头原因"""
        system = BreakDetectionSystem(num_spindles=32)
        random.seed(12345)
        for _ in range(100):
            system.simulate_break_scenario(random.randint(0, 31), 300.0, 25.0)
        stats = system.get_statistics()
        assert len(stats["break_cause_distribution"]) >= 3

    def test_simulate_boundary_spindle_ids(self):
        """边界场景：边界锭子ID"""
        system = BreakDetectionSystem(num_spindles=32)
        random.seed(42)
        r0 = system.simulate_break_scenario(0, 300.0, 25.0)
        r31 = system.simulate_break_scenario(31, 300.0, 25.0)
        assert r0["break_event"]["spindle_id"] == 0
        assert r31["break_event"]["spindle_id"] == 31

    def test_all_32_spindles_break_counted(self):
        """边界场景：32锭子各断一次的统计"""
        system = BreakDetectionSystem(num_spindles=32)
        random.seed(999)
        for i in range(32):
            system.simulate_break_scenario(i, 300.0, 25.0)
        stats = system.get_statistics()
        assert stats["total_breaks"] == 32
        spindle_counts = stats["spindle_break_counts"]
        assert all(c >= 0 for c in spindle_counts.values())
