from datetime import UTC, datetime, timedelta

import pytest

from isg_api.frame_queue import FramePipelineStatus, LatestFrameQueue
from isg_api.video_source import VideoFrame


class FakeTime:
    def __init__(self) -> None:
        self.seconds = 10.0
        self.utc = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)

    def monotonic(self) -> float:
        return self.seconds

    def utc_now(self) -> datetime:
        return self.utc

    def advance(self, seconds: float) -> None:
        self.seconds += seconds
        self.utc += timedelta(seconds=seconds)


def frame(index: int, session_id: str = "session-a") -> VideoFrame:
    return VideoFrame(
        source_id="camera",
        session_id=session_id,
        frame_index=index,
        source_timestamp_seconds=index / 25,
        observed_at_utc=datetime(2026, 11, 9, 12, 0, tzinfo=UTC),
        image=f"image-{index}",
    )


def make_queue(clock: FakeTime, capacity=2) -> LatestFrameQueue:
    return LatestFrameQueue(
        capacity,
        stale_after_seconds=2.0,
        monotonic=clock.monotonic,
        utc_now=clock.utc_now,
    )


def test_full_queue_drops_oldest_frame_without_blocking() -> None:
    clock = FakeTime()
    queue = make_queue(clock)
    queue.start_session("session-a")

    queue.put(frame(0))
    queue.put(frame(1))
    queue.put(frame(2))

    assert queue.get().frame_index == 1
    assert queue.get().frame_index == 2
    assert queue.snapshot().dropped_count == 1


def test_new_session_clears_old_frames_and_counters() -> None:
    clock = FakeTime()
    queue = make_queue(clock)
    queue.start_session("session-a")
    queue.put(frame(0))

    queue.start_session("session-b")

    snapshot = queue.snapshot()
    assert snapshot.session_id == "session-b"
    assert snapshot.queue_size == 0
    assert snapshot.received_count == snapshot.dropped_count == 0
    with pytest.raises(RuntimeError, match="etkin kuyruk oturumuna"):
        queue.put(frame(1, "session-a"))


def test_snapshot_distinguishes_idle_backlog_healthy_and_stale() -> None:
    clock = FakeTime()
    queue = make_queue(clock, capacity=1)
    queue.start_session("session-a")
    assert queue.snapshot().status is FramePipelineStatus.IDLE

    queue.put(frame(0))
    assert queue.snapshot().status is FramePipelineStatus.BACKLOG

    queue.get()
    assert queue.snapshot().status is FramePipelineStatus.HEALTHY

    clock.advance(2.1)
    assert queue.snapshot().status is FramePipelineStatus.STALE

    queue.close()
    assert queue.snapshot().status is FramePipelineStatus.STOPPED


def test_processed_frame_records_count_and_latency() -> None:
    clock = FakeTime()
    queue = make_queue(clock)
    queue.start_session("session-a")
    item = frame(0)
    queue.put(item)
    clock.advance(0.25)

    queue.mark_processed(item)

    snapshot = queue.snapshot()
    assert snapshot.processed_count == 1
    assert snapshot.last_processing_latency_ms == 250.0


def test_closed_empty_queue_returns_none() -> None:
    clock = FakeTime()
    queue = make_queue(clock)
    queue.start_session("session-a")
    queue.close()

    assert queue.get() is None


def test_invalid_configuration_and_timeout_are_reported() -> None:
    clock = FakeTime()
    with pytest.raises(ValueError):
        LatestFrameQueue(0)
    queue = make_queue(clock)
    queue.start_session("session-a")

    with pytest.raises(TimeoutError):
        queue.get(timeout=0)
