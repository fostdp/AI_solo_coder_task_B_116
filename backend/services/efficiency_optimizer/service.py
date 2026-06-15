"""能效优化服务（遗传算法多目标优化）

职责:
  - 订阅 spinning:opt:request
  - 运行 GeneticAlgorithmOptimizer
  - 发布 spinning:opt:result 带 correlation_id 供 API 网关匹配
"""

import os
import sys
import time
import signal

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from app.optimization import optimizer
from shared.bus import MessageBus
from shared.config_loader import get_config


class EfficiencyOptimizerService:
    def __init__(self):
        self.bus = MessageBus.instance()
        self.running = False

    def _validate(self, params: dict) -> dict:
        p = dict(params)
        cfg = get_config("optimization", default={}) or {}
        p.setdefault("population_size", int(cfg.get("default_population", 30)))
        p.setdefault("generations", int(cfg.get("default_generations", 50)))
        p.setdefault("belt_friction_coeff", 0.35)
        p.setdefault("wrap_angle_deg", 180.0)
        p.setdefault("initial_belt_tension", 200.0)
        weights_default = cfg.get("default_weights", {}) or {}
        p.setdefault("weight_energy_efficiency", weights_default.get("energy_efficiency", 0.7))
        p.setdefault("weight_production", weights_default.get("production", 0.3))
        p.setdefault("weight_twist_uniformity", weights_default.get("twist_uniformity", 0.0))
        p.setdefault("weight_low_breakage", weights_default.get("low_breakage", 0.0))
        return p

    def on_optimize_request(self, envelope: dict):
        payload = envelope.get("payload") or {}
        corr_id = envelope.get("id")
        started = time.time()
        try:
            params = self._validate(payload)
            result = optimizer.optimize(
                water_speed=params["water_speed"],
                wheel_radius=params.get("wheel_radius", 1.5),
                gear_ratio=params.get("gear_ratio", 8.0),
                mechanical_efficiency=params.get("mechanical_efficiency", 0.85),
                friction_coefficient=params.get("friction_coefficient", 0.05),
                min_tension=params.get("min_tension", 5.0),
                max_tension=params.get("max_tension", 15.0),
                max_twist_cv=params.get("max_twist_cv", 5.0),
                population_size=params["population_size"],
                generations=params["generations"],
                belt_friction_coeff=params["belt_friction_coeff"],
                wrap_angle_deg=params["wrap_angle_deg"],
                initial_belt_tension=params["initial_belt_tension"],
                weight_energy_efficiency=params["weight_energy_efficiency"],
                weight_production=params["weight_production"],
                weight_twist_uniformity=params["weight_twist_uniformity"],
                weight_low_breakage=params["weight_low_breakage"],
            )
            result["request_id"] = corr_id
            result["elapsed_sec"] = round(time.time() - started, 3)
            self.bus.publish("optimization_result", result, correlation_id=corr_id)
            print(f"[EfficiencyOpt] 优化完成 spindles={result['optimal_num_spindles']} "
                  f"angle={result['optimal_blade_angle']} elapsed={result['elapsed_sec']}s")
        except Exception as e:
            print(f"[EfficiencyOpt] 优化失败: {e}")
            err = {"error": str(e), "request_id": corr_id}
            self.bus.publish("optimization_result", err, correlation_id=corr_id)

    def start(self):
        self.running = True
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._shutdown)
        self.bus.subscribe("optimization_request", self.on_optimize_request)
        print(f"[EfficiencyOpt] 启动，等待优化请求... Redis={self.bus.ping()}")
        while self.running:
            time.sleep(1.0)
        print("[EfficiencyOpt] 已退出")

    def _shutdown(self, signum, frame):
        print(f"[EfficiencyOpt] 收到信号 {signum}，开始退出")
        self.running = False
        try:
            self.bus.close()
        except Exception:
            pass


def main():
    svc = EfficiencyOptimizerService()
    svc.start()


if __name__ == "__main__":
    main()
