"""
公众体验虚拟纺纱模块
用户可实时调节水流速度、原料纤维等参数，观察纱线生成过程
"""
from __future__ import annotations

import math
import time
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class YarnFiber:
    """单根虚拟纤维"""
    fiber_id: int
    x: float
    y: float
    angle: float
    length: float
    thickness: float
    color: str
    speed: float


@dataclass
class LodLevel:
    """LOD等级定义"""
    name: str
    name_cn: str
    fiber_count: int
    fiber_pool_size: int
    snapshot_fiber_limit: int
    particle_update_skip: int
    physics_substeps: int
    water_particle_count: int
    min_fps_target: float


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


@dataclass
class VirtualSpinningState:
    """虚拟纺纱状态"""
    session_id: str
    start_time: float
    water_speed: float
    fiber_type: str
    wheel_rpm: float
    spindle_rpm: float
    yarn_length_m: float
    yarn_count_tex: float
    yarn_tension_cn: float
    yarn_twist_per_m: float
    fibers: List[YarnFiber]
    twist_rotation: float
    quality_score: float
    efficiency_score: float
    break_count: int
    is_running: bool
    message: str


class VirtualSpinningEngine:
    """虚拟纺纱引擎"""

    FIBER_COLORS = {
        "cotton": "#FFF8E7",
        "hemp": "#F5E6C8",
        "flax": "#E8D4A8",
        "silk": "#FFF5F0",
        "wool": "#FAF0E6"
    }

    def __init__(self, session_id: str = None, lod_level: int = 2):
        self.session_id = session_id or f"session_{int(time.time()*1000000)}_{random.randint(1000, 9999)}"
        self.lod = LodManager(initial_level=lod_level, adapt_enabled=True)
        self._tick_counter = 0
        self._last_lod_adjust_at = 0
        self.state = VirtualSpinningState(
            session_id=self.session_id,
            start_time=time.time(),
            water_speed=2.0,
            fiber_type="cotton",
            wheel_rpm=0.0,
            spindle_rpm=0.0,
            yarn_length_m=0.0,
            yarn_count_tex=100.0,
            yarn_tension_cn=20.0,
            yarn_twist_per_m=350.0,
            fibers=[],
            twist_rotation=0.0,
            quality_score=0.0,
            efficiency_score=0.0,
            break_count=0,
            is_running=False,
            message="准备就绪，请调整参数后开始纺纱"
        )
        self._fiber_pool = []
        self._initialize_fiber_pool()

    def _initialize_fiber_pool(self):
        """初始化纤维池（根据当前LOD等级动态调整数量）"""
        lod = self.lod.level
        pool_size = lod.fiber_pool_size
        visible_count = lod.fiber_count
        colors = self.FIBER_COLORS.get(self.state.fiber_type, "#FFF8E7")
        self._fiber_pool = []
        for i in range(pool_size):
            self._fiber_pool.append(YarnFiber(
                fiber_id=i,
                x=random.uniform(-50, 50),
                y=random.uniform(-30, 30),
                angle=random.uniform(-0.2, 0.2),
                length=random.uniform(20, 40),
                thickness=random.uniform(0.8, 1.5),
                color=colors,
                speed=0.0
            ))
        self.state.fibers = random.sample(self._fiber_pool, min(visible_count, len(self._fiber_pool)))

    def set_lod_level(self, level_index: int):
        """手动设置LOD等级并重建纤维池"""
        old_index = self.lod.level_index
        self.lod.set_manual_level(level_index)
        if self.lod.level_index != old_index:
            self._initialize_fiber_pool()

    def set_parameters(self, water_speed: float = None, fiber_type: str = None):
        """设置纺纱参数"""
        if water_speed is not None:
            self.state.water_speed = max(0.1, min(8.0, float(water_speed)))
        if fiber_type is not None and fiber_type in self.FIBER_COLORS:
            self.state.fiber_type = fiber_type
            new_color = self.FIBER_COLORS[fiber_type]
            for f in self.state.fibers:
                f.color = new_color
        self._update_message()

    def start(self):
        """开始纺纱"""
        self.state.is_running = True
        self.state.message = "纺纱进行中..."

    def pause(self):
        """暂停纺纱"""
        self.state.is_running = False
        self.state.message = "已暂停"

    def reset(self):
        """重置纺纱"""
        self.state.is_running = False
        self.state.yarn_length_m = 0.0
        self.state.break_count = 0
        self.state.quality_score = 0.0
        self.state.efficiency_score = 0.0
        self.state.twist_rotation = 0.0
        self.state.wheel_rpm = 0.0
        self.state.spindle_rpm = 0.0
        self.state.message = "已重置，准备开始"
        self._initialize_fiber_pool()

    def _update_message(self):
        """根据参数更新提示消息"""
        if self.state.water_speed < 0.5:
            self.state.message = "水流太慢，水轮可能无法启动"
        elif self.state.water_speed > 6.0:
            self.state.message = "水流过快，注意张力过大可能断头"
        elif self.state.water_speed < 1.0:
            self.state.message = "水流偏弱，产量较低"
        else:
            self.state.message = "参数良好，可以开始纺纱"

    def tick(self, dt: float = 0.05) -> VirtualSpinningState:
        """执行一次纺纱时间步长（LOD自适应：粒子更新跳帧、物理子步）"""
        tick_start = time.perf_counter()
        self._tick_counter += 1
        if not self.state.is_running:
            self.lod.sample_frame_time(dt)
            return self.state

        lod = self.lod.level
        substeps = max(1, lod.physics_substeps)
        sub_dt = dt / substeps
        for _ in range(substeps):
            self._physics_step(sub_dt)

        if self._tick_counter % lod.particle_update_skip == 0:
            delivery_speed = max(0, self.state.spindle_rpm * 1000 / max(self.state.yarn_twist_per_m, 1) / 60)
            self._update_fibers(dt * lod.particle_update_skip, delivery_speed)

        self.lod.sample_frame_time(time.perf_counter() - tick_start)
        return self.state

    def _physics_step(self, dt: float):
        """单个物理子步：水轮/锭子/张力/断头"""
        water_speed = self.state.water_speed
        water_power = 0.5 * 1000 * math.pi * (2.5 ** 2) * (water_speed ** 3) * 0.25

        target_wheel_rpm = min(water_speed * 12, 80.0)
        self.state.wheel_rpm += (target_wheel_rpm - self.state.wheel_rpm) * min(dt * 2, 1.0)

        target_spindle_rpm = self.state.wheel_rpm * 12 * 0.72
        self.state.spindle_rpm += (target_spindle_rpm - self.state.spindle_rpm) * min(dt * 1.5, 1.0)

        twist_per_sec = self.state.spindle_rpm / 60
        self.state.twist_rotation += twist_per_sec * dt * math.pi * 2

        delivery_speed = max(0, self.state.spindle_rpm * 1000 / max(self.state.yarn_twist_per_m, 1) / 60)
        length_added = delivery_speed * dt
        self.state.yarn_length_m += length_added

        base_tension = 15.0 + water_speed * 4.0
        if self.state.fiber_type == "silk":
            base_tension *= 0.8
        elif self.state.fiber_type == "hemp":
            base_tension *= 1.3
        self.state.yarn_tension_cn = base_tension + math.sin(time.time() * 2) * 2

        max_tension = 80.0
        break_prob = 0.0
        tension_ratio = self.state.yarn_tension_cn / max_tension
        if tension_ratio > 0.8:
            break_prob = 0.001 * math.exp(4 * (tension_ratio - 0.8))
        if random.random() < break_prob * dt * 20:
            self.state.break_count += 1
            self.state.spindle_rpm *= 0.3
            self.state.message = f"发生断头！累计断头 {self.state.break_count} 次"
        self._update_scores(length_added)

    def _update_fibers(self, dt: float, delivery_speed: float):
        """更新纤维位置"""
        for fiber in self.state.fibers:
            fiber.x -= delivery_speed * dt * 100
            fiber.angle += math.sin(time.time() * 5 + fiber.fiber_id) * 0.02

            if fiber.x < -100:
                fiber.x = 100 + random.uniform(0, 50)
                fiber.y = random.uniform(-25, 25)
                fiber.angle = random.uniform(-0.3, 0.3)
                fiber.speed = delivery_speed * 100

    def _update_scores(self, length_added: float):
        """更新质量和效率评分"""
        if self.state.yarn_length_m > 0:
            tension_deviation = abs(self.state.yarn_tension_cn - 25) / 25
            speed_stability = 1.0 - abs(self.state.spindle_rpm - 300) / 600
            break_penalty = self.state.break_count * 0.05

            self.state.quality_score = max(0, min(100,
                (1.0 - tension_deviation * 0.5) * speed_stability * 100 - break_penalty * 10
            ))

            water_efficiency = length_added / max(self.state.water_speed, 0.1)
            ideal_production = 0.008
            self.state.efficiency_score = max(0, min(100,
                water_efficiency / ideal_production * 50 + speed_stability * 50
            ))

    def get_snapshot(self) -> Dict:
        """获取当前状态快照（LOD自适应限制纤维数）"""
        lod = self.lod.level
        fiber_limit = min(lod.snapshot_fiber_limit, len(self.state.fibers))
        return {
            "session_id": self.state.session_id,
            "running_time_seconds": round(time.time() - self.state.start_time, 1),
            "water_speed": round(self.state.water_speed, 2),
            "fiber_type": self.state.fiber_type,
            "fiber_name": {
                "cotton": "棉花", "hemp": "苎麻", "flax": "亚麻",
                "silk": "桑蚕丝", "wool": "绵羊毛"
            }.get(self.state.fiber_type, "未知"),
            "wheel_rpm": round(self.state.wheel_rpm, 1),
            "spindle_rpm": round(self.state.spindle_rpm, 1),
            "yarn_length_m": round(self.state.yarn_length_m, 3),
            "yarn_tension_cn": round(self.state.yarn_tension_cn, 2),
            "twist_rotation_rad": round(self.state.twist_rotation, 3),
            "quality_score": round(self.state.quality_score, 1),
            "efficiency_score": round(self.state.efficiency_score, 1),
            "break_count": self.state.break_count,
            "is_running": self.state.is_running,
            "message": self.state.message,
            "performance": self.lod.get_performance_report(),
            "water_particles_count": lod.water_particle_count,
            "fibers": [
                {
                    "x": round(f.x, 1),
                    "y": round(f.y, 1),
                    "angle": round(f.angle, 3),
                    "length": round(f.length, 1),
                    "thickness": round(f.thickness, 2),
                    "color": f.color
                }
                for f in self.state.fibers[:fiber_limit]
            ]
        }


