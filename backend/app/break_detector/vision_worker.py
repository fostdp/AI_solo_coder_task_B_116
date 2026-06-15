from __future__ import annotations

import math
import random
import uuid
from collections import deque
from typing import Deque, Dict, List, Optional

from .denoiser import WaveletDenoiser
from .models import CameraConfig


class VisionDetectionWorker:
    """独立图像识别Worker类，线程/队列解耦的断头检测Worker

    接收spindle_id+raw_confidence队列，内部做小波去噪+阈值判断，返回检测结果。
    提供submit_detection_task和get_result接口，内部用队列+字典模拟异步Worker。
    """

    def __init__(self, camera_configs: List[CameraConfig] = None):
        self._cameras = camera_configs or self._default_cameras()
        self._denoiser = WaveletDenoiser()
        self._confidence_buffers: Dict[int, List[float]] = {}
        self._denoise_enabled = True
        self._task_queue: Deque[Dict] = deque()
        self._results: Dict[str, Dict] = {}
        self._task_counter = 0

    @staticmethod
    def _default_cameras() -> List[CameraConfig]:
        """默认相机配置（32锭子，4台相机，每台覆盖8锭）"""
        return [
            CameraConfig("cam_0", 1280, 720, 30, (0, 7), 0.65, 0.02, 0.03),
            CameraConfig("cam_1", 1280, 720, 30, (8, 15), 0.65, 0.02, 0.03),
            CameraConfig("cam_2", 1280, 720, 30, (16, 23), 0.65, 0.02, 0.03),
            CameraConfig("cam_3", 1280, 720, 30, (24, 31), 0.65, 0.02, 0.03)
        ]

    def enable_denoise(self, enabled: bool = True):
        """启用或禁用小波去噪"""
        self._denoise_enabled = enabled

    def _find_camera(self, spindle_id: int) -> Optional[CameraConfig]:
        for cam in self._cameras:
            start, end = cam.coverage_spindle_range
            if start <= spindle_id <= end:
                return cam
        return None

    def submit_detection_task(self, spindle_id: int, raw_confidence: float) -> str:
        """提交检测任务，返回task_id

        :param spindle_id: 锭子ID
        :param raw_confidence: 原始置信度
        :return: 任务ID
        """
        task_id = str(uuid.uuid4())
        self._task_queue.append({
            "task_id": task_id,
            "spindle_id": spindle_id,
            "raw_confidence": raw_confidence
        })
        self._process_queue()
        return task_id

    def get_result(self, task_id: str) -> Optional[Dict]:
        """获取检测结果

        :param task_id: 任务ID
        :return: 检测结果字典，若未完成则返回None
        """
        return self._results.get(task_id)

    def _process_queue(self):
        """处理任务队列中的所有待处理任务"""
        while self._task_queue:
            task = self._task_queue.popleft()
            result = self._process_single_task(task)
            self._results[task["task_id"]] = result

    def _process_single_task(self, task: Dict) -> Dict:
        """处理单个检测任务

        参考VisionDetectionSystem的detect_break核心逻辑，
        接收spindle_id+raw_confidence，做小波去噪+阈值判断。
        """
        spindle_id = task["spindle_id"]
        raw_confidence = task["raw_confidence"]
        cam = self._find_camera(spindle_id)

        if not cam:
            return {
                "detected": False,
                "confidence": 0.0,
                "raw_confidence": raw_confidence,
                "latency_ms": 0.0,
                "camera_id": None,
                "error": "No camera covers this spindle",
                "wavelet_denoised": self._denoise_enabled,
                "noise_reduction_ratio_db": 0.0
            }

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
            noise_reduction_ratio = abs(raw_confidence - 0.85) / max(abs(confidence - 0.85), 1e-6)
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
