from __future__ import annotations

import hashlib
import threading
import time
import uuid
from datetime import UTC, datetime

import pytest

from isg_api.evidence_capture import (
    EncodedEvidenceFrame,
    EvidenceArtifact,
    EvidenceCaptureManager,
    EvidenceCompletionReason,
    EvidencePolicy,
    EvidenceStatus,
    EvidenceWriteResult,
    FilesystemEvidenceWriter,
    PreparedEvidence,
)


def frame(second: float, *, session_id: str = "session-a", content: bytes | None = None):
    return EncodedEvidenceFrame(
        session_id=session_id,
        source_timestamp_seconds=second,
        observed_at_utc=datetime(2026, 11, 11, 10, 0, tzinfo=UTC),
        jpeg_bytes=content or f"jpeg-{second}".encode(),
        width=640,
        height=360,
    )


def result_for(event_id: uuid.UUID) -> EvidenceWriteResult:
    digest = hashlib.sha256(str(event_id).encode()).hexdigest()
    return EvidenceWriteResult(
        snapshot=EvidenceArtifact(
            relative_path=f"events/{event_id}/snapshot.jpg",
            mime_type="image/jpeg",
            size_bytes=10,
            sha256=digest,
        ),
        clip=EvidenceArtifact(
            relative_path=f"events/{event_id}/clip.mp4",
            mime_type="video/mp4",
            size_bytes=20,
            sha256=digest,
        ),
    )


class RecordingWriter:
    def __init__(self) -> None:
        self.items: list[PreparedEvidence] = []

    def write(self, evidence: PreparedEvidence) -> EvidenceWriteResult:
        self.items.append(evidence)
        return result_for(evidence.event_id)


class FailingWriter:
    def write(self, evidence: PreparedEvidence) -> EvidenceWriteResult:
        raise OSError("disk dolu\nayrıntı")


class BlockingWriter:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()

    def write(self, evidence: PreparedEvidence) -> EvidenceWriteResult:
        self.started.set()
        if not self.release.wait(3):
            raise TimeoutError("test yazıcısı serbest bırakılmadı")
        return result_for(evidence.event_id)


def test_policy_and_frame_reject_invalid_limits() -> None:
    with pytest.raises(ValueError):
        EvidencePolicy(pre_event_seconds=0, post_event_seconds=0)
    with pytest.raises(ValueError):
        EvidencePolicy(max_buffer_bytes=0)
    with pytest.raises(ValueError):
        frame(-1)
    with pytest.raises(ValueError):
        EncodedEvidenceFrame("session", 0, datetime(2026, 1, 1), b"jpeg", 1, 1)


def test_buffer_is_bounded_by_frame_count_and_bytes() -> None:
    manager = EvidenceCaptureManager(
        RecordingWriter(),
        EvidencePolicy(
            pre_event_seconds=100,
            post_event_seconds=1,
            max_buffer_frames=2,
            max_buffer_bytes=7,
        ),
    )
    try:
        manager.start_session("session-a")
        manager.ingest(frame(0, content=b"1111"))
        manager.ingest(frame(1, content=b"2222"))
        assert manager.buffered_frame_count == 1
        assert manager.buffered_bytes == 4

        manager.ingest(frame(2, content=b"33"))
        manager.ingest(frame(3, content=b"4"))
        assert manager.buffered_frame_count == 2
        assert manager.buffered_bytes == 3
    finally:
        manager.close()


def test_buffer_discards_frames_older_than_pre_event_window() -> None:
    manager = EvidenceCaptureManager(
        RecordingWriter(), EvidencePolicy(pre_event_seconds=2, post_event_seconds=1)
    )
    try:
        manager.start_session("session-a")
        for second in (0.0, 1.0, 3.0):
            manager.ingest(frame(second))
        assert manager.buffered_frame_count == 2
    finally:
        manager.close()


