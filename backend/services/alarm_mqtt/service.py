"""告警 & MQTT 推送服务

职责:
  - 订阅 spinning:sim:result
  - 检测断头率/锭速异常（阈值来自 config.yaml）
  - 通过 Paho MQTT 推送告警到 broker
  - 发布 spinning:alarm:event 供 API 网关/WebSocket 广播
"""

import os
import sys
import time
import json
import signal
from datetime import datetime
from typing import List, Dict, Any, Optional

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

import paho.mqtt.client as mqtt
from shared.bus import MessageBus
from shared.config_loader import get_config


class AlarmMQTTService:
    def __init__(self):
        self.bus = MessageBus.instance()
        self.running = False

        alarm_cfg = get_config("alarm", default={}) or {}
        self.max_breakage_rate = float(alarm_cfg.get("max_breakage_rate", 5.0))
        self.speed_dev_low = float(alarm_cfg.get("speed_deviation_low", 0.8))
        self.speed_dev_high = float(alarm_cfg.get("speed_deviation_high", 1.2))

        mqtt_cfg = alarm_cfg.get("mqtt", {}) or {}
        self.mqtt_broker = mqtt_cfg.get("broker", "localhost")
        self.mqtt_port = int(mqtt_cfg.get("port", 1883))
        self.mqtt_topic = mqtt_cfg.get("topic", "spinning/alerts")
        self.mqtt_client_id = mqtt_cfg.get("client_id", "alarm_service")
        self.mqtt_keepalive = int(mqtt_cfg.get("keepalive", 60))

        self._mqtt_client: Optional[mqtt.Client] = None
        self._mqtt_connected = False
        self._active_alarms: List[Dict[str, Any]] = []

    # ---------- MQTT ----------
    def connect_mqtt(self) -> bool:
        try:
            if self._mqtt_client is None:
                self._mqtt_client = mqtt.Client(client_id=self.mqtt_client_id)
                self._mqtt_client.on_connect = self._on_connect
                self._mqtt_client.on_disconnect = self._on_disconnect
            self._mqtt_client.connect(self.mqtt_broker, self.mqtt_port, keepalive=self.mqtt_keepalive)
            self._mqtt_client.loop_start()
            time.sleep(0.5)
            return self._mqtt_connected
        except Exception as e:
            print(f"[AlarmMQTT] MQTT连接失败: {e}")
            self._mqtt_connected = False
            return False

    def disconnect_mqtt(self):
        if self._mqtt_client:
            try:
                self._mqtt_client.loop_stop()
                self._mqtt_client.disconnect()
            except Exception:
                pass
        self._mqtt_connected = False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._mqtt_connected = True
            print("[AlarmMQTT] MQTT broker 已连接")
        else:
            print(f"[AlarmMQTT] MQTT 连接失败 code={rc}")
            self._mqtt_connected = False

    def _on_disconnect(self, client, userdata, rc):
        self._mqtt_connected = False
        print(f"[AlarmMQTT] MQTT broker 断开 (rc={rc})")

    def _publish_mqtt(self, alarm: Dict[str, Any]) -> bool:
        if not self._mqtt_connected and not self.connect_mqtt():
            return False
        try:
            payload = json.dumps(alarm, default=str, ensure_ascii=False)
            info = self._mqtt_client.publish(self.mqtt_topic, payload, qos=1)
            info.wait_for_publish(timeout=2.0)
            return info.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"[AlarmMQTT] MQTT 发布失败: {e}")
            return False

    # ---------- 告警检测 ----------
    def _check_breakage(self, spindles) -> Optional[Dict[str, Any]]:
        total = len(spindles)
        if total == 0:
            return None
        broken = sum(1 for s in spindles if s.get("broken"))
        rate = broken / total * 100
        if rate >= self.max_breakage_rate:
            return {
                "timestamp": datetime.now().isoformat(),
                "alarm_type": "high_breakage_rate",
                "severity": "critical",
                "message": f"纱线断头率过高: {rate:.2f}% (阈值 {self.max_breakage_rate}%)",
                "spindle_id": None,
                "value": rate,
                "threshold": self.max_breakage_rate,
            }
        return None

    def _check_speed_anomaly(self, spindles) -> List[Dict[str, Any]]:
        alarms: List[Dict[str, Any]] = []
        active = [s for s in spindles if not s.get("broken")]
        if not active:
            return alarms
        avg = sum(s.get("speed", 0) for s in active) / len(active)
        if avg <= 0:
            return alarms
        upper = avg * self.speed_dev_high
        lower = avg * self.speed_dev_low
        for s in active:
            sp = s.get("speed", 0)
            if sp > upper or sp < lower:
                dev = (sp - avg) / avg * 100
                alarms.append({
                    "timestamp": datetime.now().isoformat(),
                    "alarm_type": "spindle_speed_anomaly",
                    "severity": "warning" if abs(dev) < 30 else "critical",
                    "message": (f"锭子 {s.get('spindle_id')} 转速异常: {sp:.2f} rpm "
                                f"(均值 {avg:.2f}, 偏差 {dev:+.2f}%)"),
                    "spindle_id": s.get("spindle_id"),
                    "value": sp,
                    "threshold": avg,
                })
        return alarms

    def detect_all(self, sim_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        spindles = sim_result.get("spindles") or []
        alarms: List[Dict[str, Any]] = []
        b = self._check_breakage(spindles)
        if b:
            alarms.append(b)
        alarms.extend(self._check_speed_anomaly(spindles))
        return alarms

    # ---------- 事件处理 ----------
    def on_simulation_result(self, envelope: dict):
        payload = envelope.get("payload") or {}
        if not isinstance(payload, dict) or not payload.get("spindles"):
            return
        try:
            alarms = self.detect_all(payload)
        except Exception as e:
            print(f"[AlarmMQTT] 告警检测异常: {e}")
            return
        if not alarms:
            return
        for a in alarms:
            self._active_alarms.append(a)
            if len(self._active_alarms) > 500:
                self._active_alarms = self._active_alarms[-500:]
            mqtt_ok = self._publish_mqtt(a)
            a["mqtt_published"] = mqtt_ok
            try:
                self.bus.publish("alarm_event", a)
            except Exception as e:
                print(f"[AlarmMQTT] Redis告警发布失败: {e}")
        print(f"[AlarmMQTT] 检测到 {len(alarms)} 条告警")

    # ---------- 启动 ----------
    def start(self):
        self.running = True
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._shutdown)

        self.connect_mqtt()
        self.bus.subscribe("simulation_result", self.on_simulation_result)

        print(f"[AlarmMQTT] 启动，等待仿真结果... Redis={self.bus.ping()} MQTT={self._mqtt_connected}")

        while self.running:
            time.sleep(1.0)
        print("[AlarmMQTT] 已退出")

    def _shutdown(self, signum, frame):
        print(f"[AlarmMQTT] 收到信号 {signum}，开始退出")
        self.running = False
        try:
            self.disconnect_mqtt()
            self.bus.close()
        except Exception:
            pass


def main():
    svc = AlarmMQTTService()
    svc.start()


if __name__ == "__main__":
    main()
