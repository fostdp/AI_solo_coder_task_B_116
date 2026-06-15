"""Modbus 数据采集服务

职责:
  - 周期性通过 Modbus TCP 读取水轮/锭子/系统原始数据
  - 发布 spinning:raw:collected 事件到 Redis，供下游动力学服务消费
  - 如果 Modbus 连接失败，发布 status=offline 标志
"""

import os
import sys
import time
import signal

# 让 services/ 目录能 import 上层 app/ 和 shared/
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from app.modbus_client import SpinningWheelModbusClient
from shared.bus import MessageBus
from shared.config_loader import get_config


class ModbusReceiverService:
    def __init__(self):
        self.bus = MessageBus.instance()
        self.running = False
        cfg_mb = get_config("modbus", default={}) or {}
        self.interval = float(cfg_mb.get("collection_interval", 5.0))
        self.client = SpinningWheelModbusClient(
            host=cfg_mb.get("host"),
            port=cfg_mb.get("port"),
            num_spindles=int(cfg_mb.get("num_spindles", 32)),
            timeout=int(cfg_mb.get("timeout", 5)),
        )

    def _collect_once(self) -> dict:
        started_at = time.time()
        try:
            if not self.client.connect():
                return {
                    "status": "offline",
                    "error": "modbus_connect_failed",
                    "ts": started_at,
                }
            data = self.client.read_all_data()
            if not data:
                return {
                    "status": "empty",
                    "ts": started_at,
                }
            data["status"] = "online"
            return data
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "ts": started_at,
            }

    def start(self):
        self.running = True
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._shutdown)
        print(f"[ModbusReceiver] 启动，周期 {self.interval}s，Redis={self.bus.ping()}")

        while self.running:
            tick_start = time.time()
            raw = self._collect_once()
            try:
                self.bus.publish("raw_data_collected", raw)
                print(f"[ModbusReceiver] 发布采集完成事件 status={raw.get('status')}")
            except Exception as e:
                print(f"[ModbusReceiver] 发布失败: {e}")
            elapsed = time.time() - tick_start
            sleep_for = max(0.0, self.interval - elapsed)
            if sleep_for:
                time.sleep(sleep_for)

        print("[ModbusReceiver] 已退出")

    def _shutdown(self, signum, frame):
        print(f"[ModbusReceiver] 收到信号 {signum}，开始退出")
        self.running = False
        try:
            self.client.disconnect()
            self.bus.close()
        except Exception:
            pass


def main():
    svc = ModbusReceiverService()
    svc.start()


if __name__ == "__main__":
    main()
