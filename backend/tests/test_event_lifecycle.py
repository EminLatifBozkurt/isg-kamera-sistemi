import uuid

import pytest

from isg_api.event_lifecycle import (
    EventEndReason,
    EventLifecycleKey,
    EventLifecyclePolicy,
    EventLifecycleTracker,
    EventTransitionKind,
)
from isg_api.models import TechnicalStatus
from isg_api.rules import Equipment


def key(
    *,
    session_id: uuid.UUID | None = None,
    rule_id: uuid.UUID | None = None,
    track_id: int = 7,
) -> EventLifecycleKey:
    return EventLifecycleKey(
        camera_session_id=session_id or uuid.UUID(int=1),
        rule_version_id=rule_id or uuid.UUID(int=2),
        track_id=track_id,
    )


def id_factory() -> object:
    ids = iter((uuid.UUID(int=100), uuid.UUID(int=101), uuid.UUID(int=102)))
    return lambda: next(ids)


def test_empty_candidate_does_not_start_event() -> None:
    tracker = EventLifecycleTracker()

    assert tracker.observe(key(), [], 0.0) == ()
    assert tracker.active_event_count == 0


def test_continuous_candidate_starts_once_and_notifies_once() -> None:
    tracker = EventLifecycleTracker(event_id_factory=id_factory())

    started = tracker.observe(key(), [Equipment.HELMET], 0.0)[0]
    updated = tracker.observe(key(), [Equipment.HELMET], 0.5)[0]

    assert started.kind is EventTransitionKind.STARTED
    assert started.notification_required
    assert updated.kind is EventTransitionKind.UPDATED
    assert not updated.notification_required
    assert updated.event_id == started.event_id
    assert tracker.active_event_count == 1


def test_equipment_changes_merge_into_same_continuous_event() -> None:
    tracker = EventLifecycleTracker(event_id_factory=id_factory())
    started = tracker.observe(key(), [Equipment.HELMET], 0.0)[0]

    updated = tracker.observe(key(), [Equipment.VEST], 0.5)[0]

    assert updated.event_id == started.event_id
    assert updated.observed_equipment == (Equipment.HELMET, Equipment.VEST)
    assert updated.current_equipment == (Equipment.VEST,)
    assert not updated.notification_required


def test_one_clear_frame_does_not_end_event() -> None:
    tracker = EventLifecycleTracker(event_id_factory=id_factory())
    tracker.observe(key(), [Equipment.HELMET], 0.0)

    transition = tracker.observe(key(), [], 0.5)[0]

    assert transition.kind is EventTransitionKind.UPDATED
    assert transition.technical_status is TechnicalStatus.ACTIVE


def test_two_clear_observations_over_grace_period_end_as_resolved() -> None:
    tracker = EventLifecycleTracker(event_id_factory=id_factory())
    tracker.observe(key(), [Equipment.HELMET], 0.0)
    tracker.observe(key(), [], 0.5)

    ended = tracker.observe(key(), [], 1.5)[0]

    assert ended.kind is EventTransitionKind.ENDED
    assert ended.technical_status is TechnicalStatus.ENDED
    assert ended.end_reason is EventEndReason.RESOLVED
    assert ended.ended_at_seconds == 1.5
    assert tracker.active_event_count == 0


def test_violation_during_resolution_grace_keeps_same_event() -> None:
    tracker = EventLifecycleTracker(event_id_factory=id_factory())
    started = tracker.observe(key(), [Equipment.HELMET], 0.0)[0]
    tracker.observe(key(), [], 0.5)

    resumed = tracker.observe(key(), [Equipment.HELMET], 1.0)[0]

    assert resumed.event_id == started.event_id
    assert resumed.kind is EventTransitionKind.UPDATED
    assert not resumed.notification_required


def test_new_violation_after_resolution_starts_new_event() -> None:
    tracker = EventLifecycleTracker(event_id_factory=id_factory())
    first = tracker.observe(key(), [Equipment.HELMET], 0.0)[0]
    tracker.observe(key(), [], 0.5)
    tracker.observe(key(), [], 1.5)

    second = tracker.observe(key(), [Equipment.HELMET], 2.0)[0]

    assert second.kind is EventTransitionKind.STARTED
    assert second.notification_required
    assert second.event_id != first.event_id


def test_missing_track_expires_once_with_observation_lost_reason() -> None:
    tracker = EventLifecycleTracker(event_id_factory=id_factory())
    tracker.observe(key(), [Equipment.HELMET], 0.0)

    assert tracker.expire_missing(1.9) == ()
    ended = tracker.expire_missing(2.0)[0]

    assert ended.end_reason is EventEndReason.OBSERVATION_LOST
    assert tracker.expire_missing(3.0) == ()


def test_session_end_closes_every_open_event_in_that_session() -> None:
    tracker = EventLifecycleTracker(event_id_factory=id_factory())
    session_id = uuid.UUID(int=8)
    tracker.observe(key(session_id=session_id, track_id=1), [Equipment.HELMET], 0.0)
    tracker.observe(key(session_id=session_id, track_id=2), [Equipment.VEST], 0.2)
    tracker.observe(key(session_id=uuid.UUID(int=9)), [Equipment.GLOVES], 0.0)

    ended = tracker.end_session(session_id, 1.0)

    assert len(ended) == 2
    assert {item.end_reason for item in ended} == {EventEndReason.SESSION_ENDED}
    assert tracker.active_event_count == 1


def test_rule_change_ends_old_event_and_starts_new_one() -> None:
    tracker = EventLifecycleTracker(event_id_factory=id_factory())
    old = tracker.observe(key(rule_id=uuid.UUID(int=20)), [Equipment.HELMET], 0.0)[0]

    transitions = tracker.observe(key(rule_id=uuid.UUID(int=21)), [Equipment.HELMET], 0.5)

    assert [item.kind for item in transitions] == [
        EventTransitionKind.ENDED,
        EventTransitionKind.STARTED,
    ]
    assert transitions[0].event_id == old.event_id
    assert transitions[0].end_reason is EventEndReason.RULE_CHANGED
    assert transitions[1].event_id != old.event_id
    assert transitions[1].notification_required


def test_same_track_number_in_different_session_is_independent() -> None:
    tracker = EventLifecycleTracker(event_id_factory=id_factory())
    first = tracker.observe(key(session_id=uuid.UUID(int=30)), [Equipment.HELMET], 0.0)[0]
    second = tracker.observe(key(session_id=uuid.UUID(int=31)), [Equipment.HELMET], 0.0)[0]

    assert first.event_id != second.event_id
    assert tracker.active_event_count == 2


def test_out_of_order_and_invalid_time_are_rejected() -> None:
    tracker = EventLifecycleTracker()
    tracker.observe(key(), [Equipment.HELMET], 1.0)

    with pytest.raises(ValueError, match="geriye"):
        tracker.observe(key(), [Equipment.HELMET], 0.9)
    with pytest.raises(ValueError):
        tracker.expire_missing(float("nan"))


def test_invalid_policy_is_rejected() -> None:
    with pytest.raises(ValueError):
        EventLifecyclePolicy(resolution_observations=1)
    with pytest.raises(ValueError):
        EventLifecyclePolicy(
            resolution_duration_seconds=2.0,
            observation_lost_seconds=1.0,
        )
