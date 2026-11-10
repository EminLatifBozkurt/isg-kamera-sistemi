import uuid

import pytest

from isg_api.rules import Assessment, Equipment
from isg_api.temporal_violations import (
    TemporalDecision,
    TemporalObservationKey,
    TemporalPolicy,
    TemporalViolationTracker,
)


def key(
    *,
    session_id: uuid.UUID | None = None,
    rule_id: uuid.UUID | None = None,
    track_id: int = 7,
    equipment: Equipment = Equipment.HELMET,
) -> TemporalObservationKey:
    return TemporalObservationKey(
        camera_session_id=session_id or uuid.UUID(int=1),
        rule_version_id=rule_id or uuid.UUID(int=2),
        track_id=track_id,
        equipment=equipment,
    )


def observe_violations(
    tracker: TemporalViolationTracker,
    observation_key: TemporalObservationKey,
    times: list[float],
):
    return [
        tracker.observe(observation_key, Assessment.VIOLATION_CANDIDATE, time) for time in times
    ]


def test_single_bad_frame_does_not_create_candidate() -> None:
    result = TemporalViolationTracker().observe(key(), Assessment.VIOLATION_CANDIDATE, 0.0)

    assert result.decision is TemporalDecision.ACCUMULATING
    assert not result.candidate_ready
    assert result.violation_observation_count == 1


def test_repeated_observations_over_minimum_duration_create_candidate_once() -> None:
    results = observe_violations(TemporalViolationTracker(), key(), [0.0, 0.5, 1.0, 1.5, 1.8])

    assert [item.candidate_ready for item in results] == [False, False, False, True, True]
    assert [item.became_candidate for item in results] == [False, False, False, True, False]
    assert results[-1].decision is TemporalDecision.CANDIDATE


def test_many_fast_bad_frames_still_need_minimum_duration() -> None:
    results = observe_violations(TemporalViolationTracker(), key(), [0.0, 0.1, 0.2, 0.3])

    assert results[-1].violation_observation_count == 4
    assert not results[-1].candidate_ready


def test_large_gap_starts_new_evidence_sequence() -> None:
    results = observe_violations(TemporalViolationTracker(), key(), [0.0, 0.5, 1.6, 2.1])

    assert results[-1].violation_observation_count == 2
    assert not results[-1].candidate_ready


def test_short_unassessable_period_pauses_without_counting_as_violation() -> None:
    tracker = TemporalViolationTracker()
    observation_key = key()
    observe_violations(tracker, observation_key, [0.0, 0.5])

    unknown = tracker.observe(observation_key, Assessment.UNASSESSABLE, 0.9)
    final = tracker.observe(observation_key, Assessment.VIOLATION_CANDIDATE, 1.0)

    assert unknown.decision is TemporalDecision.UNASSESSABLE
    assert unknown.violation_observation_count == 2
    assert final.violation_observation_count == 3
    assert not final.candidate_ready


def test_long_unassessable_period_expires_old_evidence() -> None:
    tracker = TemporalViolationTracker()
    observation_key = key()
    observe_violations(tracker, observation_key, [0.0, 0.5])

    unknown = tracker.observe(observation_key, Assessment.UNASSESSABLE, 1.6)

    assert unknown.violation_observation_count == 0
    assert not unknown.candidate_ready


def test_compliant_observation_clears_accumulated_evidence() -> None:
    tracker = TemporalViolationTracker()
    observation_key = key()
    observe_violations(tracker, observation_key, [0.0, 0.5, 1.0])

    clear = tracker.observe(observation_key, Assessment.COMPLIANT, 1.2)
    next_bad = tracker.observe(observation_key, Assessment.VIOLATION_CANDIDATE, 1.4)

    assert clear.decision is TemporalDecision.CLEAR
    assert next_bad.violation_observation_count == 1


def test_sessions_rules_tracks_and_equipment_keep_independent_state() -> None:
    tracker = TemporalViolationTracker()
    base_key = key()
    observe_violations(tracker, base_key, [0.0, 0.5, 1.0])

    for other_key in (
        key(session_id=uuid.UUID(int=3)),
        key(rule_id=uuid.UUID(int=4)),
        key(track_id=8),
        key(equipment=Equipment.VEST),
    ):
        result = tracker.observe(other_key, Assessment.VIOLATION_CANDIDATE, 1.2)
        assert result.violation_observation_count == 1


def test_out_of_order_or_invalid_time_is_rejected() -> None:
    tracker = TemporalViolationTracker()
    observation_key = key()
    tracker.observe(observation_key, Assessment.VIOLATION_CANDIDATE, 1.0)

    with pytest.raises(ValueError, match="geriye"):
        tracker.observe(observation_key, Assessment.VIOLATION_CANDIDATE, 0.9)
    with pytest.raises(ValueError):
        tracker.observe(key(track_id=9), Assessment.VIOLATION_CANDIDATE, float("nan"))


def test_stale_state_and_completed_session_can_be_removed() -> None:
    tracker = TemporalViolationTracker()
    first = key(session_id=uuid.UUID(int=10))
    second = key(session_id=uuid.UUID(int=11))
    tracker.observe(first, Assessment.VIOLATION_CANDIDATE, 0.0)
    tracker.observe(second, Assessment.VIOLATION_CANDIDATE, 5.0)

    assert tracker.prune_stale(11.0) == 1
    assert tracker.reset_session(second.camera_session_id) == 1
    assert tracker.reset_session(second.camera_session_id) == 0


@pytest.mark.parametrize(
    "policy",
    [
        TemporalPolicy(minimum_violation_observations=2),
        TemporalPolicy(minimum_violation_duration_seconds=0.5),
    ],
)
def test_valid_custom_policy_can_be_used(policy: TemporalPolicy) -> None:
    assert TemporalViolationTracker(policy).policy is policy


def test_invalid_policy_is_rejected() -> None:
    with pytest.raises(ValueError):
        TemporalPolicy(minimum_violation_observations=1)
    with pytest.raises(ValueError):
        TemporalPolicy(
            minimum_violation_duration_seconds=4.0,
            observation_window_seconds=3.0,
        )
