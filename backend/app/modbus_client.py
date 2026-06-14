import os
import time
from typing import List, Dict, Any, Optional
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
from dotenv import load_dotenv

load_dotenv()

REGISTER_SCALE = 100.0


class ModbusSensorClient:
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None,
                 timeout: int = 5):
        self.host = host or os.getenv("MODBUS_HOST", "localhost")
        self.port = port or int(os.getenv("MODBUS_PORT", "5020"))
        self.timeout = timeout
        self._client = None
        self._connected = False

    def connect(self) -> bool:
        try:
            if self._client is None:
                self._client = ModbusTcpClient(self.host, port=self.port, timeout=self.timeout)
            self._connected = self._client.connect()
            return self._connected
        except ModbusException as e:
            print(f"Modbus connection error: {e}")
            self._connected = False
            return False

    def disconnect(self):
        if self._client:
            self._client.close()
            self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def read_holding_register(self, address: int, count: int = 1,
                              slave_id: int = 1) -> Optional[List[int]]:
        if not self._connected:
            if not self.connect():
                return None
        try:
            result = self._client.read_holding_registers(address, count, slave=slave_id)
            if result.isError():
                print(f"Modbus read error at address {address}: {result}")
                return None
            return result.registers
        except ModbusException as e:
            print(f"Modbus exception: {e}")
            self._connected = False
            return None

    def read_scaled_float(self, address: int, slave_id: int = 1,
                          scale: float = REGISTER_SCALE) -> Optional[float]:
        registers = self.read_holding_register(address, 1, slave_id)
        if registers and len(registers) >= 1:
            return registers[0] / scale
        return None


