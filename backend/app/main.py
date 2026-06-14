"""
FastAPI API 网关（重构版 v1.2.0）

本模块只负责：
  1. 接收前端 HTTP 与 WebSocket 请求
  2. 通过 Redis Pub/Sub 与 4 个微服务通信
  3. 聚合结果返回前端 / 通过 WS 广播
  4. InfluxDB 历史数据查询

不再直接包含：
  - Modbus 采集   → modbus_receiver 服务
  - 动力学仿真   → dynamics_simulator 服务
  - 遗传算法优化 → efficiency_optimizer 服务
  - 告警/MQTT    → alarm_mqtt 服务
"""

import os
import sys
import json
import asyncio
from typing import List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from app.models import (
    DynamicsRequest, DynamicsResponse, OptimizationRequest,
    OptimizationResult, AlarmData
)
from app.database import db_manager
from shared.bus import MessageBus
from shared.config_loader import get_config, load_config

CFG = load_config()
API_CFG = get_config("api_gateway", default={}) or {}
RESPONSE_TIMEOUT = float(API_CFG.get("response_timeout", 30.0))

bus = MessageBus.instance()


# ============================================================
# WebSocket 连接管理
# ============================================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active_connections:
            self.active_connections.remove(ws)

    async def broadcast(self, message: dict):
        for conn in list(self.active_connections):
            try:
                await conn.send_json(message)
            except Exception:
                pass


ws_manager = ConnectionManager()
latest_data: Optional[dict] = None
latest_alarms: List[dict] = []
_event_loop_ref: Optional[asyncio.AbstractEventLoop] = None


def _async_broadcast(message: dict):
    """从 Redis 订阅回调线程把广播送到 asyncio 循环里。"""
    if _event_loop_ref is None:
        return
    try:
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast(message), _event_loop_ref)
    except Exception:
        pass


# ============================================================
# Redis 事件 → 网关状态同步
# ============================================================
def _on_simulation_result(envelope: dict):
    global latest_data
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        return
    latest_data = payload
    # 写入 InfluxDB（兼容旧逻辑，在网关层完成）
    try:
        db_manager.write_spinning_wheel_data(payload)
    except Exception as e:
        print(f"[APIGateway] InfluxDB 写入失败: {e}")
    _async_broadcast({"type": "data", "data": payload})


def _on_alarm_event(envelope: dict):
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        return
    latest_alarms.append(payload)
    if len(latest_alarms) > 200:
        latest_alarms[:] = latest_alarms[-200:]
    try:
        db_manager.write_alarm(payload)
    except Exception as e:
        print(f"[APIGateway] 告警入库失败: {e}")
    _async_broadcast({"type": "alarm", "data": payload})


# ============================================================
# 启动 / 关闭
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _event_loop_ref
    _event_loop_ref = asyncio.get_running_loop()

    try:
        db_manager.connect()
        print("[APIGateway] InfluxDB connected")
    except Exception as e:
        print(f"[APIGateway] InfluxDB 连接失败(忽略): {e}")

    try:
        bus.subscribe("simulation_result", _on_simulation_result)
        bus.subscribe("alarm_event", _on_alarm_event)
        print(f"[APIGateway] Redis 订阅已就绪 connected={bus.ping()}")
    except Exception as e:
        print(f"[APIGateway] Redis 订阅失败: {e}")

    yield

    try:
        db_manager.close()
    except Exception:
        pass
    try:
        bus.close()
    except Exception:
        pass
    print("[APIGateway] Shutdown complete")


app = FastAPI(
    title="水转大纺车 API 网关",
    description="基于 FastAPI + Redis Pub/Sub 的微服务网关，动力学/优化/告警均委托微服务处理",
    version=CFG.get("version", "1.2.0"),
    lifespan=lifespan,
)

