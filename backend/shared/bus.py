import json
import time
import uuid
import threading
from typing import Any, Callable, Dict, Optional
from contextlib import contextmanager

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None

from .config_loader import get_config


# ---------- 消息工具 ----------
def make_envelope(topic: str, payload: Any, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    return {
        "id": correlation_id or uuid.uuid4().hex,
        "ts": time.time(),
        "topic": topic,
        "payload": payload,
    }


def dump_envelope(env: Dict[str, Any]) -> bytes:
    return json.dumps(env, ensure_ascii=False, default=str).encode("utf-8")


def load_envelope(raw: bytes) -> Dict[str, Any]:
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, AttributeError):
        return {"id": "parse_failed", "ts": time.time(), "topic": "", "payload": None}


# ---------- Redis 消息总线 ----------
class MessageBus:
    """基于 Redis Pub/Sub 的微服务消息总线。

    支持三种模式:
      1. publish(topic, payload)       — 火过即忘，多个订阅者都能收到
      2. request(topic, payload, wait) — 请求/响应：publish + 等待带 correlation_id 的回复
      3. subscribe(topic, callback)    — 后台线程订阅，回调函数处理
    """

    _instance: Optional["MessageBus"] = None

    @classmethod
    def instance(cls) -> "MessageBus":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if redis is None:
            raise RuntimeError("redis 包未安装，请先执行 pip install redis pyyaml")
        self._cfg = get_config("redis", default={}) or {}
        self._client = redis.Redis(
            host=self._cfg.get("host", "localhost"),
            port=int(self._cfg.get("port", 6379)),
            db=int(self._cfg.get("db", 0)),
            password=self._cfg.get("password"),
            socket_timeout=float(self._cfg.get("socket_timeout", 5.0)),
            decode_responses=False,
        )
        self._topics = get_config("topics", default={}) or {}
        self._pubsub = self._client.pubsub(ignore_subscribe_messages=True)
        self._listener_thread: Optional[threading.Thread] = None
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._pending_events: Dict[str, Optional[Dict[str, Any]]] = {}
        self._pending_lock = threading.Lock()
        self._started = False

    # ---------- 主题名 ----------
    def topic(self, name: str) -> str:
        return self._topics.get(name, name)

    # ---------- 连接测试 ----------
    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except Exception:
            return False

    # ---------- 发布 ----------
    def publish(self, topic_name: str, payload: Any, correlation_id: Optional[str] = None) -> str:
        env = make_envelope(self.topic(topic_name), payload, correlation_id)
        self._client.publish(self.topic(topic_name), dump_envelope(env))
        return env["id"]

    # ---------- 请求/响应 ----------
    def request(self, request_topic: str, reply_topic: str,
                payload: Any, timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        corr_id = uuid.uuid4().hex
        with self._pending_lock:
            self._pending_events[corr_id] = None
        try:
            # 订阅一次响应主题（只在未订阅时）
            self._ensure_handler_installed(reply_topic, self._pending_reply_handler)
            self.publish(request_topic, payload, correlation_id=corr_id)
            deadline = time.time() + timeout
            while time.time() < deadline:
                with self._pending_lock:
                    result = self._pending_events.pop(corr_id, None)
                if result is not None:
                    return result
                time.sleep(0.05)
            return None
        finally:
            with self._pending_lock:
                self._pending_events.pop(corr_id, None)

    # ---------- 订阅 ----------
    def subscribe(self, topic_name: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        self._ensure_handler_installed(topic_name, handler)

    def _ensure_handler_installed(self, topic_name: str,
                                  handler: Callable[[Dict[str, Any]], None]) -> None:
        key = self.topic(topic_name)
        if key in self._handlers:
            # 合并：request模式和subscribe可能用同一topic
            existing = self._handlers[key]
            self._handlers[key] = self._combine_handlers(existing, handler)
        else:
            self._handlers[key] = handler
            self._pubsub.subscribe(**{key: self._dispatch})
        self._start_listener_once()

    @staticmethod
    def _combine_handlers(h1, h2) -> Callable:
        def _multi(env):
            h1(env)
            h2(env)
        return _multi

    # ---------- 监听线程 ----------
    def _start_listener_once(self) -> None:
        if self._started:
            return
        self._started = True
        self._listener_thread = threading.Thread(
            target=self._run_listener, daemon=True, name="MessageBusListener"
        )
        self._listener_thread.start()

    def _run_listener(self) -> None:
        for msg in self._pubsub.listen():
            try:
                pass  # _dispatch 已经在 subscribe 回调里
            except Exception as e:
                print(f"[MessageBus] listener error: {e}")

    def _dispatch(self, msg) -> None:
        if msg is None or msg.get("type") != "message":
            return
        channel = msg.get("channel")
        if isinstance(channel, bytes):
            channel = channel.decode("utf-8")
        handler = self._handlers.get(channel)
        if not handler:
            return
        try:
            env = load_envelope(msg.get("data", b""))
            handler(env)
        except Exception as e:
            print(f"[MessageBus] handler error on {channel}: {e}")

    # ---------- request 的响应回调 ----------
    def _pending_reply_handler(self, env: Dict[str, Any]) -> None:
        corr_id = env.get("id")
        if not corr_id:
            return
        with self._pending_lock:
            if corr_id in self._pending_events:
                self._pending_events[corr_id] = env.get("payload")

    # ---------- 资源释放 ----------
    def close(self) -> None:
        try:
            self._pubsub.unsubscribe()
            self._pubsub.close()
            self._client.close()
        except Exception:
            pass


@contextmanager
def message_bus_scope():
    bus = MessageBus.instance()
    try:
        yield bus
    finally:
        bus.close()
