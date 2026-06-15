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
    OptimizationResult, AlarmData,
    HistoricalComparisonRequest, FiberOptimizationRequest,
    FiberComparisonRequest, BreakDetectionRequest,
    VirtualSpinningCreateRequest, VirtualSpinningControlRequest
)
from app.database import db_manager
from app.historical import HistoricalSpinningWheels, EfficiencyCalculator
from app.fiber_optimization import FiberDatabase, SpinningParameterOptimizer
from app.yarn_detection import BreakDetectionSystem, VisionDetectionSystem, AutoPiecingRobot
from app.virtual_spinning import PublicExperienceManager
from shared.bus import MessageBus
from shared.config_loader import get_config, load_config

CFG = load_config()
API_CFG = get_config("api_gateway", default={}) or {}
RESPONSE_TIMEOUT = float(API_CFG.get("response_timeout", 30.0))

bus = MessageBus.instance()

_break_detection_system = BreakDetectionSystem(num_spindles=32)
_public_experience_manager = PublicExperienceManager(max_sessions=100)
_virtual_spinning_task = None


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

    global _virtual_spinning_task

    async def _virtual_spinning_ticker():
        while True:
            try:
                _public_experience_manager.tick_all(dt=0.05)
            except Exception as e:
                print(f"[APIGateway] 虚拟纺纱tick异常: {e}")
            await asyncio.sleep(0.05)

    _virtual_spinning_task = asyncio.create_task(_virtual_spinning_ticker())
    print("[APIGateway] 公众虚拟纺纱体验引擎已启动")

    yield

    try:
        db_manager.close()
    except Exception:
        pass
    try:
        bus.close()
    except Exception:
        pass
    try:
        if _virtual_spinning_task and not _virtual_spinning_task.done():
            _virtual_spinning_task.cancel()
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


# ============================================================
# 新增功能一：历史纺车技术对比 API
# ============================================================
@app.get("/api/historical/wheels", tags=["历史纺车对比"])
async def get_historical_wheel_list():
    """获取所有历史纺车规格列表"""
    specs = HistoricalSpinningWheels.get_all_specs()
    result = []
    for key, spec in specs.items():
        result.append({
            "wheel_type": spec.wheel_type,
            "wheel_name": spec.wheel_name,
            "era": spec.era,
            "dynasty": spec.dynasty,
            "year_range": spec.year_range,
            "power_source": spec.power_source,
            "num_spindles": spec.num_spindles,
            "description": spec.description
        })
    return {"wheels": result}


@app.get("/api/historical/wheels/{wheel_type}", tags=["历史纺车对比"])
async def get_historical_wheel_detail(wheel_type: str):
    """获取单个纺车详细规格"""
    spec = HistoricalSpinningWheels.get_spec(wheel_type)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Unknown wheel type: {wheel_type}")
    efficiency = EfficiencyCalculator.calculate_efficiency_metrics(spec)
    quality = EfficiencyCalculator.calculate_quality_metrics(spec)
    return {
        "spec": {
            "wheel_type": spec.wheel_type,
            "wheel_name": spec.wheel_name,
            "era": spec.era,
            "dynasty": spec.dynasty,
            "year_range": spec.year_range,
            "power_source": spec.power_source,
            "num_spindles": spec.num_spindles,
            "wheel_radius_m": spec.wheel_radius_m,
            "transmission_ratio": spec.transmission_ratio,
            "mechanical_efficiency": spec.mechanical_efficiency,
            "max_spindle_rpm": spec.max_spindle_rpm,
            "max_daily_production_kg": spec.max_daily_production_kg,
            "labor_requirement": spec.labor_requirement,
            "material": spec.material,
            "floor_space_m2": spec.floor_space_m2,
            "cost_relative": spec.cost_relative,
            "description": spec.description
        },
        "efficiency": efficiency,
        "quality": quality
    }


@app.post("/api/historical/comparison", tags=["历史纺车对比"])
async def compare_historical_wheels(req: HistoricalComparisonRequest):
    """对比多种纺车的效率与质量"""
    result = EfficiencyCalculator.calculate_comparison(
        wheel_types=req.wheel_types,
        operating_hours=req.operating_hours,
        utilization_rate=req.utilization_rate
    )
    return result


