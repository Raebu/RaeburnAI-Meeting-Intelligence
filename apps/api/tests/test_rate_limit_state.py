from collections import deque

from meeting_intelligence.main import _consume_rate_limit, _rate_window


def setup_function() -> None:
    _rate_window.clear()


def teardown_function() -> None:
    _rate_window.clear()


def test_rate_limit_reuses_existing_client_bucket() -> None:
    assert _consume_rate_limit("client-a", 1.0)
    assert _consume_rate_limit("client-a", 2.0)
    assert list(_rate_window) == ["client-a"]
    assert list(_rate_window["client-a"]) == [1.0, 2.0]


def test_rate_limit_prunes_stale_clients_before_capacity_check(monkeypatch) -> None:
    settings = __import__(
        "meeting_intelligence.main", fromlist=["get_settings"]
    ).get_settings()
    monkeypatch.setattr(settings, "rate_limit_max_clients", 100)

    for index in range(100):
        _rate_window[f"stale-{index}"] = deque([1.0])

    assert _consume_rate_limit("fresh-client", 62.1)
    assert list(_rate_window) == ["fresh-client"]


def test_rate_limit_refuses_new_clients_when_capacity_is_active(monkeypatch) -> None:
    settings = __import__(
        "meeting_intelligence.main", fromlist=["get_settings"]
    ).get_settings()
    monkeypatch.setattr(settings, "rate_limit_max_clients", 100)

    for index in range(100):
        _rate_window[f"active-{index}"] = deque([30.0])

    assert not _consume_rate_limit("overflow-client", 60.0)
    assert len(_rate_window) == 100
    assert "overflow-client" not in _rate_window
