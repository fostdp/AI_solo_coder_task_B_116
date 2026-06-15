import os
import math
from dotenv import load_dotenv

load_dotenv()


class ModbusConfig:
    HOST = os.getenv("MODBUS_HOST", "0.0.0.0")
    PORT = int(os.getenv("MODBUS_PORT", 5020))
    SLAVE_ID = int(os.getenv("MODBUS_SLAVE_ID", 1))


class ReportingConfig:
    INTERVAL_SECONDS = int(os.getenv("REPORT_INTERVAL", 60))


class WaterWheelConfig:
    MAX_RPM = 60.0
    MIN_RPM = 0.0
    INERTIA = 50.0
    FRICTION_COEFF = 0.05
    DIAMETER = 4.0
    TORQUE_COEFF = 800.0


class BeltDriveConfig:
    DRIVEN_PULLEY_RATIO = 5.0
    EFFICIENCY = 0.92
    BASE_SLIP = 0.02

    BELT_FRICTION_COEFF = 0.35
    WRAP_ANGLE_RAD = math.pi
    INITIAL_TENSION = 200.0
    DRIVEN_PULLEY_RADIUS = 0.15

    @classmethod
    def calculate_critical_torque(cls) -> float:
        if cls.BELT_FRICTION_COEFF <= 0 or cls.WRAP_ANGLE_RAD <= 0:
            return float("inf")
        e_mu_alpha = math.exp(cls.BELT_FRICTION_COEFF * cls.WRAP_ANGLE_RAD)
        max_force_diff = 2 * cls.INITIAL_TENSION * (e_mu_alpha - 1) / (e_mu_alpha + 1)
        return max_force_diff * cls.DRIVEN_PULLEY_RADIUS

    @classmethod
    def calculate_slip_rate(cls, required_torque: float) -> float:
        critical_torque = cls.calculate_critical_torque()
        if critical_torque <= 0:
            return 1.0
        if required_torque <= critical_torque:
            elastic_slip = cls.BASE_SLIP * (required_torque / critical_torque)
            return cls.BASE_SLIP * 0.3 + elastic_slip * 0.7
        else:
            severe_slip = 1.0 - critical_torque / required_torque
            return min(0.08 + severe_slip * 0.9, 0.95)


class SpindleConfig:
    COUNT = 32
    MAX_RPM = 1500.0
    MIN_RPM = 0.0
    GEAR_RATIO = 12.0
    FRICTION_TORQUE = 0.15
    RPM_FLUCTUATION = 0.03


class YarnConfig:
    SPEC = os.getenv("YARN_SPEC", "cotton_20s")
    TENSION_MAX = 500.0
    TENSION_MIN = 0.0
    TENSION_NOMINAL = 150.0
    TWIST_MAX = 1000.0
    TWIST_MIN = 0.0
    TWIST_NOMINAL = 400.0
    BREAK_TENSION_THRESHOLD = 420.0
    TWIST_UNEVENNESS_THRESHOLD = 0.25

    # 纱线规格预设库 - 不同材质和支数的物理参数
    SPEC_PRESETS = {
        "cotton_10s": {
            "name": "棉纱10支（粗支）",
            "material": "cotton",
            "count_ne": 10,
            "tension_nominal": 250.0,
            "tension_max": 600.0,
            "break_threshold": 520.0,
            "twist_nominal": 300.0,
            "twist_max": 800.0,
            "twist_uneven_threshold": 0.28,
            "elongation": 0.08,
        },
        "cotton_20s": {
            "name": "棉纱20支（中支）",
            "material": "cotton",
            "count_ne": 20,
            "tension_nominal": 180.0,
            "tension_max": 500.0,
            "break_threshold": 420.0,
            "twist_nominal": 400.0,
            "twist_max": 1000.0,
            "twist_uneven_threshold": 0.25,
            "elongation": 0.06,
        },
        "cotton_30s": {
            "name": "棉纱30支（中支）",
            "material": "cotton",
            "count_ne": 30,
            "tension_nominal": 150.0,
            "tension_max": 450.0,
            "break_threshold": 380.0,
            "twist_nominal": 480.0,
            "twist_max": 1100.0,
            "twist_uneven_threshold": 0.23,
            "elongation": 0.05,
        },
        "cotton_40s": {
            "name": "棉纱40支（细支）",
            "material": "cotton",
            "count_ne": 40,
            "tension_nominal": 120.0,
            "tension_max": 400.0,
            "break_threshold": 340.0,
            "twist_nominal": 550.0,
            "twist_max": 1200.0,
            "twist_uneven_threshold": 0.22,
            "elongation": 0.045,
        },
        "wool_30s": {
            "name": "羊毛30支",
            "material": "wool",
            "count_ne": 30,
            "tension_nominal": 130.0,
            "tension_max": 420.0,
            "break_threshold": 360.0,
            "twist_nominal": 380.0,
            "twist_max": 900.0,
            "twist_uneven_threshold": 0.30,
            "elongation": 0.12,
        },
        "silk_20d": {
            "name": "桑蚕丝20旦",
            "material": "silk",
            "denier": 20,
            "tension_nominal": 80.0,
            "tension_max": 280.0,
            "break_threshold": 240.0,
            "twist_nominal": 700.0,
            "twist_max": 1500.0,
            "twist_uneven_threshold": 0.18,
            "elongation": 0.15,
        },
        "hemp_15s": {
            "name": "麻15支",
            "material": "hemp",
            "count_ne": 15,
            "tension_nominal": 220.0,
            "tension_max": 550.0,
            "break_threshold": 480.0,
            "twist_nominal": 350.0,
            "twist_max": 850.0,
            "twist_uneven_threshold": 0.32,
            "elongation": 0.03,
        },
    }

    @classmethod
    def apply_spec(cls, spec_key: str):
        """根据预设规格键应用纱线参数"""
        preset = cls.SPEC_PRESETS.get(spec_key)
        if preset is None:
            raise ValueError(f"未知纱线规格: {spec_key}, 可用: {list(cls.SPEC_PRESETS.keys())}")
        cls.SPEC = spec_key
        cls.TENSION_NOMINAL = preset["tension_nominal"]
        cls.TENSION_MAX = preset["tension_max"]
        cls.BREAK_TENSION_THRESHOLD = preset["break_threshold"]
        cls.TWIST_NOMINAL = preset["twist_nominal"]
        cls.TWIST_MAX = preset["twist_max"]
        cls.TWIST_UNEVENNESS_THRESHOLD = preset["twist_uneven_threshold"]
        return preset


