from datetime import UTC, datetime
from pathlib import Path

import pytest

import isg_api.ppe_tracking as ppe_tracking
from isg_api.ppe_tracking import (
    AssignmentStatus,
    BoundingBox,
    TrackedDetection,
    UltralyticsPpeTracker,
    assign_equipment_to_people,
)
from isg_api.video_source import VideoFrame


def person(track_id: int, box=(0, 0, 100, 200)) -> TrackedDetection:
    return TrackedDetection("Person", 0.9, BoundingBox(*box), track_id)


def equipment(name: str, box) -> TrackedDetection:
    return TrackedDetection(name, 0.8, BoundingBox(*box))


def test_equipment_is_assigned_to_expected_body_region() -> None:
    detections = [
        person(7),
        equipment("helmet", (30, 5, 70, 45)),
        equipment("vest", (20, 55, 80, 130)),
        equipment("boots", (20, 155, 80, 198)),
    ]

    people, assignments = assign_equipment_to_people(detections)

    assert people[0].detected_equipment == {"helmet", "vest", "boots"}
    assert {item.status for item in assignments} == {AssignmentStatus.ASSIGNED}
    assert {item.person_track_id for item in assignments} == {7}


def test_neighbouring_person_does_not_receive_other_persons_helmet() -> None:
    detections = [
        person(1, (0, 0, 100, 200)),
        person(2, (120, 0, 220, 200)),
        equipment("helmet", (25, 5, 75, 45)),
    ]

    people, _ = assign_equipment_to_people(detections)

    by_id = {item.track_id: item for item in people}
    assert by_id[1].detected_equipment == {"helmet"}
    assert by_id[2].detected_equipment == set()


def test_equipment_between_overlapping_people_stays_ambiguous() -> None:
    detections = [
        person(1, (0, 0, 120, 220)),
        person(2, (20, 0, 140, 220)),
        equipment("helmet", (45, 5, 95, 45)),
    ]

    people, assignments = assign_equipment_to_people(detections)

    assert assignments[0].status is AssignmentStatus.AMBIGUOUS
    assert assignments[0].person_track_id is None
    assert assignments[0].candidate_track_ids == (2, 1)
    assert all(not item.detected_equipment for item in people)
    assert all(item.ambiguous_equipment == {"helmet"} for item in people)


def test_wrong_body_region_is_not_assigned() -> None:
    detections = [person(3), equipment("helmet", (30, 150, 70, 195))]

    people, assignments = assign_equipment_to_people(detections)

    assert people[0].detected_equipment == set()
    assert assignments[0].status is AssignmentStatus.UNASSIGNED


def test_person_without_confirmed_track_id_is_not_used() -> None:
    detections = [
        TrackedDetection("Person", 0.9, BoundingBox(0, 0, 100, 200)),
        equipment("vest", (20, 50, 80, 130)),
    ]

    people, assignments = assign_equipment_to_people(detections)

    assert people == ()
    assert assignments[0].status is AssignmentStatus.UNASSIGNED


def test_invalid_box_and_margin_are_rejected() -> None:
    with pytest.raises(ValueError):
        BoundingBox(10, 0, 5, 20)
    with pytest.raises(ValueError):
        assign_equipment_to_people([], ambiguity_margin=1.5)


class FakeTrackerState:
    def __init__(self) -> None:
        self.reset_count = 0

    def reset(self) -> None:
        self.reset_count += 1


class FakePredictor:
    def __init__(self, trackers) -> None:
        self.trackers = trackers


class FakeModel:
    predictor = None

    def track(self, **_kwargs):
        raise AssertionError("Bu testte çıkarım yapılmamalı")


def test_starting_new_session_resets_existing_bytetrack_state() -> None:
    states = [FakeTrackerState(), FakeTrackerState()]
    model = FakeModel()
    model.predictor = FakePredictor(states)
    tracker = UltralyticsPpeTracker(Path("unused.pt"), model=model)

    tracker.start_session("new-session")

    assert [state.reset_count for state in states] == [1, 1]


def test_frame_from_another_session_is_rejected_before_inference() -> None:
    tracker = UltralyticsPpeTracker(Path("unused.pt"), model=FakeModel())
    tracker.start_session("expected")
    frame = VideoFrame(
        source_id="camera",
        session_id="other",
        frame_index=0,
        source_timestamp_seconds=0.0,
        observed_at_utc=datetime(2026, 11, 9, tzinfo=UTC),
        image=object(),
    )

    with pytest.raises(RuntimeError, match="etkin takip oturumuna"):
        tracker.process_frame(frame)


def test_missing_tracker_dependency_stops_without_auto_install(tmp_path, monkeypatch) -> None:
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"local")
    monkeypatch.setattr(ppe_tracking, "find_spec", lambda _name: None)

    with pytest.raises(RuntimeError, match="otomatik indirme kapalı"):
        UltralyticsPpeTracker(model_path)

    assert ppe_tracking.os.environ["YOLO_AUTOINSTALL"] == "False"