def test_event_collects_snapshot_pre_frames_and_post_frames() -> None:
    writer = RecordingWriter()
    manager = EvidenceCaptureManager(
        writer, EvidencePolicy(pre_event_seconds=2, post_event_seconds=1)
    )
    event_id = uuid.UUID(int=1)
    try:
        manager.start_session("session-a")
        for second in (8.0, 9.0, 10.0):
            manager.ingest(frame(second))

        initial = manager.start_event(event_id, session_id="session-a", event_source_time=10.0)
        assert initial.status is EvidenceStatus.PREPARING
        assert initial.snapshot_source_time == 10.0
        assert initial.clip_frame_count == 3

        assert manager.ingest(frame(10.5)) == ()
        assert manager.ingest(frame(11.0)) == (event_id,)
        finished = manager.wait_until_finished(event_id)

        assert finished.status is EvidenceStatus.READY
        assert finished.completion_reason is EvidenceCompletionReason.POST_WINDOW_COMPLETE
        assert not finished.is_partial
        assert finished.clip_frame_count == 5
        assert [item.source_timestamp_seconds for item in writer.items[0].clip_frames] == [
            8.0,
            9.0,
            10.0,
            10.5,
            11.0,
        ]
    finally:
        manager.close()


def test_session_end_submits_short_clip_as_partial() -> None:
    writer = RecordingWriter()
    manager = EvidenceCaptureManager(
        writer, EvidencePolicy(pre_event_seconds=1, post_event_seconds=5)
    )
    event_id = uuid.UUID(int=2)
    try:
        manager.start_session("session-a")
        manager.ingest(frame(4))
        manager.start_event(event_id, session_id="session-a", event_source_time=4)
        manager.ingest(frame(4.5))

        assert manager.end_session("session-a") == (event_id,)
        finished = manager.wait_until_finished(event_id)

        assert finished.status is EvidenceStatus.READY
        assert finished.is_partial
        assert finished.completion_reason is EvidenceCompletionReason.SESSION_ENDED
        assert finished.clip_frame_count == 2
        assert writer.items[0].is_partial
    finally:
        manager.close()


def test_writer_failure_sets_failed_status_with_single_line_error() -> None:
    manager = EvidenceCaptureManager(
        FailingWriter(), EvidencePolicy(pre_event_seconds=1, post_event_seconds=0)
    )
    event_id = uuid.UUID(int=3)
    try:
        manager.start_session("session-a")
        manager.ingest(frame(1))
        manager.start_event(event_id, session_id="session-a", event_source_time=1)

        finished = manager.wait_until_finished(event_id)
        assert finished.status is EvidenceStatus.FAILED
        assert finished.error_message == "OSError: disk dolu ayrıntı"
        assert finished.result is None
    finally:
        manager.close()


def test_analysis_calls_do_not_wait_for_slow_writer() -> None:
    writer = BlockingWriter()
    manager = EvidenceCaptureManager(
        writer, EvidencePolicy(pre_event_seconds=1, post_event_seconds=0)
    )
    event_id = uuid.UUID(int=4)
    try:
        manager.start_session("session-a")
        manager.ingest(frame(1))
        started_at = time.perf_counter()
        manager.start_event(event_id, session_id="session-a", event_source_time=1)
        elapsed = time.perf_counter() - started_at

        assert elapsed < 0.1
        assert writer.started.wait(1)
        assert manager.job_snapshot(event_id).status is EvidenceStatus.PREPARING
        writer.release.set()
        assert manager.wait_until_finished(event_id).status is EvidenceStatus.READY
    finally:
        writer.release.set()
        manager.close()


