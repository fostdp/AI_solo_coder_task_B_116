from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class SpindleData(BaseModel):
    spindle_id: int = Field(description="锭子编号")
    speed: float = Field(description="转速 (rpm)")
    tension: float = Field(description="纱线张力 (N)")
    twist: float = Field(description="捻度 (捻/米)")
    broken: bool = Field(default=False, description="是否断头")


class WaterWheelData(BaseModel):
    water_speed: float = Field(description="水流速度 (m/s)")
    blade_angle: float = Field(description="叶片角度 (度)")
    wheel_radius: float = Field(description="水轮半径 (m)")
    torque: float = Field(description="水轮扭矩 (N·m)")
    rotational_speed: float = Field(description="水轮转速 (rpm)")


class TransmissionData(BaseModel):
    gear_ratio: float = Field(description="传动比")
    mechanical_efficiency: float = Field(description="机械效率")
    input_torque: float = Field(description="输入扭矩 (N·m)")
    output_torque: float = Field(description="输出扭矩 (N·m)")
    input_speed: float = Field(description="输入转速 (rpm)")
    output_speed: float = Field(description="输出转速 (rpm)")
    slip_rate: Optional[float] = Field(None, description="皮带打滑率 (0-1)")
    critical_torque: Optional[float] = Field(None, description="临界打滑扭矩 (N·m)")
    belt_friction_coeff: Optional[float] = Field(None, description="皮带摩擦系数")
    wrap_angle_deg: Optional[float] = Field(None, description="包角 (度)")


class SpinningWheelData(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    water_wheel: WaterWheelData = Field(description="水轮数据")
    transmission: TransmissionData = Field(description="传动系统数据")
    spindles: List[SpindleData] = Field(description="锭子数据列表")
    total_production_rate: float = Field(description="总生产率 (米/分钟)")
    energy_efficiency: float = Field(description="能效比 (米/分钟·kW)")
    twist_uniformity_cv: float = Field(description="捻度均匀性变异系数")
    breakage_rate: float = Field(description="断头率 (%)")


class DynamicsRequest(BaseModel):
    water_speed: float = Field(gt=0, description="水流速度 (m/s)")
    blade_angle: float = Field(ge=15, le=75, description="叶片角度 (度)")
    wheel_radius: float = Field(gt=0, description="水轮半径 (m)")
    gear_ratio: float = Field(gt=0, description="传动比")
    mechanical_efficiency: float = Field(gt=0, le=1, description="机械效率")
    num_spindles: int = Field(ge=16, le=64, description="锭子数量")
    friction_coefficient: float = Field(ge=0, description="锭子摩擦系数")
    belt_friction_coeff: float = Field(default=0.35, ge=0.05, le=0.9, description="皮带-轮摩擦系数 (μ)")
    wrap_angle_deg: float = Field(default=180.0, ge=90.0, le=270.0, description="皮带包角 (度)")
    initial_belt_tension: float = Field(default=200.0, ge=50.0, le=1000.0, description="皮带初始张力 (N)")


class DynamicsResponse(BaseModel):
    water_wheel: WaterWheelData
    transmission: TransmissionData
    spindles: List[SpindleData]
    total_production_rate: float
    energy_efficiency: float
    twist_uniformity_cv: float
    breakage_rate: float
    twist_variance: float
    speed_standard_deviation: float


class OptimizationRequest(BaseModel):
    water_speed: float = Field(gt=0, description="水流速度 (m/s)")
    wheel_radius: float = Field(gt=0, description="水轮半径 (m)")
    gear_ratio: float = Field(gt=0, description="传动比")
    mechanical_efficiency: float = Field(gt=0, le=1, description="机械效率")
    friction_coefficient: float = Field(ge=0, description="锭子摩擦系数")
    min_tension: float = Field(gt=0, description="最小纱线张力 (N)")
    max_tension: float = Field(gt=0, description="最大纱线张力 (N)")
    max_twist_cv: float = Field(gt=0, description="最大捻度变异系数")
    population_size: int = Field(default=50, ge=10, description="遗传算法种群大小")
    generations: int = Field(default=100, ge=10, description="遗传算法迭代代数")
    belt_friction_coeff: float = Field(default=0.35, ge=0.05, le=0.9, description="皮带摩擦系数")
    wrap_angle_deg: float = Field(default=180.0, ge=90.0, le=270.0, description="皮带包角 (度)")
    initial_belt_tension: float = Field(default=200.0, ge=50.0, le=1000.0, description="皮带初始张力 (N)")
    weight_energy_efficiency: float = Field(default=0.7, ge=0.0, le=1.0, description="能效目标权重")
    weight_production: float = Field(default=0.3, ge=0.0, le=1.0, description="生产率目标权重")
    weight_twist_uniformity: float = Field(default=0.0, ge=0.0, le=1.0, description="捻度均匀性目标权重")
    weight_low_breakage: float = Field(default=0.0, ge=0.0, le=1.0, description="低断头率目标权重")


class OptimizationResult(BaseModel):
    optimal_num_spindles: int
    optimal_blade_angle: float
    max_objective_value: float
    total_production_rate: float
    energy_efficiency: float
    twist_uniformity_cv: float
    breakage_rate: float
    convergence_history: List[float]
    weights_used: dict = Field(description="实际使用的归一化权重")


class AlarmData(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    alarm_type: str = Field(description="告警类型")
    severity: str = Field(description="告警级别: info/warning/critical")
    message: str = Field(description="告警消息")
    spindle_id: Optional[int] = Field(None, description="相关锭子编号")
    value: Optional[float] = Field(None, description="当前值")
    threshold: Optional[float] = Field(None, description="阈值")


class DataQueryRequest(BaseModel):
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    measurement: Optional[str] = Field(None, description="测量类型")
    limit: Optional[int] = Field(100, description="返回数据条数限制")


class ModbusConfig(BaseModel):
    host: str = Field(default="localhost", description="Modbus TCP主机")
    port: int = Field(default=5020, description="Modbus TCP端口")
    timeout: int = Field(default=5, description="超时时间(秒)")
