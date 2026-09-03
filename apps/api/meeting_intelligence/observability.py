from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from threading import Lock

import structlog

logger = structlog.get_logger(__name__)
_lock = Lock()
_counters: Counter[tuple[str, tuple[tuple[str, str], ...]]] = Counter()
_histograms: dict[
    tuple[str, tuple[tuple[str, str], ...]], tuple[int, float, float]
] = {}
_ALLOWED_LABELS = {"method", "route", "status", "operation", "system", "outcome"}


def safe_ref(value: str) -> str:
    """Return a stable non-reversible operational reference."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _labels(labels: dict[str, str]) -> tuple[tuple[str, str], ...]:
    """Allow only bounded operational labels; never transcript/user content."""
    return tuple(
        sorted(
            (key, str(value))
            for key, value in labels.items()
            if key in _ALLOWED_LABELS
        )
    )


def increment(name: str, **labels: str) -> None:
    with _lock:
        _counters[(name, _labels(labels))] += 1


def observe(name: str, value: float, **labels: str) -> None:
    key = (name, _labels(labels))
    with _lock:
        count, total, maximum = _histograms.get(key, (0, 0.0, 0.0))
        _histograms[key] = (count + 1, total + value, max(maximum, value))


@contextmanager
def trace_span(name: str, **fields: str) -> Iterator[None]:
    """Emit a transcript-safe structured span without external telemetry dependency."""
    started = time.perf_counter()
    trace_id = hashlib.sha256(f"{time.time_ns()}:{name}".encode()).hexdigest()[:16]
    safe_fields = {key: value for key, value in fields.items() if key in _ALLOWED_LABELS}
    logger.info("trace_started", span=name, trace_id=trace_id, **safe_fields)
    try:
        yield
    except Exception:
        increment("trace_errors_total", operation=name)
        logger.error("trace_failed", span=name, trace_id=trace_id, **safe_fields)
        raise
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        observe("trace_duration_ms", duration_ms, operation=name)
        logger.info(
            "trace_completed",
            span=name,
            trace_id=trace_id,
            duration_ms=duration_ms,
            **safe_fields,
        )


def prometheus_metrics() -> str:
    """Render bounded process metrics in Prometheus text exposition format."""
    lines: list[str] = []
    with _lock:
        counters = list(_counters.items())
        histograms = list(_histograms.items())
    for (name, labels), value in sorted(counters):
        suffix = _render_labels(labels)
        lines.append(f"{name}{suffix} {value}")
    for (name, labels), (count, total, maximum) in sorted(histograms):
        suffix = _render_labels(labels)
        lines.append(f"{name}_count{suffix} {count}")
        lines.append(f"{name}_sum{suffix} {total:.3f}")
        lines.append(f"{name}_max{suffix} {maximum:.3f}")
    return "\n".join(lines) + ("\n" if lines else "")


def _render_labels(labels: tuple[tuple[str, str], ...]) -> str:
    if not labels:
        return ""
    rendered = ",".join(f"{key}={json.dumps(value)}" for key, value in labels)
    return "{" + rendered + "}"
