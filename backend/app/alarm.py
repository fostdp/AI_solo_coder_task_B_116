import os
import json
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()


class AlarmManager:
    BREAKAGE_RATE_THRESHOLD = 5.0
    SPEED_DEVIATION_THRESHOLD = 0.2

    def __init__(self):
        self.mqtt_broker = os.getenv("MQTT_BROKER", "localhost")
        self.mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        self.mqtt_topic = os.getenv("MQTT_TOPIC_ALARM", "spinning-wheel/alarm")
        self._mqtt_client = None
        self._connected = False
        self._alarm_callbacks: List[Callable] = []
        self._active_alarms: List[Dict[str, Any]] = []

    def connect_mqtt(self) -> bool:
        try:
            if self._mqtt_client is None:
                self._mqtt_client = mqtt.Client(client_id="spinning-wheel-alarm")
                self._mqtt_client.on_connect = self._on_connect
                self._mqtt_client.on_disconnect = self._on_disconnect

            self._mqtt_client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
            self._mqtt_client.loop_start()
            return True
        except Exception as e:
            print(f"MQTT connection error: {e}")
            self._connected = False
            return False

    def disconnect_mqtt(self):
        if self._mqtt_client:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()
            self._connected = False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            print("MQTT connected successfully")
        else:
            print(f"MQTT connection failed with code {rc}")
            self._connected = False

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        print("MQTT disconnected")

    def is_mqtt_connected(self) -> bool:
        return self._connected

    def publish_alarm(self, alarm: Dict[str, Any]) -> bool:
        if not self._connected:
            if not self.connect_mqtt():
                print("Cannot publish alarm: MQTT not connected")
                return False

        try:
            payload = json.dumps(alarm, default=str, ensure_ascii=False)
            result = self._mqtt_client.publish(self.mqtt_topic, payload, qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self._active_alarms.append(alarm)
                if len(self._active_alarms) > 1000:
                    self._active_alarms = self._active_alarms[-500:]
                self._trigger_callbacks(alarm)
                return True
            return False
        except Exception as e:
            print(f"Error publishing alarm: {e}")
            return False

    def register_callback(self, callback: Callable):
        self._alarm_callbacks.append(callback)

    def _trigger_callbacks(self, alarm: Dict[str, Any]):
        for callback in self._alarm_callbacks:
            try:
                callback(alarm)
            except Exception as e:
                print(f"Error in alarm callback: {e}")

    def check_breakage_rate(self, spindles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not spindles:
            return None

        total = len(spindles)
        broken = sum(1 for s in spindles if s.get("broken", False))
        breakage_rate = (broken / total) * 100

        if breakage_rate >= self.BREAKAGE_RATE_THRESHOLD:
            alarm = {
                "timestamp": datetime.now(),
                "alarm_type": "high_breakage_rate",
                "severity": "critical",
                "message": f"纱线断头率过高: {breakage_rate:.2f}% (阈值: {self.BREAKAGE_RATE_THRESHOLD}%)",
                "spindle_id": None,
                "value": breakage_rate,
                "threshold": self.BREAKAGE_RATE_THRESHOLD
            }
            return alarm
        return None

    def check_spindle_speed_anomaly(self, spindles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        alarms = []
        if not spindles:
            return alarms

        speeds = [s.get("speed", 0) for s in spindles if not s.get("broken", False)]
        if not speeds:
            return alarms

        avg_speed = sum(speeds) / len(speeds)
        if avg_speed == 0:
            return alarms

        upper_threshold = avg_speed * (1 + self.SPEED_DEVIATION_THRESHOLD)
        lower_threshold = avg_speed * (1 - self.SPEED_DEVIATION_THRESHOLD)

        for spindle in spindles:
            if spindle.get("broken", False):
                continue

            speed = spindle.get("speed", 0)
            spindle_id = spindle.get("spindle_id", 0)

            if speed > upper_threshold or speed < lower_threshold:
                deviation = ((speed - avg_speed) / avg_speed) * 100
                severity = "warning" if abs(deviation) < 30 else "critical"
                alarm = {
                    "timestamp": datetime.now(),
                    "alarm_type": "spindle_speed_anomaly",
                    "severity": severity,
                    "message": f"锭子 {spindle_id} 转速异常: {speed:.2f} rpm (均值: {avg_speed:.2f} rpm, 偏差: {deviation:.2f}%)",
                    "spindle_id": spindle_id,
                    "value": speed,
                    "threshold": avg_speed
                }
                alarms.append(alarm)

        return alarms

    def check_all(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        all_alarms = []
        spindles = data.get("spindles", [])

        breakage_alarm = self.check_breakage_rate(spindles)
        if breakage_alarm:
            all_alarms.append(breakage_alarm)
            self.publish_alarm(breakage_alarm)

        speed_alarms = self.check_spindle_speed_anomaly(spindles)
        for alarm in speed_alarms:
            all_alarms.append(alarm)
            self.publish_alarm(alarm)

        return all_alarms

    def get_active_alarms(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._active_alarms[-limit:]

    def clear_alarms(self):
        self._active_alarms = []


alarm_manager = AlarmManager()
