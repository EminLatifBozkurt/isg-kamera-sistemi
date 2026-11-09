from datetime import UTC, datetime, timedelta

import pytest

from isg_api.webcam_source import (
    WebcamReadError,
    WebcamSource,
    WebcamStatus,
    WebcamUnavailableError,
)


class FakeClock:
    def __init__(self) -> None:
        self.monotonic_value = 10.0
        self.utc_value = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)

    def monotonic(self) -> float:
        value = self.monotonic_value
        self.monotonic_value += 0.04
        return value

    def utc_now(self) -> datetime:
        value = self.utc_value
        self.utc_value += timedelta(milliseconds=40)
        return value


class FakeWebcamCapture:
    def __init__(
        self,
        frames: list[object],
        *,
        opened: bool = True,
        fps: float = 25.0,
    ) -> None:
        self.frames = list(frames)
        self._opened = opened
        self._fps = fps
        self.released = False

    @property
    def is_opened(self) -> bool:
        return self._opened

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def frame_count(self) -> None:
        return None

    @property
    def width(self) -> int:
        return 1280

    @property
    def height(self) -> int:
        return 720

    @property
    def position_seconds(self) -> None:
        return None

    def read(self) -> tuple[bool, object | None]:
        if not self.frames:
            return False, None
        return True, self.frames.pop(0)

    def release(self) -> None:
        self.released = True


def make_source(capture_factory, clock=None) -> WebcamSource:
    clock = clock or FakeClock()
    return WebcamSource(
        0,
        source_id="dahili-kamera",
        capture_factory=capture_factory,
        monotonic=clock.monotonic,
        utc_now=clock.utc_now,
    )


def test_webcam_open_and_close_statuses_are_explicit() -> None:
    capture = FakeWebcamCapture(["frame"])
    source = make_source(lambda _: capture)

    session = source.open_session()

    assert source.status.status is WebcamStatus.STREAMING
    assert source.status.message == "Webcam açıldı; ilk kare bekleniyor"
    assert source.status.session_id == session.metadata.session_id
    assert session.metadata.reported_fps == 25.0

    session.close()

    assert source.status.status is WebcamStatus.STOPPED
    assert capture.released


def test_frames_update_count_time_and_tracking_scope() -> None:
    clock = FakeClock()
    capture = FakeWebcamCapture(["first", "second"])
    source = make_source(lambda _: capture, clock)
    session = source.open_session()
    frames = session.frames()

    first = next(frames)
    second = next(frames)
    frames.close()

    assert [first.frame_index, second.frame_index] == [0, 1]
    assert first.source_timestamp_seconds == pytest.approx(0.04)
    assert second.source_timestamp_seconds == pytest.approx(0.08)
    assert first.tracking_scope == second.tracking_scope
    assert source.status.frame_count == 2
    assert source.status.last_frame_at_utc == second.observed_at_utc
    assert source.status.status is WebcamStatus.STOPPED


def test_read_failure_is_not_hidden_as_normal_stop() -> None:
    capture = FakeWebcamCapture([])
    source = make_source(lambda _: capture)
    session = source.open_session()

    with pytest.raises(WebcamReadError, match="yeni kare okunamadı"):
        next(session.frames())

    assert source.status.status is WebcamStatus.READ_ERROR
    assert capture.released


def test_unavailable_camera_updates_status_and_releases_capture() -> None:
    capture = FakeWebcamCapture([], opened=False)
    source = make_source(lambda _: capture)

    with pytest.raises(WebcamUnavailableError, match="erişilemiyor"):
        source.open_session()

    assert source.status.status is WebcamStatus.UNAVAILABLE
    assert capture.released


def test_capture_factory_error_is_reported_as_unavailable() -> None:
    def failing_factory(_index):
        raise OSError("driver error")

    source = make_source(failing_factory)

    with pytest.raises(WebcamUnavailableError, match="oluşturulamadı"):
        source.open_session()

    assert source.status.status is WebcamStatus.UNAVAILABLE


def test_second_session_is_rejected_while_first_is_active() -> None:
    source = make_source(lambda _: FakeWebcamCapture(["frame"]))
    session = source.open_session()

    with pytest.raises(RuntimeError, match="zaten etkin"):
        source.open_session()

    session.close()


def test_reopening_camera_uses_new_session_and_tracking_scope() -> None:
    captures = [FakeWebcamCapture(["a"]), FakeWebcamCapture(["b"])]
    source = make_source(lambda _: captures.pop(0))

    first_session = source.open_session()
    first_frame = next(first_session.frames())
    first_session.close()
    second_session = source.open_session()
    second_frame = next(second_session.frames())
    second_session.close()

    assert first_session.metadata.session_id != second_session.metadata.session_id
    assert first_frame.tracking_scope != second_frame.tracking_scope


@pytest.mark.parametrize(
    ("device_index", "source_id"),
    [(-1, "camera"), (0, "   ")],
)
def test_invalid_webcam_configuration_is_rejected(device_index, source_id) -> None:
    with pytest.raises(ValueError):
        WebcamSource(device_index, source_id=source_id)


@pytest.mark.parametrize("fps", [0.0, -1.0, float("nan")])
def test_missing_reported_fps_does_not_block_live_camera(fps) -> None:
    source = make_source(lambda _: FakeWebcamCapture(["frame"], fps=fps))

    session = source.open_session()

    assert session.metadata.reported_fps is None
    session.close()