def test_full_writer_queue_fails_new_job_instead_of_blocking_analysis() -> None:
    writer = BlockingWriter()
    manager = EvidenceCaptureManager(
        writer,
        EvidencePolicy(
            pre_event_seconds=1,
            post_event_seconds=0,
            max_pending_writes=1,
        ),
    )
    ids = [uuid.UUID(int=value) for value in (10, 11, 12)]
    try:
        manager.start_session("session-a")
        manager.ingest(frame(1))
        manager.start_event(ids[0], session_id="session-a", event_source_time=1)
        assert writer.started.wait(1)

        manager.ingest(frame(2))
        manager.start_event(ids[1], session_id="session-a", event_source_time=2)
        manager.ingest(frame(3))
        started_at = time.perf_counter()
        third = manager.start_event(ids[2], session_id="session-a", event_source_time=3)
        elapsed = time.perf_counter() - started_at

        assert elapsed < 0.1
        assert third.status is EvidenceStatus.FAILED
        assert "kuyruğu dolu" in (third.error_message or "")
        writer.release.set()
        assert manager.wait_until_finished(ids[0]).status is EvidenceStatus.READY
        assert manager.wait_until_finished(ids[1]).status is EvidenceStatus.READY
    finally:
        writer.release.set()
        manager.close()


def test_session_and_source_time_boundaries_are_enforced() -> None:
    manager = EvidenceCaptureManager(
        RecordingWriter(), EvidencePolicy(pre_event_seconds=1, post_event_seconds=1)
    )
    try:
        manager.start_session("session-a")
        with pytest.raises(RuntimeError, match="etkin kanıt oturumuna"):
            manager.ingest(frame(1, session_id="session-b"))
        manager.ingest(frame(2))
        with pytest.raises(ValueError, match="geriye gidemez"):
            manager.ingest(frame(1))
        with pytest.raises(RuntimeError, match="uygun tampon karesi yok"):
            manager.start_event(uuid.uuid4(), session_id="session-a", event_source_time=20)
        with pytest.raises(RuntimeError, match="Önce etkin"):
            manager.start_session("session-b")
    finally:
        manager.close()


class FakeClipEncoder:
    def encode(self, path, frames) -> None:
        path.write_bytes(b"mp4-" + str(len(frames)).encode())


class FailingClipEncoder:
    def encode(self, path, frames) -> None:
        path.write_bytes(b"partial")
        raise RuntimeError("encoder failed")


def prepared(event_id: uuid.UUID) -> PreparedEvidence:
    item = frame(1, content=b"jpeg-content")
    return PreparedEvidence(
        event_id=event_id,
        session_id="session-a",
        snapshot_frame=item,
        clip_frames=(item,),
        completion_reason=EvidenceCompletionReason.POST_WINDOW_COMPLETE,
        is_partial=False,
    )


def test_filesystem_writer_creates_relative_artifacts_and_hashes(tmp_path) -> None:
    event_id = uuid.UUID(int=20)
    writer = FilesystemEvidenceWriter(tmp_path, clip_encoder=FakeClipEncoder())

    result = writer.write(prepared(event_id))

    snapshot_path = tmp_path / result.snapshot.relative_path
    clip_path = tmp_path / result.clip.relative_path
    assert snapshot_path.read_bytes() == b"jpeg-content"
    assert clip_path.read_bytes() == b"mp4-1"
    assert result.snapshot.mime_type == "image/jpeg"
    assert result.clip.mime_type == "video/mp4"
    assert result.snapshot.sha256 == hashlib.sha256(b"jpeg-content").hexdigest()
    assert not list(tmp_path.rglob("*.part.*"))


def test_filesystem_writer_removes_partial_files_after_encoding_error(tmp_path) -> None:
    event_id = uuid.UUID(int=21)
    writer = FilesystemEvidenceWriter(tmp_path, clip_encoder=FailingClipEncoder())

    with pytest.raises(RuntimeError, match="encoder failed"):
        writer.write(prepared(event_id))

    event_directory = tmp_path / "events" / str(event_id)
    assert list(event_directory.iterdir()) == []


def test_filesystem_writer_never_overwrites_existing_event_evidence(tmp_path) -> None:
    event_id = uuid.UUID(int=22)
    writer = FilesystemEvidenceWriter(tmp_path, clip_encoder=FakeClipEncoder())
    first = writer.write(prepared(event_id))

    with pytest.raises(FileExistsError, match="üzerine yazılmadı"):
        writer.write(prepared(event_id))

    assert (tmp_path / first.snapshot.relative_path).read_bytes() == b"jpeg-content"
    assert (tmp_path / first.clip.relative_path).read_bytes() == b"mp4-1"
