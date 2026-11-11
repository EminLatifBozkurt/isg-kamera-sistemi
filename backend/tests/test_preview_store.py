import uuid
from datetime import UTC, datetime, timedelta

import pytest

from isg_api.preview_store import FilesystemPreviewStore, PreviewState

JPEG_ONE = b"\xff\xd8first-jpeg\xff\xd9"
JPEG_TWO = b"\xff\xd8second-jpeg\xff\xd9"


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)

    def utc_now(self) -> datetime:
        return self.now


def test_missing_preview_is_explicitly_unavailable(tmp_path) -> None:
    store = FilesystemPreviewStore(tmp_path)

    snapshot, content = store.read(uuid.uuid4())

    assert snapshot.state is PreviewState.UNAVAILABLE
    assert snapshot.captured_at is None
    assert content is None


def test_published_preview_is_shared_as_single_latest_file(tmp_path) -> None:
    clock = Clock()
    camera_id = uuid.uuid4()
    store = FilesystemPreviewStore(tmp_path, utc_now=clock.utc_now)

    first = store.publish(camera_id, JPEG_ONE, captured_at=clock.now)
    second = store.publish(camera_id, JPEG_TWO, captured_at=clock.now)
    snapshot, content = store.read(camera_id)

    assert first.path == second.path == snapshot.path
    assert content == JPEG_TWO
    assert snapshot.state is PreviewState.LIVE
    assert list(tmp_path.glob(f"{camera_id}*.jpg")) == [snapshot.path]
    assert not list(tmp_path.glob("*.part"))


def test_old_preview_is_marked_stale_but_remains_readable(tmp_path) -> None:
    clock = Clock()
    camera_id = uuid.uuid4()
    store = FilesystemPreviewStore(tmp_path, stale_after_seconds=3, utc_now=clock.utc_now)
    store.publish(camera_id, JPEG_ONE, captured_at=clock.now)

    clock.now += timedelta(seconds=3.1)
    snapshot, content = store.read(camera_id)

    assert snapshot.state is PreviewState.STALE
    assert snapshot.age_seconds == 3.1
    assert content == JPEG_ONE


def test_future_file_time_does_not_create_negative_age(tmp_path) -> None:
    clock = Clock()
    store = FilesystemPreviewStore(tmp_path, utc_now=clock.utc_now)

    snapshot = store.publish(uuid.uuid4(), JPEG_ONE, captured_at=clock.now + timedelta(seconds=2))

    assert snapshot.age_seconds == 0
    assert snapshot.state is PreviewState.LIVE


@pytest.mark.parametrize("content", [b"", b"not-jpeg", b"\xff\xd8unfinished"])
def test_invalid_jpeg_is_rejected_without_partial_file(tmp_path, content) -> None:
    store = FilesystemPreviewStore(tmp_path)

    with pytest.raises(ValueError, match="JPEG"):
        store.publish(uuid.uuid4(), content, captured_at=datetime.now(UTC))

    assert list(tmp_path.iterdir()) == []


def test_capture_time_must_include_timezone(tmp_path) -> None:
    store = FilesystemPreviewStore(tmp_path)

    with pytest.raises(ValueError, match="saat dilimi"):
        store.publish(uuid.uuid4(), JPEG_ONE, captured_at=datetime(2026, 11, 11))
