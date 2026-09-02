from meeting_intelligence.observability import (
    increment,
    observe,
    prometheus_metrics,
    safe_ref,
    trace_span,
)


def test_metrics_exclude_unapproved_high_cardinality_labels() -> None:
    secret_transcript = "customer said their password is swordfish"
    increment(
        "requests_total",
        method="GET",
        route="/healthz",
        status="200",
        transcript=secret_transcript,
        workspace_id="private-workspace",
    )
    observe(
        "request_duration_ms",
        12.5,
        method="GET",
        route="/healthz",
        status="200",
        transcript=secret_transcript,
    )
    rendered = prometheus_metrics()
    assert "requests_total" in rendered
    assert "request_duration_ms_count" in rendered
    assert secret_transcript not in rendered
    assert "private-workspace" not in rendered


def test_safe_ref_is_stable_and_non_reversible() -> None:
    value = "workspace-sensitive-name"
    assert safe_ref(value) == safe_ref(value)
    assert value not in safe_ref(value)
    assert len(safe_ref(value)) == 12


def test_trace_span_records_duration_without_payload() -> None:
    with trace_span("dispatch", system="github", transcript="never-log-this"):
        pass
    rendered = prometheus_metrics()
    assert "trace_duration_ms_count" in rendered
    assert "never-log-this" not in rendered
