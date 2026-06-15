from dataclasses import dataclass
from typing import List


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
class WaterParticle:
    """水粒子"""
    particle_id: int
    x: float
    y: float
    vx: float
    vy: float
    size: float
    life: float


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
