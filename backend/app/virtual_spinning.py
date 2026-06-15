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

    def __init__(self, session_id: str = None):
        self.session_id = session_id or f"session_{int(time.time()*1000000)}_{random.randint(1000, 9999)}"
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
        """初始化纤维池"""
        colors = self.FIBER_COLORS.get(self.state.fiber_type, "#FFF8E7")
        for i in range(200):
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
        self.state.fibers = random.sample(self._fiber_pool, 30)

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
        """执行一次纺纱时间步长"""
        if not self.state.is_running:
            return self.state

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

        self._update_fibers(dt, delivery_speed)
        self._update_scores(length_added)

        return self.state

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
        """获取当前状态快照（用于前端渲染）"""
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
            "fibers": [
                {
                    "x": round(f.x, 1),
                    "y": round(f.y, 1),
                    "angle": round(f.angle, 3),
                    "length": round(f.length, 1),
                    "thickness": round(f.thickness, 2),
                    "color": f.color
                }
                for f in self.state.fibers[:20]
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