class SpinningWheelModbusClient(ModbusSensorClient):
    WATER_WHEEL_RPM_ADDR = 0x0000
    WATER_FLOW_VELOCITY_ADDR = 0x0001

    SPINDLE_RPM_START = 0x0010
    SPINDLE_COUNT = 32

    YARN_TENSION_START = 0x0030
    YARN_TWIST_START = 0x0050
    YARN_BREAK_START = 0x0070

    POWER_CONSUMPTION_ADDR = 0x0090
    SPINDLE_BREAK_COUNT_ADDR = 0x0091
    TOTAL_BREAK_COUNT_ADDR = 0x0092
    RUN_TIME_HOURS_ADDR = 0x0093
    RUN_TIME_MINUTES_ADDR = 0x0094

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None,
                 num_spindles: int = 32, timeout: int = 5):
        super().__init__(host, port, timeout)
        self.num_spindles = num_spindles

    def read_water_wheel_data(self) -> Dict[str, Any]:
        data = {
            "water_speed": 0.0,
            "blade_angle": 45.0,
            "wheel_radius": 1.5,
            "torque": 0.0,
            "rotational_speed": 0.0
        }

        rpm = self.read_scaled_float(self.WATER_WHEEL_RPM_ADDR)
        if rpm is not None:
            data["rotational_speed"] = rpm

        water_speed = self.read_scaled_float(self.WATER_FLOW_VELOCITY_ADDR)
        if water_speed is not None:
            data["water_speed"] = water_speed

        if data["rotational_speed"] > 0 and data["water_speed"] > 0:
            data["torque"] = data["water_speed"] * data["rotational_speed"] * 80

        return data

    def read_transmission_data(self) -> Dict[str, Any]:
        data = {
            "gear_ratio": 12.0,
            "mechanical_efficiency": 0.92,
            "input_torque": 0.0,
            "output_torque": 0.0,
            "input_speed": 0.0,
            "output_speed": 0.0
        }

        wheel_rpm = self.read_scaled_float(self.WATER_WHEEL_RPM_ADDR)
        if wheel_rpm is not None:
            data["input_speed"] = wheel_rpm
            data["output_speed"] = wheel_rpm * data["gear_ratio"] * data["mechanical_efficiency"]

        return data

    def read_spindle_data(self, spindle_id: int) -> Optional[Dict[str, Any]]:
        if spindle_id < 0 or spindle_id >= self.num_spindles:
            return None

        rpm = self.read_scaled_float(self.SPINDLE_RPM_START + spindle_id)
        tension = self.read_scaled_float(self.YARN_TENSION_START + spindle_id)
        twist = self.read_scaled_float(self.YARN_TWIST_START + spindle_id)

        broken_reg = self.read_holding_register(self.YARN_BREAK_START + spindle_id, 1)
        broken = bool(broken_reg[0]) if broken_reg else False

        if rpm is None or tension is None or twist is None:
            return None

        return {
            "spindle_id": spindle_id,
            "speed": rpm,
            "tension": tension / 100.0,
            "twist": twist,
            "broken": broken
        }

    def read_all_spindles(self) -> List[Dict[str, Any]]:
        spindles = []

        rpm_regs = self.read_holding_register(self.SPINDLE_RPM_START, self.num_spindles)
        tension_regs = self.read_holding_register(self.YARN_TENSION_START, self.num_spindles)
        twist_regs = self.read_holding_register(self.YARN_TWIST_START, self.num_spindles)
        break_regs = self.read_holding_register(self.YARN_BREAK_START, self.num_spindles)

        for i in range(self.num_spindles):
            rpm = rpm_regs[i] / REGISTER_SCALE if rpm_regs else 0.0
            tension = tension_regs[i] / REGISTER_SCALE / 100.0 if tension_regs else 0.0
            twist = twist_regs[i] / REGISTER_SCALE if twist_regs else 0.0
            broken = bool(break_regs[i]) if break_regs else False

            spindles.append({
                "spindle_id": i,
                "speed": rpm,
                "tension": tension,
                "twist": twist,
                "broken": broken
            })

        return spindles

    def read_system_data(self) -> Dict[str, Any]:
        data = {
            "power_consumption": 0.0,
            "break_count": 0,
            "total_break_count": 0,
            "run_time_hours": 0,
            "run_time_minutes": 0
        }

        power = self.read_scaled_float(self.POWER_CONSUMPTION_ADDR)
        if power is not None:
            data["power_consumption"] = power

        break_count = self.read_holding_register(self.SPINDLE_BREAK_COUNT_ADDR, 1)
        if break_count:
            data["break_count"] = break_count[0]

        total_break = self.read_holding_register(self.TOTAL_BREAK_COUNT_ADDR, 1)
        if total_break:
            data["total_break_count"] = total_break[0]

        hours = self.read_holding_register(self.RUN_TIME_HOURS_ADDR, 1)
        if hours:
            data["run_time_hours"] = hours[0]

        minutes = self.read_holding_register(self.RUN_TIME_MINUTES_ADDR, 1)
        if minutes:
            data["run_time_minutes"] = minutes[0]

        return data

    def read_all_data(self) -> Dict[str, Any]:
        try:
            if not self._connected and not self.connect():
                return {}

            water_wheel = self.read_water_wheel_data()
            transmission = self.read_transmission_data()
            spindles = self.read_all_spindles()
            system = self.read_system_data()

            active_spindles = [s for s in spindles if not s["broken"]]
            avg_speed = sum(s["speed"] for s in active_spindles) / len(active_spindles) if active_spindles else 0
            avg_tension = sum(s["tension"] for s in active_spindles) if active_spindles else 0

            total_production = sum(s["speed"] * 0.01 for s in active_spindles)
            power_kw = system.get("power_consumption", 0) / 1000.0
            energy_efficiency = total_production / power_kw if power_kw > 0 else 0

            twists = [s["twist"] for s in active_spindles]
            twist_mean = sum(twists) / len(twists) if twists else 0
            twist_var = sum((t - twist_mean) ** 2 for t in twists) / len(twists) if twists else 0
            twist_cv = (twist_var ** 0.5 / twist_mean * 100) if twist_mean > 0 else 0

            breakage_rate = (system.get("break_count", 0) / len(spindles)) * 100 if spindles else 0

            return {
                "water_wheel": water_wheel,
                "transmission": transmission,
                "spindles": spindles,
                "total_production_rate": total_production,
                "energy_efficiency": energy_efficiency,
                "twist_uniformity_cv": twist_cv,
                "breakage_rate": breakage_rate,
                "twist_variance": twist_var,
                "speed_standard_deviation": 0.0,
                "system": system,
                "timestamp": time.time()
            }
        except Exception as e:
            print(f"Error reading all modbus data: {e}")
            return {}


modbus_client = SpinningWheelModbusClient()