class PowerConfig:
    MAX_POWER = 5000.0
    MIN_POWER = 0.0
    IDLE_POWER = 150.0
    EFFICIENCY = 0.85


class WaterFlowConfig:
    VELOCITY = float(os.getenv("WATER_VELOCITY", 2.5))
    MIN_VELOCITY = 0.0
    MAX_VELOCITY = 5.0
    FLUCTUATION = 0.1
    MODE = os.getenv("WATER_MODE", "stable")

    # 水流模式预设库
    MODE_PRESETS = {
        "stable": {
            "name": "平稳水流（灌溉渠）",
            "base_velocity": 2.5,
            "fluctuation": 0.03,
            "min_velocity": 2.2,
            "max_velocity": 2.8,
            "ramp_seconds": 0,
        },
        "ripple": {
            "name": "微波动水流（溪流）",
            "base_velocity": 3.0,
            "fluctuation": 0.08,
            "min_velocity": 2.6,
            "max_velocity": 3.4,
            "ramp_seconds": 0,
        },
        "turbulent": {
            "name": "湍急水流（雨季河道）",
            "base_velocity": 4.2,
            "fluctuation": 0.2,
            "min_velocity": 3.5,
            "max_velocity": 5.0,
            "ramp_seconds": 0,
        },
        "low_flow": {
            "name": "枯水期（旱季）",
            "base_velocity": 1.2,
            "fluctuation": 0.05,
            "min_velocity": 0.8,
            "max_velocity": 1.6,
            "ramp_seconds": 0,
        },
        "cycle_day": {
            "name": "昼夜周期模式",
            "base_velocity": 2.5,
            "fluctuation": 0.05,
            "min_velocity": 1.0,
            "max_velocity": 4.0,
            "ramp_seconds": 300,  # 5 分钟一个完整周期
        },
        "random_surge": {
            "name": "随机洪峰模式",
            "base_velocity": 2.5,
            "fluctuation": 0.15,
            "min_velocity": 1.0,
            "max_velocity": 5.0,
            "surge_probability": 0.002,
            "surge_duration": 30,
        },
    }

    @classmethod
    def apply_mode(cls, mode_key: str):
        """根据预设模式键应用水流参数"""
        preset = cls.MODE_PRESETS.get(mode_key)
        if preset is None:
            raise ValueError(f"未知水流模式: {mode_key}, 可用: {list(cls.MODE_PRESETS.keys())}")
        cls.MODE = mode_key
        cls.VELOCITY = preset["base_velocity"]
        cls.FLUCTUATION = preset["fluctuation"]
        cls.MIN_VELOCITY = preset["min_velocity"]
        cls.MAX_VELOCITY = preset["max_velocity"]
        return preset


class RegisterMap:
    WATER_WHEEL_RPM = 0x0000
    WATER_FLOW_VELOCITY = 0x0001
    SPINDLE_RPM_START = 0x0010
    SPINDLE_RPM_COUNT = 32
    YARN_TENSION_START = 0x0030
    YARN_TENSION_COUNT = 32
    YARN_TWIST_START = 0x0050
    YARN_TWIST_COUNT = 32
    YARN_BREAK_START = 0x0070
    YARN_BREAK_COUNT = 32
    POWER_CONSUMPTION = 0x0090
    SPINDLE_BREAK_COUNT = 0x0091
    TOTAL_BREAK_COUNT = 0x0092
    RUN_TIME_HOURS = 0x0093
    RUN_TIME_MINUTES = 0x0094
    REGISTER_SCALE = 100