class PublicExperienceManager:
    """公众体验管理器，管理多个并发纺纱会话"""

    def __init__(self, max_sessions: int = 100):
        self.sessions: Dict[str, VirtualSpinningEngine] = {}
        self.max_sessions = max_sessions

    def create_session(self) -> str:
        """创建新会话"""
        if len(self.sessions) >= self.max_sessions:
            oldest = min(self.sessions.keys(), key=lambda s: self.sessions[s].state.start_time)
            del self.sessions[oldest]

        engine = VirtualSpinningEngine()
        self.sessions[engine.session_id] = engine
        return engine.session_id

    def get_session(self, session_id: str) -> Optional[VirtualSpinningEngine]:
        """获取会话"""
        return self.sessions.get(session_id)

    def remove_session(self, session_id: str):
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]

    def tick_all(self, dt: float = 0.05):
        """所有会话推进一个时间步"""
        for engine in self.sessions.values():
            engine.tick(dt)

    def get_active_count(self) -> int:
        """获取活跃会话数"""
        return sum(1 for e in self.sessions.values() if e.state.is_running)

    def get_statistics(self) -> Dict:
        """获取体验统计"""
        total = len(self.sessions)
        running = self.get_active_count()
        total_length = sum(e.state.yarn_length_m for e in self.sessions.values())
        avg_quality = sum(e.state.quality_score for e in self.sessions.values()) / max(1, total)
        avg_efficiency = sum(e.state.efficiency_score for e in self.sessions.values()) / max(1, total)

        return {
            "total_sessions": total,
            "running_sessions": running,
            "total_yarn_produced_m": round(total_length, 2),
            "avg_quality_score": round(avg_quality, 1),
            "avg_efficiency_score": round(avg_efficiency, 1)
        }
