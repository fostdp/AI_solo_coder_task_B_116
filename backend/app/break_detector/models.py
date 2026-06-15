from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


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


@dataclass
class BreakStats:
    """断头检测统计数据"""
    window_seconds: float = None
    total_breaks: int = 0
    breaks_detected: int = 0
    detection_rate_percent: float = 0.0
    auto_pieced: int = 0
    auto_piecing_success_rate_percent: float = 0.0
    total_downtime_seconds: float = 0.0
    total_yarn_lost_m: float = 0.0
    avg_detection_latency_ms: float = 0.0
    avg_piecing_time_ms: float = 0.0
    spindle_break_counts: Dict[int, int] = field(default_factory=dict)
    break_cause_distribution: Dict[str, int] = field(default_factory=dict)
