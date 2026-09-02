from meeting_intelligence.main import (
    _MEETING_LOCK_STRIPE_COUNT,
    _meeting_lock,
    _meeting_lock_stripes,
)


def test_same_meeting_always_uses_same_lock() -> None:
    first = _meeting_lock("meeting-alpha")
    second = _meeting_lock("meeting-alpha")

    assert first is second


def test_arbitrary_meeting_ids_cannot_grow_lock_state() -> None:
    assert len(_meeting_lock_stripes) == _MEETING_LOCK_STRIPE_COUNT

    locks = {_meeting_lock(f"attacker-controlled-{index}") for index in range(10_000)}

    assert len(_meeting_lock_stripes) == _MEETING_LOCK_STRIPE_COUNT
    assert locks.issubset(set(_meeting_lock_stripes))
