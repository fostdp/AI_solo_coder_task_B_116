"""动力学仿真服务

职责:
  1. 订阅 spinning:raw:collected (来自modbus_receiver)
       - 若数据 status=online 就原样转 simulation_result
       - 若 offline/empty/error 就用默认参数运行 SpinningWheelSimulator 兜底仿真
  2. 订阅 spinning:sim:request (来自 API 网关的 /api/dynamics)
       - 用请求体参数跑仿真，发布 simulation_result + correlation_id
"""

import os
import sys
import math
import time
import signal

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from app.dynamics import simulator
from shared.bus import MessageBus
from shared.config_loader import get_config


class DynamicsSimulatorService:
    def __init__(self):
        self.bus = MessageBus.instance()
        self.running = False

        ww = get_config("water_wheel", default={}) or {}
        tr = get_config("transmission", default={}) or {}
        self.defaults = {
            "water_speed": float(ww.get("default_water_speed", 2.5)),
            "blade_angle": float(ww.get("default_blade_angle", 45.0)),
            "wheel_radius": float(ww.get("default_radius", 1.5)),
            "gear_ratio": float(tr.get("gear_ratio", 8.0)),
            "mechanical_efficiency": float(tr.get("mechanical_efficiency", 0.85)),
            "num_spindles": int(get_config("modbus", "num_spindles", default=32)),
            "friction_coefficient": 0.05,
            "belt_friction_coeff": float(tr.get("default_belt_friction", 0.35)),
            "wrap_angle": math.radians(float(tr.get("default_wrap_angle_deg", 180.0))),
            "initial_belt_tension": float(tr.get("default_initial_tension", 200.0)),
        }

    # ---------- 兜底仿真 ----------
    def fallback_simulate(self) -> dict:
        return simulator.simulate(**self.defaults)

    # ---------- 外部请求仿真 ----------
    def run_from_request(self, params: dict) -> dict:
        merged = dict(self.defaults)
        merged.update({k: v for k, v in params.items() if v is not None})
        if "wrap_angle_deg" in merged and "wrap_angle" not in params:
            merged["wrap_angle"] = math.radians(float(merged.pop("wrap_angle_deg")))
        return simulator.simulate(**{
            "water_speed": merged["water_speed"],
            "blade_angle": merged["blade_angle"],
            "wheel_radius": merged["wheel_radius"],
            "gear_ratio": merged["gear_ratio"],
            "mechanical_efficiency": merged["mechanical_efficiency"],
            "num_spindles": merged["num_spindles"],
            "friction_coefficient": merged["friction_coefficient"],
            "belt_friction_coeff": merged["belt_friction_coeff"],
            "wrap_angle": merged["wrap_angle"],
            "initial_belt_tension": merged["initial_belt_tension"],
        })

    # ---------- 事件处理器 ----------
    def on_raw_collected(self, envelope: dict):
        raw = envelope.get("payload") or {}
        status = raw.get("status")
        corr_id = envelope.get("id")
        try:
            if status == "online" and raw.get("water_wheel"):
                result = raw
                result["source"] = "modbus"
            else:
                result = self.fallback_simulate()
                result["source"] = "fallback_sim"
                result["status"] = "online"
            self.bus.publish("simulation_result", result, correlation_id=corr_id)
            print(f"[DynamicsSim] 发布仿真结果 source={result['source']} "
                  f"wheel_rpm={result['water_wheel'].get('rotational_speed', 0):.2f}")
        except Exception as e:
            print(f"[DynamicsSim] 处理采集事件失败: {e}")

    def on_sim_request(self, envelope: dict):
        payload = envelope.get("payload") or {}
        corr_id = envelope.get("id")
        try:
            result = self.run_from_request(payload)
            result["source"] = "direct_request"
            self.bus.publish("simulation_result", result, correlation_id=corr_id)
            print(f"[DynamicsSim] 处理direct请求成功 corr_id={corr_id[:8] if corr_id else ''}")
        except Exception as e:
            print(f"[DynamicsSim] 处理direct请求失败: {e}")

    # ---------- 启动 ----------
    def start(self):
        self.running = True
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._shutdown)

        self.bus.subscribe("raw_data_collected", self.on_raw_collected)
        self.bus.subscribe("spinning:sim:request", self.on_sim_request)

        print(f"[DynamicsSim] 启动，等待 Redis 事件... Redis={self.bus.ping()}")

        while self.running:
            time.sleep(1.0)

        print("[DynamicsSim] 已退出")

    def _shutdown(self, signum, frame):
        print(f"[DynamicsSim] 收到信号 {signum}，开始退出")
        self.running = False
        try:
            self.bus.close()
        except Exception:
            pass


def main():
    svc = DynamicsSimulatorService()
    svc.start()


if __name__ == "__main__":
    main()