# ============================================================
# 新增功能二：棉麻丝纤维纺纱参数优化 API
# ============================================================
@app.get("/api/fibers", tags=["纤维参数优化"])
async def get_fiber_list():
    """获取所有可用纤维特性列表"""
    fibers = FiberDatabase.get_all_fibers()
    result = []
    for key, f in fibers.items():
        result.append({
            "fiber_type": f.fiber_type,
            "fiber_name": f.fiber_name,
            "origin": f.origin,
            "color": f.color,
            "fineness_dtex": f.fineness_dtex,
            "fiber_length_mm_avg": f.fiber_length_mm_avg,
            "breaking_tenacity_cn_dtex": f.breaking_tenacity_cn_dtex,
            "moisture_regain_percent": f.moisture_regain_percent,
            "typical_count_tex_range": list(f.typical_count_tex_range),
            "description": f.description
        })
    return {"fibers": result}


@app.get("/api/fibers/{fiber_type}", tags=["纤维参数优化"])
async def get_fiber_detail(fiber_type: str):
    """获取单种纤维详细特性"""
    fiber = FiberDatabase.get_fiber(fiber_type)
    if not fiber:
        raise HTTPException(status_code=404, detail=f"Unknown fiber type: {fiber_type}")
    return {
        "fiber_type": fiber.fiber_type,
        "fiber_name": fiber.fiber_name,
        "scientific_name": fiber.scientific_name,
        "origin": fiber.origin,
        "color": fiber.color,
        "fiber_length_mm": {
            "avg": fiber.fiber_length_mm_avg,
            "min": fiber.fiber_length_mm_min,
            "max": fiber.fiber_length_mm_max
        },
        "fiber_diameter_um": fiber.fiber_diameter_um,
        "fineness_dtex": fiber.fineness_dtex,
        "density_g_cm3": fiber.density_g_cm3,
        "breaking_tenacity_cn_dtex": fiber.breaking_tenacity_cn_dtex,
        "elongation_at_break_percent": fiber.elongation_at_break_percent,
        "moisture_regain_percent": fiber.moisture_regain_percent,
        "modulus_gpa": fiber.modulus_gpa,
        "friction_coefficient": fiber.friction_coefficient,
        "crimp_percent": fiber.crimp_percent,
        "typical_count_tex_range": list(fiber.typical_count_tex_range),
        "recommended_twist_factor_range": list(fiber.recommended_twist_factor_range),
        "recommended_draft_range": list(fiber.recommended_draft_range),
        "max_spindle_speed_rpm": fiber.max_spindle_speed_rpm,
        "description": fiber.description
    }


@app.post("/api/fibers/optimize", tags=["纤维参数优化"])
async def optimize_spinning_parameters(req: FiberOptimizationRequest):
    """基于纤维特性的纺纱参数优化"""
    fiber = FiberDatabase.get_fiber(req.fiber_type)
    if not fiber:
        raise HTTPException(status_code=404, detail=f"Unknown fiber type: {req.fiber_type}")
    result = SpinningParameterOptimizer.full_spinning_optimization(
        fiber_type=req.fiber_type,
        yarn_count_tex=req.yarn_count_tex,
        roving_count_tex=req.roving_count_tex,
        quality_priority=req.quality_priority
    )
    return result


@app.post("/api/fibers/compare", tags=["纤维参数优化"])
async def compare_fiber_parameters(req: FiberComparisonRequest):
    """对比多种纤维的纺纱参数"""
    result = SpinningParameterOptimizer.compare_fibers(
        fiber_types=req.fiber_types,
        yarn_count_tex=req.yarn_count_tex,
        quality_priority=req.quality_priority
    )
    return result


# ============================================================
# 新增功能三：自动生头与断头检测模拟 API
# ============================================================
@app.post("/api/detection/simulate-break", tags=["断头检测与自动生头"])
async def simulate_yarn_break(req: BreakDetectionRequest):
    """模拟纱线断头-检测-自动生头完整流程"""
    result = _break_detection_system.simulate_break_scenario(
        spindle_id=req.spindle_id,
        speed_rpm=req.speed_rpm,
        tension_cn=req.tension_cn,
        fiber_type=req.fiber_type
    )
    return result


