"""
Memory OpenTelemetry-compatible instrumentation (Phase 9+).

Mock-first:
  - Always records spans in-process (ring buffer + optional JSONL file).
  - If ``opentelemetry`` is installed **and** SUPERAI_MEMORY_OTEL=otlp|sdk,
    attempts real OTEL tracer (best-effort; failures fall back to mock).

Never records free-text memory content — only operation names, counts, timings.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional


def _truthy(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def otel_mode() -> str:
    """
    off | mock | sdk

    SUPERAI_MEMORY_OTEL=0|off → off
    SUPERAI_MEMORY_OTEL=sdk|otlp → try real SDK
    default / mock / 1 → mock recording
    """
    raw = (os.getenv("SUPERAI_MEMORY_OTEL") or "mock").strip().lower()
    if raw in {"0", "false", "off", "no"}:
        return "off"
    if raw in {"sdk", "otlp", "opentelemetry"}:
        return "sdk"
    return "mock"


def default_export_path() -> Path:
    env = (os.getenv("SUPERAI_MEMORY_OTEL_PATH") or "").strip()
    if env:
        return Path(env).expanduser()
    p = Path.home() / ".superai" / "memory" / "otel_spans.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class SpanRecord:
    name: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    start_ns: int
    end_ns: Optional[int] = None
    status: str = "UNSET"  # UNSET|OK|ERROR
    attributes: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def duration_ms(self) -> Optional[float]:
        if self.end_ns is None:
            return None
        return (self.end_ns - self.start_ns) / 1_000_000.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["duration_ms"] = self.duration_ms
        return d


class MemoryOtel:
    """Process-local span store with optional file export."""

    def __init__(self, *, max_spans: int = 500, export_path: Optional[Path] = None):
        self.mode = otel_mode()
        self.max_spans = max(50, int(max_spans))
        self.export_path = Path(export_path) if export_path else default_export_path()
        self._spans: List[SpanRecord] = []
        self._lock = threading.Lock()
        self._otel_tracer = None
        if self.mode == "sdk":
            self._otel_tracer = self._try_otel_tracer()

    def _try_otel_tracer(self) -> Any:
        try:
            from opentelemetry import trace  # type: ignore

            return trace.get_tracer("superai.memory", "0.1.0")
        except Exception:
            return None

    def enabled(self) -> bool:
        return self.mode != "off"

    def clear(self) -> None:
        with self._lock:
            self._spans.clear()

    def list_spans(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            rows = list(self._spans[-max(1, limit) :])
        return [s.to_dict() for s in rows]

    def status(self) -> Dict[str, Any]:
        with self._lock:
            n = len(self._spans)
        # P9-R2: surface exporter-related env when SDK mode is requested
        endpoint = (os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or "").strip() or None
        service = (os.getenv("OTEL_SERVICE_NAME") or "superai.memory").strip()
        return {
            "ok": True,
            "product": "memory_otel",
            "mode": self.mode,
            "sdk_available": self._otel_tracer is not None,
            "spans_buffered": n,
            "export_path": str(self.export_path),
            "otlp_endpoint_env": endpoint,
            "otel_service_name": service,
            "env_help": {
                "SUPERAI_MEMORY_OTEL": "off|mock|sdk (default mock)",
                "SUPERAI_MEMORY_OTEL_PATH": "JSONL span export path (mock)",
                "OTEL_EXPORTER_OTLP_ENDPOINT": "when SUPERAI_MEMORY_OTEL=sdk and opentelemetry installed",
                "OTEL_SERVICE_NAME": "service name for SDK path (default superai.memory)",
            },
            "message": (
                f"Memory OTEL mode={self.mode} spans={n} "
                f"sdk={'yes' if self._otel_tracer else 'no'}"
                + (f" endpoint={endpoint}" if endpoint else "")
            ),
        }

    def start_span(
        self,
        name: str,
        *,
        attributes: Optional[Dict[str, Any]] = None,
        parent_span_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> SpanRecord:
        span = SpanRecord(
            name=name,
            trace_id=trace_id or uuid.uuid4().hex,
            span_id=uuid.uuid4().hex[:16],
            parent_span_id=parent_span_id,
            start_ns=time.time_ns(),
            attributes=_safe_attrs(attributes or {}),
        )
        if not self.enabled():
            return span
        with self._lock:
            self._spans.append(span)
            if len(self._spans) > self.max_spans:
                self._spans = self._spans[-self.max_spans :]
        return span

    def end_span(
        self,
        span: SpanRecord,
        *,
        status: str = "OK",
        error: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> SpanRecord:
        span.end_ns = time.time_ns()
        span.status = status
        if error:
            span.error = str(error)[:300]
            span.status = "ERROR"
        if attributes:
            span.attributes.update(_safe_attrs(attributes))
        if self.enabled():
            self._append_jsonl(span)
        return span

    def _append_jsonl(self, span: SpanRecord) -> None:
        try:
            self.export_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.export_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(span.to_dict(), default=str) + "\n")
        except Exception as e:  # noqa: BLE001
            # Surface export failure (AGY P9: was silent pass)
            span.attributes = dict(span.attributes or {})
            span.attributes["export_error"] = f"{type(e).__name__}:{str(e)[:120]}"

    @contextmanager
    def span(
        self,
        name: str,
        *,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Generator[SpanRecord, None, None]:
        rec = self.start_span(name, attributes=attributes)
        otel_cm = None
        if self._otel_tracer is not None:
            try:
                otel_cm = self._otel_tracer.start_as_current_span(name)
                otel_cm.__enter__()
            except Exception:
                otel_cm = None
        try:
            yield rec
            self.end_span(rec, status="OK")
            if otel_cm is not None:
                otel_cm.__exit__(None, None, None)
        except Exception as e:  # noqa: BLE001
            self.end_span(rec, status="ERROR", error=str(e))
            if otel_cm is not None:
                otel_cm.__exit__(type(e), e, e.__traceback__)
            raise


_SAFE_KEYS = frozenset(
    {
        "phase",
        "operation",
        "strategy",
        "dataset_id",
        "session_id",
        "count",
        "nodes",
        "edges",
        "chunks",
        "ok",
        "format",
        "level",
        "hook",
        "product",
        "error_code",
        "duration_ms",
    }
)


def _safe_attrs(attrs: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in (attrs or {}).items():
        if k not in _SAFE_KEYS:
            continue
        if isinstance(v, (str, int, float, bool)) or v is None:
            if isinstance(v, str) and len(v) > 120:
                v = v[:120]
            out[k] = v
        else:
            out[k] = str(v)[:80]
    return out


_DEFAULT: Optional[MemoryOtel] = None
_DEFAULT_LOCK = threading.Lock()


def get_memory_otel() -> MemoryOtel:
    global _DEFAULT
    with _DEFAULT_LOCK:
        if _DEFAULT is None:
            _DEFAULT = MemoryOtel()
        return _DEFAULT


def reset_memory_otel() -> None:
    global _DEFAULT
    with _DEFAULT_LOCK:
        _DEFAULT = None


@contextmanager
def memory_span(
    name: str, *, attributes: Optional[Dict[str, Any]] = None
) -> Generator[SpanRecord, None, None]:
    """Module-level convenience for memory operations."""
    with get_memory_otel().span(name, attributes=attributes) as s:
        yield s


def instrument_report(op: str, report: Dict[str, Any]) -> Dict[str, Any]:
    """Attach otel span summary onto an existing report dict (non-breaking)."""
    if not get_memory_otel().enabled():
        return report
    try:
        with memory_span(
            f"memory.{op}",
            attributes={
                "operation": op,
                "ok": bool(report.get("ok")),
                "count": report.get("count") or report.get("items_count") or report.get("nodes_written"),
                "dataset_id": report.get("dataset_id"),
                "strategy": report.get("strategy"),
                "product": report.get("product"),
            },
        ):
            pass
        report = dict(report)
        report.setdefault("otel_mode", get_memory_otel().mode)
    except Exception:
        pass
    return report
