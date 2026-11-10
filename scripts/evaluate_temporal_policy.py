"""E1 başlangıç eşiklerini kontrollü zaman dizileriyle görünür biçimde ölçer."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from typing import Any

from isg_api.rules import Assessment, Equipment
from isg_api.temporal_violations import (
    TemporalObservationKey,
    TemporalPolicy,
    TemporalViolationTracker,
)

SCENARIOS: dict[str, list[tuple[float, Assessment]]] = {
    "single_bad_frame": [(0.0, Assessment.VIOLATION_CANDIDATE)],
    "rapid_four_frames": [
        (0.0, Assessment.VIOLATION_CANDIDATE),
        (0.1, Assessment.VIOLATION_CANDIDATE),
        (0.2, Assessment.VIOLATION_CANDIDATE),
        (0.3, Assessment.VIOLATION_CANDIDATE),
    ],
    "sustained_violation": [
        (0.0, Assessment.VIOLATION_CANDIDATE),
        (0.5, Assessment.VIOLATION_CANDIDATE),
        (1.0, Assessment.VIOLATION_CANDIDATE),
        (1.5, Assessment.VIOLATION_CANDIDATE),
    ],
    "sparse_violation": [
        (0.0, Assessment.VIOLATION_CANDIDATE),
        (0.5, Assessment.VIOLATION_CANDIDATE),
        (1.6, Assessment.VIOLATION_CANDIDATE),
        (2.1, Assessment.VIOLATION_CANDIDATE),
    ],
    "brief_unknown": [
        (0.0, Assessment.VIOLATION_CANDIDATE),
        (0.5, Assessment.VIOLATION_CANDIDATE),
        (0.9, Assessment.UNASSESSABLE),
        (1.0, Assessment.VIOLATION_CANDIDATE),
        (1.5, Assessment.VIOLATION_CANDIDATE),
    ],
    "compliant_reset": [
        (0.0, Assessment.VIOLATION_CANDIDATE),
        (0.5, Assessment.VIOLATION_CANDIDATE),
        (1.0, Assessment.VIOLATION_CANDIDATE),
        (1.2, Assessment.COMPLIANT),
        (1.5, Assessment.VIOLATION_CANDIDATE),
    ],
}


def evaluate() -> dict[str, Any]:
    policy = TemporalPolicy()
    scenario_results: dict[str, dict[str, Any]] = {}
    for index, (name, observations) in enumerate(SCENARIOS.items(), start=1):
        tracker = TemporalViolationTracker(policy)
        key = TemporalObservationKey(
            camera_session_id=uuid.UUID(int=index),
            rule_version_id=uuid.UUID(int=100),
            track_id=1,
            equipment=Equipment.HELMET,
        )
        results = [
            tracker.observe(key, assessment, observed_at)
            for observed_at, assessment in observations
        ]
        scenario_results[name] = {
            "candidate_created": any(result.became_candidate for result in results),
            "final_decision": results[-1].decision.value,
            "final_observation_count": results[-1].violation_observation_count,
            "final_duration_seconds": results[-1].violation_duration_seconds,
        }
    return {"policy": asdict(policy), "scenarios": scenario_results}


def main() -> int:
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
