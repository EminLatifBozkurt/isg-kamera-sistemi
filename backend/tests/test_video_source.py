from datetime import UTC, datetime

import pytest

from isg_api.video_source import RecordedVideoSource, VideoSessionStatus


class FakeClock:
    def __init__(self) -> None:
        self.value = 100.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds


class FakeCapture:
    def __init__(
        self,
        frames: list[tuple[object, float | None]],
        *,
        fps: float = 25.0,
        opened: bool = True,
    ) -> None:
        self._frames = frames
        self._fps = fps
        self._opened = opened
        self._position = -1
        self.released = False

    @property
    def is_opened(self) -> bool:
        return self._opened

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    @property
    def width(self) -> int:
        return 640

    @property
    def height(self) -> int:
        return 360

    @property
    def position_seconds(self) -> float | None:
        return self._frames[self._position][1]

    def read(self) -> tuple[bool, object | None]:
        self._position += 1
        if self._position >= len(self._frames):
            return False, None
        return True, self._frames[self._position][0]

    def release(self) -> None:
        self.released = True


def make_source(tmp_path, factory, clock=None) -> RecordedVideoSource:
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"test-double")
    clock = clock or FakeClock()
    return RecordedVideoSource(
        video,
        source_id="demo-kamera",
        capture_factory=factory,
        monotonic=clock.monotonic,
        sleeper=clock.sleep,
        utc_now=lambda: datetime(2026, 11, 9, tzinfo=UTC),
    )


def test_video_frames_keep_source_and_session_identity(tmp_path) -> None:
    capture = FakeCapture([("first", 0.0), ("second", 0.04)])
    source = make_source(tmp_path, lambda _: capture)
    session = source.open_session()

    frames = list(session.frames(realtime=False))

    assert [frame.frame_index for frame in frames] == [0, 1]
    assert [frame.source_timestamp_seconds for frame in frames] == [0.0, 0.04]
    assert {frame.session_id for frame in frames} == {session.metadata.session_id}
    assert frames[0].tracking_scope.startswith("demo-kamera:")
    assert session.status is VideoSessionStatus.COMPLETED
    assert capture.released


def test_realtime_reading_waits_for_source_timestamps(tmp_path) -> None:
    clock = FakeClock()
    capture = FakeCapture([("a", 0.0), ("b", 0.04), ("c", 0.08)])
    source = make_source(tmp_path, lambda _: capture, clock)

    list(source.open_session().frames())

    assert clock.sleeps == pytest.approx([0.04, 0.04])


def test_invalid_or_repeated_timestamps_fall_back_to_fps(tmp_path) -> None:
    capture = FakeCapture([("a", None), ("b", None), ("c", 0.0)], fps=10.0)
    source = make_source(tmp_path, lambda _: capture)

    frames = list(source.open_session().frames(realtime=False))

    assert [frame.source_timestamp_seconds for frame in frames] == [0.0, 0.1, 0.2]


def test_reopening_same_video_creates_new_tracking_scope(tmp_path) -> None:
    captures = [FakeCapture([("a", 0.0)]), FakeCapture([("a", 0.0)])]
    source = make_source(tmp_path, lambda _: captures.pop(0))

    first = list(source.open_session().frames(realtime=False))[0]
    second = list(source.open_session().frames(realtime=False))[0]

    assert first.session_id != second.session_id
    assert first.tracking_scope != second.tracking_scope
    assert first.frame_index == second.frame_index == 0


def test_session_cannot_be_read_twice(tmp_path) -> None:
    source = make_source(tmp_path, lambda _: FakeCapture([("a", 0.0)]))
    session = source.open_session()
    list(session.frames(realtime=False))

    with pytest.raises(RuntimeError, match="tek kullanımlıktır"):
        list(session.frames(realtime=False))


@pytest.mark.parametrize("fps", [0.0, -1.0, float("nan")])
def test_invalid_fps_is_rejected_and_capture_is_released(tmp_path, fps) -> None:
    capture = FakeCapture([], fps=fps)
    source = make_source(tmp_path, lambda _: capture)

    with pytest.raises(ValueError, match="FPS"):
        source.open_session()

    assert capture.released


def test_unsupported_video_is_rejected(tmp_path) -> None:
    capture = FakeCapture([], opened=False)
    source = make_source(tmp_path, lambda _: capture)

    with pytest.raises(ValueError, match="Video açılamadı"):
        source.open_session()

    assert capture.released


def test_stopping_early_releases_capture(tmp_path) -> None:
    capture = FakeCapture([("a", 0.0), ("b", 0.04)])
    source = make_source(tmp_path, lambda _: capture)
    session = source.open_session()
    iterator = session.frames(realtime=False)

    next(iterator)
    iterator.close()

    assert session.status is VideoSessionStatus.STOPPED
    assert capture.released