_cors = API_CFG.get("cors_origins", ["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors if isinstance(_cors, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 路由
# ============================================================
@app.get("/")
async def root():
    return {
        "name": "水转大纺车动力学仿真与能效分析系统（微服务架构）",
        "version": CFG.get("version", "1.2.0"),
        "architecture": {
            "api_gateway": "FastAPI + Redis Pub/Sub",
            "services": [
                "modbus_receiver (Modbus TCP 采集)",
                "dynamics_simulator (动力学+欧拉皮带打滑)",
                "efficiency_optimizer (遗传算法多目标优化)",
                "alarm_mqtt (告警检测 + MQTT 推送)",
            ],
            "communication": "Redis Pub/Sub",
            "config_source": "backend/config.yaml",
        },
        "redis_connected": bus.ping(),
        "influxdb_connected": db_manager._client is not None,
        "endpoints": {
            "realtime_data": "/api/data",
            "dynamics_simulation": "/api/dynamics",
            "optimization": "/api/optimize",
            "alarms": "/api/alarms",
            "websocket": "/api/websocket",
            "health": "/api/health",
        },
    }


@app.get("/api/health")
async def health_check():
    """服务健康检查（供 docker-compose 与 Kubernetes 探针使用。"""
    redis_ok = bus.ping()
    influx_ok = False
    try:
        if db_manager._client is not None:
            influx_ok = db_manager._client.ping()
    except Exception:
        influx_ok = False

    return {
        "status": "healthy" if (redis_ok and influx_ok) else "degraded",
        "version": "v1.2.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": {
            "redis": "ok" if redis_ok else "error",
            "influxdb": "ok" if influx_ok else "error",
        },
        "latest_data_available": latest_data is not None,
        "active_websockets": len(ws_manager.active_connections),
    }


@app.get("/api/data")
async def get_realtime_data(
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    measurement: Optional[str] = Query(None),
    limit: int = Query(100),
):
    if not start_time and not end_time and not measurement:
        if latest_data:
            return latest_data
        return {"status": "waiting_for_service", "message": "等待 dynamics_simulator 发布数据..."}
    if not measurement:
        raise HTTPException(status_code=400, detail="请指定 measurement 参数")
    try:
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None
        if start_dt:
            data = db_manager.query_timerange(measurement, start_dt, end_dt, limit)
        else:
            data = db_manager.query_latest_data(measurement, limit)
        return {"measurement": measurement, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@app.post("/api/dynamics", response_model=DynamicsResponse)
async def run_dynamics_simulation(request: DynamicsRequest):
    """委托 dynamics_simulator 服务执行仿真（request/response 模式）。"""
    params = request.model_dump()
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: bus.request(
                "spinning:sim:request",
                "simulation_result",
                params,
                timeout=RESPONSE_TIMEOUT,
            ),
        )
        if result is None:
            raise HTTPException(status_code=504, detail="dynamics_simulator 服务响应超时")
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"动力学仿真失败: {str(e)}")


@app.post("/api/optimize", response_model=OptimizationResult)
async def run_optimization(request: OptimizationRequest):
    """委托 efficiency_optimizer 服务执行遗传算法优化（request/response 模式）。"""
    params = request.model_dump()
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: bus.request(
                "optimization_request",
                "optimization_result",
                params,
                timeout=max(RESPONSE_TIMEOUT, 600.0),
            ),
        )
        if result is None:
            raise HTTPException(status_code=504, detail="efficiency_optimizer 服务响应超时")
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"优化计算失败: {str(e)}")


@app.get("/api/alarms")
async def get_alarms(
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    alarm_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(100),
):
    try:
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None
        db_alarms = db_manager.query_alarms(
            start_time=start_dt, end_time=end_dt,
            alarm_type=alarm_type, severity=severity, limit=limit,
        )
        if db_alarms:
            return {"alarms": db_alarms, "count": len(db_alarms), "source": "influxdb"}
        return {"alarms": latest_alarms[-limit:], "count": len(latest_alarms[-limit:]), "source": "memory"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"告警查询失败: {str(e)}")


@app.websocket("/api/websocket")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        if latest_data:
            await websocket.send_json({"type": "data", "data": latest_data})
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                mt = msg.get("type")
                if mt == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
                elif mt == "get_data":
                    if latest_data:
                        await websocket.send_json({"type": "data", "data": latest_data})
                    else:
                        await websocket.send_json({"type": "data", "data": None, "status": "waiting"})
                elif mt == "get_alarms":
                    await websocket.send_json({"type": "alarms", "data": latest_alarms[-50:]})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ws_manager.disconnect(websocket)


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": CFG.get("version"),
        "database": "connected" if db_manager._client else "disconnected",
        "redis": "connected" if bus.ping() else "disconnected",
        "mqtt": "alarm_mqtt 独立服务运行中 (见 docker-compose)",
        "modbus": "modbus_receiver 独立服务运行中 (见 docker-compose)",
        "websocket_clients": len(ws_manager.active_connections),
        "timestamp": datetime.now().isoformat(),
    }
