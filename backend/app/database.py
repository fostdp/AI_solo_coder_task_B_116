import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv

load_dotenv()


class InfluxDBManager:
    def __init__(self, url: Optional[str] = None, token: Optional[str] = None,
                 org: Optional[str] = None, bucket: Optional[str] = None):
        self.url = url or os.getenv("INFLUXDB_URL", "http://localhost:8086")
        self.token = token or os.getenv("INFLUXDB_TOKEN", "my-token")
        self.org = org or os.getenv("INFLUXDB_ORG", "spinning-wheel-org")
        self.bucket = bucket or os.getenv("INFLUXDB_BUCKET", "spinning-wheel-data")
        self._client = None
        self._write_api = None
        self._query_api = None

    def connect(self):
        if self._client is None:
            self._client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
            self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
            self._query_api = self._client.query_api()

    def close(self):
        if self._client:
            self._client.close()
            self._client = None
            self._write_api = None
            self._query_api = None

    def write_point(self, measurement: str, fields: Dict[str, Any],
                    tags: Optional[Dict[str, str]] = None,
                    timestamp: Optional[datetime] = None):
        self.connect()
        point = Point(measurement)
        if tags:
            for key, value in tags.items():
                point.tag(key, value)
        for key, value in fields.items():
            if isinstance(value, bool):
                point.field(key, value)
            elif isinstance(value, int):
                point.field(key, value)
            elif isinstance(value, float):
                point.field(key, value)
            else:
                point.field(key, str(value))
        if timestamp:
            point.time(timestamp, WritePrecision.NS)
        self._write_api.write(bucket=self.bucket, org=self.org, record=point)

    def write_spinning_wheel_data(self, data: Dict[str, Any]):
        self.connect()
        points = []

        water_wheel = data.get("water_wheel", {})
        ww_point = Point("water_wheel")
        ww_point.field("water_speed", water_wheel.get("water_speed", 0.0))
        ww_point.field("blade_angle", water_wheel.get("blade_angle", 0.0))
        ww_point.field("wheel_radius", water_wheel.get("wheel_radius", 0.0))
        ww_point.field("torque", water_wheel.get("torque", 0.0))
        ww_point.field("rotational_speed", water_wheel.get("rotational_speed", 0.0))
        if "timestamp" in data:
            ww_point.time(data["timestamp"], WritePrecision.NS)
        points.append(ww_point)

        transmission = data.get("transmission", {})
        trans_point = Point("transmission")
        trans_point.field("gear_ratio", transmission.get("gear_ratio", 0.0))
        trans_point.field("mechanical_efficiency", transmission.get("mechanical_efficiency", 0.0))
        trans_point.field("input_torque", transmission.get("input_torque", 0.0))
        trans_point.field("output_torque", transmission.get("output_torque", 0.0))
        trans_point.field("input_speed", transmission.get("input_speed", 0.0))
        trans_point.field("output_speed", transmission.get("output_speed", 0.0))
        if "timestamp" in data:
            trans_point.time(data["timestamp"], WritePrecision.NS)
        points.append(trans_point)

        spindles = data.get("spindles", [])
        for spindle in spindles:
            sp_point = Point("spindle")
            sp_point.tag("spindle_id", str(spindle.get("spindle_id", 0)))
            sp_point.field("speed", spindle.get("speed", 0.0))
            sp_point.field("tension", spindle.get("tension", 0.0))
            sp_point.field("twist", spindle.get("twist", 0.0))
            sp_point.field("broken", spindle.get("broken", False))
            if "timestamp" in data:
                sp_point.time(data["timestamp"], WritePrecision.NS)
            points.append(sp_point)

        system_point = Point("system")
        system_point.field("total_production_rate", data.get("total_production_rate", 0.0))
        system_point.field("energy_efficiency", data.get("energy_efficiency", 0.0))
        system_point.field("twist_uniformity_cv", data.get("twist_uniformity_cv", 0.0))
        system_point.field("breakage_rate", data.get("breakage_rate", 0.0))
        system_point.field("num_spindles", len(spindles))
        if "timestamp" in data:
            system_point.time(data["timestamp"], WritePrecision.NS)
        points.append(system_point)

        self._write_api.write(bucket=self.bucket, org=self.org, record=points)

    def query_data(self, flux_query: str) -> List[Dict[str, Any]]:
        self.connect()
        result = self._query_api.query(flux_query)
        data = []
        for table in result:
            for record in table.records:
                data.append({
                    "time": record.get_time().isoformat() if record.get_time() else None,
                    "measurement": record.get_measurement(),
                    "field": record.get_field(),
                    "value": record.get_value(),
                    "tags": record.values.get("tags", {})
                })
        return data

    def query_latest_data(self, measurement: str, limit: int = 1) -> List[Dict[str, Any]]:
        self.connect()
        flux_query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -1h)
          |> filter(fn: (r) => r._measurement == "{measurement}")
          |> last()
          |> limit(n: {limit})
        '''
        return self.query_data(flux_query)

    def query_timerange(self, measurement: str, start_time: datetime,
                        end_time: Optional[datetime] = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        self.connect()
        start_str = start_time.isoformat()
        end_str = end_time.isoformat() if end_time else datetime.now().isoformat()
        flux_query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: {start_str}, stop: {end_str})
          |> filter(fn: (r) => r._measurement == "{measurement}")
          |> limit(n: {limit})
        '''
        return self.query_data(flux_query)

    def get_latest_spindle_data(self, num_spindles: int = 32) -> List[Dict[str, Any]]:
        self.connect()
        flux_query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -5m)
          |> filter(fn: (r) => r._measurement == "spindle")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> last()
        '''
        result = self._query_api.query(flux_query)
        spindles = []
        for table in result:
            for record in table.records:
                spindles.append({
                    "spindle_id": int(record.values.get("spindle_id", 0)),
                    "speed": record.values.get("speed", 0.0),
                    "tension": record.values.get("tension", 0.0),
                    "twist": record.values.get("twist", 0.0),
                    "broken": record.values.get("broken", False),
                    "time": record.get_time().isoformat() if record.get_time() else None
                })
        return sorted(spindles, key=lambda x: x["spindle_id"])

    def write_alarm(self, alarm: Dict[str, Any]):
        self.connect()
        point = Point("alarm")
        point.tag("alarm_type", alarm.get("alarm_type", "unknown"))
        point.tag("severity", alarm.get("severity", "info"))
        if alarm.get("spindle_id") is not None:
            point.tag("spindle_id", str(alarm["spindle_id"]))
        point.field("message", str(alarm.get("message", "")))
        if alarm.get("value") is not None:
            point.field("value", float(alarm["value"]))
        if alarm.get("threshold") is not None:
            point.field("threshold", float(alarm["threshold"]))
        if "timestamp" in alarm:
            point.time(alarm["timestamp"], WritePrecision.NS)
        self._write_api.write(bucket=self.bucket, org=self.org, record=point)

    def query_alarms(self, start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None,
                     alarm_type: Optional[str] = None,
                     severity: Optional[str] = None,
                     limit: int = 100) -> List[Dict[str, Any]]:
        self.connect()
        start = start_time.isoformat() if start_time else "-24h"
        end = end_time.isoformat() if end_time else "now()"

        filters = [f'r._measurement == "alarm"']
        if alarm_type:
            filters.append(f'r.alarm_type == "{alarm_type}"')
        if severity:
            filters.append(f'r.severity == "{severity}"')

        filter_str = " and ".join(filters)

        flux_query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: {start}, stop: {end})
          |> filter(fn: (r) => {filter_str})
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: {limit})
        '''
        result = self._query_api.query(flux_query)
        alarms = []
        for table in result:
            for record in table.records:
                alarms.append({
                    "timestamp": record.get_time().isoformat() if record.get_time() else None,
                    "alarm_type": record.values.get("alarm_type", ""),
                    "severity": record.values.get("severity", ""),
                    "message": record.values.get("message", ""),
                    "spindle_id": int(record.values.get("spindle_id")) if record.values.get("spindle_id") else None,
                    "value": record.values.get("value"),
                    "threshold": record.values.get("threshold")
                })
        return alarms


db_manager = InfluxDBManager()