@app.get("/api/detection/vision-status", tags=["断头检测与自动生头"])
async def get_vision_detection_status():
    """获取机器视觉检测系统状态"""
    return _break_detection_system.vision_system.get_system_status()


@app.get("/api/detection/robot-status", tags=["断头检测与自动生头"])
async def get_piecing_robot_status():
    """获取自动生头机械手状态"""
    return _break_detection_system.piecing_robot.get_performance()


@app.get("/api/detection/statistics", tags=["断头检测与自动生头"])
async def get_detection_statistics(window_seconds: float = None):
    """获取断头检测系统统计数据"""
    return _break_detection_system.get_statistics(window_seconds=window_seconds)


@app.get("/api/detection/spindle-status", tags=["断头检测与自动生头"])
async def get_all_spindle_status():
    """获取所有锭子运行状态"""
    return {"spindles": _break_detection_system.get_spindle_status()}


# ============================================================
# 新增功能四：公众体验虚拟纺纱 API
# ============================================================
@app.post("/api/virtual-spinning/create", tags=["公众虚拟纺纱体验"])
async def create_virtual_spinning_session(req: VirtualSpinningCreateRequest):
    """创建虚拟纺纱会话"""
    session_id = _public_experience_manager.create_session()
    engine = _public_experience_manager.get_session(session_id)
    if engine and req.water_speed:
        engine.set_parameters(water_speed=req.water_speed, fiber_type=req.fiber_type)
    return {
        "session_id": session_id,
        "snapshot": engine.get_snapshot() if engine else None
    }


@app.post("/api/virtual-spinning/control", tags=["公众虚拟纺纱体验"])
async def control_virtual_spinning(req: VirtualSpinningControlRequest):
    """控制虚拟纺纱会话（启动/暂停/重置/调节参数）"""
    engine = _public_experience_manager.get_session(req.session_id)
    if not engine:
        raise HTTPException(status_code=404, detail=f"Session not found: {req.session_id}")

    if req.water_speed is not None or req.fiber_type is not None:
        engine.set_parameters(water_speed=req.water_speed, fiber_type=req.fiber_type)

    if req.action == "start":
        engine.start()
    elif req.action == "pause":
        engine.pause()
    elif req.action == "reset":
        engine.reset()

    return {
        "session_id": req.session_id,
        "action": req.action,
        "snapshot": engine.get_snapshot()
    }


@app.get("/api/virtual-spinning/snapshot/{session_id}", tags=["公众虚拟纺纱体验"])
async def get_virtual_spinning_snapshot(session_id: str):
    """获取虚拟纺纱实时状态快照"""
    engine = _public_experience_manager.get_session(session_id)
    if not engine:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return engine.get_snapshot()


@app.delete("/api/virtual-spinning/session/{session_id}", tags=["公众虚拟纺纱体验"])
async def close_virtual_spinning_session(session_id: str):
    """关闭虚拟纺纱会话"""
    _public_experience_manager.remove_session(session_id)
    return {"status": "closed", "session_id": session_id}


@app.get("/api/virtual-spinning/statistics", tags=["公众虚拟纺纱体验"])
async def get_virtual_spinning_statistics():
    """获取公众体验全局统计"""
    return _public_experience_manager.get_statistics()


@app.get("/api/virtual-spinning/fiber-options", tags=["公众虚拟纺纱体验"])
async def get_virtual_spinning_fiber_options():
    """获取虚拟纺纱可选纤维列表"""
    return {
        "fibers": [
            {"type": "cotton", "name": "棉花", "difficulty": "简单", "color": "#FFF8E7"},
            {"type": "hemp", "name": "苎麻", "difficulty": "中等", "color": "#F5E6C8"},
            {"type": "flax", "name": "亚麻", "difficulty": "中等", "color": "#E8D4A8"},
            {"type": "silk", "name": "桑蚕丝", "difficulty": "困难", "color": "#FFF5F0"},
            {"type": "wool", "name": "绵羊毛", "difficulty": "中等", "color": "#FAF0E6"}
        ]
    }
