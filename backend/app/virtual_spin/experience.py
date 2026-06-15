from typing import Dict, Optional

from .engine import VirtualSpinningEngine


class PublicExperienceManager:
    """公众体验管理器，管理多个并发纺纱会话"""

    def __init__(self, max_sessions: int = 100):
        self.sessions: Dict[str, VirtualSpinningEngine] = {}
        self.max_sessions = max_sessions

    def create_session(self) -> str:
        """创建新会话"""
        if len(self.sessions) >= self.max_sessions:
            oldest = min(self.sessions.keys(), key=lambda s: self.sessions[s].state.start_time)
            del self.sessions[oldest]

        engine = VirtualSpinningEngine()
        self.sessions[engine.session_id] = engine
        return engine.session_id

    def get_session(self, session_id: str) -> Optional[VirtualSpinningEngine]:
        """获取会话"""
        return self.sessions.get(session_id)

    def remove_session(self, session_id: str):
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]

    def tick_all(self, dt: float = 0.05):
        """所有会话推进一个时间步"""
        for engine in self.sessions.values():
            engine.tick(dt)

    def get_active_count(self) -> int:
        """获取活跃会话数"""
        return sum(1 for e in self.sessions.values() if e.state.is_running)

    def get_statistics(self) -> Dict:
        """获取体验统计"""
        total = len(self.sessions)
        running = self.get_active_count()
        total_length = sum(e.state.yarn_length_m for e in self.sessions.values())
        avg_quality = sum(e.state.quality_score for e in self.sessions.values()) / max(1, total)
        avg_efficiency = sum(e.state.efficiency_score for e in self.sessions.values()) / max(1, total)

        return {
            "total_sessions": total,
            "running_sessions": running,
            "total_yarn_produced_m": round(total_length, 2),
            "avg_quality_score": round(avg_quality, 1),
            "avg_efficiency_score": round(avg_efficiency, 1)
        }
