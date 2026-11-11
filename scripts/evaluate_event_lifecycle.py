"""E2 olay birleştirme, bildirim ve bitiş politikasını kontrollü akışta ölçer."""

from __future__ import annotations

import json
import uuid
from typing import Any

from isg_api.event_lifecycle import EventLifecycleKey, EventLifecycleTracker
from isg_api.rules import Equipment


def evaluate() -> dict[str, Any]:
    event_ids = iter((uuid.UUID(int=100), uuid.UUID(int=101)))
    tracker = EventLifecycleTracker(event_id_factory=lambda: next(event_ids))
    key = EventLifecycleKey(
        camera_session_id=uuid.UUID(int=1),
        rule_version_id=uuid.UUID(int=2),
        track_id=7,
    )

    transitions = []
    for observed_at, equipment in (
        (0.0, [Equipment.HELMET]),
        (0.5, [Equipment.HELMET]),
        (1.0, [Equipment.HELMET, Equipment.VEST]),
        (1.5, []),
        (2.0, [Equipment.VEST]),
        (2.5, []),
        (3.5, []),
        (4.0, [Equipment.HELMET]),
    ):
        transitions.extend(tracker.observe(key, equipment, observed_at))

    return {
        "started_count": sum(item.kind.value == "started" for item in transitions),
        "notification_count": sum(item.notification_required for item in transitions),
        "ended_reasons": [
            item.end_reason.value for item in transitions if item.end_reason is not None
        ],
        "event_ids": [str(item.event_id) for item in transitions],
        "active_event_count": tracker.active_event_count,
    }


def main() -> int:
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
