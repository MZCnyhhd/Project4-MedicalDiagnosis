"""
模块名称: Trace Collector (评估数据采集器)
功能描述:
    无侵入式采集 Agent 全链路执行数据，构建标准化的 AgentTrace 对象。
    支持装饰器自动采集和手动埋点两种模式。
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from functools import wraps

from src.services.logging import log_info, log_warn


@dataclass
class AgentTrace:
    """Agent 执行全链路追踪数据"""
    trace_id: str
    timestamp: float
    agent_name: str
    input_report: str
    output_diagnosis: str
    latency_ms: float
    token_usage: Dict[str, int] = field(default_factory=dict)
    rag_context: List[str] = field(default_factory=list)
    rag_latency_ms: float = 0.0
    model_name: str = ""
    retry_count: int = 0
    raw_response: str = ""
    triage_result: List[str] = field(default_factory=list)
    specialist_outputs: Dict[str, str] = field(default_factory=dict)
    mdt_output: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "agent_name": self.agent_name,
            "latency_ms": self.latency_ms,
            "token_usage": self.token_usage,
            "rag_latency_ms": self.rag_latency_ms,
            "model_name": self.model_name,
            "retry_count": self.retry_count,
            "error": self.error,
        }


class TraceCollector:
    """Agent Trace 采集器（单例模式）"""

    _instance: Optional["TraceCollector"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._traces: List[AgentTrace] = []
            cls._instance._active_traces: Dict[str, AgentTrace] = {}
        return cls._instance

    def start_trace(self, agent_name: str, input_report: str) -> str:
        """开始一次新的 Trace 采集"""
        trace_id = str(uuid.uuid4())
        trace = AgentTrace(
            trace_id=trace_id,
            timestamp=time.time(),
            agent_name=agent_name,
            input_report=input_report,
            output_diagnosis="",
            latency_ms=0.0,
        )
        self._active_traces[trace_id] = trace
        log_info(f"[TraceCollector] Trace 开始: {trace_id[:8]} ({agent_name})")
        return trace_id

    def end_trace(self, trace_id: str, output_diagnosis: str, **kwargs) -> AgentTrace:
        """结束 Trace 采集并归档"""
        trace = self._active_traces.pop(trace_id, None)
        if not trace:
            log_warn(f"[TraceCollector] 未找到 Trace: {trace_id}")
            return None
        trace.output_diagnosis = output_diagnosis
        trace.latency_ms = (time.time() - trace.timestamp) * 1000
        for key, value in kwargs.items():
            if hasattr(trace, key):
                setattr(trace, key, value)
        self._traces.append(trace)
        log_info(f"[TraceCollector] Trace 结束: {trace_id[:8]} ({trace.latency_ms:.0f}ms)")
        return trace

    def record_rag(self, trace_id: str, context: List[str], latency_ms: float):
        """记录 RAG 检索结果"""
        trace = self._active_traces.get(trace_id)
        if trace:
            trace.rag_context = context
            trace.rag_latency_ms = latency_ms

    def record_token_usage(self, trace_id: str, usage: Dict[str, int]):
        """记录 Token 消耗"""
        trace = self._active_traces.get(trace_id)
        if trace:
            trace.token_usage = usage

    def record_specialist(self, trace_id: str, specialist_name: str, output: str):
        """记录专科 Agent 输出"""
        trace = self._active_traces.get(trace_id)
        if trace:
            trace.specialist_outputs[specialist_name] = output

    def record_mdt(self, trace_id: str, output: str):
        """记录 MDT 综合诊断输出"""
        trace = self._active_traces.get(trace_id)
        if trace:
            trace.mdt_output = output

    def get_recent_traces(self, n: int = 100) -> List[AgentTrace]:
        """获取最近 n 条 Trace"""
        return self._traces[-n:]

    def clear(self):
        """清空历史 Trace"""
        self._traces.clear()
        self._active_traces.clear()


def trace_agent(agent_name: str = None):
    """装饰器：自动采集被装饰函数的 Agent Trace"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            collector = TraceCollector()
            name = agent_name or func.__name__
            report = kwargs.get("medical_report", "") or (args[0] if args else "")
            trace_id = collector.start_trace(name, report)
            try:
                result = await func(*args, **kwargs)
                collector.end_trace(trace_id, str(result))
                return result
            except Exception as e:
                collector.end_trace(trace_id, "", error=str(e))
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            collector = TraceCollector()
            name = agent_name or func.__name__
            report = kwargs.get("medical_report", "") or (args[0] if args else "")
            trace_id = collector.start_trace(name, report)
            try:
                result = func(*args, **kwargs)
                collector.end_trace(trace_id, str(result))
                return result
            except Exception as e:
                collector.end_trace(trace_id, "", error=str(e))
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


import asyncio
