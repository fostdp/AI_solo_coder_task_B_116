from typing import Dict, List

from .models import LodLevel


LOD_TABLE = [
    LodLevel("ULTRA", "超精细（旗舰设备）", 50, 400, 30, 1, 2, 80, 58.0),
    LodLevel("HIGH", "精细（高性能设备）", 30, 200, 20, 1, 1, 50, 40.0),
    LodLevel("MEDIUM", "标准（普通设备）", 20, 120, 15, 2, 1, 30, 24.0),
    LodLevel("LOW", "节能（低性能设备）", 12, 80, 10, 3, 1, 18, 15.0),
    LodLevel("MINIMAL", "极简（嵌入式/省电）", 6, 40, 5, 6, 1, 8, 5.0),
]


class LodManager:
    """
    LOD（Level of Detail）性能管理器
    通过采样间隔估算渲染负载，自动调整细节等级
    """

    def __init__(self, initial_level: int = 2, adapt_enabled: bool = True):
        self._current_level = initial_level
        self._adapt_enabled = adapt_enabled
        self._frame_timings: List[float] = []
        self._estimated_fps = 30.0
        self._downgrade_count = 0
        self._upgrade_count = 0
        self._hysteresis_frames = 60

    @property
    def level(self) -> LodLevel:
        return LOD_TABLE[self._current_level]

    @property
    def level_index(self) -> int:
        return self._current_level

    def set_manual_level(self, level_index: int):
        """手动锁定LOD等级"""
        self._current_level = max(0, min(len(LOD_TABLE) - 1, level_index))
        self._adapt_enabled = False

    def enable_auto_adapt(self):
        """启用自动调节"""
        self._adapt_enabled = True

    def sample_frame_time(self, delta_seconds: float):
        """
        采样一帧耗时，用于自动估计FPS并调节LOD
        """
        if delta_seconds <= 0:
            return
        self._frame_timings.append(delta_seconds)
        if len(self._frame_timings) > self._hysteresis_frames:
            self._frame_timings.pop(0)
        avg_dt = sum(self._frame_timings) / len(self._frame_timings)
        self._estimated_fps = 1.0 / max(avg_dt, 1e-6)
        if not self._adapt_enabled:
            return
        if len(self._frame_timings) < 30:
            return
        current = self.level
        if self._estimated_fps < current.min_fps_target * 0.85 and self._current_level < len(LOD_TABLE) - 1:
            self._downgrade_count += 1
            if self._downgrade_count >= 30:
                self._current_level += 1
                self._downgrade_count = 0
                self._upgrade_count = 0
        elif self._estimated_fps > current.min_fps_target * 1.4 and self._current_level > 0:
            self._upgrade_count += 1
            if self._upgrade_count >= 60:
                self._current_level -= 1
                self._upgrade_count = 0
                self._downgrade_count = 0
        else:
            self._downgrade_count = max(0, self._downgrade_count - 1)
            self._upgrade_count = max(0, self._upgrade_count - 1)

    def get_performance_report(self) -> Dict:
        return {
            "current_lod": self.level.name,
            "current_lod_cn": self.level.name_cn,
            "level_index": self._current_level,
            "estimated_fps": round(self._estimated_fps, 1),
            "auto_adapt_enabled": self._adapt_enabled,
            "downgrade_pending_count": self._downgrade_count,
            "upgrade_pending_count": self._upgrade_count,
            "lod_table_snapshot": [
                {"name": l.name, "cn": l.name_cn, "fiber_count": l.fiber_count, "min_fps": l.min_fps_target}
                for l in LOD_TABLE
            ]
        }
