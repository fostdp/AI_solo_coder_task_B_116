"""
自动生头与断头检测模拟模块
基于计算机视觉的纱线断头检测仿真与自动生头机械手模拟
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class YarnBreakEvent:
    """纱线断头事件"""
    event_id: str
    spindle_id: int
    timestamp: float
    break_position_mm: float
    tension_at_break_cn: float
    speed_at_break_rpm: float
    break_cause: str
    confidence_score: float
    detected: bool
    detection_latency_ms: float
    auto_piecing_success: bool
    piecing_time_ms: float
    yarn_length_lost_m: float
    downtime_seconds: float


@dataclass
class CameraConfig:
    """视觉检测相机配置"""
    camera_id: str
    resolution_width: int
    resolution_height: int
    fps: int
    coverage_spindle_range: Tuple[int, int]
    detection_threshold: float
    false_positive_rate: float
    false_negative_rate: float


class YarnBreakSimulator:
    """纱线断头仿真器"""

    BREAK_CAUSES = [
        ("tension_peak", 0.35, "张力峰值"),
        ("fiber_defect", 0.20, "纤维缺陷"),
        ("improper_twist", 0.15, "捻度不匀"),
        ("roller_slip", 0.12, "罗拉打滑"),
        ("foreign_matter", 0.08, "飞花杂质"),
        ("mechanical_vibration", 0.07, "机械振动"),
        ("other", 0.03, "其他原因")
    ]

    @staticmethod
    def generate_break_event(
        spindle_id: int,
        base_speed_rpm: float,
        base_tension_cn: float,
        fiber_type: str = "cotton",
        detection_system: "VisionDetectionSystem" = None
    ) -> YarnBreakEvent:
        """生成断头事件"""
        ts = time.time()
        rand = random.random()
        cumulative = 0.0
        break_cause = "other"
        for cause, prob, _ in YarnBreakSimulator.BREAK_CAUSES:
            cumulative += prob
            if rand <= cumulative:
                break_cause = cause
                break

        tension_factor = 1.0
        if break_cause == "tension_peak":
            tension_factor = 1.8 + random.random() * 0.8
        elif break_cause == "fiber_defect":
            tension_factor = 0.9 + random.random() * 0.3

        tension_at_break = base_tension_cn * tension_factor
        speed_at_break = base_speed_rpm * (0.95 + random.random() * 0.1)
        break_position = random.uniform(50.0, 800.0)

        detected = True
        latency = 0.0
        confidence = 0.0
        if detection_system:
            result = detection_system.detect_break(spindle_id, break_cause)
            detected = result["detected"]
            latency = result["latency_ms"]
            confidence = result["confidence"]
        else:
            confidence = 0.85 + random.random() * 0.15

        return YarnBreakEvent(
            event_id=f"break_{int(ts*1000)}_{spindle_id}_{random.randint(1000,9999)}",
            spindle_id=spindle_id,
            timestamp=ts,
            break_position_mm=round(break_position, 2),
            tension_at_break_cn=round(tension_at_break, 2),
            speed_at_break_rpm=round(speed_at_break, 1),
            break_cause=break_cause,
            confidence_score=round(confidence, 4),
            detected=detected,
            detection_latency_ms=round(latency, 1),
            auto_piecing_success=False,
            piecing_time_ms=0.0,
            yarn_length_lost_m=0.0,
            downtime_seconds=0.0
        )

    @staticmethod
    def calculate_break_probability(
        speed_rpm: float,
        tension_cn: float,
        max_tension_cn: float,
        fiber_strength_cn_dtex: float,
        yarn_count_tex: float,
        twist_cv_percent: float,
        operating_hours: float = 0.0
    ) -> float:
        """计算断头概率"""
        tension_ratio = tension_cn / max_tension_cn
        speed_factor = (speed_rpm / 400.0) ** 1.5
        twist_factor = 1.0 + max(0, twist_cv_percent - 8) / 40
        wear_factor = 1.0 + operating_hours / 1000 * 0.2

        base_prob = 0.0001
        if tension_ratio > 0.8:
            base_prob *= math.exp(4 * (tension_ratio - 0.8))

        return min(base_prob * speed_factor * twist_factor * wear_factor * 100, 0.5)


class WaveletDenoiser:
    """Daubechies-4 (db4) 小波软阈值去噪器，用于消除视觉检测信号噪声"""

    DB4_DECOMPOSE = [0.4829629131445341, 0.8365163037378079, 0.2241438680420134, -0.1294095225512604]
    DB4_RECONSTRUCT = [-0.1294095225512604, -0.2241438680420134, 0.8365163037378079, -0.4829629131445341]

    @staticmethod
    def _next_pow2(n: int) -> int:
        return 1 if n == 0 else 2 ** math.ceil(math.log2(n))

    @classmethod
    def dwt(cls, signal: List[float]) -> Tuple[List[float], List[float]]:
        """一维离散小波分解（db4），返回近似系数cA和细节系数cD"""
        n = len(signal)
        padded = signal + [0.0] * (cls._next_pow2(n) - n) if n & (n - 1) else list(signal)
        L = len(padded)
        cA, cD = [0.0] * (L // 2), [0.0] * (L // 2)
        h0, h1, h2, h3 = cls.DB4_DECOMPOSE
        for i in range(L // 2):
            j = 2 * i
            cA[i] = h0 * padded[j] + h1 * padded[(j + 1) % L] + h2 * padded[(j + 2) % L] + h3 * padded[(j + 3) % L]
            cD[i] = h3 * padded[j] - h2 * padded[(j + 1) % L] + h1 * padded[(j + 2) % L] - h0 * padded[(j + 3) % L]
        return cA, cD

    @classmethod
    def idwt(cls, cA: List[float], cD: List[float], original_len: int) -> List[float]:
        """一维离散小波重构（Mallat算法的上采样+卷积合成）"""
        n = len(cA)
        L = n * 2
        padded = [0.0] * L
        h0, h1, h2, h3 = cls.DB4_DECOMPOSE
        g0, g1, g2, g3 = h3, -h2, h1, -h0
        for i in range(n):
            k = 2 * i
            padded[k] += g0 * cA[i] + g3 * cD[i]
            if k + 1 < L:
                padded[k + 1] += g1 * cA[i] + g2 * cD[i]
            if k + 2 < L:
                padded[k + 2] += g2 * cA[i] - g1 * cD[i]
            if k + 3 < L:
                padded[k + 3] += g3 * cA[i] - g0 * cD[i]
        return padded[:original_len] if original_len <= len(padded) else padded

    @classmethod
    def universal_threshold(cls, detail_coeffs: List[float], n: int) -> float:
        """Donoho-Johnstone通用阈值 σ·√(2·ln n)"""
        if len(detail_coeffs) == 0:
            return 0.0
        mean_val = sum(detail_coeffs) / len(detail_coeffs)
        deviations = [abs(x - mean_val) for x in detail_coeffs]
        deviations.sort()
        median = deviations[len(deviations) // 2]
        sigma = 1.4826 * median
        return sigma * math.sqrt(2 * math.log(max(n, 2)))

    @staticmethod
    def soft_threshold(x: float, threshold: float) -> float:
        """软阈值函数：sign(x)·max(|x|-T, 0)"""
        if x > threshold:
            return x - threshold
        elif x < -threshold:
            return x + threshold
        return 0.0

    @classmethod
    def denoise_signal(cls, signal: List[float], levels: int = 3) -> List[float]:
        """
        多层小波分解+软阈值+重构完成去噪
        :param signal: 含噪信号序列
        :param levels: 分解层数（1-4）
        :return: 去噪后的信号
        """
        if not signal:
            return []
        if len(signal) < 4:
            return list(signal)
        levels = max(1, min(levels, 4))
        n = len(signal)
        coeffs_stack = []
        current = list(signal)
        for _ in range(levels):
            if len(current) < 4:
                break
            cA, cD = cls.dwt(current)
            coeffs_stack.append(cD)
            current = cA
        for i, cD in enumerate(reversed(coeffs_stack)):
            thr = cls.universal_threshold(cD, n)
            cD_thr = [cls.soft_threshold(v, thr) for v in cD]
            current = cls.idwt(current, cD_thr, len(current) * 2)
        return current[:n]

    @classmethod
    def denoise_single_value(cls, buffer: List[float], new_value: float, window: int = 32, levels: int = 3) -> float:
        """
        滑动窗口的单值去噪：维护时间窗口，返回当前时刻去噪估计
        :param buffer: 历史信号缓冲（会被in-place更新）
        :param new_value: 当前新观测值
        :param window: 窗口长度
        :param levels: 小波分解层数
        :return: 去噪后的当前值
        """
        buffer.append(new_value)
        if len(buffer) > window:
            buffer.pop(0)
        if len(buffer) < 8:
            return new_value
        denoised = cls.denoise_signal(buffer, levels)
        return denoised[-1]


class VisionDetectionSystem:
    """机器视觉断头检测系统"""

    def __init__(self, configs: List[CameraConfig] = None):
        self.cameras = configs or self._default_cameras()
        self.detection_stats = {
            "total_scanned": 0,
            "breaks_detected": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "avg_latency_ms": 0.0
        }
        self._denoiser = WaveletDenoiser()
        self._confidence_buffers: Dict[int, List[float]] = {}
        self._denoise_enabled = True

    def enable_denoise(self, enabled: bool = True):
        """启用或禁用小波去噪"""
        self._denoise_enabled = enabled

    @staticmethod
    def _default_cameras() -> List[CameraConfig]:
        """默认相机配置（32锭子，4台相机，每台覆盖8锭）"""
        return [
            CameraConfig("cam_0", 1280, 720, 30, (0, 7), 0.65, 0.02, 0.03),
            CameraConfig("cam_1", 1280, 720, 30, (8, 15), 0.65, 0.02, 0.03),
            CameraConfig("cam_2", 1280, 720, 30, (16, 23), 0.65, 0.02, 0.03),
            CameraConfig("cam_3", 1280, 720, 30, (24, 31), 0.65, 0.02, 0.03)
        ]

    def _find_camera(self, spindle_id: int) -> Optional[CameraConfig]:
        for cam in self.cameras:
            start, end = cam.coverage_spindle_range
            if start <= spindle_id <= end:
                return cam
        return None

    def detect_break(self, spindle_id: int, break_cause: str = None) -> Dict:
        """模拟视觉检测（支持小波去噪）"""
        cam = self._find_camera(spindle_id)
        self.detection_stats["total_scanned"] += 1

        if not cam:
            return {
                "detected": False,
                "confidence": 0.0,
                "latency_ms": 0.0,
                "camera_id": None,
                "error": "No camera covers this spindle"
            }

        base_confidence = 0.92
        if break_cause == "fiber_defect":
            base_confidence = 0.85
        elif break_cause == "foreign_matter":
            base_confidence = 0.88
        elif break_cause == "mechanical_vibration":
            base_confidence = 0.78

        raw_noise = random.gauss(0, 0.05)
        raw_confidence = base_confidence + raw_noise

        if self._denoise_enabled:
            if spindle_id not in self._confidence_buffers:
                self._confidence_buffers[spindle_id] = []
            smoothed = self._denoiser.denoise_single_value(
                self._confidence_buffers[spindle_id],
                raw_confidence,
                window=24,
                levels=3
            )
            confidence = max(0.1, min(0.99, smoothed))
            noise_reduction_ratio = abs(raw_confidence - base_confidence) / max(abs(confidence - base_confidence), 1e-6)
        else:
            confidence = max(0.1, min(0.99, raw_confidence))
            noise_reduction_ratio = 1.0
        detected = confidence > cam.detection_threshold

        rand = random.random()
        if not detected and rand < cam.false_negative_rate:
            detected = False
        elif not detected:
            detected = True

        if detected and rand < cam.false_positive_rate:
            pass

        latency = 18.0 + random.gauss(0, 5.0)
        latency = max(8.0, latency)

        if detected:
            self.detection_stats["breaks_detected"] += 1

        self.detection_stats["avg_latency_ms"] = (
            self.detection_stats["avg_latency_ms"] * (self.detection_stats["total_scanned"] - 1) + latency
        ) / self.detection_stats["total_scanned"]

        return {
            "detected": detected,
            "confidence": round(confidence, 4),
            "raw_confidence": round(raw_confidence, 4),
            "noise_reduction_ratio_db": round(10 * math.log10(max(noise_reduction_ratio, 1.01)), 2),
            "wavelet_denoised": self._denoise_enabled,
            "latency_ms": round(latency, 2),
            "camera_id": cam.camera_id,
            "bounding_box": {
                "x": random.randint(100, 1100),
                "y": random.randint(100, 600),
                "width": random.randint(40, 120),
                "height": random.randint(40, 120)
            },
            "frame_number": random.randint(0, 9999),
            "detection_algorithm": "YOLOv8-BreakNet + db4-WaveletDenoise"
        }

    def get_system_status(self) -> Dict:
        """获取检测系统状态"""
        total = max(1, self.detection_stats["total_scanned"])
        return {
            "cameras": [
                {
                    "camera_id": c.camera_id,
                    "resolution": f"{c.resolution_width}x{c.resolution_height}",
                    "fps": c.fps,
                    "coverage": f"锭{c.coverage_spindle_range[0]}-{c.coverage_spindle_range[1]}"
                } for c in self.cameras
            ],
            "statistics": {
                "total_frames_scanned": self.detection_stats["total_scanned"],
                "breaks_detected": self.detection_stats["breaks_detected"],
                "detection_rate_percent": round(self.detection_stats["breaks_detected"] / total * 100, 4),
                "avg_detection_latency_ms": round(self.detection_stats["avg_latency_ms"], 2)
            },
            "algorithm": {
                "name": "YOLOv8-BreakNet",
                "input_size": "640x640",
                "model_size_mb": 27.3,
                "inference_device": "NVIDIA Jetson Orin",
                "pretrained_dataset": "YarnBreak-20K"
            }
        }


class AutoPiecingRobot:
    """自动生头机械手"""

    def __init__(self, robot_id: str = "robot_0", efficiency: float = 0.95):
        self.robot_id = robot_id
        self.efficiency = efficiency
        self.piecing_stats = {
            "total_attempts": 0,
            "successful": 0,
            "failed": 0,
            "total_piecing_time_ms": 0.0,
            "total_yarn_saved_m": 0.0
        }
        self.current_task = None

    def perform_piecing(self, break_event: YarnBreakEvent) -> Dict:
        """执行自动生头操作"""
        self.piecing_stats["total_attempts"] += 1
        self.current_task = break_event.event_id

        success = random.random() < self.efficiency
        if break_event.break_cause in ("tension_peak", "foreign_matter"):
            if success:
                success = random.random() < 0.92
        elif break_event.break_cause == "fiber_defect":
            if success:
                success = random.random() < 0.85

        base_time = 3500.0
        if break_event.break_position_mm > 600:
            base_time += 800.0
        elif break_event.break_position_mm < 200:
            base_time += 500.0

        piecing_time = base_time + random.gauss(0, 400.0)
        piecing_time = max(2000.0, piecing_time)

        yarn_lost = break_event.break_position_mm / 1000.0 * 1.2
        yarn_saved = 0.0
        if success:
            yarn_saved = max(0, 5.0 - yarn_lost)
            self.piecing_stats["successful"] += 1
            self.piecing_stats["total_yarn_saved_m"] += yarn_saved
        else:
            self.piecing_stats["failed"] += 1

        self.piecing_stats["total_piecing_time_ms"] += piecing_time

        downtime = piecing_time / 1000.0 + 1.5

        break_event.auto_piecing_success = success
        break_event.piecing_time_ms = round(piecing_time, 1)
        break_event.yarn_length_lost_m = round(yarn_lost, 3)
        break_event.downtime_seconds = round(downtime, 2)

        self.current_task = None

        return {
            "event_id": break_event.event_id,
            "robot_id": self.robot_id,
            "success": success,
            "piecing_time_ms": round(piecing_time, 1),
            "yarn_lost_m": round(yarn_lost, 3),
            "yarn_saved_m": round(yarn_saved, 3),
            "downtime_seconds": round(downtime, 2),
            "break_cause": break_event.break_cause,
            "steps": [
                {"name": "寻位", "time_ms": round(piecing_time * 0.15, 1)},
                {"name": "吸纱", "time_ms": round(piecing_time * 0.20, 1)},
                {"name": "捻接", "time_ms": round(piecing_time * 0.45, 1)},
                {"name": "检查", "time_ms": round(piecing_time * 0.20, 1)}
            ]
        }

    def get_performance(self) -> Dict:
        """获取机械手性能统计"""
        total = max(1, self.piecing_stats["total_attempts"])
        return {
            "robot_id": self.robot_id,
            "total_attempts": self.piecing_stats["total_attempts"],
            "successful": self.piecing_stats["successful"],
            "failed": self.piecing_stats["failed"],
            "success_rate_percent": round(self.piecing_stats["successful"] / total * 100, 2),
            "avg_piecing_time_ms": round(self.piecing_stats["total_piecing_time_ms"] / total, 1),
            "total_yarn_saved_m": round(self.piecing_stats["total_yarn_saved_m"], 3),
            "current_task": self.current_task,
            "status": "idle" if not self.current_task else "working"
        }


class BreakDetectionSystem:
    """完整断头检测与自动生头系统"""

    def __init__(self, num_spindles: int = 32):
        self.num_spindles = num_spindles
        self.vision_system = VisionDetectionSystem()
        self.piecing_robot = AutoPiecingRobot()
        self.break_history: List[YarnBreakEvent] = []
        self.spindle_status = {i: "running" for i in range(num_spindles)}

    def simulate_break_scenario(
        self,
        spindle_id: int,
        speed_rpm: float,
        tension_cn: float,
        fiber_type: str = "cotton"
    ) -> Dict:
        """模拟完整断-检-接流程"""
        break_event = YarnBreakSimulator.generate_break_event(
            spindle_id, speed_rpm, tension_cn, fiber_type, self.vision_system
        )
        self.spindle_status[spindle_id] = "broken"
        self.break_history.append(break_event)

        piecing_result = None
        if break_event.detected:
            piecing_result = self.piecing_robot.perform_piecing(break_event)
            if piecing_result["success"]:
                self.spindle_status[spindle_id] = "running"
            else:
                self.spindle_status[spindle_id] = "needs_manual"

        return {
            "break_event": {
                "event_id": break_event.event_id,
                "spindle_id": break_event.spindle_id,
                "timestamp": break_event.timestamp,
                "break_cause": break_event.break_cause,
                "break_cause_cn": next((c for _, _, c in YarnBreakSimulator.BREAK_CAUSES if _ == break_event.break_cause), "未知"),
                "tension_at_break_cn": break_event.tension_at_break_cn,
                "speed_at_break_rpm": break_event.speed_at_break_rpm,
                "confidence": break_event.confidence_score,
                "detection_latency_ms": break_event.detection_latency_ms
            },
            "detection": {
                "detected": break_event.detected,
                "camera_id": cam.camera_id if (cam := self.vision_system._find_camera(spindle_id)) else None
            },
            "auto_piecing": piecing_result,
            "spindle_status": self.spindle_status[spindle_id]
        }

    def get_statistics(self, window_seconds: float = None) -> Dict:
        """获取系统统计数据"""
        history = self.break_history
        if window_seconds:
            cutoff = time.time() - window_seconds
            history = [e for e in history if e.timestamp >= cutoff]

        detected = sum(1 for e in history if e.detected)
        pieced = sum(1 for e in history if e.auto_piecing_success)
        total_downtime = sum(e.downtime_seconds for e in history)
        total_yarn_lost = sum(e.yarn_length_lost_m for e in history)
        avg_latency = sum(e.detection_latency_ms for e in history) / max(1, len(history))
        avg_piecing = sum(e.piecing_time_ms for e in history if e.piecing_time_ms > 0) / max(1, pieced)

        cause_dist = {}
        for e in history:
            cause_dist[e.break_cause] = cause_dist.get(e.break_cause, 0) + 1

        return {
            "window_seconds": window_seconds,
            "total_breaks": len(history),
            "breaks_detected": detected,
            "detection_rate_percent": round(detected / max(1, len(history)) * 100, 2),
            "auto_pieced": pieced,
            "auto_piecing_success_rate_percent": round(pieced / max(1, detected) * 100, 2),
            "total_downtime_seconds": round(total_downtime, 2),
            "total_yarn_lost_m": round(total_yarn_lost, 3),
            "avg_detection_latency_ms": round(avg_latency, 2),
            "avg_piecing_time_ms": round(avg_piecing, 1),
            "spindle_break_counts": {
                i: sum(1 for e in history if e.spindle_id == i) for i in range(self.num_spindles)
            },
            "break_cause_distribution": cause_dist
        }

    def get_spindle_status(self) -> List[Dict]:
        """获取所有锭子状态"""
        return [
            {"spindle_id": i, "status": self.spindle_status[i]}
            for i in range(self.num_spindles)
        ]
